"""Inferred transfer-fee and market-value ranges.

Aberdeen's fees are usually undisclosed. This module does not pretend to know
them. It separates:

- disclosed/reported fees, which carry a public source;
- free transfers, where the fee is zero but the player still has a value;
- loans, where the loan fee is unknown;
- modelled ranges for everything else.

The model is deliberately simple and transparent: a market/position base,
an age curve, and a calibration factor from the reported/disclosed anchors.
Every modelled output is a range with a confidence label, never a point
estimate presented as fact.
"""

from __future__ import annotations

import re
from datetime import date
from statistics import median
from typing import Any

from fitba.analytics.recruitment import market_for

POSITION_GROUP = {
    "Goalkeeper": "GK",
    "Defender": "DEF",
    "Midfielder": "MID",
    "Attacker": "FWD",
}
BASE_VALUE_M = {
    "scotland": {"GK": 0.15, "DEF": 0.18, "MID": 0.22, "FWD": 0.25, "UNK": 0.20},
    "england": {"GK": 0.25, "DEF": 0.35, "MID": 0.40, "FWD": 0.50, "UNK": 0.35},
    "europe": {"GK": 0.20, "DEF": 0.30, "MID": 0.35, "FWD": 0.45, "UNK": 0.30},
    "other": {"GK": 0.10, "DEF": 0.15, "MID": 0.18, "FWD": 0.22, "UNK": 0.15},
    "unknown": {"GK": 0.10, "DEF": 0.15, "MID": 0.18, "FWD": 0.22, "UNK": 0.15},
}
POSITION_FACTOR = {"GK": 0.80, "DEF": 0.90, "MID": 1.00, "FWD": 1.15, "UNK": 0.90}
FX_TO_GBP = {"GBP": 1.0, "EUR": 0.85, "USD": 0.78}
FEE_RE = re.compile(
    r"(?P<symbol>£|€|\$|GBP|EUR|USD)?\s*(?P<number>\d[\d,.]*)\s*(?P<suffix>[KkMm])?",
    re.IGNORECASE,
)
SYMBOL_CURRENCY = {"£": "GBP", "€": "EUR", "$": "USD"}
CURRENCY_WORDS = {"GBP": "GBP", "EUR": "EUR", "USD": "USD"}


def position_group(position: Any) -> str:
    return POSITION_GROUP.get(str(position or ""), "UNK")


def _date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def age_at(birth_date: Any, on: Any) -> int | None:
    born = _date(birth_date)
    when = _date(on)
    if born is None or when is None:
        return None
    return when.year - born.year - ((when.month, when.day) < (born.month, born.day))


def age_factor(age: int | None) -> float:
    if age is None:
        return 1.0
    if age <= 18:
        return 0.50
    if age <= 20:
        return 0.70
    if age <= 23:
        return 0.90
    if age <= 27:
        return 1.00
    if age <= 29:
        return 0.80
    if age <= 31:
        return 0.55
    return 0.30


def parse_fee(
    row: dict[str, Any], *, fx: dict[str, float] | None = None
) -> tuple[float | None, str | None, str | None]:
    """Return (GBP amount, currency, note) for a disclosed/reported fee."""
    rates = {**FX_TO_GBP, **(fx or {})}
    status = str(row.get("fee_status") or "")
    if status == "free":
        return 0.0, "GBP", "Free transfer; no fee."
    if status == "loan":
        return None, None, "Loan fee is not public."
    amount = row.get("fee_amount")
    currency = str(row.get("fee_currency") or "GBP").upper()
    if status == "disclosed" and amount is not None:
        return round(float(amount) * rates.get(currency, 1.0), -3), currency, None
    raw = str(row.get("fee_raw") or "")
    if not raw:
        return None, None, None
    match = FEE_RE.search(raw)
    if not match:
        return None, None, None
    symbol = (match.group("symbol") or "").upper()
    if symbol in SYMBOL_CURRENCY:
        currency = SYMBOL_CURRENCY[symbol]
    elif symbol in CURRENCY_WORDS:
        currency = CURRENCY_WORDS[symbol]
    else:
        currency = "GBP"
    try:
        value = float(match.group("number").replace(",", ""))
    except ValueError:
        return None, None, None
    suffix = (match.group("suffix") or "").casefold()
    if suffix == "k":
        value *= 1_000
    elif suffix == "m":
        value *= 1_000_000
    return round(value * rates.get(currency, 1.0), -3), currency, raw


