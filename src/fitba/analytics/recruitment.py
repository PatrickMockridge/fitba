"""Recruitment aggregates for the historical record.

The transfer row remains the canonical fact; this module only derives season
counts, disclosed-fee totals, source-market mix and age-at-arrival coverage.
Disclosed fees are never presented as complete net spend.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from statistics import mean, median
from typing import Any

MARKET_ORDER = ("scotland", "england", "europe", "other", "unknown")


def _date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _age_at(birth: Any, on: date | None) -> int | None:
    born = _date(birth)
    if born is None or on is None:
        return None
    return on.year - born.year - ((on.month, on.day) < (born.month, born.day))


def _market_maps(markets: list[dict[str, Any]]) -> tuple[dict[str, str], dict[str, str]]:
    by_id: dict[str, str] = {}
    by_name: dict[str, str] = {}
    for entry in markets:
        market = str(entry.get("market") or "unknown")
        if entry.get("club_id"):
            by_id[str(entry["club_id"])] = market
        if entry.get("club_name"):
            by_name[str(entry["club_name"]).casefold()] = market
    return by_id, by_name


def market_for(
    club_id: str | None,
    club_name: str | None,
    *,
    by_id: dict[str, str],
    by_name: dict[str, str],
) -> str:
    if club_id and club_id in by_id:
        return by_id[club_id]
    if club_name and club_name.casefold() in by_name:
        return by_name[club_name.casefold()]
    if club_id and club_id.startswith("sco:"):
        if club_id.startswith("sco:provisional-") or club_id == "sco:free-agent":
            return "unknown"
        return "scotland"
    if club_id and club_id.startswith("eng:"):
        return "england"
    return "unknown"


def recruitment_profile(
    transfers: list[dict[str, Any]],
    *,
    season: str,
    markets: list[dict[str, Any]] | None = None,
    birth_dates: dict[str, Any] | None = None,
    coverage: str = "curated_partial",
) -> dict[str, Any]:
    """Derive the season's recruitment aggregates from published transfer rows."""
    rows = [row for row in transfers if str(row.get("season")) == str(season)]
    arrivals = [row for row in rows if row.get("direction") == "in"]
    departures = [row for row in rows if row.get("direction") == "out"]
    permanent_in = [row for row in arrivals if row.get("transfer_kind") == "permanent"]
    permanent_out = [row for row in departures if row.get("transfer_kind") == "permanent"]
    loans_in = [row for row in arrivals if row.get("transfer_kind") == "loan"]
    loans_out = [row for row in departures if row.get("transfer_kind") == "loan"]
    free_in = [row for row in arrivals if row.get("transfer_kind") == "free"]
    free_out = [row for row in departures if row.get("transfer_kind") == "free"]
    disclosed_in = [
        row
        for row in arrivals
        if row.get("fee_status") == "disclosed" and row.get("fee_amount") is not None
    ]
    disclosed_out = [
        row
        for row in departures
        if row.get("fee_status") == "disclosed" and row.get("fee_amount") is not None
    ]
    spend = sum(float(row["fee_amount"]) for row in disclosed_in)
    income = sum(float(row["fee_amount"]) for row in disclosed_out)
    undisclosed = sum(
        1
        for row in rows
        if row.get("transfer_kind") == "permanent" and row.get("fee_status") != "disclosed"
    )
    by_id, by_name = _market_maps(markets or [])
    market_counts: Counter[str] = Counter()
    for row in arrivals:
        market_counts[
            market_for(
                row.get("from_club_id"),
                row.get("from_club_name"),
                by_id=by_id,
                by_name=by_name,
            )
        ] += 1
    ages: list[int] = []
    birth_dates = birth_dates or {}
    for row in arrivals:
        key = str(row.get("player_key") or "")
        age = _age_at(birth_dates.get(key), _date(row.get("date_effective")))
        if age is not None:
            ages.append(age)
    age_bands: Counter[str] = Counter()
    for age in ages:
        if age < 21:
            age_bands["u21"] += 1
        elif age < 25:
            age_bands["21-24"] += 1
        elif age < 30:
            age_bands["25-29"] += 1
        else:
            age_bands["30+"] += 1
    top_clubs = Counter(
        str(row.get("from_club_name") or "Unknown") for row in arrivals
    ).most_common(5)
    return {
        "season": season,
        "coverage": coverage,
        "arrivals": len(arrivals),
        "departures": len(departures),
        "permanent_in": len(permanent_in),
        "permanent_out": len(permanent_out),
        "loans_in": len(loans_in),
        "loans_out": len(loans_out),
        "free_in": len(free_in),
        "free_out": len(free_out),
        "disclosed_spend": spend,
        "disclosed_income": income,
        "disclosed_net": (spend - income) if (disclosed_in or disclosed_out) else None,
        "disclosed_count": len(disclosed_in) + len(disclosed_out),
        "undisclosed_count": undisclosed,
        "market_mix": [
            {
                "market": market,
                "arrivals": market_counts.get(market, 0),
                "share": round(market_counts.get(market, 0) / len(arrivals), 3)
                if arrivals
                else None,
            }
            for market in MARKET_ORDER
        ],
        "market_unknown_count": market_counts.get("unknown", 0),
        "age_coverage": round(len(ages) / len(arrivals), 3) if arrivals else None,
        "median_age": round(median(ages), 1) if ages else None,
        "average_age": round(mean(ages), 1) if ages else None,
        "age_bands": {key: age_bands.get(key, 0) for key in ("u21", "21-24", "25-29", "30+")},
        "top_source_clubs": [{"club": club, "arrivals": count} for club, count in top_clubs],
        "note": (
            "Disclosed fees only. Undisclosed is never zero and is excluded from "
            "the totals. Age is shown only where a birth date is known."
        ),
    }


def era_recruitment_profile(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate the season recruitment profiles without inventing fees."""
    usable = [profile for profile in profiles if profile]
    if not usable:
        return {"seasons": 0}
    spend = sum(float(profile.get("disclosed_spend") or 0) for profile in usable)
    income = sum(float(profile.get("disclosed_income") or 0) for profile in usable)
    disclosed_count = sum(int(profile.get("disclosed_count") or 0) for profile in usable)
    undisclosed = sum(int(profile.get("undisclosed_count") or 0) for profile in usable)
    arrivals = sum(int(profile.get("arrivals") or 0) for profile in usable)
    departures = sum(int(profile.get("departures") or 0) for profile in usable)
    market_totals: Counter[str] = Counter()
    unknown = 0
    for profile in usable:
        unknown += int(profile.get("market_unknown_count") or 0)
        for item in profile.get("market_mix") or []:
            market_totals[str(item.get("market"))] += int(item.get("arrivals") or 0)
    return {
        "seasons": len(usable),
        "arrivals": arrivals,
        "departures": departures,
        "disclosed_spend": spend,
        "disclosed_income": income,
        "disclosed_net": (spend - income) if disclosed_count else None,
        "disclosed_count": disclosed_count,
        "undisclosed_count": undisclosed,
        "market_mix": [
            {
                "market": market,
                "arrivals": market_totals.get(market, 0),
                "share": round(market_totals.get(market, 0) / arrivals, 3) if arrivals else None,
            }
            for market in MARKET_ORDER
        ],
        "market_unknown_count": unknown,
        "note": "Disclosed fees only; pre-2024 windows are curated partial.",
    }


__all__ = [
    "MARKET_ORDER",
    "era_recruitment_profile",
    "market_for",
    "recruitment_profile",
]
