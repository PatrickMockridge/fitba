from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from fitba.ingest.runner import load_matches
from fitba.publish.case import (
    CaseDocument,
    build_case_payload,
    case_schema,
    fallback_case_payload,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data" / "generated"


def _inputs():
    season = "2026-27"
    all_matches = load_matches(None)
    return {
        "season": season,
        "generated_at": "2026-10-22T00:00:00+00:00",
        "matches": all_matches.filter(pl.col("season") == season),
        "all_matches": all_matches,
        "squad_data": json.loads((DATA / "squad" / "aberdeen.json").read_text()),
        "transfers_data": json.loads((DATA / "transfers" / "aberdeen.json").read_text()),
        "history_index": json.loads((DATA / "history" / "aberdeen.json").read_text()),
        "history_season": json.loads((DATA / "history" / "seasons" / "2026-27.json").read_text()),
        "history_seasons": {
            path.stem: json.loads(path.read_text())
            for path in (DATA / "history" / "seasons").glob("*.json")
        },
        "availability": json.loads((DATA / "availability" / "aberdeen.json").read_text()),
    }


def test_payload_validates() -> None:
    document = build_case_payload(**_inputs())
    CaseDocument(**document)
    assert document["schema_version"] == "3.0.0"
    assert len(document["claims"]) == 6


def test_checked_in_schema_is_current() -> None:
    path = ROOT / "contracts" / "themes.schema.json"
    assert json.loads(path.read_text(encoding="utf-8")) == case_schema()


def test_fallback_carries_previous() -> None:
    previous = build_case_payload(**_inputs())
    fallback = fallback_case_payload(
        previous,
        generated_at="2026-10-23T00:00:00+00:00",
        season="2026-27",
        reason="case_build_failed:RuntimeError",
    )
    assert fallback["state"] == "stale"
    assert fallback["stale_reason"] == "case_build_failed:RuntimeError"


def test_fallback_without_previous_is_explicit() -> None:
    fallback = fallback_case_payload(
        None,
        generated_at="2026-10-23T00:00:00+00:00",
        season="2026-27",
        reason="case_build_failed:RuntimeError",
    )
    assert fallback["state"] == "unavailable"
    assert all(claim["status"] == "cant_test" for claim in fallback["claims"])
