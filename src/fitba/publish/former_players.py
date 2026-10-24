"""Published former-player index and per-season detail documents."""

from __future__ import annotations

import copy
from collections import Counter
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from fitba.analytics.former_players import (
    aberdeen_record,
    arrival_for,
    club_context,
    development_summary,
    former_anchor,
    former_player_rows,
    post_career_record,
    sell_on_watch,
    vs_aberdeen_record,
)
from fitba.analytics.scouting import per90
from fitba.analytics.valuation import age_at
from fitba.ingest.former_players import (
    load_former_meta,
    load_former_players,
    load_post_seasons,
    load_transfer_events,
)
from fitba.ingest.history import load_all_history
from fitba.normalize.teams import TeamRegistry
from fitba.settings import former_players as former_config
from fitba.settings import (
    history_markets,
)
from fitba.settings import (
    sell_on_clauses as sell_on_config,
)
from fitba.settings import (
    sell_on_events as sell_on_events_config,
)
from fitba.util.dates import current_season, season_start_year, seasons_between, utc_now_iso


class FormerPlayer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_key: str
    player_id: int | None = None
    identity_status: str
    alias_keys: list[str] = Field(default_factory=list)
    name: str
    position: str | None = None
    nationality: str | None = None
    birth_date: str | None = None
    age_at_exit: int | None = None
    href: str
    transfer_href: str | None = None
    departure: dict[str, Any]
    aberdeen: dict[str, Any]
    post_career: dict[str, Any]
    sell_on_clause_id: str | None = None


class FormerPlayersDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    club_id: str
    name: str
    season: str
    generated_at: str
    state: Literal["available", "partial", "stale", "unavailable"]
    served_generated_at: str | None = None
    definition: dict[str, Any]
    coverage: dict[str, Any]
    summary: dict[str, Any]
    players: list[FormerPlayer]
    sell_on_watch: dict[str, Any]
    development_scorecard: dict[str, Any]
    sources: list[dict[str, Any]]
    notes: str


class FormerSeasonsDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    generated_at: str
    season: str
    club_id: str
    state: Literal["available", "partial", "stale", "unavailable"]
    seasons: dict[str, dict[str, Any]]
    coverage: dict[str, Any]


def former_players_schema() -> dict[str, Any]:
    return FormerPlayersDocument.model_json_schema()


def former_seasons_schema() -> dict[str, Any]:
    return FormerSeasonsDocument.model_json_schema()


def _fee_display(row: dict[str, Any] | None) -> str:
    if not row:
        return "Undisclosed"
    status = row.get("fee_status")
    if status == "free":
        return "Free"
    if status == "loan":
        return "Loan"
    if status == "disclosed" and row.get("fee_amount") is not None:
        currency = row.get("fee_currency") or "GBP"
        symbol = {"GBP": "£", "EUR": "€", "USD": "$"}.get(currency, "")
        return f"{symbol}{float(row['fee_amount']):,.0f}"
    return "Undisclosed"


def _count(rows: list[Any], key) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        value = key(row)
        counter["unknown" if value in (None, "") else str(value)] += 1
    return dict(sorted(counter.items()))


def _arrival(
    key: str, aliases: list[str], transfers: list[dict[str, Any]]
) -> dict[str, Any] | None:
    candidates = [
        arrival
        for candidate_key in [key, *aliases]
        if (arrival := arrival_for(candidate_key, transfers)) is not None
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda row: str(row.get("date_effective") or ""))


def _expected_seasons(departure: dict[str, Any], season: str) -> list[str]:
    departure_season = str(departure.get("season") or season)
    if not departure_season:
        return []
    try:
        return seasons_between(departure_season, season)
    except ValueError:
        return []


