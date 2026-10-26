from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import polars as pl
import pytest

from fitba.metrics.registry import MetricRegistry
from fitba.publish.semantic import (
    build_changelog,
    build_definitions,
    build_entities,
    build_page_meta,
)

SQUAD = {
    "players": [
        {"player_key": "api:player:1", "player_id": 1, "name": "Squad One"},
    ],
    "excluded_players": [],
}

FORMER = {
    "players": [
        {"player_key": "api:player:2", "player_id": 2, "name": "Former Profiled"},
        {"player_key": "curated:player:no-id", "name": "Former Register Only"},
    ]
}

SCOUTING = {
    "pools": {
        "sco-premiership": {
            "players": [
                {"player_id": 3, "full_name": "Scouted Three"},
                {"player_id": 1, "full_name": "Squad One"},
            ]
        }
    },
    "search": {
        "players": [
            {"i": 3, "n": "S Three", "l": "SCO", "rf": "CB"},
            {"i": 1, "n": "Squad One", "l": "SCO", "rf": "ST"},
        ]
    },
}

FIXTURES = {
    "fixtures": [
        {
            "fixture_id": 10,
            "home_team_name": "Aberdeen",
            "away_team_name": "Celtic",
            "home_goals": 2,
            "away_goals": 1,
        }
    ]
}

HISTORY = {
    "seasons": [{"season": "2025-26"}],
    "staff": [{"person_id": "jimmy-thelin", "name": "Jimmy Thelin"}],
}

CASE = {"claims": [{"id": "team-now", "title": "The team now"}]}

TABLES = {"sco:premiership": pl.DataFrame([{"team_id": "sco:181", "team_name": "Aberdeen"}])}

PAGES = {
    "pages": [
        {"id": "scotland", "patterns": ["/scotland/"], "layers": ["league_standings"]}
    ],
    "static_pages": [{"id": "home", "name": "Home", "path": "/"}],
}


def _build_entities() -> tuple[dict, dict]:
    return build_entities(
        squad=SQUAD,
        former=FORMER,
        scouting_bundle=SCOUTING,
        fixture_index=FIXTURES,
        history_index=HISTORY,
        case_payload=CASE,
        tables=TABLES,
        pages_config=PAGES,
    )


def _by_id(entities: list[dict]) -> dict[str, dict]:
    return {row["entity_id"]: row for row in entities}


def test_core_entities_cover_every_published_type() -> None:
    entities, _ = _build_entities()
    rows = _by_id(entities["entities"])
    assert rows["page:home"]["href"] == "/"
    assert rows["club:sco:181"]["href"] == "/scotland/premiership/#club-181"
    assert rows["player:api:player:1"]["href"] == "/players/1/"
    assert rows["player:api:player:2"]["href"] == "/scouting/player/2/"
    assert rows["player:curated:player:no-id"]["href"] == (
        "/former-players/#former-curated-player-no-id"
    )
    assert rows["fixture:10"]["name"] == "Aberdeen 2-1 Celtic"
    assert rows["fixture:10"]["href"] == "/matches/10/"
    assert rows["season:2025-26"]["href"] == "/history/2025-26/"
    assert rows["staff:jimmy-thelin"]["href"] == "/history/#staff-jimmy-thelin"
    assert rows["claim:team-now"]["href"] == "/claims/#claim-team-now"


def test_former_href_kind_distinguishes_profile_from_register() -> None:
    entities, _ = _build_entities()
    rows = _by_id(entities["entities"])
    assert rows["player:api:player:2"]["href_kind"] == "profile"
    assert rows["player:curated:player:no-id"]["href_kind"] == "register"
    assert rows["player:curated:player:no-id"]["routes"]["former"].startswith(
        "/former-players/#"
    )


def test_scouted_group_is_disjoint_from_core_and_compact() -> None:
    entities, scouted = _build_entities()
    core_ids = set(_by_id(entities["entities"]))
    scouted_ids = {f"player:api:player:{row['i']}" for row in scouted["entities"]}
    assert core_ids.isdisjoint(scouted_ids)
    # A current squad player in the pool stays in the core index only.
    assert scouted_ids == {"player:api:player:3"}
    assert set(scouted["entities"][0]) == {"i", "n", "a", "h", "l", "rf"}
    assert scouted["entities"][0]["h"] == "/scouting/player/3/"


