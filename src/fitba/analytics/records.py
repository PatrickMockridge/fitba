"""Shared win/draw/loss and points arithmetic.

Matchday and history both summarise a set of club-perspective match rows. That
arithmetic has one home here so the two surfaces cannot disagree about a record.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def record_totals(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Return played, W-D-L, goals, points, goal difference and PPG."""
    items = list(rows)
    played = len(items)
    won = sum(1 for row in items if row.get("result") == "W")
    drawn = sum(1 for row in items if row.get("result") == "D")
    lost = sum(1 for row in items if row.get("result") == "L")
    gf = sum(int(row.get("gf") or 0) for row in items)
    ga = sum(int(row.get("ga") or 0) for row in items)
    points = sum(int(row.get("points") or 0) for row in items)
    return {
        "played": played,
        "won": won,
        "drawn": drawn,
        "lost": lost,
        "gf": gf,
        "ga": ga,
        "gd": gf - ga,
        "points": points,
        "ppg": round(points / played, 2) if played else None,
    }


__all__ = ["record_totals"]
