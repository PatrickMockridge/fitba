#!/usr/bin/env python3
"""Check the built export for shell-level accessibility basics."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "out"
REQUIRED_PAGES = [
    "index.html",
    "matches/index.html",
    "analysis/index.html",
    "squad/index.html",
    "former-players/index.html",
]


def main() -> int:
    if not OUT.exists():
        print(f"error: missing {OUT}")
        return 1
    errors: list[str] = []
    warnings: list[str] = []
    pages = sorted(OUT.glob("**/*.html"))
    for page in pages:
        text = page.read_text(encoding="utf-8", errors="ignore")
        relative = page.relative_to(OUT)
        if 'href="#main-content"' not in text:
            errors.append(f"{relative}: no skip link")
        if 'id="main-content"' not in text:
            errors.append(f"{relative}: no main landmark id")
        tables = len(re.findall(r"<table\b", text))
        captions = len(re.findall(r"<caption\b", text))
        if tables > captions:
            warnings.append(f"{relative}: {tables} tables, {captions} captions")
    for relative in REQUIRED_PAGES:
        if not (OUT / relative).exists():
            errors.append(f"missing page {relative}")
    for warning in warnings[:20]:
        print(f"warning: {warning}")
    for error in errors[:50]:
        print(f"error: {error}")
    print(
        f"{'FAIL' if errors else 'PASS'} accessibility check: "
        f"{len(pages)} pages, {len(errors)} error(s), {len(warnings)} warning(s)"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
