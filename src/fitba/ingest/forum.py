"""Derive fan signal from AFC Chat's Rumour Mill first pages.

Raw post text stays in the gitignored normalized store and is never published.
The published layer contains topic metadata, player mention counts,
cross-reference labels and aggregate sentiment only.

Rules:
- sampled first pages, not full threads;
- no usernames, quotes or post bodies in any published payload;
- rule-based VADER sentiment, described as descriptive and noisy, not truth;
- a cross-reference label records source coverage, not a probability.
"""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import polars as pl
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from fitba.analytics.affiliation import AffiliationIndex
from fitba.analytics.former_players import former_player_rows
from fitba.ingest.cache import cache_path
from fitba.ingest.news import load_news
from fitba.ingest.transfers import published_transfers
from fitba.normalize.players import normalize_player_name
from fitba.normalize.positions import position_group
from fitba.settings import (
    NORMALIZED_DIR,
    ensure_dirs,
)
from fitba.settings import (
    players as players_config,
)
from fitba.settings import (
    rumours as rumours_config,
)
from fitba.sources import afc_chat, api_football
from fitba.sources.base import IngestResult
from fitba.util.dates import current_season, utc_now_iso

POST_COLUMNS = [
    "post_key",
    "topic_id",
    "posted_at",
    "text",
    "word_count",
    "compound",
    "positive",
    "neutral",
    "negative",
    "ingested_at",
]
TOPIC_COLUMNS = [
    "topic_id",
    "title",
    "url",
    "published_at",
    "sampled_posts",
    "latest_post",
    "ingested_at",
]
SIGNAL_COLUMNS = [
    "player_name",
    "player_key",
    "position",
    "position_group",
    "nationality",
    "age",
    "mentions",
    "topics",
    "topic_count",
    "sentiment_count",
    "sentiment_mean",
    "sentiment_median",
    "positive_share",
    "neutral_share",
    "negative_share",
    "credibility",
    "affiliation",
    "affiliation_source",
    "cross_confirmed",
    "cross_historic",
    "cross_press",
    "cross_club",
    "ingested_at",
]

CAP_SEQ_RE = re.compile(r"\b([A-Z][a-zA-Z'\u2019\-]+(?:\s+[A-Z][a-zA-Z'\u2019\-]+){0,3})\b")
# Capitalised phrases that are not player names.
STOP_PHRASES = {
    "transfer window",
    "deadline day",
    "january window",
    "summer window",
    "premier league",
    "scottish cup",
    "league cup",
    "premiership",
    "championship",
    "league one",
    "league two",
    "pittodrie",
    "aberdeen",
    "aberdeen fc",
    "the dons",
    "dons",
    "celtic",
    "rangers",
    "hibernian",
    "hearts",
    "motherwell",
    "dundee",
    "dundee united",
    "st mirren",
    "kilmarnock",
    "falkirk",
    "livingston",
    "ross county",
    "st johnstone",
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "i",
}
# Single tokens that are far more often ordinary words than surnames.
STOP_SURNAMES = {
    "young",
    "long",
    "small",
    "little",
    "brown",
    "black",
    "white",
    "gray",
    "grey",
    "green",
    "wood",
    "hill",
    "miller",
    "baker",
    "fisher",
    "hunter",
    "walker",
    "porter",
    "page",
    "hall",
    "march",
    "may",
    "read",
    "rose",
    "short",
    "best",
    "king",
    "price",
    "power",
    "law",
    "hope",
    "dick",
    "moore",
}
# First tokens that are never a player's first name in this context.
NON_NAME_FIRST = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "if",
    "by",
    "for",
    "from",
    "with",
    "more",
    "less",
    "right",
    "left",
    "centre",
    "central",
    "jan",
    "feb",
    "mar",
    "apr",
    "jun",
    "jul",
    "aug",
    "sep",
    "sept",
    "oct",
    "nov",
    "dec",
    "lutz",
    "get",
    "sack",
    "sign",
    "loan",
    "best",
    "worse",
    "same",
    "next",
    "last",
    "new",
    "old",
    "our",
    "their",
    "his",
    "her",
    "this",
    "that",
    "these",
    "those",
}
ANALYZER = SentimentIntensityAnalyzer()
SEARCH_CACHE = cache_path("afc_chat", "player_search.json")


@dataclass(slots=True)
class GazetteerEntry:
    name: str
    player_key: str | None = None
    position: str | None = None
    nationality: str | None = None
    age: int | None = None
    source: str = "local"

    @property
    def norm(self) -> str:
        return normalize_player_name(self.name)

    @property
    def surname(self) -> str:
        tokens = self.norm.split()
        return tokens[-1] if tokens else ""


