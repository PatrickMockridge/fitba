#!/usr/bin/env python3
"""CI guard for the published data-provenance truth table."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from fitba.publish.provenance import ProvenanceDocument, provenance_schema
from fitba.settings import source_registry

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "web" / "data" / "generated"
DOCUMENT = GENERATED / "provenance.json"
SCHEMA = ROOT / "contracts" / "provenance.schema.json"
MANIFEST = GENERATED / "manifest.json"
MAX_FILE_BYTES = 2_000_000
SPECIAL_PRIMARIES = {"computed", "curated", "mixed", "derived", "none"}
STALE_PHRASES = (
    "league cup from the spfl club feed",
    "league and league cup fixtures come from the spfl",
    "after the key-test",
    "next phase moves public data to a licensed api-football base",
    "transfers/loans, injuries",
)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        output: list[str] = []
        for key, item in value.items():
            output.append(str(key))
            output.extend(_strings(item))
        return output
    if isinstance(value, list):
        output = []
        for item in value:
            output.extend(_strings(item))
        return output
    return []


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    if not DOCUMENT.exists():
        print(f"missing {DOCUMENT}; run `uv run fitba publish`")
        return 1
    document = _load(DOCUMENT)
    try:
        ProvenanceDocument(**document)
    except ValidationError as error:
        errors.append(f"provenance.json does not validate: {error}")
    if SCHEMA.exists():
        if _load(SCHEMA) != provenance_schema():
            errors.append(f"{SCHEMA} is stale; regenerate it from the Pydantic model")
    else:
        errors.append(f"missing {SCHEMA}")

    registry = (source_registry() or {}).get("sources") or {}
    layer_ids = [layer.get("id") for layer in document.get("layers") or []]
    if len(layer_ids) != len(set(layer_ids)):
        errors.append("duplicate provenance layer ids")
    if len(layer_ids) < 10:
        errors.append(f"provenance matrix has only {len(layer_ids)} layers")
    for layer in document.get("layers") or []:
        primary = str(layer.get("primary"))
        if primary not in SPECIAL_PRIMARIES and primary not in registry:
            errors.append(f"{layer.get('id')}: unknown primary source {primary!r}")
        for fallback in layer.get("fallback") or []:
            if fallback not in registry:
                errors.append(f"{layer.get('id')}: unknown fallback source {fallback!r}")

    primary_layers: dict[str, set[str]] = {}
    for layer in document.get("layers") or []:
        primary = str(layer.get("primary"))
        if primary in SPECIAL_PRIMARIES:
            continue
        primary_layers.setdefault(primary, set()).add(str(layer.get("id")))
    for source in document.get("sources") or []:
        source_id = str(source.get("id"))
        if source_id not in registry:
            errors.append(f"source summary {source_id!r} is not registered")
            continue
        expected = sorted(primary_layers.get(source_id, set()))
        actual = sorted(source.get("primary_layers") or [])
        if expected != actual:
            errors.append(f"{source_id}: primary_layers {actual} != matrix {expected}")
        if int(source.get("rows") or 0) < 0:
            errors.append(f"{source_id}: negative rows")

    for text in _strings(document):
        lowered = text.casefold()
        for phrase in STALE_PHRASES:
            if phrase in lowered:
                errors.append(f"stale source claim in provenance: {phrase!r}")

    for path in (
        ROOT / "docs" / "sources.md",
        ROOT / "README.md",
        ROOT / "web" / "app" / "methodology" / "page.tsx",
        ROOT / "web" / "app" / "sources" / "page.tsx",
    ):
        if not path.exists():
            continue
        lowered = path.read_text(encoding="utf-8").casefold()
        for phrase in STALE_PHRASES:
            if phrase in lowered:
                errors.append(f"{path.relative_to(ROOT)}: stale source claim {phrase!r}")

    if DOCUMENT.stat().st_size > MAX_FILE_BYTES:
        errors.append(f"{DOCUMENT} exceeds the {MAX_FILE_BYTES} byte cap")
    if MANIFEST.exists():
        manifest = _load(MANIFEST)
        files = {row.get("path"): row for row in manifest.get("files") or []}
        info = files.get("provenance.json")
        if info is None:
            errors.append("manifest missing provenance.json")
        else:
            digest = "sha256:" + hashlib.sha256(DOCUMENT.read_bytes()).hexdigest()
            if info.get("checksum") != digest:
                errors.append("manifest checksum does not match provenance.json")
        marts = {mart.get("id") for mart in manifest.get("marts") or []}
        if "provenance" not in marts:
            errors.append("manifest missing provenance mart")
        if "provenance" not in (manifest.get("coverage") or {}):
            errors.append("manifest coverage missing provenance")
        if not (manifest.get("provenance") or {}).get("checksum"):
            errors.append("manifest provenance block has no checksum")
        for source in manifest.get("sources") or []:
            if source.get("id") not in registry:
                errors.append(f"manifest source {source.get('id')!r} is not registered")

    for error in errors:
        print(f"  - {error}")
    for warning in warnings:
        print(f"  ! {warning}")
    if errors:
        print(f"Provenance check failed ({len(errors)} error(s))")
        return 1
    print(
        "Provenance check passed "
        f"({len(layer_ids)} layers, {len(document.get('sources') or [])} sources, "
        f"migration {document['migration']['gate_status']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
