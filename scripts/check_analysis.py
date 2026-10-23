#!/usr/bin/env python3
"""Guard for the season-overview payload and rendered page."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data" / "generated" / "analysis" / "summary.json"
MATCHDAY = ROOT / "web" / "data" / "generated" / "matchday" / "upcoming.json"
OUT = ROOT / "web" / "out" / "analysis" / "index.html"
FORBIDDEN = (
    "will leave",
    "set to leave",
    "sold",
    "sell-high",
    "possible injury",
)
FORBIDDEN_KEYS = {
    "fee",
    "wage",
    "salary",
    "contract_end",
    "contract_expiry",
    "release_clause",
    "value_gbp",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk(value: Any) -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.append((str(key), child))
            found.extend(_walk(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk(child))
    return found


def main() -> int:
    errors: list[str] = []
    if not DATA.exists():
        print(f"missing {DATA}; run `uv run fitba publish`")
        return 1
    data = _load(DATA)
    if data.get("schema_version") != "1.0.0":
        errors.append("analysis summary schema_version is not 1.0.0")
    next_up = data.get("next_up") or []
    if not 0 <= len(next_up) <= 3:
        errors.append("next_up must contain at most three rows")
    if any(row.get("conflict_review") for row in next_up):
        errors.append("next_up contains a conflict-review fixture")
    availability = data.get("availability") or {}
    counts = availability.get("counts") or {}
    official_total = sum(
        int(counts.get(key) or 0)
        for key in ("out_official", "suspended_official", "doubtful", "available", "returned")
    )
    if int(counts.get("active") or 0) != official_total + int(counts.get("unknown") or 0):
        errors.append(
            "availability counts do not sum: "
            f"active={counts.get('active')} official={official_total} "
            f"unknown={counts.get('unknown')}"
        )
    for row in availability.get("inferred") or []:
        if "injur" in str(row.get("note") or "").casefold():
            errors.append("inferred absence must not claim injury")
    for row in availability.get("suspensions") or []:
        if not row.get("competition_id") or not row.get("status"):
            errors.append("suspension row missing competition or status")
        if (
            row.get("rule_verified")
            and row.get("status") == "projected"
            and not row.get("rule_source")
        ):
            errors.append("projected suspension missing rule source")
    aims = data.get("aims") or []
    if len(aims) > 3:
        errors.append("aims must contain at most three rows")
    if not any("Analyst-set" in str(row.get("note") or "") for row in aims):
        errors.append("aims must carry the analyst-set baseline note")
    squad = data.get("squad_decisions") or {}
    if (squad.get("contract") or {}).get("status") != "unavailable":
        errors.append("squad decisions contract status must be unavailable")
    for key, _value in _walk(data):
        if key.casefold() in FORBIDDEN_KEYS:
            errors.append(f"forbidden analysis field {key!r}")
    if MATCHDAY.exists():
        matchday = _load(MATCHDAY)
        current = (matchday.get("fixture") or {}).get("date")
        if current and next_up and str(next_up[0].get("date")) != str(current):
            errors.append("analysis next fixture does not match matchday current fixture")
    if OUT.exists():
        html = OUT.read_text(encoding="utf-8")
        if len(re.findall(r"<h1[ >]", html)) != 1:
            errors.append("analysis page must have exactly one H1")
        lowered = html.casefold()
        for phrase in ("case.claim", "owner view", "chairman frame", "how the record compares"):
            if phrase in lowered:
                errors.append(f"old analysis content still rendered: {phrase!r}")
        for phrase in FORBIDDEN:
            if phrase in lowered:
                errors.append(f"forbidden analysis copy: {phrase!r}")
    if errors:
        print("Analysis check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(
        f"Analysis check passed ({len(next_up)} next fixtures, "
        f"{int(counts.get('active') or 0)} active availability rows)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
