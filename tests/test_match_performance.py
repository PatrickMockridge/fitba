"""Tests for the match-page performance selection."""

from __future__ import annotations

from fitba.publish.fixture import _performance_block


def _player(
    player_id: int,
    name: str,
    is_aberdeen: bool,
    rating: float | None,
    goals: int = 0,
    assists: int = 0,
    shots_on: int = 0,
) -> dict:
    return {
        "player_id": player_id,
        "player_name": name,
        "href": f"/players/{player_id}/",
        "team_name": "Aberdeen" if is_aberdeen else "Opponent",
        "is_aberdeen": is_aberdeen,
        "rating": rating,
        "minutes": 90,
        "goals": goals,
        "assists": assists,
        "shots_total": shots_on + 2,
        "shots_on": shots_on,
        "passes_total": 30,
        "pass_accuracy": 25,
        "tackles": 2,
        "duels_won": 5,
    }


def test_selects_top_ratings_and_aberdeen_strengths() -> None:
    players = [
        _player(1, "A", True, 8.0, goals=1),
        _player(2, "B", True, 7.5, assists=1),
        _player(3, "C", True, 7.0),
        _player(4, "D", True, 6.0),
        _player(5, "E", False, 7.8),
        _player(6, "F", False, 7.2),
    ]
    home_stats = {
        "shots": 17,
        "shots_on_target": 7,
        "shots_insidebox": 10,
        "possession": 35.0,
        "passes_pct": 72.0,
    }
    away_stats = {
        "shots": 13,
        "shots_on_target": 7,
        "shots_insidebox": 8,
        "possession": 65.0,
        "passes_pct": 83.0,
    }
    stat_rows = [
        {"key": "shots", "source": "api_football"},
        {"key": "shots_insidebox", "source": "api_football"},
    ]
    performance = _performance_block(
        players,
        home_stats=home_stats,
        away_stats=away_stats,
        stat_rows=stat_rows,
        aberdeen_is_home=True,
    )
    assert performance["available"] is True
    assert performance["aberdeen"]["basis"] == "provider_rating"
    assert [p["player_name"] for p in performance["aberdeen"]["players"]] == [
        "A",
        "B",
        "C",
    ]
    assert performance["opponent"]["players"][0]["player_name"] == "E"
    assert [item["label"] for item in performance["strengths"]] == [
        "Shots",
        "Shots inside box",
    ]
    assert all(item["aberdeen"] > item["opponent"] for item in performance["strengths"])


def test_falls_back_to_measured_output_without_ratings() -> None:
    players = [
        _player(1, "A", True, None, goals=2),
        _player(2, "B", True, None, goals=1, assists=1),
        _player(3, "C", True, None, goals=0, assists=2),
    ]
    performance = _performance_block(
        players,
        home_stats={"shots": 10},
        away_stats={"shots": 8},
        stat_rows=[{"key": "shots", "source": "api_football"}],
        aberdeen_is_home=True,
    )
    assert performance["aberdeen"]["basis"] == "measured_output"
    assert performance["aberdeen"]["players"][0]["player_name"] == "A"
