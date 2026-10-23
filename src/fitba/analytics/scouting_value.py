"""Anchor-backed player value model for the scouting pool.

The value index (in ``fitba.analytics.scouting``) is a scouting ordering, not a
currency value. This module owns the public-source anchor register and the fit
that is allowed to publish a GBP band only when the register passes the gate.

No market-value feed is licensed. The register is curated from official club or
league announcements and Wikipedia season records, one source at a time, with a
URL and a verified date. If the gate is not met, no GBP band is published.
"""

from __future__ import annotations

import math
from collections import Counter
from datetime import date
from pathlib import Path
from statistics import NormalDist, mean
from typing import Any

import polars as pl

from fitba.analytics.scouting import midrank_percentile
from fitba.analytics.valuation import parse_fee
from fitba.settings import (
    NORMALIZED_DIR,
    REFERENCE_DIR,
    load_yaml,
    scouting_leagues,
    scouting_value,
)
from fitba.settings import (
    transfers as transfer_rows,
)

ANCHORS_PATH = REFERENCE_DIR / "scouting_values.yaml"
ALLOWED_SOURCE_IDS = {"club_official", "league_official", "wikipedia"}
PROHIBITED_HOSTS = {
    "transfermarkt",
    "transfermarkt.co.uk",
    "transfermarkt.com",
    "fotmob",
    "sofascore",
    "fbref",
    "bbc.co.uk",
    "bbc.com",
}
ROLE_GROUPS = {
    "goalkeeper": "GK",
    "centre_back": "DEF",
    "full_back": "DEF",
    "wing_back": "DEF",
    "defensive_midfield": "MID",
    "central_midfield": "MID",
    "attacking_midfield": "MID",
    "wide_midfield": "MID",
    "wide_forward": "FWD",
    "centre_forward": "FWD",
}
AGE_BANDS = ((0, 20), (21, 23), (24, 27), (28, 30), (31, 120))


def _load_anchors() -> list[dict[str, Any]]:
    if not ANCHORS_PATH.exists():
        return []
    document = load_yaml(ANCHORS_PATH) or {}
    return list(document.get("anchors") or [])


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _host_allowed(url: str | None) -> bool:
    if not url or not str(url).startswith("https://"):
        return False
    host = str(url).split("://", 1)[1].split("/", 1)[0].lower().removeprefix("www.")
    return not any(host == blocked or host.endswith("." + blocked) for blocked in PROHIBITED_HOSTS)


def _season_for_date(value: date) -> str:
    start = value.year if value.month >= 7 else value.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def _season_start(season: str) -> int | None:
    try:
        return int(str(season).split("-", 1)[0])
    except (TypeError, ValueError):
        return None


def _time_aligned(anchor: dict[str, Any]) -> bool:
    value_date = _parse_date(anchor.get("value_date"))
    season = str(anchor.get("performance_season") or "")
    start = _season_start(season)
    if value_date is None or start is None:
        return False
    season_of_value = _season_for_date(value_date)
    allowed = {season_of_value}
    value_start = _season_start(season_of_value)
    if value_start is not None and value_date.month in {6, 7, 8}:
        allowed.add(f"{value_start - 1}-{str(value_start)[-2:]}")
    return season in allowed