def _post_rows(
    seasons: list[dict[str, Any]], key: str, departure: dict[str, Any], season: str
) -> list[dict[str, Any]]:
    start = season_start_year(str(departure.get("season") or season))
    rows = [
        row
        for row in seasons
        if str(row.get("player_key") or "") == key
        and int(row.get("season_year") or 0) >= start
        and str(row.get("team_name") or "") != "Aberdeen"
        and str(row.get("scope") or "league") == "league"
    ]
    return sorted(
        rows, key=lambda row: (str(row.get("season") or ""), str(row.get("team_name") or ""))
    )


def _events_for(
    events: list[dict[str, Any]], key: str, departure: dict[str, Any]
) -> list[dict[str, Any]]:
    cutoff = str(departure.get("date_effective") or "")[:10]
    rows = []
    seen: set[tuple[str, str, str, str]] = set()
    for row in events:
        if str(row.get("player_key") or "") != key:
            continue
        if cutoff and str(row.get("event_date") or "")[:10] <= cutoff:
            continue
        event_key = (
            str(row.get("event_date") or "")[:4],
            str(row.get("from_team_name") or "").casefold(),
            str(row.get("to_team_name") or "").casefold(),
            str(row.get("kind") or ""),
        )
        if event_key in seen:
            continue
        seen.add(event_key)
        rows.append(
            {
                "date": str(row.get("event_date") or "")[:10],
                "type": row.get("type"),
                "kind": row.get("kind"),
                "teams": {
                    "out": {
                        "id": row.get("from_team_id"),
                        "name": row.get("from_team_name"),
                    },
                    "in": {
                        "id": row.get("to_team_id"),
                        "name": row.get("to_team_name"),
                    },
                },
            }
        )
    return rows


def _sources() -> list[dict[str, Any]]:
    return [
        {
            "id": "api_football",
            "name": "API-Football",
            "url": "https://www.api-football.com",
            "verified_at": "2026-10-23",
            "note": "Licensed provider; derived display only, no raw provider dump.",
        },
        {
            "id": "transfer_register",
            "name": "Confirmed transfer register",
            "url": None,
            "verified_at": "2026-10-21",
            "note": "Former-player universe and departure facts.",
        },
        {
            "id": "wikipedia",
            "name": "Wikipedia season records",
            "url": "https://en.wikipedia.org",
            "verified_at": "2026-10-21",
            "note": "Finding aid and curated fee/sell-on evidence where cited.",
        },
    ]


def _empty_watch() -> dict[str, Any]:
    return {
        "clauses": [],
        "summary": {
            "total": 0,
            "computed": 0,
            "missing_inputs": 0,
            "not_triggered": 0,
            "no_sale": 0,
            "unknown": 0,
            "known_receipts_gbp": None,
            "unavailable_count": 0,
            "note": "No sell-on watch is available.",
        },
    }


def _empty_scorecard() -> dict[str, Any]:
    return {
        "definitions": {},
        "cohorts": {},
        "by_exit_season": [],
        "vs_aberdeen": {
            "players_with_appearance": 0,
            "appearances": 0,
            "goals": 0,
            "assists": 0,
        },
        "note": "No former-player record is available.",
    }


