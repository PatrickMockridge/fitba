#!/usr/bin/env python3
"""Decide whether the published data is older than a finished Aberdeen fixture.

The matchday check runs every two hours. It reads the committed fixture
schedule and manifest and returns ``true`` only when a scheduled Aberdeen
fixture has finished and the published data predates that finish. That lets the
workflow dispatch the full daily update after a game without running the data
pipeline on empty checks.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "web" / "data" / "generated" / "fixtures" / "index.json"
MANIFEST = ROOT / "web" / "data" / "generated" / "manifest.json"
LONDON = ZoneInfo("Europe/London")

# A normal match ends within two hours; extra time and penalties can take
# closer to three. The next even-hour check makes the update effectively
# post-match without guessing the exact final whistle.
FINISH_BUFFER = timedelta(hours=3)


def _load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _parse_generated(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_kickoff(row: dict[str, Any]) -> datetime | None:
    date = str(row.get("date") or "").strip()
    kickoff = str(row.get("kickoff") or "").strip()
    if not date or not kickoff:
        return None
    try:
        local = datetime.fromisoformat(f"{date}T{kickoff}:00")
    except ValueError:
        return None
    return local.replace(tzinfo=LONDON)


def refresh_due(
    schedule: dict[str, Any],
    manifest: dict[str, Any],
    now: datetime,
) -> bool:
    """Return True when a finished fixture is newer than the published data."""
    generated = _parse_generated(manifest.get("generated_at"))
    for row in schedule.get("scheduled") or []:
        if not isinstance(row, dict):
            continue
        kickoff = _parse_kickoff(row)
        if kickoff is None:
            continue
        finished = kickoff + FINISH_BUFFER
        if now < finished:
            continue
        if generated is None or generated < finished:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--now",
        help="Override the current time (ISO 8601) for a manual check.",
    )
    args = parser.parse_args()
    now = (
        datetime.fromisoformat(args.now.replace("Z", "+00:00")).astimezone(UTC)
        if args.now
        else datetime.now(UTC)
    )
    due = refresh_due(_load(FIXTURES), _load(MANIFEST), now)
    value = "true" if due else "false"
    print(f"matchday refresh due: {value}")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"update={value}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
