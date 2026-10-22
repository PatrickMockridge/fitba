#!/usr/bin/env python3
"""CI guard for the Cormack-era historical record.

Structural problems fail. Missing backfill, partial historical transfers and a
missing staff role are warnings: the record is report-only on coverage.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fitba.publish.history import history_index_schema, history_season_schema
from fitba.settings import (
    history_era,
    history_honours,
    history_policy,
    history_seasons,
    history_staff,
)
from fitba.validate.history import validate_published, validate_reference

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "web" / "data" / "generated"
INDEX = GENERATED / "history" / "aberdeen.json"
SEASON_DIR = GENERATED / "history" / "seasons"
SCHEMAS = {
    "index": ROOT / "contracts" / "history-index.schema.json",
    "season": ROOT / "contracts" / "history-season.schema.json",
}
CLUB = GENERATED / "clubs" / "aberdeen.json"
TRANSFERS = GENERATED / "transfers" / "aberdeen.json"
MANIFEST = GENERATED / "manifest.json"
MAX_FILE_BYTES = 2_000_000


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> Any:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    if not INDEX.exists():
        print(f"missing {INDEX}; run `uv run fitba publish`")
        return 1
    index = _load(INDEX)
    season_docs = (
        {path.stem: _load(path) for path in sorted(SEASON_DIR.glob("*.json"))}
        if SEASON_DIR.exists()
        else {}
    )
    if not season_docs:
        errors.append("no history season documents")
    club = _load(CLUB) if CLUB.exists() else {}
    transfers = _load(TRANSFERS) if TRANSFERS.exists() else {}
    policy = history_policy()
    reference_errors, reference_warnings = validate_reference(
        policy=policy,
        era=history_era(),
        staff=history_staff(),
        honours=history_honours(),
        seasons=history_seasons(),
        transfer_rows=transfers.get("transfers") or [],
    )
    errors.extend(reference_errors)
    warnings.extend(reference_warnings)
    published_errors, published_warnings = validate_published(
        index=index,
        season_docs=season_docs,
        club_history=club.get("history") or [],
        transfer_payload=transfers,
        policy=policy,
    )
    errors.extend(published_errors)
    warnings.extend(published_warnings)

    for name, path in SCHEMAS.items():
        if not path.exists():
            errors.append(f"missing schema {path}")
            continue
        checked_in = _load(path)
        generated = history_index_schema() if name == "index" else history_season_schema()
        if checked_in != generated:
            errors.append(f"{path} is stale; regenerate it from the Pydantic model")

    for path in [INDEX, *sorted(SEASON_DIR.glob("*.json"))]:
        if path.exists() and path.stat().st_size > MAX_FILE_BYTES:
            errors.append(f"{path} exceeds the {MAX_FILE_BYTES} byte cap")
    if MANIFEST.exists():
        manifest = _load(MANIFEST)
        files = {row.get("path"): row for row in manifest.get("files") or []}
        for relative in [
            "history/aberdeen.json",
            *[f"history/seasons/{season}.json" for season in season_docs],
        ]:
            if relative not in files:
                errors.append(f"manifest missing {relative}")
        for mart in manifest.get("marts") or []:
            if str(mart.get("id", "")).startswith("history.") and not mart.get("checksum"):
                errors.append(f"history mart {mart.get('id')} has no checksum")

    for error in errors:
        print(f"  - {error}")
    for warning in warnings:
        print(f"  ! {warning}")
    if errors:
        print(f"History publication check failed ({len(errors)} error(s))")
        return 1
    print(
        "History publication check passed "
        f"({len(season_docs)} seasons, {len(index.get('staff', []))} people, "
        f"{len(index.get('honours', []))} honours)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
