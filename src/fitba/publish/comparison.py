"""Publish the reviewed current-squad comparison allowlist.

The crosswalk is identity and cohort metadata only. It never copies minutes,
percentiles, fees or any other published number; the scouting squad payload
remains the source.
"""

from __future__ import annotations

import re
from typing import Any

PLAYER_KEY = re.compile(r"^api:player:\d+$")


def build_comparison_crosswalk(
    *,
    config: dict[str, Any],
    squad_data: dict[str, Any],
    scouting_squad: list[dict[str, Any]],
) -> dict[str, Any]:
    squad_ids = {
        int(player["player_id"])
        for player in squad_data.get("players") or []
        if player.get("player_id") is not None
    }
    profile = {
        int(row["player_id"]): row
        for row in scouting_squad or []
        if row.get("player_id") is not None
    }
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for row in config.get("players") or []:
        player_id = int(row.get("player_id") or 0)
        player_key = str(row.get("player_key") or "")
        if not player_id or player_id in seen:
            raise ValueError(f"comparison: duplicate or missing player id {player_id}")
        seen.add(player_id)
        if not PLAYER_KEY.match(player_key):
            raise ValueError(f"comparison: invalid player_key {player_key!r}")
        if str(row.get("league_slug") or "") != "sco-premiership":
            raise ValueError("comparison: current-squad rows must use sco-premiership")
        if player_id not in squad_ids:
            raise ValueError(f"comparison: {player_id} is not on the current squad")
        published = profile.get(player_id)
        if published is None:
            raise ValueError(f"comparison: {player_id} has no published squad profile row")
        if published.get("rating_percentile") is None:
            raise ValueError(f"comparison: {player_id} has no published percentile")
        if str(published.get("role_family") or "") != str(row.get("role_family") or ""):
            raise ValueError(
                f"comparison: {player_id} role_family does not match the published row"
            )
        if not str(row.get("reviewed_by") or "").strip():
            raise ValueError(f"comparison: {player_id} has no reviewer")
        if not str(row.get("reviewed_at") or "").startswith("20"):
            raise ValueError(f"comparison: {player_id} has no review date")
        rows.append(
            {
                "player_id": player_id,
                "player_key": player_key,
                "league_slug": str(row["league_slug"]),
                "role_family": str(row["role_family"]),
                "cohort_basis": str(row.get("cohort_basis") or "role_family"),
                "reviewed_by": str(row["reviewed_by"]),
                "reviewed_at": str(row["reviewed_at"]),
                "notes": str(row.get("notes") or "").strip(),
            }
        )
    rows.sort(key=lambda item: item["player_id"])
    return {
        "schema_version": "1.0.0",
        "state": "available" if rows else "not_reviewed",
        "reviewed": str(config.get("reviewed") or ""),
        "owner": str(config.get("owner") or ""),
        "players": rows,
    }
