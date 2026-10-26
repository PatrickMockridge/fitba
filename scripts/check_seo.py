#!/usr/bin/env python3
"""Check the built static export for canonical, Open Graph and sitemap basics."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "out"


def main() -> int:
    if not OUT.exists():
        print(f"error: missing {OUT}")
        return 1
    errors: list[str] = []
    pages = sorted(OUT.glob("**/*.html"))
    if not pages:
        print("error: no built pages")
        return 1
    titles: dict[str, str] = {}
    for page in pages:
        text = page.read_text(encoding="utf-8", errors="ignore")
        relative = page.relative_to(OUT)
        if str(relative).startswith(("_not-found/", "404/")) or str(relative) == "404.html":
            continue
        if 'rel="canonical"' not in text:
            errors.append(f"{relative}: no canonical link")
        if 'property="og:title"' not in text:
            errors.append(f"{relative}: no og:title")
        if 'property="og:description"' not in text:
            errors.append(f"{relative}: no og:description")
        match = re.search(r"<title>(.*?)</title>", text, re.DOTALL)
        if not match or not match.group(1).strip():
            errors.append(f"{relative}: no title")
        else:
            title = match.group(1).strip()
            if title in titles:
                errors.append(f"{relative}: duplicate title with {titles[title]}")
            else:
                titles[title] = str(relative)
    sitemap = OUT / "sitemap.xml"
    if not sitemap.exists():
        errors.append("no sitemap.xml")
    else:
        sitemap_text = sitemap.read_text(encoding="utf-8")
        for required in (
            "/matchday/",
            "/matches/",
            "/analysis/",
            "/former-players/",
            "/corrections/",
            "/search/",
            "/claims/",
        ):
            if required not in sitemap_text:
                errors.append(f"sitemap is missing {required}")
    if not (OUT / "icon.svg").exists():
        errors.append("no icon.svg")
    for error in errors[:50]:
        print(f"error: {error}")
    print(f"{'FAIL' if errors else 'PASS'} SEO check: {len(pages)} pages, {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
