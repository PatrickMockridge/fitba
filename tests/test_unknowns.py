from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from fitba.metrics.registry import MetricRegistry
from fitba.publish.unknowns import build_unknowns

PAGES = {
    "pages": [
        {"id": "matchday", "label": "Matchday", "patterns": ["/matchday/"]},
        {"id": "squad", "label": "Squad", "patterns": ["/squad/"]},
    ]
}


def _registry() -> MetricRegistry:
    metric = SimpleNamespace(
        id="coverage.surfaces",
        home_payload="coverage.json",
        payload_paths=["coverage.json#/**"],
    )
    return cast(
        MetricRegistry,
        SimpleNamespace(metrics=[metric]),
    )


def _data(tmp_path: Path) -> Path:
    path = tmp_path / "coverage.json"
    path.write_text(json.dumps({"availability": {"unknown": 3}}), encoding="utf-8")
    return tmp_path


def _class(**overrides) -> dict:
    row = {
        "id": "availability.unverified",
        "domain": "availability",
        "label": "No verified team news",
        "description": "Availability stays unknown.",
        "reason": "No official entry.",
        "affected_surfaces": ["matchday", "squad"],
        "resolving_source": {
            "label": "Official team news",
            "url": "https://example.invalid/news",
            "note": "Only the club resolves it.",
        },
    }
    row.update(overrides)
    return row


def _build(tmp_path: Path, rows: list[dict]):
    return build_unknowns(
        classes_config={"reviewed": "2026-10-26", "owner": "owner", "classes": rows},
        data_dir=_data(tmp_path),
        registry=_registry(),
        pages_config=PAGES,
    )


def test_a_class_resolves_its_surfaces_and_count(tmp_path: Path) -> None:
    document = _build(
        tmp_path,
        [
            _class(
                count={
                    "payload": "coverage.json",
                    "pointer": "/availability/unknown",
                    "metric_id": "coverage.surfaces",
                }
            )
        ],
    )
    row = document["classes"][0]
    assert [surface["id"] for surface in row["surfaces"]] == ["matchday", "squad"]
    assert row["count"] == {
        "metric_id": "coverage.surfaces",
        "payload": "coverage.json",
        "pointer": "/availability/unknown",
    }
    assert "value" not in row["count"]
    assert row["no_public_source"] is False


def test_exactly_one_source_mode_is_required(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="exactly one"):
        _build(
            tmp_path,
            [
                _class(
                    resolving_source=None,
                )
            ],
        )
    with pytest.raises(ValueError, match="exactly one"):
        _build(
            tmp_path,
            [_class(no_public_source=True)],
        )


def test_an_unknown_surface_or_metric_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown affected surface"):
        _build(tmp_path, [_class(affected_surfaces=["nope"])])
    with pytest.raises(ValueError, match="unknown metric"):
        _build(
            tmp_path,
            [
                _class(
                    count={
                        "payload": "coverage.json",
                        "pointer": "/availability/unknown",
                        "metric_id": "not.a.metric",
                    }
                )
            ],
        )


def test_an_unregistered_payload_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "other.json").write_text(json.dumps({"x": 1}), encoding="utf-8")
    with pytest.raises(ValueError, match="not a registered payload"):
        _build(
            tmp_path,
            [
                _class(
                    count={
                        "payload": "other.json",
                        "pointer": "/x",
                        "metric_id": "coverage.surfaces",
                    }
                )
            ],
        )


def test_a_missing_pointer_or_non_numeric_value_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no key"):
        _build(
            tmp_path,
            [
                _class(
                    count={
                        "payload": "coverage.json",
                        "pointer": "/availability/missing",
                        "metric_id": "coverage.surfaces",
                    }
                )
            ],
        )
    document = _build(
        tmp_path,
        [
            _class(
                count={
                    "payload": "coverage.json",
                    "pointer": "/availability/unknown",
                    "metric_id": "coverage.surfaces",
                }
            )
        ],
    )
    assert document["classes"][0]["count"]["pointer"] == "/availability/unknown"