def base_value_gbp(market: str, position: str, age: int | None) -> float:
    group = POSITION_GROUP.get(position, "UNK")
    base = BASE_VALUE_M.get(market, BASE_VALUE_M["unknown"]).get(group, 0.25)
    return base * 1_000_000 * POSITION_FACTOR.get(group, 0.9) * age_factor(age)


def calibration_factor(
    rows: list[dict[str, Any]],
    *,
    birth_dates: dict[str, str],
    markets: list[dict[str, Any]],
    fx: dict[str, float] | None = None,
) -> tuple[float, int]:
    """Median ratio of reported fee to the base model, from public anchors."""
    by_id, by_name = _market_maps(markets)
    ratios: list[float] = []
    for row in rows:
        if row.get("transfer_kind") not in {"permanent", "free"}:
            continue
        if row.get("direction") not in {"in", "out"}:
            continue
        amount, _currency, _note = parse_fee(row, fx=fx)
        if amount is None or amount <= 0:
            continue
        position = str(row.get("position") or "")
        group = POSITION_GROUP.get(position, "UNK")
        if group == "UNK":
            continue
        market = market_for(
            row.get("from_club_id") if row.get("direction") == "in" else row.get("to_club_id"),
            row.get("from_club_name") if row.get("direction") == "in" else row.get("to_club_name"),
            by_id=by_id,
            by_name=by_name,
        )
        age = age_at(
            birth_dates.get(str(row.get("player_key") or "")),
            row.get("date_effective"),
        )
        base = base_value_gbp(market, position, age)
        if base > 0:
            ratios.append(amount / base)
    if len(ratios) < 2:
        return 1.0, len(ratios)
    factor = median(ratios)
    return max(0.50, min(2.0, factor)), len(ratios)


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


def _round_range(value: float) -> tuple[float, float]:
    step = 25_000 if value < 1_000_000 else 100_000
    low = max(0.0, round((value * 0.6) / step) * step)
    high = round((value * 1.6) / step) * step
    if high <= low:
        high = low + step
    return low, high


def estimate_transfer(
    row: dict[str, Any],
    *,
    birth_dates: dict[str, str],
    markets: list[dict[str, Any]],
    calibration: float,
    fx: dict[str, float] | None = None,
) -> dict[str, Any]:
    by_id, by_name = _market_maps(markets)
    direction = str(row.get("direction") or "")
    market = market_for(
        row.get("from_club_id") if direction == "in" else row.get("to_club_id"),
        row.get("from_club_name") if direction == "in" else row.get("to_club_name"),
        by_id=by_id,
        by_name=by_name,
    )
    position = str(row.get("position") or "")
    group = POSITION_GROUP.get(position, "UNK")
    age = age_at(
        birth_dates.get(str(row.get("player_key") or "")),
        row.get("date_effective"),
    )
    amount, currency, reported_note = parse_fee(row, fx=fx)
    model_value = base_value_gbp(market, position, age) * calibration
    low, high = _round_range(model_value)
    confidence = "low"
    if age is not None and group != "UNK" and market != "unknown":
        confidence = "medium"
    if row.get("fee_status") == "disclosed":
        confidence = "high"
    elif row.get("fee_status") == "loan":
        confidence = "low"
    if amount is not None:
        basis = (
            "free"
            if row.get("fee_status") == "free"
            else ("disclosed" if row.get("fee_status") == "disclosed" else "reported")
        )
        fee_low = fee_high = amount
        method = "public_source"
    elif row.get("fee_status") == "loan":
        basis = "loan"
        fee_low = fee_high = None
        method = "loan_fee_unknown"
    else:
        basis = "modelled"
        fee_low, fee_high = low, high
        method = "age_position_market_model"
    return {
        "basis": basis,
        "currency": "GBP",
        "fee_low_gbp": fee_low,
        "fee_high_gbp": fee_high,
        "market_value_low_gbp": low,
        "market_value_high_gbp": high,
        "confidence": confidence,
        "method": method,
        "reported_currency": currency,
        "reported_note": reported_note,
        "source_urls": list(row.get("source_urls") or []) if amount is not None else [],
        "note": (
            "Public fee."
            if amount is not None and basis != "free"
            else "Free transfer; fee is zero."
            if basis == "free"
            else "Loan fee not public; value range is a proxy."
            if basis == "loan"
            else "Inferred range from age, position, market and reported-fee anchors."
        ),
    }


