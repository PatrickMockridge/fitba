"""Published availability layer.

The curated ledger is primary. The provider snapshot is optional and is never
allowed to create a confirmed team-news status. The document is derived from
local data and never calls the network.
"""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from fitba.analytics.availability_facts import availability_universes
from fitba.analytics.availability_reconcile import (
    assert_no_unresolved_contradictions,
    load_reconciliation_evidence,
)
from fitba.ingest.availability import (
    _merge,
    load_availability_frame,
    load_availability_meta,
)
from fitba.settings import source_registry

SCHEMA_VERSION = "1.1.0"
STATUS = Literal["out", "doubtful", "suspended", "returned", "available", "unknown"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    dataset_id: str | None = None
    update_id: str | None = None
    published_at: str | None = None
    served_by_update_id: str | None = None
    dataset_state: str | None = None
    stale_reason: str | None = None
    source_snapshots: dict[str, Any] | None = None


class AvailabilitySource(StrictModel):
    id: str
    name: str
    url: str | None = None


class ContradictedBy(StrictModel):
    fixture_id: int | None = None
    date: str | None = None
    competition_id: str | None = None
    opponent_name: str | None = None
    squad_status: str | None = None
    started: bool | None = None
    minutes: int | None = None


class SuspensionState(StrictModel):
    competition_id: str | None = None
    card_fixture_id: int | None = None
    card_date: str | None = None
    red_type: str | None = None
    ban_matches: int | None = None
    state: str | None = None
    served_fixture_id: int | None = None
    served_date: str | None = None
    served_count: int | None = None
    appearance_fixture_id: int | None = None
    appearance_date: str | None = None
    appearance_squad_status: str | None = None
    rule_verified: bool = False
    rule_source: str | None = None


class AvailabilityEntry(StrictModel):
    player_id: int | None = None
    player_key: str | None = None
    player_name: str | None = None
    status: STATUS = "unknown"
    original_status: STATUS | None = None
    competition_id: str | None = None
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
    review_required: bool = False
    review_reason: str | None = None
    review_reasons: list[str] = Field(default_factory=list)
    review_severity: str | None = None
    contradicted_by: ContradictedBy | None = None
    status_age_days: int | None = None
    fresh_until: str | None = None
    stale_after: str | None = None
    suspension: SuspensionState | None = None


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
    needs_review: int = 0
    contradicted: int = 0
    provider_snapshot: dict[str, Any] = {}
    note: str


class AvailabilityReview(StrictModel):
    status: str = "ok"
    count: int = 0
    contradicted: int = 0
    aging: int = 0
    suspension_served: int = 0
    reconciliation: dict[str, Any] = {}
    ledger: dict[str, Any] = {}


class AvailabilityDocument(StrictModel):
    schema_version: str = SCHEMA_VERSION
    generated_at: str
    season: str
    club_id: str
    state: str
    as_of: str | None = None
    policy_version: str
    coverage: AvailabilityCoverage
    universes: dict[str, Any] = {}
    entries: list[AvailabilityEntry]
    review: AvailabilityReview = Field(default_factory=AvailabilityReview)
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


def _snapshot_entries(
    squad_data: dict[str, Any] | None,
    evidence: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Merge curated ledger statuses with the ingested provider evidence.

    The snapshot supplies provider signals and conflicts. The curated ledger
    remains the source of a confirmed team-news status; an older snapshot must
    not roll a verified entry back to unknown.
    """
    entries = {
        int(entry["player_id"]): entry
        for entry in _merge(squad_data=squad_data, provider={"rows": []}, evidence=evidence)
        if entry.get("player_id") is not None
    }
    frame = load_availability_frame()
    for row in frame.to_dicts() if frame.height else []:
        player_id = row.get("player_id")
        if player_id is None or int(player_id) not in entries:
            continue
        entry = entries[int(player_id)]
        for key in ("provider_signal", "conflict"):
            if row.get(key) is not None:
                entry[key] = row.get(key)
        if row.get("provider_signal") and not entry.get("source_url"):
            entry["provider_signal"] = row.get("provider_signal")
    return sorted(
        entries.values(),
        key=lambda row: (row.get("player_name") or "", row["player_id"]),
    )


def build_availability_payload(
    *,
    squad_data: dict[str, Any] | None,
    generated_at: str,
    season: str,
) -> dict[str, Any]:
    meta = load_availability_meta()
    provider = meta.get("provider") or {}
    try:
        evidence = load_reconciliation_evidence(season)
    except Exception as error:  # noqa: BLE001 - reconciliation failure is a review state
        evidence = {
            "status": "unavailable",
            "errors": [f"{type(error).__name__}: {error}"],
            "participation": [],
            "red_cards": [],
            "schedule": [],
            "coverage": {},
        }
    entries = _snapshot_entries(squad_data, evidence)
    if not entries:
        entries = _merge(squad_data=squad_data, provider={"rows": []}, evidence=evidence)
    assert_no_unresolved_contradictions(entries)
    universes = availability_universes(entries, squad_data)
    counts = {
        status: sum(1 for entry in entries if entry.get("status") == status)
        for status in ("out", "suspended", "doubtful", "returned", "available", "unknown")
    }
    known = sum(
        counts[status] for status in ("out", "suspended", "doubtful", "returned", "available")
    )
    stale = sum(1 for entry in entries if entry.get("stale"))
    conflicts = sum(1 for entry in entries if entry.get("conflict"))
    contradicted = sum(1 for entry in entries if entry.get("review_severity") == "contradicted")
    aging = sum(1 for entry in entries if entry.get("review_severity") == "aging")
    needs_review = sum(1 for entry in entries if entry.get("review_required"))
    served = sum(1 for entry in entries if (entry.get("suspension") or {}).get("state") == "served")
    reconciliation = meta.get("reconciliation") or {
        "status": "ok" if evidence.get("status") == "ok" else "unavailable",
        "errors": evidence.get("errors") or [],
        "evidence": evidence.get("coverage") or {},
    }
    ledger = meta.get("ledger") or {}
    if reconciliation.get("status") == "unavailable":
        review_status = "unavailable"
    elif contradicted:
        review_status = "contradicted"
    elif aging:
        review_status = "review"
    else:
        review_status = "ok"
    if reconciliation.get("status") == "unavailable":
        dataset_state = "stale"
        stale_reason = "availability_reconciliation_unavailable"
    elif ledger.get("status") == "review":
        dataset_state = "stale"
        stale_reason = str(ledger.get("reason") or "ledger_older_than_latest_news")
    else:
        dataset_state = "fresh"
        stale_reason = None
    document = AvailabilityDocument(
        generated_at=generated_at,
        season=season,
        club_id="sco:aberdeen",
        state="partial" if known else "unavailable",
        as_of=str(meta.get("generated_at") or "") or None,
        policy_version=str(meta.get("schema_version") or SCHEMA_VERSION),
        dataset_state=dataset_state,
        stale_reason=stale_reason,
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
            needs_review=needs_review,
            contradicted=contradicted,
            provider_snapshot={
                "status": provider.get("status") or "unavailable",
                "reason": provider.get("reason"),
                "rows": provider.get("rows", 0),
                "coverage": provider.get("coverage") or {},
            },
            note=(
                "Curated official AFC team news is primary. Provider injuries "
                "are optional and are not team news. No adverse entry means "
                "available by default, not a verified fit. Contradicted claims "
                "are shown in the review block."
            ),
        ),
        universes=universes,
        entries=[
            AvailabilityEntry(
                player_id=entry.get("player_id"),
                player_key=entry.get("player_key"),
                player_name=entry.get("player_name"),
                status=cast(STATUS, str(entry.get("status") or "unknown")),
                original_status=(
                    cast(STATUS, str(entry.get("original_status")))
                    if entry.get("original_status")
                    else None
                ),
                competition_id=entry.get("competition_id"),
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
                review_required=bool(entry.get("review_required")),
                review_reason=entry.get("review_reason"),
                review_reasons=list(entry.get("review_reasons") or []),
                review_severity=entry.get("review_severity"),
                contradicted_by=entry.get("contradicted_by"),
                status_age_days=entry.get("status_age_days"),
                fresh_until=entry.get("fresh_until"),
                stale_after=entry.get("stale_after"),
                suspension=entry.get("suspension"),
            )
            for entry in entries
        ],
        review=AvailabilityReview(
            status=review_status,
            count=needs_review,
            contradicted=contradicted,
            aging=aging,
            suspension_served=served,
            reconciliation={
                "status": reconciliation.get("status"),
                "errors": reconciliation.get("errors") or [],
                "evidence": reconciliation.get("evidence") or {},
            },
            ledger=ledger,
        ),
        sources=_sources(),
        notes=(
            "Availability is a special case of team news. Only a verified "
            "curated entry changes the predicted XI; a provider signal alone "
            "does not. Contradicted claims become unknown and stay visible in "
            "the review block. Context-only names without an official public "
            "source are held in a private verification queue and are not "
            "published."
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
