"""Medium and long-term themes for the matchday dashboard.

Themes are hypotheses with evidence. Current-season themes use the local
Aberdeen lineup, event and provider-stat frames; the mission theme uses the
published Cormack-era and transfer records. No network access, no individual
ratings as verdicts, and no invented availability or channel data.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from typing import Any

import polars as pl

from fitba.analytics.history import club_match_rows
from fitba.analytics.matchday import form_block
from fitba.settings import themes as themes_config

TEAM_ID = 252
SEASON_YEAR = 2026
FAMILY_GROUPS = ("GK", "CB", "FB/WB", "MID", "AM/WM", "W", "ST")
BENCH_SCOPE = "Premiership only"
RATING_SCOPE = "Premiership starters"


def _rows(frame: pl.DataFrame | Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if frame is None:
        return []
    if isinstance(frame, pl.DataFrame):
        return frame.to_dicts() if frame.height else []
    return [dict(row) for row in frame]


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean(values: Iterable[float]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return round(sum(clean) / len(clean), 2) if clean else None


def _median(values: Iterable[float]) -> float | None:
    clean = sorted(float(value) for value in values if value is not None)
    if not clean:
        return None
    middle = len(clean) // 2
    return (
        round(clean[middle], 2)
        if len(clean) % 2
        else round((clean[middle - 1] + clean[middle]) / 2, 2)
    )


def _percentile(values: Iterable[float], share: float) -> float | None:
    clean = sorted(float(value) for value in values if value is not None)
    if not clean:
        return None
    index = max(0, min(len(clean) - 1, round((len(clean) - 1) * share)))
    return round(clean[index], 2)


def _ratio(numerator: float | None, denominator: int | float | None) -> float | None:
    if numerator is None or not denominator:
        return None
    return round(float(numerator) / float(denominator), 2)


def _pct(value: float | None, digits: int = 0) -> str | None:
    return f"{value * 100:.{digits}f}%" if value is not None else None


def _confidence(
    *,
    minutes: int,
    matches: int,
    high_minutes: int,
    high_matches: int,
    medium_minutes: int,
    medium_matches: int,
) -> str:
    if minutes >= high_minutes and matches >= high_matches:
        return "high"
    if minutes >= medium_minutes and matches >= medium_matches:
        return "medium"
    return "low"


def _primary_family(player: dict[str, Any]) -> str | None:
    for key in ("display_role", "role"):
        family = (player.get(key) or {}).get("family")
        if family and family != "unknown":
            return str(family)
    career = (player.get("career_role") or {}).get("dominant") or {}
    family = career.get("family")
    if family and family != "unknown":
        return str(family)
    return None


def _squad_lookup(
    squad_data: dict[str, Any] | None,
    *,
    config: dict[str, Any],
) -> dict[int, dict[str, Any]]:
    duplicates = {
        int(key): int(value)
        for key, value in ((config.get("identity") or {}).get("duplicate_player_ids") or {}).items()
    }
    lookup: dict[int, dict[str, Any]] = {}
    for player in (squad_data or {}).get("players", []):
        player_id = _int(player.get("player_id"))
        if player_id is None:
            continue
        lookup[player_id] = {
            "player_id": player_id,
            "player_key": player.get("player_key"),
            "name": player.get("name") or player.get("full_name") or f"Player {player_id}",
            "primary_family": _primary_family(player),
            "position_group": player.get("position_group"),
            "status": player.get("status"),
            "injured": bool(player.get("injured")),
            "number": player.get("number"),
            "duplicates": duplicates,
        }
    for duplicate, canonical in duplicates.items():
        if canonical in lookup:
            lookup[duplicate] = {**lookup[canonical], "player_id": canonical}
    return lookup


def _canonical_id(
    player_id: int | None,
    lookup: dict[int, dict[str, Any]],
    duplicates: dict[int, int],
) -> int | None:
    if player_id is None:
        return None
    if player_id in lookup and player_id not in duplicates:
        return player_id
    return duplicates.get(player_id, player_id)


def _family_map(config: dict[str, Any]) -> dict[str, str]:
    output: dict[str, str] = {}
    for group, families in (config.get("family_groups") or {}).items():
        for family in families or []:
            output[str(family)] = str(group)
    return output


def _team_frames(
    appearances: pl.DataFrame | Iterable[dict[str, Any]],
    match_stats: pl.DataFrame | Iterable[dict[str, Any]],
    team_shapes: pl.DataFrame | Iterable[dict[str, Any]] | None,
    *,
    season_year: int = SEASON_YEAR,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    apps = [
        row
        for row in _rows(appearances)
        if _int(row.get("team_id")) == TEAM_ID and _int(row.get("season")) == season_year
    ]
    stats = [
        row
        for row in _rows(match_stats)
        if _int(row.get("team_id")) == TEAM_ID and _int(row.get("season")) == season_year
    ]
    shapes = [
        row
        for row in _rows(team_shapes)
        if _int(row.get("team_id")) == TEAM_ID and _int(row.get("season")) == season_year
    ]
    return apps, stats, shapes


def _rating_maps(
    stats: list[dict[str, Any]],
    *,
    lookup: dict[int, dict[str, Any]],
    duplicates: dict[int, int],
) -> tuple[dict[tuple[int, int], float], dict[tuple[int, int], int], dict[tuple[int, int], int]]:
    ratings: dict[tuple[int, int], float] = {}
    goals: dict[tuple[int, int], int] = {}
    assists: dict[tuple[int, int], int] = {}
    for row in stats:
        fixture_id = _int(row.get("fixture_id"))
        player_id = _canonical_id(_int(row.get("player_id")), lookup, duplicates)
        if fixture_id is None or player_id is None:
            continue
        key = (fixture_id, player_id)
        rating = _float(row.get("rating"))
        if rating is not None:
            ratings[key] = rating
        goals[key] = max(goals.get(key, 0), int(row.get("goals") or 0))
        assists[key] = max(assists.get(key, 0), int(row.get("assists") or 0))
    return ratings, goals, assists


def _squad_mean_rating(
    apps: list[dict[str, Any]],
    *,
    ratings: dict[tuple[int, int], float],
    family_map: dict[str, str],
) -> tuple[float | None, int, int]:
    weighted = 0.0
    minutes = 0
    matches = 0
    for row in apps:
        if not row.get("started") or not family_map.get(str(row.get("role_family"))):
            continue
        rating = ratings.get((int(row["fixture_id"]), int(row["player_id"])))
        if rating is None:
            continue
        row_minutes = int(row.get("minutes") or 0)
        weighted += rating * row_minutes
        minutes += row_minutes
        matches += 1
    return (round(weighted / minutes, 2) if minutes else None), minutes, matches


def family_balance(
    appearances: pl.DataFrame | Iterable[dict[str, Any]],
    match_stats: pl.DataFrame | Iterable[dict[str, Any]],
    squad_data: dict[str, Any] | None,
    *,
    config: dict[str, Any] | None = None,
    season_year: int = SEASON_YEAR,
) -> dict[str, Any]:
    """Minutes-weighted provider ratings and output by role family."""
    config = config or themes_config()
    thresholds = (config.get("thresholds") or {}).get("family") or {}
    family_map = _family_map(config)
    lookup = _squad_lookup(squad_data, config=config)
    duplicates = {
        int(key): int(value)
        for key, value in ((config.get("identity") or {}).get("duplicate_player_ids") or {}).items()
    }
    apps, stats, _ = _team_frames(appearances, match_stats, None, season_year=season_year)
    ratings, goal_map, assist_map = _rating_maps(stats, lookup=lookup, duplicates=duplicates)
    squad_mean, _, _ = _squad_mean_rating(apps, ratings=ratings, family_map=family_map)
    fixtures_total = len({int(row["fixture_id"]) for row in apps})
    fixtures_with_ratings = len(
        {int(row["fixture_id"]) for row in stats if _float(row.get("rating")) is not None}
    )
    starts_total = sum(1 for row in apps if row.get("started"))
    starts_with_role = sum(
        1 for row in apps if row.get("started") and family_map.get(str(row.get("role_family")))
    )
    minutes_total = sum(int(row.get("minutes") or 0) for row in apps)
    sub_minutes = sum(int(row.get("minutes_as_sub") or 0) for row in apps)
    provider_rating_rows = len(ratings)
    provider_rating_minutes = sum(
        int(row.get("minutes") or 0)
        for row in apps
        if row.get("started") and (int(row["fixture_id"]), int(row["player_id"])) in ratings
    )

    buckets: dict[str, dict[str, Any]] = {
        group: {
            "family": group,
            "starts": 0,
            "starter_minutes": 0,
            "players": set(),
            "matches": set(),
            "rating_values": [],
            "rating_minutes": 0,
            "rating_weighted": 0.0,
            "goals": 0,
            "assists": 0,
        }
        for group in FAMILY_GROUPS
    }
    for row in apps:
        group = family_map.get(str(row.get("role_family")))
        if not group or not row.get("started"):
            continue
        bucket = buckets[group]
        row_minutes = int(row.get("minutes") or 0)
        bucket["starts"] += 1
        bucket["starter_minutes"] += row_minutes
        bucket["players"].add(int(row["player_id"]))
        bucket["matches"].add(int(row["fixture_id"]))
        rating = ratings.get((int(row["fixture_id"]), int(row["player_id"])))
        if rating is not None:
            bucket["rating_values"].append(rating)
            bucket["rating_minutes"] += row_minutes
            bucket["rating_weighted"] += rating * row_minutes

    # Goals and assists use the player's primary family so substitutes count.
    for (_fixture_id, player_id), goals in goal_map.items():
        player = lookup.get(player_id) or {}
        group = family_map.get(str(player.get("primary_family")))
        if not group:
            continue
        buckets[group]["goals"] += goals
    for (_fixture_id, player_id), assists in assist_map.items():
        player = lookup.get(player_id) or {}
        group = family_map.get(str(player.get("primary_family")))
        if not group:
            continue
        buckets[group]["assists"] += assists

    rows = []
    for group in FAMILY_GROUPS:
        bucket = buckets[group]
        provider_rating = (
            round(bucket["rating_weighted"] / bucket["rating_minutes"], 2)
            if bucket["rating_minutes"]
            else None
        )
        rows.append(
            {
                "family": group,
                "starts": bucket["starts"],
                "starter_minutes": bucket["starter_minutes"],
                "players": len(bucket["players"]),
                "matches": len(bucket["matches"]),
                "provider_rating": provider_rating,
                "rating_median": _median(bucket["rating_values"]),
                "rating_p25": _percentile(bucket["rating_values"], 0.25),
                "rating_sample": {
                    "player_matches": len(bucket["rating_values"]),
                    "players": len(bucket["players"]),
                    "minutes": bucket["rating_minutes"],
                },
                "squad_rating_delta": (
                    round(provider_rating - squad_mean, 2)
                    if provider_rating is not None and squad_mean is not None
                    else None
                ),
                "goals": bucket["goals"],
                "assists": bucket["assists"],
                "confidence": _confidence(
                    minutes=bucket["rating_minutes"],
                    matches=len(bucket["matches"]),
                    high_minutes=int(thresholds.get("high_minutes") or 900),
                    high_matches=int(thresholds.get("high_matches") or 6),
                    medium_minutes=int(thresholds.get("medium_minutes") or 450),
                    medium_matches=int(thresholds.get("medium_matches") or 3),
                ),
            }
        )
    rated = [row for row in rows if row["provider_rating"] is not None]
    rated.sort(key=lambda row: float(row["provider_rating"]))
    weakest = rated[0] if rated else None
    strongest = rated[-1] if rated else None
    cb = next((row for row in rows if row["family"] == "CB"), None)
    cb_delta = cb.get("squad_rating_delta") if cb else None
    if cb and cb_delta is not None and cb_delta < -0.10:
        cb_read = (
            f"The CB family mean is {cb['provider_rating']:.2f}, "
            f"{abs(cb_delta):.2f} below the squad mean; the weak-family read is "
            "supported, but the spread still matters."
        )
    elif cb and cb_delta is not None:
        cb_read = (
            f"The CB family mean is {cb['provider_rating']:.2f}, "
            f"{cb_delta:+.2f} against the squad mean. The data does not show a "
            "weak CB family overall; it shows dispersion and a shape effect."
        )
    else:
        cb_read = "The CB rating sample is too small for a family read."
    read = (
        f"Provider ratings put {strongest['family'] if strongest else 'no family'} "
        f"at the top ({strongest['provider_rating'] if strongest else '—'}) and "
        f"{weakest['family'] if weakest else 'no family'} at the bottom "
        f"({weakest['provider_rating'] if weakest else '—'}). {cb_read} "
        "Ratings are provider match ratings, not a fitba rating and not "
        "position-adjusted."
    )
    evidence = [
        {
            "label": "Squad provider mean",
            "value": squad_mean,
            "note": "minutes-weighted starters, Premiership",
            "basis": "measured",
        },
        {
            "label": "Weakest family",
            "value": weakest["family"] if weakest else None,
            "note": f"{weakest['provider_rating']:.2f}" if weakest else "no sample",
            "basis": "measured",
        },
        {
            "label": "CB mean",
            "value": cb.get("provider_rating") if cb else None,
            "note": f"{cb_delta:+.2f} vs squad" if cb_delta is not None else "no sample",
            "basis": "measured",
        },
        {
            "label": "CB spread",
            "value": cb.get("rating_p25") if cb else None,
            "note": "25th-percentile match rating",
            "basis": "measured",
        },
    ]
    status = (
        "available"
        if apps and stats and starts_with_role and provider_rating_rows
        else "partial"
        if apps
        else "unavailable"
    )
    reason = None
    if status == "unavailable":
        reason = "no_current_season_appearances"
    elif not stats or not provider_rating_rows:
        reason = "no_provider_ratings"
    return {
        "status": status,
        "reason": reason,
        "headline": (
            f"{weakest['family']} and "
            f"{rated[1]['family'] if len(rated) > 1 else '—'} rate lowest; "
            "the CB mean is not the weak spot."
            if weakest
            else "No family rating sample is available."
        ),
        "read": read,
        "basis": "measured",
        "read_basis": "inferred",
        "confidence": ("medium" if len(rated) >= 5 else "low"),
        "evidence": evidence,
        "players": [],
        "metrics": {
            "scope": {
                "ratings": RATING_SCOPE,
                "minutes": "all competitive fixtures",
                "note": (
                    "Provider ratings are Premiership-only and current-season. "
                    "They are not position-adjusted; cross-family comparison is "
                    "descriptive."
                ),
            },
            "coverage": {
                "fixtures_total": fixtures_total,
                "fixtures_with_ratings": fixtures_with_ratings,
                "starts_total": starts_total,
                "starts_with_role": starts_with_role,
                "role_start_coverage": (
                    round(starts_with_role / starts_total, 3) if starts_total else None
                ),
                "minutes_total": minutes_total,
                "sub_minutes": sub_minutes,
                "provider_rating_rows": provider_rating_rows,
                "provider_rating_minutes": provider_rating_minutes,
            },
            "squad_provider_rating": squad_mean,
            "groups": rows,
        },
        "caveats": [
            "Provider ratings are not position-adjusted and are not a fitba rating.",
            "The rating sample is Premiership-only; starts and minutes include cup fixtures.",
            "A family mean can hide a high-variance unit; the 25th percentile and spread matter.",
            "The squad-page position-group rating is an equal-weighted season aggregate "
            "and mixes full-backs with centre-backs; this layer uses per-match starters.",
        ],
        "method": (
            "Minutes-weighted mean of provider match ratings for starters with an "
            "observed role. Goals and assists use the player's primary family so "
            "substitutes count."
        ),
    }


def _shape_group(row: dict[str, Any]) -> str:
    family = str(row.get("shape_family") or "")
    cb_count = _int(row.get("cb_count"))
    if family in {"back_three", "back_five"} or cb_count == 3:
        return "three_cb"
    if family == "back_four" or cb_count == 2:
        return "two_cb"
    return "unknown"


def shape_tradeoff(
    team_shapes: pl.DataFrame | Iterable[dict[str, Any]],
    appearances: pl.DataFrame | Iterable[dict[str, Any]],
    match_stats: pl.DataFrame | Iterable[dict[str, Any]],
    squad_data: dict[str, Any] | None,
    *,
    config: dict[str, Any] | None = None,
    season_year: int = SEASON_YEAR,
) -> dict[str, Any]:
    """Back-four vs three-centre-back splits and the wing-back/wide trade-off."""
    config = config or themes_config()
    family_map = _family_map(config)
    lookup = _squad_lookup(squad_data, config=config)
    duplicates = {
        int(key): int(value)
        for key, value in ((config.get("identity") or {}).get("duplicate_player_ids") or {}).items()
    }
    apps, stats, shapes = _team_frames(
        appearances, match_stats, team_shapes, season_year=season_year
    )
    ratings, _, _ = _rating_maps(stats, lookup=lookup, duplicates=duplicates)
    by_fixture: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in apps:
        if row.get("started"):
            by_fixture[int(row["fixture_id"])].append(row)
    bench_by_fixture: dict[int, list[int]] = defaultdict(list)
    sub_minutes_by_fixture: dict[int, int] = defaultdict(int)
    for row in stats:
        if not row.get("substitute"):
            continue
        fixture_id = _int(row.get("fixture_id"))
        player_id = _canonical_id(_int(row.get("player_id")), lookup, duplicates)
        if fixture_id is None or player_id is None:
            continue
        if row.get("minutes") is None:
            bench_by_fixture[fixture_id].append(player_id)
        elif int(row.get("minutes") or 0) > 0:
            player = lookup.get(player_id) or {}
            if family_map.get(str(player.get("primary_family"))) == "W":
                sub_minutes_by_fixture[fixture_id] += int(row["minutes"])

    groups: dict[str, dict[str, Any]] = {}
    players: dict[int, dict[str, Any]] = {}
    for row in shapes:
        group = _shape_group(row)
        bucket = groups.setdefault(
            group,
            {
                "group": group,
                "matches": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
                "points": 0,
                "saves": [],
                "cb_ratings": [],
                "wb_starts": 0,
                "wf_starts": 0,
                "fb_starts": 0,
                "named_bench_wf": 0,
                "named_bench_fbwb": 0,
                "wf_sub_minutes": 0,
            },
        )
        fixture_id = int(row["fixture_id"])
        starts = by_fixture.get(fixture_id, [])
        bucket["matches"] += 1
        result = row.get("result")
        bucket["wins"] += 1 if result == "W" else 0
        bucket["draws"] += 1 if result == "D" else 0
        bucket["losses"] += 1 if result == "L" else 0
        bucket["goals_for"] += int(row.get("goals_for") or 0)
        bucket["goals_against"] += int(row.get("goals_against") or 0)
        bucket["points"] += 3 if result == "W" else 1 if result == "D" else 0
        if row.get("saves") is not None:
            bucket["saves"].append(int(row["saves"]))
        cb_values = []
        for appearance in starts:
            family = str(appearance.get("role_family"))
            if family == "wing_back":
                bucket["wb_starts"] += 1
            elif family == "wide_forward":
                bucket["wf_starts"] += 1
            elif family == "full_back":
                bucket["fb_starts"] += 1
            if family == "centre_back":
                rating = ratings.get((fixture_id, int(appearance["player_id"])))
                if rating is not None:
                    cb_values.append(rating)
            if family in {"wing_back", "wide_forward", "full_back"}:
                player = lookup.get(int(appearance["player_id"])) or {}
                if player:
                    item = players.setdefault(
                        int(appearance["player_id"]),
                        {
                            "player_id": int(appearance["player_id"]),
                            "name": player.get("name"),
                            "role_family": family,
                            "two_cb_starts": 0,
                            "three_cb_starts": 0,
                            "sub_minutes": 0,
                            "bench_named": 0,
                        },
                    )
                    key = "three_cb_starts" if group == "three_cb" else "two_cb_starts"
                    item[key] += 1
        if cb_values:
            bucket["cb_ratings"].append(_mean(cb_values))
        bench_ids = bench_by_fixture.get(fixture_id, [])
        for player_id in bench_ids:
            player = lookup.get(player_id) or {}
            family = family_map.get(str(player.get("primary_family")))
            if family == "W":
                bucket["named_bench_wf"] += 1
            elif family == "FB/WB":
                bucket["named_bench_fbwb"] += 1
        bucket["wf_sub_minutes"] += sub_minutes_by_fixture.get(fixture_id, 0)

    for player_id, item in players.items():
        player_stats = [
            row
            for row in stats
            if _canonical_id(_int(row.get("player_id")), lookup, duplicates) == player_id
        ]
        item["sub_minutes"] = sum(
            int(row.get("minutes") or 0)
            for row in player_stats
            if row.get("substitute") and row.get("minutes") is not None
        )
        item["bench_named"] = sum(
            1 for row in player_stats if row.get("substitute") and row.get("minutes") is None
        )

    rows = []
    for group in ("two_cb", "three_cb", "unknown"):
        bucket = groups.get(group)
        if not bucket:
            continue
        matches = bucket["matches"]
        rows.append(
            {
                "group": group,
                "matches": matches,
                "record": f"{bucket['wins']}-{bucket['draws']}-{bucket['losses']}",
                "points_pg": _ratio(bucket["points"], matches),
                "gf_pm": _ratio(bucket["goals_for"], matches),
                "ga_pm": _ratio(bucket["goals_against"], matches),
                "saves_pm": _mean(bucket["saves"]),
                "cb_rating": _mean(bucket["cb_ratings"]),
                "wb_starts_pm": _ratio(bucket["wb_starts"], matches),
                "wf_starts_pm": _ratio(bucket["wf_starts"], matches),
                "fb_starts_pm": _ratio(bucket["fb_starts"], matches),
                "named_bench_wf_pm": _ratio(bucket["named_bench_wf"], matches),
                "named_bench_fbwb_pm": _ratio(bucket["named_bench_fbwb"], matches),
                "wf_sub_minutes_pm": _ratio(bucket["wf_sub_minutes"], matches),
            }
        )
    two = next((row for row in rows if row["group"] == "two_cb"), None)
    three = next((row for row in rows if row["group"] == "three_cb"), None)
    if three and two:
        read = (
            f"There are {three['matches']} three-CB fixtures and {two['matches']} "
            f"two-CB fixtures. Wing-backs start {three['wb_starts_pm']:.1f} per "
            f"match in the three-CB set and {two['wb_starts_pm']:.1f} in the "
            f"two-CB set; wide forwards start {three['wf_starts_pm']:.1f} vs "
            f"{two['wf_starts_pm']:.1f}. Three-CB games concede "
            f"{three['ga_pm']:.2f} goals per match vs {two['ga_pm']:.2f}, with "
            f"{three['saves_pm'] or 0:.1f} vs {two['saves_pm'] or 0:.1f} saves "
            "per match where saves are available. This is an association in a "
            "small sample, not a causal claim."
        )
    else:
        read = "The shape split is unavailable or has no comparable groups."
    evidence = [
        {
            "label": "Three-CB fixtures",
            "value": three["matches"] if three else 0,
            "note": "kick-off shape only",
            "basis": "measured",
        },
        {
            "label": "Wing-back starts",
            "value": three["wb_starts_pm"] if three else None,
            "note": "per match in three-CB games",
            "basis": "measured",
        },
        {
            "label": "Wide-forward starts",
            "value": three["wf_starts_pm"] if three else None,
            "note": "per match in three-CB games",
            "basis": "measured",
        },
        {
            "label": "Goals against",
            "value": three["ga_pm"] if three else None,
            "note": "per match, three-CB vs two-CB",
            "basis": "measured",
        },
    ]
    player_rows = sorted(
        players.values(),
        key=lambda item: (
            -(item["three_cb_starts"] + item["two_cb_starts"]),
            -(item["sub_minutes"] + item["bench_named"]),
            item["name"] or "",
        ),
    )
    fixtures_total = len({int(row["fixture_id"]) for row in shapes})
    fixtures_with_shape = sum(1 for row in shapes if _shape_group(row) != "unknown")
    unknown_shapes = sum(1 for row in shapes if _shape_group(row) == "unknown")
    status = "available" if shapes and two and three else "partial" if shapes else "unavailable"
    reason = None
    if status == "unavailable":
        reason = "no_team_shapes"
    elif not three or not two:
        reason = "shape_groups_incomplete"
    return {
        "status": status,
        "reason": reason,
        "headline": (
            "Three at the back is a wing-back tax: the wide defenders start, the "
            "wide forwards do not."
            if three and three["wb_starts_pm"] and not three["wf_starts_pm"]
            else "The shape split is more mixed than the fan read."
        ),
        "read": read,
        "basis": "measured",
        "read_basis": "inferred",
        "confidence": ("low" if not three or three["matches"] < 5 else "medium"),
        "evidence": evidence,
        "players": player_rows,
        "metrics": {
            "scope": {
                "shapes": "all competitive fixtures; kick-off only",
                "ratings": "Premiership only",
                "bench": BENCH_SCOPE,
                "unknown_shapes": unknown_shapes,
            },
            "coverage": {
                "fixtures_total": fixtures_total,
                "fixtures_with_shape": fixtures_with_shape,
                "unknown_shapes": unknown_shapes,
                "bench_scope": BENCH_SCOPE,
            },
            "groups": rows,
        },
        "caveats": [
            "Kick-off shape only; mid-game switches are not inferred.",
            "The three-CB sample is small; association is not causation.",
            f"Named bench and substitute data are {BENCH_SCOPE.lower()}.",
            'No channel or cross data: the "doubling up in the channels" claim cannot be measured.',
        ],
        "method": (
            "Group fixtures by kick-off centre-back count, then count observed "
            "wing-back, full-back and wide-forward starters, named bench rows and "
            "substitute minutes."
        ),
    }


def cover_question(
    appearances: pl.DataFrame | Iterable[dict[str, Any]],
    match_stats: pl.DataFrame | Iterable[dict[str, Any]],
    squad_data: dict[str, Any] | None,
    transfers: Iterable[dict[str, Any]] | None,
    *,
    config: dict[str, Any] | None = None,
    season_year: int = SEASON_YEAR,
    curated_notes: list[dict[str, Any]] | None = None,
    availability: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Centre-back and full-back/wing-back depth, rotation and arrivals."""
    config = config or themes_config()
    thresholds = (config.get("thresholds") or {}).get("depth") or {}
    family_map = _family_map(config)
    lookup = _squad_lookup(squad_data, config=config)
    duplicates = {
        int(key): int(value)
        for key, value in ((config.get("identity") or {}).get("duplicate_player_ids") or {}).items()
    }
    apps, stats, _ = _team_frames(appearances, match_stats, None, season_year=season_year)
    starts: Counter[int] = Counter()
    minutes: Counter[int] = Counter()
    sub_apps: Counter[int] = Counter()
    bench: Counter[int] = Counter()
    for row in apps:
        player_id = _canonical_id(_int(row.get("player_id")), lookup, duplicates)
        if player_id is None:
            continue
        if row.get("started"):
            starts[player_id] += 1
        else:
            sub_apps[player_id] += 1
        minutes[player_id] += int(row.get("minutes") or 0)
    for row in stats:
        if row.get("substitute") and row.get("minutes") is None:
            player_id = _canonical_id(_int(row.get("player_id")), lookup, duplicates)
            if player_id is not None:
                bench[player_id] += 1
    arrivals = {
        str(item.get("player_key") or ""): item
        for item in (transfers or [])
        if item.get("direction") == "in" and str(item.get("season")) == str(config.get("season"))
    }
    groups: dict[str, list[dict[str, Any]]] = {"CB": [], "FB/WB": []}
    for player_id, player in lookup.items():
        if player.get("player_id") != player_id or player_id in duplicates:
            continue
        group = family_map.get(str(player.get("primary_family")))
        if group not in groups:
            continue
        player_starts = starts.get(player_id, 0)
        player_minutes = minutes.get(player_id, 0)
        status = str(player.get("status") or "")
        if status == "loan_out":
            continue
        availability_row = (availability or {}).get(player_id, {})
        availability_status = str(availability_row.get("status") or "unknown")
        injured = bool(player.get("injured"))
        if availability_status in {"out", "suspended"}:
            category = "unavailable"
        elif injured:
            category = "injured"
        elif player_starts >= int(thresholds.get("starter_starts") or 5) or player_minutes >= int(
            thresholds.get("starter_minutes") or 450
        ):
            category = "starter"
        elif player_starts >= 1 or player_minutes >= int(thresholds.get("rotation_minutes") or 90):
            category = "rotation"
        else:
            category = "fringe"
        arrival = arrivals.get(str(player.get("player_key") or ""))
        note = None
        for curated in curated_notes or []:
            if str(curated.get("player_id")) == str(player_id):
                note = curated.get("note")
        groups[group].append(
            {
                "player_id": player_id,
                "name": player.get("name"),
                "role_family": player.get("primary_family"),
                "starts": player_starts,
                "minutes": player_minutes,
                "sub_apps": sub_apps.get(player_id, 0),
                "bench_named": bench.get(player_id, 0),
                "category": category,
                "arrival": arrival.get("date_effective") if arrival else None,
                "arrival_kind": arrival.get("transfer_kind") if arrival else None,
                "note": note,
                "availability_status": availability_status,
                "availability_confidence": availability_row.get("confidence"),
                "availability_source": availability_row.get("source_id"),
                "availability_verified_at": availability_row.get("verified_at"),
                "availability_note": availability_row.get("note"),
                "availability_conflict": bool(availability_row.get("conflict")),
            }
        )
    rows = []
    for group, players in groups.items():
        players.sort(key=lambda item: (-item["minutes"], -item["starts"], item["name"] or ""))
        total_minutes = sum(item["minutes"] for item in players if item["category"] != "loan_out")
        top = max(
            (item["minutes"] for item in players if item["category"] != "loan_out"),
            default=0,
        )
        starter_count = sum(1 for item in players if item["category"] == "starter")
        rotation_count = sum(1 for item in players if item["category"] == "rotation")
        fringe_count = sum(1 for item in players if item["category"] == "fringe")
        three_start = sum(1 for item in players if item["starts"] >= 3)
        arrivals_here = [item for item in players if item["arrival"]]
        rows.append(
            {
                "group": group,
                "players": len(players),
                "total_minutes": total_minutes,
                "top_share": round(top / total_minutes, 2) if total_minutes else None,
                "concentration": (
                    "high"
                    if total_minutes
                    and top / total_minutes >= float(thresholds.get("concentration_high") or 0.55)
                    else "moderate"
                    if total_minutes
                    else "unknown"
                ),
                "starters": starter_count,
                "rotation": rotation_count,
                "fringe": fringe_count,
                "players_with_3_starts": three_start,
                "thin_rotation": three_start < int(thresholds.get("thin_rotation_starts") or 3),
                "named_bench": sum(item["bench_named"] for item in players),
                "arrivals": len(arrivals_here),
                "arrival_minutes": sum(item["minutes"] for item in arrivals_here),
                "items": players,
            }
        )
    by_group = {row["group"]: row for row in rows}
    cb = by_group.get("CB")
    fb = by_group.get("FB/WB")
    cb_top = _pct(cb["top_share"] if cb else None) or "—"
    read = (
        f"The CB group has {cb['starters'] if cb else 0} players at starter "
        f"minutes and {cb['players_with_3_starts'] if cb else 0} with at least "
        f"three starts; the top CB carries {cb_top} of the group minutes. "
        f"The FB/WB group has {fb['starters'] if fb else 0} players at starter "
        f"minutes and {fb['players_with_3_starts'] if fb else 0} with at least "
        "three starts. The minutes pattern is consistent with limited rotation; "
        "the data cannot distinguish selection from availability."
    )
    evidence = [
        {
            "label": "CB top share",
            "value": _pct(cb["top_share"] if cb else None),
            "note": "share of CB group minutes",
            "basis": "measured",
        },
        {
            "label": "FB/WB top share",
            "value": _pct(fb["top_share"] if fb else None),
            "note": "share of FB/WB group minutes",
            "basis": "measured",
        },
        {
            "label": "CB starters",
            "value": cb["starters"] if cb else None,
            "note": f"{cb['players_with_3_starts'] if cb else 0} with 3+ starts",
            "basis": "measured",
        },
        {
            "label": "Defensive arrivals",
            "value": (cb["arrivals"] if cb else 0) + (fb["arrivals"] if fb else 0),
            "note": "2026-27 arrivals in these groups",
            "basis": "measured",
        },
    ]
    bench_rows = sum(bench.values())
    bench_classified = sum(
        1
        for player_id, count in bench.items()
        for _ in range(count)
        if family_map.get(str((lookup.get(player_id) or {}).get("primary_family")))
        in {"CB", "FB/WB"}
    )
    availability_counts = Counter(
        str(item.get("availability_status") or "unknown")
        for group in groups.values()
        for item in group
    )
    status = "available" if cb or fb else "unavailable"
    reason = None if status == "available" else "no_defensive_squad_roles"
    return {
        "status": status,
        "reason": reason,
        "headline": (
            "The defensive minutes are concentrated at the top and thin behind "
            "it; the data cannot say whether that is selection or availability."
            if (cb and cb["thin_rotation"])
            or (fb and fb["thin_rotation"])
            or (cb and cb["concentration"] == "high")
            or (fb and fb["concentration"] == "high")
            else (
                "The defensive minutes are spread across a larger group than the fan read suggests."
            )
        ),
        "read": read,
        "basis": "measured",
        "read_basis": "inferred",
        "confidence": "medium",
        "evidence": evidence,
        "players": [
            item for group in ("CB", "FB/WB") for item in by_group.get(group, {}).get("items", [])
        ],
        "metrics": {
            "scope": {
                "minutes": "all competitive fixtures",
                "bench": BENCH_SCOPE,
                "availability": "curated team-news ledger; provider injuries optional",
            },
            "coverage": {
                "squad_players": sum(row["players"] for row in rows),
                "minutes_total": sum(row["total_minutes"] for row in rows),
                "bench_rows": bench_rows,
                "bench_classified": bench_classified,
                "bench_unknown": max(0, bench_rows - bench_classified),
                "transfers_available": bool(transfers),
                "availability": dict(availability_counts),
            },
            "groups": rows,
            "curated_notes": curated_notes or [],
        },
        "caveats": [
            "Minutes are not proof of trust; the data cannot distinguish "
            "selection from availability.",
            "Availability comes from the curated official team-news ledger; "
            "provider injury flags are not team news. Unknown stays unknown.",
            "Named bench rows are Premiership-only.",
        ],
        "method": (
            "Aggregate starts, minutes, substitute appearances and named bench "
            "rows by primary role family, then classify players as starter, "
            "rotation or fringe. Recent arrivals are identified from the transfer "
            "register."
        ),
    }


