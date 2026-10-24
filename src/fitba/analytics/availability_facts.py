"""Availability counts for the two published squad universes.

The curated ledger covers every player on the official team list, including
loans out. Analysis and matchday usually care about the active squad; the
availability page and needs board may show the full register. Both are
legitimate, so both are published with their universe named rather than one
number being reused under the same label.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

KNOWN_STATUSES = ("out", "suspended", "doubtful", "returned", "available")
ALL_STATUSES = (*KNOWN_STATUSES, "unknown")


def _summary(
    *,
    universe: str,
    players: list[dict[str, Any]],
    entries: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    counts = {status: 0 for status in ALL_STATUSES}
    seen: set[int] = set()
    for player in players:
        player_id = int(player["player_id"])
        if player_id in seen:
            continue
        seen.add(player_id)
        status = str((entries.get(player_id) or {}).get("status") or "unknown")
        counts[status if status in counts else "unknown"] += 1
    known = sum(counts[status] for status in KNOWN_STATUSES)
    return {
        "universe": universe,
        "players": len(seen),
        "known": known,
        "unknown": counts["unknown"],
        "counts": counts,
    }


def availability_universes(
    entries: Iterable[dict[str, Any]] | None,
    squad_data: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return official-list and active-squad availability summaries."""
    players = list((squad_data or {}).get("players") or [])
    by_id = {
        int(entry["player_id"]): entry
        for entry in entries or []
        if entry.get("player_id") is not None
    }
    official = [player for player in players if player.get("squad_member", True)]
    active = [player for player in official if player.get("status") == "squad"]
    return {
        "official_list": _summary(
            universe="official_list",
            players=official,
            entries=by_id,
        ),
        "active_squad": _summary(
            universe="active_squad",
            players=active,
            entries=by_id,
        ),
    }


__all__ = ["ALL_STATUSES", "KNOWN_STATUSES", "availability_universes"]