def summarise_valuations(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate fee ranges for permanent/free moves; loans are separate.

    Per-row ranges remain on the cards. For the aggregate we use the midpoint of
    modelled rows plus a portfolio band, rather than adding every row's low and
    high extremes (which would produce an implausibly wide net range).
    """
    spend_mid = income_mid = modelled_gross = 0.0
    counts = {"disclosed": 0, "reported": 0, "modelled": 0, "free": 0, "loan": 0, "unknown": 0}
    for row in rows:
        estimate = row.get("fee_estimate") or {}
        basis = str(estimate.get("basis") or "unknown")
        counts[basis] = counts.get(basis, 0) + 1
        if row.get("transfer_kind") == "loan" or basis == "loan":
            continue
        low = estimate.get("fee_low_gbp")
        high = estimate.get("fee_high_gbp")
        if low is None or high is None:
            counts["unknown"] += 1
            continue
        midpoint = (float(low) + float(high)) / 2
        if basis == "modelled":
            modelled_gross += abs(midpoint)
        if row.get("direction") == "in":
            spend_mid += midpoint
        elif row.get("direction") == "out":
            income_mid += midpoint
    permanent = sum(counts[key] for key in ("disclosed", "reported", "modelled", "free"))
    known = counts["disclosed"] + counts["reported"]
    confidence = "low"
    if permanent and known / permanent >= 0.7:
        confidence = "high"
    elif permanent and (known + counts["modelled"]) / permanent >= 0.7:
        confidence = "medium"
    net_mid = spend_mid - income_mid
    band = 0.20 * modelled_gross
    return {
        "currency": "GBP",
        "fee_low_gbp": round(net_mid - band),
        "fee_high_gbp": round(net_mid + band),
        "spend_low_gbp": round(max(0.0, spend_mid - 0.20 * modelled_gross)),
        "spend_high_gbp": round(spend_mid + 0.20 * modelled_gross),
        "income_low_gbp": round(max(0.0, income_mid - 0.20 * modelled_gross)),
        "income_high_gbp": round(income_mid + 0.20 * modelled_gross),
        "confidence": confidence,
        "counts": counts,
        "note": (
            "Estimated net spend range from public/reported fees and a transparent "
            "model. The aggregate uses modelled midpoints with a 20% portfolio band "
            "on modelled gross flows, not the sum of every row's extremes. Free "
            "transfers count as zero fee; loan fees are excluded. Negative means "
            "income exceeds spend. Not an audited balance."
        ),
    }


__all__ = [
    "BASE_VALUE_M",
    "FX_TO_GBP",
    "POSITION_GROUP",
    "age_at",
    "base_value_gbp",
    "calibration_factor",
    "estimate_transfer",
    "parse_fee",
    "position_group",
    "summarise_valuations",
]
