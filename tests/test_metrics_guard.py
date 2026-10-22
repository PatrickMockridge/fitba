from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from fitba.metrics.audit import (
    _matches,
    _segments,
    load_corpus,
    numeric_leaf_pointers,
    pointer_matches,
)
from fitba.metrics.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data" / "generated"
SPEC = importlib.util.spec_from_file_location(
    "check_metrics", ROOT / "scripts" / "check_metrics.py"
)
assert SPEC and SPEC.loader
check_metrics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_metrics)


@pytest.fixture(scope="module")
def corpus() -> dict:
    return load_corpus(DATA)


def test_every_numeric_leaf_is_registered(corpus) -> None:
    registry = load_registry()
    covered = set()
    for metric in registry.metrics:
        for pattern in metric.payload_paths:
            payload_pattern, _, pointer = pattern.partition("#")
            for key in _matches(corpus, payload_pattern):
                for concrete, _ in numeric_leaf_pointers(corpus[key], _segments(pointer or "/**")):
                    covered.add((key, concrete))

    uncovered = []
    for key in corpus:
        if key == "manifest.json" or key.startswith(("audit/", "metrics/")):
            continue
        for pointer, value in numeric_leaf_pointers(corpus[key], []):
            if (key, pointer) in covered:
                continue
            if any(
                pointer_matches(pattern, pointer) for pattern in registry.structural_number_patterns
            ):
                continue
            uncovered.append(f"{key}#{pointer}={value}")
    assert uncovered == []


def test_pointer_matching() -> None:
    assert pointer_matches("**/player_id", "/players/0/player_id")
    assert pointer_matches("**/*_at", "/generated_at")
    assert pointer_matches("/themes/*/metrics/**", "/themes/0/metrics/scope")
    assert not pointer_matches("/themes/*/metrics/**", "/themes/0/players/0/minutes")
    assert pointer_matches("**/team_id", "/teams/aberdeen/api_team_id") is False


def test_marts_reconcile() -> None:
    report = check_metrics.Report()
    check_metrics._check_manifest_marts(DATA, report)
    assert report.errors == []


def test_published_guard_passes() -> None:
    report = check_metrics.Report()
    registry = load_registry()
    check_metrics._check_registry(registry, report)
    check_metrics._check_parameters(registry, report)
    check_metrics._check_published_registry(registry, DATA, report)
    check_metrics._check_audit(DATA, registry, report)
    check_metrics._check_validation(DATA, report)
    assert report.errors == []


def test_tampered_payload_is_caught(tmp_path) -> None:
    copy = tmp_path / "generated"
    shutil.copytree(DATA, copy)
    path = copy / "squad" / "aberdeen.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["summary"]["total_players"] = payload["summary"]["total_players"] + 1
    path.write_text(json.dumps(payload), encoding="utf-8")

    report = check_metrics.Report()
    registry = load_registry()
    check_metrics._check_audit(copy, registry, report)
    assert any("reproducible" in error for error in report.errors)


def test_generated_at_is_consistent() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    mismatches = []
    for path in sorted(DATA.rglob("*.json")):
        relative = str(path.relative_to(DATA))
        if relative == "manifest.json" or relative.startswith(("audit/", "metrics/")):
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (
            isinstance(payload, dict)
            and "generated_at" in payload
            and payload["generated_at"] != manifest["generated_at"]
        ):
            mismatches.append((relative, payload["generated_at"]))
    assert mismatches == []
