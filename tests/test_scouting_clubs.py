from __future__ import annotations

from datetime import date

from fitba.ingest.scouting_clubs import _status_for, latest_transfer


def _transfer(day: str, kind: str = "Transfer", current: str = "Club") -> dict:
    return {
        "date": day,
        "type": kind,
        "teams": {"in": {"id": 1, "name": current}, "out": {"id": 2, "name": "Old"}},
    }


def test_latest_transfer_ignores_future_and_picks_latest():
    transfers = [
        _transfer("2024-01-01"),
        _transfer("2026-08-10", current="Sevilla"),
        _transfer("2026-12-01", current="Future"),
    ]
    found = latest_transfer(transfers, today=date(2026, 10, 23))
    assert found is not None
    assert (found.get("teams") or {}).get("in", {}).get("name") == "Sevilla"
    before = latest_transfer(transfers, today=date(2026, 8, 1))
    assert before is not None
    assert (before.get("teams") or {}).get("in", {}).get("name") == "Club"


def test_statuses():
    assert _status_for(_transfer("2026-01-01", "Loan"), "Club") == "loan"
    assert _status_for(_transfer("2026-01-01", "Back from Loan"), "Club") == "transferred"
    assert _status_for(_transfer("2026-01-01", "Free"), "Without Club") == "free_agent"
    assert _status_for(_transfer("2026-01-01", "Transfer"), "Retired") == "retired"
    assert _status_for(_transfer("2026-01-01", "Transfer"), "Sevilla") == "transferred"
