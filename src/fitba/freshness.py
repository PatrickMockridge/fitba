"""Source freshness discovery and the published-corpus freshness guard.

The manifest is the update report. This module answers two questions:

1. How old is each source snapshot the update consumes?
2. Does every published document belong to the current dataset epoch, or say
   explicitly that it is stale and why?

Freshness is not inferred from a page timestamp. A source is ``fresh`` only
inside its configured TTL, ``stale`` after it, and ``missing`` when no snapshot
exists. Required sources must be fresh before publish; optional sources may be
stale but must be listed in ``manifest.freshness.stale_sources``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fitba.settings import NORMALIZED_DIR, ROOT
from fitba.util.dates import current_season

CACHE_DIR = ROOT / ".cache"

SOURCE_SPECS: list[dict[str, Any]] = [
    {
        "id": "football_data_uk",
        "paths": [CACHE_DIR / "football_data_uk" / current_season() / "*.meta.json"],
        "ttl_hours": 6,
        "required": True,
    },
    {
        "id": "spfl",
        "paths": [CACHE_DIR / "spfl" / "aberdeen" / "*.meta.json"],
        "ttl_hours": 1,
        "required": True,
    },
    {
        "id": "api_results",
        "paths": [NORMALIZED_DIR / "api_results" / "meta.json"],
        "ttl_hours": 1,
        "required": False,
    },
    {
        "id": "api_football",
        "paths": [CACHE_DIR / "api_football" / "**" / "*.json"],
        "ttl_hours": 24,
        "required": False,
    },
    {
        "id": "matchday_snapshot",
        "paths": [NORMALIZED_DIR / "matchday" / "meta.json"],
        "ttl_hours": 20,
        "required": False,
    },
    {
        "id": "history_backfill",
        "paths": [NORMALIZED_DIR / "history" / "backfill_meta.json"],
        "ttl_hours": 24,
        "required": False,
    },
    {
        "id": "scouting_pool",
        "paths": [NORMALIZED_DIR / "scouting" / "meta.json"],
        "ttl_hours": 24,
        "required": False,
    },
    {
        "id": "scouting_roles",
        "paths": [NORMALIZED_DIR / "scouting" / "roles_state.json"],
        "ttl_hours": 6,
        "required": False,
    },
    {
        "id": "scouting_rose_history",
        "paths": [NORMALIZED_DIR / "scouting" / "rose_history_meta.json"],
        "ttl_hours": 168,
        "required": False,
    },
    {
        "id": "scouting_europe",
        "paths": [NORMALIZED_DIR / "scouting" / "europe_meta.json"],
        "ttl_hours": 24,
        "required": False,
    },
    {
        "id": "scouting_standings",
        "paths": [NORMALIZED_DIR / "scouting" / "team_standings_meta.json"],
        "ttl_hours": 24,
        "required": False,
    },
    {
        "id": "scouting_clubs",
        "paths": [NORMALIZED_DIR / "scouting" / "current_clubs_meta.json"],
        "ttl_hours": 24,
        "required": False,
    },
    {
        "id": "former_players",
        "paths": [NORMALIZED_DIR / "former_players" / "meta.json"],
        "ttl_hours": 24,
        "required": False,
    },
    {
        "id": "availability",
        "paths": [NORMALIZED_DIR / "availability" / "meta.json"],
        "ttl_hours": 504,
        "required": False,
    },
    {
        "id": "career",
        "paths": [NORMALIZED_DIR / "career" / "career_roles_meta.json"],
        "ttl_hours": 24,
        "required": False,
    },
    {
        "id": "xg_enrichment",
        "paths": [NORMALIZED_DIR / "xg" / "enrichment_meta.json"],
        "ttl_hours": 24,
        "required": False,
    },
]


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _meta_time(path: Path) -> datetime | None:
    if path.suffix == ".json":
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            document = {}
        for key in ("generated_at", "refreshed_at", "updated_at", "fetched_at", "finished_at"):
            parsed = _parse_time(document.get(key))
            if parsed:
                return parsed
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    except OSError:
        return None


def _source_paths(spec: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    for pattern in spec["paths"]:
        pattern = Path(pattern)
        if any(char in str(pattern) for char in "*?["):
            try:
                relative = str(pattern.relative_to(ROOT))
            except ValueError:
                relative = str(pattern)
            paths.extend(sorted(ROOT.glob(relative)))
        elif pattern.exists():
            paths.append(pattern)
    return paths


def collect_source_snapshots(now: datetime | None = None) -> dict[str, dict[str, Any]]:
    now = now or datetime.now(UTC)
    output: dict[str, dict[str, Any]] = {}
    for spec in SOURCE_SPECS:
        paths = _source_paths(spec)
        times = [value for value in (_meta_time(path) for path in paths) if value]
        refreshed = max(times) if times else None
        age_hours = round((now - refreshed).total_seconds() / 3600, 2) if refreshed else None
        if refreshed is None:
            state = "missing"
        elif age_hours is not None and age_hours <= float(spec["ttl_hours"]):
            state = "fresh"
        else:
            state = "stale"
        output[str(spec["id"])] = {
            "refreshed_at": refreshed.isoformat() if refreshed else None,
            "age_hours": age_hours,
            "ttl_hours": float(spec["ttl_hours"]),
            "state": state,
            "required": bool(spec["required"]),
            "paths": [str(path.relative_to(ROOT)) for path in paths[:3]],
        }
    return output


def _checksum(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def check_freshness(root: Path, *, strict: bool = False) -> dict[str, Any]:
    """Validate the epoch and source freshness of a published corpus."""
    manifest_path = root / "manifest.json"
    errors: list[str] = []
    warnings: list[str] = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "fail",
            "errors": [f"manifest unreadable: {exc}"],
            "warnings": [],
            "sources": {},
        }
    dataset_id = str(manifest.get("dataset_version") or "")
    update_block = manifest.get("update") or {}
    update_id = str(
        update_block.get("id")
        or (manifest.get("freshness") or {}).get("update_id")
        or ""
    )
    manifest_time = _parse_time(manifest.get("generated_at"))
    listed = {
        str(entry.get("path")): entry
        for entry in manifest.get("files") or []
        if entry.get("path")
    }
    actual_files = {
        str(path.relative_to(root)): path
        for path in root.rglob("*.json")
    }
    for path, entry in listed.items():
        if path not in actual_files:
            errors.append(f"manifest lists a missing file: {path}")
            continue
        if entry.get("checksum") and entry["checksum"] != _checksum(actual_files[path]):
            errors.append(f"checksum mismatch: {path}")
    for path in sorted(actual_files):
        if path == "manifest.json":
            continue
        if path not in listed:
            errors.append(f"published file is not listed in the manifest: {path}")

    fresh_payloads = 0
    stale_payloads = 0
    for path, full in sorted(actual_files.items()):
        if path == "manifest.json":
            continue
        try:
            document = json.loads(full.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(document, dict):
            continue
        state = str(document.get("dataset_state") or "")
        if state == "stale":
            stale_payloads += 1
            if not document.get("stale_reason"):
                errors.append(f"stale payload has no reason: {path}")
        else:
            fresh_payloads += 1
            if dataset_id and document.get("dataset_id") != dataset_id:
                errors.append(
                    f"payload dataset_id mismatch: {path} "
                    f"({document.get('dataset_id')!r} != {dataset_id!r})"
                )
        served = document.get("served_by_update_id")
        if update_id and served and served != update_id:
            errors.append(f"payload served_by_update_id mismatch: {path}")
        generated = _parse_time(document.get("generated_at"))
        if generated is None:
            errors.append(f"payload has no parseable generated_at: {path}")
        elif manifest_time and generated > manifest_time:
            errors.append(f"payload generated_at is later than the manifest: {path}")

    sources = (manifest.get("freshness") or {}).get("sources") or {}
    stale_sources = set((manifest.get("freshness") or {}).get("stale_sources") or [])
    for source_id, source in sources.items():
        state = str(source.get("state") or "missing")
        if source.get("required") and state != "fresh":
            errors.append(f"required source is {state}: {source_id}")
        elif state != "fresh" and source_id not in stale_sources:
            message = f"optional source is {state} and not listed as stale: {source_id}"
            if strict:
                errors.append(message)
            else:
                warnings.append(message)

    guard = (manifest.get("update") or {}).get("results_guard") or {}
    if guard and guard.get("status") not in (None, "pass"):
        errors.append(f"manifest results guard is {guard.get('status')}")

    return {
        "status": "fail" if errors else "pass",
        "errors": errors,
        "warnings": warnings,
        "dataset_id": dataset_id,
        "update_id": update_id,
        "fresh_payloads": fresh_payloads,
        "stale_payloads": stale_payloads,
        "files_checked": len(listed),
        "sources": sources,
    }


__all__ = ["SOURCE_SPECS", "check_freshness", "collect_source_snapshots"]
