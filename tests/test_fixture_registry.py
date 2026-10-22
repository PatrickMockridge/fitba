from __future__ import annotations

import polars as pl
import pytest

from fitba.normalize.fixture_registry import (
    FixtureRecord,
    FixtureRegistry,
    FixtureRegistryError,
    build_fixture_registry,
)

POLICY = {
    "scope": {"first_season": "2025-26", "last_season": "2025-26"},
    "matching": {"date_tolerance_days": 0, "overrides": {}},
}


def _history() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "fixture_id": 1001,
                "season": "2025-26",
                "date": "2025-08-04T19:00:00+00:00",
                "status": "FT",
                "competition_id": "sco:premiership",
                "competition_name": "Premiership",
                "round": "Regular Season - 1",
                "home_team_name": "Aberdeen",
                "away_team_name": "St Mirren",
                "home_goals": 2,
                "away_goals": 1,
            },
            {
                "fixture_id": 1002,
                "season": "2025-26",
                "date": "2025-08-10T14:00:00+00:00",
                "status": "FT",
                "competition_id": "sco:league-cup",
                "competition_name": "League Cup",
                "round": "Group Stage",
                "home_team_name": "Dundee",
                "away_team_name": "Aberdeen",
                "home_goals": 0,
                "away_goals": 3,
            },
            {
                "fixture_id": 1003,
                "season": "2025-26",
                "date": "2025-08-17T14:00:00+00:00",
                "status": "NS",
                "competition_id": "sco:premiership",
                "competition_name": "Premiership",
                "round": "Regular Season - 3",
                "home_team_name": "Aberdeen",
                "away_team_name": "Dundee United",
                "home_goals": None,
                "away_goals": None,
            },
        ]
    )


def _matches(*rows: dict) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "match_id": "premiership-2025-26-2025-08-04-aberdeen-st-mirren",
                "date": "2025-08-04",
                "competition_id": "sco:premiership",
                "home_team_id": "sco:aberdeen",
                "away_team_id": "sco:st-mirren",
            },
            *rows,
        ]
    )


def test_registry_joins_league_alias_and_keeps_cup_separate() -> None:
    registry = build_fixture_registry(
        history_frames={"2025-26": _history()},
        match_rows=_matches(),
        policy=POLICY,
    )
    coverage = registry.coverage()

    assert coverage.total == 3
    assert coverage.played == 2
    assert coverage.competitive == 2
    assert coverage.friendlies == 0
    assert coverage.with_league_alias == 1

    league = registry.by_fixture_id[1001]
    assert league.match_id == "premiership-2025-26-2025-08-04-aberdeen-st-mirren"
    assert league.href == "/matches/1001/"
    assert league.source_ids["football_data_uk"] == league.match_id
    assert league.venue == "H"
    assert league.opponent_id == "sco:st-mirren"

    cup = registry.by_fixture_id[1002]
    assert cup.match_id is None
    assert cup.href == "/matches/1002/"
    assert cup.venue == "A"

    unplayed = registry.by_fixture_id[1003]
    assert unplayed.played is False
    assert unplayed.href is None


def test_registry_tolerates_date_offset_when_configured() -> None:
    policy = {**POLICY, "matching": {"date_tolerance_days": 1, "overrides": {}}}
    registry = build_fixture_registry(
        history_frames={"2025-26": _history()},
        match_rows=_matches(),
        policy=policy,
    )
    assert registry.by_fixture_id[1001].match_id is not None


def test_registry_rejects_ambiguous_alias() -> None:
    duplicate = _matches(
        {
            "match_id": "premiership-2025-26-2025-08-04-aberdeen-st-mirren-copy",
            "date": "2025-08-04",
            "competition_id": "sco:premiership",
            "home_team_id": "sco:aberdeen",
            "away_team_id": "sco:st-mirren",
        }
    )
    with pytest.raises(FixtureRegistryError, match="ambiguous"):
        build_fixture_registry(
            history_frames={"2025-26": _history()},
            match_rows=duplicate,
            policy=POLICY,
        )


def test_registry_override_selects_known_match() -> None:
    policy = {
        **POLICY,
        "matching": {
            "date_tolerance_days": 0,
            "overrides": {"api:fixture:1001": "manual-match"},
        },
    }
    matches = _matches(
        {
            "match_id": "manual-match",
            "date": "2025-08-05",
            "competition_id": "sco:premiership",
            "home_team_id": "sco:aberdeen",
            "away_team_id": "sco:st-mirren",
        }
    )
    registry = build_fixture_registry(
        history_frames={"2025-26": _history()},
        match_rows=matches,
        policy=policy,
    )
    assert registry.by_fixture_id[1001].match_id == "manual-match"


def test_registry_rejects_duplicate_fixture_id() -> None:
    fixture = FixtureRecord(
        key="api:fixture:1",
        fixture_id=1,
        match_id=None,
        season="2025-26",
        date="2025-08-04",
        competition_id="sco:premiership",
        competition_name="Premiership",
        round=None,
        home_team_id="sco:aberdeen",
        home_team_name="Aberdeen",
        away_team_id="sco:st-mirren",
        away_team_name="St Mirren",
        home_goals=1,
        away_goals=0,
        status="FT",
    )
    with pytest.raises(FixtureRegistryError, match="duplicate fixture_id"):
        FixtureRegistry([fixture, fixture])
