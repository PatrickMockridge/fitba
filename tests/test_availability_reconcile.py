from __future__ import annotations

from datetime import date

import pytest

from fitba.analytics.availability_reconcile import (
    assert_no_unresolved_contradictions,
    ledger_review,
    reconcile_entries,
    reconcile_entry,
)

TODAY = date(2026, 11, 9)
POLICY = {
    "fresh_days": 7,
    "max_age_days": 21,
    "suspensions": {
        "red_cards": {
            "categories": {"second_yellow": 1, "other": 1},
            "same_competition": True,
            "verified": False,
            "source_url": "https://example.test/rules.pdf",
        }
    },
}


def _entry(
    status: str,
    *,
    verified_at: str = "2026-11-08",
    competition_id: str | None = None,
) -> dict:
    return {
        "player_id": 1,
        "player_name": "Test Player",
        "status": status,
        "competition_id": competition_id,
        "reason": "recorded claim",
        "reason_category": "injury",
        "source_id": "afc_news",
        "source_url": "https://www.afc.co.uk/en/news/example",
        "verified_at": verified_at,
    }


def _participation(
    fixture_id: int,
    *,
    date_text: str = "2026-11-07",
    competition_id: str = "sco:premiership",
    squad_status: str = "starter",
    bench_complete: bool = True,
    player_id: int = 1,
) -> dict:
    return {
        "player_id": player_id,
        "fixture_id": fixture_id,
        "date": date_text,
        "competition_id": competition_id,
        "opponent_name": "Opponent",
        "team_id": 252,
        "squad_status": squad_status,
        "started": squad_status == "starter",
        "minutes": 90 if squad_status == "starter" else 10,
        "bench_complete": bench_complete,
    }


def _schedule(
    fixture_id: int,
    date_text: str,
    competition_id: str,
    *,
    status: str = "played",
) -> dict:
    return {
        "fixture_id": fixture_id,
        "date": date_text,
        "competition_id": competition_id,
        "opponent_name": "Opponent",
        "status": status,
        "bench_complete": True,
    }


def _evidence(
    *,
    participation: list[dict] | None = None,
    schedule: list[dict] | None = None,
    red_cards: list[dict] | None = None,
) -> dict:
    return {
        "status": "ok",
        "participation": participation or [],
        "schedule": schedule or [],
        "red_cards": red_cards or [],
        "coverage": {"fixtures": 1, "with_squads": 1, "complete_bench": 1},
    }


def test_out_player_who_starts_becomes_unknown() -> None:
    entry = _entry("out", verified_at="2026-10-27")
    evidence = _evidence(participation=[_participation(1)])
    result = reconcile_entry(entry, evidence, POLICY, TODAY)
    assert result["status"] == "unknown"
    assert result["original_status"] == "out"
    assert result["review_severity"] == "contradicted"
    assert result["review_reason"] == "appeared_after_status"
    assert result["contradicted_by"]["fixture_id"] == 1


def test_out_player_on_incomplete_bench_is_not_a_hard_contradiction() -> None:
    entry = _entry("out", verified_at="2026-11-08")
    evidence = _evidence(
        participation=[_participation(1, squad_status="sub_unused", bench_complete=False)]
    )
    result = reconcile_entry(entry, evidence, POLICY, TODAY)
    assert result["status"] == "out"
    assert result["review_required"] is False


def test_doubtful_player_who_starts_is_withdrawn() -> None:
    entry = _entry("doubtful", verified_at="2026-10-27")
    evidence = _evidence(participation=[_participation(1)])
    result = reconcile_entry(entry, evidence, POLICY, TODAY)
    assert result["status"] == "unknown"
    assert result["review_reason"] == "doubt_resolved_by_appearance"


def test_doubtful_player_unused_on_bench_is_consistent() -> None:
    entry = _entry("doubtful", verified_at="2026-11-08")
    evidence = _evidence(participation=[_participation(1, squad_status="sub_unused")])
    result = reconcile_entry(entry, evidence, POLICY, TODAY)
    assert result["status"] == "doubtful"
    assert result["review_required"] is False


def test_cup_suspension_is_served_by_the_next_cup_fixture() -> None:
    entry = _entry("suspended", verified_at="2026-10-27", competition_id="sco:league-cup")
    evidence = _evidence(
        schedule=[
            _schedule(1, "2026-09-12", "sco:league-cup"),
            _schedule(2, "2026-10-31", "sco:league-cup"),
            _schedule(3, "2026-10-28", "sco:premiership"),
        ],
        participation=[_participation(3, date_text="2026-10-28")],
        red_cards=[
            {
                "player_id": 1,
                "fixture_id": 1,
                "date": "2026-09-12",
                "competition_id": "sco:league-cup",
                "red_type": "second_yellow",
            }
        ],
    )
    result = reconcile_entry(entry, evidence, POLICY, TODAY)
    assert result["status"] == "unknown"
    assert result["review_reason"] == "suspension_served"
    assert result["suspension"]["state"] == "served"
    assert result["suspension"]["served_fixture_id"] == 2
    assert result["suspension"]["ban_matches"] == 1


