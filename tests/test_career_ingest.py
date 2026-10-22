from datetime import date

from fitba.ingest import career_roles
from fitba.ingest.career_roles import (
    _lineup_evidence,
    _scope_for,
    aggregate_evidence,
    scan_aberdeen_history,
)
from fitba.settings import roles as roles_config

CONFIG = roles_config()


def _fixture() -> dict:
    return {
        "fixture": {"id": 1, "date": "2025-08-01T14:00:00+00:00", "status": {"short": "FT"}},
        "teams": {
            "home": {"id": 100, "name": "Previous FC"},
            "away": {"id": 200, "name": "Opponent"},
        },
    }


def _lineup(*, include: bool = True, formation: str = "4-2-3-1") -> dict:
    grid = [
        ("1:1", "G"),
        ("2:1", "D"),
        ("2:2", "D"),
        ("2:3", "D"),
        ("2:4", "D"),
        ("3:1", "M"),
        ("3:2", "M"),
        ("4:1", "M"),
        ("4:2", "M"),
        ("4:3", "M"),
        ("5:1", "F"),
    ]
    starters = []
    for index, (slot, pos) in enumerate(grid):
        player_id = 10 if include and index == 1 else 100 + index
        starters.append(
            {"player": {"id": player_id, "name": f"P{index}", "grid": slot, "pos": pos}}
        )
    return {"team": {"id": 100}, "formation": formation, "startXI": starters}


def _unmapped_lineup() -> dict:
    slots = [("1:1", "G")]
    slots.extend((f"2:{column}", "D") for column in range(1, 10))
    slots.append(("3:1", "F"))
    starters = []
    for index, (slot, pos) in enumerate(slots):
        player_id = 10 if index == 1 else 100 + index
        starters.append(
            {"player": {"id": player_id, "name": f"P{index}", "grid": slot, "pos": pos}}
        )
    return {"team": {"id": 100}, "formation": "9-0-1", "startXI": starters}


def _candidate() -> dict:
    return {
        "player_id": 10,
        "season": "2025-26",
        "team_id": 100,
        "team_name": "Previous FC",
        "scope": "previous_club",
        "scope_source": "fallback",
        "league_id": 1,
        "competition": "League",
    }


def test_lineup_grid_maps_to_a_specific_slot_role():
    row, role_code, missing = _lineup_evidence(
        player_id=10,
        candidate=_candidate(),
        fixture=_fixture(),
        lineup=_lineup(),
        config=CONFIG,
        policy="test",
        now="2026-10-21T00:00:00Z",
    )
    assert row is not None
    assert role_code == "LB"
    assert row["role_family"] == "full_back"
    assert row["role_status"] == "observed"
    assert missing is None


def test_substitute_has_no_role_evidence():
    row, role_code, _ = _lineup_evidence(
        player_id=10,
        candidate=_candidate(),
        fixture=_fixture(),
        lineup=_lineup(include=False),
        config=CONFIG,
        policy="test",
        now="2026-10-21T00:00:00Z",
    )
    assert row is None
    assert role_code is None


def test_unmapped_formation_is_unknown_not_guessed():
    row, role_code, missing = _lineup_evidence(
        player_id=10,
        candidate=_candidate(),
        fixture=_fixture(),
        lineup=_unmapped_lineup(),
        config=CONFIG,
        policy="test",
        now="2026-10-21T00:00:00Z",
    )
    assert row is not None
    assert role_code is None
    assert row["role_status"] == "unknown"
    assert row["unknown_reason"] == "unmapped_formation"
    assert missing == "9-1"


def test_scope_classification_for_loan_and_national(monkeypatch):
    monkeypatch.setattr(career_roles, "_team_info", lambda *args, **kwargs: {})
    scope, source = _scope_for(
        team_id=300,
        season="2025-26",
        loan_intervals=[{"team_id": 300, "start": date(2025, 7, 1), "end": date(2026, 1, 1)}],
        team_cache={},
        force=False,
    )
    assert (scope, source) == ("loan_club", "transfer_history")

    monkeypatch.setattr(career_roles, "_team_info", lambda *args, **kwargs: {"national": True})
    scope, source = _scope_for(
        team_id=400,
        season="2026-27",
        loan_intervals=[],
        team_cache={},
        force=False,
    )
    assert (scope, source) == ("national_team", "team_metadata")


