"""Former-player universe, Aberdeen tenure, post-career record and sell-on watch.

This module is the single production home for the former-player facts. It reads
published transfer rows, covered history rows and normalized provider seasons;
it never calls the network and never re-runs the transfer valuation.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from fitba.analytics.valuation import age_at, parse_fee
from fitba.normalize.names import slugify
from fitba.normalize.players import normalize_player_name
from fitba.normalize.scope import is_competitive_row
from fitba.normalize.teams import TeamRegistry
from fitba.normalize.transfer_history import (
    parse_date,
    parse_transfer_type,
    subsequent_permanent_transfer,
    transfer_date,
)
from fitba.util.dates import previous_season, season_start_year, seasons_between

REGISTER_FROM = "2019-20"
RIVAL_IDS = ("sco:celtic", "sco:rangers", "sco:dundee-united")


def _norm(value: Any) -> str:
    return " ".join(normalize_player_name(str(value or "")).split())


def _date(value: Any) -> date | None:
    return parse_date(value)


def _latest_out_by_key(transfers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in transfers:
        if str(row.get("direction") or "") != "out":
            continue
        key = str(row.get("player_key") or "")
        if not key:
            continue
        current = latest.get(key)
        if current is None or _row_sort(row) > _row_sort(current):
            latest[key] = row
    return latest


def _row_sort(row: dict[str, Any]) -> tuple[date, date, str]:
    effective = _date(row.get("date_effective")) or date.min
    announced = _date(row.get("date_announced")) or date.min
    return effective, announced, str(row.get("transfer_id") or "")


def _has_later_return(
    key: str, departure: dict[str, Any], transfers: list[dict[str, Any]]
) -> bool:
    """A genuine return after the exit makes the player current, not former.

    ``loan_return`` rows are ignored here: they record the end of an earlier
    loan and can sit beside a free exit (the Besuijen case). A later ``loan`` or
    ``permanent`` incoming row is a real return.
    """
    cutoff = _date(departure.get("date_effective")) or date.min
    for row in transfers:
        if str(row.get("player_key") or "") != key:
            continue
        if str(row.get("direction") or "") != "in":
            continue
        if str(row.get("transfer_kind") or "") not in {"permanent", "loan"}:
            continue
        moved = _date(row.get("date_effective")) or date.min
        if moved > cutoff:
            return True
    return False


def former_player_rows(
    transfers: list[dict[str, Any]],
    squad: dict[str, Any] | None,
    *,
    register_from: str = REGISTER_FROM,
) -> list[dict[str, Any]]:
    """Return one canonical row per former player.

    The universe is the latest outgoing row per player, kept only for
    permanent/free exits, excluding a later permanent return and any official
    squad member. Excluded profiles are allowed only when the register confirms
    the exit.
    """
    squad = squad or {}
    official = {
        str(player.get("player_key") or "")
        for player in squad.get("players") or []
        if player.get("player_key")
    }
    latest = _latest_out_by_key(transfers)
    candidates: list[dict[str, Any]] = []
    for key, departure in latest.items():
        if str(departure.get("transfer_kind") or "") not in {"permanent", "free"}:
            continue
        if key in official:
            continue
        if _has_later_return(key, departure, transfers):
            continue
        season = str(departure.get("season") or "")
        if season and season < register_from:
            continue
        candidates.append(departure)

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        grouped[
            (
                _norm(row.get("player_name")),
                _norm(row.get("to_club_name")),
                str(row.get("season") or ""),
            )
        ].append(row)

    out: list[dict[str, Any]] = []
    for group in grouped.values():
        keys = [str(row.get("player_key") or "") for row in group]
        api_keys = [key for key in keys if key.startswith("api:player:")]
        if len(group) > 1 and len(api_keys) > 1:
            for row in group:
                out.append(
                    {
                        "player_key": str(row.get("player_key") or ""),
                        "identity_status": "ambiguous_identity",
                        "alias_keys": [],
                        "departure": row,
                    }
                )
            continue
        if len(group) > 1:
            chosen = api_keys[0] if api_keys else keys[0]
            aliases = [key for key in keys if key != chosen]
            # Use the earliest dated row for the departure event; provider and
            # curated rows can drift by weeks and the earliest is the move.
            departure = min(group, key=_row_sort)
            out.append(
                {
                    "player_key": chosen,
                    "identity_status": "merged_duplicate",
                    "alias_keys": sorted(set(aliases)),
                    "departure": departure,
                }
            )
        else:
            row = group[0]
            key = str(row.get("player_key") or "")
            out.append(
                {
                    "player_key": key,
                    "identity_status": (
                        "resolved_api" if key.startswith("api:player:") else "curated_slug"
                    ),
                    "alias_keys": [],
                    "departure": row,
                }
            )
    out.sort(key=lambda item: _row_sort(item["departure"]), reverse=True)
    return out


def arrival_for(player_key: str, transfers: list[dict[str, Any]]) -> dict[str, Any] | None:
    rows = [
        row
        for row in transfers
        if str(row.get("player_key") or "") == player_key
        and str(row.get("direction") or "") == "in"
    ]
    if not rows:
        return None
    return max(rows, key=_row_sort)


def last_playing_season(departure: dict[str, Any]) -> str:
    season = str(departure.get("season") or "")
    if not season:
        return ""
    if str(departure.get("window") or "") == "summer":
        return previous_season(season)
    return season


def _weighted_rating(rows: list[dict[str, Any]]) -> float | None:
    pairs = [
        (float(row["rating"]), max(int(row.get("minutes") or 0), 1))
        for row in rows
        if row.get("rating") is not None
    ]
    if not pairs:
        return None
    total_weight = sum(weight for _, weight in pairs)
    return round(sum(value * weight for value, weight in pairs) / total_weight, 2)


def _sum_or_none(rows: list[dict[str, Any]], field: str) -> int | None:
    values: list[int] = []
    for row in rows:
        value = row.get(field)
        if value is not None:
            values.append(int(float(value)))
    return sum(values) if values else None


def aberdeen_record(
    appearances: list[dict[str, Any]],
    match_stats: list[dict[str, Any]],
    *,
    player_key: str,
    departure: dict[str, Any],
    birth_date: str | None,
    arrival: dict[str, Any] | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    rows = [
        row
        for row in appearances
        if str(row.get("player_key") or "") == player_key
        and str(row.get("team_name") or "") == "Aberdeen"
        and is_competitive_row(row)
    ]
    stats_by_fixture = {
        int(row["fixture_id"]): row
        for row in match_stats
        if str(row.get("player_key") or "") == player_key
        and row.get("fixture_id") is not None
    }
    by_season: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_season[str(row.get("season") or "")].append(row)

    seasons: list[dict[str, Any]] = []
    for season, season_rows in sorted(by_season.items()):
        stat_rows = [
            stats_by_fixture[int(row["fixture_id"])]
            for row in season_rows
            if row.get("fixture_id") is not None
            and int(row["fixture_id"]) in stats_by_fixture
        ]
        seasons.append(
            {
                "season": season,
                "squad_selections": len(season_rows),
                "appearances": sum(
                    1
                    for row in season_rows
                    if bool(row.get("started")) or int(row.get("minutes") or 0) > 0
                ),
                "starts": sum(1 for row in season_rows if bool(row.get("started"))),
                "sub_apps": sum(
                    1
                    for row in season_rows
                    if not bool(row.get("started")) and int(row.get("minutes") or 0) > 0
                ),
                "minutes": sum(int(row.get("minutes") or 0) for row in season_rows),
                "goals": _sum_or_none(stat_rows, "goals"),
                "assists": _sum_or_none(stat_rows, "assists"),
                "rating": _weighted_rating(stat_rows),
            }
        )

    def total(field: str) -> int | None:
        values = [row[field] for row in seasons if row.get(field) is not None]
        return sum(int(value) for value in values) if values else None

    first = min(
        (
            row
            for row in rows
            if bool(row.get("started")) or int(row.get("minutes") or 0) > 0
        ),
        key=lambda row: str(row.get("date") or ""),
        default=None,
    )
    first_date = str(first.get("date")) if first else None
    first_age = age_at(birth_date, first_date) if first_date else None
    register_from = str((config.get("coverage") or {}).get("register_from") or REGISTER_FROM)
    arrival_season = str((arrival or {}).get("season") or "")
    covered_arrival = bool(arrival_season) and arrival_season >= register_from
    development = config.get("development") or {}
    developed: str
    if not rows:
        developed = "unknown"
        developed_basis = "No covered Aberdeen appearance."
    elif not covered_arrival or first_age is None:
        developed = "unknown"
        developed_basis = (
            "Arrival is outside the covered record or the birth date is unknown; "
            "the covered first appearance is not the career debut."
        )
    elif first_age <= int(development.get("debut_age_max") or 21) and int(
        total("starts") or 0
    ) >= int(development.get("min_starts") or 10):
        developed = "yes"
        developed_basis = (
            f"First covered appearance at {first_age}; "
            f"{int(total('starts') or 0)} Aberdeen starts."
        )
    else:
        developed = "no"
        developed_basis = (
            f"First covered appearance at {first_age}; "
            f"{int(total('starts') or 0)} Aberdeen starts."
        )

    final_season = last_playing_season(departure)
    final_row = next((row for row in seasons if row["season"] == final_season), None)
    tenure_coverage = "unavailable" if not rows else ("complete" if covered_arrival else "partial")
    return {
        "coverage": "measured" if rows else "unavailable",
        "first_season": seasons[0]["season"] if seasons else None,
        "last_season": seasons[-1]["season"] if seasons else None,
        "seasons": [row["season"] for row in seasons],
        "squad_selections": len(rows),
        "appearances": total("appearances"),
        "starts": total("starts"),
        "sub_apps": total("sub_apps"),
        "minutes": total("minutes"),
        "goals": total("goals"),
        "assists": total("assists"),
        "rating": _weighted_rating(
            [
                stats_by_fixture[int(row["fixture_id"])]
                for row in rows
                if row.get("fixture_id") is not None
                and int(row["fixture_id"]) in stats_by_fixture
            ]
        ),
        "rating_note": "Provider rating; league-relative and not a verdict.",
        "by_season": seasons,
        "final_season": (
            {**final_row, "coverage": "measured"}
            if final_row
            else {"season": final_season, "coverage": "unavailable"}
        ),
        "history_from": register_from,
        "tenure_coverage": tenure_coverage,
        "first_appearance_covered": first_date,
        "age_at_first_appearance_covered": first_age,
        "developed_here": developed,
        "developed_basis": developed_basis,
    }


def _market_maps(markets: list[dict[str, Any]]) -> tuple[dict[str, str], dict[str, str]]:
    by_id: dict[str, str] = {}
    by_name: dict[str, str] = {}
    for entry in markets:
        market = str(entry.get("market") or "unknown")
        if entry.get("club_id"):
            by_id[str(entry["club_id"])] = market
        if entry.get("club_name"):
            by_name[_norm(entry["club_name"])] = market
    return by_id, by_name


def club_context(
    *,
    club_id: str | None,
    club_name: str | None,
    teams: TeamRegistry,
    markets: list[dict[str, Any]],
    rival_ids: tuple[str, ...] = RIVAL_IDS,
) -> dict[str, Any]:
    resolved_id = teams.resolve(str(club_name or "")) if club_name else None
    canonical_id = resolved_id
    team = None
    if canonical_id is None and club_id:
        try:
            team = teams.get(club_id)
            canonical_id = club_id
        except KeyError:
            canonical_id = None
    elif canonical_id:
        team = teams.get(canonical_id)
    by_id, by_name = _market_maps(markets)
    market = (
        by_id.get(str(canonical_id or ""))
        or by_name.get(_norm(club_name))
        or ("england" if str(club_id or "").startswith("eng:") else None)
    )
    country = team.country if team else None
    if country and country.casefold() == "scotland":
        market = "scotland"
    if market is None:
        market = "unknown"
    if not country:
        for entry in markets:
            if _norm(entry.get("club_name")) == _norm(club_name):
                country = entry.get("country")
                break
    is_scottish = True if market == "scotland" else (False if market != "unknown" else None)
    rival_name = None
    if canonical_id in rival_ids:
        rival_name = team.name if team else club_name
    else:
        for entry in markets:
            if _norm(entry.get("club_name")) == _norm(club_name):
                if str(entry.get("club_id") or "") in rival_ids:
                    rival_name = entry.get("club_name")
                break
        if rival_name is None and _norm(club_name) in {
            _norm(value) for value in ("Celtic", "Rangers", "Dundee United")
        }:
            rival_name = teams.display_name_for_id(canonical_id, club_name)
    return {
        "club_id": canonical_id or club_id,
        "club_name": (
            teams.display_name_for_id(canonical_id, club_name)
            if (canonical_id or club_name)
            else None
        ),
        "market": market,
        "country": country,
        "is_scottish_club": is_scottish,
        "is_rival": rival_name is not None,
        "rival_name": rival_name,
    }


def _current_from_rows(
    rows: list[dict[str, Any]], *, current_season: str
) -> dict[str, Any] | None:
    current = [row for row in rows if str(row.get("season") or "") == current_season]
    if not current:
        return None
    by_team: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in current:
        by_team[str(row.get("team_name") or "")].append(row)
    team_name, team_rows = max(
        by_team.items(), key=lambda item: sum(int(row.get("minutes") or 0) for row in item[1])
    )
    first = team_rows[0]
    return {
        "club_id": first.get("team_id"),
        "club_name": team_name,
        "parent_club_name": None,
        "league": first.get("league_name") or first.get("competition"),
        "country": first.get("country"),
        "league_tier": first.get("league_tier"),
        "source": "current_season_stats",
        "coverage": "current",
    }


def _current_from_events(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not events:
        return None
    latest = max(events, key=lambda event: transfer_date(event) or date.min)
    kind = str(latest.get("kind") or parse_transfer_type(latest.get("type")))
    teams = latest.get("teams") or {}
    incoming = teams.get("in") or {}
    outgoing = teams.get("out") or {}
    name = str(incoming.get("name") or "Unknown club")
    lower = name.casefold()
    if kind == "retired" or lower in {"retired", "end of career"}:
        return {
            "club_id": None,
            "club_name": None,
            "parent_club_name": None,
            "league": None,
            "country": None,
            "league_tier": None,
            "status": "retired",
            "source": "transfer_history",
            "coverage": "current",
        }
    if kind in {"free", "free_agent"} or lower in {"free agent", "without club"}:
        return {
            "club_id": None,
            "club_name": "Free agent",
            "parent_club_name": None,
            "league": None,
            "country": None,
            "league_tier": None,
            "status": "free_agent",
            "source": "transfer_history",
            "coverage": "historical",
        }
    return {
        "club_id": incoming.get("id"),
        "club_name": name,
        "parent_club_name": outgoing.get("name") if kind == "loan" else None,
        "league": None,
        "country": None,
        "league_tier": None,
        "status": "on_loan" if kind == "loan" else "at_club",
        "source": "transfer_history",
        "coverage": "historical",
    }


def _rival_spells(
    rows: list[dict[str, Any]],
    *,
    current: dict[str, Any],
    departure: dict[str, Any],
    teams: TeamRegistry,
    markets: list[dict[str, Any]],
    rival_ids: tuple[str, ...],
) -> list[dict[str, Any]]:
    spells: dict[str, dict[str, Any]] = {}
    for row in rows:
        context = club_context(
            club_id=str(row.get("team_id") or "") or None,
            club_name=row.get("team_name"),
            teams=teams,
            markets=markets,
            rival_ids=rival_ids,
        )
        if not context["is_rival"]:
            continue
        club = context["rival_name"] or context["club_name"]
        season = str(row.get("season") or "")
        entry = spells.setdefault(
            club, {"club": club, "from_season": season, "to_season": season, "current": False}
        )
        entry["from_season"] = min(entry["from_season"], season)
        entry["to_season"] = max(entry["to_season"], season)
    departure_context = club_context(
        club_id=departure.get("to_club_id"),
        club_name=departure.get("to_club_name"),
        teams=teams,
        markets=markets,
        rival_ids=rival_ids,
    )
    if departure_context["is_rival"]:
        club = departure_context["rival_name"] or departure_context["club_name"] or "Rival"
        season = str(departure.get("season") or "")
        entry = spells.setdefault(
            club, {"club": club, "from_season": season, "to_season": season, "current": False}
        )
        entry["from_season"] = min(entry["from_season"], season)
        entry["to_season"] = max(entry["to_season"], season)
    if current.get("is_rival"):
        club = current.get("rival_name") or current.get("club_name") or "Rival"
        entry = spells.setdefault(
            club, {"club": club, "from_season": "", "to_season": "", "current": True}
        )
        entry["current"] = True
    return sorted(spells.values(), key=lambda item: (item["from_season"] or "", item["club"]))


def post_career_record(
    seasons: list[dict[str, Any]],
    events: list[dict[str, Any]],
    *,
    player_key: str,
    departure: dict[str, Any],
    birth_date: str | None,
    config: dict[str, Any],
    current_season: str,
    teams: TeamRegistry,
    markets: list[dict[str, Any]],
) -> dict[str, Any]:
    del birth_date  # reserved for future age-at-post-season facts
    departure_season = str(departure.get("season") or "")
    start_year = season_start_year(departure_season) if departure_season else 0
    rows = [
        row
        for row in seasons
        if str(row.get("player_key") or "") == player_key
        and int(row.get("season_year") or 0) >= start_year
        and str(row.get("team_name") or "") != "Aberdeen"
        and str(row.get("scope") or "league") == "league"
    ]
    expected = (
        seasons_between(departure_season, current_season) if departure_season else []
    )
    present = sorted({str(row.get("season") or "") for row in rows if row.get("season")})
    if not rows:
        status = "unavailable"
    elif len(present) < len(expected):
        status = "partial"
    else:
        status = "measured"

    def total(field: str) -> int | None:
        values: list[int] = []
        for row in rows:
            value = row.get(field)
            if value is not None:
                values.append(int(float(value)))
        return sum(values) if values else None

    clubs: dict[str, int] = defaultdict(int)
    countries: dict[str, int] = defaultdict(int)
    for row in rows:
        if row.get("team_name"):
            clubs[str(row["team_name"])] += int(row.get("minutes") or 0)
        if row.get("country"):
            countries[str(row["country"])] += int(row.get("minutes") or 0)

    departure_date = _date(departure.get("date_effective"))
    player_events = [
        event
        for event in events
        if str(event.get("player_key") or "") == player_key
        and (
            departure_date is None
            or (transfer_date(event) or date.min) > departure_date
        )
    ]
    current = _current_from_rows(rows, current_season=current_season)
    if current is None:
        current = _current_from_events(player_events)
    if current is None:
        latest_team = max(clubs, key=lambda name: clubs[name]) if clubs else None
        latest_row = next((row for row in rows if row.get("team_name") == latest_team), None)
        if latest_row:
            current = {
                "club_id": latest_row.get("team_id"),
                "club_name": latest_team,
                "parent_club_name": None,
                "league": latest_row.get("league_name") or latest_row.get("competition"),
                "country": latest_row.get("country"),
                "league_tier": latest_row.get("league_tier"),
                "status": "at_club",
                "source": "latest_season",
                "coverage": "historical",
            }
    if current is None:
        destination = str(departure.get("to_club_name") or "")
        current = {
            "club_id": departure.get("to_club_id"),
            "club_name": destination or None,
            "parent_club_name": None,
            "league": None,
            "country": None,
            "league_tier": None,
            "status": "free_agent" if destination.casefold() == "free agent" else "unknown",
            "source": "register_destination",
            "coverage": "historical",
        }
    context = club_context(
        club_id=str(current.get("club_id") or "") or None,
        club_name=current.get("club_name"),
        teams=teams,
        markets=markets,
        rival_ids=tuple(
            str(item.get("club_id"))
            for item in (config.get("rivals") or [])
            if item.get("club_id")
        )
        or RIVAL_IDS,
    )
    current.update(context)
    current["status"] = current.get("status") or "at_club"
    current["rival_current"] = bool(
        current.get("is_rival") and current.get("coverage") == "current"
    )
    current["as_of"] = current_season
    rival_spells = _rival_spells(
        rows,
        current=current,
        departure=departure,
        teams=teams,
        markets=markets,
        rival_ids=tuple(
            str(item.get("club_id"))
            for item in (config.get("rivals") or [])
            if item.get("club_id")
        )
        or RIVAL_IDS,
    )
    return {
        "status": status,
        "coverage_note": (
            "Provider seasons after the departure; missing seasons are gaps, not zero."
        ),
        "seasons_expected": len(expected),
        "seasons_with_data": len(present),
        "first_season": present[0] if present else None,
        "last_season": present[-1] if present else None,
        "totals": {
            "seasons_expected": len(expected),
            "seasons_with_data": len(present),
            "appearances": total("appearances"),
            "starts": total("starts"),
            "minutes": total("minutes"),
            "goals": total("goals"),
            "assists": total("assists"),
        },
        "clubs": [
            {"club": club, "minutes": minutes}
            for club, minutes in sorted(clubs.items(), key=lambda item: -item[1])
            if minutes > 0
        ],
        "countries": [
            {"country": country, "minutes": minutes}
            for country, minutes in sorted(countries.items(), key=lambda item: -item[1])
            if minutes > 0
        ],
        "current": current,
        "top_flight": (
            True
            if current.get("league_tier") == 1
            else (False if current.get("league_tier") is not None else None)
        ),
        "top_flight_abroad": (
            True
            if current.get("league_tier") == 1
            and current.get("country")
            and str(current.get("country")).casefold() != "scotland"
            else (
                False
                if current.get("league_tier") is not None and current.get("country")
                else None
            )
        ),
        "at_rival": bool(rival_spells),
        "rival_current": bool(current.get("rival_current")),
        "rival_spells": rival_spells,
    }


def vs_aberdeen_record(
    appearances: list[dict[str, Any]],
    match_stats: list[dict[str, Any]],
    *,
    player_key: str,
    after: str | None,
) -> dict[str, Any]:
    cutoff = _date(after)
    rows = [
        row
        for row in appearances
        if str(row.get("player_key") or "") == player_key
        and _norm(row.get("opponent")) == "aberdeen"
        and (cutoff is None or (_date(row.get("date")) or date.min) > cutoff)
    ]
    stats = {
        int(row["fixture_id"]): row
        for row in match_stats
        if str(row.get("player_key") or "") == player_key
        and row.get("fixture_id") is not None
    }
    stat_rows = [
        stats[int(row["fixture_id"])]
        for row in rows
        if row.get("fixture_id") is not None and int(row["fixture_id"]) in stats
    ]
    return {
        "coverage": "measured" if rows else "unavailable",
        "appearances": sum(
            1 for row in rows if bool(row.get("started")) or int(row.get("minutes") or 0) > 0
        ),
        "starts": sum(1 for row in rows if bool(row.get("started"))),
        "minutes": sum(int(row.get("minutes") or 0) for row in rows),
        "goals": _sum_or_none(stat_rows, "goals"),
        "assists": _sum_or_none(stat_rows, "assists"),
        "note": "Aberdeen fixtures after the departure in the covered record only.",
    }


def _fee_anchor(
    fee_events: list[dict[str, Any]],
    *,
    clause: dict[str, Any],
    event: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if event is None:
        return None
    event_date = str(event.get("date") or "")[:10]
    teams = event.get("teams") or {}
    destination = _norm((teams.get("in") or {}).get("name"))
    for row in fee_events:
        if str(row.get("clause_id") or "") != str(clause.get("clause_id") or ""):
            continue
        if str(row.get("player_key") or "") != str(clause.get("player_key") or ""):
            continue
        if str(row.get("subsequent_transfer_date") or "")[:10] != event_date:
            continue
        if destination and _norm(row.get("to_club_name")) != destination:
            continue
        return row
    return None


def sell_on_watch(
    clauses: list[dict[str, Any]],
    transfer_rows: list[dict[str, Any]],
    events_by_key: dict[str, list[dict[str, Any]]],
    fee_events: list[dict[str, Any]],
    *,
    config: dict[str, Any],
) -> dict[str, Any]:
    rows_by_id = {str(row.get("transfer_id")): row for row in transfer_rows}
    sell_on_policy = config.get("sell_on") or {}
    fx = sell_on_policy.get("fx_to_gbp") or {"GBP": 1.0}
    allowed_basis = set(
        sell_on_policy.get("allowed_basis") or ["gross_fee", "profit"]
    )
    require_percentage = bool(sell_on_policy.get("require_percentage", True))
    require_public_fee = bool(sell_on_policy.get("require_public_fee", True))
    watch: list[dict[str, Any]] = []
    computed = missing = not_triggered = no_sale = unknown = 0
    known_receipts: list[float] = []
    for clause in clauses:
        player_key = str(clause.get("player_key") or "")
        events = events_by_key.get(player_key, [])
        sale_date = _date(clause.get("sale_date"))
        buyer = str(clause.get("buyer_club_name") or "")
        event = subsequent_permanent_transfer(events, after=sale_date, from_club_name=buyer)
        event_kind = (
            str(event.get("kind") or parse_transfer_type(event.get("type")))
            if event
            else None
        )
        event_out: dict[str, Any] | None = None
        if event:
            teams = event.get("teams") or {}
            incoming = teams.get("in") or {}
            outgoing = teams.get("out") or {}
            event_out = {
                "date": str(event.get("date") or "")[:10],
                "from_club_name": outgoing.get("name"),
                "to_club_name": incoming.get("name"),
                "kind": event_kind,
                "fee_status": "unknown",
                "fee_display": None,
                "source_urls": [],
            }
        if event is None:
            not_triggered += 1
            event_status = "not_triggered"
        elif event_kind in {"free", "free_agent"} or (
            event_out and str(event_out.get("to_club_name") or "").casefold() == "free agent"
        ):
            no_sale += 1
            event_status = "no_sale"
        else:
            event_status = "detected_unpriced"
        anchor = _fee_anchor(fee_events, clause=clause, event=event)
        if anchor and event_out:
            event_out["fee_status"] = anchor.get("fee_status")
            event_out["fee_display"] = (
                f"{anchor.get('fee_currency') or 'GBP'} {anchor.get('fee_amount')}"
                if anchor.get("fee_amount") is not None
                else None
            )
            event_out["source_urls"] = anchor.get("source_urls") or []
            if anchor.get("fee_status") in {"disclosed", "reported"} and anchor.get(
                "fee_amount"
            ) is not None:
                event_status = "detected_priced"
        receipt_status = "not_triggered"
        missing_inputs: list[str] = []
        receipt: dict[str, Any] | None = None
        if event_status in {"detected_unpriced", "detected_priced"}:
            clause_evidenced = bool(clause.get("source_urls")) and str(
                clause.get("confidence") or ""
            ) in {"confirmed", "reported"}
            pct = clause.get("sell_on_pct")
            basis = str(clause.get("basis") or "unknown")
            if not clause_evidenced:
                missing_inputs.append("clause_not_evidenced")
            if require_percentage and pct is None:
                missing_inputs.append("percentage")
            if basis not in allowed_basis:
                missing_inputs.append("basis")
            subsequent_fee = None
            subsequent_currency = "GBP"
            if (
                anchor
                and anchor.get("fee_status") in {"disclosed", "reported"}
                and anchor.get("fee_amount") is not None
            ):
                subsequent_fee = float(anchor["fee_amount"])
                subsequent_currency = str(anchor.get("fee_currency") or "GBP")
            if require_public_fee and subsequent_fee is None:
                missing_inputs.append("subsequent_fee")
            original_fee = None
            if basis == "profit":
                original = rows_by_id.get(str(clause.get("transfer_id") or ""))
                if original and original.get("fee_status") in {"disclosed", "reported"}:
                    amount, _currency, _note = parse_fee(original, fx=fx)
                    original_fee = amount
                if original_fee is None:
                    missing_inputs.append("original_fee")
            if missing_inputs:
                receipt_status = "missing_inputs"
                missing += 1
            else:
                rate = float(fx.get(subsequent_currency, 1.0))
                fee_gbp = float(subsequent_fee or 0.0) * rate
                if basis == "gross_fee":
                    value = fee_gbp * float(pct or 0.0) / 100.0
                else:
                    value = (
                        max(0.0, fee_gbp - float(original_fee or 0.0))
                        * float(pct or 0.0)
                        / 100.0
                    )
                value = round(value, -3)
                receipt = {
                    "status": "computed",
                    "receipt_gbp": value,
                    "gross_fee_gbp": round(fee_gbp, -3),
                    "original_fee_gbp": round(float(original_fee), -3)
                    if original_fee is not None
                    else None,
                    "profit_gbp": round(fee_gbp - float(original_fee or 0.0), -3)
                    if basis == "profit"
                    else None,
                    "currency": "GBP",
                    "method": (
                        "pct * subsequent fee"
                        if basis == "gross_fee"
                        else "pct * max(0, subsequent fee - original fee)"
                    ),
                    "inputs": {
                        "sell_on_pct": pct,
                        "basis": basis,
                        "subsequent_fee": subsequent_fee,
                        "subsequent_currency": subsequent_currency,
                        "original_fee": original_fee,
                    },
                    "missing_inputs": [],
                    "confidence": clause.get("confidence"),
                }
                computed += 1
                known_receipts.append(value)
        elif event_status == "not_triggered":
            receipt_status = "not_triggered"
        elif event_status == "no_sale":
            receipt_status = "no_sale"
        else:
            unknown += 1
            receipt_status = "unknown"
        watch.append(
            {
                **clause,
                "event": event_out,
                "event_status": event_status,
                "receipt": receipt
                or {
                    "status": receipt_status,
                    "receipt_gbp": None,
                    "gross_fee_gbp": None,
                    "original_fee_gbp": None,
                    "profit_gbp": None,
                    "currency": "GBP",
                    "method": None,
                    "inputs": {},
                    "missing_inputs": missing_inputs,
                    "confidence": clause.get("confidence"),
                },
            }
        )
    total_receipt = round(sum(known_receipts), -3) if known_receipts else None
    return {
        "clauses": watch,
        "summary": {
            "total": len(watch),
            "computed": computed,
            "missing_inputs": missing,
            "not_triggered": not_triggered,
            "no_sale": no_sale,
            "unknown": unknown,
            "known_receipts_gbp": total_receipt,
            "unavailable_count": len(watch) - computed,
            "note": (
                "Only publicly evidenced receipts are computed. Zero computed is "
                "not zero future income."
            ),
        },
    }


def development_summary(
    players: list[dict[str, Any]], *, config: dict[str, Any]
) -> dict[str, Any]:
    development = config.get("development") or {}
    scorecard_config = config.get("scorecard") or {}
    young_max = int(development.get("young_exit_age_max") or 23)
    min_post_minutes = int(scorecard_config.get("min_post_minutes") or 90)
    min_post_seasons = int(scorecard_config.get("min_post_seasons") or 1)

    def cohort(rows: list[dict[str, Any]]) -> dict[str, Any]:
        with_fee = sum(
            1
            for row in rows
            if str((row.get("departure") or {}).get("fee_status") or "")
            in {"disclosed", "reported", "undisclosed"}
            and (row.get("departure") or {}).get("fee_status") != "free"
        )
        free = sum(
            1 for row in rows if str((row.get("departure") or {}).get("fee_status")) == "free"
        )
        post_minutes = sum(
            int(((row.get("post_career") or {}).get("totals") or {}).get("minutes") or 0)
            for row in rows
        )
        return {
            "players": len(rows),
            "with_fee": with_fee,
            "free": free,
            "post_career_minutes": post_minutes,
            "top_flight_abroad": sum(
                1 for row in rows if (row.get("post_career") or {}).get("top_flight_abroad")
            ),
            "at_rival": sum(1 for row in rows if (row.get("post_career") or {}).get("at_rival")),
            "in_covered_feed": sum(
                1
                for row in rows
                if ((row.get("post_career") or {}).get("totals") or {}).get(
                    "seasons_with_data"
                )
            ),
            "with_min_post_minutes": sum(
                1
                for row in rows
                if int(
                    ((row.get("post_career") or {}).get("totals") or {}).get(
                        "minutes"
                    )
                    or 0
                )
                >= min_post_minutes
                and int(
                    ((row.get("post_career") or {}).get("totals") or {}).get(
                        "seasons_with_data"
                    )
                    or 0
                )
                >= min_post_seasons
            ),
        }

    all_rows = players
    young = [
        row
        for row in players
        if row.get("age_at_exit") is not None and row["age_at_exit"] <= young_max
    ]
    developed = [
        row
        for row in players
        if (row.get("aberdeen") or {}).get("developed_here") == "yes"
    ]
    by_season: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"players": 0, "young_exits": 0, "developed_here": 0, "with_fee": 0}
    )
    for row in players:
        season = str((row.get("departure") or {}).get("season") or "")
        bucket = by_season[season]
        bucket["players"] += 1
        if row.get("age_at_exit") is not None and row["age_at_exit"] <= young_max:
            bucket["young_exits"] += 1
        if (row.get("aberdeen") or {}).get("developed_here") == "yes":
            bucket["developed_here"] += 1
        if (row.get("departure") or {}).get("fee_status") in {
            "disclosed",
            "reported",
            "undisclosed",
        }:
            bucket["with_fee"] += 1
    return {
        "definitions": {
            "young_exit_age_max": young_max,
            "debut_age_max": int(development.get("debut_age_max") or 21),
            "min_starts": int(development.get("min_starts") or 10),
            "min_post_minutes": min_post_minutes,
            "min_post_seasons": min_post_seasons,
            "note": "Descriptive cohorts; not an academy register or a model score.",
        },
        "cohorts": {
            "all": cohort(all_rows),
            "young": cohort(young),
            "developed_here": cohort(developed),
        },
        "by_exit_season": [
            {"season": season, **values}
            for season, values in sorted(by_season.items(), reverse=True)
        ],
        "note": (
            "These are descriptive indicators. A later career does not prove a sale "
            "was wrong, and a fee does not prove the sale was sportingly costless."
        ),
    }


def former_anchor(player_key: str) -> str:
    prefix, _, value = player_key.partition(":")
    if prefix == "api" and value.startswith("player:"):
        return f"former-{value.split(':', 1)[1]}"
    return f"former-{slugify(player_key)}"


__all__ = [
    "RIVAL_IDS",
    "aberdeen_record",
    "arrival_for",
    "club_context",
    "development_summary",
    "former_anchor",
    "former_player_rows",
    "last_playing_season",
    "post_career_record",
    "sell_on_watch",
    "vs_aberdeen_record",
]
