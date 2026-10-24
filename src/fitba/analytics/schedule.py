"""One next-fixture selector for matchday, analysis, club and fixtures.

A cached matchday snapshot may be older than the live schedule. The schedule
is the source of truth; the snapshot is a cache. Conflict-review rows are kept
in the record but are not presented as confirmed upcoming fixtures.
"""

from __future__ import annotations

from typing import Any


def _sort_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get("date") or ""), str(row.get("kickoff") or ""))


def upcoming_fixtures(
    schedule: list[dict[str, Any]],
    *,
    limit: int | None = None,
    exclude_conflict: bool = True,
    exclude_friendly: bool = True,
) -> list[dict[str, Any]]:
    """Return scheduled fixtures in chronological order."""
    rows = [
        row
        for row in schedule
        if row.get("status") == "scheduled"
        and not (exclude_conflict and row.get("conflict_review"))
        and not (exclude_friendly and row.get("is_friendly"))
    ]
    rows.sort(key=_sort_key)
    return rows[:limit] if limit is not None else rows


def next_fixture(
    schedule: list[dict[str, Any]],
    *,
    exclude_conflict: bool = True,
) -> dict[str, Any] | None:
    rows = upcoming_fixtures(
        schedule,
        limit=1,
        exclude_conflict=exclude_conflict,
    )
    return rows[0] if rows else None


__all__ = ["next_fixture", "upcoming_fixtures"]