@dataclass(slots=True)
class Gazetteer:
    by_full: dict[str, GazetteerEntry] = field(default_factory=dict)
    by_surname: dict[str, list[GazetteerEntry]] = field(default_factory=dict)

    def add(self, entry: GazetteerEntry) -> None:
        if not entry.norm:
            return

        def merge(target: GazetteerEntry) -> None:
            for attribute in ("position", "nationality", "age"):
                if getattr(target, attribute) is None and getattr(entry, attribute) is not None:
                    setattr(target, attribute, getattr(entry, attribute))

        existing = self.by_full.get(entry.norm)
        if existing is not None:
            merge(existing)
            return
        self.by_full[entry.norm] = entry
        surname = entry.surname
        if surname:
            bucket = self.by_surname.setdefault(surname, [])
            for candidate in bucket:
                if entry.player_key and candidate.player_key == entry.player_key:
                    merge(candidate)
                    return
            bucket.append(entry)

    def match_full(self, value: str) -> GazetteerEntry | None:
        return self.by_full.get(normalize_player_name(value))

    def match_surname(self, value: str) -> GazetteerEntry | None:
        bucket = self.by_surname.get(normalize_player_name(value), [])
        # Only an unambiguous surname is accepted for single-token matching.
        return bucket[0] if len(bucket) == 1 else None


def score_text(text: str) -> dict[str, float]:
    scores = ANALYZER.polarity_scores(text)
    return {
        "compound": float(scores["compound"]),
        "positive": float(scores["pos"]),
        "neutral": float(scores["neu"]),
        "negative": float(scores["neg"]),
    }


def _label(compound: float) -> str:
    if compound >= 0.05:
        return "positive"
    if compound <= -0.05:
        return "negative"
    return "neutral"


def summarize_sentiment(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "positive_share": None,
            "neutral_share": None,
            "negative_share": None,
        }
    labels = [_label(value) for value in values]
    return {
        "count": len(values),
        "mean": round(statistics.fmean(values), 3),
        "median": round(statistics.median(values), 3),
        "positive_share": round(labels.count("positive") / len(labels), 3),
        "neutral_share": round(labels.count("neutral") / len(labels), 3),
        "negative_share": round(labels.count("negative") / len(labels), 3),
    }


