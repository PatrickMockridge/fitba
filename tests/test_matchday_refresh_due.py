"""Tests for the post-match refresh gate."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "matchday_refresh_due", ROOT / "scripts" / "matchday_refresh_due.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _schedule(*rows: dict) -> dict:
    return {"scheduled": list(rows)}


def test_refresh_after_a_finished_summer_fixture() -> None:
    schedule = _schedule(
        {
            "date": "2026-10-24",
            "kickoff": "15:00",
            "status": "scheduled",
        }
    )
    manifest = {"generated_at": "2026-10-24T10:00:00+00:00"}
    # 15:00 Europe/London on 24 October is 14:00 UTC; three hours later is
    # 17:00 UTC.
    assert MODULE.refresh_due(schedule, manifest, datetime(2026, 10, 24, 18, 0, tzinfo=UTC))


def test_no_refresh_before_the_finish_buffer() -> None:
    schedule = _schedule({"date": "2026-10-24", "kickoff": "15:00", "status": "scheduled"})
    manifest = {"generated_at": "2026-10-24T10:00:00+00:00"}
    assert not MODULE.refresh_due(schedule, manifest, datetime(2026, 10, 24, 16, 0, tzinfo=UTC))


def test_no_refresh_when_data_is_newer_than_the_finish() -> None:
    schedule = _schedule({"date": "2026-10-24", "kickoff": "15:00", "status": "scheduled"})
    manifest = {"generated_at": "2026-10-24T19:00:00+00:00"}
    assert not MODULE.refresh_due(schedule, manifest, datetime(2026, 10, 24, 20, 0, tzinfo=UTC))


def test_refresh_uses_winter_time() -> None:
    schedule = _schedule({"date": "2026-12-05", "kickoff": "15:00", "status": "scheduled"})
    manifest = {"generated_at": "2026-12-05T10:00:00+00:00"}
    # 15:00 Europe/London in December is 15:00 UTC; the finish is 18:00 UTC.
    assert MODULE.refresh_due(schedule, manifest, datetime(2026, 12, 5, 19, 0, tzinfo=UTC))


def test_no_refresh_for_a_future_fixture() -> None:
    schedule = _schedule({"date": "2026-11-07", "kickoff": "15:00", "status": "scheduled"})
    manifest = {"generated_at": "2026-10-24T10:00:00+00:00"}
    assert not MODULE.refresh_due(schedule, manifest, datetime(2026, 10, 24, 20, 0, tzinfo=UTC))


def test_no_refresh_without_a_kickoff_or_a_schedule() -> None:
    manifest = {"generated_at": "2026-10-24T10:00:00+00:00"}
    now = datetime(2026, 10, 24, 20, 0, tzinfo=UTC)
    assert not MODULE.refresh_due(_schedule({"date": "2026-10-24", "kickoff": None}), manifest, now)
    assert not MODULE.refresh_due({}, manifest, now)


def test_missing_manifest_refreshes_a_finished_fixture() -> None:
    schedule = _schedule({"date": "2026-10-24", "kickoff": "15:00", "status": "scheduled"})
    assert MODULE.refresh_due(schedule, {}, datetime(2026, 10, 24, 18, 0, tzinfo=UTC))