def _unavailable(season: str, generated_at: str) -> tuple[dict[str, Any], dict[str, Any]]:
    config = former_config()
    definition = {
        "universe": (
            "Latest published permanent/free departure, excluding current squad, "
            "returns and loan-outs"
        ),
        "universe_as_of": generated_at,
        "start_season": str((config.get("coverage") or {}).get("register_from") or "2019-20"),
        "include_kinds": ["permanent", "free"],
        "exclude_kinds": ["loan", "loan_return"],
        "rivals": config.get("rivals") or [],
        "developed_proxy": config.get("development") or {},
        "scorecard": config.get("scorecard") or {},
        "sell_on_policy": (
            "Compute a receipt only when percentage, basis and a public subsequent fee "
            "are all evidenced."
        ),
    }
    index = {
        "schema_version": "1.0.0",
        "club_id": "sco:aberdeen",
        "name": "Aberdeen",
        "season": season,
        "generated_at": generated_at,
        "state": "unavailable",
        "served_generated_at": None,
        "definition": definition,
        "coverage": {
            "status": "unavailable",
            "as_of": generated_at,
            "register_from": definition["start_season"],
            "post_career_source": "api_football",
            "post_career_updated_at": None,
            "backfill": {},
            "counts": {
                "players": 0,
                "with_api_id": 0,
                "without_api_id": 0,
                "with_post_career_rows": 0,
                "without_post_career_rows": 0,
                "current_club_known": 0,
                "current_club_unknown": 0,
            },
            "gaps": [],
            "note": (
                "Run `uv run fitba former-players backfill` and then publish. "
                "The former-player record is unavailable."
            ),
        },
        "summary": {
            "total": 0,
            "by_exit_kind": {},
            "by_fee_status": {},
            "by_fee_basis": {},
            "by_exit_season": {},
            "by_destination": {},
            "by_current_league": {},
            "by_current_country": {},
            "by_current_status": {},
            "by_current_coverage": {},
            "at_rival_now": 0,
            "rival_spell": 0,
            "at_club": 0,
            "on_loan": 0,
            "free_agent": 0,
            "retired": 0,
            "current_unknown": 0,
            "in_covered_feed": 0,
            "not_in_covered_feed": 0,
            "top_flight_abroad": 0,
            "current_club_unknown": 0,
            "young_exits": 0,
            "developed_here": 0,
            "developed_here_with_fee": 0,
            "sell_on_clauses": 0,
            "sell_on_triggers": 0,
            "sell_on_computable": 0,
            "sell_on_implied_events": 0,
            "sell_on_implied_low_gbp": None,
            "sell_on_implied_high_gbp": None,
            "sell_on_not_computable": 0,
        },
        "players": [],
        "sell_on_watch": _empty_watch(),
        "development_scorecard": _empty_scorecard(),
        "sources": _sources(),
        "notes": "Former-player record unavailable.",
    }
    seasons_doc = {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "season": season,
        "club_id": "sco:aberdeen",
        "state": "unavailable",
        "seasons": {},
        "coverage": {
            "players_with_detail": 0,
            "players_without_detail": 0,
            "note": "No former-player season detail is available.",
        },
    }
    return index, seasons_doc


