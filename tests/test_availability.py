from __future__ import annotations

from fitba.ingest import availability as ingest
from fitba.publish.availability import build_availability_payload


def _squad():
    return {
        "players": [
            {"player_id": 1, "name": "Player One", "player_key": "api:player:1"},
            {"player_id": 2, "name": "Player Two", "player_key": "api:player:2"},
        ]
    }


def _entry(**overrides):
    base = {
        "player_key": "api:player:1",
        "player_name": "Player One",
        "status": "out",
        "reason_category": "injury",
        "reason": "Injured",
        "source_id": "afc_news",
        "source_url": "https://www.afc.co.uk/news/team-news",
        "verified_at": "2026-10-21",
        "confidence": "confirmed",
        "note": "Official team news.",
    }
    base.update(overrides)
    return base


def test_merge_accepts_verified_afc_entry(monkeypatch):
    monkeypatch.setattr(ingest, "_rows", lambda: [_entry()])
    entries = ingest._merge(squad_data=_squad(), provider={"rows": []})
    row = next(item for item in entries if item["player_id"] == 1)
    assert row["status"] == "out"
    assert row["stale"] is False
    assert row["in_squad"] is True


def test_merge_rejects_missing_source_url(monkeypatch):
    monkeypatch.setattr(ingest, "_rows", lambda: [_entry(source_url=None)])
    entries = ingest._merge(squad_data=_squad(), provider={"rows": []})
    row = next(item for item in entries if item["player_id"] == 1)
    assert row["status"] == "unknown"


def test_merge_rejects_stale_entry(monkeypatch):
    monkeypatch.setattr(ingest, "_rows", lambda: [_entry(verified_at="2020-01-01")])
    entries = ingest._merge(squad_data=_squad(), provider={"rows": []})
    row = next(item for item in entries if item["player_id"] == 1)
    assert row["status"] == "unknown"
    assert row["stale"] is True


def test_provider_signal_alone_stays_unknown(monkeypatch):
    monkeypatch.setattr(ingest, "_rows", lambda: [])
    entries = ingest._merge(
        squad_data=_squad(),
        provider={
            "rows": [
                {
                    "player_id": 2,
                    "player_name": "Player Two",
                    "type": "Missing Fixture",
                    "reason": "Injury",
                    "date": "2026-10-21",
                }
            ]
        },
    )
    row = next(item for item in entries if item["player_id"] == 2)
    assert row["status"] == "unknown"
    assert row["provider_signal"] == "out"


def test_conflict_is_flagged(monkeypatch):
    monkeypatch.setattr(
        ingest,
        "_rows",
        lambda: [_entry(status="available", reason_category="unknown")],
    )
    entries = ingest._merge(
        squad_data=_squad(),
        provider={
            "rows": [
                {
                    "player_id": 1,
                    "player_name": "Player One",
                    "type": "Missing Fixture",
                    "reason": "Injury",
                    "date": "2026-10-21",
                }
            ]
        },
    )
    row = next(item for item in entries if item["player_id"] == 1)
    assert row["status"] == "available"
    assert row["conflict"] is True


def test_payload_unknown_without_ledger(monkeypatch):
    monkeypatch.setattr(ingest, "_rows", lambda: [])
    payload = build_availability_payload(
        squad_data=_squad(),
        generated_at="2026-10-22T00:00:00+00:00",
        season="2026-27",
    )
    assert payload["state"] == "unavailable"
    assert payload["coverage"]["known"] == 0
    assert all(entry["status"] == "unknown" for entry in payload["entries"])
