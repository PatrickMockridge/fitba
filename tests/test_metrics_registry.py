from __future__ import annotations

import json
from pathlib import Path

import pytest

from fitba.metrics.audit import _parameter_entry
from fitba.metrics.checks import CHECKS
from fitba.metrics.registry import SCHEMA_PATH, load_registry, registry_checksum, registry_schema

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def registry():
    return load_registry()


def test_registry_validates(registry) -> None:
    assert registry.registry_version
    assert registry.schema_version == 1
    assert registry.metrics
    assert len({metric.id for metric in registry.metrics}) == len(registry.metrics)
    assert len({parameter.id for parameter in registry.parameters}) == len(registry.parameters)


def test_schema_on_disk_is_current() -> None:
    assert SCHEMA_PATH.exists(), "contracts/metrics.schema.json is missing"
    assert json.loads(SCHEMA_PATH.read_text(encoding="utf-8")) == registry_schema()


def test_recompute_metrics_have_implementations(registry) -> None:
    for metric in registry.metrics:
        if metric.verification == "recompute":
            assert metric.implementation in CHECKS, metric.id
        if metric.verification == "cross_surface":
            assert metric.implementation or metric.verification_checks, metric.id
        if metric.verification == "source_checksum":
            assert metric.source_paths, metric.id
        if metric.verification == "provenance_only":
            assert metric.limitations, metric.id


def test_parameter_values_match_config(registry) -> None:
    failures = []
    for parameter in registry.parameters:
        entry = _parameter_entry(parameter)
        if entry["status"] != "pass":
            failures.append((parameter.id, entry["errors"], entry["mismatches"][:3]))
    assert failures == []


def test_registry_checksum_is_stable(registry) -> None:
    checksum = registry_checksum(registry)
    assert checksum.startswith("sha256:")
    assert len(checksum) == len("sha256:") + 64
    assert checksum == registry_checksum(load_registry())


def test_metric_ids_are_namespaced(registry) -> None:
    for metric in registry.metrics:
        assert "." in metric.id
        assert metric.id == metric.id.lower()
        assert " " not in metric.id