def test_page_meta_references_only_known_layers_and_metrics() -> None:
    metric = SimpleNamespace(
        id="league.table",
        label="Table",
        description="x",
        formula="x",
        unit="count",
        basis="measured",
        coverage_tier="published",
        source_layer="league_standings",
        limitations=[],
        status="active",
        home_surface="/scotland/",
        displayed_surfaces=["/scotland/"],
        payload_paths=[],
    )
    registry = cast(
        MetricRegistry,
        SimpleNamespace(registry_version="3.9.1", metrics=[metric]),
    )
    meta = build_page_meta(
        registry=registry,
        registry_checksum="sha256:0",
        generated_at="2026-10-26T00:00:00Z",
        dataset_version="2026-10-26",
        update_id="u",
        source_snapshots={},
        pages_config=PAGES,
    )
    surface = meta["surfaces"]["scotland"]
    assert surface["route_patterns"] == ["/scotland/"]
    assert surface["layers"] == ["league_standings"]
    assert surface["metrics"] == ["league.table"]
    assert meta["registry_version"] == "3.9.1"


def _metric(metric_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=metric_id,
        label=metric_id,
        description="Registered definition.",
        formula="x",
        unit="count",
        basis="measured",
        coverage_tier="published",
        source_layer="league_standings",
        limitations=["A limit."],
        status="active",
    )


def _fake_registry() -> MetricRegistry:
    return cast(
        MetricRegistry,
        SimpleNamespace(registry_version="3.9.1", metrics=[_metric("league.table")]),
    )


def test_definitions_copy_registry_fields_and_load_curated_terms() -> None:
    registry = _fake_registry()
    document = build_definitions(
        registry=registry,
        registry_checksum="sha256:0",
        definitions_config={
            "reviewed": "2026-10-26",
            "owner": "owner",
            "terms": [
                {
                    "id": "basis",
                    "term": "Basis",
                    "short": "How the value is measured.",
                    "body": "Measured or derived.",
                    "metric_ids": ["league.table"],
                }
            ],
        },
    )
    entries = {row["id"]: row for row in document["entries"]}
    assert entries["metric.league.table"]["formula"] == "x"
    assert entries["metric.league.table"]["provenance"] == "registry"
    assert entries["def.basis"]["provenance"] == "curated_overlay"
    assert entries["def.basis"]["formula"] is None
    assert entries["def.basis"]["metric_ids"] == ["league.table"]


def test_related_ids_resolve_to_generated_entries() -> None:
    registry = _fake_registry()
    document = build_definitions(
        registry=registry,
        registry_checksum="sha256:0",
        definitions_config={
            "terms": [
                {
                    "id": "basis",
                    "term": "Basis",
                    "metric_ids": ["league.table"],
                    "related": ["coverage_tier", "league.table"],
                },
                {"id": "coverage_tier", "term": "Coverage tier", "metric_ids": []},
            ]
        },
    )
    entries = {row["id"]: row for row in document["entries"]}
    assert entries["def.basis"]["related"] == [
        "def.coverage_tier",
        "metric.league.table",
    ]


def test_related_rejects_unknown_and_self_reference() -> None:
    registry = _fake_registry()
    with pytest.raises(ValueError, match="unknown related id"):
        build_definitions(
            registry=registry,
            registry_checksum="sha256:0",
            definitions_config={
                "terms": [{"id": "basis", "term": "Basis", "related": ["nope"]}]
            },
        )
    with pytest.raises(ValueError, match="related points at itself"):
        build_definitions(
            registry=registry,
            registry_checksum="sha256:0",
            definitions_config={
                "terms": [{"id": "basis", "term": "Basis", "related": ["basis"]}]
            },
        )


def test_a_curated_definition_may_not_name_an_unknown_metric() -> None:
    registry = _fake_registry()
    with pytest.raises(ValueError, match="unknown metric ids"):
        build_definitions(
            registry=registry,
            registry_checksum="sha256:0",
            definitions_config={
                "terms": [{"id": "bad", "term": "Bad", "metric_ids": ["made.up"]}]
            },
        )


def test_changelog_is_sorted_newest_first_and_append_only() -> None:
    document = build_changelog(
        changelog_config={
            "last_reviewed": "2026-10-26",
            "contact_url": "https://example.invalid/",
            "note": " note ",
            "append_only": True,
            "entries": [
                {"id": "older", "date": "2026-10-01", "title": "Older"},
                {"id": "newer-b", "date": "2026-10-20", "title": "Newer B"},
                {"id": "newer-a", "date": "2026-10-20", "title": "Newer A"},
            ],
        }
    )
    assert [row["id"] for row in document["entries"]] == [
        "newer-a",
        "newer-b",
        "older",
    ]
    assert document["append_only"] is True
    assert document["note"] == "note"
