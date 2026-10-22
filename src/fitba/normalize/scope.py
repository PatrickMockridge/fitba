"""Shared match-scope rules for season and player aggregates.

The public record uses competitive matches (league and cups) by default.
Friendlies are shown separately and never silently mixed into a season total.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

COMPETITIVE = "competitive"
ALL = "all"
FRIENDLY_MARKERS = ("friendly", "friendlies")


def is_friendly_competition(value: Any) -> bool:
    text = str(value or "").casefold()
    if text.startswith("sco:other:friendlies"):
        return True
    return any(marker in text for marker in FRIENDLY_MARKERS)


def is_competitive_row(row: dict[str, Any]) -> bool:
    value = row.get("competition_id") or row.get("competition") or row.get("competition_name") or ""
    return not is_friendly_competition(value)


def filter_scope(rows: Iterable[dict[str, Any]], scope: str = COMPETITIVE) -> list[dict[str, Any]]:
    items = list(rows)
    if scope == ALL:
        return items
    return [row for row in items if is_competitive_row(row)]


__all__ = [
    "ALL",
    "COMPETITIVE",
    "filter_scope",
    "is_competitive_row",
    "is_friendly_competition",
]
