from __future__ import annotations

from fitba.ingest.scouting_europe import (
    _aggregate,
    is_league_phase,
    season_year,
)


def _row(player_id: int, competition_id: str, minutes: int, rating: float | None) -> dict:
    return {
        "player_id": player_id,
        "player_key": f"api:player:{player_id}",
        "player_name": f"Player {player_id}",
        "team_id": 100,
        "team_name": "Club",
        "competition_id": competition_id,
        "competition": "UEFA Champions League",
        "league_phase": True,
        "minutes": minutes,
        "appearances": 1,
        "rating": rating,
    }


def test_league_phase_round_filter():
    assert is_league_phase("League Stage - 1")
    assert is_league_phase("league stage - 8")
    assert not is_league_phase("1st Qualifying Round")
    assert not is_league_phase("Play-offs")
    assert not is_league_phase("Playoff round")


def test_season_year_is_the_start_year():
    assert season_year("2026-27") == 2026


def test_aggregate_sums_minutes_and_weights_rating():
    rows = [
        _row(1, "uefa:champions-league", 90, 7.0),
        _row(1, "uefa:champions-league", 30, 8.0),
        _row(2, "uefa:champions-league", 120, None),
    ]
    out = _aggregate(rows, "2026-10-23T00:00:00Z")
    first = next(item for item in out if item["player_id"] == 1)
    assert first["minutes"] == 120
    assert first["appearances"] == 2
    assert first["fixtures"] == 2
    assert first["rating"] == 7.25
    second = next(item for item in out if item["player_id"] == 2)
    assert second["rating"] is None
