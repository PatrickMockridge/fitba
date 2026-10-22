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
    assert summary["reconciliation"]["matched"] is True
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
