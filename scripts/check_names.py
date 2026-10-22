#!/usr/bin/env python3
"""Guard against non-canonical club-name capitalisation in published data.

The pipeline resolves Scottish clubs through reference/teams.yaml and
title-cases unresolved provisional clubs. This check catches the common
regressions: all-caps "ST" before Johnstone/Mirren, lower-case place names,
and "FC ST." spellings.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "web" / "data" / "generated"
REFERENCE_FILES = [
    ROOT / "reference" / "transfers.yaml",
    ROOT / "reference" / "transfers.candidates.yaml",
    ROOT / "reference" / "transfers.candidates.history.yaml",
    ROOT / "reference" / "history" / "markets.yaml",
]
BAD_PATTERNS = [
    re.compile(r"\bST\s+Johnstone\b"),
    re.compile(r"\bST\s+Mirren\b"),
    re.compile(r"\bSt\.\s+(?:Johnstone|Mirren)\b"),
    re.compile(r"\bSt\s+johnstone\b"),
    re.compile(r"\bSt\s+mirren\b"),
    re.compile(r"\bFC\s+ST\."),
    re.compile(r"\bST\.\s+(?:Johnstone|Mirren)\b"),
    re.compile(r"\bADO\s+den\s+Haag\b"),
    re.compile(r"\bFree\s+Agent\b"),
    re.compile(r"\bFriendlies\s+Clubs\b"),
    re.compile(r"\bRops\b"),
]


def _walk(value: Any, path: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.extend(_walk(child, f"{path}.{key}" if path else str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_walk(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        found.append((path, value))
    return found


def main() -> int:
    errors: list[str] = []
    checked = 0
    for path in sorted(GENERATED.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path}: invalid JSON ({exc})")
            continue
        for location, value in _walk(payload):
            checked += 1
            for pattern in BAD_PATTERNS:
                if pattern.search(value):
                    errors.append(f"{path.relative_to(ROOT)}:{location}: {value!r}")
    for path in REFERENCE_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in BAD_PATTERNS:
            for match in pattern.finditer(text):
                errors.append(
                    f"{path.relative_to(ROOT)}: non-canonical club name {match.group(0)!r}"
                )
    for error in errors:
        print(f"  - {error}")
    if errors:
        print(f"Club-name check failed ({len(errors)} error(s))")
        return 1
    print(f"Club-name check passed ({checked} published strings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
