"""Loan scopes: official team list versus the transfer register.

The same player can be on the official On loan section, in the current-season
register, in both, or only in the register (typically a development loan the
official first-team page does not list). These are different facts with
different denominators. This module publishes them together so no page has to
choose silently.
"""

from __future__ import annotations

from typing import Any


def _player_ref(player: dict[str, Any]) -> dict[str, Any]:
    loan = player.get("loan") or {}
    return {
        "player_id": player.get("player_id"),
        "player_key": player.get("player_key"),
        "player_name": player.get("name") or player.get("full_name"),
        "club": loan.get("club"),
        "since": loan.get("since"),
        "end_date": loan.get("end_date"),
    }


def _register_ref(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "player_id": row.get("player_id"),
        "player_key": row.get("player_key"),
        "player_name": row.get("player_name"),
        "club": (
            row.get("to_club_name")
            if row.get("direction") == "out"
            else row.get("from_club_name")
        ),
        "date_effective": row.get("date_effective"),
        "season": row.get("season"),
    }


def loan_scope(
    squad_data: dict[str, Any] | None,
    transfers_payload: dict[str, Any] | None,
    season: str,
) -> dict[str, Any]:
    """Return the official, current-register and all-time loan scopes."""
    players = list((squad_data or {}).get("players") or [])
    official_out = [player for player in players if player.get("status") == "loan_out"]
    official_in = [player for player in players if player.get("status") == "loan_in"]
    register_out = list((transfers_payload or {}).get("loans_out") or [])
    register_in = list((transfers_payload or {}).get("loans_in") or [])
    current_out = [row for row in register_out if str(row.get("season")) == season]
    current_in = [row for row in register_in if str(row.get("season")) == season]

    official_keys = {str(player.get("player_key")) for player in official_out}
    current_keys = {str(row.get("player_key")) for row in current_out}
    register_only = [
        _register_ref(row) for row in current_out if str(row.get("player_key")) not in official_keys
    ]
    official_only = [
        _player_ref(player)
        for player in official_out
        if str(player.get("player_key")) not in current_keys
    ]
    return {
        "season": season,
        "official_list": {
            "out_count": len(official_out),
            "in_count": len(official_in),
            "out": [_player_ref(player) for player in official_out],
            "in": [_player_ref(player) for player in official_in],
        },
        "register_current": {
            "out_count": len(current_out),
            "in_count": len(current_in),
            "out": [_register_ref(row) for row in current_out],
            "in": [_register_ref(row) for row in current_in],
        },
        "register_all_time": {
            "out_count": len(register_out),
            "in_count": len(register_in),
        },
        "reconciliation": {
            "matched_out": len(official_keys & current_keys),
            "register_only_out": register_only,
            "official_only_out": official_only,
            "note": (
                "The official list and the transfer register are different "
                "scopes. The official On loan section is the squad count; the "
                "register also includes development loans the first-team page "
                "does not list."
            ),
        },
    }


__all__ = ["loan_scope"]
