"""Build the public unknowns register.

The register records what the public record does not know, why, and which public
source would resolve it. It never invents a value or a resolver, and every count
must already exist in a registered metric's published payload.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fitba.metrics.registry import MetricRegistry


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _unescape(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _resolve_pointer(document: Any, pointer: str) -> Any:
    if pointer in ("", "/"):
        return document
    value = document
    for raw in pointer.lstrip("/").split("/"):
        token = _unescape(raw)
        if isinstance(value, list):
            try:
                value = value[int(token)]
            except (ValueError, IndexError) as error:
                raise ValueError(f"pointer {pointer!r}: no item {token!r}") from error
        elif isinstance(value, dict):
            if token not in value:
                raise ValueError(f"pointer {pointer!r}: no key {token!r}")
            value = value[token]
        else:
            raise ValueError(f"pointer {pointer!r}: cannot descend into {type(value).__name__}")
    return value


def _metric_paths(metric: Any) -> list[str]:
    return [str(metric.home_payload or ""), *[str(path) for path in metric.payload_paths or []]]


def _payload_is_registered(payload: str, metric: Any) -> bool:
    for path in _metric_paths(metric):
        if path == payload or path.startswith(f"{payload}#") or payload.startswith(f"{path}#"):
            return True
    return False


def _surfaces(
    ids: list[str], pages_config: dict[str, Any]
) -> list[dict[str, str]]:
    pages = {str(row.get("id")): row for row in pages_config.get("pages") or []}
    output: list[dict[str, str]] = []
    for page_id in ids:
        page = pages.get(page_id)
        if page is None:
            raise ValueError(f"unknown affected surface: {page_id}")
        patterns = [str(item) for item in page.get("patterns") or []]
        output.append(
            {
                "id": page_id,
                "label": str(page.get("label") or page_id),
                "path": patterns[0] if patterns else "/",
            }
        )
    return output


def build_unknowns(
    *,
    classes_config: dict[str, Any],
    data_dir: Path,
    registry: MetricRegistry,
    pages_config: dict[str, Any],
) -> dict[str, Any]:
    metrics = {metric.id: metric for metric in registry.metrics}
    classes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in classes_config.get("classes") or []:
        class_id = str(row.get("id") or "")
        if not class_id or class_id in seen:
            raise ValueError(f"unknowns: duplicate or missing class id {class_id!r}")
        seen.add(class_id)
        resolver = row.get("resolving_source") or None
        no_source = bool(row.get("no_public_source"))
        if bool(resolver) == no_source:
            raise ValueError(
                f"unknowns {class_id}: set exactly one of resolving_source or no_public_source"
            )
        output: dict[str, Any] = {
            "id": class_id,
            "domain": str(row.get("domain") or "other"),
            "label": str(row.get("label") or class_id),
            "description": str(row.get("description") or "").strip(),
            "reason": str(row.get("reason") or "").strip(),
            "surfaces": _surfaces(
                [str(item) for item in row.get("affected_surfaces") or []],
                pages_config,
            ),
            "resolving_source": (
                {
                    "label": str(resolver.get("label") or ""),
                    "url": str(resolver.get("url") or ""),
                    "note": str(resolver.get("note") or "").strip(),
                }
                if resolver
                else None
            ),
            "no_public_source": no_source,
        }
        count = row.get("count")
        if count:
            payload = str(count.get("payload") or "")
            pointer = str(count.get("pointer") or "")
            metric_id = str(count.get("metric_id") or "")
            metric = metrics.get(metric_id)
            if metric is None:
                raise ValueError(f"unknowns {class_id}: unknown metric {metric_id}")
            if not _payload_is_registered(payload, metric):
                raise ValueError(
                    f"unknowns {class_id}: {payload} is not a registered payload for {metric_id}"
                )
            document = _load_json(data_dir / payload)
            if document is None:
                raise ValueError(f"unknowns {class_id}: missing payload {payload}")
            value = _resolve_pointer(document, pointer)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"unknowns {class_id}: count is not numeric")
            # The register stores the reference, not the value. The value stays
            # in its registered payload and is resolved at render time.
            output["count"] = {
                "metric_id": metric_id,
                "payload": payload,
                "pointer": pointer,
            }
        classes.append(output)
    return {
        "schema_version": "1.0.0",
        "state": "available",
        "reviewed": str(classes_config.get("reviewed") or ""),
        "owner": str(classes_config.get("owner") or ""),
        "owner_note": str(classes_config.get("note") or "").strip(),
        "classes": classes,
    }
