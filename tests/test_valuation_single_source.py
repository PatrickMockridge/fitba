from __future__ import annotations

from typing import Any

import pytest

import fitba.publish.history as history_module
from fitba.analytics.valuation import summarise_valuations, value_transfers
from fitba.settings import NORMALIZED_DIR

HAS_MATCHES = (NORMALIZED_DIR / "matches").exists()

ROWS: list[dict[str, Any]] = [
    {
        "transfer_id": "t1",
        "player_key": "api:player:1",
        "direction": "in",
        "transfer_kind": "permanent",
        "fee_status": "disclosed",
        "fee_amount": 500_000,
        "fee_currency": "GBP",
        "position": "Midfielder",
        "date_effective": "2025-07-01",
        "from_club_id": "eng:club",
        "from_club_name": "English Club",
        "to_club_id": "sco:aberdeen",
        "to_club_name": "Aberdeen",
    },
    {
        "transfer_id": "t2",
        "player_key": "api:player:2",
        "direction": "out",
        "transfer_kind": "permanent",
        "fee_status": "disclosed",
        "fee_amount": 1_000_000,
        "fee_currency": "GBP",
        "position": "Attacker",
        "date_effective": "2025-08-01",
        "from_club_id": "sco:aberdeen",
        "from_club_name": "Aberdeen",
        "to_club_id": "eng:club",
        "to_club_name": "English Club",
    },
]

BIRTH_DATES = {"api:player:1": "2000-01-01", "api:player:2": "1999-01-01"}
MARKETS = [
    {"club_id": "eng:club", "club_name": "English Club", "market": "england"},
    {"club_id": "sco:aberdeen", "club_name": "Aberdeen", "market": "scotland"},
]


def test_value_transfers_attaches_and_summarises() -> None:
    rows = [dict(row) for row in ROWS]
    summary = value_transfers(rows, birth_dates=BIRTH_DATES, markets=MARKETS)
    assert all(row.get("fee_estimate") for row in rows)
    assert summary["anchor_count"] == 2
    assert summary["counts"]["disclosed"] == 2
    expected = summarise_valuations(rows)
    assert summary["counts"] == expected["counts"]
    assert summary["fee_low_gbp"] == expected["fee_low_gbp"]
    assert summary["fee_high_gbp"] == expected["fee_high_gbp"]


@pytest.mark.skipif(
    not HAS_MATCHES,
    reason="requires the local normalized match layer",
)
def test_history_uses_the_supplied_valuation(monkeypatch) -> None:
    rows = [dict(row) for row in ROWS]
    valuation = value_transfers(rows, birth_dates=BIRTH_DATES, markets=MARKETS)

    def fail(*args, **kwargs):
        raise AssertionError("history recalculated the valuation")

    monkeypatch.setattr(history_module, "value_transfers", fail)
    payloads = history_module.build_history_payloads(
        generated_at="2026-10-22T00:00:00+00:00",
        season="2026-27",
        transfers=rows,
        valuation=valuation,
    )
    assert "valuation" in payloads["index"]["scorecard"]["recruitment"]
