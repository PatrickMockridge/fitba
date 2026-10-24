#!/usr/bin/env python3
"""Decide whether a finished Aberdeen fixture still needs a data update.

The gate is result-aware: a finish is due only when the canonical record or the
published fixture index has no result for it. A publish that merely re-stamps
timestamps therefore cannot mark a missing result as up to date.
"""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime

from fitba.update import refresh_due


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
    due = refresh_due(now=now)
    value = "true" if due else "false"
    print(f"matchday refresh due: {value}")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"update={value}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
