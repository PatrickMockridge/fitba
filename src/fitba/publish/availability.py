"""Published availability layer.

The curated ledger is primary. The provider snapshot is optional and is never
allowed to create a confirmed team-news status. The document is derived from
local data and never calls the network.
"""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict

from fitba.ingest.availability import (
    _merge,
    load_availability_meta,
)
from fitba.settings import source_registry

SCHEMA_VERSION = "1.0.0"
STATUS = Literal["out", "doubtful", "suspended", "returned", "available", "unknown"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AvailabilitySource(StrictModel):
    id: str
    name: str
    url: str | None = None


class AvailabilityEntry(StrictModel):
    player_id: int | None = None
    player_key: str | None = None
    player_name: str | None = None
    status: STATUS = "unknown"
    reason_category: str = "unknown"
    reason: str | None = None
    expected_return: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    source_id: str = "none"
    source_url: str | None = None
    source_title: str | None = None
    verified_at: str | None = None
    confidence: str = "unknown"
    stale: bool = False
    provider_signal: str | None = None
    conflict: bool = False
    in_squad: bool = True
    note: str | None = None


class AvailabilityCoverage(StrictModel):
    status: str
    entries: int
    known: int
    unknown: int
    out: int
    suspended: int
    doubtful: int
    returned: int
    stale: int
    conflicts: int
    provider_snapshot: dict[str, Any] = {}
    note: str


class AvailabilityDocument(StrictModel):
    schema_version: str = SCHEMA_VERSION
    generated_at: str
    season: str
    club_id: str
    state: str
    as_of: str | None = None
    policy_version: str
    coverage: AvailabilityCoverage
    entries: list[AvailabilityEntry]
    sources: list[AvailabilitySource] = []
    notes: str


def availability_schema() -> dict[str, Any]:
    return AvailabilityDocument.model_json_schema()


def _sources() -> list[AvailabilitySource]:
    registry = (source_registry() or {}).get("sources") or {}
    output = []
    for source_id in ("afc_news", "api_football"):
        item = registry.get(source_id)
        if not item:
            continue
        output.append(
            AvailabilitySource(
                id=source_id,
                name=str(item.get("name") or source_id),
                url=item.get("url") or item.get("base_url"),
            )
        )
    return output


def _date_text(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    return str(value)


def build_availability_payload(
    *,
    squad_data: dict[str, Any] | None,
    generated_at: str,
    season: str,
) -> dict[str, Any]:
    meta = load_availability_meta()
    provider = meta.get("provider") or {}
    entries = _merge(
        squad_data=squad_data,
        provider={"rows": []},
    )
    counts = {
        status: sum(1 for entry in entries if entry.get("status") == status)
        for status in ("out", "suspended", "doubtful", "returned", "available", "unknown")
    }
    known = sum(
        counts[status] for status in ("out", "suspended", "doubtful", "returned", "available")
    )
    stale = sum(1 for entry in entries if entry.get("stale"))
    conflicts = sum(1 for entry in entries if entry.get("conflict"))
    document = AvailabilityDocument(
        generated_at=generated_at,
        season=season,
        club_id="sco:aberdeen",
        state="partial" if known else "unavailable",
        as_of=str(meta.get("generated_at") or "") or None,
        policy_version=str(meta.get("schema_version") or SCHEMA_VERSION),
        coverage=AvailabilityCoverage(
            status="partial" if known else "unavailable",
            entries=len(entries),
            known=known,
            unknown=counts["unknown"],
            out=counts["out"],
            suspended=counts["suspended"],
            doubtful=counts["doubtful"],
            returned=counts["returned"],
            stale=stale,
            conflicts=conflicts,
            provider_snapshot={
                "status": provider.get("status") or "unavailable",
                "reason": provider.get("reason"),
                "rows": provider.get("rows", 0),
                "coverage": provider.get("coverage") or {},
            },
            note=(
                "Curated official AFC team news is primary. Provider injuries "
                "are optional and are not team news. Unknown stays unknown."
            ),
        ),
        entries=[
            AvailabilityEntry(
                player_id=entry.get("player_id"),
                player_key=entry.get("player_key"),
                player_name=entry.get("player_name"),
                status=cast(STATUS, str(entry.get("status") or "unknown")),
                reason_category=str(entry.get("reason_category") or "unknown"),
                reason=entry.get("reason"),
                expected_return=_date_text(entry.get("expected_return")),
                effective_from=_date_text(entry.get("effective_from")),
                effective_to=_date_text(entry.get("effective_to")),
                source_id=str(entry.get("source_id") or "none"),
                source_url=entry.get("source_url"),
                source_title=entry.get("source_title"),
                verified_at=_date_text(entry.get("verified_at")),
                confidence=str(entry.get("confidence") or "unknown"),
                stale=bool(entry.get("stale")),
                provider_signal=entry.get("provider_signal"),
                conflict=bool(entry.get("conflict")),
                in_squad=bool(entry.get("in_squad", True)),
                note=entry.get("note"),
            )
            for entry in entries
        ],
        sources=_sources(),
        notes=(
            "Availability is a special case of team news. Only a verified "
            "curated entry changes the predicted XI; a provider signal alone "
            "does not. Context-only names without an official public source are "
            "held in a private verification queue and are not published."
        ),
    )
    return document.model_dump()


def fallback_availability_payload(
    previous: dict[str, Any] | None,
    *,
    generated_at: str,
    season: str,
    reason: str,
) -> dict[str, Any]:
    if previous:
        carried = {
            **previous,
            "generated_at": generated_at,
            "season": season,
            "state": "stale",
            "notes": f"{previous.get('notes', '')} Carried forward: {reason}",
        }
        try:
            return AvailabilityDocument(**carried).model_dump()
        except Exception:  # noqa: BLE001
            pass
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "season": season,
        "club_id": "sco:aberdeen",
        "state": "unavailable",
        "as_of": None,
        "policy_version": SCHEMA_VERSION,
        "coverage": {
            "status": "unavailable",
            "entries": 0,
            "known": 0,
            "unknown": 0,
            "out": 0,
            "suspended": 0,
            "doubtful": 0,
            "returned": 0,
            "stale": 0,
            "conflicts": 0,
            "provider_snapshot": {},
            "note": reason,
        },
        "entries": [],
        "sources": [],
        "notes": "Availability is unavailable for this publish.",
    }


__all__ = [
    "AvailabilityDocument",
    "availability_schema",
    "build_availability_payload",
    "fallback_availability_payload",
]
