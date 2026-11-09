"""Reconcile curated availability claims with match participation.

A curated injury or suspension claim is only current while the record does not
contradict it. This module compares each known claim with named matchday squads,
appearances and card-derived suspension service, and returns review flags. It
never turns a contradiction into "fit": a contradicted claim becomes
``unknown`` with its original claim, source and evidence preserved.

The pure functions have no fitba imports at module level. The evidence loader
lazily imports the ingest modules so callers can pass synthetic evidence in
tests without touching the local feeds.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

COMPETITIVE_COMPETITIONS = {"sco:premiership", "sco:league-cup", "sco:scottish-cup"}
KNOWN_STATUSES = {"out", "doubtful", "suspended", "returned", "available"}
CONTRADICTABLE_STATUSES = {"out", "doubtful", "suspended"}


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def status_age_days(verified_at: Any, today: date | None = None) -> int | None:
    verified = _as_date(verified_at)
    if verified is None:
        return None
    current = today or date.today()
    return max(0, (current - verified).days)


def fresh_until(verified_at: Any, fresh_days: int) -> str | None:
    verified = _as_date(verified_at)
    if verified is None:
        return None
    return _iso(verified + timedelta(days=max(0, int(fresh_days))))


def stale_after(verified_at: Any, max_age_days: int) -> str | None:
    verified = _as_date(verified_at)
    if verified is None:
        return None
    return _iso(verified + timedelta(days=max(0, int(max_age_days))))


def _fixture_map(schedule: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(row["fixture_id"]): row for row in schedule if row.get("fixture_id") is not None}


def _boundary(entry: dict[str, Any]) -> date | None:
    dates = [
        value
        for value in (
            _as_date(entry.get("verified_at")),
            _as_date(entry.get("effective_from")),
        )
        if value is not None
    ]
    return max(dates) if dates else None


def _participation_for(player_id: int, evidence: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in evidence.get("participation") or []
        if int(row.get("player_id") or 0) == player_id
        and str(row.get("competition_id") or "") in COMPETITIVE_COMPETITIONS
    ]
    return sorted(
        rows, key=lambda row: (str(row.get("date") or ""), int(row.get("fixture_id") or 0))
    )


def _contradicting_appearance(
    entry: dict[str, Any],
    evidence: dict[str, Any],
    boundary: date | None,
) -> dict[str, Any] | None:
    if boundary is None:
        return None
    player_id = int(entry.get("player_id") or 0)
    status = str(entry.get("status") or "unknown")
    for row in _participation_for(player_id, evidence):
        row_date = _as_date(row.get("date"))
        if row_date is None or row_date <= boundary:
            continue
        squad_status = str(row.get("squad_status") or "")
        if status == "out":
            if squad_status in {"starter", "sub_used"}:
                return row
            if squad_status == "sub_unused" and bool(row.get("bench_complete")):
                return row
        if status == "doubtful" and squad_status in {"starter", "sub_used"}:
            return row
    return None


def _red_card_for(
    entry: dict[str, Any],
    evidence: dict[str, Any],
    boundary: date | None,
) -> dict[str, Any] | None:
    player_id = int(entry.get("player_id") or 0)
    scope = str(entry.get("competition_id") or "")
    cards = [
        row
        for row in evidence.get("red_cards") or []
        if int(row.get("player_id") or 0) == player_id
        and (not scope or str(row.get("competition_id") or "") == scope)
    ]
    if boundary is not None:

        def _on_or_before(row: dict[str, Any]) -> bool:
            row_date = _as_date(row.get("date"))
            return row_date is not None and row_date <= boundary

        cards = [row for row in cards if _on_or_before(row)]
    if not cards:
        return None
    return max(cards, key=lambda row: str(row.get("date") or ""))


def suspension_state(
    entry: dict[str, Any],
    evidence: dict[str, Any],
    suspension_config: dict[str, Any],
) -> dict[str, Any]:
    boundary = _boundary(entry)
    red_config = suspension_config.get("red_cards") or {}
    categories = red_config.get("categories") or {}
    card = _red_card_for(entry, evidence, boundary)
    scope = str(entry.get("competition_id") or (card or {}).get("competition_id") or "")
    if card is None:
        return {
            "competition_id": scope or None,
            "card_fixture_id": None,
            "card_date": None,
            "red_type": None,
            "ban_matches": None,
            "state": "scope_unknown",
            "served_fixture_id": None,
            "served_date": None,
            "served_count": 0,
            "rule_verified": bool(red_config.get("verified")),
            "rule_source": red_config.get("source_url"),
        }
    red_type = str(card.get("red_type") or "other")
    ban_matches = int(categories.get(red_type, categories.get("other", 1)) or 1)
    card_date = _as_date(card.get("date"))
    same_competition = bool(red_config.get("same_competition", True))
    fixtures = []
    if card_date is not None:
        for row in evidence.get("schedule") or []:
            row_date = _as_date(row.get("date"))
            if row.get("status") != "played":
                continue
            if str(row.get("competition_id") or "") not in COMPETITIVE_COMPETITIONS:
                continue
            if row_date is None or row_date <= card_date:
                continue
            if same_competition and str(row.get("competition_id") or "") != scope:
                continue
            fixtures.append(row)
    fixtures.sort(key=lambda row: (str(row.get("date") or ""), int(row.get("fixture_id") or 0)))
    fixtures_by_id = {
        int(row["fixture_id"]): row for row in fixtures if row.get("fixture_id") is not None
    }
    participation = {
        int(row.get("fixture_id") or 0): row
        for row in _participation_for(int(entry.get("player_id") or 0), evidence)
    }
    served_count = 0
    served_fixture: dict[str, Any] | None = None
    incomplete_bench = False
    for fixture_id, fixture in fixtures_by_id.items():
        appearance = participation.get(fixture_id)
        if appearance is not None:
            return {
                "competition_id": scope,
                "card_fixture_id": card.get("fixture_id"),
                "card_date": _iso(card_date),
                "red_type": red_type,
                "ban_matches": ban_matches,
                "state": "not_applied",
                "served_fixture_id": None,
                "served_date": None,
                "served_count": served_count,
                "appearance_fixture_id": fixture_id,
                "appearance_date": fixture.get("date"),
                "appearance_squad_status": appearance.get("squad_status"),
                "rule_verified": bool(red_config.get("verified")),
                "rule_source": red_config.get("source_url"),
            }
        if not bool(fixture.get("bench_complete")):
            # An absence is only evidence of service when the bench is complete.
            incomplete_bench = True
            continue
        served_count += 1
        served_fixture = fixture
        if served_count >= ban_matches:
            return {
                "competition_id": scope,
                "card_fixture_id": card.get("fixture_id"),
                "card_date": _iso(card_date),
                "red_type": red_type,
                "ban_matches": ban_matches,
                "state": "served",
                "served_fixture_id": fixture_id,
                "served_date": fixture.get("date"),
                "served_count": served_count,
                "rule_verified": bool(red_config.get("verified")),
                "rule_source": red_config.get("source_url"),
            }
    if served_count < ban_matches and not incomplete_bench:
        state = "no_remaining_fixture"
    elif incomplete_bench:
        state = "unverified"
    else:
        state = "active"
    return {
        "competition_id": scope,
        "card_fixture_id": card.get("fixture_id"),
        "card_date": _iso(card_date),
        "red_type": red_type,
        "ban_matches": ban_matches,
        "state": state,
        "served_fixture_id": served_fixture.get("fixture_id") if served_fixture else None,
        "served_date": served_fixture.get("date") if served_fixture else None,
        "served_count": served_count,
        "rule_verified": bool(red_config.get("verified")),
        "rule_source": red_config.get("source_url"),
    }


def reconcile_entry(
    entry: dict[str, Any],
    evidence: dict[str, Any],
    policy: dict[str, Any],
    today: date | None = None,
) -> dict[str, Any]:
    """Return a copy of an availability entry with review flags applied."""
    current = today or date.today()
    result = dict(entry)
    original_status = str(entry.get("status") or "unknown")
    result["original_status"] = original_status
    if original_status not in KNOWN_STATUSES:
        result.setdefault("review_required", False)
        result.setdefault("review_reason", None)
        result.setdefault("review_reasons", [])
        result.setdefault("review_severity", None)
        result.setdefault("contradicted_by", None)
        result.setdefault("suspension", None)
        result["status_age_days"] = status_age_days(entry.get("verified_at"), current)
        result["fresh_until"] = fresh_until(
            entry.get("verified_at"), int(policy.get("fresh_days") or 7)
        )
        result["stale_after"] = stale_after(
            entry.get("verified_at"), int(policy.get("max_age_days") or 21)
        )
        return result

    boundary = _boundary(entry)
    age = status_age_days(entry.get("verified_at"), current)
    fresh_days = int(policy.get("fresh_days") or 7)
    max_age_days = int(policy.get("max_age_days") or 21)
    reasons: list[str] = []
    severity: str | None = None
    contradicted_by: dict[str, Any] | None = None
    suspension: dict[str, Any] | None = None

    if original_status == "suspended":
        suspension = suspension_state(entry, evidence, policy.get("suspensions") or {})
        state = suspension.get("state")
        if state in {"served", "not_applied"}:
            result["status"] = "unknown"
            reasons.append(f"suspension_{state}")
            severity = "contradicted"
            if state == "not_applied":
                contradicted_by = {
                    "fixture_id": suspension.get("appearance_fixture_id"),
                    "date": suspension.get("appearance_date"),
                    "squad_status": suspension.get("appearance_squad_status"),
                }
        elif state in {"no_remaining_fixture"}:
            result["status"] = "unknown"
            reasons.append("suspension_resolved")
            severity = "contradicted"
        elif state in {"scope_unknown", "unverified"}:
            reasons.append("suspension_scope_unknown")
            severity = "aging"
    elif original_status in {"out", "doubtful"}:
        appearance = _contradicting_appearance(entry, evidence, boundary)
        if appearance is not None:
            result["status"] = "unknown"
            reasons.append(
                "appeared_after_status"
                if original_status == "out"
                else "doubt_resolved_by_appearance"
            )
            severity = "contradicted"
            contradicted_by = {
                "fixture_id": appearance.get("fixture_id"),
                "date": appearance.get("date"),
                "competition_id": appearance.get("competition_id"),
                "opponent_name": appearance.get("opponent_name"),
                "squad_status": appearance.get("squad_status"),
                "started": appearance.get("started"),
                "minutes": appearance.get("minutes"),
            }

    if result.get("status") in KNOWN_STATUSES and age is not None and age > max_age_days:
        result["status"] = "unknown"
        reasons.append("status_older_than_max_age")
        severity = severity or "aging"
    if result.get("status") in KNOWN_STATUSES and age is not None and age > fresh_days:
        reasons.append("status_older_than_7_days")
        severity = severity or "aging"

    result["review_required"] = bool(reasons)
    result["review_reasons"] = reasons
    result["review_severity"] = severity
    result["review_reason"] = reasons[0] if reasons else None
    result["contradicted_by"] = contradicted_by
    result["suspension"] = suspension
    result["status_age_days"] = age
    result["fresh_until"] = fresh_until(entry.get("verified_at"), fresh_days)
    result["stale_after"] = stale_after(entry.get("verified_at"), max_age_days)
    return result


def reconcile_entries(
    entries: list[dict[str, Any]],
    evidence: dict[str, Any],
    policy: dict[str, Any],
    today: date | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reconcile every entry and return the review summary."""
    if str(evidence.get("status") or "ok") != "ok":
        result = []
        for entry in entries:
            current = dict(entry)
            current.setdefault("review_required", False)
            current.setdefault("review_reason", None)
            current.setdefault("review_reasons", [])
            current.setdefault("review_severity", None)
            current.setdefault("contradicted_by", None)
            current.setdefault("suspension", None)
            result.append(current)
        return result, {
            "status": "unavailable",
            "count": 0,
            "contradicted": 0,
            "aging": 0,
            "suspension_served": 0,
            "reconciliation": {
                "status": "unavailable",
                "errors": evidence.get("errors") or [],
                "evidence": evidence.get("coverage") or {},
            },
        }
    reconciled = [reconcile_entry(entry, evidence, policy, today) for entry in entries]
    contradicted = sum(1 for entry in reconciled if entry.get("review_severity") == "contradicted")
    aging = sum(1 for entry in reconciled if entry.get("review_severity") == "aging")
    served = sum(
        1 for entry in reconciled if (entry.get("suspension") or {}).get("state") == "served"
    )
    count = sum(1 for entry in reconciled if entry.get("review_required"))
    status = "contradicted" if contradicted else "review" if aging else "ok"
    return reconciled, {
        "status": status,
        "count": count,
        "contradicted": contradicted,
        "aging": aging,
        "suspension_served": served,
        "reconciliation": {
            "status": "ok",
            "errors": [],
            "evidence": evidence.get("coverage") or {},
        },
    }