def leaky_boat(
    matches: pl.DataFrame,
    match_stats: pl.DataFrame | Iterable[dict[str, Any]],
    appearances: pl.DataFrame | Iterable[dict[str, Any]],
    squad_data: dict[str, Any] | None,
    *,
    season: str,
    config: dict[str, Any] | None = None,
    season_year: int = SEASON_YEAR,
) -> dict[str, Any]:
    """Attack output vs defensive concession, with goals by primary family."""
    config = config or themes_config()
    family_map = _family_map(config)
    lookup = _squad_lookup(squad_data, config=config)
    duplicates = {
        int(key): int(value)
        for key, value in ((config.get("identity") or {}).get("duplicate_player_ids") or {}).items()
    }
    _, stats, _ = _team_frames(appearances, match_stats, None, season_year=season_year)
    _, goal_map, _ = _rating_maps(stats, lookup=lookup, duplicates=duplicates)
    required = {"home_team_id", "away_team_id", "home_goals", "away_goals"}
    if matches is None or matches.height == 0 or not required <= set(matches.columns):
        rows = []
    else:
        rows = club_match_rows(matches, "sco:aberdeen").to_dicts()
    block = form_block(
        rows,
        n=5,
        competition_id="sco:premiership",
        competition_name="Premiership",
        season=season,
    )
    goals_by_family: Counter[str] = Counter()
    top_scorers: Counter[tuple[int, str]] = Counter()
    for (_fixture_id, player_id), goals in goal_map.items():
        player = lookup.get(player_id) or {}
        group = family_map.get(str(player.get("primary_family")))
        if not group or goals <= 0:
            continue
        goals_by_family[group] += goals
        top_scorers[(player_id, str(player.get("name") or "Unknown"))] += goals
    total_goals = sum(goals_by_family.values())
    attack_goals = goals_by_family.get("W", 0) + goals_by_family.get("ST", 0)
    defence_goals = goals_by_family.get("CB", 0) + goals_by_family.get("FB/WB", 0)
    midfield_goals = (
        goals_by_family.get("MID", 0)
        + goals_by_family.get("AM/WM", 0)
        + goals_by_family.get("GK", 0)
    )
    attack_share = round(attack_goals / total_goals, 3) if total_goals else None
    season_record = block["season_record"]
    recent = block["recent"]
    read = (
        f"The league season is {season_record['gf']}-{season_record['ga']} with "
        f"{season_record['points']} points. Forwards scored {attack_goals} of "
        f"{total_goals} goals ({attack_share:.0%})"
        if attack_share is not None
        else "The goals-by-family sample is unavailable."
    )
    read += (
        "; the data shows where the goals come from and what the team concedes. "
        'It does not prove the forwards are "bailing out" the defence, and '
        "there is no xG or shot-quality model here."
    )
    evidence = [
        {
            "label": "League goals",
            "value": f"{season_record['gf']}-{season_record['ga']}",
            "note": f"{season_record['points']} points",
            "basis": "measured",
        },
        {
            "label": "Attack share",
            "value": _pct(attack_share),
            "note": "share of league goals scored by W/ST",
            "basis": "measured",
        },
        {
            "label": "Last five",
            "value": f"{recent['gf']}-{recent['ga']}",
            "note": f"{recent['points']} points",
            "basis": "measured",
        },
        {
            "label": "Shot share",
            "value": season_record.get("shot_share"),
            "note": "shots for / (for + against)",
            "basis": "measured",
        },
    ]
    status = "available" if rows and stats else "partial" if rows else "unavailable"
    reason = None
    if status == "unavailable":
        reason = "no_league_matches"
    elif not stats:
        reason = "no_provider_goals"
    return {
        "status": status,
        "reason": reason,
        "headline": (
            "The attack is producing most of the goals; the defence is conceding "
            "enough to keep the balance fragile."
            if attack_share is not None and attack_share >= 0.55
            else "The goals are spread across the team rather than carried by one line."
        ),
        "read": read,
        "basis": "measured",
        "read_basis": "inferred",
        "confidence": "medium",
        "evidence": evidence,
        "players": [
            {
                "player_id": player_id,
                "name": name,
                "role_family": (lookup.get(player_id) or {}).get("primary_family"),
                "starts": None,
                "minutes": None,
                "sub_apps": None,
                "bench_named": None,
                "category": "scorer",
                "note": f"{goals} league goals",
            }
            for (player_id, name), goals in top_scorers.most_common(5)
        ],
        "metrics": {
            "scope": {"competition": "Premiership", "basis": "league only"},
            "coverage": {
                "league_matches": len(rows),
                "provider_stat_rows": len(stats),
            },
            "season": season_record,
            "last_five": recent,
            "goals_by_family": {
                "attack": attack_goals,
                "midfield": midfield_goals,
                "defence": defence_goals,
                "total": total_goals,
                "attack_share": attack_share,
            },
        },
        "caveats": [
            "No xG, shot quality or expected-goals model.",
            "Goals by family use the player's primary role, not the role in each match.",
            "A descriptive balance is not a causal explanation.",
        ],
        "method": (
            "League match rows for goals, shots and points; provider goals joined "
            "to the squad's primary role family."
        ),
    }


