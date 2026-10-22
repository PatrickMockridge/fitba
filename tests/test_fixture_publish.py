from __future__ import annotations

import polars as pl

from fitba.normalize.fixture_registry import FixtureRecord
from fitba.normalize.teams import TeamRegistry
from fitba.publish.fixture import (
    _depth,
    _player_stats_block,
    _resolve_event_team,
    _scoreboard,
    _stat_rows,
    _timeline,
    _xg_block,
)


def _fixture(
    *,
    status: str = "FT",
    home_goals: int = 2,
    away_goals: int = 1,
    home_penalties: int | None = None,
    away_penalties: int | None = None,
    home_team_id: str = "sco:aberdeen",
    home_team_name: str = "Aberdeen",
    away_team_id: str = "sco:st-mirren",
    away_team_name: str = "St Mirren",
) -> FixtureRecord:
    return FixtureRecord(
        key="api:fixture:1",
        fixture_id=1,
        match_id=None,
        season="2025-26",
        date="2025-08-04",
        competition_id="sco:premiership",
        competition_name="Premiership",
        round=None,
        home_team_id=home_team_id,
        home_team_name=home_team_name,
        away_team_id=away_team_id,
        away_team_name=away_team_name,
        home_goals=home_goals,
        away_goals=away_goals,
        home_penalties=home_penalties,
        away_penalties=away_penalties,
        status=status,
        home_ht_goals=1,
        away_ht_goals=0,
    )


