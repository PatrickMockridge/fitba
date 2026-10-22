from __future__ import annotations

import importlib.util
from pathlib import Path

from fitba.settings import roles

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_matchday", ROOT / "scripts" / "check_matchday.py"
)
assert SPEC and SPEC.loader
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)

SLOTS = [
    ("1:1", "GK"),
    ("2:1", "LB"),
    ("2:2", "CB"),
    ("2:3", "CB"),
    ("2:4", "RB"),
    ("3:1", "CM"),
    ("3:2", "CM"),
    ("4:1", "LW"),
    ("4:2", "AM"),
    ("4:3", "RW"),
    ("5:1", "ST"),
]


def _block() -> dict:
    return {
        "status": "available",
        "formation": "4-2-3-1",
        "formation_confidence": "high",
        "team_confidence": "high",
        "filled": 11,
        "coverage": {"fixtures_with_lineups": 6, "fixtures_total": 9, "lineup_coverage": 0.667},
        "disclaimer": "Predicted, not official team news.",
        "unavailable": [],
        "unknowns": [],
        "players": [
            {
                "player_id": index + 1,
                "name": f"Player {index + 1}",
                "grid": grid,
                "role_code": role,
                "confidence": "high",
            }
            for index, (grid, role) in enumerate(SLOTS)
        ],
        "contenders": [
            {
                "player_id": 100 + index,
                "name": f"Contender {index}",
                "slot": "3:2",
                "role_code": "CM",
                "confidence": "medium",
            }
            for index in range(4)
        ],
    }


def _squad() -> dict[int, dict]:
    return {
        player_id: {"player_id": player_id, "status": "squad", "injured": False}
        for player_id in range(1, 12)
    }


def test_valid_lineup_passes():
    errors: list[str] = []
    warnings: list[str] = []
    GUARD._check_lineup(
        "aberdeen",
        _block(),
        squad=_squad(),
        roles_config=roles(),
        errors=errors,
        warnings=warnings,
    )
    assert errors == []


def test_duplicate_and_wrong_role_fail():
    block = _block()
    block["players"][1]["player_id"] = 1
    block["players"][2]["role_code"] = "ST"
    errors: list[str] = []
    warnings: list[str] = []
    GUARD._check_lineup(
        "aberdeen",
        block,
        squad=_squad(),
        roles_config=roles(),
        errors=errors,
        warnings=warnings,
    )
    assert any("duplicate" in error for error in errors)
    assert any("expected" in error for error in errors)


def test_missing_goalkeeper_fails():
    block = _block()
    block["players"][0]["role_code"] = "CB"
    errors: list[str] = []
    warnings: list[str] = []
    GUARD._check_lineup(
        "aberdeen",
        block,
        squad=_squad(),
        roles_config=roles(),
        errors=errors,
        warnings=warnings,
    )
    assert any("goalkeeper" in error for error in errors)


def test_loan_out_and_injured_players_fail():
    squad = _squad()
    squad[1]["injured"] = True
    squad[2]["status"] = "loan_out"
    errors: list[str] = []
    warnings: list[str] = []
    GUARD._check_lineup(
        "aberdeen",
        _block(),
        squad=squad,
        roles_config=roles(),
        errors=errors,
        warnings=warnings,
    )
    assert any("injured" in error for error in errors)
    assert any("loan-out" in error for error in errors)


def test_string_scan_finds_certainty_language_and_forbidden_hosts():
    text = GUARD._strings(
        {
            "a": "confirmed XI",
            "b": "https://www.transfermarkt.com/player",
            "c": "Predicted, not official team news.",
        }
    )
    joined = " | ".join(text).casefold()
    assert "confirmed xi" in joined
    assert "transfermarkt." in joined