def _stale(
    previous_index: dict[str, Any], previous_seasons: dict[str, Any] | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    index = copy.deepcopy(previous_index)
    index["state"] = "stale"
    index["served_generated_at"] = previous_index.get("generated_at")
    index.setdefault("coverage", {})["status"] = "stale"
    index["coverage"]["note"] = (
        "Local post-Aberdeen data is unavailable; this is the last served payload. "
        "Run the former-players refresh and republish."
    )
    seasons_doc = copy.deepcopy(previous_seasons or {})
    if seasons_doc:
        seasons_doc["state"] = "stale"
    return index, seasons_doc


def build_former_bundle(
    *,
    season: str | None = None,
    squad: dict[str, Any] | None = None,
    transfers: list[dict[str, Any]] | None = None,
    generated_at: str | None = None,
    previous_index: dict[str, Any] | None = None,
    previous_seasons: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    target_season = season or current_season()
    generated = generated_at or utc_now_iso()
    config = former_config()
    profile_frame = load_former_players()
    season_frame = load_post_seasons()
    event_frame = load_transfer_events()
    if profile_frame.height == 0:
        if previous_index:
            return _stale(previous_index, previous_seasons)
        return _unavailable(target_season, generated)
    profiles = {str(row.get("player_key")): row for row in profile_frame.to_dicts()}
    seasons_rows = season_frame.to_dicts() if season_frame.height else []
    event_rows = event_frame.to_dicts() if event_frame.height else []
    transfer_rows = transfers or []
    squad_data = squad or {"players": [], "excluded_players": []}
    universe = former_player_rows(transfer_rows, squad_data)
    if not universe:
        if previous_index:
            return _stale(previous_index, previous_seasons)
        return _unavailable(target_season, generated)
    teams = TeamRegistry()
    markets = (history_markets() or {}).get("markets", [])
    history = load_all_history().get("seasons") or {}
    appearances: list[dict[str, Any]] = []
    match_stats: list[dict[str, Any]] = []
    for payload in history.values():
        if payload.get("appearances") is not None and payload["appearances"].height:
            appearances.extend(payload["appearances"].to_dicts())
        if payload.get("player_match_stats") is not None and payload["player_match_stats"].height:
            match_stats.extend(payload["player_match_stats"].to_dicts())
    clauses = list(sell_on_config().get("clauses") or [])
    fee_events = list(sell_on_events_config().get("events") or [])
    events_by_key: dict[str, list[dict[str, Any]]] = {}
    for row in event_rows:
        key = str(row.get("player_key") or "")
        events_by_key.setdefault(key, []).append(
            {
                "date": row.get("event_date"),
                "type": row.get("type"),
                "kind": row.get("kind"),
                "teams": {
                    "out": {
                        "id": row.get("from_team_id"),
                        "name": row.get("from_team_name"),
                    },
                    "in": {
                        "id": row.get("to_team_id"),
                        "name": row.get("to_team_name"),
                    },
                },
            }
        )
    watch = sell_on_watch(clauses, transfer_rows, events_by_key, fee_events, config=config)
    for clause in watch.get("clauses") or []:
        event = clause.get("event")
        if event:
            event["from_club_name"] = (
                teams.display_name(str(event.get("from_club_name") or ""))
                if event.get("from_club_name")
                else None
            )
            event["to_club_name"] = (
                teams.display_name(str(event.get("to_club_name") or ""))
                if event.get("to_club_name")
                else None
            )
    clause_by_player = {
        str(clause.get("player_key")): clause.get("clause_id")
        for clause in (watch.get("clauses") or [])
        if clause.get("player_key")
    }
    players: list[dict[str, Any]] = []
    seasons_doc: dict[str, Any] = {}
    vs_totals = {"players_with_appearance": 0, "appearances": 0, "goals": 0, "assists": 0}
    for item in universe:
        key = item["player_key"]
        departure = item["departure"]
        profile = profiles.get(key) or {}
        aliases = list(item.get("alias_keys") or [])
        birth_date = profile.get("birth_date")
        arrival = _arrival(key, aliases, transfer_rows)
        tenure = aberdeen_record(
            appearances,
            match_stats,
            player_key=key,
            departure=departure,
            birth_date=birth_date,
            arrival=arrival,
            config=config,
        )
        post_rows = _post_rows(seasons_rows, key, departure, target_season)
        events = _events_for(event_rows, key, departure)
        post = post_career_record(
            post_rows,
            events,
            player_key=key,
            departure=departure,
            birth_date=birth_date,
            config=config,
            current_season=target_season,
            teams=teams,
            markets=markets,
        )
        post["clubs"] = [
            {"club": teams.display_name(row["club"]), "minutes": row["minutes"]}
            for row in post.get("clubs") or []
        ]
        current = post.get("current") or {}
        if current.get("club_name"):
            current["club_name"] = teams.display_name(str(current["club_name"]))
        if current.get("parent_club_name"):
            current["parent_club_name"] = teams.display_name(str(current["parent_club_name"]))
        post["current"] = current
        vs = vs_aberdeen_record(
            appearances,
            match_stats,
            player_key=key,
            after=str(departure.get("date_effective") or "")[:10],
        )
        if vs.get("appearances"):
            vs_totals["players_with_appearance"] += 1
            vs_totals["appearances"] += int(vs.get("appearances") or 0)
            vs_totals["goals"] += int(vs.get("goals") or 0)
            vs_totals["assists"] += int(vs.get("assists") or 0)
        destination = club_context(
            club_id=str(departure.get("to_club_id") or "") or None,
            club_name=departure.get("to_club_name"),
            teams=teams,
            markets=markets,
            rival_ids=tuple(
                str(row.get("club_id"))
                for row in (config.get("rivals") or [])
                if row.get("club_id")
            ),
        )
        anchor = former_anchor(key)
        departure_payload = {
            "transfer_id": departure.get("transfer_id"),
            "date": departure.get("date_effective"),
            "season": departure.get("season"),
            "window": departure.get("window"),
            "kind": departure.get("transfer_kind"),
            "fee_status": departure.get("fee_status"),
            "fee_amount": departure.get("fee_amount"),
            "fee_currency": departure.get("fee_currency"),
            "fee_display": _fee_display(departure),
            "fee_estimate": departure.get("fee_estimate"),
            "to_club_id": departure.get("to_club_id"),
            "to_club_name": destination["club_name"],
            "to_market": destination["market"],
            "to_country": destination["country"],
            "is_scottish_club": destination["is_scottish_club"],
            "is_rival": destination["is_rival"],
            "rival_name": destination["rival_name"],
            "verification_status": departure.get("verification_status"),
            "source_urls": departure.get("source_urls") or [],
        }
        aberdeen_payload = {k: v for k, v in tenure.items() if k != "by_season"}
        players.append(
            {
                "player_key": key,
                "player_id": profile.get("player_id"),
                "identity_status": item["identity_status"],
                "alias_keys": aliases,
                "name": profile.get("player_name") or departure.get("player_name") or key,
                "position": profile.get("position") or departure.get("position"),
                "nationality": profile.get("nationality") or departure.get("nationality"),
                "birth_date": birth_date,
                "age_at_exit": age_at(birth_date, departure.get("date_effective")),
                "href": f"/former-players/#{anchor}",
                "transfer_href": (
                    f"/transfers/#transfer-{departure.get('transfer_id')}"
                    if departure.get("transfer_id")
                    else None
                ),
                "departure": departure_payload,
                "aberdeen": aberdeen_payload,
                "post_career": post,
                "sell_on_clause_id": clause_by_player.get(key),
            }
        )
        expected = _expected_seasons(departure, target_season)
        present = sorted({str(row.get("season") or "") for row in post_rows})
        missing = [item_season for item_season in expected if item_season not in present]
        seasons_doc[key] = {
            "coverage": {
                "status": post.get("status"),
                "expected_seasons": expected,
                "present_seasons": present,
                "missing_seasons": missing,
            },
            "aberdeen_by_season": tenure.get("by_season") or [],
            "post_seasons": [
                {
                    **{
                        field: row.get(field)
                        for field in (
                            "season",
                            "competition",
                            "country",
                            "league_tier",
                            "appearances",
                            "starts",
                            "minutes",
                            "goals",
                            "assists",
                            "rating",
                            "source",
                        )
                    },
                    "team_name": teams.display_name(str(row.get("team_name") or "")),
                    "goals_p90": per90(row.get("goals"), row.get("minutes"))
                    if int(row.get("minutes") or 0)
                    >= int((config.get("post_career") or {}).get("min_minutes_for_rates") or 180)
                    else None,
                    "assists_p90": per90(row.get("assists"), row.get("minutes"))
                    if int(row.get("minutes") or 0)
                    >= int((config.get("post_career") or {}).get("min_minutes_for_rates") or 180)
                    else None,
                }
                for row in post_rows
            ],
            "transfer_chain": [
                {
                    "date": event.get("date"),
                    "from_club_name": teams.display_name(
                        str(((event.get("teams") or {}).get("out") or {}).get("name") or "")
                    ),
                    "to_club_name": teams.display_name(
                        str(((event.get("teams") or {}).get("in") or {}).get("name") or "")
                    ),
                    "kind": event.get("kind"),
                }
                for event in events
            ],
            "vs_aberdeen": vs,
        }

    summary = {
        "total": len(players),
        "by_exit_kind": _count(players, lambda row: (row["departure"] or {}).get("kind")),
        "by_fee_status": _count(players, lambda row: (row["departure"] or {}).get("fee_status")),
        "by_fee_basis": _count(
            players, lambda row: ((row["departure"] or {}).get("fee_estimate") or {}).get("basis")
        ),
        "by_exit_season": _count(players, lambda row: (row["departure"] or {}).get("season")),
        "by_destination": _count(players, lambda row: (row["departure"] or {}).get("to_market")),
        "by_current_league": _count(
            players, lambda row: (row["post_career"] or {}).get("current", {}).get("league")
        ),
        "by_current_country": _count(
            players, lambda row: (row["post_career"] or {}).get("current", {}).get("country")
        ),
        "by_current_status": _count(
            players, lambda row: (row["post_career"] or {}).get("current", {}).get("status")
        ),
        "by_current_coverage": _count(
            players, lambda row: (row["post_career"] or {}).get("current", {}).get("coverage")
        ),
        "at_rival_now": sum(
            1 for row in players if (row["post_career"] or {}).get("rival_current")
        ),
        "rival_spell": sum(1 for row in players if (row["post_career"] or {}).get("at_rival")),
        "at_club": sum(
            1
            for row in players
            if (row["post_career"] or {}).get("current", {}).get("status") == "at_club"
        ),
        "on_loan": sum(
            1
            for row in players
            if (row["post_career"] or {}).get("current", {}).get("status") == "on_loan"
        ),
        "free_agent": sum(
            1
            for row in players
            if (row["post_career"] or {}).get("current", {}).get("status") == "free_agent"
        ),
        "retired": sum(
            1
            for row in players
            if (row["post_career"] or {}).get("current", {}).get("status") == "retired"
        ),
        "current_unknown": sum(
            1
            for row in players
            if (row["post_career"] or {}).get("current", {}).get("status") == "unknown"
        ),
        "in_covered_feed": sum(
            1
            for row in players
            if (row["post_career"] or {}).get("current", {}).get("coverage") == "current"
        ),
        "not_in_covered_feed": sum(
            1
            for row in players
            if (row["post_career"] or {}).get("current", {}).get("coverage") != "current"
        ),
        "top_flight_abroad": sum(
            1 for row in players if (row["post_career"] or {}).get("top_flight_abroad")
        ),
        "current_club_unknown": sum(
            1
            for row in players
            if not (row["post_career"] or {}).get("current", {}).get("club_name")
        ),
        "young_exits": sum(
            1
            for row in players
            if row.get("age_at_exit") is not None
            and row["age_at_exit"]
            <= int((config.get("development") or {}).get("young_exit_age_max") or 23)
        ),
        "developed_here": sum(
            1 for row in players if (row["aberdeen"] or {}).get("developed_here") == "yes"
        ),
        "developed_here_with_fee": sum(
            1
            for row in players
            if (row["aberdeen"] or {}).get("developed_here") == "yes"
            and (row["departure"] or {}).get("fee_status")
            in {"disclosed", "reported", "undisclosed"}
        ),
        "sell_on_clauses": int((watch.get("summary") or {}).get("total") or 0),
        "sell_on_triggers": sum(
            1
            for clause in watch.get("clauses") or []
            if clause.get("event_status") in {"detected_priced", "detected_unpriced"}
        ),
        "sell_on_computable": int((watch.get("summary") or {}).get("computed") or 0),
        "sell_on_implied_events": int((watch.get("summary") or {}).get("computed") or 0),
        "sell_on_implied_low_gbp": (watch.get("summary") or {}).get("known_receipts_gbp"),
        "sell_on_implied_high_gbp": (watch.get("summary") or {}).get("known_receipts_gbp"),
        "sell_on_not_computable": int((watch.get("summary") or {}).get("missing_inputs") or 0),
    }
    meta = load_former_meta()
    gaps = [
        {"player_key": row["player_key"], "reason": "no_api_id"}
        for row in players
        if row.get("player_id") is None
    ]
    for row in players:
        key = row["player_key"]
        detail = seasons_doc.get(key) or {}
        for season_value in (detail.get("coverage") or {}).get("missing_seasons") or []:
            gaps.append(
                {
                    "player_key": key,
                    "season": season_value,
                    "reason": "season_unavailable",
                }
            )
    gaps = gaps[:100]
    post_player_count = sum(
        1
        for row in players
        if ((row.get("post_career") or {}).get("totals") or {}).get("seasons_with_data")
    )
    coverage = {
        "status": "partial" if gaps else "measured",
        "as_of": meta.get("generated_at") or generated,
        "register_from": str((config.get("coverage") or {}).get("register_from") or "2019-20"),
        "post_career_source": "api_football",
        "post_career_updated_at": meta.get("generated_at"),
        "backfill": meta,
        "counts": {
            "players": len(players),
            "with_api_id": sum(1 for row in players if row.get("player_id") is not None),
            "without_api_id": sum(1 for row in players if row.get("player_id") is None),
            "with_post_career_rows": post_player_count,
            "without_post_career_rows": len(players) - post_player_count,
            "current_club_known": sum(
                1
                for row in players
                if (row.get("post_career") or {}).get("current", {}).get("club_name")
            ),
            "current_club_unknown": sum(
                1
                for row in players
                if not (row.get("post_career") or {}).get("current", {}).get("club_name")
            ),
        },
        "gaps": gaps,
        "note": (
            "The register covers 2019-20 onward. Post-career league seasons are measured "
            "where the provider covers them; missing seasons are gaps, not zero. Cup and "
            "European provider rows are excluded from totals because some repeat league "
            "totals. Ratings are league-relative."
        ),
    }
    scorecard = development_summary(players, config=config)
    scorecard["vs_aberdeen"] = vs_totals
    definition = {
        "universe": (
            "Latest published permanent/free departure, excluding current squad, "
            "returns and loan-outs"
        ),
        "universe_as_of": generated,
        "start_season": coverage["register_from"],
        "include_kinds": ["permanent", "free"],
        "exclude_kinds": ["loan", "loan_return"],
        "rivals": config.get("rivals") or [],
        "developed_proxy": config.get("development") or {},
        "scorecard": config.get("scorecard") or {},
        "sell_on_policy": (
            "Compute a receipt only when percentage, basis and a public subsequent fee "
            "are all evidenced."
        ),
    }
    state = (
        "partial" if (gaps or meta.get("budget_exhausted") or meta.get("errors")) else "available"
    )
    index = {
        "schema_version": "1.0.0",
        "club_id": "sco:aberdeen",
        "name": "Aberdeen",
        "season": target_season,
        "generated_at": generated,
        "state": state,
        "served_generated_at": None,
        "definition": definition,
        "coverage": coverage,
        "summary": summary,
        "players": players,
        "sell_on_watch": watch,
        "development_scorecard": scorecard,
        "sources": _sources(),
        "notes": (
            "Former players are not transfer targets. A later career does not prove a "
            "sale was right, and a public fee is not the club's internal valuation."
        ),
    }
    seasons_document = {
        "schema_version": "1.0.0",
        "generated_at": generated,
        "season": target_season,
        "club_id": "sco:aberdeen",
        "state": state,
        "seasons": seasons_doc,
        "coverage": {
            "players_with_detail": len(seasons_doc),
            "players_without_detail": max(0, len(players) - len(seasons_doc)),
            "note": (
                "One entry per former player. Aberdeen seasons are covered from 2019-20; "
                "post-Aberdeen rows are league competitions only."
            ),
        },
    }
    FormerPlayersDocument.model_validate(index)
    FormerSeasonsDocument.model_validate(seasons_document)
    return index, seasons_document


__all__ = [
    "FormerPlayer",
    "FormerPlayersDocument",
    "FormerSeasonsDocument",
    "build_former_bundle",
    "former_players_schema",
    "former_seasons_schema",
]
