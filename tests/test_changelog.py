from __future__ import annotations

import json
from pathlib import Path

import yaml

from fitba.publish.semantic import build_changelog

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "reference" / "changelog.yaml"
METRIC_CHANGES = ROOT / "docs" / "metric-changes.md"


def _config() -> dict:
    return yaml.safe_load(CHANGELOG.read_text(encoding="utf-8"))


def _document() -> dict:
    return build_changelog(changelog_config=_config())


def test_the_projection_is_deterministic() -> None:
    first = json.dumps(_document(), sort_keys=True)
    second = json.dumps(_document(), sort_keys=True)
    assert first == second


def test_the_log_is_append_only_and_newest_first() -> None:
    document = _document()
    assert document["append_only"] is True
    dates = [str(row.get("date") or "") for row in document["entries"]]
    assert dates == sorted(dates, reverse=True)


def test_every_entry_has_an_id_date_kind_and_status() -> None:
    kinds = {"correction", "metric", "source", "page", "data"}
    statuses = {"fixed", "reviewing", "withdrawn", "published"}
    entries = _document()["entries"]
    assert entries
    ids = [row.get("id") for row in entries]
    assert len(ids) == len(set(ids))
    for row in entries:
        assert row.get("id")
        assert str(row.get("date") or "").startswith("20")
        assert row.get("kind") in kinds
        assert row.get("status") in statuses
        assert row.get("pages")
        assert row.get("evidence")


def test_a_metric_entry_names_a_version_with_a_documented_heading() -> None:
    headings = METRIC_CHANGES.read_text(encoding="utf-8")
    for row in _document()["entries"]:
        if row.get("kind") != "metric":
            continue
        version = str(row.get("registry_version") or "")
        assert version, row.get("id")
        assert version in headings, row.get("id")


def test_metric_ids_resolve_to_the_registry() -> None:
    from fitba.metrics.registry import load_registry

    known = {metric.id for metric in load_registry().metrics}
    for row in _document()["entries"]:
        for metric_id in row.get("metric_ids") or []:
            assert metric_id in known, row.get("id")


def test_blocked_evidence_urls_do_not_enter_the_log() -> None:
    for row in _document()["entries"]:
        for evidence in row.get("evidence") or []:
            assert "github.com" not in str(evidence.get("url") or "")
