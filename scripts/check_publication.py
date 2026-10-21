#!/usr/bin/env python3
"""CI guard: the public data directory contains only derived, bounded JSON."""

from __future__ import annotations

import subprocess
import sys

from fitba.settings import WEB_DATA_DIR
from fitba.validate.checks import validate_published


def main() -> int:
    checks = validate_published(WEB_DATA_DIR)
    failed = False
    for check in checks:
        print(f"{check.level:<7} {check.name}: {check.message}")
        if check.failed:
            failed = True

    tracked = subprocess.run(
        ["git", "ls-files", "data", ".cache"],
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if tracked:
        print("error   repository tracks raw data:")
        print(tracked)
        failed = True
    else:
        print("ok      no raw data or cache files are tracked")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
