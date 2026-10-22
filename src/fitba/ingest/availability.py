"""Curated availability ledger and optional provider injury snapshot.

The curated ledger is primary. API-Football /injuries is only consulted when the
provider's league metadata says injuries are covered for the season; Scottish
2026 currently reports false, so the normal state is ``provider_snapshot:
unavailable``. A provider signal never becomes a published out/available status
without a curated entry.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any
from urllib.parse import urlparse

import polars as pl

from fitba.settings import (
    NORMALIZED_DIR,
    availability_ledger,
    availability_policy,
    ensure_dirs,
)
from fitba.sources import api_football
from fitba.util.dates import utc_now_iso

AVAILABILITY_DIR = NORMALIZED_DIR / "availability"
SNAPSHOT_PATH = AVAILABILITY_DIR / "aberdeen.parquet"
META_PATH = AVAILABILITY_DIR / "meta.json"
TEAM_ID = 252
SEASON = 2026
SEASON_LABEL = "2026-27"
STATUSES = {"out", "doubtful", "suspended", "returned", "available", "unknown"}
ENTRY_COLUMNS = [
    "player_id",
    "player_key",
    "player_name",
    "status",
    "reason_category",
    "reason",
    "expected_return",
    "effective_from",
    "effective_to",
    "source_id",
    "source_url",
    "source_title",
    "verified_at",
    "confidence",
    "stale",
    "provider_signal",
    "conflict",
    "in_squad",
    "note",
    "updated_at",
]


def _rows() -> list[dict[str, Any]]:
    return list((availability_ledger() or {}).get("entries") or [])


def _policy() -> dict[str, Any]:
    return (availability_policy() or {}).get("policy") or {}


def _host_allowed(url: str | None, allowed: list[str]) -> bool:
    if not url:
        return False
    host = (urlparse(url).hostname or "").lower()
    return any(host == item.lower() or host.endswith("." + item.lower()) for item in allowed)


def _stale(verified_at: str | None, max_age_days: int) -> bool:
    if not verified_at:
        return True
    try:
        checked = date.fromisoformat(str(verified_at)[:10])
    except ValueError:
        return True
    return (date.today() - checked).days > max_age_days


def _player_map(squad_data: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    return {
        int(player["player_id"]): player
        for player in (squad_data or {}).get("players", [])
        if player.get("player_id") is not None
    }


def _provider_snapshot(*, force: bool = False) -> dict[str, Any]:
    policy = (availability_policy() or {}).get("provider") or {}
    league_id = int(policy.get("league_id") or 179)
    try:
        coverage = api_football.league_coverage(league_id, season=SEASON, force=force)
    except Exception as error:  # noqa: BLE001 - provider failure is a coverage state
        return {
            "status": "unavailable",
            "reason": f"provider_error:{type(error).__name__}",
            "coverage": {},
            "rows": [],
            "requests": 0,
        }
    injuries_covered = bool(coverage.get("injuries") or False)
    if not injuries_covered:
        return {
            "status": "unavailable",
            "reason": "provider_declares_injuries_false",
            "coverage": coverage,
            "rows": [],
            "requests": 0,
        }
    try:
        payload = api_football.injuries(
            team_id=TEAM_ID,
            season=SEASON,
            ttl_hours=6,
            force=force,
        )
    except Exception as error:  # noqa: BLE001
        return {
            "status": "unavailable",
            "reason": f"provider_error:{type(error).__name__}",
            "coverage": coverage,
            "rows": [],
            "requests": 0,
        }
    rows = []
    for item in payload:
        player = item.get("player") or {}
        team = item.get("team") or {}
        fixture = item.get("fixture") or {}
        rows.append(
            {
                "player_id": player.get("id"),
                "player_name": player.get("name"),
                "team_id": team.get("id"),
                "fixture_id": fixture.get("id"),
                "date": str(fixture.get("date") or "")[:10],
                "type": item.get("type"),
                "reason": item.get("reason"),
            }
        )
    return {
        "status": "available" if rows else "empty",
        "reason": None if rows else "provider_returned_no_rows",
        "coverage": coverage,
        "rows": rows,
        "requests": 1,
    }


def _merge(
    *,
    squad_data: dict[str, Any] | None,
    provider: dict[str, Any],
) -> list[dict[str, Any]]:
    policy = _policy()
    max_age = int(policy.get("max_age_days") or 21)
    allowed_hosts = [str(item) for item in (policy.get("allowed_hosts") or [])]
    require_url = bool(policy.get("require_source_url", True))
    squad = _player_map(squad_data)
    entries: dict[int, dict[str, Any]] = {}
    updated_at = utc_now_iso()
    for raw in _rows():
        player_id = raw.get("player_id")
        if player_id is None:
            player_key = str(raw.get("player_key") or "")
            if player_key.startswith("api:player:"):
                try:
                    player_id = int(player_key.split(":")[-1])
                except ValueError:
                    player_id = None
        if player_id is None:
            continue
        status = str(raw.get("status") or "unknown")
        if status not in STATUSES:
            status = "unknown"
        source_url = raw.get("source_url")
        source_id = str(raw.get("source_id") or "")
        verified_at = raw.get("verified_at")
        stale = _stale(str(verified_at) if verified_at else None, max_age)
        invalid_source = require_url and (
            not source_url or not _host_allowed(str(source_url), allowed_hosts)
        )
        if invalid_source:
            status = "unknown"
        if stale and status in {"out", "doubtful", "suspended", "returned", "available"}:
            status = "unknown"
        player = squad.get(int(player_id), {})
        entries[int(player_id)] = {
            "player_id": int(player_id),
            "player_key": raw.get("player_key") or f"api:player:{player_id}",
            "player_name": raw.get("player_name") or player.get("name"),
            "status": status,
            "reason_category": raw.get("reason_category") or "unknown",
            "reason": raw.get("reason"),
            "expected_return": raw.get("expected_return"),
            "effective_from": raw.get("effective_from"),
            "effective_to": raw.get("effective_to"),
            "source_id": source_id or "unknown",
            "source_url": source_url,
            "source_title": raw.get("source_title"),
            "verified_at": verified_at,
            "confidence": raw.get("confidence") or "unknown",
            "stale": stale,
            "provider_signal": None,
            "conflict": False,
            "in_squad": int(player_id) in squad,
            "note": raw.get("note"),
            "updated_at": updated_at,
        }
    for row in provider.get("rows") or []:
        player_id = row.get("player_id")
        if player_id is None:
            continue
        key = int(player_id)
        signal = "out" if "missing" in str(row.get("type") or "").casefold() else "questionable"
        if key in entries:
            if entries[key]["status"] in {"available", "returned"} and signal == "out":
                entries[key]["conflict"] = True
            entries[key]["provider_signal"] = signal
            continue
        player = squad.get(key, {})
        entries[key] = {
            "player_id": key,
            "player_key": f"api:player:{key}",
            "player_name": row.get("player_name") or player.get("name"),
            "status": "unknown",
            "reason_category": "unknown",
            "reason": row.get("reason"),
            "expected_return": None,
            "effective_from": row.get("date"),
            "effective_to": None,
            "source_id": "api_football",
            "source_url": None,
            "source_title": None,
            "verified_at": row.get("date"),
            "confidence": "unknown",
            "stale": False,
            "provider_signal": signal,
            "conflict": False,
            "in_squad": key in squad,
            "note": "Provider signal only; not team news.",
            "updated_at": updated_at,
        }
    # Every current squad player has an explicit state; absence is unknown.
    for key, player in squad.items():
        entries.setdefault(
            key,
            {
                "player_id": key,
                "player_key": player.get("player_key"),
                "player_name": player.get("name"),
                "status": "unknown",
                "reason_category": "unknown",
                "reason": None,
                "expected_return": None,
                "effective_from": None,
                "effective_to": None,
                "source_id": "none",
                "source_url": None,
                "source_title": None,
                "verified_at": None,
                "confidence": "unknown",
                "stale": False,
                "provider_signal": None,
                "conflict": False,
                "in_squad": True,
                "note": "No verified official team-news entry.",
                "updated_at": updated_at,
            },
        )
    return sorted(entries.values(), key=lambda row: (row["player_name"] or "", row["player_id"]))


def refresh_availability(
    *,
    squad_data: dict[str, Any] | None,
    force: bool = False,
) -> dict[str, Any]:
    """Write the normalized availability snapshot and meta."""
    ensure_dirs()
    AVAILABILITY_DIR.mkdir(parents=True, exist_ok=True)
    provider = _provider_snapshot(force=force)
    entries = _merge(squad_data=squad_data, provider=provider)
    frame = pl.DataFrame(entries, infer_schema_length=None)
    for column in ENTRY_COLUMNS:
        if column not in frame.columns:
            frame = frame.with_columns(pl.lit(None).alias(column))
    frame.select(ENTRY_COLUMNS).write_parquet(SNAPSHOT_PATH)
    counts: dict[str, int] = {}
    for entry in entries:
        counts[str(entry["status"])] = counts.get(str(entry["status"]), 0) + 1
    meta = {
        "schema_version": "1.0.0",
        "generated_at": utc_now_iso(),
        "season": SEASON_LABEL,
        "club_id": "sco:aberdeen",
        "entry_count": len(entries),
        "counts": counts,
        "provider": {
            "status": provider.get("status"),
            "reason": provider.get("reason"),
            "coverage": provider.get("coverage"),
            "rows": len(provider.get("rows") or []),
        },
        "policy": _policy(),
        "note": (
            "Curated official AFC team news is primary. Provider injuries are "
            "optional and are not team news. Unknown stays unknown."
        ),
    }
    META_PATH.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return meta


def load_availability_meta() -> dict[str, Any]:
    if not META_PATH.exists():
        return {}
    try:
        return json.loads(META_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def load_availability_frame() -> pl.DataFrame:
    if not SNAPSHOT_PATH.exists():
        return pl.DataFrame({column: [] for column in ENTRY_COLUMNS})
    return pl.read_parquet(SNAPSHOT_PATH)


__all__ = [
    "load_availability_frame",
    "load_availability_meta",
    "refresh_availability",
]
