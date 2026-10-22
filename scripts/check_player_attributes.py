#!/usr/bin/env python3
"""CI guard for the published preferred-foot payload.

Every non-null foot value must have a registered, allowed source, a URL, a
verification date and a derivation. Conflicts publish no value. Unknown is a
valid, explicit state. Side is not checked here: it is derived from the role,
not resolved as an attribute.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SQUAD = ROOT / "web" / "data" / "generated" / "squad" / "aberdeen.json"
SOURCES = ROOT / "config" / "sources.yaml"

ALLOWED = {
    "preferred_foot": {"left", "right", "both"},
}
VALID_STATUS = {"known", "unknown", "conflict"}
VALID_COVERAGE = {"known", "unknown", "conflict"}
FORBIDDEN_KEYS = {
    "source_text",
    "evidence_text",
    "wikitext",
    "raw_html",
    "alternate_sources",
    "birth_date",
}


def _walk(payload: Any, path: str = "") -> list[tuple[str, Any]]:
    items = [(path, payload)]
    if isinstance(payload, dict):
        for key, value in payload.items():
            items.extend(_walk(value, f"{path}.{key}" if path else key))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            items.extend(_walk(value, f"{path}[{index}]"))
    return items


def _source_registry() -> dict[str, Any]:
    return yaml.safe_load(SOURCES.read_text(encoding="utf-8")).get("sources", {})


def _check_attribute(
    player: dict[str, Any],
    attribute: str,
    block: dict[str, Any],
    sources: dict[str, Any],
    errors: list[str],
) -> None:
    pid = player.get("player_id")
    status = block.get("status")
    value = block.get("value")
    if status not in VALID_STATUS:
        errors.append(f"{pid}: {attribute} invalid status {status!r}")
        return
    if status == "known":
        if value not in ALLOWED[attribute]:
            errors.append(f"{pid}: {attribute} invalid value {value!r}")
        source = block.get("source")
        if not isinstance(source, dict):
            errors.append(f"{pid}: {attribute} known without a source")
            return
        for field in ("id", "tier", "url", "verified_at", "confidence", "derivation"):
            if source.get(field) in (None, ""):
                errors.append(f"{pid}: {attribute} source missing {field}")
        source_id = str(source.get("id") or "")
        registry = sources.get(source_id)
        if registry is None:
            errors.append(f"{pid}: {attribute} unknown source {source_id!r}")
        else:
            if registry.get("lane") == "no_publication":
                errors.append(
                    f"{pid}: {attribute} uses a source not allowed for publication {source_id}"
                )
            if "player_attributes" not in (registry.get("capabilities") or []):
                errors.append(f"{pid}: {attribute} source {source_id} lacks capability")
        url = str(source.get("url") or "")
        if url and not url.startswith(("http://", "https://")):
            errors.append(f"{pid}: {attribute} source URL is not http(s)")
        if source_id == "wikipedia":
            if not source.get("revision"):
                errors.append(f"{pid}: {attribute} Wikipedia source has no revision")
            if "oldid=" not in url:
                errors.append(f"{pid}: {attribute} Wikipedia source is not a permalink")
        if block.get("conflict_state") == "unresolved":
            errors.append(f"{pid}: {attribute} known value is marked unresolved")
    elif status == "conflict":
        if value is not None:
            errors.append(f"{pid}: {attribute} conflict has a value")
        if block.get("conflict_state") != "unresolved":
            errors.append(f"{pid}: {attribute} conflict state is not unresolved")
        conflict_sources = block.get("conflict_sources") or []
        if len(conflict_sources) < 2:
            errors.append(f"{pid}: {attribute} conflict lists fewer than two sources")
        for item in conflict_sources:
            if item.get("source_id") not in sources:
                errors.append(f"{pid}: {attribute} conflict has unknown source")
    else:
        if value is not None:
            errors.append(f"{pid}: {attribute} unknown has a value")
        if block.get("source") is not None:
            errors.append(f"{pid}: {attribute} unknown has a source")
        if not block.get("unknown_reason"):
            errors.append(f"{pid}: {attribute} unknown has no reason")


def main() -> int:
    if not SQUAD.exists():
        print(f"missing {SQUAD}")
        return 1
    squad = json.loads(SQUAD.read_text(encoding="utf-8"))
    players = squad.get("players", [])
    sources = _source_registry()
    errors: list[str] = []
    if not players:
        errors.append("squad payload is empty")
    if not squad.get("attributes_meta"):
        errors.append("missing attributes_meta")

    for player in players:
        attributes = player.get("attributes")
        if not isinstance(attributes, dict):
            errors.append(f"{player.get('player_id')}: missing attributes block")
            continue
        block = attributes.get("preferred_foot")
        if not isinstance(block, dict):
            errors.append(f"{player.get('player_id')}: missing preferred_foot")
            continue
        _check_attribute(player, "preferred_foot", block, sources, errors)
        expected = (
            "conflict"
            if block.get("status") == "conflict"
            else "known"
            if block.get("status") == "known"
            else "unknown"
        )
        if attributes.get("coverage") not in VALID_COVERAGE:
            errors.append(f"{player.get('player_id')}: invalid attribute coverage")
        elif attributes.get("coverage") != expected:
            errors.append(f"{player.get('player_id')}: attribute coverage mismatch")

    summary = squad.get("summary", {})
    expected_summary = {
        "attributes_foot_known": sum(
            1
            for player in players
            if (player.get("attributes") or {}).get("preferred_foot", {}).get("status") == "known"
        ),
        "attributes_unknown": sum(
            1 for player in players if (player.get("attributes") or {}).get("coverage") == "unknown"
        ),
        "attributes_conflicts": sum(
            1
            for player in players
            if (player.get("attributes") or {}).get("coverage") == "conflict"
        ),
    }
    for field, expected in expected_summary.items():
        if summary.get(field) != expected:
            errors.append(f"summary {field} mismatch")

    meta = squad.get("attributes_meta") or {}
    if meta.get("known") != sum(
        1
        for player in players
        for block in (player.get("attributes") or {}).values()
        if isinstance(block, dict) and block.get("status") == "known"
    ):
        errors.append("attributes_meta known count mismatch")
    if meta.get("conflicts") != sum(
        1
        for player in players
        for block in (player.get("attributes") or {}).values()
        if isinstance(block, dict) and block.get("status") == "conflict"
    ):
        errors.append("attributes_meta conflict count mismatch")

    for path, _value in _walk(squad):
        key = path.split(".")[-1].split("[")[0]
        if key in FORBIDDEN_KEYS:
            errors.append(f"published payload contains forbidden key {path}")

    if errors:
        print("Preferred-foot publication check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        "Preferred-foot publication check passed "
        f"({len(players)} players, {summary.get('attributes_foot_known', 0)} known, "
        f"{summary.get('attributes_conflicts', 0)} conflicts, "
        f"{summary.get('attributes_unknown', 0)} unknown)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
