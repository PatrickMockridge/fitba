#!/usr/bin/env python3
"""Fail when a published document is not on the current epoch or a source is stale."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fitba.freshness import check_freshness

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "web" / "data" / "generated"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--strict", action="store_true", help="exit non-zero on any failure")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args()
    if not args.data.exists():
        print(f"missing {args.data}; run `uv run fitba publish`")
        return 1
    report = check_freshness(args.data, strict=args.strict)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"freshness {report['status']}: {report.get('fresh_payloads', 0)} fresh, "
            f"{report.get('stale_payloads', 0)} stale, "
            f"{report.get('files_checked', 0)} files"
        )
        for source_id, source in (report.get("sources") or {}).items():
            print(
                f"  {source_id}: {source.get('state')} · "
                f"{source.get('age_hours')}h / {source.get('ttl_hours')}h"
            )
        for error in report.get("errors") or []:
            print(f"  - {error}")
        for warning in report.get("warnings") or []:
            print(f"  warning: {warning}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
