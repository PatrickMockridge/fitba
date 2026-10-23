from __future__ import annotations

import pytest

from fitba.ingest.scouting import (
    _aggregate_roles,
    _pool_row,
    _select_leagues,
    season_year,
)

LEAGUE = {
    "id": "eng:league-two",
    "slug": "eng-league-two",
    "name": "EFL League Two",
    "country": "England",
    "tier": 4,
    "provider": {"api_football_id": 42, "player_stats": True, "lineups": True},
}


def _entry(team_id: int, team_name: str, minutes: int, goals: int) -> dict:
    return {
        "team": {"id": team_id, "name": team_name},
        "league": {"id": 42, "name": "League Two", "season": 2026},
        "games": {
            "appearences": 10,
            "lineups": 10,
            "minutes": minutes,
            "position": "Midfielder",
            "rating": "6.80",
        },
        "goals": {"total": goals, "assists": 1, "saves": 0, "conceded": 0},
        "cards": {"yellow": 1, "red": 0, "yellowred": 0},
        "shots": {"total": 4, "on": 2},
        "passes": {"total": 300, "key": 3, "accuracy": "80%"},
        "tackles": {"total": 10, "blocks": 1, "interceptions": 5},
        "duels": {"total": 40, "won": 20},
        "dribbles": {"attempts": 10, "success": 6},
        "fouls": {"drawn": 2, "committed": 3},
        "penalty": {"won": 0, "commited": 0, "scored": 0, "missed": 0, "saved": 0},
    }


def _raw(entries: list[dict]) -> dict:
    return {
        "player": {
            "id": 1,
            "name": "A. Player",
            "firstname": "A",
            "lastname": "Player",
            "age": 24,
            "nationality": "England",
            "birth": {"date": "2002-01-01"},
        },
        "statistics": entries,
    }


def test_season_year_is_the_start_year():
    assert season_year("2026-27") == 2026
    assert season_year("2025-26") == 2025


def test_select_leagues_rejects_unknown_ids():
    with pytest.raises(ValueError, match="unknown scouting leagues"):
        _select_leagues("eng:not-a-league")


def test_pool_row_sums_team_entries_and_keeps_the_primary_club():
    row = _pool_row(
        _raw(
            [
                _entry(1, "Club A", 600, 3),
                _entry(2, "Club B", 300, 1),
            ]
        ),
        LEAGUE,
        year=2026,
        ingested_at="2026-10-23T00:00:00Z",
    )
    assert row is not None
    assert row["player_id"] == 1
    assert row["position_group"] == "MID"
    assert row["team_name"] == "Club A"
    assert row["multi_team"] is True
    assert row["minutes"] == 900
    assert row["goals"] == 4
    assert row["passes_total"] == 600
    assert row["rating"] == 6.8
    assert row["competition_id"] == "eng:league-two"
    assert "contract" not in row


def test_pool_row_ignores_another_league_and_an_empty_statistics_list():
    other = _entry(1, "Club A", 600, 3)
    other["league"] = {"id": 179, "name": "Premiership", "season": 2026}
    assert _pool_row(_raw([other]), LEAGUE, year=2026, ingested_at="x") is None
    assert _pool_row(_raw([]), LEAGUE, year=2026, ingested_at="x") is None


def test_role_aggregation_uses_the_primary_family_and_share():
    rows = [
        {
            "player_id": 1,
            "league_id": "eng:league-two",
            "team_id": 10,
            "team_name": "Club A",
            "role_code": "CB",
            "role_family": "centre_back",
        },
        {
            "player_id": 1,
            "league_id": "eng:league-two",
            "team_id": 10,
            "team_name": "Club A",
            "role_code": "CB",
            "role_family": "centre_back",
        },
        {
            "player_id": 1,
            "league_id": "eng:league-two",
            "team_id": 10,
            "team_name": "Club A",
            "role_code": "RB",
            "role_family": "full_back",
        },
    ]
    out = _aggregate_roles(rows, year=2026)
    assert len(out) == 1
    assert out[0]["role_family"] == "centre_back"
    assert out[0]["role_code"] == "CB"
    assert out[0]["starts_total"] == 3
    assert out[0]["role_family_share"] == 0.667
    assert out[0]["role_status"] == "observed"
