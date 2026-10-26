from __future__ import annotations

from collections import Counter

import pytest
import yaml

from fitba.metrics.registry import load_registry, registry_checksum
from fitba.publish.semantic import build_definitions

ROOT_DEFINITIONS = "reference/definitions.yaml"


def _config() -> dict:
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / ROOT_DEFINITIONS
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _document() -> dict:
    registry = load_registry()
    return build_definitions(
        registry=registry,
        registry_checksum=registry_checksum(registry),
        definitions_config=_config(),
    )


def test_every_definition_id_is_unique() -> None:
    document = _document()
    ids = [row["id"] for row in document["entries"]]
    duplicates = [item for item, count in Counter(ids).items() if count > 1]
    assert duplicates == []


def test_every_definition_alias_is_unique() -> None:
    document = _document()
    aliases = [
        str(alias).casefold()
        for row in document["entries"]
        for alias in row.get("aliases") or []
    ]
    duplicates = [item for item, count in Counter(aliases).items() if count > 1]
    assert duplicates == []


def test_curated_terms_never_override_a_registry_field() -> None:
    config = _config()
    for term in config.get("terms") or []:
        assert not term.get("formula")
        assert not term.get("unit")
        assert not term.get("basis")
        assert not term.get("coverage_tier")
        assert not term.get("source_layer")


def test_every_curated_metric_id_resolves() -> None:
    registry = load_registry()
    known = {metric.id for metric in registry.metrics}
    for term in _config().get("terms") or []:
        for metric_id in term.get("metric_ids") or []:
            assert metric_id in known, term.get("id")


def test_registry_entries_copy_the_registry_verbatim() -> None:
    registry = load_registry()
    document = build_definitions(
        registry=registry,
        registry_checksum=registry_checksum(registry),
        definitions_config={"terms": []},
    )
    by_id = {metric.id: metric for metric in registry.metrics}
    for entry in document["entries"]:
        metric = by_id[entry["metric_ids"][0]]
        assert entry["term"] == metric.label
        assert entry["formula"] == metric.formula
        assert entry["unit"] == metric.unit
        assert entry["basis"] == metric.basis
        assert entry["coverage_tier"] == metric.coverage_tier
        assert entry["source_layer"] == metric.source_layer


def test_a_curated_term_with_unknown_metric_fails_loudly() -> None:
    registry = load_registry()
    with pytest.raises(ValueError):
        build_definitions(
            registry=registry,
            registry_checksum=registry_checksum(registry),
            definitions_config={
                "terms": [{"id": "x", "term": "X", "metric_ids": ["not.a.metric"]}]
            },
        )
