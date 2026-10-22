"""Published layer-by-layer provenance.

The truth table lives in ``config/provenance.yaml``; this module joins it to the
source registry and the actual row contributions so the web page and the
manifest can say which source owns each layer. It never promotes a source to
primary for a layer it does not supply.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict

from fitba.settings import (
    league_migration,
    source_registry,
)
from fitba.settings import (
    provenance as provenance_config,
)

SCHEMA_VERSION = "1.0.0"
STATUS = Literal["active", "partial", "gated", "unavailable", "planned", "not_published"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceRef(StrictModel):
    id: str
    name: str
    url: str | None = None
    verified_at: str | None = None
    lane: str | None = None
    attribution: str | None = None


class LayerSource(StrictModel):
    source_id: str
    role: Literal["primary", "fallback", "corroboration", "optional"]
    name: str
    url: str | None = None
    verified_at: str | None = None
    rows: int | None = None


class LayerGate(StrictModel):
    id: str | None = None
    status: str
    report: str | None = None
    reason: str | None = None


class ProvenanceLayer(StrictModel):
    id: str
    label: str
    kind: str
    status: str
    scope: str
    fields: list[str] = []
    primary: str
    primary_source: SourceRef | None = None
    fallback: list[str] = []
    sources: list[LayerSource] = []
    gate: LayerGate | None = None
    surfaces: list[str] = []
    note: str | None = None


class SourceSummary(StrictModel):
    id: str
    name: str
    url: str | None = None
    lane: str | None = None
    attribution: str | None = None
    last_verified: str | None = None
    primary_layers: list[str] = []
    rows: int
    rows_basis: str = "primary contributions only"


class ExcludedSource(StrictModel):
    id: str
    reason: str


class MigrationState(StrictModel):
    season: str
    enabled: bool
    gate_status: str
    active_source: str
    report: str | None = None
    reason: str | None = None


class AvailabilityState(StrictModel):
    status: str
    provider_snapshot: str
    reason: str | None = None


class ProvenanceDocument(StrictModel):
    schema_version: str = SCHEMA_VERSION
    generated_at: str
    season: str
    layers: list[ProvenanceLayer]
    sources: list[SourceSummary]
    excluded: list[ExcludedSource] = []
    migration: MigrationState
    availability: AvailabilityState
    notes: str


def provenance_schema() -> dict[str, Any]:
    return ProvenanceDocument.model_json_schema()


def _source_ref(source_id: str, registry: dict[str, Any]) -> SourceRef | None:
    item = registry.get(source_id)
    if not item:
        return None
    return SourceRef(
        id=source_id,
        name=str(item.get("name") or source_id),
        url=item.get("url") or item.get("base_url"),
        verified_at=str(item.get("last_verified") or ""),
        lane=item.get("lane"),
        attribution=item.get("attribution"),
    )


def _migration_state(generated_at: str) -> MigrationState:
    policy = league_migration() or {}
    report_path = Path(str(policy.get("report") or ""))
    fallback = str(policy.get("fallback") or "football_data_uk")
    gate_status = "not_run"
    active_source = fallback
    reason = "Migration is disabled; football-data remains primary."
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            gate = report.get("gate") or {}
            gate_status = str(gate.get("status") or "not_run")
            active_source = str(gate.get("active_source") or fallback)
            failures = gate.get("failures") or []
            if gate_status == "pass":
                reason = (
                    "Gate passed; migration is enabled."
                    if policy.get("enabled")
                    else "Gate passed; migration remains disabled until a human enables it."
                )
            else:
                reason = "Gate failed: " + "; ".join(str(item) for item in failures[:3])
                active_source = fallback
        except (json.JSONDecodeError, OSError):
            gate_status = "report_unreadable"
            reason = "The migration report exists but could not be read."
    elif policy.get("enabled"):
        gate_status = "missing_report"
        reason = "Migration is enabled but the gate report is missing."
    return MigrationState(
        season=str(policy.get("season") or "2026-27"),
        enabled=bool(policy.get("enabled")),
        gate_status=gate_status,
        active_source=active_source,
        report=str(report_path) if policy.get("report") else None,
        reason=reason,
    )


def build_provenance_payload(
    *,
    season: str,
    generated_at: str,
    contributions: dict[str, dict[str, int]] | None = None,
    availability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the provenance document from config, sources and row counts."""
    config = provenance_config() or {}
    registry = (source_registry() or {}).get("sources") or {}
    contributions = contributions or {}
    layers: list[ProvenanceLayer] = []
    primary_layers: dict[str, list[str]] = {}
    source_rows: dict[str, int] = {}
    appeared_sources: set[str] = set()

    for raw in config.get("layers", []) or []:
        layer_id = str(raw.get("id") or "")
        primary = str(raw.get("primary") or "none")
        fallback = [str(item) for item in (raw.get("fallback") or [])]
        layer_contributions = contributions.get(layer_id) or {}
        sources = []
        for source_id, role in (
            [(primary, "primary")]
            + [(item, "fallback") for item in fallback]
            + [
                (source_id, "corroboration")
                for source_id in layer_contributions
                if source_id not in {primary, *fallback}
            ]
        ):
            item = registry.get(source_id)
            if not item:
                continue
            appeared_sources.add(source_id)
            sources.append(
                LayerSource(
                    source_id=source_id,
                    role=cast(
                        Literal["primary", "fallback", "corroboration", "optional"],
                        role,
                    ),
                    name=str(item.get("name") or source_id),
                    url=item.get("url") or item.get("base_url"),
                    verified_at=str(item.get("last_verified") or ""),
                    rows=layer_contributions.get(source_id),
                )
            )
            if role == "primary":
                primary_layers.setdefault(source_id, []).append(layer_id)
                source_rows[source_id] = source_rows.get(source_id, 0) + int(
                    layer_contributions.get(source_id) or 0
                )
        primary_source = _source_ref(primary, registry) if primary in registry else None
        gate_raw = raw.get("gate")
        gate = (
            LayerGate(
                id=str(gate_raw.get("id") or gate_raw)
                if isinstance(gate_raw, dict)
                else str(gate_raw)
                if gate_raw
                else None,
                status=str((gate_raw or {}).get("status"))
                if isinstance(gate_raw, dict)
                else "configured",
                report=str((gate_raw or {}).get("report")) if isinstance(gate_raw, dict) else None,
                reason=str((gate_raw or {}).get("reason")) if isinstance(gate_raw, dict) else None,
            )
            if gate_raw
            else None
        )
        layers.append(
            ProvenanceLayer(
                id=layer_id,
                label=str(raw.get("label") or layer_id),
                kind=str(raw.get("kind") or "provider"),
                status=str(raw.get("status") or "active"),
                scope=str(raw.get("scope") or ""),
                fields=[str(item) for item in (raw.get("fields") or [])],
                primary=primary,
                primary_source=primary_source,
                fallback=fallback,
                sources=sources,
                gate=gate,
                surfaces=[str(item) for item in (raw.get("surfaces") or [])],
                note=str(raw.get("note") or "").strip() or None,
            )
        )

    summaries = []
    for source_id, item in registry.items():
        if source_id not in appeared_sources and source_id not in source_rows:
            continue
        summaries.append(
            SourceSummary(
                id=source_id,
                name=str(item.get("name") or source_id),
                url=item.get("url") or item.get("base_url"),
                lane=item.get("lane"),
                attribution=item.get("attribution"),
                last_verified=str(item.get("last_verified") or ""),
                primary_layers=sorted(primary_layers.get(source_id, [])),
                rows=source_rows.get(source_id, 0),
            )
        )
    summaries.sort(key=lambda row: (row.rows, row.name), reverse=True)

    excluded = [
        ExcludedSource(id=str(item.get("id")), reason=str(item.get("reason") or ""))
        for item in (config.get("excluded") or [])
    ]
    migration = _migration_state(generated_at)
    availability_state = AvailabilityState(
        status=str((availability or {}).get("status") or "unavailable"),
        provider_snapshot=str((availability or {}).get("provider_snapshot") or "unavailable"),
        reason=(availability or {}).get("reason"),
    )
    document = ProvenanceDocument(
        generated_at=generated_at,
        season=season,
        layers=layers,
        sources=summaries,
        excluded=excluded,
        migration=migration,
        availability=availability_state,
        notes=(
            "A source is listed as primary only for the layers it actually "
            "supplies. Row counts are primary contributions only; curated and "
            "derived layers are labelled as such."
        ),
    )
    return document.model_dump()


__all__ = [
    "ProvenanceDocument",
    "build_provenance_payload",
    "provenance_schema",
]
