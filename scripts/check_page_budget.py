#!/usr/bin/env python3
"""Enforce browser payload budgets on generated data and the static export.

A budget is a performance threshold, not a content cap: a breach is fixed by
sharding or lazy loading, never by deleting evidence. Page budgets are measured
on the HTML the browser receives for a route; JSON budgets are measured on the
generated payload and on the copy served under the static export.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "web-budgets.yaml"
DEFAULT_DATA = ROOT / "web" / "data" / "generated"
DEFAULT_OUT = ROOT / "web" / "out"


def _load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}


def _relative_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file())


def _check_pattern(
    root: Path,
    pattern: str,
    budget: int,
    *,
    label: str,
    errors: list[str],
) -> int:
    matches = [
        path
        for path in _relative_files(root)
        if fnmatch.fnmatch(path.relative_to(root).as_posix(), pattern)
    ]
    if not matches:
        errors.append(f"{label}: no file matches {pattern!r}")
        return 0
    for path in matches:
        size = path.stat().st_size
        if size > budget:
            relative = path.relative_to(root).as_posix()
            errors.append(
                f"{label}: {relative} is {size} bytes, budget {budget}; "
                "shard or lazy-load, do not delete evidence"
            )
    return len(matches)


def check(data: Path = DEFAULT_DATA, out: Path | None = None) -> list[str]:
    config = _load_config()
    errors: list[str] = []

    json_budgets = config.get("json") or {}
    for pattern, budget in json_budgets.items():
        _check_pattern(data, str(pattern), int(budget), label="json", errors=errors)

    if out is not None:
        page_budgets = config.get("pages") or {}
        for route, budget in page_budgets.items():
            route = str(route)
            relative = route.strip("/")
            page = out / relative / "index.html" if relative else out / "index.html"
            if not page.exists():
                errors.append(f"page: no built HTML for {route}")
                continue
            size = page.stat().st_size
            if size > int(budget):
                errors.append(
                    f"page: {route} is {size} bytes, budget {int(budget)}; "
                    "shard or lazy-load, do not delete evidence"
                )
        built_budgets = config.get("built_json") or {}
        for pattern, budget in built_budgets.items():
            _check_pattern(out, str(pattern), int(budget), label="built_json", errors=errors)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    out = args.out if args.out is not None else None
    errors = check(args.data, out)
    if args.json:
        print(json.dumps({"status": "pass" if not errors else "fail", "errors": errors}, indent=2))
    else:
        for error in errors:
            print(f"error: {error}")
        print(f"{'PASS' if not errors else 'FAIL'} page budget check: {len(errors)} error(s)")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
