from __future__ import annotations

import pytest

from fitba.publish.manager_market import manager_market_payload

OPEN_STAFF = {
    "people": [
        {
            "person_id": "previous",
            "name": "Previous Manager",
            "stints": [
                {
                    "stint_id": "previous-2026",
                    "role": "Manager",
                    "role_group": "manager",
                    "start": "2026-03-12",
                    "end": "2026-11-09",
                    "interim": False,
                }
            ],
        },
        {
            "person_id": "stuart-duff",
            "name": "Stuart Duff",
            "stints": [
                {
                    "stint_id": "stuart-duff-interim-2026",
                    "role": "Interim manager",
                    "role_group": "manager",
                    "start": "2026-11-09",
                    "end": None,
                    "interim": True,
                }
            ],
        },
    ]
}

CLOSED_STAFF = {
    "people": [
        {
            "person_id": "permanent",
            "name": "Permanent Manager",
            "stints": [
                {
                    "stint_id": "permanent-2026",
                    "role": "Manager",
                    "role_group": "manager",
                    "start": "2026-11-12",
                    "end": None,
                    "interim": False,
                }
            ],
        }
    ]
}

MARKET = {
    "snapshot": {
        "source_id": "gambling_com",
        "provider": "Gambling.com",
        "publisher": "The Herald via Yahoo Sports",
        "observed_at": "2026-11-11T10:00:00Z",
        "source_url": "https://uk.sports.yahoo.com/news/example",
        "field_complete": False,
    },
    "candidates": [
        {
            "candidate_id": "tony-docherty",
            "name": "Tony Docherty",
            "odds_fractional": "4/1",
        },
        {
            "candidate_id": "michael-wimmer",
            "name": "Michael Wimmer",
            "odds_fractional": None,
        },
    ],
}


def _payload(staff: dict, market: dict = MARKET, mentions: list[dict] | None = None):
    return manager_market_payload(
        season="2026-27",
        generated_at="2026-11-11T12:00:00+00:00",
        staff=staff,
        market_config=market,
        mentions=mentions or [],
    )


def test_open_market_publishes_odds_and_mentions() -> None:
    payload = _payload(
        OPEN_STAFF,
        mentions=[
            {
                "candidate_id": "michael-wimmer",
                "mentions": 2,
                "topic_count": 1,
                "first_seen": "2026-11-10T17:21:48Z",
                "last_seen": "2026-11-11T10:08:50Z",
            }
        ],
    )
    assert payload["market"]["state"] == "open"
    assert payload["market"]["gate"]["interim_manager"] == "Stuart Duff"
    assert payload["market"]["gate"]["vacancy_started"] == "2026-11-09"
    rows = {row["candidate_id"]: row for row in payload["candidates"]}
    assert rows["tony-docherty"]["odds"]["decimal"] == 5.0
    assert rows["tony-docherty"]["odds"]["implied_probability"] == 0.2
    assert rows["michael-wimmer"]["status"] == "mentioned"
    assert rows["michael-wimmer"]["odds"] is None
    assert payload["market"]["coverage"]["priced_count"] == 1
    assert payload["market"]["coverage"]["mentioned_count"] == 1
    assert payload["market"]["coverage"]["overround"] is None


def test_closed_market_publishes_no_odds() -> None:
    payload = _payload(CLOSED_STAFF)
    assert payload["market"]["state"] == "closed"
    assert payload["candidates"] == []
    assert payload["market"]["gate"]["permanent_manager"] == "Permanent Manager"


def test_stale_odds_are_withheld_after_the_hard_limit() -> None:
    market = {
        **MARKET,
        "snapshot": {
            **MARKET["snapshot"],
            "observed_at": "2026-11-01T00:00:00Z",
        },
    }
    payload = _payload(
        OPEN_STAFF,
        market=market,
        mentions=[
            {
                "candidate_id": "michael-wimmer",
                "mentions": 1,
                "topic_count": 1,
                "first_seen": "2026-11-10T17:21:48Z",
                "last_seen": "2026-11-11T10:08:50Z",
            }
        ],
    )
    assert payload["market"]["coverage"]["status"] == "withheld"
    assert all(row["odds"] is None for row in payload["candidates"])
    assert payload["market"]["coverage"]["priced_count"] == 0


def test_affiliate_url_is_rejected() -> None:
    market = {
        **MARKET,
        "snapshot": {
            **MARKET["snapshot"],
            "source_url": "https://example.test/?utm_source=affiliate",
        },
    }
    with pytest.raises(ValueError, match="affiliate"):
        _payload(OPEN_STAFF, market=market)
