"""Published medium and long-term themes.

The document is derived from local match, squad and history data. It owns the
five theme narratives and their evidence; league tables, squad profiles,
transfers and the historical record remain the canonical homes for their facts.
"""

from __future__ import annotations

from typing import Any, Literal

import polars as pl
from pydantic import BaseModel, ConfigDict

from fitba.analytics.themes import build_theme_document
from fitba.ingest.match_data import (
    load_player_appearances,
    load_player_match_stats,
    load_team_shapes,
)
from fitba.settings import source_registry, transfer_gaps
from fitba.settings import themes as themes_config

SCHEMA_VERSION = "1.0.0"
STATE = Literal["fresh", "partial", "unavailable", "stale"]
HORIZON = Literal["season", "mission"]
BASIS = Literal["measured", "inferred", "curated", "mixed", "unknown"]
STATUS = Literal["available", "partial", "unavailable"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    dataset_id: str | None = None
    update_id: str | None = None
    published_at: str | None = None
    served_by_update_id: str | None = None
    dataset_state: str | None = None
    stale_reason: str | None = None
    source_snapshots: dict[str, Any] | None = None


class ThemeSource(StrictModel):
    id: str
    name: str
    url: str | None = None
    verified_at: str | None = None


class ThemeEvidence(StrictModel):
    label: str
    value: Any = None
    note: str | None = None
    basis: BASIS = "measured"


class ThemePlayer(StrictModel):
    player_id: int | None = None
    name: str | None = None
    role_family: str | None = None
    starts: int | None = None
    minutes: int | None = None
    sub_apps: int | None = None
    bench_named: int | None = None
    category: str | None = None
    note: str | None = None
    arrival: str | None = None
    arrival_kind: str | None = None
    two_cb_starts: int | None = None
    three_cb_starts: int | None = None
    sub_minutes: int | None = None
    availability_status: str | None = None
    availability_confidence: str | None = None
    availability_source: str | None = None
    availability_verified_at: str | None = None
    availability_note: str | None = None
    availability_conflict: bool | None = None


class ThemeLink(StrictModel):
    label: str
    href: str


class Theme(StrictModel):
    theme_id: str
    horizon: HORIZON
    order: int
    title: str
    fan_question: str
    status: STATUS
    reason: str | None = None
    headline: str | None = None
    read: str | None = None
    basis: BASIS = "measured"
    read_basis: BASIS = "inferred"
    confidence: Literal["high", "medium", "low", "unknown"] = "unknown"
    evidence: list[ThemeEvidence] = []
    players: list[ThemePlayer] = []
    metrics: dict[str, Any] = {}
    links: list[ThemeLink] = []
    caveats: list[str] = []
    method: str | None = None
    implications: list[dict[str, Any]] = []


class ThemeScope(StrictModel):
    season: str
    season_weight: int = 80
    mission_weight: int = 20
    mission_label: str
    note: str


class ThemesCoverage(StrictModel):
    status: str
    season: str
    role_basis: str
    provider_ratings: str
    fixtures_total: int | None = None
    fixtures_with_ratings: int | None = None
    starts_total: int | None = None
    starts_with_role: int | None = None
    role_start_coverage: float | None = None
    minutes_total: int | None = None
    sub_minutes: int | None = None
    provider_rating_rows: int | None = None
    provider_rating_minutes: int | None = None
    shapes: str | None = None
    bench: str | None = None
    availability_feed: dict[str, Any] = {}
    channel_data: bool = False
    xg: bool = False
    possession: bool = False
    midgame_shape: bool = False
    historical_ratings: bool = False
    note: str


class ThemesDocument(StrictModel):
    schema_version: str = SCHEMA_VERSION
    generated_at: str
    season: str
    club_id: str
    state: STATE
    served_generated_at: str | None = None
    title: str
    scope: ThemeScope
    summary: dict[str, Any]
    coverage: ThemesCoverage
    themes: list[Theme]
    sources: list[ThemeSource] = []
    notes: str


def themes_schema() -> dict[str, Any]:
    return ThemesDocument.model_json_schema()


def _source_refs() -> list[ThemeSource]:
    registry = (source_registry() or {}).get("sources") or {}
    output = []
    for source_id in ("spfl", "football_data_uk", "api_football", "wikipedia"):
        item = registry.get(source_id)
        if not item:
            continue
        output.append(
            ThemeSource(
                id=source_id,
                name=str(item.get("name") or source_id),
                url=item.get("url") or item.get("base_url"),
                verified_at=str(item.get("last_verified") or ""),
            )
        )
    return output


def _curated_notes() -> list[dict[str, Any]]:
    gaps = (transfer_gaps() or {}).get("gaps", []) or []
    notes = []
    for gap in gaps:
        if str(gap.get("player_key") or "") != "api:player:68534":
            continue
        reason = str(gap.get("reason") or "").strip()
        if reason:
            notes.append(
                {
                    "player_id": 68534,
                    "name": gap.get("player_name") or "K. Tobers",
                    "note": reason,
                    "basis": "curated",
                    "source": "reference/transfer_gaps.yaml",
                }
            )
    return notes


def build_themes_payload(
    *,
    season: str,
    generated_at: str,
    matches: pl.DataFrame,
    squad_data: dict[str, Any],
    transfers_data: dict[str, Any] | None,
    history_index: dict[str, Any] | None,
    history_season: dict[str, Any] | None,
    availability: dict[str, Any] | None = None,
    appearances: pl.DataFrame | None = None,
    match_stats: pl.DataFrame | None = None,
    team_shapes: pl.DataFrame | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the typed themes document from local data only."""
    policy = config or themes_config()
    appearances = appearances if appearances is not None else load_player_appearances()
    match_stats = match_stats if match_stats is not None else load_player_match_stats()
    team_shapes = team_shapes if team_shapes is not None else load_team_shapes()
    transfers = (transfers_data or {}).get("transfers", []) or []
    document = build_theme_document(
        appearances=appearances,
        match_stats=match_stats,
        team_shapes=team_shapes,
        matches=matches,
        squad_data=squad_data,
        transfers=transfers,
        history_index=history_index,
        history_season=history_season,
        season=season,
        generated_at=generated_at,
        config=policy,
        curated_notes=_curated_notes(),
        availability={
            int(entry["player_id"]): entry
            for entry in (availability or {}).get("entries", [])
            if entry.get("player_id") is not None and entry.get("in_squad", True)
        },
    )
    document["sources"] = _source_refs()
    return ThemesDocument(**document).model_dump()


def _empty_document(
    *,
    generated_at: str,
    season: str,
    state: STATE,
    reason: str,
) -> dict[str, Any]:
    return ThemesDocument(
        generated_at=generated_at,
        season=season,
        club_id="sco:aberdeen",
        state=state,
        stale_reason=reason,
        title="The bigger picture",
        scope=ThemeScope(
            season=season,
            mission_label="The Cormack-era mission",
            note=(
                "80% current season; 20% the long-term trading-club mission. "
                "The split is editorial, not a statistical model."
            ),
        ),
        summary={
            "headline": "The theme layer is unavailable.",
            "theme_count": 0,
            "season_themes": 0,
            "mission_themes": 0,
            "confidence": "unknown",
            "note": "No theme payload could be built from the local data.",
        },
        coverage=ThemesCoverage(
            status="unavailable",
            season=season,
            role_basis="unavailable",
            provider_ratings="unavailable",
            note=reason,
        ),
        themes=[],
        sources=_source_refs(),
        notes=(
            "The theme layer is derived from local match, squad and history "
            "data. It is unavailable for this publish."
        ),
    ).model_dump()


def fallback_themes_payload(
    previous: dict[str, Any] | None,
    *,
    generated_at: str,
    season: str,
    reason: str,
) -> dict[str, Any]:
    """Carry forward the last good themes document as stale, or publish empty."""
    if previous:
        carried = {
            **previous,
            "generated_at": generated_at,
            "season": season,
            "state": "stale",
            "stale_reason": reason,
            "served_generated_at": previous.get("generated_at"),
        }
        try:
            return ThemesDocument(**carried).model_dump()
        except Exception:  # noqa: BLE001 - a corrupt previous document is not reused
            pass
    return _empty_document(
        generated_at=generated_at,
        season=season,
        state="unavailable",
        reason=reason,
    )


__all__ = [
    "ThemesDocument",
    "build_themes_payload",
    "fallback_themes_payload",
    "themes_schema",
]
