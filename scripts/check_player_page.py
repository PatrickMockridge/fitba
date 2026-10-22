#!/usr/bin/env python3
"""CI guard for the player-page result document.

Validates every published players/<id>.json against the typed model and the
checked-in JSON Schema, and enforces the panel contract: fixed panel order, one
copy of each fact, known-only foot, no loan banner, and no unknown-position
midfield fallback.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fitba.publish.player_page import PlayerPageDocument, player_page_schema

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "web" / "data" / "generated"
PAGES = GENERATED / "players"
SCHEMA = ROOT / "contracts" / "player-page.schema.json"
SQUAD = GENERATED / "squad" / "aberdeen.json"
PANEL_ORDER = ["position", "playing_time", "performance", "records"]
PANEL_IDS = set(PANEL_ORDER)
OLD_DUPLICATE_TITLES = {
    "Role this season",
    "Career role profile",
    "Defensive context",
    "Profile provenance",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
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
    expected_ids = {str(player["player_id"]) for player in squad.get("players", [])}
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

    if errors:
        print("Player-page check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Player-page check passed ({len(files)} documents)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
