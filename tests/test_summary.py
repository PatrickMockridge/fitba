from __future__ import annotations

import pytest

from fitba.analytics.summary import build_summary


def _event(minute: int, team: str, player: str, **extra: object) -> dict:
    return {
        "minute": minute,
        "extra_minute": 0,
        "team_name": team,
        "player_name": player,
        "assist_name": None,
        "is_goal": True,
        "is_own_goal": False,
        "is_penalty": False,
        "is_shootout": False,
        "is_red_card": False,
        "is_second_yellow": False,
        "is_var": False,
        **extra,
    }


def test_goalless_draw_and_missing_stats() -> None:
    summary = build_summary(
        fixture={
            "home_team_name": "Aberdeen",
            "away_team_name": "St Mirren",
            "home_goals": 0,
            "away_goals": 0,
        },
        events=[],
        stats=None,
        xg=None,
    )
    assert "draw 0-0" in summary["headline"]
    assert summary["reconciliation"]["matched"] is None
    assert summary["events_available"] is False
    assert any("event feed is unavailable" in item["text"] for item in summary["bullets"])
    assert not any("records 0 goals" in item["text"] for item in summary["bullets"])
    assert any("Team statistics are unavailable" in item["text"] for item in summary["bullets"])
    assert summary["basis"] == "unknown"


def test_late_winner_and_measured_stats() -> None:
    summary = build_summary(
        fixture={
            "home_team_name": "Aberdeen",
            "away_team_name": "St Mirren",
            "home_goals": 2,
            "away_goals": 1,
        },
        events=[
            _event(20, "Aberdeen", "A"),
            _event(55, "St Mirren", "B"),
            _event(88, "Aberdeen", "C"),
        ],
        stats={
            "home": {"shots": 18, "shots_on_target": 7, "possession": 55},
            "away": {"shots": 6, "shots_on_target": 3, "possession": 45},
        },
        xg={
            "home": 1.8,
            "home_low": 1.2,
            "home_high": 2.4,
            "away": 0.9,
            "away_low": 0.5,
            "away_high": 1.3,
        },
    )
    assert "win it late" in summary["headline"]
    assert any("Shots: Aberdeen 18, St Mirren 6" in item["text"] for item in summary["bullets"])
    assert any(item["basis"] == "inferred" for item in summary["bullets"])


def test_shootout_final_names_the_penalty_winner() -> None:
    summary = build_summary(
        fixture={
            "home_team_name": "Aberdeen",
            "away_team_name": "Celtic",
            "home_goals": 1,
            "away_goals": 1,
        },
        events=[_event(20, "Aberdeen", "A"), _event(50, "Celtic", "B")],
        stats=None,
        xg=None,
        status="PEN",
        home_penalties=4,
        away_penalties=3,
    )
    assert "Aberdeen beat Celtic 4-3 on penalties" in summary["headline"]
    assert "after a 1-1 draw" in summary["headline"]


def test_heavy_defeat_is_not_a_late_win() -> None:
    summary = build_summary(
        fixture={
            "home_team_name": "Hibernian",
            "away_team_name": "Aberdeen",
            "home_goals": 6,
            "away_goals": 0,
        },
        events=[_event(minute, "Hibernian", f"H{minute}") for minute in (10, 20, 30, 40, 80, 90)],
        stats=None,
        xg=None,
    )
    assert "win it late" not in summary["headline"]
    assert "Hibernian beat Aberdeen 6-0" in summary["headline"]


def test_summary_lists_every_scoring_event() -> None:
    summary = build_summary(
        fixture={
            "home_team_name": "Aberdeen",
            "away_team_name": "St Mirren",
            "home_goals": 3,
            "away_goals": 1,
        },
        events=[
            _event(2, "Aberdeen", "Lyons"),
            _event(42, "St Mirren", "Sule"),
            _event(58, "Aberdeen", "Nisbet"),
            _event(72, "Aberdeen", "Mouloua"),
        ],
        stats=None,
        xg=None,
    )
    text = " ".join(item["text"] for item in summary["bullets"])
    for scorer in ("Lyons", "Sule", "Nisbet", "Mouloua"):
        assert scorer in text


def test_partial_event_feed_is_labelled_incomplete() -> None:
    summary = build_summary(
        fixture={
            "home_team_name": "Heart of Midlothian",
            "away_team_name": "Aberdeen",
            "home_goals": 4,
            "away_goals": 4,
        },
        events=[_event(12, "Aberdeen", "A"), _event(44, "Heart of Midlothian", "B")],
        stats=None,
        xg=None,
        events_available=True,
        goals_complete=False,
    )
    assert summary["goals_complete"] is False
    assert any("does not reconcile" in item["text"] for item in summary["bullets"])


def test_red_card_and_own_goal_are_measured() -> None:
    summary = build_summary(
        fixture={
            "home_team_name": "Aberdeen",
            "away_team_name": "Dundee",
            "home_goals": 1,
            "away_goals": 1,
        },
        events=[
            _event(
                12,
                "Dundee",
                "D",
                is_own_goal=True,
                beneficiary_side="away",
            ),
            _event(50, "Aberdeen", "A", beneficiary_side="home"),
            _event(70, "Dundee", "E", is_goal=False, is_red_card=True),
        ],
        stats=None,
        xg=None,
    )
    assert any("own goal" in item["text"].casefold() for item in summary["bullets"])
    assert any("sent off" in item["text"] for item in summary["bullets"])
    assert summary["reconciliation"]["matched"] is True


def test_banned_verdict_language_is_rejected() -> None:
    with pytest.raises(ValueError, match="banned summary phrase"):
        build_summary(
            fixture={
                "home_team_name": "Aberdeen",
                "away_team_name": "Dundee",
                "home_goals": 1,
                "away_goals": 0,
            },
            events=[_event(20, "Aberdeen", "Deserved Hero")],
            stats={"home": {"shots": 10}, "away": {"shots": 2}},
            xg=None,
        )
