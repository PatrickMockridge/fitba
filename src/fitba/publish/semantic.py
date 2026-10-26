"""Published reader-facing semantic layer.

This module is the bridge between the wrangled data and the static UI:

* one canonical entity index and href precedence;
* one page-metadata registry keyed by surface id;
* one definitions document derived from the metric registry plus curated terms;
* one append-only public changelog.

It never re-derives a published number. Citations and page provenance resolve
references at render time; the semantic documents contain identity, links,
source-layer ids and metric ids, not a second copy of a value.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fitba.metrics.models import MetricRegistry
from fitba.normalize.entities import (
    EntityRef,
    claim_href,
    club_href,
    entity_id,
    fixture_href,
    former_href,
    page_href,
    player_href,
    scouting_href,
    season_href,
    staff_href,
)
from fitba.normalize.players import normalize_player_name
from fitba.settings import CONFIG_DIR, REFERENCE_DIR, load_yaml

PAGES_PATH = CONFIG_DIR / "pages.yaml"
DEFINITIONS_PATH = REFERENCE_DIR / "definitions.yaml"
CHANGELOG_PATH = REFERENCE_DIR / "changelog.yaml"
CANONICAL_BASE_URL = "https://patrickmockridge.github.io/fitba/"


@dataclass(slots=True)
class SemanticBundle:
    entities: dict[str, Any]
    scouted: dict[str, Any]
    page_meta: dict[str, Any]
    definitions: dict[str, Any]
    changelog: dict[str, Any]


def _load_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    document = load_yaml(path)
    return document if isinstance(document, dict) else {}


def _normalized(value: Any) -> str:
    return normalize_player_name(str(value or ""))


def _aliases(entities: list[dict[str, Any]]) -> None:
    """Keep an alias only when it identifies one entity; never guess."""
    counts: Counter[str] = Counter()
    for entity in entities:
        for alias in entity.get("aliases") or []:
            normalized = _normalized(alias)
            if normalized:
                counts[normalized] += 1
    for entity in entities:
        entity["aliases"] = [
            alias
            for alias in entity.get("aliases") or []
            if alias and counts.get(_normalized(alias), 0) == 1
        ]


def _player_layers() -> tuple[str, ...]:
    return ("squad_roster", "squad_identity", "lineups_roles")


def _entity(
    *,
    kind: str,
    value: str,
    name: str,
    href: str | None,
    aliases: list[str] | None = None,
    external_ids: dict[str, str] | None = None,
    routes: dict[str, str] | None = None,
    href_kind: str = "primary",
    indexable: bool = True,
    no_href_reason: str | None = None,
    search_group: str | None = None,
    sitemap: bool = False,
    source_layers: tuple[str, ...] | list[str] = (),
    league: str | None = None,
    role_family: str | None = None,
) -> EntityRef:
    return EntityRef(
        entity_id=entity_id(kind, value),
        type=kind,
        name=name,
        href=href,
        href_kind=href_kind,
        aliases=tuple(dict.fromkeys(alias for alias in (aliases or []) if alias)),
        external_ids=external_ids or {},
        routes=routes or {},
        indexable=indexable,
        no_href_reason=no_href_reason,
        search_group=search_group or kind,
        sitemap=sitemap,
        source_layers=tuple(source_layers),
        league=league,
        role_family=role_family,
    )


def _page_entities(pages_config: dict[str, Any]) -> list[EntityRef]:
    output: list[EntityRef] = []
    for row in pages_config.get("static_pages") or []:
        path = str(row.get("path") or "/")
        name = str(row.get("name") or row.get("id") or path)
        output.append(
            _entity(
                kind="page",
                value=str(row.get("id") or path.strip("/") or "home"),
                name=name,
                href=page_href(path),
                aliases=[str(row.get("id") or "")],
                search_group="page",
            )
        )
    return output


def _club_entities(
    tables: dict[str, Any],
    *,
    layers: list[str],
) -> list[EntityRef]:
    output: dict[str, EntityRef] = {}
    for competition_id, table in tables.items():
        for row in getattr(table, "to_dicts", lambda: [])():
            team_id = str(row.get("team_id") or "")
            if not team_id.startswith("sco:") or team_id.startswith("sco:provisional"):
                continue
            name = str(row.get("team_name") or team_id)
            output[team_id] = _entity(
                kind="club",
                value=team_id,
                name=name,
                href=club_href(team_id, competition_id),
                aliases=[name],
                search_group="club",
                source_layers=layers,
                no_href_reason=None
                if club_href(team_id, competition_id)
                else "no_current_table_anchor",
            )
    return list(output.values())


def _squad_entities(squad: dict[str, Any]) -> list[EntityRef]:
    output: list[EntityRef] = []
    seen: set[str] = set()
    for player in [*(squad.get("players") or []), *(squad.get("excluded_players") or [])]:
        key = str(player.get("player_key") or "")
        player_id = player.get("player_id")
        if not key or player_id is None or key in seen:
            continue
        seen.add(key)
        name = str(player.get("name") or player.get("full_name") or key)
        href = str(player.get("href") or player_href(player_id))
        output.append(
            _entity(
                kind="player",
                value=key,
                name=name,
                href=href,
                aliases=[name, str(player.get("full_name") or "")],
                external_ids={"api_football": str(player_id)},
                routes={"player": href},
                search_group="player",
                sitemap=True,
                source_layers=_player_layers(),
            )
        )
    return output


def _former_entities(former: dict[str, Any]) -> list[EntityRef]:
    output: list[EntityRef] = []
    for player in former.get("players") or []:
        key = str(player.get("player_key") or "")
        if not key:
            continue
        player_id = player.get("player_id")
        name = str(player.get("name") or key)
        profile = scouting_href(player_id)
        register = str(player.get("href") or former_href(key, player_id))
        routes = {"former": register}
        if profile:
            routes["scouting"] = profile
        output.append(
            _entity(
                kind="player",
                value=key,
                name=name,
                href=profile or register,
                aliases=[name],
                external_ids={"api_football": str(player_id)} if player_id else {},
                routes=routes,
                href_kind="profile" if profile else "register",
                search_group="former-player",
                sitemap=bool(profile),
                source_layers=("former_player_record", "transfer_register"),
            )
        )
    return output


def _full_name_map(scouting_bundle: dict[str, Any]) -> dict[int, str]:
    output: dict[int, str] = {}
    for document in (scouting_bundle.get("pools") or {}).values():
        for player in document.get("players") or []:
            player_id = player.get("player_id")
            if player_id is None:
                continue
            name = str(player.get("full_name") or player.get("name") or "")
            if name:
                output[int(player_id)] = name
    return output


def _scouted_entities(
    scouting_bundle: dict[str, Any],
    *,
    excluded_keys: set[str],
) -> list[EntityRef]:
    full_names = _full_name_map(scouting_bundle)
    output: list[EntityRef] = []
    seen: set[str] = set()
    for row in (scouting_bundle.get("search") or {}).get("players") or []:
        player_id = row.get("i")
        if player_id is None:
            continue
        key = f"api:player:{player_id}"
        if key in excluded_keys or key in seen:
            continue
        seen.add(key)
        name = full_names.get(int(player_id)) or str(row.get("n") or key)
        league = str(row.get("l") or "")
        role = str(row.get("rf") or "")
        href = scouting_href(player_id)
        if not href:
            continue
        output.append(
            _entity(
                kind="player",
                value=key,
                name=name,
                href=href,
                aliases=[name, str(row.get("n") or ""), league, role],
                external_ids={"api_football": str(player_id)},
                routes={"scouting": href},
                search_group="scouted-player",
                sitemap=True,
                source_layers=("scouting_pool", "scouting_current_clubs"),
                league=league or None,
                role_family=role or None,
            )
        )
    return output


def _fixture_entities(fixture_index: dict[str, Any]) -> list[EntityRef]:
    output: list[EntityRef] = []
    seen: set[int] = set()
    for row in fixture_index.get("fixtures") or []:
        fixture_id = row.get("fixture_id")
        if fixture_id is None or int(fixture_id) in seen:
            continue
        seen.add(int(fixture_id))
        home = str(row.get("home_team_name") or "Home")
        away = str(row.get("away_team_name") or "Away")
        home_goals = row.get("home_goals")
        away_goals = row.get("away_goals")
        name = (
            f"{home} {home_goals}-{away_goals} {away}"
            if home_goals is not None and away_goals is not None
            else f"{home} v {away}"
        )
        href = str(row.get("href") or fixture_href(fixture_id))
        output.append(
            _entity(
                kind="fixture",
                value=str(fixture_id),
                name=name,
                href=href,
                aliases=[name, f"{home} v {away}"],
                external_ids={"api_football": str(fixture_id)},
                search_group="match",
                sitemap=True,
                source_layers=("club_fixtures", "lineups_roles", "player_match_stats"),
            )
        )
    return output


def _season_entities(history_index: dict[str, Any]) -> list[EntityRef]:
    output: list[EntityRef] = []
    for row in history_index.get("seasons") or []:
        season = str(row.get("season") or "")
        if not season:
            continue
        href = str(row.get("href") or season_href(season))
        output.append(
            _entity(
                kind="season",
                value=season,
                name=f"Aberdeen {season}",
                href=href,
                aliases=[season, str(row.get("headline") or "")],
                search_group="season",
                sitemap=True,
                source_layers=("history",),
            )
        )
    return output


def _staff_entities(history_index: dict[str, Any]) -> list[EntityRef]:
    output: list[EntityRef] = []
    for person in history_index.get("staff") or []:
        person_id = str(person.get("person_id") or "")
        name = str(person.get("name") or person_id)
        if not person_id:
            continue
        output.append(
            _entity(
                kind="staff",
                value=person_id,
                name=name,
                href=staff_href(person_id),
                aliases=[name],
                search_group="staff",
                source_layers=("history",),
            )
        )
    return output


def _claim_entities(case_payload: dict[str, Any]) -> list[EntityRef]:
    output: list[EntityRef] = []
    for claim in case_payload.get("claims") or []:
        claim_id = str(claim.get("id") or "")
        if not claim_id:
            continue
        title = str(claim.get("title") or claim_id)
        output.append(
            _entity(
                kind="claim",
                value=claim_id,
                name=title,
                href=claim_href(claim_id),
                aliases=[title, claim_id],
                search_group="claim",
                source_layers=("themes",),
            )
        )
    return output


def build_entities(
    *,
    squad: dict[str, Any],
    former: dict[str, Any],
    scouting_bundle: dict[str, Any],
    fixture_index: dict[str, Any],
    history_index: dict[str, Any],
    case_payload: dict[str, Any],
    tables: dict[str, Any],
    pages_config: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    pages = pages_config or _load_optional(PAGES_PATH)
    layers = {
        str(row.get("id")): [str(item) for item in row.get("layers") or []]
        for row in pages.get("pages") or []
    }
    core = [
        *_page_entities(pages),
        *_club_entities(tables, layers=layers.get("scotland") or []),
        *_squad_entities(squad),
        *_former_entities(former),
        *_fixture_entities(fixture_index),
        *_season_entities(history_index),
        *_staff_entities(history_index),
        *_claim_entities(case_payload),
    ]
    core_keys = {entity.entity_id for entity in core}
    scouted = _scouted_entities(
        scouting_bundle,
        excluded_keys={
            str(entity.entity_id).split(":", 1)[1]
            for entity in core
            if entity.type == "player"
        },
    )
    scouted = [
        entity for entity in scouted if entity.entity_id not in core_keys
    ]
    core_dicts = [entity.to_dict() for entity in core]
    scouted_dicts = [entity.to_dict() for entity in scouted]
    _aliases(core_dicts)
    _aliases(scouted_dicts)
    scouted_dicts = [
        {
            "i": str(row["entity_id"]).rsplit(":", 1)[-1],
            "n": row.get("name"),
            "a": row.get("aliases") or [],
            "h": row.get("href"),
            "l": row.get("league"),
            "rf": row.get("role_family"),
        }
        for row in scouted_dicts
    ]
    return (
        {
            "schema_version": "1.0.0",
            "state": "available",
            "entities": core_dicts,
        },
        {
            "schema_version": "1.0.0",
            "state": "available",
            "entities": scouted_dicts,
        },
    )


def _surface_prefix(pattern: str) -> str:
    return pattern.split("{", 1)[0]


def _metrics_for_surface(registry: MetricRegistry, patterns: list[str]) -> list[str]:
    prefixes = [_surface_prefix(pattern) for pattern in patterns]
    output: list[str] = []
    for metric in registry.metrics:
        surfaces = [metric.home_surface, *metric.displayed_surfaces]
        if any(
            surface == prefix
            or (prefix != "/" and surface.startswith(prefix))
            or (surface != "/" and prefix.startswith(surface))
            for surface in surfaces
            for prefix in prefixes
        ):
            output.append(metric.id)
    return sorted(dict.fromkeys(output))


def build_page_meta(
    *,
    registry: MetricRegistry,
    registry_checksum: str,
    generated_at: str,
    dataset_version: str,
    update_id: str,
    source_snapshots: dict[str, Any],
    pages_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pages = pages_config or _load_optional(PAGES_PATH)
    surfaces: dict[str, Any] = {}
    for row in pages.get("pages") or []:
        surface_id = str(row.get("id") or "")
        if not surface_id:
            continue
        patterns = [str(item) for item in row.get("patterns") or []]
        layers = [str(item) for item in row.get("layers") or []]
        metrics = _metrics_for_surface(registry, patterns)
        surfaces[surface_id] = {
            "label": str(row.get("label") or surface_id),
            "route_patterns": patterns,
            "layers": layers,
            "metrics": metrics,
            "no_layers_reason": row.get("no_layers_reason"),
        }
    return {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "dataset_id": dataset_version,
        "update_id": update_id,
        "source_snapshots": source_snapshots,
        "canonical_base_url": CANONICAL_BASE_URL,
        "registry_version": registry.registry_version,
        "registry_checksum": registry_checksum,
        "surfaces": surfaces,
    }


def build_definitions(
    *,
    registry: MetricRegistry,
    registry_checksum: str,
    definitions_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = definitions_config or _load_optional(DEFINITIONS_PATH)
    entries: list[dict[str, Any]] = []
    for metric in registry.metrics:
        if metric.status != "active":
            continue
        entries.append(
            {
                "id": f"metric.{metric.id}",
                "term": metric.label,
                "aliases": [],
                "short": metric.description,
                "body": metric.description,
                "category": "metric",
                "metric_ids": [metric.id],
                "formula": metric.formula,
                "unit": metric.unit,
                "basis": metric.basis,
                "coverage_tier": metric.coverage_tier,
                "source_layer": metric.source_layer,
                "limitations": metric.limitations,
                "href": f"/metrics/#metric-{metric.id}",
                "provenance": "registry",
                "registry_version": registry.registry_version,
            }
        )
    known_metrics = {metric.id for metric in registry.metrics}
    for term in config.get("terms") or []:
        term_id = str(term.get("id") or "")
        if not term_id:
            continue
        metric_ids = [str(item) for item in term.get("metric_ids") or []]
        unknown = [item for item in metric_ids if item not in known_metrics]
        if unknown:
            raise ValueError(f"definition {term_id}: unknown metric ids {unknown}")
        entries.append(
            {
                "id": f"def.{term_id}",
                "term": str(term.get("term") or term_id),
                "aliases": [str(item) for item in term.get("aliases") or []],
                "short": str(term.get("short") or ""),
                "body": str(term.get("body") or "").strip(),
                "category": str(term.get("category") or "concept"),
                "metric_ids": metric_ids,
                "formula": None,
                "unit": None,
                "basis": None,
                "coverage_tier": None,
                "source_layer": None,
                "limitations": [],
                "href": f"/glossary/#def-{term_id}",
                "provenance": "curated_overlay",
                "registry_version": registry.registry_version,
            }
        )
    _aliases(entries)
    return {
        "schema_version": "1.0.0",
        "registry_version": registry.registry_version,
        "registry_checksum": registry_checksum,
        "reviewed": str(config.get("reviewed") or ""),
        "owner": str(config.get("owner") or ""),
        "entries": entries,
    }


def _iso_value(value: Any) -> Any:
    """YAML reads an unquoted date as ``datetime.date``; publish it as text."""
    return value.isoformat() if hasattr(value, "isoformat") else value


def build_changelog(
    *,
    changelog_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = changelog_config or _load_optional(CHANGELOG_PATH)
    entries = [dict(row) for row in config.get("entries") or []]
    for row in entries:
        for field in ("date", "fixed_in_dataset"):
            if field in row:
                row[field] = _iso_value(row[field])
    # Newest first; within one date, the id is ascending. Two stable passes
    # keep this deterministic without reversing the id order.
    entries.sort(key=lambda row: str(row.get("id") or ""))
    entries.sort(key=lambda row: str(row.get("date") or ""), reverse=True)
    return {
        "schema_version": "1.0.0",
        "last_reviewed": str(_iso_value(config.get("last_reviewed")) or ""),
        "contact_url": str(config.get("contact_url") or ""),
        "note": str(config.get("note") or "").strip(),
        "append_only": bool(config.get("append_only")),
        "entries": entries,
    }


def build_semantic_bundle(
    *,
    squad: dict[str, Any],
    former: dict[str, Any],
    scouting_bundle: dict[str, Any],
    fixture_index: dict[str, Any],
    history_index: dict[str, Any],
    case_payload: dict[str, Any],
    tables: dict[str, Any],
    registry: MetricRegistry,
    registry_checksum: str,
    generated_at: str,
    dataset_version: str,
    update_id: str,
    source_snapshots: dict[str, Any],
    pages_config: dict[str, Any] | None = None,
    definitions_config: dict[str, Any] | None = None,
    changelog_config: dict[str, Any] | None = None,
) -> SemanticBundle:
    entities, scouted = build_entities(
        squad=squad,
        former=former,
        scouting_bundle=scouting_bundle,
        fixture_index=fixture_index,
        history_index=history_index,
        case_payload=case_payload,
        tables=tables,
        pages_config=pages_config,
    )
    return SemanticBundle(
        entities=entities,
        scouted=scouted,
        page_meta=build_page_meta(
            registry=registry,
            registry_checksum=registry_checksum,
            generated_at=generated_at,
            dataset_version=dataset_version,
            update_id=update_id,
            source_snapshots=source_snapshots,
            pages_config=pages_config,
        ),
        definitions=build_definitions(
            registry=registry,
            registry_checksum=registry_checksum,
            definitions_config=definitions_config,
        ),
        changelog=build_changelog(changelog_config=changelog_config),
    )


__all__ = [
    "SemanticBundle",
    "build_changelog",
    "build_definitions",
    "build_entities",
    "build_page_meta",
    "build_semantic_bundle",
]
