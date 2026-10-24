#!/usr/bin/env python3
"""CI guard for the player-page result document.

Validates every published players/<id>.json against the typed model and the
checked-in JSON Schema, and enforces the panel contract: fixed panel order, one
copy of each fact, known-only foot, no loan banner, and no unknown-position
midfield fallback.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from fitba.publish.player_page import PlayerPageDocument, player_page_schema

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "web" / "data" / "generated"
PAGES = GENERATED / "players"
SCHEMA = ROOT / "contracts" / "player-page.schema.json"
SQUAD = GENERATED / "squad" / "aberdeen.json"
OUT = ROOT / "web" / "out"
PANEL_ORDER = [
    "profile",
    "position",
    "playing_time",
    "performance",
    "availability",
    "recent_matches",
    "records",
]
PANEL_IDS = set(PANEL_ORDER)
OLD_DUPLICATE_TITLES = {
    "Role this season",
    "Career role profile",
    "Defensive context",
    "Profile provenance",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def check_pages() -> list[str]:
    errors: list[str] = []
    squad = _load(SQUAD) if SQUAD.exists() else {}
    current = {
        int(player["player_id"])
        for player in squad.get("players", [])
        if player.get("status") == "squad"
    }
    markers = (
        "player-profile.header",
        "player-profile.rose",
        "player-profile.summary",
        "player-profile.output",
        "player-profile.context",
        "player-profile.coverage",
    )
    pages = sorted((OUT / "players").glob("*/index.html")) if (OUT / "players").exists() else []
    expected_pages = len(squad.get("players", [])) + len(squad.get("excluded_players") or [])
    if len(pages) != expected_pages:
        errors.append("rendered player pages do not match the squad plus retained profiles")
    excluded_ids = {
        int(player["player_id"]) for player in (squad.get("excluded_players") or [])
    }
    for page in pages:
        html = page.read_text(encoding="utf-8")
        player_id = int(page.parent.name)
        if len(re.findall(r"<h1[ >]", html)) != 1:
            errors.append(f"{player_id}: expected exactly one H1")
        if 'data-contract-page="player-profile"' not in html:
            errors.append(f"{player_id}: missing the player-profile contract page marker")
        for marker in markers:
            if f'data-contract="{marker}"' not in html:
                errors.append(f"{player_id}: missing {marker} marker")
        if html.count('data-rose-figure="overall"') != 1:
            errors.append(f"{player_id}: missing the overall rose figure")
        if html.count('data-rose-figure="position"') != 1:
            errors.append(f"{player_id}: missing the position rose figure")
        for phrase in ("Overall profile", "Position profile"):
            if phrase not in html:
                errors.append(f"{player_id}: missing {phrase!r}")
        if player_id in current:
            for phrase in ("Availability and team news", "Recent match log"):
                if phrase not in html:
                    errors.append(f"{player_id}: current squad profile missing {phrase!r}")
        if player_id in excluded_ids and 'data-contract="player-profile.excluded"' not in html:
            errors.append(f"{player_id}: retained profile has no excluded marker")
        if (
            player_id not in excluded_ids
            and 'data-contract="player-profile.excluded"' in html
        ):
            errors.append(f"{player_id}: official profile is marked excluded")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", action="store_true", help="also check the rendered HTML")
    args = parser.parse_args()
    errors: list[str] = []
    if not PAGES.exists():
        print(f"missing {PAGES}; run `uv run fitba publish`")
        return 1
    schema = _load(SCHEMA) if SCHEMA.exists() else None
    if schema is None:
        errors.append(f"missing {SCHEMA}")
    elif schema != player_page_schema():
        errors.append("contracts/player-page.schema.json is stale; regenerate it")

    squad = _load(SQUAD) if SQUAD.exists() else {}
    expected_ids = {
        str(player["player_id"])
        for player in [
            *(squad.get("players") or []),
            *(squad.get("excluded_players") or []),
        ]
    }
    files = sorted(PAGES.glob("*.json"))
    if expected_ids != {path.stem for path in files}:
        errors.append("player-page files do not match the squad player ids")

    for path in files:
        payload = _load(path)
        try:
            document = PlayerPageDocument.model_validate(payload)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{path.name}: schema validation failed: {exc}")
            continue
        pid = document.player_id
        if document.panel_order != PANEL_ORDER:
            errors.append(f"{pid}: panel order is {document.panel_order!r}")
        if set(document.panels) != PANEL_IDS:
            errors.append(f"{pid}: panel set is {sorted(document.panels)!r}")
        for key, panel in document.panels.items():
            if key not in PANEL_IDS:
                errors.append(f"{pid}: unknown panel {key!r}")
            if getattr(panel, "id", None) != key:
                errors.append(f"{pid}: panel id {getattr(panel, 'id', None)!r} != key {key!r}")
            if panel.title in OLD_DUPLICATE_TITLES:
                errors.append(f"{pid}: duplicate legacy panel title {panel.title!r}")
        identity = document.identity
        if identity.preferred_foot.status != "known" and identity.preferred_foot.value is not None:
            errors.append(f"{pid}: unknown foot has a value")
        foot_text = json.dumps(payload).lower()
        for phrase in ("foot unknown", "unknown is not inferred", "loan banner", "loan_banner"):
            if phrase in foot_text:
                errors.append(f"{pid}: forbidden player-page copy {phrase!r}")

        position_data = document.panels["position"].data or {}
        role = position_data.get("role") or {}
        display = position_data.get("display_role") or {}
        performance = document.panels["performance"].data or {}
        if not role.get("code") and not display.get("code") and performance.get("tiles"):
            errors.append(f"{pid}: unknown position has role tiles")
        history_status = position_data.get("history_status")
        if history_status not in {"observed", "partial", "no_role_evidence"}:
            errors.append(f"{pid}: invalid history_status {history_status!r}")
        career = position_data.get("career_role") or {}
        club_history = position_data.get("club_history") or []
        if not career.get("history") and not club_history and history_status != "no_role_evidence":
            errors.append(f"{pid}: no history but status is {history_status!r}")
        if career.get("history") and history_status == "no_role_evidence":
            errors.append(f"{pid}: role history present but status is no_role_evidence")

        profile = document.panels["profile"].data or {}
        if profile.get("tier") not in {"extended", "standard"}:
            errors.append(f"{pid}: invalid profile tier {profile.get('tier')!r}")
        rose = profile.get("rose") or {}
        figures = rose.get("figures") or []
        if [figure.get("id") for figure in figures] != ["overall", "position"]:
            errors.append(f"{pid}: rose figures are not overall, position")
        for figure in figures:
            for axis in figure.get("axes") or []:
                percentile = axis.get("percentile")
                if percentile is not None and not 0 <= float(percentile) <= 100:
                    errors.append(f"{pid}: rose percentile out of range {percentile!r}")
        if rose.get("fallback"):
            if not rose.get("season_used") or rose.get("season_used") == document.season:
                errors.append(f"{pid}: fallback rose has no prior season")
            if rose.get("cohort_season") != rose.get("season_used"):
                errors.append(f"{pid}: fallback cohort season does not match season_used")
            if int(rose.get("minutes") or 0) < int(rose.get("min_minutes") or 180):
                errors.append(f"{pid}: fallback rose is below the minimum minutes")
            if not rose.get("fallback_reason") or not rose.get("fallback_note"):
                errors.append(f"{pid}: fallback rose has no reason/note")
        elif rose.get("status") in {"available", "partial"}:
            if rose.get("season_used") != document.season:
                errors.append(f"{pid}: current rose season does not match the document")
        elif rose.get("status") == "unavailable" and rose.get("reason") == "below_min_minutes":
            if rose.get("fallback_reason") not in {
                "no_prior_premiership_season",
                "prior_cohort_unavailable",
            }:
                errors.append(f"{pid}: no-fallback rose has no explicit fallback reason")
        if document.out_of_squad and "EXCLUDED_FROM_SQUAD" not in {
            warning.code for warning in document.warnings
        }:
            errors.append(f"{pid}: retained profile has no EXCLUDED_FROM_SQUAD warning")
        if (
            document.out_of_squad
            and int(document.panels["profile"].data.get("summary", {}).get("minutes") or 0)
            >= int(rose.get("min_minutes") or 180)
        ):
            errors.append(f"{pid}: excluded profile has current squad minutes")

        availability = document.panels["availability"].data or {}
        if profile.get("current_squad") and not availability:
            errors.append(f"{pid}: current squad has no availability projection")
        recent = document.panels["recent_matches"].data or []
        if (
            profile.get("current_squad")
            and not recent
            and document.panels["recent_matches"].status == "available"
        ):
            errors.append(f"{pid}: available recent-match panel has no rows")

    if args.pages:
        errors.extend(check_pages())

    if errors:
        print("Player-page check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Player-page check passed ({len(files)} documents)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
