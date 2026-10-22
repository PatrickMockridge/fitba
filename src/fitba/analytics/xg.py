"""fxG: fitba's own shot-on-target expectation, with an interval.

The model is deliberately small enough to audit:

- conversion is estimated from goals per shot on target, by competition-season,
  with an empirical-Bayes Beta prior;
- a match's fxG is shots on target x the posterior conversion rate;
- a residual overdispersion term widens the interval for match-to-match noise;
- the interval is an 80% model interval, not a promise about the result.

It is not provider xG. Provider xG is carried separately and is never blended
into fxG.
"""

from __future__ import annotations

import math
import random
import zlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

RateKey = tuple[str, str]


@dataclass(frozen=True, slots=True)
class Rate:
    competition_id: str
    season: str | None
    goals: int
    shots_on_target: int
    matches: int
    alpha: float
    beta: float
    source: str
    low_p: float
    high_p: float

    @property
    def mean(self) -> float:
        total = self.alpha + self.beta
        return self.alpha / total if total else 0.0


@dataclass(frozen=True, slots=True)
class FxGModel:
    model_id: str
    label: str
    status: str
    prior_strength: float
    interval_level: float
    z: float
    overdispersion: float
    global_rate: Rate
    rates: dict[RateKey, Rate] = field(default_factory=dict)
    competition_rates: dict[str, Rate] = field(default_factory=dict)
    fit_seasons: tuple[str, ...] = ()
    fit_matches: int = 0

    def rate_for(self, competition_id: str, season: str) -> tuple[Rate, str]:
        exact = self.rates.get((competition_id, season))
        if exact is not None:
            return exact, "competition-season"
        competition = self.competition_rates.get(competition_id)
        if competition is not None:
            return competition, "competition"
        return self.global_rate, "global"


def _rate(
    *,
    competition_id: str,
    season: str | None,
    goals: int,
    shots_on_target: int,
    matches: int,
    prior_rate: float,
    prior_strength: float,
    source: str,
    draws: int,
    seed: int,
    level: float,
) -> Rate:
    alpha = prior_rate * prior_strength + goals
    beta = (1 - prior_rate) * prior_strength + max(0, shots_on_target - goals)
    if alpha <= 0:
        alpha = 0.5
    if beta <= 0:
        beta = 0.5
    rng = random.Random(seed)
    samples = sorted(rng.betavariate(alpha, beta) for _ in range(draws))
    low = samples[int((1 - level) / 2 * (draws - 1))]
    high = samples[int((1 + level) / 2 * (draws - 1))]
    return Rate(
        competition_id=competition_id,
        season=season,
        goals=goals,
        shots_on_target=shots_on_target,
        matches=matches,
        alpha=alpha,
        beta=beta,
        source=source,
        low_p=low,
        high_p=high,
    )


def _seed_for(key: str, seed: int) -> int:
    return seed + zlib.crc32(key.encode("utf-8"))


def _valid_row(row: dict[str, Any]) -> bool:
    return (
        row.get("goals_for") is not None
        and row.get("shots_on_target") is not None
        and int(row["shots_on_target"]) >= 0
    )


