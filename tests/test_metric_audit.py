from __future__ import annotations

import json
from pathlib import Path

import pytest

from fitba.metrics.audit import build_audit, build_registry_payload, load_corpus
from fitba.metrics.registry import load_registry, registry_checksum

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data" / "generated"


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def audit(manifest) -> dict:
    return json.loads((DATA / "audit" / "metrics.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def registry():
    return load_registry()


def test_audit_passes(audit) -> None:
    assert audit["status"] == "pass"
    assert audit["summary"]["metrics_failed"] == 0
    assert audit["summary"]["parameters_failed"] == 0


def test_audit_covers_every_metric_and_parameter(audit, registry) -> None:
    assert {entry["id"] for entry in audit["metrics"]} == {metric.id for metric in registry.metrics}
    assert {entry["id"] for entry in audit["parameters"]} == {
        parameter.id for parameter in registry.parameters
    }


def test_audit_matches_manifest(manifest, audit) -> None:
    block = manifest["metrics"]
    assert block["status"] == audit["status"]
    assert block["registry_version"] == audit["registry_version"]
    assert block["metrics_total"] == audit["summary"]["metrics_total"]
    assert block["parameters_total"] == audit["summary"]["parameters_total"]
    assert block["provenance_only"] == audit["summary"]["provenance_only"]


EPOCH_FIELDS = {
    "dataset_id",
    "update_id",
    "published_at",
    "served_by_update_id",
    "dataset_state",
    "stale_reason",
    "source_snapshots",
}


def _without_epoch(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if key not in EPOCH_FIELDS}


def test_audit_is_reproducible(manifest, audit, registry) -> None:
    reproduced = build_audit(
        corpus=load_corpus(DATA),
        registry=registry,
        dataset_version=manifest["dataset_version"],
        generated_at=manifest["generated_at"],
        season=manifest["season"],
        audited_at=audit["audited_at"],
        allowlist=audit["allowlist"],
    )
    assert reproduced == _without_epoch(audit)


def test_registry_artifact_matches_config(registry) -> None:
    published = json.loads((DATA / "metrics" / "registry.json").read_text(encoding="utf-8"))
    comparable = _without_epoch(published)
    comparable.pop("generated_at", None)
    assert comparable == build_registry_payload(registry)
    assert published["checksum"] == registry_checksum(registry)


def test_provenance_only_is_labelled(audit) -> None:
    for entry in audit["metrics"]:
        if entry["verification"] == "provenance_only":
            assert entry["provenance_only"] is True
            assert entry["limitations"]
        else:
            assert entry["provenance_only"] is False


def test_every_metric_has_a_location(audit) -> None:
    for entry in audit["metrics"]:
        assert entry["locations"], entry["id"]
