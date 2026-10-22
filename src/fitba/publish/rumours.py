"""Build the published rumour, opinion and fan-signal payloads.

The rumour register is curated in ``reference/rumours.yaml``. The fan signal is
derived from sampled AFC Chat first pages. Neither is the confirmed transfer
register; the two never merge.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from fitba.ingest.forum import (
    build_profile,
    load_forum_posts,
    load_forum_signals,
    load_forum_topics,
    summarize_sentiment,
)
from fitba.ingest.news import load_news
from fitba.settings import rumours as rumours_config
from fitba.settings import source_registry
from fitba.util.dates import utc_now_iso

if TYPE_CHECKING:
    from fitba.publish.squad import PlayerLinkIndex

VALID_STATUS = {"active", "denied", "confirmed", "stale"}
VALID_CONFIDENCE = {"low", "medium", "high"}
VALID_DIRECTION = {"in", "out"}
VALID_SOURCES = {"press", "journalist", "forum", "club"}
VALID_VALUE_BANDS = {
    "free",
    "loan",
    "under-500k",
    "500k-1m",
    "1m-2m",
    "2m-plus",
    "unknown",
}
CONFIDENCE_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.3}
RECENCY_HALF_LIFE_DAYS = 180
RECENCY_FLOOR = 0.35


def _today() -> date:
    return datetime.now().date()


def _validate(row: dict[str, Any]) -> None:
    rumour_id = row.get("rumour_id") or "<missing id>"
    if row.get("status") not in VALID_STATUS:
        raise ValueError(f"{rumour_id}: invalid status {row.get('status')!r}")
    if row.get("confidence") not in VALID_CONFIDENCE:
        raise ValueError(f"{rumour_id}: invalid confidence {row.get('confidence')!r}")
    if row.get("direction") not in VALID_DIRECTION:
        raise ValueError(f"{rumour_id}: invalid direction {row.get('direction')!r}")
    sources = set(row.get("source_types") or [])
    if not sources or not sources <= VALID_SOURCES:
        raise ValueError(f"{rumour_id}: source_types must be a subset of {sorted(VALID_SOURCES)}")
    if not row.get("source_urls"):
        raise ValueError(f"{rumour_id}: at least one source_url is required")
    if row.get("value_band") and row["value_band"] not in VALID_VALUE_BANDS:
        raise ValueError(f"{rumour_id}: invalid value_band {row.get('value_band')!r}")
    if row.get("status") == "confirmed" and not row.get("linked_transfer_id"):
        raise ValueError(f"{rumour_id}: a confirmed rumour must link a transfer")
    if row.get("status") != "confirmed" and row.get("linked_transfer_id"):
        raise ValueError(f"{rumour_id}: linked_transfer_id is only valid when confirmed")


def load_rumour_rows() -> list[dict[str, Any]]:
    rows = []
    for row in rumours_config().get("rumours", []) or []:
        _validate(row)
        rows.append(
            {
                "rumour_id": row.get("rumour_id"),
                "player_key": row.get("player_key"),
                "linked_player_key": row.get("linked_player_key") or row.get("player_key"),
                "player_name": row.get("player_name"),
                "linked_club": row.get("linked_club", "sco:aberdeen"),
                "direction": row.get("direction"),
                "current_club": row.get("current_club"),
                "position": row.get("position"),
                "age": row.get("age"),
                "league": row.get("league"),
                "value_band": row.get("value_band", "unknown"),
                "claim": row.get("claim"),
                "status": row.get("status"),
                "confidence": row.get("confidence"),
                "source_urls": row.get("source_urls", []),
                "source_types": row.get("source_types", []),
                "first_seen": str(row.get("first_seen")) if row.get("first_seen") else None,
                "last_seen": str(row.get("last_seen")) if row.get("last_seen") else None,
                "verified_at": str(row.get("verified_at")) if row.get("verified_at") else None,
                "linked_transfer_id": row.get("linked_transfer_id"),
                "analysis_tags": row.get("analysis_tags", []),
                # TODO(engagement): reserved for the separate engagement project.
                "engagement": None,
            }
        )
    return sorted(
        rows,
        key=lambda row: (row.get("last_seen") or "", row["player_name"]),
        reverse=True,
    )


def _opinion_payload(
    rows: list[dict[str, Any]], player_index: PlayerLinkIndex
) -> list[dict[str, Any]]:
    known = {row["rumour_id"] for row in rows}
    opinions = []
    for row in rumours_config().get("opinions", []) or []:
        evidence = [item for item in row.get("evidence", []) if item in known]
        if not evidence:
            continue
        opinions.append(
            {
                "opinion_id": row.get("opinion_id"),
                "title": row.get("title"),
                "stance": row.get("stance"),
                "body": row.get("body"),
                "evidence": evidence,
                "published": str(row.get("published")) if row.get("published") else None,
                "label": "Opinion — data-cited, not club guidance",
                "player_mentions": player_index.mentions(
                    f"{row.get('title') or ''} {row.get('body') or ''}"
                ),
            }
        )
    return opinions


def _counts(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        values = row.get(field)
        values = values if isinstance(values, list) else [values]
        for value in values:
            if value is None:
                continue
            key = str(value)
            result[key] = result.get(key, 0) + 1
    return dict(sorted(result.items()))


def rumours_payload(
    rows: list[dict[str, Any]],
    season: str,
    player_index: PlayerLinkIndex,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return {
        "club_id": "sco:aberdeen",
        "name": "Aberdeen",
        "season": season,
        "generated_at": generated_at or utc_now_iso(),
        "rumours": [
            {
                **row,
                "player_href": player_index.href(
                    row.get("player_key") or row.get("linked_player_key")
                ),
                "player_mentions": player_index.mentions(row.get("claim")),
            }
            for row in rows
        ],
        "opinions": _opinion_payload(rows, player_index),
        "summary": {
            "total": len(rows),
            "by_status": _counts(rows, "status"),
            "by_confidence": _counts(rows, "confidence"),
            "by_source_type": _counts(rows, "source_types"),
            "by_direction": _counts(rows, "direction"),
        },
        "coverage": {
            "status": "curated",
            "note": (
                "A curated register of Aberdeen-linked rumours, separate from the "
                "confirmed transfer register. Status is a lifecycle label, not a "
                "probability. Confidence is editorial and must be justified by the "
                "linked sources. Confirmed rows link to the transfer register and "
                "are then a historical record, not a second source of truth."
            ),
        },
        "notes": "No fabricated quotes, no player abuse, no betting framing.",
    }


def _recency_weight(last_seen: str | None) -> float:
    if not last_seen:
        return 0.5
    try:
        seen = date.fromisoformat(last_seen[:10])
    except ValueError:
        return 0.5
    age_days = max(0, (_today() - seen).days)
    decay = 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)
    return max(RECENCY_FLOOR, decay)


def _bucket(rows: list[dict[str, Any]], field: str, weight_of: Any) -> dict[str, float]:
    result: dict[str, float] = {}
    for row in rows:
        value = row.get(field)
        if value is None:
            continue
        key = str(value)
        result[key] = result.get(key, 0.0) + weight_of(row)
    return {key: round(value, 2) for key, value in sorted(result.items())}


def _age_band(age: Any) -> str | None:
    if age is None:
        return None
    try:
        value = int(age)
    except (TypeError, ValueError):
        return None
    if value < 21:
        return "under-21"
    if value < 24:
        return "21-23"
    if value < 27:
        return "24-26"
    if value < 30:
        return "27-29"
    return "30-plus"


def _share(count: float, total: float) -> float:
    return round(count / total, 3) if total else 0.0


def _narrative(buckets: dict[str, dict[str, float]], total: float, sample: int) -> str:
    if not sample or not total:
        return (
            "No active, curated links yet. The profile activates when the rumour "
            "register has sourced rows; until then it is deliberately empty."
        )
    position = max(buckets["position"], key=lambda key: buckets["position"][key], default=None)
    age = max(buckets["age_band"], key=lambda key: buckets["age_band"][key], default=None)
    league = max(buckets["league"], key=lambda key: buckets["league"][key], default=None)
    value = max(buckets["value_band"], key=lambda key: buckets["value_band"][key], default=None)
    parts = [f"{sample} active curated link{'s' if sample != 1 else ''}"]
    if position:
        parts.append(
            f"{position} is the largest position group "
            f"({_share(buckets['position'][position], total):.0%} of weight)"
        )
    if age:
        parts.append(f"the weighted age band is {age}")
    if value:
        parts.append(f"the most common value band is {value}")
    if league:
        parts.append(f"the most frequent league is {league}")
    return "; ".join(parts) + "."


def profile_payload(
    rows: list[dict[str, Any]],
    player_index: PlayerLinkIndex,
    generated_at: str | None = None,
) -> dict[str, Any]:
    active = [row for row in rows if row.get("status") == "active"]

    def weight_of(row: dict[str, Any]) -> float:
        return CONFIDENCE_WEIGHT.get(str(row.get("confidence")), 0.3) * _recency_weight(
            row.get("last_seen")
        )

    total = sum(weight_of(row) for row in active)
    buckets = {
        "position": _bucket(active, "position", weight_of),
        "age_band": {},
        "league": _bucket(active, "league", weight_of),
        "value_band": _bucket(active, "value_band", weight_of),
    }
    age_weights: dict[str, float] = {}
    for row in active:
        band = _age_band(row.get("age"))
        if band:
            age_weights[band] = age_weights.get(band, 0.0) + weight_of(row)
    buckets["age_band"] = {key: round(value, 2) for key, value in sorted(age_weights.items())}

    return {
        "club_id": "sco:aberdeen",
        "generated_at": generated_at or utc_now_iso(),
        "sample_size": len(active),
        "weighted_total": round(total, 2),
        "low_confidence": len(active) < 5,
        "weights": {
            "confidence": CONFIDENCE_WEIGHT,
            "recency_half_life_days": RECENCY_HALF_LIFE_DAYS,
            "recency_floor": RECENCY_FLOOR,
        },
        "buckets": buckets,
        "narrative": _narrative(buckets, total, len(active)),
        "signals": [
            {
                "rumour_id": row["rumour_id"],
                "player_name": row["player_name"],
                "position": row.get("position"),
                "age": row.get("age"),
                "league": row.get("league"),
                "value_band": row.get("value_band"),
                "confidence": row.get("confidence"),
                "weight": round(weight_of(row), 2),
                "player_href": player_index.href(
                    row.get("player_key") or row.get("linked_player_key")
                ),
            }
            for row in active
        ],
        "note": (
            "Advisory only. The data-driven scouting fit stays primary; a small "
            "rumour cohort must never override it. The club's internal target "
            "list is not public and is not implied."
        ),
    }


def _forum_sentiment() -> dict[str, Any]:
    posts = load_forum_posts()
    forum_values = [float(value) for value in posts["compound"].to_list()] if posts.height else []
    press_claims = [
        str(row.get("claim"))
        for row in rumours_config().get("rumours", []) or []
        if set(row.get("source_types", [])) & {"press", "journalist"}
    ]
    news_titles = [str(row["title"]) for row in load_news(limit=100).to_dicts()]
    from fitba.ingest.forum import score_text

    press_values = [score_text(text)["compound"] for text in press_claims if text]
    club_values = [score_text(text)["compound"] for text in news_titles if text]
    return {
        "forum": summarize_sentiment(forum_values),
        "press": summarize_sentiment(press_values),
        "club": summarize_sentiment(club_values),
        "note": (
            "Rule-based VADER sentiment on sampled forum posts, curated press "
            "rumour claims and official AFC news titles. Descriptive and noisy; "
            "not a measure of truth, credibility or fanbase opinion."
        ),
    }


def forum_payload(player_index: PlayerLinkIndex, generated_at: str | None = None) -> dict[str, Any]:
    topics = load_forum_topics()
    signals = load_forum_signals()
    posts = load_forum_posts()
    source = source_registry()["sources"].get("afc_chat", {})
    signal_rows = signals.to_dicts() if signals.height else []
    topic_rows = topics.to_dicts() if topics.height else []
    generated = None
    if topic_rows:
        generated = max(str(row.get("ingested_at") or "") for row in topic_rows) or None
    return {
        "source": {
            "id": "afc_chat",
            "name": source.get("name", "AFC Chat — The Rumour Mill"),
            "url": source.get("url"),
            "rss": source.get("rss"),
            "content_signal": source.get("content_signal"),
        },
        "generated_at": generated_at or utc_now_iso(),
        "sampled_at": generated,
        "coverage": {
            "topics_sampled": len(topic_rows),
            "posts_sampled": posts.height,
            "first_page_only": True,
            "raw_posts_published": False,
            "note": (
                "Sampled first pages of recent Rumour Mill topics. This is not "
                "the whole thread, the whole forum or the fanbase. No raw post "
                "bodies, usernames or quotes are published, and the text is not "
                "used for AI training."
            ),
        },
        "topics": [
            {
                "title": row.get("title"),
                "url": row.get("url"),
                "published_at": row.get("published_at"),
                "latest_post": row.get("latest_post"),
                "sampled_posts": row.get("sampled_posts"),
                "player_mentions": player_index.mentions(row.get("title")),
            }
            for row in topic_rows
        ],
        "signals": [
            {
                "player_name": row.get("player_name"),
                "player_key": row.get("player_key"),
                "position": row.get("position"),
                "position_group": row.get("position_group"),
                "nationality": row.get("nationality"),
                "age": row.get("age"),
                "mentions": row.get("mentions"),
                "topic_count": row.get("topic_count"),
                "credibility": row.get("credibility"),
                "player_href": player_index.href(row.get("player_key")),
                "cross_references": {
                    "confirmed_transfer": row.get("cross_confirmed"),
                    "historic_transfer": row.get("cross_historic"),
                    "press_rumour": row.get("cross_press"),
                    "club_output": row.get("cross_club"),
                },
            }
            for row in signal_rows
        ],
        "profile": build_profile(signal_rows),
        "sentiment": _forum_sentiment(),
        "notes": (
            "A mention count is not a transfer link. A cross-reference label "
            "records whether the same name also appears in the press rumour "
            "register, the club's output or the confirmed register; it is not a "
            "probability."
        ),
    }


__all__ = [
    "forum_payload",
    "load_rumour_rows",
    "profile_payload",
    "rumours_payload",
]