def fit_fxg(rows: Iterable[dict[str, Any]], config: dict[str, Any]) -> FxGModel:
    fit_config = config.get("fit") or {}
    interval_config = config.get("interval") or {}
    before_season = str(fit_config.get("before_season") or "2026-27")
    min_sot = int(fit_config.get("min_shots_on_target") or 120)
    prior_strength = float(fit_config.get("prior_strength_sot") or 250)
    excluded = tuple(fit_config.get("exclude_competition_prefixes") or ())
    draws = int(interval_config.get("draws") or 10000)
    seed = int(interval_config.get("seed") or 1)
    level = float(interval_config.get("level") or 0.80)

    fit_rows = [
        row
        for row in rows
        if _valid_row(row)
        and int(row["shots_on_target"]) > 0
        and str(row.get("season") or "") < before_season
        and not str(row.get("competition_id") or "").startswith(excluded)
    ]
    if not fit_rows:
        raise ValueError("no rows available to fit fxG")

    global_goals = sum(int(row["goals_for"]) for row in fit_rows)
    global_sot = sum(int(row["shots_on_target"]) for row in fit_rows)
    global_rate_value = global_goals / global_sot if global_sot else 0.0
    global_rate = _rate(
        competition_id="all",
        season=None,
        goals=global_goals,
        shots_on_target=global_sot,
        matches=len(fit_rows),
        prior_rate=global_rate_value,
        prior_strength=prior_strength,
        source="global",
        draws=draws,
        seed=_seed_for("global", seed),
        level=level,
    )

    groups: dict[RateKey, list[dict[str, Any]]] = {}
    competitions: dict[str, list[dict[str, Any]]] = {}
    for row in fit_rows:
        competition_id = str(row["competition_id"])
        season = str(row["season"])
        groups.setdefault((competition_id, season), []).append(row)
        competitions.setdefault(competition_id, []).append(row)

    competition_rates: dict[str, Rate] = {}
    for competition_id, group in competitions.items():
        goals = sum(int(row["goals_for"]) for row in group)
        sot = sum(int(row["shots_on_target"]) for row in group)
        if sot < min_sot:
            continue
        competition_rates[competition_id] = _rate(
            competition_id=competition_id,
            season=None,
            goals=goals,
            shots_on_target=sot,
            matches=len(group),
            prior_rate=global_rate_value,
            prior_strength=prior_strength,
            source="competition",
            draws=draws,
            seed=_seed_for(competition_id, seed),
            level=level,
        )

    rates: dict[RateKey, Rate] = {}
    for (competition_id, season), group in groups.items():
        goals = sum(int(row["goals_for"]) for row in group)
        sot = sum(int(row["shots_on_target"]) for row in group)
        if sot < min_sot:
            continue
        fallback = competition_rates.get(competition_id)
        prior_rate = fallback.mean if fallback is not None else global_rate_value
        rates[(competition_id, season)] = _rate(
            competition_id=competition_id,
            season=season,
            goals=goals,
            shots_on_target=sot,
            matches=len(group),
            prior_rate=prior_rate,
            prior_strength=prior_strength,
            source="competition-season",
            draws=draws,
            seed=_seed_for(f"{competition_id}:{season}", seed),
            level=level,
        )

    # Pearson-style overdispersion using the fitted rate for each row.
    residuals: list[float] = []
    for row in fit_rows:
        competition_id = str(row["competition_id"])
        season = str(row["season"])
        rate = (
            rates.get((competition_id, season))
            or competition_rates.get(competition_id)
            or global_rate
        )
        mu = max(1e-6, int(row["shots_on_target"]) * rate.mean)
        residuals.append((int(row["goals_for"]) - mu) ** 2 / mu)
    overdispersion = max(1.0, sum(residuals) / max(1, len(residuals) - 1))
    overdispersion = min(overdispersion, 10.0)

    return FxGModel(
        model_id=str(config.get("model_id") or "fxg-1"),
        label=str(config.get("label") or "fxG"),
        status=str(config.get("status") or "experimental"),
        prior_strength=prior_strength,
        interval_level=level,
        z=float(interval_config.get("z") or 1.2816),
        overdispersion=overdispersion,
        global_rate=global_rate,
        rates=rates,
        competition_rates=competition_rates,
        fit_seasons=tuple(sorted({str(row["season"]) for row in fit_rows})),
        fit_matches=len(fit_rows),
    )


def predict_fxg(model: FxGModel, row: dict[str, Any]) -> dict[str, Any]:
    sot = int(row["shots_on_target"])
    rate, source = model.rate_for(str(row["competition_id"]), str(row["season"]))
    mu = sot * rate.mean
    sd = math.sqrt(max(0.0, sot * rate.mean * (1 - rate.mean)) + model.overdispersion * mu)
    low = min(sot * rate.low_p, max(0.0, mu - model.z * sd))
    high = max(sot * rate.high_p, mu + model.z * sd)
    return {
        "fxg": round(mu, 3),
        "low": round(low, 3),
        "high": round(high, 3),
        "rate": round(rate.mean, 4),
        "rate_source": source,
        "model_id": model.model_id,
    }