def ledger_review(
    ledger_updated_at: Any,
    max_verified_at: Any,
    latest_news: dict[str, Any] | None,
    policy: dict[str, Any],
    today: date | None = None,
) -> dict[str, Any]:
    if not bool(policy.get("ledger_news_review", True)):
        return {"status": "ok", "reason": None}
    current = today or date.today()
    ledger_dates = [
        value for value in (_as_date(ledger_updated_at), _as_date(max_verified_at)) if value
    ]
    ledger_date = max(ledger_dates) if ledger_dates else None
    news_date = _as_date((latest_news or {}).get("date"))
    if ledger_date is None:
        return {
            "status": "review",
            "reason": "ledger_date_missing",
            "ledger_updated_at": None,
            "ledger_max_verified_at": _iso(_as_date(max_verified_at)),
            "latest_news_date": _iso(news_date),
            "latest_news_title": (latest_news or {}).get("title"),
            "latest_news_url": (latest_news or {}).get("url"),
            "days_since_ledger_update": None,
            "days_since_latest_news": None,
        }
    review = news_date is not None and news_date > ledger_date
    return {
        "status": "review" if review else "ok",
        "reason": "ledger_older_than_latest_news" if review else None,
        "ledger_updated_at": _iso(_as_date(ledger_updated_at)),
        "ledger_max_verified_at": _iso(_as_date(max_verified_at)),
        "latest_news_date": _iso(news_date),
        "latest_news_title": (latest_news or {}).get("title"),
        "latest_news_url": (latest_news or {}).get("url"),
        "days_since_ledger_update": (current - ledger_date).days,
        "days_since_latest_news": (current - news_date).days if news_date else None,
    }


