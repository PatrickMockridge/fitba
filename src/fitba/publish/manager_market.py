"""Next-manager market payload.

The market is a narrow, gated exception to the no-betting rule: a single
curated public bookmaker-odds snapshot is published only while the staff
register has an interim manager and no permanent manager. It is intelligence,
not advice, a recommendation or a promotion. No affiliate or sign-up links.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from fitba.analytics.manager_market import (
    fractional_decimal,
    implied_probability,
    manager_vacancy,
)
from fitba.ingest.forum import load_donstalk_manager_mentions
from fitba.settings import (
    history_staff,
    manager_market,
    manager_market_policy,
)

SCHEMA_VERSION = "1.0.0"
STATE = Literal["open", "closed", "unavailable"]

AFFILIATE_TOKENS = (
    "affiliate",
    "aff_id",
    "affid",
    "utm_",
    "clickid",
    "gclid",
    "promo",
    "signup",
    "sign_up",
    "register",
    "oddschecker",
    "bet=",
)
CTA_KEYS = {"bet_url", "signup_url", "affiliate_url", "bet_link", "promo_code"}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class OddsQuote(StrictModel):
    fractional: str
    decimal: float
    implied_probability: float


class Mentions(StrictModel):
    count: int
    topic_count: int
    sources: list[dict[str, Any]] = Field(default_factory=list)
    first_seen: str | None = None
    last_seen: str | None = None


class Candidate(StrictModel):
    candidate_id: str
    name: str
    current_role: str | None = None
    current_club: str | None = None
    status: str
    odds: OddsQuote | None = None
    mentions: Mentions | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)


class Gate(StrictModel):
    is_open: bool
    state: STATE
    permanent_manager: str | None = None
    permanent_manager_start: str | None = None
    interim_manager: str | None = None
    interim_since: str | None = None
    vacancy_started: str | None = None
    checked_at: str | None = None
    reason: str | None = None


class Freshness(StrictModel):
    age_hours: float | None = None
    stale: bool = False
    max_age_hours: int = 48


class Coverage(StrictModel):
    status: str
    candidate_count: int = 0
    priced_count: int = 0
    mentioned_count: int = 0
    field_complete: bool = False
    overround: float | None = None
    note: str


class Market(StrictModel):
    id: str
    label: str
    state: STATE
    gate: Gate
    observed_at: str | None = None
    bookmaker: str | None = None
    publisher: str | None = None
    source_urls: list[str] = Field(default_factory=list)
    freshness: Freshness = Field(default_factory=Freshness)
    coverage: Coverage


class ManagerMarketDocument(StrictModel):
    schema_version: str = SCHEMA_VERSION
    generated_at: str
    season: str
    club_id: str = "sco:aberdeen"
    market: Market
    candidates: list[Candidate] = Field(default_factory=list)
    disclaimer: str
    notes: str


def manager_market_schema() -> dict[str, Any]:
    return ManagerMarketDocument.model_json_schema()


def _age_hours(observed_at: str | None, generated_at: str) -> float | None:
    if not observed_at:
        return None
    try:
        observed = datetime.fromisoformat(str(observed_at).replace("Z", "+00:00"))
        generated = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=UTC)
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=UTC)
    return round((generated - observed).total_seconds() / 3600, 1)


def _check_url(value: str | None) -> None:
    if not value:
        return
    lowered = value.casefold()
    if any(token in lowered for token in AFFILIATE_TOKENS):
        raise ValueError(f"affiliate/tracking URL is not allowed: {value}")


def _candidate_rows(
    *,
    market_config: dict[str, Any],
    mentions_rows: list[dict[str, Any]],
    withheld: bool,
    observed_at: str | None,
) -> list[Candidate]:
    snapshot = market_config.get("snapshot") or {}
    source = {
        "id": snapshot.get("source_id") or "manager_market",
        "url": snapshot.get("source_url"),
        "observed_at": observed_at,
    }
    mentions_by_id = {
        str(row.get("candidate_id")): row for row in mentions_rows if row.get("candidate_id")
    }
    rows: list[Candidate] = []
    for candidate in market_config.get("candidates") or []:
        candidate_id = str(candidate.get("candidate_id") or candidate.get("id") or "")
        if not candidate_id:
            continue
        fractional = candidate.get("odds_fractional")
        decimal = fractional_decimal(fractional) if fractional else None
        if fractional and decimal is None:
            raise ValueError(f"invalid fractional odds for {candidate_id}: {fractional}")
        mention = mentions_by_id.get(candidate_id)
        mention_row = mention or {}
        mention_count = int(mention_row.get("mentions") or 0)
        if not decimal and not mention_count:
            continue
        published_odds = None
        if decimal is not None and not withheld:
            published_odds = OddsQuote(
                fractional=str(fractional),
                decimal=decimal,
                implied_probability=float(implied_probability(decimal) or 0),
            )
        mention_block = None
        if mention_count:
            mention_block = Mentions(
                count=mention_count,
                topic_count=int(mention_row.get("topic_count") or 0),
                sources=[{"id": "donstalk", "count": mention_count}],
                first_seen=mention_row.get("first_seen"),
                last_seen=mention_row.get("last_seen"),
            )
        status = (
            "priced_and_mentioned"
            if published_odds and mention_block
            else "priced"
            if published_odds
            else "mentioned"
        )
        rows.append(
            Candidate(
                candidate_id=candidate_id,
                name=str(candidate.get("name") or candidate_id),
                current_role=candidate.get("current_role"),
                current_club=candidate.get("current_club"),
                status=status,
                odds=published_odds,
                mentions=mention_block,
                sources=[source] if published_odds else [],
            )
        )
    rows.sort(
        key=lambda row: (
            row.odds.decimal if row.odds else 9999,
            -(row.mentions.count if row.mentions else 0),
            row.name,
        )
    )
    return rows


def manager_market_payload(
    *,
    season: str,
    generated_at: str,
    staff: dict[str, Any] | None = None,
    market_config: dict[str, Any] | None = None,
    mentions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    staff = staff if staff is not None else history_staff()
    config = market_config if market_config is not None else manager_market()
    if mentions is None:
        mentions = load_donstalk_manager_mentions().to_dicts()
    policy = manager_market_policy()
    gate = manager_vacancy(staff, checked_at=generated_at)
    label = str((policy.get("policy") or {}).get("label") or "Next Aberdeen manager")
    state = str(gate.get("state") or "unavailable")
    disclaimer = str((policy.get("policy") or {}).get("disclaimer") or "").strip()
    snapshot = config.get("snapshot") or {}
    observed_at = snapshot.get("observed_at")
    freshness_config = policy.get("freshness") or {}
    stale_after = int(freshness_config.get("stale_after_hours") or 48)
    withhold_after = int(freshness_config.get("withhold_after_hours") or 168)
    age = _age_hours(observed_at, generated_at)
    stale = age is not None and age > stale_after
    withheld = age is None or age > withhold_after
    source_url = snapshot.get("source_url")
    _check_url(source_url)
    for candidate in config.get("candidates") or []:
        _check_url(candidate.get("source_url"))
        if set(candidate) & CTA_KEYS:
            raise ValueError("betting call-to-action fields are not allowed")

    if state != "open":
        coverage_status = "closed" if state == "closed" else "unavailable"
        note = (
            "No odds are published while a permanent manager is in post."
            if state == "closed"
            else "The staff register is not a valid vacancy; no odds are published."
        )
        document = ManagerMarketDocument(
            generated_at=generated_at,
            season=season,
            market=Market(
                id="next-manager",
                label=label,
                state=state,  # type: ignore[arg-type]
                gate=Gate(**gate),
                observed_at=None,
                bookmaker=None,
                publisher=None,
                source_urls=[],
                freshness=Freshness(age_hours=None, stale=False, max_age_hours=stale_after),
                coverage=Coverage(status=coverage_status, note=note),
            ),
            candidates=[],
            disclaimer=disclaimer,
            notes=note,
        )
        return document.model_dump()

    rows = _candidate_rows(
        market_config=config,
        mentions_rows=mentions or [],
        withheld=withheld,
        observed_at=str(observed_at) if observed_at else None,
    )
    priced = [row for row in rows if row.odds]
    mentioned = [row for row in rows if row.mentions]
    field_complete = bool(snapshot.get("field_complete"))
    overround = None
    if field_complete and priced and not withheld:
        total = sum(row.odds.implied_probability for row in priced if row.odds)
        overround = round(total - 1, 4)
    if withheld:
        coverage_status = "withheld"
        note = (
            "The odds snapshot is older than the freshness limit; prices are withheld. "
            "Mention-only candidates remain."
        )
    else:
        coverage_status = "available"
        note = (
            "Single public bookmaker-odds snapshot; raw implied prices are not a "
            "probability and do not sum to 100% unless the field is complete."
            if not field_complete
            else "Single public bookmaker-odds snapshot; overround is published."
        )
    document = ManagerMarketDocument(
        generated_at=generated_at,
        season=season,
        market=Market(
            id="next-manager",
            label=label,
            state="open",
            gate=Gate(**gate),
            observed_at=str(observed_at) if observed_at else None,
            bookmaker="Gambling.com bookmaker list" if not withheld else None,
            publisher=str(snapshot.get("publisher") or "") or None,
            source_urls=[str(source_url)] if source_url and not withheld else [],
            freshness=Freshness(
                age_hours=age,
                stale=stale,
                max_age_hours=stale_after,
            ),
            coverage=Coverage(
                status=coverage_status,
                candidate_count=len(rows),
                priced_count=len(priced),
                mentioned_count=len(mentioned),
                field_complete=field_complete,
                overround=overround,
                note=note,
            ),
        ),
        candidates=rows,
        disclaimer=disclaimer,
        notes=(
            "Published only while Aberdeen have no permanent manager; removed when "
            "a permanent manager is appointed. Not betting advice, a recommendation "
            "or a promotion. No affiliate or advertising relationship."
        ),
    )
    return document.model_dump()


__all__ = [
    "ManagerMarketDocument",
    "manager_market_payload",
    "manager_market_schema",
]
