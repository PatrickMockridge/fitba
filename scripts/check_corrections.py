#!/usr/bin/env python3
"""Validate the public correction log and, if built, its page markers."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data" / "corrections.json"
PAGE = ROOT / "web" / "out" / "corrections" / "index.html"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STATUSES = {"fixed", "reviewing", "withdrawn"}


def main() -> int:
    errors: list[str] = []
    if not DATA.exists():
        print(f"error: missing {DATA}")
        return 1
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    if not DATE_RE.match(str(payload.get("last_reviewed") or "")):
        errors.append("last_reviewed must be YYYY-MM-DD")
    contact = str(payload.get("contact_url") or "")
    if not contact.startswith("https://"):
        errors.append("contact_url must be https")
    entries = payload.get("entries") or []
    if not entries:
        errors.append("correction log is empty")
    seen: set[tuple[str, str, str]] = set()
    for index, entry in enumerate(entries):
        for field in ("date", "page", "claim", "correction", "status"):
            if not str(entry.get(field) or "").strip():
                errors.append(f"entry {index}: missing {field}")
        if entry.get("date") and not DATE_RE.match(str(entry["date"])):
            errors.append(f"entry {index}: date must be YYYY-MM-DD")
        if entry.get("status") not in STATUSES:
            errors.append(f"entry {index}: invalid status {entry.get('status')!r}")
        key = (
            str(entry.get("date")),
            str(entry.get("page")),
            str(entry.get("claim")),
        )
        if key in seen:
            errors.append(f"entry {index}: duplicate correction")
        seen.add(key)
        try:
            if entry.get("date") and date.fromisoformat(str(entry["date"])) > date.today():
                errors.append(f"entry {index}: correction date is in the future")
        except ValueError:
            errors.append(f"entry {index}: invalid date")
    if PAGE.exists():
        page = PAGE.read_text(encoding="utf-8")
        for marker in ("corrections.policy", "corrections.contact", "corrections.log"):
            if f'data-contract="{marker}"' not in page:
                errors.append(f"built page is missing {marker}")
    for error in errors:
        print(f"error: {error}")
    print(
        f"{'FAIL' if errors else 'PASS'} corrections check: "
        f"{len(entries)} entries, {len(errors)} error(s)"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
