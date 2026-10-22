from datetime import date
from pathlib import Path

import pytest

from fitba.ingest.forum import (
    Gazetteer,
    GazetteerEntry,
    _cross_reference,
    capitalised_bigrams,
    extract_mentions,
    plausible_name,
    score_text,
    summarize_sentiment,
)
from fitba.publish.rumours import _validate, profile_payload
from fitba.publish.squad import PlayerLinkIndex
from fitba.sources.afc_chat import parse_feed, parse_topic

FIXTURES = Path(__file__).parent / "fixtures"


def _gazetteer(*entries: GazetteerEntry) -> Gazetteer:
    gazetteer = Gazetteer()
    for entry in entries:
        gazetteer.add(entry)
    return gazetteer


def test_parse_feed_orders_topics_and_extracts_ids():
    topics = parse_feed((FIXTURES / "afc_chat_feed.xml").read_bytes())
    assert [topic["topic_id"] for topic in topics] == ["49531", "49303"]
    assert topics[0]["title"] == "January 2027 transfer window"
    assert str(topics[0]["published_at"]).startswith("2026-09-01")


def test_parse_topic_strips_quoted_post_text():
    posts = parse_topic((FIXTURES / "afc_chat_topic.html").read_text(encoding="utf-8"))
    assert len(posts) == 3
    assert posts[1]["comment_id"] == "3186195"
    text = str(posts[1]["text"])
    assert "Killian Phillips" in text
    # The quoted post must not be counted twice.
    assert "heartbeat" not in text


def test_capitalised_bigrams_and_plausibility_filter():
    text = "David Turnbull would be good. The Cormack way. Killian Phillips too."
    assert "David Turnbull" in capitalised_bigrams(text)
    assert plausible_name("David Turnbull")
    assert not plausible_name("The Cormack")
    assert not plausible_name("January Window")


def test_extract_full_name_and_unique_surname():
    gazetteer = _gazetteer(
        GazetteerEntry(name="David Turnbull", player_key="api:player:1"),
        GazetteerEntry(name="Killian Phillips", player_key="api:player:2"),
        GazetteerEntry(name="Dimitar Mitov", player_key="api:player:3"),
    )
    text = "I would take David Turnbull. I rate Turnbull. I thought Mitov was excellent."
    names = {entry.name for entry in extract_mentions(text, gazetteer)}
    assert {"David Turnbull", "Dimitar Mitov"} <= names


def test_ambiguous_surname_is_not_guessed():
    gazetteer = _gazetteer(
        GazetteerEntry(name="Nicky Devlin", player_key="api:player:1"),
        GazetteerEntry(name="Cameron Devlin", player_key="api:player:2"),
    )
    assert extract_mentions("I like Devlin in midfield.", gazetteer) == []


def test_cross_reference_labels():
    today = date.today().isoformat()
    entry = GazetteerEntry(name="Killian Phillips", source="api_name_check")
    fan_only = _cross_reference(entry, transfers=[], rumours=[], news_titles=[])
    assert fan_only["credibility"] == "fan_only"

    press = _cross_reference(
        entry,
        transfers=[],
        rumours=[{"player_name": "K. Phillips", "source_types": ["press"], "status": "active"}],
        news_titles=[],
    )
    assert press["credibility"] == "cross_referenced_press"

    squad = _cross_reference(
        GazetteerEntry(name="Dimitar Mitov", source="aberdeen_squad"),
        transfers=[],
        rumours=[],
        news_titles=[],
    )
    assert squad["credibility"] == "club_player"

    transfer = _cross_reference(
        entry,
        transfers=[{"player_name": "K. Phillips", "date_effective": today}],
        rumours=[],
        news_titles=[],
    )
    assert transfer["credibility"] == "cross_referenced_transfer"


def test_sentiment_summary_shares():
    assert score_text("Great win, brilliant performance")["compound"] > 0
    assert score_text("Terrible, awful defeat")["compound"] < 0
    summary = summarize_sentiment([0.8, 0.0, -0.7])
    assert summary["count"] == 3
    total = summary["positive_share"] + summary["neutral_share"] + summary["negative_share"]
    assert total == pytest.approx(1.0, abs=1e-2)


def test_rumour_validation_rejects_unsourced_and_unlinked_confirmed():
    base = {
        "rumour_id": "rum:test",
        "status": "active",
        "confidence": "low",
        "direction": "in",
        "source_types": ["press"],
        "source_urls": ["https://example.com/story"],
    }
    _validate(base)

    with pytest.raises(ValueError, match="source_url"):
        _validate({**base, "source_urls": []})

    with pytest.raises(ValueError, match="must link a transfer"):
        _validate({**base, "status": "confirmed"})

    with pytest.raises(ValueError, match="only valid when confirmed"):
        _validate({**base, "linked_transfer_id": "afc:1"})


def test_profile_flags_small_cohort_and_weights_confidence():
    rows = [
        {
            "rumour_id": "rum:1",
            "player_name": "A Player",
            "status": "active",
            "confidence": "high",
            "position": "W",
            "age": 22,
            "league": "Premiership",
            "value_band": "1m-2m",
            "last_seen": date.today().isoformat(),
        },
        {
            "rumour_id": "rum:2",
            "player_name": "B Player",
            "status": "active",
            "confidence": "low",
            "position": "ST",
            "age": 29,
            "league": "Championship",
            "value_band": "unknown",
            "last_seen": date.today().isoformat(),
        },
        {
            "rumour_id": "rum:3",
            "player_name": "C Player",
            "status": "stale",
            "confidence": "high",
            "position": "CB",
            "age": 24,
            "league": "Premiership",
            "value_band": "under-500k",
            "last_seen": date.today().isoformat(),
        },
    ]
    profile = profile_payload(rows, PlayerLinkIndex.from_payload({"players": []}))
    assert profile["sample_size"] == 2
    assert profile["low_confidence"] is True
    assert profile["buckets"]["position"]["W"] > profile["buckets"]["position"]["ST"]
    assert profile["weighted_total"] > 0
