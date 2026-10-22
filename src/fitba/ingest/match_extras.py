"""Normalise API-Football events and team lineups for the fixture record.

The provider event payload carries minute, team, player, assist, type, detail
and comments. It does not carry shot coordinates or a running score, so this
module keeps only what exists and classifies the rest explicitly. The summary
builder reconstructs the score from the ordered goal events.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl

from fitba.settings import NORMALIZED_DIR

EVENT_COLUMNS = [
    "fixture_id",
    "season",
    "event_order",
    "minute",
    "extra_minute",
    "team_id",
    "team_name",
    "player_id",
    "player_name",
    "assist_id",
    "assist_name",
    "event_type",
    "detail",
    "comments",
    "is_goal",
    "is_own_goal",
    "is_penalty",
    "is_shootout",
    "is_red_card",
    "is_second_yellow",
    "is_var",
    "ingested_at",
]

LINEUP_COLUMNS = [
    "fixture_id",
    "season",
    "team_id",
    "team_name",
    "formation",
    "coach_id",
    "coach_name",
    "ingested_at",
]


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _event_flags(event_type: str, detail: str, comments: str) -> dict[str, bool]:
    combined = f"{detail} {comments}".casefold()
    second_yellow = event_type == "card" and "second yellow" in combined
    return {
        "is_goal": event_type == "goal" and "missed penalty" not in combined,
        "is_own_goal": event_type == "goal" and "own goal" in combined,
        "is_penalty": "penalty" in combined and "missed penalty" not in combined,
        "is_shootout": "shootout" in combined,
        "is_red_card": event_type == "card" and ("red" in combined or second_yellow),
        "is_second_yellow": second_yellow,
        "is_var": event_type == "var",
    }


def derive_second_yellows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mark a generic red card as a second yellow when two yellows preceded it.

    The provider sometimes sends the dismissal as a plain "Red Card" after two
    separate yellow-card events instead of a "Second Yellow card" detail. The
    law makes that dismissal a second yellow, not a straight red. Explicit
    provider text wins; a red after only one yellow stays a straight red.
    """
    ordered = sorted(
        rows,
        key=lambda row: (
            int(row.get("minute") or 0),
            int(row.get("extra_minute") or 0),
            int(row.get("event_order") or 0),
        ),
    )
    yellows: dict[tuple[Any, Any, Any], int] = {}
    for row in ordered:
        if str(row.get("event_type") or "") != "card":
            continue
        key = (
            row.get("fixture_id"),
            row.get("team_id") or row.get("team_name"),
            row.get("player_id") or row.get("player_name"),
        )
        combined = f"{row.get('detail') or ''} {row.get('comments') or ''}".casefold()
        is_second = bool(row.get("is_second_yellow"))
        is_red = bool(row.get("is_red_card"))
        if is_second:
            row["is_red_card"] = True
            yellows[key] = yellows.get(key, 0) + 1
            continue
        if is_red:
            if yellows.get(key, 0) >= 2:
                row["is_second_yellow"] = True
                row["is_red_card"] = True
            continue
        if "yellow" in combined:
            yellows[key] = yellows.get(key, 0) + 1
    return rows


def normalize_events(
    payload: list[dict[str, Any]],
    *,
    fixture_id: int,
    season: str,
    ingested_at: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event_order, event in enumerate(payload or []):
        time = event.get("time") or {}
        team = event.get("team") or {}
        player = event.get("player") or {}
        assist = event.get("assist") or {}
        event_type = str(event.get("type") or "").casefold()
        detail = str(event.get("detail") or "")
        comments = str(event.get("comments") or "")
        rows.append(
            {
                "fixture_id": fixture_id,
                "season": season,
                "event_order": event_order,
                "minute": _int(time.get("elapsed")),
                "extra_minute": _int(time.get("extra")),
                "team_id": _int(team.get("id")),
                "team_name": str(team.get("name") or "") or None,
                "player_id": _int(player.get("id")),
                "player_name": str(player.get("name") or "") or None,
                "assist_id": _int(assist.get("id")),
                "assist_name": str(assist.get("name") or "") or None,
                "event_type": event_type or None,
                "detail": detail or None,
                "comments": comments or None,
                **_event_flags(event_type, detail, comments),
                "ingested_at": ingested_at,
            }
        )
    return derive_second_yellows(rows)


def normalize_lineups(
    payload: list[dict[str, Any]],
    *,
    fixture_id: int,
    season: str,
    ingested_at: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for block in payload or []:
        team = block.get("team") or {}
        coach = block.get("coach") or {}
        team_id = _int(team.get("id"))
        if team_id is None:
            continue
        rows.append(
            {
                "fixture_id": fixture_id,
                "season": season,
                "team_id": team_id,
                "team_name": str(team.get("name") or "") or None,
                "formation": str(block.get("formation") or "") or None,
                "coach_id": _int(coach.get("id")),
                "coach_name": str(coach.get("name") or "") or None,
                "ingested_at": ingested_at,
            }
        )
    return rows


def _season_dir(season: str) -> Path:
    return NORMALIZED_DIR / "history" / f"season={season}"


def _load(path: Path, columns: list[str]) -> pl.DataFrame:
    if not path.exists():
        return pl.DataFrame({column: [] for column in columns})
    frame = pl.read_parquet(path)
    return frame.select([column for column in columns if column in frame.columns])


def load_events(season: str) -> pl.DataFrame:
    return _load(_season_dir(season) / "events.parquet", EVENT_COLUMNS)


def load_lineups(season: str) -> pl.DataFrame:
    return _load(_season_dir(season) / "lineups.parquet", LINEUP_COLUMNS)


__all__ = [
    "EVENT_COLUMNS",
    "LINEUP_COLUMNS",
    "derive_second_yellows",
    "load_events",
    "load_lineups",
    "normalize_events",
    "normalize_lineups",
]
