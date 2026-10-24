from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fitba.freshness import check_freshness
from fitba.publish.epoch import DatasetStamp, reset_stamp, set_stamp, stamp_payload


def _stamp() -> DatasetStamp:
    return DatasetStamp(
        dataset_id="dataset-1",
        update_id="update-1",
        published_at="2026-10-24T20:00:00+00:00",
        source_snapshots={"football_data_uk": "2026-10-24T19:00:00+00:00"},
    )


def _write_corpus(root: Path, *, payload: dict | None = None) -> None:
    root.mkdir(parents=True, exist_ok=True)
    document = payload or {
        "generated_at": "2026-10-24T20:00:00+00:00",
        "dataset_id": "dataset-1",
        "update_id": "update-1",
        "published_at": "2026-10-24T20:00:00+00:00",
        "served_by_update_id": "update-1",
        "dataset_state": "fresh",
        "source_snapshots": {"football_data_uk": "2026-10-24T19:00:00+00:00"},
    }
    path = root / "sample.json"
    path.write_text(json.dumps(document))
    digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        "generated_at": "2026-10-24T20:00:00+00:00",
        "dataset_version": "dataset-1",
        "update": {"id": "update-1", "results_guard": {"status": "pass"}},
        "freshness": {
            "dataset_id": "dataset-1",
            "update_id": "update-1",
            "stale_sources": [],
            "sources": {
                "football_data_uk": {
                    "state": "fresh",
                    "required": True,
                    "age_hours": 1,
                    "ttl_hours": 6,
                }
            },
        },
        "files": [{"path": "sample.json", "checksum": digest}],
    }
    (root / "manifest.json").write_text(json.dumps(manifest))


def test_fresh_stamped_payload_passes(tmp_path):
    _write_corpus(tmp_path)
    report = check_freshness(tmp_path, strict=True)
    assert report["status"] == "pass", report["errors"]
    assert report["fresh_payloads"] == 1


def test_stamp_keeps_a_stale_payload_on_its_old_dataset():
    token = set_stamp(_stamp())
    try:
        payload = stamp_payload(
            {
                "generated_at": "2026-10-20T10:00:00+00:00",
                "dataset_id": "dataset-0",
                "update_id": "update-0",
                "state": "stale",
                "served_generated_at": "2026-10-20T10:00:00+00:00",
            }
        )
    finally:
        reset_stamp(token)
    assert payload["dataset_id"] == "dataset-0"
    assert payload["update_id"] == "update-0"
    assert payload["dataset_state"] == "stale"
    assert payload["stale_reason"] == "served_from_previous_publish"
    assert payload["served_by_update_id"] == "update-1"
    assert payload["generated_at"] == "2026-10-20T10:00:00+00:00"


def test_stamp_is_idempotent():
    token = set_stamp(_stamp())
    try:
        first = stamp_payload({"generated_at": "2026-10-24T20:00:00+00:00"})
        second = stamp_payload(first)
    finally:
        reset_stamp(token)
    assert first == second


def test_missing_epoch_fails(tmp_path):
    _write_corpus(tmp_path, payload={"generated_at": "2026-10-24T20:00:00+00:00"})
    report = check_freshness(tmp_path, strict=True)
    assert report["status"] == "fail"
    assert any("dataset_id" in error for error in report["errors"])


def test_checksum_mismatch_fails(tmp_path):
    _write_corpus(tmp_path)
    (tmp_path / "sample.json").write_text("{}")
    report = check_freshness(tmp_path, strict=True)
    assert report["status"] == "fail"
    assert any("checksum" in error for error in report["errors"])


def test_unlisted_file_fails(tmp_path):
    _write_corpus(tmp_path)
    (tmp_path / "extra.json").write_text("{}")
    report = check_freshness(tmp_path, strict=True)
    assert report["status"] == "fail"
    assert any("not listed" in error for error in report["errors"])


def test_stale_payload_requires_a_reason(tmp_path):
    _write_corpus(
        tmp_path,
        payload={
            "generated_at": "2026-10-20T20:00:00+00:00",
            "dataset_id": "dataset-0",
            "update_id": "update-0",
            "dataset_state": "stale",
            "served_by_update_id": "update-1",
        },
    )
    report = check_freshness(tmp_path, strict=True)
    assert report["status"] == "fail"
    assert any("stale payload has no reason" in error for error in report["errors"])


def test_required_source_must_be_fresh(tmp_path):
    _write_corpus(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    manifest["freshness"]["sources"]["football_data_uk"]["state"] = "stale"
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    report = check_freshness(tmp_path, strict=True)
    assert report["status"] == "fail"
    assert any("required source" in error for error in report["errors"])
