"""Published squad-needs document.

Role profiles and market routes only: no named targets, fees or wages. The
measured depth/availability drives the category; the curated prior is shown
separately and is not blended into a verdict.
"""

from __future__ import annotations

from typing import Any, Literal

import polars as pl
from pydantic import BaseModel, ConfigDict

from fitba.analytics.needs import build_needs_document
from fitba.settings import needs_policy, source_registry

SCHEMA_VERSION = "1.0.0"
STATE = Literal["fresh", "partial", "unavailable", "stale"]
CATEGORY = Literal["cover", "replace", "strengthen", "monitor", "none", "unknown"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NeedsSource(StrictModel):
    id: str
    name: str
    url: str | None = None
    verified_at: str | None = None


class NeedsLink(StrictModel):
    label: str
    href: str


class NeedsPlayer(StrictModel):
    player_id: int | None = None
    name: str | None = None
    role_family: str | None = None
    starts: int | None = None
    minutes: int | None = None
    sub_apps: int | None = None
    category: str | None = None
    availability_status: str | None = None
    availability_note: str | None = None
    availability_conflict: bool | None = None
    arrival: str | None = None
    arrival_kind: str | None = None
    note: str | None = None


class NeedsFamily(StrictModel):
    family: str
    label: str
    category: CATEGORY
    priority: int | None = None
    urgency: str
    measured_score: float | None = None
    curated_prior: float | None = None
    confidence: str
    basis: str
    expected_slots: float | None = None
    measured: dict[str, Any]
    evidence: list[dict[str, Any]] = []
    drivers: list[str] = []
    availability: list[dict[str, Any]] = []
    outgoing_risk: dict[str, Any] = {}
    replace_status: str
    scouting_groups: list[str] = []
    role_profile: dict[str, Any] = {}
    market_route: dict[str, Any] = {}
    roster_space: dict[str, Any] = {}
    players: list[NeedsPlayer] = []
    caveats: list[str] = []
    links: list[NeedsLink] = []


class NeedsDocument(StrictModel):
    schema_version: str = SCHEMA_VERSION
    generated_at: str
    season: str
    club_id: str
    state: STATE
    summary: dict[str, Any]
    coverage: dict[str, Any]
    roster_space: dict[str, Any]
    families: list[NeedsFamily]
    sources: list[NeedsSource] = []
    notes: str


def needs_schema() -> dict[str, Any]:
    return NeedsDocument.model_json_schema()


def _sources() -> list[NeedsSource]:
    registry = (source_registry() or {}).get("sources") or {}
    output = []
    for source_id in ("afc_news", "api_football", "football_data_uk"):
        item = registry.get(source_id)
        if not item:
            continue
        output.append(
            NeedsSource(
                id=source_id,
                name=str(item.get("name") or source_id),
                url=item.get("url") or item.get("base_url"),
                verified_at=str(item.get("last_verified") or ""),
            )
        )
    return output


def build_needs_payload(
    *,
    season: str,
    generated_at: str,
    themes: dict[str, Any] | None,
    availability: dict[str, Any] | None,
    squad_data: dict[str, Any] | None,
    transfers_data: dict[str, Any] | None,
    rumours: list[dict[str, Any]] | None,
    team_shapes: pl.DataFrame | None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    document = build_needs_document(
        season=season,
        generated_at=generated_at,
        themes=themes,
        availability=availability,
        squad_data=squad_data,
        transfers=(transfers_data or {}).get("transfers", []) or [],
        rumours=rumours or [],
        team_shapes=team_shapes,
        config=config or needs_policy(),
    )
    document["sources"] = _sources()
    return NeedsDocument(**document).model_dump()


THEME_FAMILIES = {
    "family_balance": None,
    "wing_back_tax": ["FB/WB", "W"],
    "cover_question": ["CB", "FB/WB", "MID"],
    "leaky_boat": ["CB", "MID", "ST"],
    "mission_check": [],
}


def attach_theme_implications(
    themes_payload: dict[str, Any],
    needs_payload: dict[str, Any],
) -> dict[str, Any]:
    """Attach short, evidence-bound transfer implications to theme blocks."""
    families = {str(row.get("family")): row for row in needs_payload.get("families", [])}
    for theme in themes_payload.get("themes", []):
        theme_id = str(theme.get("theme_id"))
        if theme_id == "family_balance":
            ordered = [
                row
                for row in needs_payload.get("families", [])
                if row.get("category") in {"cover", "replace", "strengthen"}
            ][:2]
            selected = [str(row.get("family")) for row in ordered]
        else:
            selected = list(THEME_FAMILIES.get(theme_id) or [])
        implications = []
        for family in selected:
            row = families.get(family)
            if not row:
                continue
            category = str(row.get("category"))
            if category not in {"cover", "replace", "strengthen"}:
                continue
            route = (row.get("market_route") or {}).get("primary") or "none"
            implications.append(
                {
                    "family": family,
                    "category": category,
                    "urgency": row.get("urgency"),
                    "line": (
                        f"{row.get('label')}: {category.replace('_', ' ')}; "
                        f"{row.get('urgency')} urgency; market route {route}."
                    ),
                    "href": f"/recruitment/#needs-{family.lower().replace('/', '-')}",
                    "basis": "mixed",
                }
            )
        theme["implications"] = implications
    return themes_payload


def fallback_needs_payload(
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
            return NeedsDocument(**carried).model_dump()
        except Exception:  # noqa: BLE001
            pass
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "season": season,
        "club_id": "sco:aberdeen",
        "state": "unavailable",
        "summary": {
            "families": 0,
            "counts": {},
            "top_priority": None,
            "availability_known": 0,
            "availability_unknown": 0,
            "note": reason,
        },
        "coverage": {"status": "unavailable", "note": reason},
        "roster_space": {},
        "families": [],
        "sources": [],
        "notes": "Squad needs are unavailable for this publish.",
    }


__all__ = [
    "NeedsDocument",
    "attach_theme_implications",
    "build_needs_payload",
    "fallback_needs_payload",
    "needs_schema",
]
