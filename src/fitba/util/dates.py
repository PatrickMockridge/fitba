"""Season and date helpers.

A Scottish season starts in July and ends in June. The pipeline derives the
current season from the date rather than hard-coding it.
"""

from __future__ import annotations

import re
from datetime import date

SEASON_RE = re.compile(r"^(\d{4})-(\d{2})$")


def validate_season(season: str) -> str:
    match = SEASON_RE.match(season)
    if not match:
        raise ValueError(f"season must look like 2026-27, got {season!r}")
    start, end = int(match.group(1)), int(match.group(2))
    if end != (start + 1) % 100:
        raise ValueError(f"season end does not follow start: {season!r}")
    return season


def season_start_year(season: str) -> int:
    return int(validate_season(season)[:4])


def season_code(season: str) -> str:
    """2026-27 -> 2627 (football-data.co.uk naming)."""
    year = season_start_year(season)
    return f"{year % 100:02d}{(year + 1) % 100:02d}"


def season_from_date(day: date) -> str:
    start = day.year if day.month >= 7 else day.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def current_season(today: date | None = None) -> str:
    return season_from_date(today or date.today())


def season_bounds(season: str) -> tuple[date, date]:
    start = season_start_year(season)
    return date(start, 7, 1), date(start + 1, 6, 30)


def seasons_between(first: str, last: str) -> list[str]:
    """Inclusive list of seasons, e.g. 2013-14 .. 2015-16."""
    start, end = season_start_year(first), season_start_year(last)
    if end < start:
        raise ValueError(f"last season {last} precedes first {first}")
    out = []
    for year in range(start, end + 1):
        out.append(f"{year}-{(year + 1) % 100:02d}")
    return out


def season_label(season: str) -> str:
    return f"{season_start_year(season)}/{(season_start_year(season) + 1) % 100:02d}"


def previous_season(season: str) -> str:
    year = season_start_year(season) - 1
    return f"{year}-{(year + 1) % 100:02d}"


def date_range_days(start: date, end: date) -> int:
    return (end - start).days


def parse_ddmmyyyy(value: str) -> date:
    return date(int(value[6:10]), int(value[3:5]), int(value[0:2]))


def utc_now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(microsecond=0).isoformat()


def season_age(season: str, today: date | None = None) -> int:
    """Age of a season in years (integer), useful for staleness checks."""
    today = today or date.today()
    return today.year - season_start_year(season)


__all__ = [
    "current_season",
    "date_range_days",
    "parse_ddmmyyyy",
    "previous_season",
    "season_age",
    "season_bounds",
    "season_code",
    "season_from_date",
    "season_label",
    "seasons_between",
    "utc_now_iso",
    "validate_season",
]
