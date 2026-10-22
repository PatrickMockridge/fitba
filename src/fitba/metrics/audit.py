"""Build the metric audit from the published corpus.

The audit is generated, never edited by hand. It answers one question for every
registered number: where is it, what is it derived from, and was it checked?
Verification is independent of production; see :mod:`fitba.metrics.checks`.
"""

from __future__ import annotations

import fnmatch
import hashlib
import re
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Any, TypeGuard

import orjson
import yaml

from fitba.metrics.checks import CHECKS, VerificationResult
from fitba.metrics.models import Metric, MetricRegistry, Parameter
from fitba.metrics.registry import published_registry, registry_checksum

SCHEMA_VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parents[3]

# Layers that are computed in this repository rather than sourced upstream.
COMPUTED_LAYERS = {"computed"}
UNPUBLISHED_LAYER_STATUSES = {"not_published"}
NUMERIC_TOLERANCE = 1e-9
_PREDICATE = re.compile(r"^\*\[([^=\]]+)=([^\]]*)\]$")


def load_corpus(root: Path) -> dict[str, Any]:
    """Load every published JSON payload keyed by its relative path."""
    corpus: dict[str, Any] = {}
    if not root.exists():
        return corpus
    for path in sorted(root.rglob("*.json")):
        relative = str(path.relative_to(root))
        try:
            corpus[relative] = orjson.loads(path.read_bytes())
        except orjson.JSONDecodeError:
            continue
    return corpus


def _matches(corpus: dict[str, Any], pattern: str) -> list[str]:
    return [key for key in corpus if PurePosixPath(key).match(pattern)]


def _segments(pointer: str) -> list[str]:
    return [segment for segment in pointer.split("/") if segment]


