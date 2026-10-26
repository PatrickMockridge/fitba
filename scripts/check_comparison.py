#!/usr/bin/env python3
"""Validate the reviewed current-squad comparison allowlist.

The crosswalk is identity and cohort metadata only. Every row must match the
published squad and scouting squad profile, and no fee, wage or contract field
may enter it.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data" / "generated"
CROSSWALK = ROOT / "reference" / "comparison_crosswalk.yaml"
MODEL = ROOT / "config" / "scouting" / "model.yaml"
ALLOWED = {
    "player_id",
    "player_key",
    "league_slug",
    "role_family",
    "cohort_basis",
    "reviewed_by",
    "reviewed_at",
    "notes",
}
FORBIDDEN = re.compile(r"fee|wage|salary|contract|value|release", re.IGNORECASE)
PLAYER_KEY = re.compile(r"^api:player:\d+$")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def check() -> list[str]:
    errors: list[str] = []
    document_path = DATA / "scouting" / "comparison.json"
    if not document_path.exists():
        return ["missing scouting/comparison.json"]
    document = _load(document_path)
    config = yaml.safe_load(CROSSWALK.read_text(encoding="utf-8")) or {}
    model = yaml.safe_load(MODEL.read_text(encoding="utf-8")) or {}
    minimum = int((model.get("pool") or {}).get("min_cohort") or 15)
    by_family = (model.get("pool") or {}).get("min_cohort_by_family") or {}
    squad = _load(DATA / "squad" / "aberdeen.json")
    hub = _load(DATA / "scouting" / "aberdeen.json")
    squad_ids = {
        int(player["player_id"])
        for player in squad.get("players") or []
        if player.get("player_id") is not None
    }
    profiles = {
        int(row["player_id"]): row
        for row in hub.get("squad") or []
        if row.get("player_id") is not None
    }
    rows = document.get("players") or []
    configured = config.get("players") or []
    if len(rows) != len(configured):
        errors.append("published rows do not match reference/comparison_crosswalk.yaml")
    if rows and document.get("state") != "available":
        errors.append("rows exist but state is not available")
    if not rows and document.get("state") != "not_reviewed":
        errors.append("an empty allowlist must be state not_reviewed")
    seen: set[int] = set()
    for row in rows:
        extra = set(row) - ALLOWED
        if extra:
            errors.append(f"{row.get('player_id')}: unexpected fields {sorted(extra)}")
        for key in row:
            if FORBIDDEN.search(str(key)):
                errors.append(f"{row.get('player_id')}: forbidden field {key}")
        player_id = int(row.get("player_id") or 0)
        if not player_id or player_id in seen:
            errors.append(f"duplicate or missing player id {player_id}")
        seen.add(player_id)
        if str(row.get("player_key") or "") != f"api:player:{player_id}":
            errors.append(f"{player_id}: player_key does not match player id")
        if not PLAYER_KEY.match(str(row.get("player_key") or "")):
            errors.append(f"{player_id}: invalid player_key")
        if str(row.get("league_slug") or "") != "sco-premiership":
            errors.append(f"{player_id}: league must be sco-premiership")
        if player_id not in squad_ids:
            errors.append(f"{player_id}: not in the official squad payload")
        profile = profiles.get(player_id)
        if profile is None:
            errors.append(f"{player_id}: no published scouting squad row")
            continue
        if str(profile.get("role_family") or "") != str(row.get("role_family") or ""):
            errors.append(f"{player_id}: role family does not match the published row")
        if profile.get("rating_percentile") is None:
            errors.append(f"{player_id}: no published percentile")
        cohort_n = (profile.get("cohort") or {}).get("n")
        family_minimum = int(by_family.get(str(row.get("role_family"))) or minimum)
        if cohort_n is None or int(cohort_n) < family_minimum:
            errors.append(f"{player_id}: published cohort is below the model minimum")
        if not str(row.get("reviewed_by") or "").strip():
            errors.append(f"{player_id}: no reviewer")
        if not str(row.get("reviewed_at") or "").startswith("20"):
            errors.append(f"{player_id}: no review date")
    return errors


def main() -> int:
    errors = check()
    for error in errors:
        print(f"error: {error}")
    print(
        f"{'PASS' if not errors else 'FAIL'} comparison check: "
        f"{len(errors)} error(s)"
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
