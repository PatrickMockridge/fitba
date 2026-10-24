#!/usr/bin/env python3
"""Fail when two published surfaces disagree about the same fact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fitba.metrics.audit import load_corpus
from fitba.metrics.consistency import run_consistency

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
    results = run_consistency(load_corpus(args.data), root=args.data)
    failures = [result for result in results if result.status != "pass"]
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "id": result.id,
                        "description": result.description,
                        "status": result.status,
                        "rows_checked": result.rows_checked,
                        "fields_checked": result.fields_checked,
                        "errors": result.errors,
                        "payloads": result.payloads,
                    }
                    for result in results
                ],
                indent=2,
            )
        )
    else:
        for result in results:
            marker = "PASS" if result.status == "pass" else "FAIL"
            print(
                f"{marker} {result.id}: {result.description} "
                f"({result.rows_checked} rows, {result.fields_checked} fields)"
            )
            for error in result.errors:
                print(f"  - {error}")
        print(
            f"Consistency check: {len(results) - len(failures)} passed, "
            f"{len(failures)} failed"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
