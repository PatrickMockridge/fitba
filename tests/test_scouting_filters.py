"""Verify the reader-filter data contract and the published defaults.

The hub and the advanced search recompute leader lists in the browser from
`scouting/search/meta.json` and its shards. These tests reproduce the published defaults from
that index with the registered formulas, so the client cannot silently drift
from the publisher.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCOUTING = ROOT / "web" / "data" / "generated" / "scouting"
SEARCH = SCOUTING / "search"
SEARCH_SHARDS = 4
HUB = SCOUTING / "aberdeen.json"
POOL = SCOUTING / "pool"

ATTACK_FAMILIES = {"centre_forward", "wide_forward", "attacking_midfield"}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def search() -> dict:
    meta = _load(SEARCH / "meta.json")
    players = []
    for shard in range(SEARCH_SHARDS):
        players.extend(_load(SEARCH / f"players-{shard}.json").get("players") or [])
    assert players, "run `uv run fitba publish` first"
    return {**meta, "players": players}


@pytest.fixture(scope="module")
def hub() -> dict:
    return _load(HUB)


def _age_multiplier(row: dict, priority: dict) -> float:
    age = row.get("a")
    return (
        float(priority["u23_multiplier"])
        if age is not None and int(age) <= int(priority["u23_max_age"])
        else 1.0
    )


def _europe_multiplier(row: dict, priority: dict) -> float:
    return float(priority["europe_multiplier"]) if row.get("es") == "qualified" else 1.0


def _profile_entry(row: dict, profile_id: str, order: dict[str, int]) -> list | None:
    index = order[profile_id]
    for entry in row.get("arp") or []:
        if entry[0] == index:
            return entry
    return None


def _profile_scores(row: dict, profile_keys: list[str]) -> dict[str, float]:
    return {
        profile_keys[entry[0]]: float(entry[1])
        for entry in row.get("arp") or []
        if entry[1] is not None and entry[0] < len(profile_keys)
    }


def _value_index(row: dict, value_model: dict) -> float | None:
    weights = value_model["weights"]
    components: dict[str, float] = {}
    if row.get("ap") is not None:
        components["performance"] = float(row["ap"]) / 100
    age = row.get("a")
    if age is not None:
        curve = None
        for band in value_model["age_curve"]:
            if int(age) <= int(band["max_age"]):
                curve = float(band["factor"])
                break
        if curve is not None:
            components["age"] = curve
    minutes = int(row.get("m") or 0)
    if minutes > 0:
        components["minutes"] = min(1.0, minutes / float(value_model["minutes_full"]))
    scores = [float(entry[1]) for entry in row.get("arp") or [] if entry[1] is not None]
    if scores:
        components["profile"] = max(scores) / 100
    total = sum(float(value) for value in weights.values())
    if total <= 0:
        return None
    available = sum(float(weights[key]) for key in components)
    coverage = available / total
    if coverage < float(value_model["min_weight_coverage"]):
        return None
    value = sum(float(weights[key]) * component for key, component in components.items())
    return round(100 * value / available, 1)


def _priority(row: dict, search: dict) -> float | None:
    value = row.get("vi")
    if value is None:
        return None
    priority = search["priority"]
    return round(
        float(value) * _age_multiplier(row, priority) * _europe_multiplier(row, priority),
        1,
    )


def test_search_projection_fields(search: dict) -> None:
    assert search["archetype_min_coverage"] == 0.7
    assert search["value_model"]["weights"] == {
        "performance": 0.55,
        "age": 0.15,
        "minutes": 0.15,
        "profile": 0.15,
    }
    assert search["value_model"]["min_weight_coverage"] == 0.7
    assert search["value_model"]["minutes_full"] == 1800
    assert search["team_context"] == {
        "min_lift": 0,
        "underperforming_ppg_percentile_max": 40,
    }
    for row in search["players"]:
        for entry in row.get("arp") or []:
            assert isinstance(entry, list) and len(entry) == 4
            assert 0 <= entry[0] < len(search["profile_labels"])
        for key in ("gl", "ast", "g90", "sh90", "cv"):
            if key in row:
                assert isinstance(row[key], (int, float))


def test_default_value_index_reproduces(search: dict) -> None:
    mismatches = []
    for row in search["players"]:
        expected = _value_index(row, search["value_model"])
        published = row.get("vi")
        if expected is None or published is None:
            if expected != published:
                mismatches.append((row["i"], row["l"], published, expected))
            continue
        if abs(float(published) - expected) > 0.1:
            mismatches.append((row["i"], row["l"], published, expected))
    assert not mismatches[:10], f"{len(mismatches)} value-index mismatches"


def test_default_priority_reproduces(search: dict) -> None:
    mismatches = []
    for path in sorted(POOL.glob("*.json")):
        document = _load(path)
        for row in document.get("players") or []:
            key = (int(row["player_id"]), str(document["league"]["slug"]))
            search_row = next(
                (
                    item
                    for item in search["players"]
                    if int(item["i"]) == key[0] and str(item["l"]) == key[1]
                ),
                None,
            )
            if search_row is None:
                continue
            expected = _priority(search_row, search)
            published = row.get("scouting_priority")
            if expected is None or published is None:
                if expected != published:
                    mismatches.append((key, published, expected))
                continue
            if abs(float(published) - expected) > 0.1:
                mismatches.append((key, published, expected))
            if len(mismatches) > 10:
                break
    assert not mismatches[:10], f"{len(mismatches)} priority mismatches"


def _profile_order(search: dict) -> dict[str, int]:
    keys = search["profile_order"]
    return {key: index for index, key in enumerate(keys)}


def test_profile_leaders_reproduce(hub: dict, search: dict) -> None:
    order = _profile_order(search)
    priority = search["priority"]
    min_coverage = float(search["archetype_min_coverage"])
    for definition in hub["archetypes"]:
        profile_id = definition["id"]
        candidates = []
        for row in search["players"]:
            entry = _profile_entry(row, profile_id, order)
            if entry is None or entry[1] is None:
                continue
            if entry[3] is not None and float(entry[3]) < min_coverage:
                continue
            rank = (
                float(entry[1]) * _age_multiplier(row, priority) * _europe_multiplier(row, priority)
            )
            candidates.append((rank, float(entry[1]), int(row.get("m") or 0), row))
        candidates.sort(key=lambda item: (-item[0], -item[1], -item[2]))
        expected = [
            (int(item[3]["i"]), str(item[3]["l"]))
            for item in candidates[: len(definition["leaders"])]
        ]
        actual = [
            (int(leader["player_id"]), str(leader["league_slug"]))
            for leader in definition["leaders"]
        ]
        assert actual == expected, f"{profile_id} leaders drifted"


def test_attacker_leaders_reproduce(hub: dict, search: dict) -> None:
    priority = search["priority"]
    profile_keys = list(search["profile_order"])
    candidates = []
    for row in search["players"]:
        if row.get("rf") not in ATTACK_FAMILIES:
            continue
        scores = _profile_scores(row, profile_keys)
        if "assist_creator" not in scores or "goal_scorer" not in scores:
            continue
        bias = scores["assist_creator"] - scores["goal_scorer"]
        candidates.append((bias, row))
    for key, profile_id, reverse in (
        ("assist_bias", "assist_creator", True),
        ("goal_bias", "goal_scorer", False),
    ):
        group = [(bias, row) for bias, row in candidates if (bias > 0 if reverse else bias < 0)]
        group.sort(
            key=lambda item: (
                -(
                    _profile_scores(item[1], profile_keys)[profile_id]
                    * _age_multiplier(item[1], priority)
                    * _europe_multiplier(item[1], priority)
                ),
                -(item[0] if reverse else -item[0]),
                -(_priority(item[1], search) or 0),
            )
        )
        expected = [
            (int(row["i"]), str(row["l"]))
            for _, row in group[: len(hub["attackers"][key]["leaders"])]
        ]
        actual = [
            (int(leader["player_id"]), str(leader["league_slug"]))
            for leader in hub["attackers"][key]["leaders"]
        ]
        assert actual == expected, f"{key} leaders drifted"


def test_goal_scoring_reproduces(hub: dict, search: dict) -> None:
    rows = [
        row
        for row in search["players"]
        if row.get("rf") in ATTACK_FAMILIES and row.get("g90") is not None
    ]
    rows.sort(
        key=lambda row: (
            -float(row.get("g90") or 0),
            -float(row.get("ga") or 0),
            -int(row.get("m") or 0),
        )
    )
    expected = [
        (int(row["i"]), str(row["l"])) for row in rows[: len(hub["attackers"]["goal_scoring"])]
    ]
    actual = [
        (int(row["player_id"]), str(row["league_slug"])) for row in hub["attackers"]["goal_scoring"]
    ]
    assert actual == expected


def test_team_lens_reproduces(hub: dict, search: dict) -> None:
    threshold = float(search["team_context"]["underperforming_ppg_percentile_max"])
    min_lift = float(search["team_context"]["min_lift"])
    rows = [
        row
        for row in search["players"]
        if row.get("tpc") is not None
        and float(row["tpc"]) <= threshold
        and row.get("tl") is not None
        and float(row["tl"]) > min_lift
    ]
    rows.sort(
        key=lambda row: (
            -float(row.get("tl") or 0),
            -(_priority(row, search) or 0),
            -int(row.get("m") or 0),
        )
    )
    expected = [(int(row["i"]), str(row["l"])) for row in rows[: len(hub["team_lens"]["leaders"])]]
    actual = [
        (int(row["player_id"]), str(row["league_slug"])) for row in hub["team_lens"]["leaders"]
    ]
    assert actual == expected
