"""Shared parser for API-Football `/fixtures/statistics` team blocks.

The provider returns two team blocks per fixture. Keep both, keep every field
we can name, and let each caller select its own storage schema. A missing
provider value is None, never zero.
"""

from __future__ import annotations

from typing import Any

TEAM_STAT_FIELDS = [
    "fixture_id",
    "team_id",
    "team_name",
    "possession",
    "shots",
    "shots_on_target",
    "shots_off",
    "shots_blocked",
    "shots_insidebox",
    "shots_outsidebox",
    "expected_goals",
    "goals_prevented",
    "passes",
    "pass_accuracy",
    "passes_pct",
    "corners",
    "fouls",
    "offsides",
    "yellow_cards",
    "red_cards",
    "saves",
]


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).replace("%", "").strip()))
    except (TypeError, ValueError):
        return None


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def _values(block: dict[str, Any]) -> dict[str, Any]:
    return {
        str(stat.get("type") or "").casefold().replace(" ", "_"): stat.get("value")
        for stat in block.get("statistics") or []
    }


def parse_team_stats(
    payload: list[dict[str, Any]],
    *,
    fixture_id: int,
) -> list[dict[str, Any]]:
    """Parse both team blocks into the canonical team-stat fields."""
    rows: list[dict[str, Any]] = []
    for block in payload or []:
        team = block.get("team") or {}
        team_id = _int(team.get("id"))
        if team_id is None:
            continue
        values = _values(block)
        rows.append(
            {
                "fixture_id": fixture_id,
                "team_id": team_id,
                "team_name": team.get("name"),
                "possession": _float(values.get("ball_possession")),
                "shots": _int(values.get("total_shots")),
                "shots_on_target": _int(values.get("shots_on_goal")),
                "shots_off": _int(values.get("shots_off_goal")),
                "shots_blocked": _int(values.get("blocked_shots")),
                "shots_insidebox": _int(values.get("shots_insidebox")),
                "shots_outsidebox": _int(values.get("shots_outsidebox")),
                "expected_goals": _float(values.get("expected_goals")),
                "goals_prevented": _float(values.get("goals_prevented")),
                "passes": _int(values.get("total_passes")),
                "pass_accuracy": _int(values.get("passes_accurate")),
                "passes_pct": _float(values.get("passes_%")),
                "corners": _int(values.get("corner_kicks")),
                "fouls": _int(values.get("fouls")),
                "offsides": _int(values.get("offsides")),
                "yellow_cards": _int(values.get("yellow_cards")),
                "red_cards": _int(values.get("red_cards")),
                "saves": _int(values.get("goalkeeper_saves")),
            }
        )
    return rows


__all__ = ["TEAM_STAT_FIELDS", "parse_team_stats"]