def _load_search_cache() -> dict[str, Any]:
    if not SEARCH_CACHE.exists():
        return {}
    try:
        return json.loads(SEARCH_CACHE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_search_cache(payload: dict[str, Any]) -> None:
    SEARCH_CACHE.parent.mkdir(parents=True, exist_ok=True)
    SEARCH_CACHE.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


SCOTTISH_LEAGUE_IDS = (179, 180, 183, 184)


def _search_player(phrase: str, cache: dict[str, Any]) -> dict[str, Any] | None:
    """Validate a capitalised name against Scottish league squads.

    The catalogue search is by surname. A candidate is accepted when the
    surname matches and, where the API returns an initial, the initial matches
    the phrase. Ambiguous surnames are rejected rather than guessed.
    """
    key = phrase.casefold()
    if key in cache:
        return cache[key]

    tokens = phrase.split()
    if len(tokens) != 2:
        return None
    first_initial = tokens[0][0].casefold()
    surname = normalize_player_name(tokens[-1])
    if not surname.isalpha() or len(surname) < 3:
        return None

    matches: list[dict[str, Any]] = []
    failures = 0
    for league_id in SCOTTISH_LEAGUE_IDS:
        try:
            results = api_football.players_search(surname, league_id=league_id)
        except Exception:  # noqa: BLE001 - enrichment is optional
            failures += 1
            continue
        for item in results:
            player = item.get("player") or {}
            found = str(player.get("name") or "")
            parts = found.split()
            if not parts or normalize_player_name(parts[-1]) != surname:
                continue
            if len(parts) > 1 and parts[0] and parts[0][0].casefold() != first_initial:
                continue
            position = None
            for statistic in item.get("statistics", []):
                position = (statistic.get("games") or {}).get("position") or position
                if position:
                    break
            matches.append(
                {
                    "player_key": f"api:player:{player.get('id')}",
                    "name": found,
                    "age": player.get("age"),
                    "nationality": player.get("nationality"),
                    "position": position,
                }
            )

    if failures == len(SCOTTISH_LEAGUE_IDS):
        # Do not cache a transient API failure as a negative match.
        return None
    chosen = matches[0] if len(matches) == 1 else None
    cache[key] = chosen
    return chosen


def build_gazetteer(
    *,
    enrich: bool = True,
    candidates: list[str] | None = None,
) -> Gazetteer:
    """Build the player gazetteer from local sources plus the Aberdeen squad.

    ``candidates`` are unmatched capitalised bigrams from the sampled posts.
    They are validated one by one against API-Football, capped, and cached; this
    is a name check, not a bulk roster download.
    """
    gazetteer = Gazetteer()

    # The current squad goes in first so surname matches carry position and age
    # even when the transfer register only has an abbreviated name.
    try:
        for item in api_football.players_squads(252):
            for player in item.get("players", []):
                gazetteer.add(
                    GazetteerEntry(
                        name=str(player.get("name") or ""),
                        player_key=f"api:player:{player.get('id')}",
                        position=player.get("position"),
                        age=player.get("age"),
                        source="aberdeen_squad",
                    )
                )
    except Exception:  # noqa: BLE001 - the forum layer must not depend on the API
        pass

    for row in rumours_config().get("rumours", []):
        if row.get("player_name"):
            gazetteer.add(
                GazetteerEntry(
                    name=str(row["player_name"]),
                    player_key=row.get("player_key") or row.get("linked_player_key"),
                    position=row.get("position"),
                    age=row.get("age"),
                    source="rumour_register",
                )
            )

    for row in players_config().get("players", []):
        if row.get("name"):
            gazetteer.add(
                GazetteerEntry(
                    name=str(row["name"]),
                    player_key=row.get("player_key"),
                    position=row.get("position"),
                    nationality=row.get("nationality"),
                    age=row.get("age"),
                    source="curated_player",
                )
            )

    for row in published_transfers():
        if row.get("player_name"):
            gazetteer.add(
                GazetteerEntry(
                    name=str(row["player_name"]),
                    player_key=row.get("player_key"),
                    position=row.get("position"),
                    nationality=row.get("nationality"),
                    source="transfer_register",
                )
            )

    if enrich and candidates:
        cache = _load_search_cache()
        for name in candidates[:20]:
            found = _search_player(name, cache)
            if found:
                gazetteer.add(
                    GazetteerEntry(
                        name=name,
                        player_key=found.get("player_key"),
                        position=found.get("position"),
                        nationality=found.get("nationality"),
                        age=found.get("age"),
                        source="api_name_check",
                    )
                )
        _save_search_cache(cache)

    return gazetteer


def plausible_name(phrase: str) -> bool:
    """A cheap filter before spending an API name check on a phrase."""
    if normalize_player_name(phrase) in STOP_PHRASES:
        return False
    tokens = phrase.split()
    if len(tokens) != 2:
        return False
    first, last = tokens
    if first.casefold() in NON_NAME_FIRST:
        return False
    if not first.isalpha() or not last.isalpha():
        return False
    return not (last.endswith("'s") or len(last) < 3)


def capitalised_bigrams(text: str) -> list[str]:
    """Return capitalised multi-word phrases that look like personal names."""
    found: list[str] = []
    for match in CAP_SEQ_RE.finditer(text):
        tokens = match.group(1).split()
        if len(tokens) < 2:
            continue
        phrase = " ".join(tokens)
        if normalize_player_name(phrase) in STOP_PHRASES:
            continue
        found.append(phrase)
    return found


def extract_mentions(text: str, gazetteer: Gazetteer) -> list[GazetteerEntry]:
    """Extract gazetteer players from a post.

    Full names match anywhere. A surname-only mention is accepted when the
    surname is unique in the gazetteer, is at least four characters, is not on
    the ambiguous-surname list, and is not the first word of the sentence.
    """
    mentions: dict[str, GazetteerEntry] = {}
    consumed: list[tuple[int, int]] = []

    for match in CAP_SEQ_RE.finditer(text):
        tokens = match.group(1).split()
        if " ".join(tokens).casefold() in STOP_PHRASES:
            continue
        matched_span: tuple[int, int] | None = None
        for size in range(len(tokens), 1, -1):
            for start in range(0, len(tokens) - size + 1):
                phrase = " ".join(tokens[start : start + size])
                entry = gazetteer.match_full(phrase)
                if entry is not None:
                    mentions.setdefault(entry.norm, entry)
                    matched_span = (match.start(), match.end())
                    break
            if matched_span:
                break
        if matched_span:
            consumed.append(matched_span)

    for match in CAP_SEQ_RE.finditer(text):
        if any(start <= match.start() < end for start, end in consumed):
            continue
        tokens = match.group(1).split()
        for index, token in enumerate(tokens):
            if len(token) < 4:
                continue
            norm = normalize_player_name(token)
            if norm in STOP_SURNAMES:
                continue
            entry = gazetteer.match_surname(token)
            if entry is None:
                continue
            sentence_start = match.start() == 0 or text[match.start() - 1] in ".!?\"'"
            if sentence_start and index == 0 and len(tokens) == 1:
                continue
            mentions.setdefault(entry.norm, entry)

    return list(mentions.values())


RECENT_TRANSFER_DAYS = 550


def _same_player(name: Any, entry: GazetteerEntry) -> bool:
    normalized = normalize_player_name(str(name or ""))
    if not normalized:
        return False
    return normalized == entry.norm or normalized.split()[-1] == entry.surname


def _is_recent(value: Any) -> bool:
    try:
        moved = datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return False
    return (datetime.now(UTC).date() - moved).days <= RECENT_TRANSFER_DAYS


def _cross_reference(
    entry: GazetteerEntry,
    *,
    transfers: list[dict[str, Any]],
    rumours: list[dict[str, Any]],
    news_titles: list[str],
) -> dict[str, Any]:
    surname = entry.surname

    matching_transfers = [row for row in transfers if _same_player(row.get("player_name"), entry)]
    confirmed = any(_is_recent(row.get("date_effective")) for row in matching_transfers)
    historic = bool(matching_transfers) and not confirmed
    press_rumours = [
        row for row in rumours if set(row.get("source_types", [])) & {"press", "journalist"}
    ]
    press = any(_same_player(row.get("player_name"), entry) for row in press_rumours)
    confirmed_rumour = any(
        row.get("status") == "confirmed" and _same_player(row.get("player_name"), entry)
        for row in rumours
    )
    club = any(
        surname and re.search(rf"\b{re.escape(surname)}\b", title, re.IGNORECASE)
        for title in news_titles
    )

    if press:
        credibility = "cross_referenced_press"
    elif confirmed_rumour:
        credibility = "official_confirmed"
    elif entry.source == "aberdeen_squad":
        credibility = "club_player"
    elif confirmed:
        credibility = "cross_referenced_transfer"
    elif club:
        credibility = "cross_referenced_club"
    else:
        credibility = "fan_only"

    return {
        "credibility": credibility,
        "cross_references": {
            "confirmed_transfer": confirmed,
            "historic_transfer": historic,
            "press_rumour": press,
            "club_output": club,
        },
    }


def _age_band(age: int | None) -> str | None:
    if age is None:
        return None
    if age < 21:
        return "under-21"
    if age < 24:
        return "21-23"
    if age < 27:
        return "24-26"
    if age < 30:
        return "27-29"
    return "30-plus"


def build_signals(
    posts: pl.DataFrame,
    gazetteer: Gazetteer,
    *,
    transfers: list[dict[str, Any]],
    rumours: list[dict[str, Any]],
    news_titles: list[str],
    affiliations: AffiliationIndex | None = None,
) -> list[dict[str, Any]]:
    signals: dict[str, dict[str, Any]] = {}
    for row in posts.to_dicts():
        text = str(row.get("text") or "")
        if not text:
            continue
        for entry in extract_mentions(text, gazetteer):
            signal = signals.setdefault(
                entry.norm,
                {
                    "player_name": entry.name,
                    "player_key": entry.player_key,
                    "position": entry.position,
                    "position_group": position_group(entry.position),
                    "nationality": entry.nationality,
                    "age": entry.age,
                    "gazetteer_source": entry.source,
                    "mentions": 0,
                    "topics": set(),
                    "compounds": [],
                },
            )
            signal["mentions"] += 1
            signal["topics"].add(str(row.get("topic_id")))
            signal["compounds"].append(float(row.get("compound") or 0.0))

    output = []
    for signal in signals.values():
        reference = _cross_reference(
            GazetteerEntry(
                name=signal["player_name"],
                source=signal.get("gazetteer_source", "local"),
            ),
            transfers=transfers,
            rumours=rumours,
            news_titles=news_titles,
        )
        signal.pop("gazetteer_source", None)
        compounds = signal.pop("compounds")
        topics = sorted(signal.pop("topics"))
        signal["topics"] = topics
        signal["topic_count"] = len(topics)
        signal["sentiment"] = summarize_sentiment(compounds)
        signal.update(reference)
        if affiliations is not None:
            affiliation, affiliation_source = affiliations.affiliation_for(
                signal.get("player_key"), signal.get("player_name")
            )
        else:
            affiliation, affiliation_source = "unknown", "none"
        signal["affiliation"] = affiliation
        signal["affiliation_source"] = affiliation_source
        output.append(signal)
    return sorted(output, key=lambda row: (-row["mentions"], row["player_name"]))


def build_profile(signals: list[dict[str, Any]]) -> dict[str, Any]:
    """A descriptive profile of external names, separate from Aberdeen players."""
    external = [
        signal
        for signal in signals
        if str(signal.get("affiliation") or "unknown") == "external_target"
    ]
    positions: dict[str, int] = {}
    ages: dict[str, int] = {}
    sources: dict[str, int] = {}
    affiliation_mix: dict[str, int] = {}
    for signal in signals:
        affiliation = str(signal.get("affiliation") or "unknown")
        affiliation_mix[affiliation] = affiliation_mix.get(affiliation, 0) + 1
        sources[signal["credibility"]] = sources.get(signal["credibility"], 0) + 1
    for signal in external:
        if signal.get("position_group"):
            positions[signal["position_group"]] = positions.get(signal["position_group"], 0) + 1
        band = _age_band(signal.get("age"))
        if band:
            ages[band] = ages.get(band, 0) + 1
    former = [signal for signal in signals if signal.get("affiliation") == "former_player"]
    return {
        "sample_size": len(external),
        "total_signals": len(signals),
        "external_sample_size": len(external),
        "position_mix": positions,
        "age_mix": ages,
        "source_mix": sources,
        "affiliation_mix": dict(sorted(affiliation_mix.items())),
        "excluded_counts": {
            key: value for key, value in sorted(affiliation_mix.items()) if key != "external_target"
        },
        "lanes": {
            key: {
                "count": value,
                "players": sorted(
                    str(signal.get("player_name"))
                    for signal in signals
                    if str(signal.get("affiliation") or "unknown") == key
                ),
            }
            for key, value in sorted(affiliation_mix.items())
        },
        "former_player_profile": {
            "sample_size": len(former),
            "mentions": sum(int(signal.get("mentions") or 0) for signal in former),
            "players": sorted(str(signal.get("player_name")) for signal in former),
        },
        "low_confidence": len(external) < 5,
        "note": (
            "The position and age mixes count external names only, not current squad "
            "or former players. This is still a descriptive profile of sampled first "
            "pages, not the club's recruitment list."
        ),
    }


def signal_frame(signals: list[dict[str, Any]], now: str) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    for signal in signals:
        sentiment = signal.get("sentiment") or {}
        refs = signal.get("cross_references") or {}
        rows.append(
            {
                "player_name": signal.get("player_name"),
                "player_key": signal.get("player_key"),
                "position": signal.get("position"),
                "position_group": signal.get("position_group"),
                "nationality": signal.get("nationality"),
                "age": signal.get("age"),
                "mentions": int(signal.get("mentions") or 0),
                "topics": list(signal.get("topics") or []),
                "topic_count": int(signal.get("topic_count") or 0),
                "sentiment_count": sentiment.get("count"),
                "sentiment_mean": sentiment.get("mean"),
                "sentiment_median": sentiment.get("median"),
                "positive_share": sentiment.get("positive_share"),
                "neutral_share": sentiment.get("neutral_share"),
                "negative_share": sentiment.get("negative_share"),
                "credibility": signal.get("credibility"),
                "affiliation": signal.get("affiliation"),
                "affiliation_source": signal.get("affiliation_source"),
                "cross_confirmed": bool(refs.get("confirmed_transfer")),
                "cross_historic": bool(refs.get("historic_transfer")),
                "cross_press": bool(refs.get("press_rumour")),
                "cross_club": bool(refs.get("club_output")),
                "ingested_at": now,
            }
        )
    if not rows:
        return pl.DataFrame({column: [] for column in SIGNAL_COLUMNS})
    return pl.DataFrame(rows).select(SIGNAL_COLUMNS)


def _topic_frame(topics: list[dict[str, Any]], now: str) -> pl.DataFrame:
    rows = [
        {
            "topic_id": str(topic.get("topic_id")),
            "title": str(topic.get("title") or ""),
            "url": str(topic.get("url") or ""),
            "published_at": topic.get("published_at"),
            "sampled_posts": int(topic.get("sampled_posts") or 0),
            "latest_post": topic.get("latest_post"),
            "ingested_at": now,
        }
        for topic in topics
    ]
    if not rows:
        return pl.DataFrame({column: [] for column in TOPIC_COLUMNS})
    return pl.DataFrame(rows).select(TOPIC_COLUMNS)


def ingest_forum(
    *,
    limit: int = 8,
    days: int = 365,
    enrich: bool = True,
    force: bool = False,
) -> IngestResult:
    ensure_dirs()
    try:
        topics, posts = afc_chat.sample_topics(limit=limit, days=days, force=force)
        now = utc_now_iso()
        post_rows: list[dict[str, Any]] = []
        candidate_bigrams: dict[str, int] = {}
        for post in posts:
            text = str(post.get("text") or "")
            if not text:
                continue
            scores = score_text(text)
            post_rows.append(
                {
                    "post_key": afc_chat.post_key(
                        str(post.get("topic_id")), str(post.get("comment_id"))
                    ),
                    "topic_id": str(post.get("topic_id")),
                    "posted_at": post.get("posted_at"),
                    "text": text,
                    "word_count": len(text.split()),
                    "ingested_at": now,
                    **scores,
                }
            )
            for phrase in capitalised_bigrams(text):
                candidate_bigrams[phrase] = candidate_bigrams.get(phrase, 0) + 1

        repeated = [
            phrase
            for phrase, count in candidate_bigrams.items()
            if count >= 1 and plausible_name(phrase)
        ]
        gazetteer = build_gazetteer(enrich=enrich, candidates=repeated)

        posts_frame = (
            pl.DataFrame(post_rows).select(POST_COLUMNS)
            if post_rows
            else pl.DataFrame({column: [] for column in POST_COLUMNS})
        )
        topics_frame = _topic_frame(topics, now)

        output_dir = NORMALIZED_DIR / "forum"
        output_dir.mkdir(parents=True, exist_ok=True)
        posts_frame.write_parquet(output_dir / "afc_chat_posts.parquet")
        topics_frame.write_parquet(output_dir / "afc_chat_topics.parquet")

        from fitba.publish.squad import squad_payload

        transfers = published_transfers()
        squad = squad_payload(current_season())
        former = former_player_rows(transfers, squad)
        affiliations = AffiliationIndex.from_payloads(
            squad=squad,
            former_keys={str(row["player_key"]) for row in former},
        )
        signals = build_signals(
            posts_frame,
            gazetteer,
            transfers=transfers,
            rumours=list(rumours_config().get("rumours", [])),
            news_titles=[str(row["title"]) for row in load_news(limit=50).to_dicts()],
            affiliations=affiliations,
        )
        signal_frame(signals, now).write_parquet(output_dir / "afc_chat_signals.parquet")

        return IngestResult(
            source="afc_chat",
            status="ok",
            rows=posts_frame.height,
            path=str(output_dir / "afc_chat_posts.parquet"),
            details={
                "topics_sampled": len(topics),
                "posts_sampled": posts_frame.height,
                "gazetteer_size": len(gazetteer.by_full),
                "signals": len(signals),
                "name_checks": len(repeated),
                "sentiment": summarize_sentiment([float(row["compound"]) for row in post_rows]),
            },
        )
    except Exception as exc:  # noqa: BLE001 - reported by the CLI
        return IngestResult(source="afc_chat", status="error", errors=[str(exc)])


def load_forum_topics() -> pl.DataFrame:
    path = NORMALIZED_DIR / "forum" / "afc_chat_topics.parquet"
    if not path.exists():
        return pl.DataFrame({column: [] for column in TOPIC_COLUMNS})
    return pl.read_parquet(path)


def load_forum_posts() -> pl.DataFrame:
    path = NORMALIZED_DIR / "forum" / "afc_chat_posts.parquet"
    if not path.exists():
        return pl.DataFrame({column: [] for column in POST_COLUMNS})
    return pl.read_parquet(path)


def load_forum_signals() -> pl.DataFrame:
    path = NORMALIZED_DIR / "forum" / "afc_chat_signals.parquet"
    if not path.exists():
        return pl.DataFrame({column: [] for column in SIGNAL_COLUMNS})
    return pl.read_parquet(path)


__all__ = [
    "Gazetteer",
    "GazetteerEntry",
    "build_gazetteer",
    "build_profile",
    "build_signals",
    "capitalised_bigrams",
    "extract_mentions",
    "ingest_forum",
    "load_forum_posts",
    "load_forum_topics",
    "score_text",
    "summarize_sentiment",
]
