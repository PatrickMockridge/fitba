"""Shared win/draw/loss and points arithmetic.

Matchday and history both summarise a set of club-perspective match rows. That
arithmetic has one home here so the two surfaces cannot disagree about a record.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def match_result(
    goals_for: int | None,
    goals_against: int | None,
    *,
    shootout_for: int | None = None,
    shootout_against: int | None = None,
) -> dict[str, Any]:
    """Return the regulation result and, separately, the shootout outcome.

    ``result`` is the 90/120-minute result used for W-D-L and league points.
    ``outcome`` includes a penalty shootout; it is the result a supporter would
    call the tie. A shootout is never collapsed into a bare league-style draw.
    """
    gf = int(goals_for or 0)
    ga = int(goals_against or 0)
    result = "W" if gf > ga else "L" if gf < ga else "D"
    if shootout_for is None or shootout_against is None:
        return {
            "result": result,
            "outcome": result,
            "result_label": result,
            "shootout_result": None,
            "decided_by": "regulation",
        }
    penalties_for = int(shootout_for)
    penalties_against = int(shootout_against)
    if penalties_for == penalties_against:
        return {
            "result": result,
            "outcome": result,
            "result_label": f"{result} ({penalties_for}-{penalties_against} pens)",
            "shootout_result": "level",
            "decided_by": "penalties",
        }
    won = penalties_for > penalties_against
    return {
        "result": result,
        "outcome": "W" if won else "L",
        "result_label": (
            f"{result} ({'won' if won else 'lost'} "
            f"{penalties_for}-{penalties_against} pens)"
        ),
        "shootout_result": "won" if won else "lost",
        "decided_by": "penalties",
    }


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


__all__ = ["match_result", "record_totals"]
