#!/usr/bin/env python3
"""CI guard for the squad-needs document."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from fitba.publish.needs import NeedsDocument, needs_schema

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "web" / "data" / "generated"
DOCUMENT = GENERATED / "needs" / "aberdeen.json"
THEMES = GENERATED / "themes" / "aberdeen.json"
SQUAD = GENERATED / "squad" / "aberdeen.json"
SCHEMA = ROOT / "contracts" / "needs.schema.json"
MANIFEST = GENERATED / "manifest.json"
SEARCH = GENERATED / "search-index.json"
MAX_FILE_BYTES = 2_000_000

FAMILIES = {"GK", "CB", "FB/WB", "MID", "AM/WM", "W", "ST"}
CATEGORIES = {"cover", "replace", "strengthen", "monitor", "none", "unknown"}
URGENCIES = {"critical", "high", "medium", "low", "none"}
CONFIDENCE = {"high", "medium", "low", "unknown"}
MARKETS = {"loan", "permanent", "free", "none"}
BLAME = (
    "must sign",
    "should sign",
    "data says sign",
    "doesn't trust",
    "to blame",
    "at fault",
)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        output = []
        for key, item in value.items():
            output.append(str(key))
            output.extend(_strings(item))
        return output
    if isinstance(value, list):
        output = []
        for item in value:
            output.extend(_strings(item))
        return output
    return []


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    if not DOCUMENT.exists():
        print(f"missing {DOCUMENT}; run `uv run fitba publish`")
        return 1
    document = _load(DOCUMENT)
    try:
        NeedsDocument(**document)
    except ValidationError as error:
        errors.append(f"needs.json does not validate: {error}")
    if SCHEMA.exists():
        if _load(SCHEMA) != needs_schema():
            errors.append(f"{SCHEMA} is stale; regenerate it from the Pydantic model")
    else:
        errors.append(f"missing {SCHEMA}")

    families = document.get("families") or []
    names = [row.get("family") for row in families]
    if len(names) != len(set(names)):
        errors.append("duplicate needs families")
    if set(names) != FAMILIES:
        errors.append(f"needs families {sorted(set(names))} != {sorted(FAMILIES)}")
    if sorted(row.get("priority") for row in families) != list(range(1, len(families) + 1)):
        errors.append("need priorities must be 1..7")
    squad = _load(SQUAD) if SQUAD.exists() else {}
    squad_ids = {
        int(player["player_id"])
        for player in squad.get("players", [])
        if player.get("player_id") is not None
    }
    for family in families:
        family_name = family.get("family")
        category = family.get("category")
        urgency = family.get("urgency")
        if category not in CATEGORIES:
            errors.append(f"{family_name}: invalid category {category!r}")
        if urgency not in URGENCIES:
            errors.append(f"{family_name}: invalid urgency {urgency!r}")
        if family.get("confidence") not in CONFIDENCE:
            errors.append(f"{family_name}: invalid confidence")
        measured = family.get("measured") or {}
        shortfall = measured.get("projected_shortfall")
        depth_gap = measured.get("depth_gap")
        availability_risk = measured.get("availability_risk")
        if category == "cover" and not (
            (availability_risk or 0) > 0 and ((shortfall or 0) >= 1 or (depth_gap or 0) >= 0.5)
        ):
            errors.append(f"{family_name}: cover without a depth/availability trigger")
        if category == "replace":
            evidence = (family.get("outgoing_risk") or {}).get("evidence") or []
            if not evidence or not any(
                item.get("type") == "active_outgoing_rumour" for item in evidence
            ):
                errors.append(f"{family_name}: replace without active outgoing evidence")
            for item in evidence:
                if item.get("type") == "active_outgoing_rumour" and item.get(
                    "affiliation"
                ) not in {None, "current_squad"}:
                    errors.append(
                        f"{family_name}: replace evidence is not a current-squad player"
                    )
        if category == "unknown" and measured.get("status") != "unavailable":
            errors.append(f"{family_name}: unknown category with measured depth")
        route = family.get("market_route") or {}
        if route.get("primary") not in MARKETS:
            errors.append(f"{family_name}: invalid market route")
        if route.get("fee_expectation") != "unknown":
            errors.append(f"{family_name}: fee expectation must be unknown")
        if "targets" in family:
            errors.append(f"{family_name}: targets are not allowed")
        for player in family.get("players") or []:
            player_id = player.get("player_id")
            if player_id is not None and int(player_id) not in squad_ids:
                errors.append(f"{family_name}: player {player_id} is not in the current squad")
        roster = family.get("roster_space") or {}
        if roster.get("status") == "requires_outgoing" and not (
            int(roster.get("current") or 0) >= int(roster.get("max_squad") or 0)
        ):
            errors.append(f"{family_name}: requires_outgoing without a full roster")

    for text in _strings(document):
        lowered = text.casefold()
        for phrase in BLAME:
            if phrase in lowered:
                errors.append(f"blame or target language {phrase!r}")

    if DOCUMENT.stat().st_size > MAX_FILE_BYTES:
        errors.append(f"{DOCUMENT} exceeds the {MAX_FILE_BYTES} byte cap")
    if MANIFEST.exists():
        manifest = _load(MANIFEST)
        files = {row.get("path"): row for row in manifest.get("files") or []}
        info = files.get("needs/aberdeen.json")
        if info is None:
            errors.append("manifest missing needs/aberdeen.json")
        else:
            digest = "sha256:" + hashlib.sha256(DOCUMENT.read_bytes()).hexdigest()
            if info.get("checksum") != digest:
                errors.append("manifest checksum does not match needs/aberdeen.json")
        marts = {mart.get("id") for mart in manifest.get("marts") or []}
        if "needs.sco:aberdeen" not in marts:
            errors.append("manifest missing needs.sco:aberdeen mart")
        if "needs" not in (manifest.get("coverage") or {}):
            errors.append("manifest coverage missing needs")
    if SEARCH.exists():
        search = _load(SEARCH)
        if not any(entry.get("href") == "/recruitment/#squad-needs" for entry in search):
            errors.append("search index missing the squad-needs anchor")
        if not any(entry.get("href") == "/scouting/#priority-profiles" for entry in search):
            errors.append("search index missing the priority-profiles anchor")

    for error in errors:
        print(f"  - {error}")
    for warning in warnings:
        print(f"  ! {warning}")
    if errors:
        print(f"Needs check failed ({len(errors)} error(s))")
        return 1
    counts = (document.get("summary") or {}).get("counts") or {}
    print(
        "Needs check passed "
        f"({len(families)} families, {counts.get('cover', 0)} cover, "
        f"{counts.get('strengthen', 0)} strengthen, {counts.get('replace', 0)} replace)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
