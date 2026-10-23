#!/usr/bin/env python3
"""CI guard for the availability ledger and its front-end use."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError

from fitba.publish.availability import AvailabilityDocument, availability_schema

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "web" / "data" / "generated"
DOCUMENT = GENERATED / "availability" / "aberdeen.json"
MATCHDAY = GENERATED / "matchday" / "upcoming.json"
SCHEMA = ROOT / "contracts" / "availability.schema.json"
MANIFEST = GENERATED / "manifest.json"
MAX_FILE_BYTES = 2_000_000
STATUSES = {"out", "doubtful", "suspended", "returned", "available", "unknown"}
ALLOWED_HOSTS = {"afc.co.uk", "www.afc.co.uk"}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _allowed_url(url: str | None) -> bool:
    if not url:
        return False
    host = (urlparse(url).hostname or "").lower()
    return any(host == item or host.endswith("." + item) for item in ALLOWED_HOSTS)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    if not DOCUMENT.exists():
        print(f"missing {DOCUMENT}; run `uv run fitba publish`")
        return 1
    document = _load(DOCUMENT)
    try:
        AvailabilityDocument(**document)
    except ValidationError as error:
        errors.append(f"availability.json does not validate: {error}")
    if SCHEMA.exists():
        if _load(SCHEMA) != availability_schema():
            errors.append(f"{SCHEMA} is stale; regenerate it from the Pydantic model")
    else:
        errors.append(f"missing {SCHEMA}")

    entries = document.get("entries") or []
    player_ids = [entry.get("player_id") for entry in entries if entry.get("player_id")]
    if len(player_ids) != len(set(player_ids)):
        errors.append("duplicate availability player ids")
    counts = {
        status: sum(1 for entry in entries if entry.get("status") == status) for status in STATUSES
    }
    coverage = document.get("coverage") or {}
    for key in ("out", "suspended", "doubtful", "returned", "unknown"):
        if int(coverage.get(key) or 0) != counts[key]:
            errors.append(f"coverage {key} {coverage.get(key)} != entries {counts[key]}")
    known = sum(counts[status] for status in STATUSES - {"unknown"})
    if int(coverage.get("known") or 0) != known:
        errors.append(f"coverage known {coverage.get('known')} != entries {known}")
    provider = coverage.get("provider_snapshot") or {}
    if provider.get("status") not in {"available", "empty", "unavailable"}:
        errors.append(f"invalid provider snapshot status {provider.get('status')!r}")

    for entry in entries:
        status = entry.get("status")
        if status not in STATUSES:
            errors.append(f"invalid availability status {status!r}")
        if status in {"out", "suspended", "doubtful", "returned", "available"}:
            if not _allowed_url(entry.get("source_url")):
                errors.append(
                    f"{entry.get('player_name')}: {status} without an allowed AFC source URL"
                )
            if not entry.get("verified_at"):
                errors.append(f"{entry.get('player_name')}: {status} without verified_at")
            if entry.get("source_id") == "api_football" and status in {
                "available",
                "returned",
                "suspended",
            }:
                errors.append(f"{entry.get('player_name')}: provider cannot set {status}")
        if entry.get("stale") and status != "unknown":
            errors.append(f"{entry.get('player_name')}: stale entry is not unknown")
        if entry.get("conflict") and status in {"out", "suspended"}:
            warnings.append(f"{entry.get('player_name')}: conflict with an out/suspended status")

    if MATCHDAY.exists():
        matchday = _load(MATCHDAY)
        lineup = ((matchday.get("predicted_lineups") or {}).get("aberdeen")) or {}
        selected = {
            player.get("player_id")
            for player in lineup.get("players") or []
            if player.get("player_id") is not None
        }
        excluded = {
            entry["player_id"]
            for entry in entries
            if entry.get("status") in {"out", "suspended"} and entry.get("player_id") is not None
        }
        overlap = selected & excluded
        if overlap:
            errors.append(f"predicted XI contains out/suspended players {sorted(overlap)}")
        for player in lineup.get("players") or []:
            if (
                player.get("availability_status") == "doubtful"
                and player.get("confidence") == "high"
            ):
                errors.append(f"{player.get('name')}: doubtful player retains high confidence")
        availability = lineup.get("availability") or {}
        squad_known = sum(
            1
            for entry in entries
            if entry.get("in_squad", True) and entry.get("status") != "unknown"
        )
        if availability and int(availability.get("known") or 0) != squad_known:
            warnings.append(
                "matchday availability known count differs from the published squad entries"
            )

    if DOCUMENT.stat().st_size > MAX_FILE_BYTES:
        errors.append(f"{DOCUMENT} exceeds the {MAX_FILE_BYTES} byte cap")
    if MANIFEST.exists():
        manifest = _load(MANIFEST)
        files = {row.get("path"): row for row in manifest.get("files") or []}
        info = files.get("availability/aberdeen.json")
        if info is None:
            errors.append("manifest missing availability/aberdeen.json")
        else:
            digest = "sha256:" + hashlib.sha256(DOCUMENT.read_bytes()).hexdigest()
            if info.get("checksum") != digest:
                errors.append("manifest checksum does not match availability/aberdeen.json")
        marts = {mart.get("id") for mart in manifest.get("marts") or []}
        if "availability.sco:aberdeen" not in marts:
            errors.append("manifest missing availability.sco:aberdeen mart")
        if "availability" not in (manifest.get("coverage") or {}):
            errors.append("manifest coverage missing availability")

    for error in errors:
        print(f"  - {error}")
    for warning in warnings:
        print(f"  ! {warning}")
    if errors:
        print(f"Availability check failed ({len(errors)} error(s))")
        return 1
    print(
        "Availability check passed "
        f"({len(entries)} entries, {known} known, "
        f"{counts['unknown']} unknown)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
