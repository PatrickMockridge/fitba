from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from fitba import update


def _state(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(update, "STATE_PATH", tmp_path / "update_state.json")


def _spec(
    step_id: str,
    runner,
    *,
    required: bool = False,
    network: bool = False,
    api_only: bool = False,
):
    return update.StepSpec(
        step_id,
        runner,
        required=required,
        network=network,
        api_only=api_only,
    )


def test_dry_run_lists_the_ordered_plan(monkeypatch: pytest.MonkeyPatch):
    report = update.run_update(mode="daily", dry_run=True)
    assert report["status"] == "dry_run"
    ids = [step["id"] for step in report["steps"]]
    assert ids[0] == "ingest.results"
    assert "ingest.scouting_pool" in ids
    assert "xg.enrich" in ids
    assert ids[-1] == "guard.metrics"


def test_required_failure_aborts_before_publish(tmp_path, monkeypatch):
    _state(tmp_path, monkeypatch)
    calls: list[str] = []

    def fail(_ctx):
        calls.append("fail")
        raise RuntimeError("boom")

    def publish(_ctx):
        calls.append("publish")
        return {"rows": 1}

    monkeypatch.setattr(
        update,
        "STEP_SPECS",
        [
            _spec("ingest.results", fail, required=True),
            _spec("publish", publish, required=True),
        ],
    )
    report = update.run_update(mode="daily", publish=True)
    assert report["status"] == "failed"
    assert calls == ["fail"]
    assert report["steps"][0]["status"] == "failed"


def test_optional_failure_is_recorded_and_continues(tmp_path, monkeypatch):
    _state(tmp_path, monkeypatch)
    calls: list[str] = []

    def fail(_ctx):
        calls.append("optional")
        raise RuntimeError("late feed")

    def ok(_ctx):
        calls.append("required")
        return {"rows": 2}

    monkeypatch.setattr(
        update,
        "STEP_SPECS",
        [
            _spec("ingest.cups", fail),
            _spec("warehouse.build", ok, required=True),
        ],
    )
    report = update.run_update(mode="daily", publish=False)
    assert report["status"] == "degraded"
    assert calls == ["optional", "required"]
    assert report["stale_sources"][0]["source"] == "ingest.cups"


def test_ci_records_network_steps_as_skipped_without_a_key(tmp_path, monkeypatch):
    _state(tmp_path, monkeypatch)
    monkeypatch.delenv("API_FOOTBALL_KEY", raising=False)
    calls: list[str] = []

    def network(_ctx):
        calls.append("network")
        return {}

    def local(_ctx):
        calls.append("local")
        return {}

    def results(_ctx):
        calls.append("results")
        return {}

    monkeypatch.setattr(
        update,
        "STEP_SPECS",
        [
            _spec("ingest.cups", network, network=True, api_only=True),
            _spec("ingest.results", results, required=True, network=True),
            _spec("warehouse.build", local, required=True),
        ],
    )
    report = update.run_update(mode="ci", publish=False)
    assert calls == ["results", "local"]
    skipped = [step for step in report["steps"] if step["status"] == "skipped"]
    assert skipped and skipped[0]["error"] == "missing_api_key"


def test_matchday_mode_stops_when_no_result_is_due(tmp_path, monkeypatch):
    _state(tmp_path, monkeypatch)
    called: list[str] = []

    def runner(_ctx):
        called.append("ran")
        return {}

    monkeypatch.setattr(update, "STEP_SPECS", [_spec("ingest.results", runner, required=True)])
    monkeypatch.setattr(update, "refresh_due", lambda **_: False)
    report = update.run_update(mode="matchday", publish=False)
    assert report["status"] == "not_due"
    assert called == []


def test_state_file_is_written_atomically(tmp_path, monkeypatch):
    _state(tmp_path, monkeypatch)
    monkeypatch.setattr(
        update,
        "STEP_SPECS",
        [_spec("warehouse.build", lambda _ctx: {"rows": 1}, required=True)],
    )
    report = update.run_update(mode="daily", publish=False)
    saved = json.loads((tmp_path / "update_state.json").read_text())
    assert saved["run_id"] == report["update_id"]
    assert saved["steps"][0]["status"] == "ok"


def test_update_honours_only_and_skip(monkeypatch: pytest.MonkeyPatch):
    report = update.run_update(
        mode="daily",
        dry_run=True,
        only="ingest.results,warehouse.build,publish",
        skip="publish",
    )
    ids = [step["id"] for step in report["steps"]]
    assert ids == ["ingest.results", "warehouse.build"]


def test_refresh_due_accepts_an_explicit_now(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(update, "refresh_due", lambda **_: True)
    report = update.run_update(
        mode="matchday",
        force_run=True,
        dry_run=True,
        only="ingest.results",
    )
    assert report["status"] == "dry_run"


def test_next_refresh_uses_the_finish_buffer():
    schedule = {
        "scheduled": [
            {
                "date": "2026-10-24",
                "kickoff": "15:00",
                "home_team_id": "sco:a",
                "away_team_id": "sco:b",
            }
        ]
    }
    assert update.refresh_due(
        now=datetime(2026, 10, 24, 18, 0, tzinfo=UTC),
        fixtures_index=schedule,
        manifest={"generated_at": "2026-10-24T10:00:00+00:00"},
    )