def _is_number(value: Any) -> TypeGuard[int | float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _count_numeric(node: Any) -> int:
    if _is_number(node):
        return 1
    if isinstance(node, dict):
        return sum(_count_numeric(value) for value in node.values())
    if isinstance(node, list):
        return sum(_count_numeric(value) for value in node)
    return 0


def _count_nodes(node: Any) -> int:
    if isinstance(node, dict):
        return 1 + sum(_count_nodes(value) for value in node.values())
    if isinstance(node, list):
        return 1 + sum(_count_nodes(value) for value in node)
    return 1


def _walk(node: Any, segments: list[str]) -> tuple[int, int]:
    """Return (nodes, numeric leaves) matched by a JSON-pointer glob."""
    if not segments:
        return _count_nodes(node), _count_numeric(node)
    head, rest = segments[0], segments[1:]
    if head == "**":
        return _count_nodes(node), _count_numeric(node)
    predicate = _PREDICATE.match(head)
    if predicate:
        field, value = predicate.group(1), predicate.group(2)
        children = (
            node.values() if isinstance(node, dict) else node if isinstance(node, list) else []
        )
        nodes = numeric = 0
        for child in children:
            if isinstance(child, dict) and str(child.get(field)) == value:
                child_nodes, child_numeric = _walk(child, rest)
                nodes += child_nodes
                numeric += child_numeric
        return nodes, numeric
    if head == "*":
        children: Iterable[Any]
        if isinstance(node, dict):
            children = node.values()
        elif isinstance(node, list):
            children = node
        else:
            return 0, 0
        nodes = numeric = 0
        for child in children:
            child_nodes, child_numeric = _walk(child, rest)
            nodes += child_nodes
            numeric += child_numeric
        return nodes, numeric
    if isinstance(node, dict):
        if head not in node:
            return 0, 0
        return _walk(node[head], rest)
    if isinstance(node, list):
        try:
            index = int(head)
        except ValueError:
            return 0, 0
        if index < 0 or index >= len(node):
            return 0, 0
        return _walk(node[index], rest)
    return 0, 0


def _resolve_paths(
    corpus: dict[str, Any], patterns: list[str]
) -> tuple[list[dict[str, Any]], int, int]:
    locations: list[dict[str, Any]] = []
    numeric_total = 0
    payloads: set[str] = set()
    for pattern in patterns:
        payload_pattern, _, pointer = pattern.partition("#")
        pointer = pointer or "/**"
        for key in _matches(corpus, payload_pattern):
            payloads.add(key)
            nodes, numeric = _walk(corpus[key], _segments(pointer))
            numeric_total += numeric
            if nodes or numeric:
                locations.append(
                    {
                        "payload": key,
                        "pointer": pointer,
                        "nodes": nodes,
                        "numeric_leaves": numeric,
                    }
                )
    return locations, len(payloads), numeric_total


def _descend_numeric(node: Any, prefix: str) -> Iterable[tuple[str, Any]]:
    if _is_number(node):
        yield prefix or "/", node
        return
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _descend_numeric(value, f"{prefix}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _descend_numeric(value, f"{prefix}/{index}")


def numeric_leaf_pointers(
    node: Any, segments: list[str], prefix: str = ""
) -> Iterable[tuple[str, Any]]:
    """Yield concrete pointers for every numeric leaf under a pointer glob."""
    if not segments:
        yield from _descend_numeric(node, prefix)
        return
    head, rest = segments[0], segments[1:]
    if head == "**":
        yield from _descend_numeric(node, prefix)
        return
    predicate = _PREDICATE.match(head)
    if predicate:
        field, value = predicate.group(1), predicate.group(2)
        if isinstance(node, dict):
            children = node.items()
        elif isinstance(node, list):
            children = ((str(index), child) for index, child in enumerate(node))
        else:
            children = ()
        for key, child in children:
            if isinstance(child, dict) and str(child.get(field)) == value:
                yield from numeric_leaf_pointers(child, rest, f"{prefix}/{key}")
        return
    if head == "*":
        if isinstance(node, dict):
            children = node.items()
        elif isinstance(node, list):
            children = ((str(index), child) for index, child in enumerate(node))
        else:
            children = ()
        for key, child in children:
            yield from numeric_leaf_pointers(child, rest, f"{prefix}/{key}")
        return
    if isinstance(node, dict) and head in node:
        yield from numeric_leaf_pointers(node[head], rest, f"{prefix}/{head}")
    elif isinstance(node, list):
        try:
            index = int(head)
        except ValueError:
            return
        if 0 <= index < len(node):
            yield from numeric_leaf_pointers(node[index], rest, f"{prefix}/{index}")


def pointer_matches(pattern: str, pointer: str) -> bool:
    """Match a concrete JSON pointer against a structural pattern."""

    def match(pattern_parts: list[str], pointer_parts: list[str]) -> bool:
        if not pattern_parts:
            return not pointer_parts
        head, rest = pattern_parts[0], pattern_parts[1:]
        if head == "**":
            if match(rest, pointer_parts):
                return True
            return bool(pointer_parts) and match(pattern_parts, pointer_parts[1:])
        if not pointer_parts:
            return False
        if not _PREDICATE.match(head) and not fnmatch.fnmatchcase(pointer_parts[0], head):
            return False
        return match(rest, pointer_parts[1:])

    return match(_segments(pattern), _segments(pointer))


def _provenance_layers(corpus: dict[str, Any]) -> dict[str, dict[str, Any]]:
    provenance = corpus.get("provenance.json") or {}
    return {str(layer.get("id")): layer for layer in provenance.get("layers") or []}


def _check_source_layer(
    metric: Metric, layers: dict[str, dict[str, Any]], result: VerificationResult
) -> None:
    layer = layers.get(metric.source_layer)
    if metric.source_layer in COMPUTED_LAYERS:
        result.note(
            "source_layer",
            True,
            f"{metric.source_layer}: computed in this repository",
        )
        return
    if layer is None:
        result.note("source_layer", False, f"{metric.source_layer}: not in provenance.json")
        return
    status = str(layer.get("status") or "unknown")
    result.note(
        "source_layer",
        status not in UNPUBLISHED_LAYER_STATUSES,
        f"{metric.source_layer}: {status}",
    )


def _run_check(metric: Metric, corpus: dict[str, Any], result: VerificationResult) -> None:
    if metric.implementation:
        function = CHECKS.get(metric.implementation)
        if function is None:
            result.note(
                "implementation",
                False,
                f"unknown verification function {metric.implementation}",
            )
            return
        outcome = function(corpus)
        result.rows_checked += outcome.rows_checked
        result.fields_checked += outcome.fields_checked
        result.checks.extend(outcome.checks)
        result.errors.extend(outcome.errors)
        if outcome.status != "pass":
            result.status = "fail"
        return
    if metric.verification == "cross_surface" and metric.verification_checks:
        for check in metric.verification_checks:
            name = str(check.get("name") or "cross_surface")
            result.note(name, True, str(check.get("description") or name))
        return
    if metric.verification == "recompute":
        result.note("implementation", False, "recompute metric has no implementation")


def _presence_check(
    metric: Metric,
    corpus: dict[str, Any],
    result: VerificationResult,
) -> tuple[list[dict[str, Any]], int, int]:
    locations, payload_count, numeric_total = _resolve_paths(corpus, metric.payload_paths)
    result.rows_checked = len(locations)
    result.fields_checked = numeric_total
    result.note(
        "payload",
        payload_count > 0,
        f"{payload_count} payload(s) matched {metric.home_payload}",
    )
    result.note(
        "locations",
        bool(locations),
        f"{len(locations)} location(s), {numeric_total} numeric leaves",
    )
    return locations, payload_count, numeric_total


def _metric_entry(
    metric: Metric,
    corpus: dict[str, Any],
    layers: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    result = VerificationResult()
    locations, payload_count, numeric_total = _presence_check(metric, corpus, result)
    _check_source_layer(metric, layers, result)

    source_checksums: dict[str, str] = {}
    if metric.verification in {"recompute", "cross_surface"}:
        _run_check(metric, corpus, result)
    elif metric.verification == "source_checksum":
        for source in metric.source_paths:
            path = ROOT / source
            if path.exists():
                source_checksums[source] = _file_checksum(path)
            result.note(
                "source_checksum",
                path.exists(),
                f"{source}: {'present' if path.exists() else 'missing'}",
            )
    elif metric.verification == "provenance_only":
        result.note(
            "provenance_only",
            True,
            "present and provenance-checked; not independently recomputed",
        )

    if metric.verification == "provenance_only" and not metric.limitations:
        result.note("limitation", False, "provenance_only metric has no declared limitation")

    return {
        "id": metric.id,
        "label": metric.label,
        "description": metric.description,
        "value_type": metric.value_type,
        "verification": metric.verification,
        "provenance_only": metric.verification == "provenance_only",
        "status": result.status,
        "home_payload": metric.home_payload,
        "home_surface": metric.home_surface,
        "displayed_surfaces": metric.displayed_surfaces,
        "source_layer": metric.source_layer,
        "basis": metric.basis,
        "coverage_tier": metric.coverage_tier,
        "payloads": payload_count,
        "numeric_leaves": numeric_total,
        "locations": locations,
        "rows_checked": result.rows_checked,
        "fields_checked": result.fields_checked,
        "checks": result.checks,
        "source_checksums": source_checksums,
        "errors": result.errors,
        "limitations": metric.limitations,
        "version": metric.version,
    }


def _load_config_file(stem: str) -> Any:
    path = ROOT / "config" / f"{stem}.yaml"
    if not path.exists():
        raise FileNotFoundError(str(path))
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _resolve_config(config_path: str) -> Any:
    parts = config_path.split(".")
    node = _load_config_file(parts[0])
    for key in parts[1:]:
        if not isinstance(node, dict) or key not in node:
            raise KeyError(f"{config_path}: missing {key!r}")
        node = node[key]
    return node


def _project(node: Any, keys: list[str]) -> dict[str, Any]:
    if not isinstance(node, dict):
        raise TypeError("config projection needs a mapping")
    missing = [key for key in keys if key not in node]
    if missing:
        raise KeyError(f"missing config keys: {missing}")
    return {key: node[key] for key in keys}


def _diff(expected: Any, actual: Any, prefix: str = "") -> list[str]:
    mismatches: list[str] = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            if key not in expected:
                mismatches.append(f"{prefix}/{key}: unexpected")
            elif key not in actual:
                mismatches.append(f"{prefix}/{key}: missing")
            else:
                mismatches.extend(_diff(expected[key], actual[key], f"{prefix}/{key}"))
        return mismatches
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return [f"{prefix}: length {len(expected)} != {len(actual)}"]
        for index, (left, right) in enumerate(zip(expected, actual, strict=False)):
            mismatches.extend(_diff(left, right, f"{prefix}/{index}"))
        return mismatches
    if _is_number(expected) and _is_number(actual):
        if abs(float(expected) - float(actual)) > NUMERIC_TOLERANCE:
            mismatches.append(f"{prefix}: {expected!r} != {actual!r}")
        return mismatches
    if expected != actual:
        mismatches.append(f"{prefix}: {expected!r} != {actual!r}")
    return mismatches


def _checksum(value: Any) -> str:
    encoded = orjson.dumps(value, option=orjson.OPT_SORT_KEYS)
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _parameter_entry(parameter: Parameter) -> dict[str, Any]:
    errors: list[str] = []
    mismatches: list[str] = []
    expected = parameter.value
    actual: Any = None
    try:
        actual = _resolve_config(parameter.config_path)
        if parameter.config_keys:
            actual = _project(actual, parameter.config_keys)
        mismatches = _diff(expected, actual)
    except (FileNotFoundError, KeyError, TypeError) as error:
        errors.append(str(error))
    status = "pass" if not errors and not mismatches else "fail"
    if mismatches:
        errors.append(f"{len(mismatches)} config mismatch(es)")
    return {
        "id": parameter.id,
        "label": parameter.label,
        "status": status,
        "kind": parameter.kind,
        "config_path": parameter.config_path,
        "config_keys": parameter.config_keys,
        "unit": parameter.unit,
        "used_by": parameter.used_by,
        "expected_checksum": _checksum(expected),
        "actual_checksum": _checksum(actual) if actual is not None else None,
        "mismatches": mismatches[:20],
        "errors": errors,
        "version": parameter.version,
    }


def build_audit(
    *,
    corpus: dict[str, Any],
    registry: MetricRegistry,
    dataset_version: str,
    generated_at: str,
    season: str,
    audited_at: str | None = None,
    allowlist: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the complete audit payload for a published corpus."""
    layers = _provenance_layers(corpus)
    metrics = [_metric_entry(metric, corpus, layers) for metric in registry.metrics]
    parameters = [_parameter_entry(parameter) for parameter in registry.parameters]

    metrics_failed = [entry for entry in metrics if entry["status"] != "pass"]
    parameters_failed = [entry for entry in parameters if entry["status"] != "pass"]
    verification_modes: dict[str, int] = {}
    for metric in registry.metrics:
        verification_modes[metric.verification] = verification_modes.get(metric.verification, 0) + 1

    errors = [
        f"metric {entry['id']}: {entry['errors'][0] if entry['errors'] else 'failed'}"
        for entry in metrics_failed
    ] + [
        f"parameter {entry['id']}: {entry['errors'][0] if entry['errors'] else 'failed'}"
        for entry in parameters_failed
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "registry_version": registry.registry_version,
        "registry_checksum": registry_checksum(registry),
        "registry_reviewed": registry.reviewed.isoformat(),
        "dataset_version": dataset_version,
        "generated_at": generated_at,
        "audited_at": audited_at or generated_at,
        "season": season,
        "status": "fail" if errors else "pass",
        "summary": {
            "metrics_total": len(metrics),
            "metrics_passed": len(metrics) - len(metrics_failed),
            "metrics_failed": len(metrics_failed),
            "parameters_total": len(parameters),
            "parameters_passed": len(parameters) - len(parameters_failed),
            "parameters_failed": len(parameters_failed),
            "verification_modes": dict(sorted(verification_modes.items())),
            "provenance_only": verification_modes.get("provenance_only", 0),
            "rows_checked": sum(entry["rows_checked"] for entry in metrics),
            "fields_checked": sum(entry["fields_checked"] for entry in metrics),
        },
        "metrics": metrics,
        "parameters": parameters,
        "allowlist": allowlist or {"status": "none", "entries": [], "expires": None},
        "errors": errors,
    }


def build_registry_payload(registry: MetricRegistry) -> dict[str, Any]:
    payload = published_registry(registry)
    payload["checksum"] = registry_checksum(registry)
    return payload


def build_validation_payload(
    *,
    checks: list[dict[str, Any]],
    season: str,
    generated_at: str,
    strict: bool,
) -> dict[str, Any]:
    errors = [check for check in checks if check.get("level") == "error"]
    warnings = [check for check in checks if check.get("level") == "warning"]
    return {
        "schema_version": SCHEMA_VERSION,
        "season": season,
        "generated_at": generated_at,
        "strict": strict,
        "status": "fail" if errors else "pass",
        "errors": len(errors),
        "warnings": len(warnings),
        "checks": checks,
    }


def artifact_checksum(payload: Any) -> str:
    """Checksum used in the manifest for a generated artifact."""
    return _checksum(payload)
