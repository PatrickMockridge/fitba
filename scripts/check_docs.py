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
    "SUMMARY.md",
    "docs-book.md",
    "player-profile-standard.md",
    "identity.md",
    "specification.md",
    "metrics.md",
    "metric-changes.md",
    "design.md",
    "page-contracts.md",
    "identity-review-2026-10.md",
    "product-strategy.md",
    "matchday.md",
    "analysis.md",
    "fixtures.md",
    "match-scoreboard.md",
    "xg.md",
    "provenance.md",
    "availability.md",
    "needs.md",
    "former-players.md",
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
    "web/app/page.tsx",
    "web/app/layout.tsx",
    "web/app/about/page.tsx",
    "web/app/sources/page.tsx",
    "web/app/methodology/page.tsx",
    "web/app/competitions/page.tsx",
    "web/app/competitions/league-cup/page.tsx",
    "web/app/competitions/scottish-cup/page.tsx",
    "web/app/transfers/page.tsx",
    "web/app/loans/page.tsx",
    "web/app/matchday/page.tsx",
    "web/app/matches/page.tsx",
    "web/app/matches/[fixtureId]/page.tsx",
    "web/app/analysis/page.tsx",
    "web/app/analysis/xg/page.tsx",
    "web/app/recruitment/page.tsx",
    "web/app/scouting/page.tsx",
    "web/app/scouting/search/page.tsx",
    "web/app/scouting/[league]/page.tsx",
    "web/app/scouting/player/[playerId]/page.tsx",
    "web/app/scouting/pool.json/route.ts",
    "web/app/sources/page.tsx",
    "web/app/rumours/page.tsx",
    "web/app/former-players/page.tsx",
    "web/app/squad/page.tsx",
    "web/app/players/[playerId]/page.tsx",
    "web/app/corrections/page.tsx",
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


STALE_COUNTS = [
    "217 of 230",
    "13 unknowns",
    "229 published rows",
    "230 curated rows",
    "−£21.4m",  # noqa: RUF001 - matches the published text exactly
    "14 anchors",
    "103 arrivals and 86 departures",
]


def check_stale_counts() -> list[str]:
    """Volatile register counts belong in the payload/audit, not the docs."""
    errors: list[str] = []
    files = [ROOT / "README.md", *DOCS.glob("*.md")]
    for path in files:
        if path.name == "identity-review-2026-10.md":
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in STALE_COUNTS:
            if phrase in text:
                errors.append(
                    f"{path.relative_to(ROOT)}: stale volatile count {phrase!r}; "
                    "link to the register or /metrics/"
                )
    return errors


def check_identity() -> list[str]:
    errors: list[str] = []
    identity = DOCS / "identity.md"
    contracts = DOCS / "page-contracts.md"
    specification = DOCS / "specification.md"
    if not identity.exists() or not contracts.exists() or not specification.exists():
        return errors
    text = identity.read_text(encoding="utf-8")
    if "Aberdeen FC, without the noise." not in text:
        errors.append("docs/identity.md is missing the identity line")
    if "## Non-negotiables" not in text:
        errors.append("docs/identity.md is missing the Non-negotiables section")
    for target in (
        "specification.md",
        "design.md",
        "page-contracts.md",
        "product-strategy.md",
        "history.md",
    ):
        if f"]({target})" not in text:
            errors.append(f"docs/identity.md does not link {target}")
    if "web/contracts/surfaces.json" not in contracts.read_text(encoding="utf-8"):
        errors.append("docs/page-contracts.md does not reference the contract manifest")
    strategy = (DOCS / "product-strategy.md").read_text(encoding="utf-8")
    if "](identity.md)" not in strategy:
        errors.append("docs/product-strategy.md does not defer to identity.md")
    if "](specification.md" not in strategy:
        errors.append("docs/product-strategy.md does not defer audience to specification.md")
    spec_text = specification.read_text(encoding="utf-8")
    for heading in (
        "## Audience",
        "## Essential, conditional and non-essential",
        "## Number governance",
        "## Change control",
    ):
        if heading not in spec_text:
            errors.append(f"docs/specification.md is missing {heading}")
    if "highly engaged, literate, numerate Aberdeen fans" not in spec_text:
        errors.append("docs/specification.md is missing the canonical audience")
    return errors


def main() -> int:
    errors: list[str] = []
    for name in REQUIRED:
        if not (DOCS / name).exists():
            errors.append(f"missing docs/{name}")
    for path in IN_APP:
        if not (ROOT / path).exists():
            errors.append(f"missing {path}")
    for path in ("AGENTS.md", "CLAUDE.md"):
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
        "web/contracts/surfaces.json",
        "contracts/player-page.schema.json",
        "contracts/matchday.schema.json",
        "contracts/themes.schema.json",
        "contracts/provenance.schema.json",
        "contracts/availability.schema.json",
        "contracts/needs.schema.json",
        "contracts/former-players.schema.json",
        "contracts/former-seasons.schema.json",
        "reference/shape_notes.yaml",
        "reference/role_notes.yaml",
    ):
        if not (ROOT / path).exists():
            errors.append(f"missing {path}")
    errors.extend(check_links())
    errors.extend(check_formats())
    errors.extend(check_identity())
    errors.extend(check_stale_counts())

    if errors:
        print("Documentation check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Documentation check passed ({len(REQUIRED)} docs, {len(IN_APP)} in-app pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
