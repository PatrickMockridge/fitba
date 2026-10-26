#!/usr/bin/env python3
"""Validate the published semantic layer and its built links.

Data mode checks the canonical entity index, page metadata, definitions and
changelog against the published payloads and config. Page mode checks that every
entity href and fragment resolves in the static export.

The semantic layer is navigation and provenance metadata. It must not introduce
an unregistered number or a second copy of a value.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "web" / "data" / "generated"
DEFAULT_OUT = ROOT / "web" / "out"
DOCS = ROOT / "docs" / "metric-changes.md"

ENTITY_TYPES = {"page", "club", "player", "fixture", "season", "staff", "claim"}
KINDS = {"correction", "metric", "source", "page", "data"}
STATUSES = {"fixed", "reviewing", "withdrawn", "published"}
FORBIDDEN = ("/analysis/#claim-", "github.com")


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _href_parts(href: str) -> tuple[str, str | None]:
    base, _, fragment = href.partition("#")
    return base, fragment or None


def _check_entities(
    document: dict[str, Any],
    *,
    name: str,
    errors: list[str],
    core_ids: set[str] | None = None,
) -> set[str]:
    entities = document.get("entities") or []
    ids: set[str] = set()
    aliases: dict[str, str] = {}
    external: dict[tuple[str, str], str] = {}
    for entity in entities:
        entity_id = str(entity.get("entity_id") or "")
        if not entity_id:
            # The scouted projection uses a compact numeric id.
            compact = str(entity.get("i") or "")
            entity_id = f"player:api:player:{compact}" if compact else ""
        if not entity_id:
            errors.append(f"{name}: entity without an id")
            continue
        if entity_id in ids:
            errors.append(f"{name}: duplicate entity id {entity_id}")
        ids.add(entity_id)
        kind = str(entity.get("type") or "player")
        if kind not in ENTITY_TYPES:
            errors.append(f"{name}: {entity_id}: unknown type {kind}")
        if not entity_id.startswith(f"{kind}:"):
            errors.append(f"{name}: {entity_id}: id does not match type {kind}")
        href = entity.get("href")
        if entity.get("indexable") and (
            not isinstance(href, str) or not href.startswith("/")
        ):
            errors.append(f"{name}: {entity_id}: indexable without an internal href")
        if href is not None and (not isinstance(href, str) or not href.startswith("/")):
            errors.append(f"{name}: {entity_id}: href is not internal")
        for alias in entity.get("aliases") or []:
            key = str(alias).casefold().strip()
            if not key:
                continue
            previous = aliases.get(key)
            if previous is not None and previous != entity_id:
                errors.append(f"{name}: alias {alias!r} identifies {previous} and {entity_id}")
            aliases[key] = entity_id
        for source, value in (entity.get("external_ids") or {}).items():
            key = (str(source), str(value))
            previous = external.get(key)
            if previous is not None and previous != entity_id:
                errors.append(f"{name}: external id {source}:{value} is duplicated")
            external[key] = entity_id
    if core_ids is not None:
        overlap = ids & core_ids
        if overlap:
            errors.append(f"{name}: overlaps core entities: {sorted(overlap)[:5]}")
    return ids


def _check_clubs(
    entities: list[dict[str, Any]], tables: dict[str, dict[str, Any]], errors: list[str]
) -> None:
    rows: dict[tuple[str, str], str] = {}
    for competition_id, table in tables.items():
        tier = str(competition_id).split(":", 1)[-1]
        for row in table.get("rows") or []:
            team_id = str(row.get("team_id") or "")
            if team_id:
                rows[(tier, team_id.split(":", 1)[-1])] = str(row.get("team_name") or team_id)
    for entity in entities:
        if entity.get("type") != "club":
            continue
        href = entity.get("href")
        if not href:
            continue
        base, fragment = _href_parts(href)
        match = re.fullmatch(r"/scotland/([^/]+)/", base)
        if not match or not fragment or not fragment.startswith("club-"):
            errors.append(f"club {entity.get('entity_id')}: invalid table href {href}")
            continue
        if (match.group(1), fragment.removeprefix("club-")) not in rows:
            errors.append(f"club {entity.get('entity_id')}: table anchor does not exist")


def _check_fixtures(
    entities: list[dict[str, Any]],
    fixture_index: dict[str, Any],
    errors: list[str],
) -> None:
    known = {str(row.get("fixture_id")) for row in fixture_index.get("fixtures") or []}
    for entity in entities:
        if entity.get("type") != "fixture":
            continue
        value = str(entity.get("entity_id") or "").split(":", 1)[-1]
        if value not in known:
            errors.append(f"fixture {value}: not in fixtures/index.json")
        expected = f"/matches/{value}/"
        if entity.get("href") != expected:
            errors.append(f"fixture {value}: href {entity.get('href')!r} != {expected!r}")


def _check_claims(
    entities: list[dict[str, Any]], case_payload: dict[str, Any], errors: list[str]
) -> None:
    known = {str(row.get("id")) for row in case_payload.get("claims") or []}
    for entity in entities:
        if entity.get("type") != "claim":
            continue
        value = str(entity.get("entity_id") or "").split(":", 1)[-1]
        if value not in known:
            errors.append(f"claim {value}: not in themes/aberdeen.json")
        href = str(entity.get("href") or "")
        if href.startswith("/analysis/#claim-"):
            errors.append(f"claim {value}: still points at the removed analysis anchors")
        if not href.startswith("/claims/#claim-"):
            errors.append(f"claim {value}: href {href!r} is not the claims surface")
    for entity in entities:
        href = str(entity.get("href") or "")
        if "/analysis/#claim-" in href:
            errors.append(f"{entity.get('entity_id')}: stale analysis claim href")


def _check_page_meta(
    page_meta: dict[str, Any],
    *,
    provenance: dict[str, Any],
    registry: dict[str, Any],
    errors: list[str],
) -> None:
    layers = {str(row.get("id")) for row in provenance.get("layers") or []}
    metrics = {str(row.get("id")) for row in registry.get("metrics") or []}
    surfaces = page_meta.get("surfaces") or {}
    if not surfaces:
        errors.append("page-meta: no surfaces")
    for surface_id, surface in surfaces.items():
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", surface_id):
            errors.append(f"page-meta: invalid surface id {surface_id!r}")
        if not surface.get("route_patterns"):
            errors.append(f"page-meta: {surface_id}: no route patterns")
        surface_layers = surface.get("layers") or []
        if not surface_layers and not surface.get("no_layers_reason"):
            errors.append(f"page-meta: {surface_id}: no layers and no reason")
        for layer in surface_layers:
            if layer not in layers:
                errors.append(f"page-meta: {surface_id}: unknown layer {layer}")
        for metric in surface.get("metrics") or []:
            if metric not in metrics:
                errors.append(f"page-meta: {surface_id}: unknown metric {metric}")


def _check_definitions(
    definitions: dict[str, Any], registry: dict[str, Any], errors: list[str]
) -> None:
    registry_metrics = {str(row.get("id")): row for row in registry.get("metrics") or []}
    entries = definitions.get("entries") or []
    all_ids = {str(entry.get("id") or "") for entry in entries}
    ids: set[str] = set()
    aliases: dict[str, str] = {}
    for entry in entries:
        entry_id = str(entry.get("id") or "")
        if not entry_id or entry_id in ids:
            errors.append(f"definitions: duplicate or missing id {entry_id!r}")
        ids.add(entry_id)
        for related in entry.get("related") or []:
            if str(related) not in all_ids:
                errors.append(f"definitions: {entry_id}: unknown related id {related}")
            elif str(related) == entry_id:
                errors.append(f"definitions: {entry_id}: related points at itself")
        for metric_id in entry.get("metric_ids") or []:
            metric = registry_metrics.get(str(metric_id))
            if metric is None:
                errors.append(f"definitions: {entry_id}: unknown metric {metric_id}")
                continue
            if entry.get("provenance") == "registry":
                for field in ("basis", "coverage_tier", "source_layer"):
                    if entry.get(field) != metric.get(field):
                        errors.append(f"definitions: {entry_id}: {field} does not match registry")
        for alias in entry.get("aliases") or []:
            key = str(alias).casefold().strip()
            if not key:
                continue
            previous = aliases.get(key)
            if previous is not None and previous != entry_id:
                errors.append(f"definitions: alias {alias!r} is duplicated")
            aliases[key] = entry_id
        if entry.get("provenance") == "curated_overlay" and entry.get("formula"):
            errors.append(f"definitions: {entry_id}: curated overlay may not override a formula")


def _check_changelog(
    changelog: dict[str, Any],
    registry: dict[str, Any],
    errors: list[str],
) -> None:
    metric_ids = {str(row.get("id")) for row in registry.get("metrics") or []}
    ids: set[str] = set()
    versions: set[str] = set()
    heading_text = DOCS.read_text(encoding="utf-8") if DOCS.exists() else ""
    for entry in changelog.get("entries") or []:
        entry_id = str(entry.get("id") or "")
        if not entry_id or entry_id in ids:
            errors.append(f"changelog: duplicate or missing id {entry_id!r}")
        ids.add(entry_id)
        if not str(entry.get("date") or "").startswith("20"):
            errors.append(f"changelog: {entry_id}: invalid date")
        if entry.get("kind") not in KINDS:
            errors.append(f"changelog: {entry_id}: invalid kind")
        if entry.get("status") not in STATUSES:
            errors.append(f"changelog: {entry_id}: invalid status")
        for metric_id in entry.get("metric_ids") or []:
            if str(metric_id) not in metric_ids:
                errors.append(f"changelog: {entry_id}: unknown metric {metric_id}")
        for page in entry.get("pages") or []:
            if not str(page).startswith("/"):
                errors.append(f"changelog: {entry_id}: page {page!r} is not internal")
        for evidence in entry.get("evidence") or []:
            url = str(evidence.get("url") or "")
            if any(token in url for token in FORBIDDEN):
                errors.append(f"changelog: {entry_id}: blocked evidence URL {url}")
        if entry.get("kind") == "metric":
            version = str(entry.get("registry_version") or "")
            if not version:
                errors.append(f"changelog: {entry_id}: metric entry has no registry version")
            else:
                versions.add(version)
                if version not in heading_text:
                    errors.append(
                        f"changelog: {entry_id}: registry version {version} "
                        "has no metric-changes heading"
                    )
    if not changelog.get("append_only"):
        errors.append("changelog: append_only must be true")


def check_data(data: Path) -> list[str]:
    errors: list[str] = []
    required = (
        "entities/index.json",
        "entities/scouted.json",
        "page-meta.json",
        "definitions.json",
        "changelog.json",
    )
    documents = {name: _load(data / name) for name in required}
    for name, document in documents.items():
        if document is None:
            errors.append(f"missing or invalid {name}")
    if errors:
        return errors
    index = documents["entities/index.json"]
    scouted = documents["entities/scouted.json"]
    core_ids = _check_entities(index, name="entities/index.json", errors=errors)
    _check_entities(
        scouted,
        name="entities/scouted.json",
        errors=errors,
        core_ids=core_ids,
    )
    entities = index.get("entities") or []
    tables: dict[str, dict[str, Any]] = {}
    for path in sorted((data / "tables").glob("*.json")):
        table = _load(path)
        if isinstance(table, dict):
            tables[str(table.get("competition_id") or path.stem)] = table
    fixture_index = _load(data / "fixtures/index.json") or {}
    case_payload = _load(data / "themes/aberdeen.json") or {}
    _check_clubs(entities, tables, errors)
    _check_fixtures(entities, fixture_index, errors)
    _check_claims(entities, case_payload, errors)
    provenance = _load(data / "provenance.json") or {}
    registry = _load(data / "metrics/registry.json") or {}
    _check_page_meta(
        documents["page-meta.json"],
        provenance=provenance,
        registry=registry,
        errors=errors,
    )
    _check_definitions(documents["definitions.json"], registry, errors)
    _check_changelog(documents["changelog.json"], registry, errors)
    # The old ad hoc index must not survive as a second source.
    if (data / "search-index.json").exists():
        errors.append("search-index.json still exists; use entities/index.json")
    for relative in required:
        text = (data / relative).read_text(encoding="utf-8", errors="ignore")
        for token in FORBIDDEN:
            if token in text:
                errors.append(f"{relative}: contains {token!r}")
    return errors


def _built_page(out: Path, href: str, base_path: str) -> Path | None:
    base, _ = _href_parts(href)
    if base_path and base.startswith(base_path):
        base = base[len(base_path) :]
    base = base.strip("/")
    path = out / base / "index.html" if base else out / "index.html"
    return path if path.exists() else None


def check_pages(data: Path, out: Path, base_path: str = "") -> list[str]:
    errors = check_data(data)
    index = _load(data / "entities/index.json") or {}
    scouted = _load(data / "entities/scouted.json") or {}
    for name, document in (("core", index), ("scouted", scouted)):
        for entity in document.get("entities") or []:
            href = entity.get("href")
            if not href:
                continue
            page = _built_page(out, href, base_path)
            entity_id = entity.get("entity_id") or entity.get("i")
            if page is None:
                errors.append(f"{name}: {entity_id}: missing built page for {href}")
                continue
            _, fragment = _href_parts(href)
            if fragment:
                html = page.read_text(encoding="utf-8", errors="ignore")
                if not re.search(rf'id=["\']{re.escape(fragment)}["\']', html):
                    errors.append(f"{name}: {entity_id}: missing fragment #{fragment}")
    definitions = _load(data / "definitions.json") or {}
    definition_hrefs: dict[str, str] = {}
    for entry in definitions.get("entries") or []:
        href = str(entry.get("href") or "")
        entry_id = str(entry.get("id") or entry.get("term"))
        definition_hrefs[entry_id] = href
        if not href.startswith("/"):
            errors.append(f"definitions: {entry_id}: href is not internal")
            continue
        page = _built_page(out, href, base_path)
        if page is None:
            errors.append(f"definitions: {entry_id}: missing built page for {href}")
            continue
        _, fragment = _href_parts(href)
        if fragment:
            html = page.read_text(encoding="utf-8", errors="ignore")
            if not re.search(rf'id=["\']{re.escape(fragment)}["\']', html):
                errors.append(f"definitions: {entry_id}: missing fragment #{fragment}")
    for page in out.rglob("index.html"):
        html = page.read_text(encoding="utf-8", errors="ignore")
        if "/analysis/#claim-" in html:
            errors.append(f"{page.relative_to(out)}: stale analysis claim link")
        for term in re.findall(r'data-definition-term=["\']([^"\']+)["\']', html):
            if term not in definition_hrefs:
                errors.append(f"{page.relative_to(out)}: unknown definition term {term}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--pages", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-path", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    errors = (
        check_pages(args.data, args.out, args.base_path)
        if args.pages
        else check_data(args.data)
    )
    if args.json:
        print(json.dumps({"status": "pass" if not errors else "fail", "errors": errors}, indent=2))
    else:
        for error in errors[:100]:
            print(f"error: {error}")
        print(
            f"{'PASS' if not errors else 'FAIL'} semantic check: "
            f"{len(errors)} error(s)"
        )
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