def validate_anchor(anchor: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    player_key = str(anchor.get("player_key") or "")
    if not player_key.startswith("api:player:"):
        errors.append("player_key must be an api:player:<id> key")
    if not anchor.get("player_name"):
        errors.append("missing player_name")
    if not anchor.get("league_id"):
        errors.append("missing league_id")
    if anchor.get("role_family") not in ROLE_GROUPS:
        errors.append("unknown role_family")
    value = anchor.get("value_gbp")
    if not isinstance(value, (int, float)) or value <= 0:
        errors.append("value_gbp must be positive")
    if anchor.get("value_kind") not in {"fee", "market_value"}:
        errors.append("value_kind must be fee or market_value")
    if _parse_date(anchor.get("value_date")) is None:
        errors.append("invalid value_date")
    if not _time_aligned(anchor):
        errors.append("value_date and performance_season do not align")
    if anchor.get("source_id") not in ALLOWED_SOURCE_IDS:
        errors.append("source_id is not an allowed public source")
    if not _host_allowed(anchor.get("source_url")):
        errors.append("source_url is missing or on a prohibited host")
    if _parse_date(anchor.get("verified_at")) is None:
        errors.append("invalid verified_at")
    minutes = anchor.get("performance_minutes")
    if not isinstance(minutes, (int, float)) or minutes <= 0:
        errors.append("performance_minutes must be positive")
    rating = anchor.get("performance_rating")
    if not isinstance(rating, (int, float)) or not 0 < rating <= 10:
        errors.append("performance_rating must be in (0, 10]")
    return errors


def _league_tiers() -> dict[str, int]:
    return {
        str(item.get("id")): int(item.get("tier") or 99)
        for item in (scouting_leagues().get("pool") or [])
    }


def _age_band(age: int) -> str:
    for low, high in AGE_BANDS:
        if low <= age <= high:
            return f"{low}-{high}"
    return "unknown"


def anchor_report(anchors: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    items = anchors if anchors is not None else _load_anchors()
    config = scouting_value().get("fit") or {}
    tiers = _league_tiers()
    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for anchor in items:
        problems = validate_anchor(anchor)
        if problems:
            invalid.append({"player_key": anchor.get("player_key"), "errors": problems})
        else:
            valid.append(anchor)
    role_counts = Counter(ROLE_GROUPS.get(str(anchor.get("role_family"))) for anchor in valid)
    tier_counts = Counter(tiers.get(str(anchor.get("league_id")), 99) for anchor in valid)
    age_counts = Counter(_age_band(int(anchor.get("age_at_value") or 0)) for anchor in valid)
    top_tier = sum(count for tier, count in tier_counts.items() if tier <= 2)
    top_share = top_tier / len(valid) if valid else 0.0
    gate = {
        "min_anchors": int(config.get("min_anchors") or 60),
        "anchor_count": len(valid),
        "min_role_anchors": int(config.get("min_role_anchors") or 5),
        "role_counts": dict(role_counts),
        "role_pass": all(
            role_counts.get(group, 0) >= int(config.get("min_role_anchors") or 5)
            for group in ("GK", "DEF", "MID", "FWD")
        ),
        "league_tiers": len(tier_counts),
        "min_league_tiers": int(config.get("min_league_tiers") or 3),
        "tier_pass": len(tier_counts) >= int(config.get("min_league_tiers") or 3),
        "age_bands": len(age_counts),
        "min_age_bands": int(config.get("min_age_bands") or 3),
        "age_pass": len(age_counts) >= int(config.get("min_age_bands") or 3),
        "top_tier_share": round(top_share, 3),
        "top_tier_required": float(config.get("top_tier_share") or 0.2),
        "top_tier_pass": top_share >= float(config.get("top_tier_share") or 0.2),
    }
    gate["passed"] = bool(
        len(valid) >= gate["min_anchors"]
        and gate["role_pass"]
        and gate["tier_pass"]
        and gate["age_pass"]
        and gate["top_tier_pass"]
    )
    return {
        "anchors": len(items),
        "usable": len(valid),
        "invalid": invalid,
        "gate": gate,
        "valid": valid,
    }


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float] | None:
    size = len(matrix)
    augmented = [[*row[:], vector[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            return None
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                value - factor * other
                for value, other in zip(augmented[row], augmented[column], strict=True)
            ]
    return [augmented[index][-1] for index in range(size)]


def _features(anchor: dict[str, Any]) -> list[float] | None:
    percentile = anchor.get("performance_adjusted_percentile")
    age = anchor.get("age_at_value")
    minutes = anchor.get("performance_minutes")
    if percentile is None or age is None or not minutes:
        return None
    group = ROLE_GROUPS.get(str(anchor.get("role_family")))
    return [
        1.0,
        float(percentile) / 100.0,
        float(age),
        float(age) ** 2,
        math.log(float(minutes)),
        1.0 if group == "GK" else 0.0,
        1.0 if group == "DEF" else 0.0,
        1.0 if group == "MID" else 0.0,
    ]


def _coefficients(rows: list[tuple[list[float], float]]) -> list[float] | None:
    if len(rows) <= len(rows[0][0]):
        return None
    width = len(rows[0][0])
    xtx = [[0.0] * width for _ in range(width)]
    xty = [0.0] * width
    for features, target in rows:
        for left in range(width):
            xty[left] += features[left] * target
            for right in range(width):
                xtx[left][right] += features[left] * features[right]
    return _solve(xtx, xty)


def _fit(rows: list[tuple[list[float], float]]) -> dict[str, Any] | None:
    coefficients = _coefficients(rows)
    if coefficients is None:
        return None

    def predict(features: list[float], coefs: list[float] | None = None) -> float:
        values = coefs or coefficients
        return sum(coefficient * value for coefficient, value in zip(values, features, strict=True))

    residuals = [target - predict(features) for features, target in rows]
    targets = [target for _, target in rows]
    target_mean = mean(targets)
    total = sum((target - target_mean) ** 2 for target in targets)
    residual_sum = sum(residual * residual for residual in residuals)
    r2 = 1.0 - residual_sum / total if total > 0 else None
    mae = mean(abs(residual) for residual in residuals)
    width = len(rows[0][0])
    sd = math.sqrt(residual_sum / max(1, len(residuals) - width))
    errors: list[float] = []
    for index in range(len(rows)):
        train = rows[:index] + rows[index + 1 :]
        train_coefficients = _coefficients(train)
        if train_coefficients is None:
            errors = []
            break
        errors.append(abs(rows[index][1] - predict(rows[index][0], train_coefficients)))
    return {
        "coefficients": coefficients,
        "in_sample_mae": round(mae, 4),
        "loocv_mae": round(mean(errors), 4) if errors else None,
        "max_loocv_error": round(max(errors), 4) if errors else None,
        "r2": round(r2, 4) if r2 is not None else None,
        "residual_sd": round(sd, 4),
        "sample": len(rows),
        "predict": predict,
    }


def fit_value_model(anchors: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    report = anchor_report(anchors)
    config = scouting_value().get("fit") or {}
    state = "awaiting_anchors"
    model = None
    if report["gate"]["passed"]:
        rows: list[tuple[list[float], float]] = []
        for anchor in report["valid"]:
            features = _features(anchor)
            if features is None:
                continue
            rows.append((features, math.log(float(anchor["value_gbp"]))))
        fitted = _fit(rows)
        if fitted is None:
            state = "fit_failed"
        else:
            state = "ready"
            model = fitted
    vector = (model or {}).get("coefficients") or []
    names = [
        "intercept",
        "adjusted_percentile",
        "age",
        "age_squared",
        "log_minutes",
        "goalkeeper",
        "defender",
        "midfielder",
    ]
    coefficients = {
        name: (round(float(vector[index]), 4) if index < len(vector) else None)
        for index, name in enumerate(names)
    }
    return {
        "state": state,
        "anchor_count": report["anchors"],
        "usable_anchors": report["usable"],
        "gate": report["gate"],
        "sample": (model or {}).get("sample"),
        "coefficients": coefficients if model is not None else None,
        "coefficient_vector": vector if model is not None else None,
        "residual_sd": (model or {}).get("residual_sd"),
        "in_sample_mae": (model or {}).get("in_sample_mae"),
        "loocv_mae": (model or {}).get("loocv_mae"),
        "max_loocv_error": (model or {}).get("max_loocv_error"),
        "r2": (model or {}).get("r2"),
        "interval": float(config.get("interval") or 0.8),
        "index": scouting_value().get("index") or {},
        "limitations": [
            "The GBP band is fitted only from a public-source anchor register; it is "
            "not a fee or a market quote.",
            "Contract length, wages, release clauses and agent fees are unknown.",
            "The performance input is the league-adjusted scouting percentile; the "
            "league adjustment is an empirical model.",
        ],
    }


def _row_features(row: dict[str, Any]) -> list[float] | None:
    percentile = row.get("adjusted_percentile")
    age = row.get("age")
    minutes = row.get("minutes")
    if percentile is None or age is None or not minutes:
        return None
    group = ROLE_GROUPS.get(str(row.get("role_family")))
    return [
        1.0,
        float(percentile) / 100.0,
        float(age),
        float(age) ** 2,
        math.log(float(minutes)),
        1.0 if group == "GK" else 0.0,
        1.0 if group == "DEF" else 0.0,
        1.0 if group == "MID" else 0.0,
    ]


def _round_value(value: float) -> int:
    step = 25_000 if value < 1_000_000 else 100_000
    return max(step, int(round(value / step) * step))


def value_for_row(model: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    """Apply a ready model to one pool row. Null when the gate is not met."""
    vector = model.get("coefficient_vector")
    residual_sd = model.get("residual_sd")
    features = _row_features(row)
    if model.get("state") != "ready" or not vector or residual_sd is None or features is None:
        return {
            "value_low_gbp": None,
            "value_high_gbp": None,
            "value_confidence": "unknown",
            "value_method": "awaiting_anchors",
        }
    prediction = sum(
        float(coefficient) * value for coefficient, value in zip(vector, features, strict=True)
    )
    interval = float(model.get("interval") or 0.8)
    z = NormalDist().inv_cdf(0.5 + interval / 2.0)
    low = math.exp(prediction - z * float(residual_sd))
    high = math.exp(prediction + z * float(residual_sd))
    confidence = "medium" if int(row.get("minutes") or 0) >= 900 else "low"
    return {
        "value_low_gbp": _round_value(low),
        "value_high_gbp": _round_value(high),
        "value_confidence": confidence,
        "value_method": "anchor_regression",
    }


def _history_season_root(season: str) -> Path:
    return NORMALIZED_DIR / "history" / f"season={season}"


def _previous_season(season: str) -> str | None:
    try:
        start = int(str(season).split("-", 1)[0])
    except (TypeError, ValueError):
        return None
    return f"{start - 1}-{str(start)[-2:]}"


def _performance_snapshot(season: str, player_id: int) -> dict[str, Any] | None:
    root = _history_season_root(season)
    stats_path = root / "player_match_stats.parquet"
    if not stats_path.exists():
        return None
    frame = pl.read_parquet(stats_path).filter(pl.col("player_id") == player_id)
    if not frame.height:
        return None
    minutes = int(frame["minutes"].sum() or 0)
    rated = frame.filter(pl.col("rating").is_not_null())
    mean_rating = rated["rating"].mean() if rated.height else None
    rating = round(float(mean_rating), 2) if isinstance(mean_rating, (int, float)) else None
    role_family = None
    appearances = root / "appearances.parquet"
    if appearances.exists():
        roles = pl.read_parquet(appearances).filter(
            (pl.col("player_id") == player_id) & pl.col("role_family").is_not_null()
        )
        if roles.height:
            role_family = (
                roles.group_by("role_family")
                .agg(pl.len().alias("starts"))
                .sort("starts", descending=True)
                .row(0, named=True)["role_family"]
            )
    age = None
    rosters = root / "rosters.parquet"
    if rosters.exists():
        roster = pl.read_parquet(rosters).filter(pl.col("player_id") == player_id)
        if roster.height:
            max_age = roster["age"].max()
            age = int(max_age) if isinstance(max_age, (int, float)) else None
    return {
        "minutes": minutes,
        "rating": rating,
        "role_family": role_family,
        "age": age,
    }


def _premiership_ratings() -> list[float]:
    path = NORMALIZED_DIR / "scouting" / "player_season.parquet"
    if not path.exists():
        return []
    frame = pl.read_parquet(path).filter(
        (pl.col("competition_id") == "sco:premiership")
        & (pl.col("minutes") >= 450)
        & pl.col("rating").is_not_null()
    )
    return [float(value) for value in frame["rating"].to_list()]


def seed_anchors_from_transfers() -> list[dict[str, Any]]:
    """Seed the diagnostic Aberdeen-market spine from the curated register.

    These anchors are historical and use the current Premiership cohort for the
    adjusted percentile. They are labelled and do not satisfy the broad gate.
    """
    cohort = _premiership_ratings()
    anchors: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in transfer_rows().get("transfers") or []:
        fee, _currency, _note = parse_fee(row)
        position = row.get("position")
        player_key = str(row.get("player_key") or "")
        if not fee or not position or not player_key.startswith("api:player:"):
            continue
        player_id = int(player_key.split(":")[-1])
        value_date = _parse_date(row.get("date_effective") or row.get("date_announced"))
        if value_date is None:
            continue
        move_season = str(row.get("season") or "")
        performance_season = move_season
        if value_date.month in {6, 7, 8}:
            performance_season = _previous_season(move_season) or move_season
        snapshot = _performance_snapshot(performance_season, player_id)
        if snapshot is None or snapshot["minutes"] < 450 or snapshot["rating"] is None:
            continue
        sources = row.get("source_urls") or []
        source_url = str(sources[0]) if sources else ""
        if not source_url:
            continue
        role_family = snapshot["role_family"] or {
            "GK": "goalkeeper",
            "DEF": "centre_back",
            "MID": "central_midfield",
            "FWD": "centre_forward",
        }.get(str(position), "central_midfield")
        value_gbp = round(float(fee))
        key = (player_key, value_date.isoformat())
        if key in seen:
            continue
        seen.add(key)
        source_id = "wikipedia" if "wikipedia" in source_url else "club_official"
        anchors.append(
            {
                "player_key": player_key,
                "player_name": row.get("player_name"),
                "league_id": "sco:premiership",
                "role_family": role_family,
                "age_at_value": snapshot["age"],
                "value_gbp": value_gbp,
                "value_kind": "fee",
                "value_date": value_date.isoformat(),
                "performance_season": performance_season,
                "performance_minutes": snapshot["minutes"],
                "performance_rating": snapshot["rating"],
                "performance_adjusted_percentile": midrank_percentile(
                    float(snapshot["rating"]), cohort
                )
                if cohort
                else None,
                "performance_mapping": "current_premiership_cohort",
                "source_id": source_id,
                "source_url": source_url,
                "source_title": "Transfer register",
                "verified_at": str(row.get("verified_at") or "2026-10-23"),
                "confidence": "confirmed"
                if row.get("verification_status") == "confirmed"
                else "reported",
                "note": (
                    "Diagnostic Aberdeen-market spine; historical performance mapped to "
                    "the current Premiership cohort."
                ),
            }
        )
    return anchors


def write_anchors(anchors: list[dict[str, Any]], path: Path = ANCHORS_PATH) -> None:
    import yaml

    header = (
        "# Public-source anchors for the scouting value model.\n"
        "# Generated by `fitba scouting values --seed` from the curated transfer\n"
        "# register; review each row before adding a new one.\n"
    )
    body = yaml.safe_dump(
        {"version": 1, "updated_at": "2026-10-23", "anchors": anchors},
        sort_keys=False,
        allow_unicode=True,
    )
    path.write_text(header + body, encoding="utf-8")


__all__ = [
    "ANCHORS_PATH",
    "anchor_report",
    "fit_value_model",
    "seed_anchors_from_transfers",
    "validate_anchor",
    "value_for_row",
    "write_anchors",
]