def mission_check(
    history_index: dict[str, Any] | None,
    history_season: dict[str, Any] | None,
    transfers: Iterable[dict[str, Any]] | None,
    *,
    season: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The 20% mission context: trading-club turnover and the sporting cost."""
    config = config or themes_config()
    index = history_index or {}
    season_doc = history_season or {}
    scorecard = index.get("scorecard") or {}
    recruitment = season_doc.get("recruitment") or {}
    selection = season_doc.get("selection") or {}
    era = index.get("era") or {}
    defensive_arrivals = [
        item
        for item in (transfers or [])
        if item.get("direction") == "in"
        and str(item.get("season")) == season
        and str(item.get("position") or "").casefold()
        in {
            "defender",
            "centre-back",
            "centre back",
            "full-back",
            "full back",
            "wing-back",
            "wing back",
        }
    ]
    status = (
        "available" if era and season_doc else "partial" if era or season_doc else "unavailable"
    )
    reason = None
    if status == "unavailable":
        reason = "no_history_payload"
    elif not season_doc:
        reason = "no_current_season_review"
    if status == "unavailable":
        read = "The mission context is unavailable because the history payload is missing."
    else:
        read = (
            f"The 2026-27 rebuild shows {recruitment.get('arrivals', 0)} arrivals and "
            f"{recruitment.get('departures', 0)} departures, a median arrival age of "
            f"{recruitment.get('median_age', '—')}, U21 minutes at "
            f"{_pct(selection.get('u21_minutes_share')) or '—'} and "
            f"{selection.get('players_used', '—')} players used. That is the trading "
            "model visible in the squad: high turnover, young minutes and a changing "
            "back line. The data can show the trade-off; it cannot decide whether the "
            "club's risk appetite is right."
        )
    pillars = [
        {
            "id": pillar.get("id"),
            "title": pillar.get("title"),
            "statement": pillar.get("statement"),
            "evidence": pillar.get("evidence") or [],
            "status": "available",
            "basis": "curated",
        }
        for pillar in (era.get("pillars") or [])
    ]
    evidence = [
        {
            "label": "Arrivals / departures",
            "value": f"{recruitment.get('arrivals', 0)} / {recruitment.get('departures', 0)}",
            "note": "2026-27",
            "basis": "measured",
        },
        {
            "label": "Median arrival age",
            "value": recruitment.get("median_age"),
            "note": "2026-27 arrivals",
            "basis": "measured",
        },
        {
            "label": "U21 minutes",
            "value": _pct(selection.get("u21_minutes_share")),
            "note": "share of minutes",
            "basis": "measured",
        },
        {
            "label": "Era league range",
            "value": (
                f"{scorecard.get('best_position', '—')}-{scorecard.get('worst_position', '—')}"
            ),
            "note": "Cormack era",
            "basis": "measured",
        },
    ]
    return {
        "status": status,
        "reason": reason,
        "headline": (
            "The model is visible in the turnover; the sporting cost is an unsettled back line."
            if recruitment.get("arrivals")
            else "The mission context is unavailable."
        ),
        "read": read,
        "basis": "mixed",
        "read_basis": "curated",
        "confidence": "medium" if status == "available" else "low",
        "evidence": evidence,
        "players": [],
        "metrics": {
            "scope": {"horizon": "Cormack era", "season": season},
            "coverage": {
                "history_index": bool(index),
                "current_season_review": bool(season_doc),
                "transfers": bool(transfers),
                "ratings_used": False,
            },
            "recruitment": recruitment,
            "selection": selection,
            "scorecard": scorecard,
            "pillars": pillars,
            "defensive_arrivals": [
                {
                    "player_name": item.get("player_name"),
                    "from_club_name": item.get("from_club_name"),
                    "date_effective": item.get("date_effective"),
                    "transfer_kind": item.get("transfer_kind"),
                }
                for item in defensive_arrivals
            ],
            "commercial_context": (config.get("mission") or {}).get("commercial_context"),
            "pillars_source": (config.get("mission") or {}).get("pillars_source"),
        },
        "caveats": [
            "The mission is the documented trading-club framing, not the club's internal model.",
            "Commercial and fanbase growth are context only; the public "
            "football data cannot measure them.",
            "High turnover is not a verdict on any individual decision.",
        ],
        "method": (
            "Join the published era scorecard, 2026-27 recruitment/selection "
            "aggregates and the transfer register. No historical ratings exist."
        ),
    }


def build_theme_document(
    *,
    appearances: pl.DataFrame | Iterable[dict[str, Any]],
    match_stats: pl.DataFrame | Iterable[dict[str, Any]],
    team_shapes: pl.DataFrame | Iterable[dict[str, Any]],
    matches: pl.DataFrame,
    squad_data: dict[str, Any] | None,
    transfers: Iterable[dict[str, Any]] | None,
    history_index: dict[str, Any] | None,
    history_season: dict[str, Any] | None,
    season: str,
    generated_at: str,
    config: dict[str, Any] | None = None,
    curated_notes: list[dict[str, Any]] | None = None,
    availability: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compose the five themes into a JSON-ready document."""
    config = config or themes_config()
    season_year = int(str(season).split("-", 1)[0]) if "-" in str(season) else SEASON_YEAR
    builders = {
        "family_balance": lambda: family_balance(
            appearances,
            match_stats,
            squad_data,
            config=config,
            season_year=season_year,
        ),
        "wing_back_tax": lambda: shape_tradeoff(
            team_shapes,
            appearances,
            match_stats,
            squad_data,
            config=config,
            season_year=season_year,
        ),
        "cover_question": lambda: cover_question(
            appearances,
            match_stats,
            squad_data,
            transfers,
            config=config,
            season_year=season_year,
            curated_notes=curated_notes,
            availability=availability,
        ),
        "leaky_boat": lambda: leaky_boat(
            matches,
            match_stats,
            appearances,
            squad_data,
            season=season,
            config=config,
            season_year=season_year,
        ),
        "mission_check": lambda: mission_check(
            history_index, history_season, transfers, season=season, config=config
        ),
    }
    links = {
        "family_balance": [
            {"label": "Squad", "href": "/squad/"},
            {"label": "Roles and shape", "href": "/methodology/"},
        ],
        "wing_back_tax": [
            {"label": "Squad", "href": "/squad/"},
            {"label": "Predicted XI", "href": "/matchday/"},
        ],
        "cover_question": [
            {"label": "Squad", "href": "/squad/"},
            {"label": "Transfers", "href": "/transfers/"},
            {"label": "Recruitment", "href": "/recruitment/"},
        ],
        "leaky_boat": [
            {"label": "Fixtures", "href": "/fixtures/"},
            {"label": "Squad", "href": "/squad/"},
        ],
        "mission_check": [
            {"label": "The Cormack era", "href": "/history/"},
            {"label": "Transfers", "href": "/transfers/"},
            {"label": "Recruitment", "href": "/recruitment/"},
        ],
    }
    themes = []
    for definition in sorted(
        config.get("themes") or [], key=lambda item: int(item.get("order") or 99)
    ):
        theme_id = str(definition.get("id"))
        builder = builders.get(theme_id)
        if builder is None:
            continue
        payload = builder()
        themes.append(
            {
                "theme_id": theme_id,
                "horizon": str(definition.get("horizon") or "season"),
                "order": int(definition.get("order") or 99),
                "fan_question": str(definition.get("fan_question") or ""),
                "title": str(definition.get("title") or theme_id),
                "status": payload.get("status") or "available",
                "reason": payload.get("reason"),
                "headline": payload.get("headline"),
                "read": payload.get("read"),
                "basis": payload.get("basis"),
                "read_basis": payload.get("read_basis"),
                "confidence": payload.get("confidence"),
                "evidence": payload.get("evidence") or [],
                "players": payload.get("players") or [],
                "metrics": payload.get("metrics") or {},
                "links": links.get(theme_id, []),
                "caveats": payload.get("caveats") or [],
                "method": payload.get("method"),
            }
        )
    statuses = [str(theme.get("status") or "available") for theme in themes]
    if not themes or all(status == "unavailable" for status in statuses):
        state = "unavailable"
    elif all(status == "available" for status in statuses):
        state = "fresh"
    else:
        state = "partial"
    family = next((theme for theme in themes if theme["theme_id"] == "family_balance"), None)
    family_coverage = ((family or {}).get("metrics") or {}).get("coverage") or {}
    availability_counts = Counter(
        str(entry.get("status") or "unknown") for entry in (availability or {}).values()
    )
    availability_known = sum(
        count for status, count in availability_counts.items() if status != "unknown"
    )
    return {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "season": season,
        "club_id": "sco:aberdeen",
        "state": state,
        "title": "The bigger picture",
        "scope": {
            "season": season,
            "season_weight": 80,
            "mission_weight": 20,
            "mission_label": "The Cormack-era mission",
            "note": (
                "80% current season; 20% the long-term trading-club mission. "
                "The split is editorial, not a statistical model."
            ),
        },
        "summary": {
            "headline": (
                "Four season themes and one mission context behind the next match."
                if state == "fresh"
                else "Some theme layers are unavailable."
            ),
            "theme_count": len(themes),
            "season_themes": sum(1 for theme in themes if theme["horizon"] == "season"),
            "mission_themes": sum(1 for theme in themes if theme["horizon"] == "mission"),
            "confidence": "medium" if state == "fresh" else "low",
            "note": (
                "Themes are hypotheses with evidence, not verdicts. Provider "
                "ratings are labelled and never an individual verdict."
            ),
        },
        "coverage": {
            "status": state,
            "season": season,
            "role_basis": (
                "observed starters for family ratings; primary squad role for "
                "bench and goals; observed starts for shape"
            ),
            "provider_ratings": RATING_SCOPE,
            "fixtures_total": family_coverage.get("fixtures_total"),
            "fixtures_with_ratings": family_coverage.get("fixtures_with_ratings"),
            "starts_total": family_coverage.get("starts_total"),
            "starts_with_role": family_coverage.get("starts_with_role"),
            "role_start_coverage": family_coverage.get("role_start_coverage"),
            "minutes_total": family_coverage.get("minutes_total"),
            "sub_minutes": family_coverage.get("sub_minutes"),
            "provider_rating_rows": family_coverage.get("provider_rating_rows"),
            "provider_rating_minutes": family_coverage.get("provider_rating_minutes"),
            "shapes": "kick-off only",
            "bench": BENCH_SCOPE,
            "availability_feed": {
                "status": "partial" if availability_known else "unavailable",
                "counts": dict(availability_counts),
                "known": availability_known,
                "unknown": availability_counts.get("unknown", 0),
            },
            "channel_data": False,
            "xg": False,
            "possession": False,
            "midgame_shape": False,
            "historical_ratings": False,
            "note": (
                "No xG, channel, possession or mid-game shape data. Provider "
                "ratings are current-season Premiership only. Availability is "
                "unknown; provider injured flags are not team news."
            ),
        },
        "themes": themes,
        "sources": [],
        "notes": (
            "The read is inferred/curated from measured evidence. It is not a "
            "result prediction, not betting advice, and not a claim about the "
            "manager's private intent."
        ),
    }


__all__ = [
    "build_theme_document",
    "cover_question",
    "family_balance",
    "leaky_boat",
    "mission_check",
    "shape_tradeoff",
]