def aggregate_fxg(model: FxGModel, rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    total_mu = 0.0
    total_var = 0.0
    total_goals = 0
    total_sot = 0
    count = 0
    for row in rows:
        if not _valid_row(row):
            continue
        prediction = predict_fxg(model, row)
        mu = float(prediction["fxg"])
        total_mu += mu
        total_var += ((float(prediction["high"]) - float(prediction["low"])) / (2 * model.z)) ** 2
        total_goals += int(row["goals_for"])
        total_sot += int(row["shots_on_target"])
        count += 1
    if not count:
        return {
            "matches": 0,
            "fxg": None,
            "low": None,
            "high": None,
            "goals": 0,
            "goals_minus_fxg": None,
            "goals_minus_low": None,
            "goals_minus_high": None,
            "shots_on_target": 0,
        }
    sd = math.sqrt(total_var)
    low = max(0.0, total_mu - model.z * sd)
    high = total_mu + model.z * sd
    return {
        "matches": count,
        "fxg": round(total_mu, 2),
        "low": round(low, 2),
        "high": round(high, 2),
        "goals": total_goals,
        "goals_minus_fxg": round(total_goals - total_mu, 2),
        "goals_minus_low": round(total_goals - high, 2),
        "goals_minus_high": round(total_goals - low, 2),
        "shots_on_target": total_sot,
    }


def _ols_slope(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    variance = sum((x - mean_x) ** 2 for x in xs)
    if variance == 0:
        return None
    return covariance / variance


def evaluate_fxg(
    model: FxGModel,
    rows: Iterable[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    evaluation = config.get("evaluation") or {}
    validation_season = str(evaluation.get("validation_season") or "2026-27")
    pairs: list[tuple[float, float]] = []
    match_keys: set[Any] = set()
    for row in rows:
        if not _valid_row(row):
            continue
        if str(row.get("season")) != validation_season:
            continue
        provider = row.get("provider_xg")
        if provider is None:
            continue
        prediction = predict_fxg(model, row)
        pairs.append((float(prediction["fxg"]), float(provider)))
        match_key = row.get("match_key") or row.get("fixture_id") or row.get("match_id")
        if match_key is not None:
            match_keys.add(match_key)
    if not pairs:
        return {
            "status": "unavailable",
            "validation_season": validation_season,
            "matches": 0,
            "bias": None,
            "mae": None,
            "calibration_slope": None,
            "passed": False,
            "note": "No provider xG is available for the validation season.",
        }
    fxg_values = [pair[0] for pair in pairs]
    provider_values = [pair[1] for pair in pairs]
    bias = sum(x - y for x, y in pairs) / len(pairs)
    mae = sum(abs(x - y) for x, y in pairs) / len(pairs)
    slope = _ols_slope(fxg_values, provider_values)
    max_bias = float(evaluation.get("max_abs_bias") or 0.15)
    max_mae = float(evaluation.get("max_mae") or 0.55)
    slope_min = float(evaluation.get("calibration_slope_min") or 0.70)
    slope_max = float(evaluation.get("calibration_slope_max") or 1.30)
    passed = (
        abs(bias) <= max_bias
        and mae <= max_mae
        and slope is not None
        and slope_min <= slope <= slope_max
    )
    return {
        "status": "pass" if passed else "fail",
        "validation_season": validation_season,
        "matches": len(match_keys) if match_keys else len(pairs),
        "team_rows": len(pairs),
        "bias": round(bias, 3),
        "mae": round(mae, 3),
        "calibration_slope": round(slope, 3) if slope is not None else None,
        "thresholds": {
            "max_abs_bias": max_bias,
            "max_mae": max_mae,
            "calibration_slope_min": slope_min,
            "calibration_slope_max": slope_max,
        },
        "passed": passed,
        "note": (
            "Provider xG is an external benchmark, not the model target. "
            "A failed gate keeps the numbers descriptive."
        ),
    }


def model_to_dict(model: FxGModel, evaluation: dict[str, Any] | None = None) -> dict[str, Any]:
    def rate_dict(rate: Rate) -> dict[str, Any]:
        return {
            "competition_id": rate.competition_id,
            "season": rate.season,
            "matches": rate.matches,
            "goals": rate.goals,
            "shots_on_target": rate.shots_on_target,
            "rate": round(rate.mean, 4),
            "low": round(rate.low_p, 4),
            "high": round(rate.high_p, 4),
            "source": rate.source,
        }

    return {
        "model_id": model.model_id,
        "label": model.label,
        "status": model.status,
        "prior_strength": model.prior_strength,
        "interval_level": model.interval_level,
        "overdispersion": round(model.overdispersion, 4),
        "fit_matches": model.fit_matches,
        "fit_seasons": list(model.fit_seasons),
        "global_rate": rate_dict(model.global_rate),
        "rates": [rate_dict(rate) for rate in model.rates.values()],
        "competition_rates": [rate_dict(rate) for rate in model.competition_rates.values()],
        "evaluation": evaluation,
    }


__all__ = [
    "FxGModel",
    "Rate",
    "aggregate_fxg",
    "evaluate_fxg",
    "fit_fxg",
    "model_to_dict",
    "predict_fxg",
]
