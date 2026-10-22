from __future__ import annotations

import polars as pl

from fitba.normalize.fixture_registry import FixtureRecord
from fitba.publish.fixture import _depth, _stat_rows, _timeline, _xg_block


def _fixture() -> FixtureRecord:
    return FixtureRecord(
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
        home_goals=2,
        away_goals=1,
        status="FT",
        home_ht_goals=1,
        away_ht_goals=0,
    )


def test_depth_states() -> None:
    assert (
        _depth(
            {
                "events": True,
                "lineups": True,
                "team_stats": True,
                "player_stats": True,
            }
        )
        == "full"
    )
    assert _depth({"events": True, "lineups": True, "team_stats": True}) == "result"
    assert _depth({"events": True, "lineups": True}) == "result"
    assert _depth({"events": False, "lineups": False}) == "score"


def test_timeline_reconstructs_score_and_own_goals() -> None:
    events = pl.DataFrame(
        {
            "minute": [20, 55],
            "extra_minute": [None, None],
            "team_name": ["Aberdeen", "St Mirren"],
            "player_name": ["A", "B"],
            "assist_name": [None, None],
            "event_type": ["Goal", "Goal"],
            "detail": ["Normal Goal", "Own Goal"],
            "comments": [None, None],
            "is_goal": [True, True],
            "is_own_goal": [False, True],
            "is_penalty": [False, False],
            "is_shootout": [False, False],
            "is_red_card": [False, False],
            "is_second_yellow": [False, False],
            "is_var": [False, False],
        }
    )
    timeline = _timeline(events, _fixture())
    assert timeline[0]["score_after"] == {"home": 1, "away": 0}
    assert timeline[1]["score_after"] == {"home": 2, "away": 0}


def test_stat_rows_keep_source_and_skip_missing() -> None:
    rows = _stat_rows(
        {"shots": 10, "possession": None},
        {"shots": 5, "possession": 45},
        {"shots": "football_data_uk", "possession": "api_football"},
    )
    keys = {row["key"] for row in rows}
    assert "shots" in keys
    assert "possession" in keys
    assert next(row for row in rows if row["key"] == "shots")["source"] == "football_data_uk"


def test_xg_block_maps_home_and_away() -> None:
    block = _xg_block(
        _fixture(),
        {
            "fxg_for": 1.6,
            "fxg_for_low": 1.1,
            "fxg_for_high": 2.1,
            "fxg_against": 0.8,
            "fxg_against_low": 0.4,
            "fxg_against_high": 1.2,
            "provider_xg_for": 1.4,
            "provider_xg_against": 0.9,
            "model_id": "fxg-1",
        },
    )
    assert block["available"] is True
    assert block["home"]["value"] == 1.6
    assert block["away"]["value"] == 0.8
    assert block["home"]["provider"] == 1.4