def test_league_appearance_does_not_contradict_a_cup_ban() -> None:
    entry = _entry("suspended", verified_at="2026-10-27", competition_id="sco:league-cup")
    evidence = _evidence(
        schedule=[
            _schedule(1, "2026-09-12", "sco:league-cup"),
            _schedule(2, "2026-10-31", "sco:league-cup"),
            _schedule(3, "2026-10-28", "sco:premiership"),
        ],
        participation=[_participation(3, date_text="2026-10-28")],
        red_cards=[
            {
                "player_id": 1,
                "fixture_id": 1,
                "date": "2026-09-12",
                "competition_id": "sco:league-cup",
                "red_type": "second_yellow",
            }
        ],
    )
    result = reconcile_entry(entry, evidence, POLICY, TODAY)
    assert result["suspension"]["state"] == "served"


def test_same_competition_appearance_is_not_applied() -> None:
    entry = _entry("suspended", verified_at="2026-10-27", competition_id="sco:league-cup")
    evidence = _evidence(
        schedule=[
            _schedule(1, "2026-09-12", "sco:league-cup"),
            _schedule(2, "2026-10-31", "sco:league-cup"),
        ],
        participation=[_participation(2, date_text="2026-10-31", competition_id="sco:league-cup")],
        red_cards=[
            {
                "player_id": 1,
                "fixture_id": 1,
                "date": "2026-09-12",
                "competition_id": "sco:league-cup",
                "red_type": "second_yellow",
            }
        ],
    )
    result = reconcile_entry(entry, evidence, POLICY, TODAY)
    assert result["status"] == "unknown"
    assert result["review_reason"] == "suspension_not_applied"
    assert result["suspension"]["state"] == "not_applied"


def test_no_remaining_fixture_resolves_the_claim() -> None:
    entry = _entry("suspended", verified_at="2026-10-27", competition_id="sco:league-cup")
    evidence = _evidence(
        schedule=[_schedule(1, "2026-09-12", "sco:league-cup")],
        red_cards=[
            {
                "player_id": 1,
                "fixture_id": 1,
                "date": "2026-09-12",
                "competition_id": "sco:league-cup",
                "red_type": "second_yellow",
            }
        ],
    )
    result = reconcile_entry(entry, evidence, POLICY, TODAY)
    assert result["status"] == "unknown"
    assert result["review_reason"] == "suspension_resolved"


def test_unknown_suspension_scope_is_aging_not_hard() -> None:
    entry = _entry("suspended", verified_at="2026-11-08")
    result = reconcile_entry(entry, _evidence(), POLICY, TODAY)
    assert result["status"] == "suspended"
    assert result["review_severity"] == "aging"
    assert result["review_reason"] == "suspension_scope_unknown"


def test_status_age_bands() -> None:
    aging = reconcile_entry(_entry("out", verified_at="2026-11-01"), _evidence(), POLICY, TODAY)
    assert aging["status"] == "out"
    assert aging["review_severity"] == "aging"
    assert aging["review_reason"] == "status_older_than_7_days"

    stale = reconcile_entry(_entry("out", verified_at="2026-10-18"), _evidence(), POLICY, TODAY)
    assert stale["status"] == "unknown"
    assert "status_older_than_max_age" in stale["review_reasons"]


def test_unresolved_contradiction_assertion() -> None:
    entries = [
        {
            "player_id": 1,
            "player_name": "Test Player",
            "status": "out",
            "review_severity": "contradicted",
        }
    ]
    with pytest.raises(ValueError, match="contradicted availability"):
        assert_no_unresolved_contradictions(entries)


def test_reconcile_entries_summarises_review() -> None:
    entries = [
        _entry("out", verified_at="2026-10-27"),
        _entry("doubtful", verified_at="2026-11-08"),
    ]
    evidence = _evidence(participation=[_participation(1)])
    reconciled, summary = reconcile_entries(entries, evidence, POLICY, TODAY)
    assert reconciled[0]["status"] == "unknown"
    assert summary["contradicted"] == 1
    assert summary["count"] == 1
    assert summary["status"] == "contradicted"


def test_ledger_review_flags_newer_news() -> None:
    review = ledger_review(
        "2026-10-27",
        "2026-10-27",
        {"date": "2026-11-08", "title": "Latest", "url": "https://example.test"},
        {"ledger_news_review": True},
        TODAY,
    )
    assert review["status"] == "review"
    assert review["reason"] == "ledger_older_than_latest_news"
    assert review["days_since_ledger_update"] == 13
