"""Load, checksum and render the canonical metric registry."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import orjson
import yaml

from fitba.metrics.models import MetricRegistry

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = ROOT / "config" / "metrics.yaml"
SCHEMA_PATH = ROOT / "contracts" / "metrics.schema.json"


def load_registry(path: Path | None = None) -> MetricRegistry:
    source = path or REGISTRY_PATH
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{source}: metric registry must be a mapping")
    return MetricRegistry.model_validate(payload)


def registry_checksum(registry: MetricRegistry) -> str:
    payload = registry.model_dump(mode="json")
    encoded = orjson.dumps(payload, option=orjson.OPT_SORT_KEYS)
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def registry_schema() -> dict[str, Any]:
    return MetricRegistry.model_json_schema()


def published_registry(registry: MetricRegistry) -> dict[str, Any]:
    return {
        "schema_version": registry.schema_version,
        "registry_version": registry.registry_version,
        "reviewed": registry.reviewed.isoformat(),
        "owner": registry.owner,
        "change_policy": registry.change_policy.model_dump(mode="json"),
        "structural_number_patterns": registry.structural_number_patterns,
        "metrics": [metric.model_dump(mode="json") for metric in registry.metrics],
        "parameters": [parameter.model_dump(mode="json") for parameter in registry.parameters],
    }