def assert_no_unresolved_contradictions(entries: list[dict[str, Any]]) -> None:
    offenders = [
        entry
        for entry in entries
        if entry.get("review_severity") == "contradicted"
        and str(entry.get("status") or "") in CONTRADICTABLE_STATUSES
    ]
    if offenders:
        labels = ", ".join(
            str(entry.get("player_name") or entry.get("player_id")) for entry in offenders
        )
        raise ValueError(f"contradicted availability still published as current: {labels}")


def load_reconciliation_evidence(season: str) -> dict[str, Any]:
    """Load the local participation, card and news evidence for a season."""
    from fitba.ingest.match_data import load_player_squads
    from fitba.ingest.match_extras import load_events
    from fitba.ingest.news import load_news
    from fitba.normalize.schedule import load_schedule

    schedule = load_schedule(season)
    played = {
        int(row["fixture_id"]): row
        for row in schedule
        if row.get("fixture_id") is not None
        and row.get("status") == "played"
        and not row.get("is_friendly")
        and str(row.get("competition_id") or "") in COMPETITIVE_COMPETITIONS
    }
    squads = load_player_squads()
    participation: list[dict[str, Any]] = []
    with_squads: set[int] = set()
    complete_bench: set[int] = set()
    if squads.height:
        for row in squads.to_dicts():
            if int(row.get("team_id") or 0) != 252:
                continue
            fixture_id = int(row.get("fixture_id") or 0)
            fixture = played.get(fixture_id)
            if fixture is None:
                continue
            with_squads.add(fixture_id)
            if bool(row.get("bench_complete")):
                complete_bench.add(fixture_id)
            participation.append(
                {
                    "player_id": int(row.get("player_id") or 0),
                    "fixture_id": fixture_id,
                    "date": fixture.get("date"),
                    "competition_id": fixture.get("competition_id"),
                    "competition_name": fixture.get("competition_name"),
                    "opponent_name": fixture.get("opponent_name") or row.get("opponent"),
                    "team_id": 252,
                    "squad_status": row.get("squad_status"),
                    "started": bool(row.get("started")),
                    "minutes": int(row.get("minutes") or 0),
                    "bench_complete": bool(row.get("bench_complete")),
                }
            )

    events = load_events(season)
    red_cards: list[dict[str, Any]] = []
    if events.height:
        for row in events.to_dicts():
            if int(row.get("team_id") or 0) != 252:
                continue
            if str(row.get("event_type") or "").casefold() != "card":
                continue
            detail = str(row.get("detail") or "").casefold()
            if not (row.get("is_red_card") or "red" in detail):
                continue
            fixture_id = int(row.get("fixture_id") or 0)
            fixture = played.get(fixture_id)
            if fixture is None:
                continue
            red_type = (
                "second_yellow"
                if row.get("is_second_yellow") or "second yellow" in detail
                else "straight_red"
            )
            red_cards.append(
                {
                    "player_id": int(row.get("player_id") or 0),
                    "fixture_id": fixture_id,
                    "date": fixture.get("date"),
                    "competition_id": fixture.get("competition_id"),
                    "competition_name": fixture.get("competition_name"),
                    "red_type": red_type,
                    "detail": row.get("detail"),
                }
            )

    schedule_rows = [
        {
            **row,
            "bench_complete": int(row.get("fixture_id") or 0) in complete_bench,
        }
        for row in schedule
        if row.get("fixture_id") is not None
    ]
    news = load_news()
    latest_news = None
    if news.height:
        row = news.row(0, named=True)
        published = _as_date(row.get("published_date"))
        latest_news = {
            "date": _iso(published),
            "title": row.get("title"),
            "url": row.get("url"),
        }
    latest_fixture = max((str(row.get("date") or "") for row in played.values()), default=None)
    return {
        "status": "ok",
        "season": season,
        "participation": participation,
        "red_cards": red_cards,
        "schedule": schedule_rows,
        "latest_news": latest_news,
        "coverage": {
            "fixtures": len(played),
            "with_squads": len(with_squads),
            "complete_bench": len(complete_bench),
            "latest_fixture_date": latest_fixture,
        },
    }


__all__ = [
    "assert_no_unresolved_contradictions",
    "fresh_until",
    "ledger_review",
    "load_reconciliation_evidence",
    "reconcile_entries",
    "reconcile_entry",
    "stale_after",
    "status_age_days",
    "suspension_state",
]