def test_discovery_keeps_entry_with_appearances_but_zero_lineups(monkeypatch):
    monkeypatch.setattr(career_roles.api_football, "transfers", lambda **kwargs: [])
    monkeypatch.setattr(
        career_roles.api_football,
        "player",
        lambda *args, **kwargs: [
            {
                "player": {"id": 10, "name": "Player"},
                "statistics": [
                    {
                        "league": {"id": 1, "name": "League", "season": 2025},
                        "team": {"id": 100, "name": "Previous FC"},
                        "games": {"lineups": 0, "appearences": 1},
                    }
                ],
            }
        ],
    )
    monkeypatch.setattr(career_roles, "_team_info", lambda *args, **kwargs: {})
    candidates, errors = career_roles.discover_candidates(
        10, current="2026-27", config=CONFIG, force=False
    )
    assert not errors
    assert any(row["team_id"] == 100 and row["season"] == "2025-26" for row in candidates)


def test_club_scan_finds_a_starter_without_a_stats_entry(monkeypatch):
    fixture = {
        "fixture": {
            "id": 9001,
            "date": "2025-09-01T14:00:00+00:00",
            "status": {"short": "FT"},
        },
        "league": {"id": 179, "name": "Premiership"},
        "teams": {
            "home": {"id": 252, "name": "Aberdeen"},
            "away": {"id": 200, "name": "Opponent"},
        },
    }
    starters = []
    for index, slot in enumerate(
        ["1:1", "2:1", "2:2", "2:3", "2:4", "3:1", "3:2", "4:1", "4:2", "4:3", "5:1"]
    ):
        player_id = 10 if index == 1 else 100 + index
        starters.append(
            {"player": {"id": player_id, "name": f"P{index}", "grid": slot, "pos": "D"}}
        )
    lineup = {"team": {"id": 252}, "formation": "4-2-3-1", "startXI": starters}

    def fake_fixtures(league_id, season, **kwargs):
        return [fixture] if int(season) == 2025 and int(league_id) == 179 else []

    monkeypatch.setattr(career_roles.api_football, "fixtures", fake_fixtures)
    monkeypatch.setattr(
        career_roles.api_football, "fixtures_lineups", lambda *args, **kwargs: [lineup]
    )

    by_player, scans, errors = scan_aberdeen_history(
        current="2026-27",
        config=CONFIG,
        squad_ids={10},
        evidence_policy="test",
        budget=None,
        force=False,
    )
    assert not errors
    assert len(by_player[10]) == 1
    assert by_player[10][0]["role_code"] == "LB"
    assert by_player[10][0]["scope"] == "aberdeen"
    assert scans[0]["season"] == "2025-26"
    assert scans[0]["starts_found"] == 1


def test_aggregate_evidence_keeps_scope_and_weights():
    evidence = [
        {
            "player_id": 1,
            "player_key": "api:player:1",
            "season": "2026-27",
            "team_id": 252,
            "team_name": "Aberdeen",
            "scope": "aberdeen",
            "scope_source": "club_id",
            "league_id": None,
            "competition": "Premiership",
            "role_code": "RW",
            "role_family": "wide_forward",
        },
        {
            "player_id": 1,
            "player_key": "api:player:1",
            "season": "2025-26",
            "team_id": 100,
            "team_name": "Previous FC",
            "scope": "previous_club",
            "scope_source": "fallback",
            "league_id": 1,
            "competition": "League",
            "role_code": "ST",
            "role_family": "centre_forward",
        },
    ]
    rows = aggregate_evidence(
        evidence, config=CONFIG, current="2026-27", now="2026-10-21T00:00:00Z"
    )
    assert len(rows) == 2
    assert {row["scope"] for row in rows} == {"aberdeen", "previous_club"}
    assert all(row["weighted_starts"] == 1.0 for row in rows)
