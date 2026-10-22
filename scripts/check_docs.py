#!/usr/bin/env python3
"""CI guard for the documentation set.

Checks that the required documents and in-app pages exist, that internal links
resolve, and that the key competition-format facts have not drifted from config.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

REQUIRED = [
    "README.md",
    "product-strategy.md",
    "matchday.md",
    "themes.md",
    "provenance.md",
    "availability.md",
    "needs.md",
    "transfers.md",
    "squad.md",
    "player-data.md",
    "player-page-spec.md",
    "roles.md",
    "career-roles.md",
    "context/aberdeen-2026-27.md",
    "rumours.md",
    "trading-model.md",
    "competition-formats.md",
    "methodology.md",
    "scouting-method.md",
    "sources.md",
    "architecture.md",
    "roadmap.md",
]

IN_APP = [
    "web/app/about/page.tsx",
    "web/app/sources/page.tsx",
    "web/app/methodology/page.tsx",
    "web/app/competitions/page.tsx",
    "web/app/competitions/league-cup/page.tsx",
    "web/app/competitions/scottish-cup/page.tsx",
    "web/app/transfers/page.tsx",
    "web/app/loans/page.tsx",
    "web/app/matchday/page.tsx",
    "web/app/themes/page.tsx",
    "web/app/recruitment/page.tsx",
    "web/app/scouting/page.tsx",
    "web/app/sources/page.tsx",
    "web/app/rumours/page.tsx",
    "web/app/squad/page.tsx",
    "web/app/players/[playerId]/page.tsx",
]

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _links(path: Path) -> list[str]:
    return LINK_RE.findall(path.read_text(encoding="utf-8"))


def check_links() -> list[str]:
    errors: list[str] = []
    files = [ROOT / "README.md", ROOT / "DATA_LICENSE.md", *DOCS.glob("*.md")]
    for path in files:
        if not path.exists():
            continue
        for target in _links(path):
            target = target.split("#", 1)[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:", "/")):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)}: broken link {target}")
    return errors


def check_formats() -> list[str]:
    errors: list[str] = []
    text = (DOCS / "competition-formats.md").read_text(encoding="utf-8")
    required_phrases = [
        "five European representatives",
        "8 groups of 5",
        "3 best runners-up",
        "137 clubs",
        "136 ties",
        "Fourth Round",
        "16 January 2027",
    ]
    for phrase in required_phrases:
        if phrase not in text:
            errors.append(f"competition-formats.md: missing {phrase!r}")

    cups = yaml.safe_load((ROOT / "config" / "cups.yaml").read_text(encoding="utf-8"))
    cup_ids = {cup["id"] for cup in cups.get("cups", [])}
    for cup_id in ("sco:league-cup", "sco:scottish-cup"):
        if cup_id not in cup_ids:
            errors.append(f"config/cups.yaml: missing {cup_id}")

    leagues = yaml.safe_load((ROOT / "config" / "competitions.yaml").read_text(encoding="utf-8"))
    league_ids = {competition["id"] for competition in leagues.get("competitions", [])}
    if len(league_ids) != 4:
        errors.append(f"config/competitions.yaml: expected 4 leagues, found {len(league_ids)}")

    # The old "top six" claim is only allowed where it is explicitly corrected.
    for path in [ROOT / "README.md", *DOCS.glob("*.md")]:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            lowered = line.lower()
            allowed_context = (
                "not",
                "originally",
                "correction",
                "corrected",
                "stale",
                "bottom six",
                "split",
            )
            if ("top six" in lowered or "top-six" in lowered) and not any(
                word in lowered for word in allowed_context
            ):
                errors.append(f"{path.relative_to(ROOT)}:{number}: stale top-six claim")
    return errors


def main() -> int:
    errors: list[str] = []
    for name in REQUIRED:
        if not (DOCS / name).exists():
            errors.append(f"missing docs/{name}")
    for path in IN_APP:
        if not (ROOT / path).exists():
            errors.append(f"missing {path}")
    for path in (
        "config/roles.yaml",
        "config/matchday.yaml",
        "config/themes.yaml",
        "config/provenance.yaml",
        "config/league_migration.yaml",
        "config/availability.yaml",
        "config/needs.yaml",
        "contracts/player-page.schema.json",
        "contracts/matchday.schema.json",
        "contracts/themes.schema.json",
        "contracts/provenance.schema.json",
        "contracts/availability.schema.json",
        "contracts/needs.schema.json",
        "reference/shape_notes.yaml",
        "reference/role_notes.yaml",
    ):
        if not (ROOT / path).exists():
            errors.append(f"missing {path}")
    errors.extend(check_links())
    errors.extend(check_formats())

    if errors:
        print("Documentation check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Documentation check passed ({len(REQUIRED)} docs, {len(IN_APP)} in-app pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
