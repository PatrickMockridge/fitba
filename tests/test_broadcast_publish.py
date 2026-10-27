from __future__ import annotations

import pytest

from fitba.publish.broadcast import build_broadcast_payload
from fitba.settings import broadcast_policy, broadcast_reference

SEASON = "2026-27"
FALKIRK = {
    "fixture_id": 1556688,
    "season": SEASON,
    "date": "2026-10-28",
    "kickoff": "19:45",
    "competition_id": "sco:premiership",
    "competition_name": "Scottish Premiership",
    "home_team_name": "Aberdeen",
    "away_team_name": "Falkirk",
    "venue": "Pittodrie Stadium",
    "status": "scheduled",
}


def _row(**overrides) -> dict:
    row = dict(FALKIRK)
    row.update(overrides)
    return row


def _build(rows: list[dict], reference=None):
    return build_broadcast_payload(
        season=SEASON,
        generated_at="2026-10-27T00:00:00+00:00",
        scheduled_rows=rows,
        reference=reference if reference is not None else broadcast_reference(),
        policy=broadcast_policy(),
    )


def test_falkirk_is_domestic_redtv_ppv_and_international_unknown() -> None:
    document = _build([_row()])
    row = document["fixtures"][0]
    assert row["state"] == "curated"
    assert row["domestic"]["status"] == "confirmed"
    assert row["domestic"]["outlets"] == [
        {"platform": "RedTV", "medium": "video", "access": "ppv"}
    ]
    assert row["international"]["status"] == "unknown"
    assert row["sources"][0]["source_id"] == "afc_news"
    assert "£" not in str(document)
    assert "price" not in str(document).lower()


def test_uncurated_saturday_1500_is_a_blackout_and_wednesday_is_not_announced() -> None:
    saturday = _row(
        fixture_id=999001,
        date="2026-11-21",
        kickoff="15:00",
        away_team_name="Kilmarnock",
    )
    wednesday = _row(
        fixture_id=999002,
        date="2026-12-02",
        kickoff="19:45",
        away_team_name="Hearts",
    )
    document = _build([saturday, wednesday])
    by_id = {row["fixture_id"]: row for row in document["fixtures"]}
    assert by_id["999001"]["domestic"]["status"] == "blackout_window"
    assert by_id["999001"]["international"]["status"] == "unknown"
    assert by_id["999002"]["domestic"]["status"] == "not_announced"
    assert by_id["999002"]["international"]["status"] == "unknown"


def test_conflict_review_withholds_both_regions() -> None:
    document = _build(
        [
            _row(
                fixture_id=999003,
                status="conflict_review",
                conflict_review=True,
                date="2026-10-31",
                kickoff="15:00",
            )
        ]
    )
    row = document["fixtures"][0]
    assert row["state"] == "fixture_conflict"
    assert row["domestic"]["status"] == "unknown"
    assert row["international"]["status"] == "unknown"
    assert row["domestic"]["outlets"] == []


def test_identity_mismatch_withholds_the_curated_claim() -> None:
    document = _build([_row(kickoff="20:00")])
    row = document["fixtures"][0]
    assert row["state"] == "source_conflict"
    assert row["domestic"]["status"] == "unknown"
    assert row["domestic"]["outlets"] == []


def test_a_disallowed_source_host_is_rejected() -> None:
    reference = {
        "version": 1,
        "season": SEASON,
        "updated_at": "2026-10-27",
        "fixtures": [
            {
                "fixture_id": "1556688",
                "season": SEASON,
                "date": "2026-10-28",
                "kickoff": "19:45",
                "competition_id": "sco:premiership",
                "home_team_name": "Aberdeen",
                "away_team_name": "Falkirk",
                "domestic": {
                    "status": "confirmed",
                    "outlets": [
                        {"platform": "RedTV", "medium": "video", "access": "ppv"}
                    ],
                    "source_ids": ["afc_news"],
                },
                "international": {"status": "unknown", "outlets": [], "source_ids": []},
                "sources": [
                    {
                        "source_id": "afc_news",
                        "url": "https://www.premiersports.com/gb",
                        "title": "Not an allowed host",
                        "verified_at": "2026-10-27",
                        "confidence": "confirmed",
                    }
                ],
            }
        ],
    }
    with pytest.raises(ValueError, match="not allowed"):
        _build([_row()], reference)


def test_curated_orphans_do_not_create_fixture_rows() -> None:
    document = _build([])
    assert document["fixtures"] == []