def _events(rows: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(rows)


def _event(
    minute: int,
    team: str,
    player: str,
    *,
    event_type: str = "goal",
    detail: str = "Normal Goal",
    extra: int | None = None,
    assist: str | None = None,
    is_goal: bool = True,
    is_own_goal: bool = False,
    is_penalty: bool = False,
    is_shootout: bool = False,
    is_red_card: bool = False,
    is_second_yellow: bool = False,
    comments: str | None = None,
) -> dict:
    return {
        "minute": minute,
        "extra_minute": extra,
        "team_name": team,
        "player_name": player,
        "assist_name": assist,
        "event_type": event_type,
        "detail": detail,
        "comments": comments,
        "is_goal": is_goal,
        "is_own_goal": is_own_goal,
        "is_penalty": is_penalty,
        "is_shootout": is_shootout,
        "is_red_card": is_red_card,
        "is_second_yellow": is_second_yellow,
        "is_var": False,
    }


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
    assert _depth({"events": True, "lineups": False, "team_stats": True}) == "partial"
    assert _depth({"events": False, "lineups": False, "team_stats": True}) == "partial"
    assert _depth({"events": False, "lineups": False}) == "score"


def test_timeline_orders_stoppage_time_after_regulation_minute() -> None:
    events = _events(
        [
            _event(
                90,
                "Aberdeen",
                "A. Card",
                event_type="card",
                detail="Yellow Card",
                is_goal=False,
                extra=3,
            ),
            _event(90, "Aberdeen", "B. Goal", detail="Normal Goal"),
        ]
    )
    timeline = _timeline(events, _fixture(home_goals=1, away_goals=0))
    assert [row["player_name"] for row in timeline] == ["B. Goal", "A. Card"]


def test_timeline_infers_second_yellow_from_two_yellows() -> None:
    events = _events(
        [
            _event(
                31,
                "St Mirren",
                "D. Happe",
                event_type="card",
                detail="Yellow Card",
                is_goal=False,
            ),
            _event(
                58,
                "St Mirren",
                "D. Happe",
                event_type="card",
                detail="Yellow Card",
                is_goal=False,
            ),
            _event(
                58,
                "St Mirren",
                "D. Happe",
                event_type="card",
                detail="Red Card",
                is_goal=False,
                is_red_card=True,
            ),
        ]
    )
    timeline = _timeline(events, _fixture(home_goals=1, away_goals=0))
    assert timeline[-1]["is_second_yellow"] is True
    assert timeline[-1]["card_type"] == "second_yellow"


def test_timeline_credits_own_goal_to_event_team_without_flip() -> None:
    events = _events(
        [
            _event(20, "Aberdeen", "A"),
            _event(55, "St Mirren", "B", detail="Own Goal", is_own_goal=True),
        ]
    )
    timeline = _timeline(events, _fixture())
    assert timeline[0]["score_after"] == {"home": 1, "away": 0}
    assert timeline[1]["side"] == "away"
    assert timeline[1]["beneficiary_side"] == "away"
    assert timeline[1]["score_after"] == {"home": 1, "away": 1}


def test_timeline_carries_assist_penalty_and_card_types() -> None:
    events = _events(
        [
            _event(12, "Aberdeen", "A", assist="B", is_penalty=True, detail="Penalty"),
            _event(
                60,
                "St Mirren",
                "C",
                event_type="card",
                detail="Second Yellow card",
                is_goal=False,
                is_red_card=True,
                is_second_yellow=True,
            ),
            _event(
                70,
                "Aberdeen",
                "D",
                event_type="card",
                detail="Red Card",
                is_goal=False,
                is_red_card=True,
            ),
            _event(
                80,
                "St Mirren",
                "E",
                event_type="card",
                detail="Yellow Card",
                is_goal=False,
            ),
            _event(90, "Aberdeen", "F", detail="Missed Penalty", is_goal=False),
        ]
    )
    timeline = _timeline(events, _fixture(home_goals=1, away_goals=0))
    assert timeline[0]["is_penalty"] is True
    assert timeline[0]["assist_name"] == "B"
    assert timeline[1]["card_type"] == "second_yellow"
    assert timeline[2]["card_type"] == "straight_red"
    assert timeline[3]["card_type"] is None
    assert timeline[4]["is_missed_penalty"] is True


def test_scoreboard_groups_goals_and_red_cards() -> None:
    fixture = _fixture(home_goals=2, away_goals=1)
    timeline = _timeline(
        _events(
            [
                _event(12, "Aberdeen", "A", assist="B"),
                _event(44, "St Mirren", "C", is_penalty=True, detail="Penalty"),
                _event(77, "Aberdeen", "D"),
                _event(
                    80,
                    "Aberdeen",
                    "E",
                    event_type="card",
                    detail="Red Card",
                    is_goal=False,
                    is_red_card=True,
                ),
            ]
        ),
        fixture,
    )
    board = _scoreboard(timeline, fixture, events_available=True)
    assert board["events_available"] is True
    assert board["goals_complete"] is True
    assert len(board["home"]["goals"]) == 2
    assert len(board["away"]["goals"]) == 1
    assert board["home"]["goals"][0]["assist_name"] == "B"
    assert board["home"]["red_cards"][0]["card_type"] == "straight_red"
    assert board["home"]["is_aberdeen"] is True
    assert board["away"]["is_aberdeen"] is False


def test_scoreboard_handles_missing_events_and_shootout() -> None:
    empty = _fixture()
    board = _scoreboard([], empty, events_available=False)
    assert board["events_available"] is False
    assert board["goals_complete"] is False
    assert board["home"]["goals"] == []
    assert "unavailable" in board["note"]

    shootout_fixture = _fixture(
        status="PEN",
        home_goals=2,
        away_goals=2,
        home_penalties=5,
        away_penalties=3,
    )
    timeline = _timeline(
        _events(
            [
                _event(37, "St Mirren", "A"),
                _event(77, "Aberdeen", "B"),
                _event(93, "St Mirren", "C", is_penalty=True, detail="Penalty"),
                _event(95, "Aberdeen", "D"),
                _event(120, "Aberdeen", "E", extra=1, is_penalty=True, detail="Penalty"),
                _event(120, "St Mirren", "F", extra=2, is_penalty=True, detail="Penalty"),
            ]
        ),
        shootout_fixture,
    )
    board = _scoreboard(timeline, shootout_fixture, events_available=True)
    assert board["goals_complete"] is True
    assert board["shootout"] == {"home": 5, "away": 3}
    assert sum(len(side["goals"]) for side in (board["home"], board["away"])) == 4
    assert all(
        not goal.get("is_penalty") for goal in board["home"]["goals"] if goal["minute"] == 120
    )


def test_alias_resolution_and_player_team_identity() -> None:
    fixture = _fixture(
        away_team_id="sco:dundee-united",
        away_team_name="Dundee United",
        away_goals=1,
    )
    side, name = _resolve_event_team("Dundee Utd", fixture, TeamRegistry())
    assert (side, name) == ("away", "Dundee United")

    stats = pl.DataFrame(
        [
            {"player_id": 1, "team_id": 252, "fixture_id": 1},
            {"player_id": 2, "team_id": 99, "fixture_id": 1},
            {"player_id": 3, "team_id": None, "fixture_id": 1},
        ]
    )
    rows = _player_stats_block(fixture, stats, aberdeen_api_id=252)
    assert rows[0]["team_name"] == "Aberdeen"
    assert rows[0]["is_aberdeen"] is True
    assert rows[1]["team_name"] == "Dundee United"
    assert rows[1]["is_aberdeen"] is False
    assert rows[2]["team_name"] is None
    assert rows[2]["is_aberdeen"] is None


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
