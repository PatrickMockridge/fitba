from __future__ import annotations

from fitba.analytics.player_facts import club_totals, league_totals, loan_totals


def _player() -> dict:
    return {
        "stats": [
            {
                "scope": "club",
                "competition": "Premiership",
                "appearances": 10,
                "starts": 9,
                "minutes": 800,
                "goals": 2,
                "assists": 1,
                "rating": 7.0,
                "passes_total": 100,
                "pass_accuracy": 80.0,
            },
            {
                "scope": "club",
                "competition": "Premier Sports Cup",
                "appearances": 2,
                "starts": 2,
                "minutes": 180,
                "goals": 1,
                "assists": 0,
                "rating": 8.0,
                "passes_total": 20,
                "pass_accuracy": 70.0,
            },
            {
                "scope": "loan",
                "competition": "Super Liga",
                "appearances": 4,
                "starts": 1,
                "minutes": 45,
                "goals": 0,
                "assists": 0,
                "rating": 6.5,
            },
        ]
    }


def test_club_totals_include_cups_but_not_loan_rows():
    totals = club_totals(_player())
    assert totals is not None
    assert totals["minutes"] == 980
    assert totals["appearances"] == 12
    assert totals["goals"] == 3
    assert totals["rating"] == 7.17


def test_league_totals_are_premiership_only():
    totals = league_totals(_player())
    assert totals is not None
    assert totals["minutes"] == 800
    assert totals["goals"] == 2
    assert totals["rating"] == 7.0


def test_loan_totals_are_separate():
    totals = loan_totals(_player())
    assert totals is not None
    assert totals["minutes"] == 45
    assert totals["rating"] == 6.5
