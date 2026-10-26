#!/usr/bin/env python3
"""Validate the public unknowns register.

Every class names a reason and exactly one source mode. A count must resolve to
a numeric leaf in a payload registered to the cited metric. The register itself
must not introduce a number.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data" / "generated"
CONFIG = ROOT / "reference" / "unknowns.yaml"
PAGES = ROOT / "config" / "pages.yaml"
REGISTRY = DATA / "metrics" / "registry.json"
DOCUMENT = DATA / "unknowns.json"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_pointer(document: Any, pointer: str) -> Any:
    value = document
    for raw in pointer.lstrip("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            value = value[int(token)]
        elif isinstance(value, dict):
            value = value[token]
        else:
            raise KeyError(pointer)
    return value


def _numeric_leaves(node: Any, path: str = "") -> list[str]:
    output: list[str] = []
    if isinstance(node, bool):
        return output
    if isinstance(node, (int, float)):
        output.append(path or "/")
    elif isinstance(node, dict):
        for key, value in node.items():
            output.extend(_numeric_leaves(value, f"{path}/{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            output.extend(_numeric_leaves(value, f"{path}/{index}"))
    return output


def check() -> list[str]:
    errors: list[str] = []
    if not DOCUMENT.exists():
        return [f"missing {DOCUMENT.relative_to(ROOT)}"]
    document = _load(DOCUMENT)
    classes = document.get("classes") or []
    if not classes:
        errors.append("the register has no classes")
    pages_config = yaml.safe_load(PAGES.read_text(encoding="utf-8")) or {}
    pages = {str(row.get("id")) for row in pages_config.get("pages") or []}
    metrics = {str(row.get("id")): row for row in (_load(REGISTRY).get("metrics") or [])}
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    config_ids = [str(row.get("id")) for row in config.get("classes") or []]
    rendered_ids = [str(row.get("id")) for row in classes]
    if config_ids != rendered_ids:
        errors.append("published class order or ids do not match reference/unknowns.yaml")
    seen: set[str] = set()
    for row in classes:
        class_id = str(row.get("id") or "")
        if not class_id or class_id in seen:
            errors.append(f"duplicate or missing class id {class_id!r}")
        seen.add(class_id)
        for field in ("domain", "label", "description", "reason"):
            if not str(row.get(field) or "").strip():
                errors.append(f"{class_id}: missing {field}")
        resolver = row.get("resolving_source")
        no_source = bool(row.get("no_public_source"))
        if bool(resolver) == no_source:
            errors.append(f"{class_id}: set exactly one source mode")
        if no_source and resolver:
            errors.append(f"{class_id}: no_public_source carries a resolver")
        if resolver:
            if not str(resolver.get("label") or "").strip():
                errors.append(f"{class_id}: resolver has no label")
            if not str(resolver.get("url") or "").startswith(("/", "https://")):
                errors.append(f"{class_id}: resolver url is not public/internal")
        surfaces = row.get("surfaces") or []
        if not surfaces:
            errors.append(f"{class_id}: no affected surfaces")
        for surface in surfaces:
            if str(surface.get("id")) not in pages:
                errors.append(f"{class_id}: unknown page id {surface.get('id')}")
            if not str(surface.get("path") or "").startswith("/"):
                errors.append(f"{class_id}: surface path is not internal")
        count = row.get("count")
        if count:
            metric_id = str(count.get("metric_id") or "")
            metric = metrics.get(metric_id)
            if metric is None:
                errors.append(f"{class_id}: unknown metric {metric_id}")
            payload = str(count.get("payload") or "")
            if not (DATA / payload).exists():
                errors.append(f"{class_id}: count payload {payload} is missing")
                continue
            if metric is not None:
                paths = [
                    str(metric.get("home_payload") or ""),
                    *[str(item) for item in metric.get("payload_paths") or []],
                ]
                if not any(
                    path == payload or path.startswith(f"{payload}#")
                    for path in paths
                ):
                    errors.append(
                        f"{class_id}: {payload} is not registered to {metric_id}"
                    )
            try:
                value = _resolve_pointer(_load(DATA / payload), str(count.get("pointer") or ""))
            except (KeyError, IndexError, ValueError, TypeError) as error:
                errors.append(f"{class_id}: count pointer does not resolve ({error})")
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors.append(f"{class_id}: count pointer is not numeric")
    # The register carries references only; it must not copy a value.
    numeric = set(_numeric_leaves(document))
    if numeric:
        errors.append(f"numeric leaves in the register: {sorted(numeric)}")
    if not str(document.get("reviewed") or "").startswith("20"):
        errors.append("reviewed date is missing or invalid")
    if document.get("schema_version") != "1.0.0":
        errors.append("schema_version must be 1.0.0")
    return errors


def main() -> int:
    errors = check()
    for error in errors:
        print(f"error: {error}")
    print(
        f"{'PASS' if not errors else 'FAIL'} unknowns check: "
        f"{len(errors)} error(s)"
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
