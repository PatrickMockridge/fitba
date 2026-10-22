#!/usr/bin/env python3
"""Compare two published data directories and report numeric value changes.

The comparison ignores volatile metadata (timestamps, dataset versions,
checksums, byte sizes). It is used to prove that a metric/governance refactor did
not change published values, or to review every intended change before release.

Exit codes: 0 no differences; 1 differences; 2 bad input.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VOLATILE_KEYS = {
    "generated_at",
    "dataset_version",
    "served_generated_at",
    "checksum",
    "checksums",
    "bytes",
    "validation",
    "age_hours",
}


@dataclass(frozen=True)
class Change:
    path: str
    before: Any
    after: Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def walk(value: Any, path: str = "") -> dict[str, Any]:
    """Return numeric leaves keyed by a JSON-like path."""
    leaves: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, item in value.items():
            if key in VOLATILE_KEYS:
                continue
            leaves.update(walk(item, f"{path}.{key}" if path else key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            leaves.update(walk(item, f"{path}[{index}]"))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        leaves[path] = value
    return leaves


def compare(before_dir: Path, after_dir: Path) -> list[Change]:
    before_files = {p.relative_to(before_dir): p for p in before_dir.rglob("*.json")}
    after_files = {p.relative_to(after_dir): p for p in after_dir.rglob("*.json")}
    changes: list[Change] = []

    for relative in sorted(set(before_files) | set(after_files)):
        before_path = before_files.get(relative)
        after_path = after_files.get(relative)
        if before_path is None:
            changes.append(Change(str(relative), None, "added file"))
            continue
        if after_path is None:
            changes.append(Change(str(relative), "removed file", None))
            continue
        before = walk(load_json(before_path))
        after = walk(load_json(after_path))
        for path in sorted(set(before) | set(after)):
            old = before.get(path, "<missing>")
            new = after.get(path, "<missing>")
            if old != new:
                changes.append(Change(f"{relative}:{path}", old, new))
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    if not args.before.is_dir() or not args.after.is_dir():
        print("both --before and --after must be directories", file=sys.stderr)
        return 2

    changes = compare(args.before, args.after)
    if args.json:
        print(
            json.dumps(
                [
                    {"path": change.path, "before": change.before, "after": change.after}
                    for change in changes
                ],
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(f"{len(changes)} changed numeric leaf/leaves")
        for change in changes[: args.limit]:
            print(f"  {change.path}: {change.before!r} -> {change.after!r}")
        if len(changes) > args.limit:
            print(f"  ... {len(changes) - args.limit} more")
    return 1 if changes else 0


if __name__ == "__main__":
    sys.exit(main())
