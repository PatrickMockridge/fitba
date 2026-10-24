"""fxG: fitba's team-match expected-goals estimate, with two ranges.

The model is deliberately small enough to audit:

- the enriched specification uses open-play shot zones, shots on target and
  blocked shots, plus a fixed penalty value, fitted to provider xG;
- a residual or conversion fallback covers matches without the enriched inputs;
- an 80% model range describes uncertainty in the estimate;
- an 80% goals range describes the spread of goals from the same chances.

It is a team-match aggregate model, not a shot-level xG model and not provider
xG. Provider xG is carried separately and is never blended into fxG.
"""

from __future__ import annotations

import math
import random
import zlib
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from typing import Any

from fitba.analytics.xg_uncertainty import (
    aggregate_goal_range,
    goal_range,
)

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
class ProviderCalibration:
    season: str
    competition_id: str
    intercept: float
    slope: float
    clamp_min: float
    sample_matches: int
    sample_team_rows: int
    in_sample_mae: float
    loocv_mae: float | None
    max_loocv_error: float | None
    r2: float | None


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
    coefficients: dict[str, float] | None = None
    interval_low_offset: float = 0.0
    interval_high_offset: float = 0.0
    fit_team_rows: int = 0
    fit_season: str | None = None
    fit_competition: str | None = None
    calibration_evaluation: dict[str, Any] | None = None
    specification: str | None = None
    features: tuple[str, ...] = ()
    fallback_coefficients: dict[str, float] | None = None
    penalty_xg: float = 0.0
    penalty_source: str = ""
    bootstrap_coefficients: tuple[dict[str, float], ...] = ()
    bootstrap_draws: int = 0
    bootstrap_seed: int = 0
    residual_pool: tuple[float, ...] = ()
    interval_basis: str = "residual"
    goals_range_method: str = "binomial_penalty"
    goals_dispersion: float = 1.0
    selection: dict[str, Any] | None = None
    transfer_check: dict[str, Any] | None = None

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


def _shot_volume_features(row: dict[str, Any]) -> tuple[float, float, float] | None:
    """Return (1, shots on target, off-target shots) for the calibrated model."""
    if row.get("shots") is None or row.get("shots_on_target") is None:
        return None
    shots = float(row["shots"])
    sot = float(row["shots_on_target"])
    if shots < 0 or sot < 0 or shots < sot:
        return None
    return (1.0, sot, shots - sot)


def _solve3(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    """Solve a 3x3 linear system with partial pivoting."""
    size = 3
    work = [[*list(matrix[row]), float(rhs[row])] for row in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(work[row][column]))
        if abs(work[pivot][column]) < 1e-12:
            raise ValueError("singular shot-volume design matrix")
        work[column], work[pivot] = work[pivot], work[column]
        divisor = work[column][column]
        work[column] = [value / divisor for value in work[column]]
        for row in range(size):
            if row == column:
                continue
            factor = work[row][column]
            if factor:
                work[row] = [
                    work[row][index] - factor * work[column][index] for index in range(size + 1)
                ]
    return [work[row][size] for row in range(size)]


CANDIDATES: dict[str, dict[str, Any]] = {
    "E": {
        "features": ("shots_on_target", "off_target_shots"),
        "intercept": True,
        "target": "provider",
        "label": "baseline shot volume",
    },
    "C": {
        "features": ("open_play_sot", "open_play_off"),
        "intercept": False,
        "target": "open",
        "label": "open-play volume",
    },
    "A": {
        "features": ("open_play_sot", "open_play_off", "open_play_blocked"),
        "intercept": False,
        "target": "open",
        "label": "open-play volume plus blocked",
    },
    "Z": {
        "features": ("open_play_insidebox", "open_play_outsidebox"),
        "intercept": False,
        "target": "open",
        "label": "shot-zone volume",
    },
    "D": {
        "features": ("open_play_insidebox", "open_play_outsidebox", "open_play_sot"),
        "intercept": False,
        "target": "open",
        "label": "shot-zone volume plus on-target",
    },
}


def _solve_linear(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    """Solve an n x n linear system with partial pivoting."""
    size = len(rhs)
    if size == 0:
        return []
    work = [[*list(matrix[row]), float(rhs[row])] for row in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(work[row][column]))
        if abs(work[pivot][column]) < 1e-12:
            raise ValueError("singular fxG design matrix")
        work[column], work[pivot] = work[pivot], work[column]
        divisor = work[column][column]
        work[column] = [value / divisor for value in work[column]]
        for row in range(size):
            if row == column:
                continue
            factor = work[row][column]
            if factor:
                work[row] = [
                    work[row][index] - factor * work[column][index]
                    for index in range(size + 1)
                ]
    return [work[row][size] for row in range(size)]


def _feature_value(row: dict[str, Any], feature: str) -> float | None:
    if feature == "off_target_shots":
        shots = row.get("shots")
        sot = row.get("shots_on_target")
        if shots is None or sot is None:
            return None
        return max(0.0, float(shots) - float(sot))
    value = row.get(feature)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _candidate_features(
    row: dict[str, Any], specification: str
) -> tuple[float, ...] | None:
    spec = CANDIDATES.get(specification)
    if spec is None:
        return None
    values: list[float] = []
    for feature in spec["features"]:
        value = _feature_value(row, feature)
        if value is None or value < 0:
            return None
        values.append(value)
    if specification in {"Z", "D"} and row.get("zone_status") != "available":
        return None
    if specification != "E" and row.get("penalty_attempts") is None:
        return None
    return tuple(values)


def _candidate_target(
    row: dict[str, Any], specification: str, penalty_xg: float
) -> float | None:
    spec = CANDIDATES[specification]
    if spec["target"] == "provider":
        value = row.get("provider_xg")
        return float(value) if value is not None else None
    value = row.get("provider_xg_open_play_fdco")
    if value is not None:
        return float(value)
    provider = row.get("provider_xg")
    penalties = row.get("penalty_attempts")
    if provider is None or penalties is None:
        return None
    return max(0.0, float(provider) - penalty_xg * float(penalties))


def _linear_prediction(
    coefficients: tuple[float, ...],
    specification: str,
    row: dict[str, Any],
    penalty_xg: float,
) -> float | None:
    spec = CANDIDATES[specification]
    features = _candidate_features(row, specification)
    if features is None:
        return None
    offset = 1 if spec["intercept"] else 0
    if len(coefficients) != len(features) + offset:
        return None
    value = coefficients[0] if offset else 0.0
    for index, feature in enumerate(features):
        value += coefficients[index + offset] * feature
    if spec["target"] == "open":
        penalties = row.get("penalty_attempts")
        value += penalty_xg * float(penalties or 0)
    return max(0.0, value)


def _fit_candidate(
    rows: list[dict[str, Any]],
    specification: str,
    penalty_xg: float,
) -> tuple[float, ...] | None:
    spec = CANDIDATES[specification]
    samples: list[tuple[tuple[float, ...], float]] = []
    for row in rows:
        features = _candidate_features(row, specification)
        target = _candidate_target(row, specification, penalty_xg)
        if features is None or target is None:
            continue
        values = (1.0, *features) if spec["intercept"] else features
        samples.append((values, target))
    minimum = len(spec["features"]) + (1 if spec["intercept"] else 0) + 1
    if len(samples) < max(4, minimum):
        return None
    active = list(range(len(samples[0][0])))
    for _ in range(len(active) + 1):
        if not active:
            return None
        matrix = [
            [
                sum(sample[i] * sample[j] for sample, _target in samples)
                for j in active
            ]
            for i in active
        ]
        rhs = [
            sum(sample[i] * target for sample, target in samples)
            for i in active
        ]
        try:
            solution = _solve_linear(matrix, rhs)
        except ValueError:
            return None
        if spec["intercept"]:
            break
        worst = min(range(len(solution)), key=lambda index: solution[index])
        if solution[worst] >= -1e-9:
            break
        active.pop(worst)
    full = [0.0] * len(samples[0][0])
    for index, value in zip(active, solution, strict=False):
        full[index] = value
    if any(not math.isfinite(value) for value in full):
        return None
    if spec["target"] == "open" and not spec["intercept"] and any(
        value > 1.0 for value in full
    ):
        return None
    return tuple(full)


def _candidate_coefficient_dict(
    coefficients: tuple[float, ...], specification: str
) -> dict[str, float]:
    spec = CANDIDATES[specification]
    offset = 1 if spec["intercept"] else 0
    output: dict[str, float] = {}
    if offset:
        output["intercept"] = coefficients[0]
    for index, feature in enumerate(spec["features"]):
        output[feature] = coefficients[index + offset]
    return output


def _candidate_metrics(
    predictions: list[float],
    actuals: list[float],
    *,
    matches: int,
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    if not predictions:
        return {
            "matches": matches,
            "team_rows": 0,
            "bias": None,
            "mae": None,
            "calibration_slope": None,
            "r2": None,
            "passed": False,
        }
    bias = sum(
        prediction - actual
        for prediction, actual in zip(predictions, actuals, strict=False)
    ) / len(predictions)
    mae = sum(
        abs(prediction - actual)
        for prediction, actual in zip(predictions, actuals, strict=False)
    ) / len(predictions)
    slope = _ols_slope(predictions, actuals)
    mean_actual = sum(actuals) / len(actuals)
    ss_total = sum((actual - mean_actual) ** 2 for actual in actuals)
    ss_residual = sum(
        (actual - prediction) ** 2
        for prediction, actual in zip(predictions, actuals, strict=False)
    )
    r2 = 1.0 - (ss_residual / ss_total) if ss_total else None
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
        "matches": matches,
        "team_rows": len(predictions),
        "bias": round(bias, 3),
        "mae": round(mae, 3),
        "calibration_slope": round(slope, 3) if slope is not None else None,
        "r2": round(r2, 3) if r2 is not None else None,
        "passed": passed,
    }


def _loocv_candidate(
    rows: list[dict[str, Any]],
    specification: str,
    penalty_xg: float,
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    groups: dict[Any, list[dict[str, Any]]] = {}
    for row in rows:
        if _candidate_features(row, specification) is None:
            continue
        if _candidate_target(row, specification, penalty_xg) is None:
            continue
        key = row.get("match_key") or row.get("match_id") or row.get("fixture_id")
        if key is None:
            continue
        groups.setdefault(key, []).append(row)
    predictions: list[float] = []
    actuals: list[float] = []
    for key, group in groups.items():
        training = [
            row
            for other_key, other_group in groups.items()
            if other_key != key
            for row in other_group
        ]
        coefficients = _fit_candidate(training, specification, penalty_xg)
        if coefficients is None:
            continue
        for row in group:
            prediction = _linear_prediction(coefficients, specification, row, penalty_xg)
            actual = row.get("provider_xg")
            if prediction is None or actual is None:
                continue
            predictions.append(prediction)
            actuals.append(float(actual))
    return _candidate_metrics(
        predictions,
        actuals,
        matches=len(groups),
        evaluation=evaluation,
    )


def _select_candidate(
    rows: list[dict[str, Any]],
    *,
    penalty_xg: float,
    evaluation: dict[str, Any],
    penalty_coverage: float,
    zone_coverage: float,
    min_zone_coverage: float,
) -> tuple[str | None, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for specification, spec in CANDIDATES.items():
        metrics = _loocv_candidate(rows, specification, penalty_xg, evaluation)
        candidate = {
            "label": spec["label"],
            "features": list(spec["features"]),
            "target": spec["target"],
            "parameters": len(spec["features"]) + (1 if spec["intercept"] else 0),
            **metrics,
        }
        if (
            specification in {"Z", "D"}
            and zone_coverage < min_zone_coverage
        ):
            candidate["passed"] = False
            candidate["reason"] = "zone_coverage_below_floor"
        candidates[specification] = candidate
    eligible = [
        (specification, metrics)
        for specification, metrics in candidates.items()
        if metrics.get("passed") and metrics.get("mae") is not None
    ]
    if not eligible:
        baseline = candidates.get("E")
        selected = "E" if baseline and baseline.get("mae") is not None else None
        return selected, {
            "rule": "no candidate passed the gate; keep the baseline",
            "selected": selected,
            "candidates": candidates,
        }
    selected, best = min(eligible, key=lambda item: float(item[1]["mae"]))
    for specification, metrics in eligible:
        if (
            float(metrics["mae"]) <= float(best["mae"]) + 0.01
            and metrics["parameters"] < best["parameters"]
        ):
            selected, best = specification, metrics
    baseline = candidates.get("E")
    open_candidates = [
        (specification, metrics)
        for specification, metrics in eligible
        if specification != "E"
    ]
    if (
        baseline
        and baseline.get("mae") is not None
        and open_candidates
        and penalty_coverage >= 0.90
    ):
        open_specification, open_metrics = min(
            open_candidates, key=lambda item: float(item[1]["mae"])
        )
        if float(open_metrics["mae"]) <= float(baseline["mae"]) + 0.01:
            selected, best = open_specification, open_metrics
    return selected, {
        "rule": "gate-eligible, lowest MAE, simpler within 0.01; penalty-adjusted when within 0.01",
        "selected": selected,
        "selected_label": CANDIDATES[selected]["label"],
        "candidates": candidates,
    }


def _bootstrap_coefficients(
    rows: list[dict[str, Any]],
    specification: str,
    penalty_xg: float,
    *,
    draws: int,
    seed: int,
) -> tuple[dict[str, float], ...]:
    groups: dict[Any, list[dict[str, Any]]] = {}
    for row in rows:
        key = row.get("match_key") or row.get("match_id") or row.get("fixture_id")
        if key is None:
            continue
        groups.setdefault(key, []).append(row)
    keys = list(groups)
    if not keys or draws <= 0:
        return ()
    rng = random.Random(seed)
    output: list[dict[str, float]] = []
    for _ in range(draws):
        sample: list[dict[str, Any]] = []
        for _ in keys:
            sample.extend(groups[keys[rng.randrange(len(keys))]])
        coefficients = _fit_candidate(sample, specification, penalty_xg)
        if coefficients is not None:
            output.append(
                _candidate_coefficient_dict(coefficients, specification)
            )
    return tuple(output)




def _coefficient_tuple(
    coefficients: dict[str, float], specification: str
) -> tuple[float, ...]:
    spec = CANDIDATES[specification]
    values: list[float] = []
    if spec["intercept"]:
        values.append(float(coefficients.get("intercept") or 0.0))
    for feature in spec["features"]:
        values.append(float(coefficients.get(feature) or 0.0))
    return tuple(values)


def _loocv_predictions(
    rows: list[dict[str, Any]],
    specification: str,
    penalty_xg: float,
) -> tuple[list[float], list[float], list[float], int]:
    groups: dict[Any, list[dict[str, Any]]] = {}
    for row in rows:
        if _candidate_features(row, specification) is None:
            continue
        if _candidate_target(row, specification, penalty_xg) is None:
            continue
        key = row.get("match_key") or row.get("match_id") or row.get("fixture_id")
        if key is None:
            continue
        groups.setdefault(key, []).append(row)
    predictions: list[float] = []
    actuals: list[float] = []
    for key, group in groups.items():
        training = [
            row
            for other_key, other_group in groups.items()
            if other_key != key
            for row in other_group
        ]
        coefficients = _fit_candidate(training, specification, penalty_xg)
        if coefficients is None:
            continue
        for row in group:
            prediction = _linear_prediction(coefficients, specification, row, penalty_xg)
            actual = row.get("provider_xg")
            if prediction is None or actual is None:
                continue
            predictions.append(prediction)
            actuals.append(float(actual))
    residuals = [
        prediction - actual
        for prediction, actual in zip(predictions, actuals, strict=False)
    ]
    return predictions, actuals, residuals, len(groups)


def _model_range_coverage(
    rows: list[dict[str, Any]],
    predictions: list[float],
    actuals: list[float],
    low_offset: float,
    high_offset: float,
) -> float | None:
    if not predictions:
        return None
    covered = 0
    for prediction, actual in zip(predictions, actuals, strict=False):
        low = max(0.0, prediction + low_offset)
        high = max(prediction, prediction + high_offset)
        if low <= actual <= high:
            covered += 1
    return round(covered / len(predictions), 3)


def _row_goal_inputs(
    row: dict[str, Any],
    prediction: float,
    specification: str,
    penalty_xg: float,
) -> tuple[float, int, int]:
    penalties = row.get("penalty_attempts") if specification != "E" else 0
    pen_count = int(penalties or 0)
    open_xg = max(0.0, prediction - penalty_xg * pen_count)
    open_shots = row.get("open_play_shots") if specification != "E" else row.get("shots")
    if open_shots is None:
        open_shots = max(0, int(row.get("shots") or 0) - pen_count)
    return open_xg, int(open_shots), pen_count


def _goals_range_coverage(
    rows: list[dict[str, Any]],
    predictions: list[float],
    *,
    specification: str,
    penalty_xg: float,
    dispersion: float,
    level: float,
) -> float | None:
    if not predictions:
        return None
    covered = 0
    for row, prediction in zip(rows, predictions, strict=False):
        open_xg, open_shots, penalties = _row_goal_inputs(
            row, prediction, specification, penalty_xg
        )
        low, high = goal_range(
            open_xg=open_xg,
            open_shots=open_shots,
            penalties=penalties,
            penalty_xg=penalty_xg,
            dispersion=dispersion,
            level=level,
        )
        goals = row.get("goals_for")
        if goals is not None and low <= int(goals) <= high:
            covered += 1
    return round(covered / len(predictions), 3)


def _goals_dispersion(
    rows: list[dict[str, Any]],
    predictions: list[float],
    *,
    specification: str,
    penalty_xg: float,
    cap: float = 3.0,
) -> float:
    numerator = 0.0
    count = 0
    for row, prediction in zip(rows, predictions, strict=False):
        goals = row.get("goals_for")
        if goals is None:
            continue
        open_xg, open_shots, penalties = _row_goal_inputs(
            row, prediction, specification, penalty_xg
        )
        p_open = open_xg / open_shots if open_shots else 0.0
        variance = open_shots * p_open * (1.0 - p_open)
        variance += penalties * penalty_xg * (1.0 - penalty_xg)
        if variance <= 0:
            continue
        numerator += (float(goals) - prediction) ** 2 / variance
        count += 1
    if count <= 1:
        return 1.0
    return round(min(cap, max(1.0, numerator / (count - 1))), 3)


def _enriched_evaluation(
    predictions: list[float],
    actuals: list[float],
    *,
    matches: int,
    evaluation: dict[str, Any],
    model_coverage: float | None,
    goals_coverage: float | None,
    dispersion: float,
    season: str,
) -> dict[str, Any]:
    metrics = _candidate_metrics(
        predictions,
        actuals,
        matches=matches,
        evaluation=evaluation,
    )
    return {
        "status": "pass" if metrics["passed"] else "fail",
        "method": "leave_one_match_out",
        "validation_season": season,
        "matches": matches,
        "team_rows": metrics["team_rows"],
        "bias": metrics["bias"],
        "mae": metrics["mae"],
        "calibration_slope": metrics["calibration_slope"],
        "r2": metrics["r2"],
        "model_interval_coverage": model_coverage,
        "goals_range_coverage": goals_coverage,
        "goals_dispersion": dispersion,
        "thresholds": {
            "max_abs_bias": float(evaluation.get("max_abs_bias") or 0.15),
            "max_mae": float(evaluation.get("max_mae") or 0.55),
            "calibration_slope_min": float(evaluation.get("calibration_slope_min") or 0.70),
            "calibration_slope_max": float(evaluation.get("calibration_slope_max") or 1.30),
        },
        "passed": metrics["passed"],
        "note": (
            "Leave-one-match-out calibration to 2026-27 provider xG. "
            "This is an in-season calibration, not an out-of-season holdout; "
            "the model is not a location xG and does not predict results."
        ),
    }


def _fit_shot_volume(rows: list[dict[str, Any]]) -> list[float]:
    features = [
        (feature, float(row["provider_xg"]))
        for row in rows
        if (feature := _shot_volume_features(row)) is not None
        and row.get("provider_xg") is not None
    ]
    if len(features) < 3:
        raise ValueError("not enough provider rows for the shot-volume fit")
    matrix = [
        [sum(feature[i] * feature[j] for feature, _ in features) for j in range(3)]
        for i in range(3)
    ]
    rhs = [sum(feature[i] * target for feature, target in features) for i in range(3)]
    return _solve3(matrix, rhs)


def _loocv_shot_volume(
    rows: list[dict[str, Any]],
) -> tuple[list[float], list[float], list[float], int]:
    """Fit once per match, predict the held-out match, and return residuals."""
    groups: dict[Any, list[dict[str, Any]]] = {}
    for row in rows:
        if _shot_volume_features(row) is None or row.get("provider_xg") is None:
            continue
        key = row.get("match_key") or row.get("fixture_id") or row.get("match_id")
        if key is None:
            continue
        groups.setdefault(key, []).append(row)
    predictions: list[float] = []
    actuals: list[float] = []
    for key, group in groups.items():
        training = [
            row
            for other_key, other_group in groups.items()
            if other_key != key
            for row in other_group
        ]
        coefficients = _fit_shot_volume(training)
        for row in group:
            feature = _shot_volume_features(row)
            if feature is None:
                continue
            value = max(
                0.0,
                coefficients[0] * feature[0]
                + coefficients[1] * feature[1]
                + coefficients[2] * feature[2],
            )
            predictions.append(value)
            actuals.append(float(row["provider_xg"]))
    residuals = [
        prediction - actual for prediction, actual in zip(predictions, actuals, strict=False)
    ]
    return predictions, actuals, residuals, len(groups)


def _quantile(values: list[float], probability: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = min(len(ordered) - 1, max(0, round(probability * (len(ordered) - 1))))
    return ordered[position]


def _calibration_evaluation(
    predictions: list[float],
    actuals: list[float],
    matches: int,
    evaluation: dict[str, Any],
    season: str,
) -> dict[str, Any]:
    pairs = list(zip(predictions, actuals, strict=False))
    if not pairs:
        return {
            "status": "unavailable",
            "method": "leave_one_match_out",
            "validation_season": season,
            "matches": 0,
            "bias": None,
            "mae": None,
            "calibration_slope": None,
            "passed": False,
            "note": "No provider xG is available for the calibration season.",
        }
    bias = sum(prediction - actual for prediction, actual in pairs) / len(pairs)
    mae = sum(abs(prediction - actual) for prediction, actual in pairs) / len(pairs)
    slope = _ols_slope(predictions, actuals)
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
        "method": "leave_one_match_out",
        "validation_season": season,
        "matches": matches,
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
            "Leave-one-match-out calibration to 2026-27 provider xG. "
            "This is an in-season calibration, not an out-of-season holdout; "
            "the model is not a location xG."
        ),
    }


def fit_fxg(rows: Iterable[dict[str, Any]], config: dict[str, Any]) -> FxGModel:
    rows = list(rows)
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

    model = FxGModel(
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

    calibration_config = config.get("calibration") or {}
    penalty_config = config.get("penalty") or {}
    evaluation_config = config.get("evaluation") or {}
    provider_season = str(calibration_config.get("season") or "2026-27")
    provider_competition = str(calibration_config.get("competition_id") or "sco:premiership")
    min_team_rows = int(calibration_config.get("min_team_rows") or 90)
    min_matches = int(calibration_config.get("min_matches") or 45)
    penalty_xg = float(penalty_config.get("xg") or 0.76)
    penalty_source = str(
        penalty_config.get("source")
        or "fixed historical penalty conversion prior; see docs/xg.md"
    )
    bootstrap_draws = int(interval_config.get("bootstrap_draws") or 2000)

    enriched_rows = [
        row
        for row in rows
        if row.get("provider_xg") is not None
        and str(row.get("season")) == provider_season
        and str(row.get("competition_id")) == provider_competition
        and _candidate_features(row, "C") is not None
    ]
    penalty_coverage = (
        sum(1 for row in enriched_rows if row.get("penalty_attempts") is not None)
        / len(enriched_rows)
        if enriched_rows
        else 0.0
    )
    zone_coverage = (
        sum(1 for row in enriched_rows if row.get("zone_status") == "available")
        / len(enriched_rows)
        if enriched_rows
        else 0.0
    )
    min_zone_coverage = float(calibration_config.get("min_zone_coverage") or 0.80)
    if len(enriched_rows) >= min_team_rows:
        selected, selection = _select_candidate(
            enriched_rows,
            penalty_xg=penalty_xg,
            evaluation=evaluation_config,
            penalty_coverage=penalty_coverage,
            zone_coverage=zone_coverage,
            min_zone_coverage=min_zone_coverage,
        )
        if selected is not None:
            final_coefficients = _fit_candidate(enriched_rows, selected, penalty_xg)
            if final_coefficients is not None:
                predictions, actuals, residuals, matches = _loocv_predictions(
                    enriched_rows, selected, penalty_xg
                )
                if matches >= min_matches and predictions:
                    low_offset = _quantile(residuals, (1 - level) / 2)
                    high_offset = _quantile(residuals, (1 + level) / 2)
                    final_predictions = [
                        _linear_prediction(final_coefficients, selected, row, penalty_xg)
                        for row in enriched_rows
                    ]
                    aligned = [
                        (row, prediction)
                        for row, prediction in zip(enriched_rows, final_predictions, strict=False)
                        if prediction is not None
                    ]
                    dispersion = _goals_dispersion(
                        [row for row, _prediction in aligned],
                        [float(prediction) for _row, prediction in aligned],
                        specification=selected,
                        penalty_xg=penalty_xg,
                    )
                    model_coverage = _model_range_coverage(
                        enriched_rows,
                        predictions,
                        actuals,
                        low_offset,
                        high_offset,
                    )
                    goals_coverage = _goals_range_coverage(
                        [row for row, _prediction in aligned],
                        [float(prediction) for _row, prediction in aligned],
                        specification=selected,
                        penalty_xg=penalty_xg,
                        dispersion=dispersion,
                        level=level,
                    )
                    evaluation = _enriched_evaluation(
                        predictions,
                        actuals,
                        matches=matches,
                        evaluation=evaluation_config,
                        model_coverage=model_coverage,
                        goals_coverage=goals_coverage,
                        dispersion=dispersion,
                        season=provider_season,
                    )
                    fallback = (
                        _fit_candidate(enriched_rows, "C", penalty_xg)
                        if selected != "C"
                        else final_coefficients
                    )
                    bootstrap = _bootstrap_coefficients(
                        enriched_rows,
                        selected,
                        penalty_xg,
                        draws=bootstrap_draws,
                        seed=seed,
                    )
                    model = replace(
                        model,
                        coefficients=_candidate_coefficient_dict(
                            final_coefficients, selected
                        ),
                        specification=selected,
                        features=CANDIDATES[selected]["features"],
                        fallback_coefficients=(
                            _candidate_coefficient_dict(fallback, "C")
                            if fallback is not None
                            else None
                        ),
                        penalty_xg=penalty_xg,
                        penalty_source=penalty_source,
                        interval_low_offset=low_offset,
                        interval_high_offset=high_offset,
                        interval_basis="residual",
                        goals_range_method="binomial_penalty",
                        goals_dispersion=dispersion,
                        bootstrap_coefficients=bootstrap,
                        bootstrap_draws=bootstrap_draws,
                        bootstrap_seed=seed,
                        residual_pool=tuple(residuals),
                        selection=selection,
                        fit_matches=matches,
                        fit_seasons=(provider_season,),
                        fit_team_rows=sum(
                            1
                            for row in enriched_rows
                            if _candidate_features(row, selected) is not None
                        ),
                        fit_season=provider_season,
                        fit_competition=provider_competition,
                        calibration_evaluation=evaluation,
                    )
                    return model

    # Fallback: the original fxg-2 shot-volume calibration on total shots.
    calibration_rows = [
        row
        for row in rows
        if row.get("provider_xg") is not None
        and str(row.get("season")) == provider_season
        and str(row.get("competition_id")) == provider_competition
        and _shot_volume_features(row) is not None
    ]
    if len(calibration_rows) >= min_team_rows:
        predictions, actuals, residuals, matches = _loocv_shot_volume(calibration_rows)
        if matches >= min_matches and predictions:
            coefficients = _fit_shot_volume(calibration_rows)
            model = replace(
                model,
                coefficients={
                    "intercept": coefficients[0],
                    "shots_on_target": coefficients[1],
                    "off_target_shots": coefficients[2],
                },
                specification=None,
                features=(),
                interval_low_offset=_quantile(residuals, (1 - level) / 2),
                interval_high_offset=_quantile(residuals, (1 + level) / 2),
                fit_matches=matches,
                fit_seasons=(provider_season,),
                fit_team_rows=len(calibration_rows),
                fit_season=provider_season,
                fit_competition=provider_competition,
                calibration_evaluation=_calibration_evaluation(
                    predictions,
                    actuals,
                    matches,
                    config.get("evaluation") or {},
                    provider_season,
                ),
            )
    return model


def _goal_position(goals: int | None, low: int, high: int) -> str | None:
    if goals is None:
        return None
    if goals < low:
        return "below"
    if goals > high:
        return "above"
    return "within"


def predict_fxg(model: FxGModel, row: dict[str, Any]) -> dict[str, Any]:
    shots = row.get("shots")
    shots_int = int(shots) if shots is not None else None
    goals = row.get("goals_for")
    goals_int = int(goals) if goals is not None else None
    basis = "conversion"
    specification = model.specification
    mu: float | None = None
    penalties_known = row.get("penalty_attempts") is not None

    if specification and model.coefficients:
        coefficients = _coefficient_tuple(model.coefficients, specification)
        mu = _linear_prediction(coefficients, specification, row, model.penalty_xg)
        if mu is None and model.fallback_coefficients:
            coefficients = _coefficient_tuple(model.fallback_coefficients, "C")
            mu = _linear_prediction(coefficients, "C", row, model.penalty_xg)
            specification = "C"
        if mu is not None:
            basis = "zones" if specification in {"Z", "D"} else "volume"
    elif model.coefficients and not specification:
        sot = float(row.get("shots_on_target") or 0)
        total = float(row.get("shots") or sot)
        off_target = max(0.0, total - sot)
        mu = max(
            0.0,
            model.coefficients.get("intercept", 0.0)
            + model.coefficients.get("shots_on_target", 0.0) * sot
            + model.coefficients.get("off_target_shots", 0.0) * off_target,
        )
        basis = "volume"

    if mu is None:
        sot = int(row["shots_on_target"])
        rate, source = model.rate_for(str(row["competition_id"]), str(row["season"]))
        mu = sot * rate.mean
        sd = math.sqrt(
            max(0.0, sot * rate.mean * (1 - rate.mean)) + model.overdispersion * mu
        )
        low = min(sot * rate.low_p, max(0.0, mu - model.z * sd))
        high = max(sot * rate.high_p, mu + model.z * sd)
        open_xg = mu
        open_shots = shots_int or sot
        penalty_count = 0
        basis = "conversion"
        interval_basis = "conversion"
    else:
        if shots_int == 0:
            mu = 0.0
        open_xg, open_shots, penalty_count = _row_goal_inputs(
            row, mu, specification or "E", model.penalty_xg
        )
        low = max(0.0, min(mu, mu + model.interval_low_offset))
        high = max(mu, mu + model.interval_high_offset)
        interval_basis = model.interval_basis

    goals_low, goals_high = goal_range(
        open_xg=open_xg,
        open_shots=open_shots,
        penalties=penalty_count if penalties_known else 0,
        penalty_xg=model.penalty_xg,
        dispersion=model.goals_dispersion or 1.0,
        level=model.interval_level,
    )
    if shots_int == 0:
        goals_low = goals_high = 0
    goals_minus = (
        round(float(goals_int) - mu, 3) if goals_int is not None else None
    )
    position = _goal_position(goals_int, goals_low, goals_high)
    per_shot = (
        round(mu / shots_int, 3)
        if shots_int is not None and shots_int > 0
        else None
    )
    penalty_component = (
        round(model.penalty_xg * penalty_count, 3)
        if specification != "E" and penalties_known
        else 0.0
    )
    return {
        "fxg": round(mu, 3),
        "low": round(low, 3),
        "high": round(high, 3),
        "goals_low": goals_low,
        "goals_high": goals_high,
        "goals": goals_int,
        "goals_minus": goals_minus,
        "goals_position": position,
        "open_play_xg": round(open_xg, 3),
        "penalty_component": penalty_component,
        "penalties": penalty_count if penalties_known else None,
        "penalties_known": penalties_known,
        "xg_per_shot": per_shot,
        "shots": shots_int,
        "open_shots": open_shots,
        "basis": basis,
        "interval_basis": interval_basis,
        "goals_range_basis": model.goals_range_method,
        "model_id": model.model_id,
        **(
            {"rate": round(rate.mean, 4), "rate_source": source}
            if basis == "conversion"
            else {}
        ),
    }




def aggregate_fxg(model: FxGModel, rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    predictions: list[dict[str, Any]] = []
    valid_rows: list[dict[str, Any]] = []
    total_mu = 0.0
    total_goals = 0
    total_shots = 0
    total_sot = 0
    total_penalties = 0
    goal_rows: list[dict[str, float | int]] = []
    for row in rows:
        if not _valid_row(row):
            continue
        prediction = predict_fxg(model, row)
        mu = float(prediction["fxg"])
        predictions.append(prediction)
        valid_rows.append(row)
        total_mu += mu
        total_goals += int(row["goals_for"])
        total_shots += int(prediction.get("shots") or 0)
        total_sot += int(row["shots_on_target"])
        total_penalties += int(prediction.get("penalties") or 0)
        goal_rows.append(
            {
                "open_xg": float(prediction.get("open_play_xg") or 0.0),
                "open_shots": int(prediction.get("open_shots") or 0),
                "penalties": int(prediction.get("penalties") or 0),
            }
        )
    count = len(predictions)
    if not count:
        return {
            "matches": 0,
            "fxg": None,
            "low": None,
            "high": None,
            "goals": 0,
            "goals_low": None,
            "goals_high": None,
            "goals_minus_fxg": None,
            "goals_minus_low": None,
            "goals_minus_high": None,
            "goals_position": None,
            "shots": 0,
            "shots_on_target": 0,
            "penalties": 0,
            "xg_per_shot": None,
            "model_range_width": None,
            "goals_range_width": None,
            "interval_method": model.interval_basis,
            "goals_range_method": model.goals_range_method,
            "goals_dispersion": model.goals_dispersion,
        }

    if model.bootstrap_coefficients and model.specification:
        rng = random.Random(model.bootstrap_seed)
        sums: list[float] = []
        for coefficients in model.bootstrap_coefficients:
            values = _coefficient_tuple(coefficients, model.specification)
            total = 0.0
            for row, prediction in zip(valid_rows, predictions, strict=False):
                value = _linear_prediction(
                    values, model.specification, row, model.penalty_xg
                )
                if value is None:
                    value = float(prediction["fxg"])
                if model.residual_pool:
                    value += model.residual_pool[
                        rng.randrange(len(model.residual_pool))
                    ]
                total += max(0.0, value)
            sums.append(total)
        low = max(0.0, _quantile(sums, (1 - model.interval_level) / 2))
        high = min(float(total_shots), _quantile(sums, (1 + model.interval_level) / 2))
    else:
        low_variance = sum(
            max(0.0, float(prediction["fxg"]) - float(prediction["low"])) ** 2
            for prediction in predictions
        )
        high_variance = sum(
            max(0.0, float(prediction["high"]) - float(prediction["fxg"])) ** 2
            for prediction in predictions
        )
        low = max(0.0, total_mu - math.sqrt(low_variance))
        high = min(float(total_shots), total_mu + math.sqrt(high_variance))
    low = min(low, total_mu)
    high = max(high, total_mu)

    goals_low, goals_high = aggregate_goal_range(
        goal_rows,
        penalty_xg=model.penalty_xg,
        dispersion=model.goals_dispersion or 1.0,
        level=model.interval_level,
    )
    goals_position = _goal_position(total_goals, goals_low, goals_high)
    per_shot = round(total_mu / total_shots, 3) if total_shots else None
    return {
        "matches": count,
        "fxg": round(total_mu, 2),
        "low": round(low, 2),
        "high": round(high, 2),
        "goals": total_goals,
        "goals_low": goals_low,
        "goals_high": goals_high,
        "goals_minus_fxg": round(total_goals - total_mu, 2),
        "goals_minus_low": round(goals_low - total_mu, 2),
        "goals_minus_high": round(goals_high - total_mu, 2),
        "goals_position": goals_position,
        "shots": total_shots,
        "shots_on_target": total_sot,
        "penalties": total_penalties,
        "xg_per_shot": per_shot,
        "model_range_width": round(high - low, 2),
        "goals_range_width": goals_high - goals_low,
        "interval_method": model.interval_basis,
        "goals_range_method": model.goals_range_method,
        "goals_dispersion": model.goals_dispersion,
    }




def evaluate_transfer(
    model: FxGModel,
    rows: Iterable[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Informational out-of-season, cross-provider check. Never used to tune."""
    section = config.get("transfer_check") or {}
    season = str(section.get("season") or "2025-26")
    competition_id = str(section.get("competition_id") or "sco:premiership")
    source = str(section.get("source") or "api_football")
    pairs: list[tuple[float, float, dict[str, Any]]] = []
    match_keys: set[Any] = set()
    for row in rows:
        if str(row.get("season")) != season:
            continue
        if str(row.get("competition_id")) != competition_id:
            continue
        provider = row.get("provider_xg")
        if provider is None or row.get("shots_on_target") is None:
            continue
        prediction = predict_fxg(model, row)
        pairs.append((float(prediction["fxg"]), float(provider), prediction))
        key = row.get("match_key") or row.get("match_id") or row.get("fixture_id")
        if key is not None:
            match_keys.add(key)
    if len(pairs) < 20:
        return {
            "status": "unavailable",
            "season": season,
            "competition_id": competition_id,
            "source": source,
            "matches": len(match_keys),
            "team_rows": len(pairs),
            "tuned_on_holdout": False,
            "note": "Fewer than 20 provider-xG team rows in the transfer sample.",
        }
    predictions = [pair[0] for pair in pairs]
    actuals = [pair[1] for pair in pairs]
    metrics = _candidate_metrics(
        predictions,
        actuals,
        matches=len(match_keys),
        evaluation={
            "max_abs_bias": 0.20,
            "max_mae": 0.55,
            "calibration_slope_min": 0.60,
            "calibration_slope_max": 1.40,
        },
    )
    model_covered = sum(
        1
        for _prediction, actual, prediction in pairs
        if float(prediction["low"]) <= actual <= float(prediction["high"])
    )
    goals_covered = sum(
        1
        for _prediction, _actual, prediction in pairs
        if prediction.get("goals") is not None
        and prediction.get("goals_low") is not None
        and prediction.get("goals_high") is not None
        and int(prediction["goals_low"])
        <= int(prediction["goals"])
        <= int(prediction["goals_high"])
    )
    passed = bool(metrics["passed"])
    return {
        "status": "pass" if passed else "warn",
        "season": season,
        "competition_id": competition_id,
        "source": source,
        "matches": len(match_keys),
        "team_rows": len(pairs),
        "bias": metrics["bias"],
        "mae": metrics["mae"],
        "calibration_slope": metrics["calibration_slope"],
        "r2": metrics["r2"],
        "model_interval_coverage": round(model_covered / len(pairs), 3),
        "goals_range_coverage": round(goals_covered / len(pairs), 3),
        "thresholds": {
            "max_abs_bias": 0.20,
            "max_mae": 0.55,
            "calibration_slope_min": 0.60,
            "calibration_slope_max": 1.40,
        },
        "tuned_on_holdout": False,
        "note": (
            "Informational transfer check: 2025-26 and API-Football provider xG "
            "against a model fitted to 2026-27 football-data xG. It crosses "
            "season and provider and is never used for tuning."
        ),
    }


def fit_provider_calibration(
    pairs: Iterable[tuple[float, float]],
    *,
    season: str,
    competition_id: str,
    sample_matches: int,
    min_team_rows: int = 60,
    clamp_min: float = 0.0,
) -> ProviderCalibration | None:
    """Fit a provider-style xG calibration from (fxg, provider_xg) team rows.

    This is a calibration on the provider values supplied for one season, not a
    reconstruction of the provider's model. A small sample or zero fxG variance
    returns None.
    """
    points = [(float(x), float(y)) for x, y in pairs]
    if len(points) < max(2, min_team_rows):
        return None
    xs = [x for x, _y in points]
    ys = [y for _x, y in points]
    fit = _ols_fit(xs, ys)
    if fit is None:
        return None
    intercept, slope = fit
    errors = [abs(y - (intercept + slope * x)) for x, y in points]
    mean_y = sum(ys) / len(ys)
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in points)
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    loocv_errors: list[float] = []
    if len(points) > 2:
        for index, (x, y) in enumerate(points):
            rest = points[:index] + points[index + 1 :]
            leave_fit = _ols_fit([p[0] for p in rest], [p[1] for p in rest])
            if leave_fit is None:
                continue
            leave_intercept, leave_slope = leave_fit
            loocv_errors.append(abs(y - (leave_intercept + leave_slope * x)))
    return ProviderCalibration(
        season=season,
        competition_id=competition_id,
        intercept=round(intercept, 4),
        slope=round(slope, 4),
        clamp_min=clamp_min,
        sample_matches=sample_matches,
        sample_team_rows=len(points),
        in_sample_mae=round(sum(errors) / len(errors), 4),
        loocv_mae=round(sum(loocv_errors) / len(loocv_errors), 4) if loocv_errors else None,
        max_loocv_error=round(max(loocv_errors), 4) if loocv_errors else None,
        r2=round(1 - ss_res / ss_tot, 4) if ss_tot else None,
    )


def estimate_provider_xg(
    calibration: ProviderCalibration | None, fxg: float | None
) -> float | None:
    if calibration is None or fxg is None:
        return None
    value = calibration.intercept + calibration.slope * float(fxg)
    return round(max(calibration.clamp_min, value), 3)


def _ols_fit(xs: list[float], ys: list[float]) -> tuple[float, float] | None:
    """Return (intercept, slope) for y = a + b*x, or None if underdetermined."""
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    variance = sum((x - mean_x) ** 2 for x in xs)
    if variance == 0:
        return None
    slope = covariance / variance
    return mean_y - slope * mean_x, slope


def _ols_slope(xs: list[float], ys: list[float]) -> float | None:
    fit = _ols_fit(xs, ys)
    return fit[1] if fit is not None else None


def evaluate_fxg(
    model: FxGModel,
    rows: Iterable[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    if model.calibration_evaluation is not None:
        return dict(model.calibration_evaluation)
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

    coefficients = model.coefficients
    if model.specification in {"Z", "D"}:
        method = "calibrated_zone_volume"
    elif model.specification in {"C", "A"}:
        method = "calibrated_open_play_volume"
    elif coefficients:
        method = "calibrated_shot_volume"
    else:
        method = "shot_conversion"
    calibration = model.calibration_evaluation or {}
    return {
        "model_id": model.model_id,
        "label": model.label,
        "status": model.status,
        "method": method,
        "specification": model.specification,
        "features": list(model.features),
        "coefficients": (
            {key: round(value, 6) for key, value in coefficients.items()}
            if coefficients
            else None
        ),
        "fallback_coefficients": (
            {key: round(value, 6) for key, value in model.fallback_coefficients.items()}
            if model.fallback_coefficients
            else None
        ),
        "penalty_xg": round(model.penalty_xg, 4),
        "penalty_source": model.penalty_source,
        "interval_level": model.interval_level,
        "interval_method": "match_bootstrap_residual",
        "interval_basis": model.interval_basis,
        "interval_low_offset": round(model.interval_low_offset, 3),
        "interval_high_offset": round(model.interval_high_offset, 3),
        "bootstrap": {
            "draws": model.bootstrap_draws,
            "seed": model.bootstrap_seed,
            "valid_draws": len(model.bootstrap_coefficients),
            "cluster": "match",
        },
        "goals_range_method": model.goals_range_method,
        "goals_dispersion": model.goals_dispersion,
        "model_interval_coverage": calibration.get("model_interval_coverage"),
        "goals_range_coverage": calibration.get("goals_range_coverage"),
        "fit_matches": model.fit_matches,
        "fit_seasons": list(model.fit_seasons),
        "fit_team_rows": model.fit_team_rows,
        "fit_season": model.fit_season,
        "fit_competition": model.fit_competition,
        "calibration": model.calibration_evaluation,
        "selection": model.selection,
        "transfer_check": model.transfer_check,
        "prior_strength": model.prior_strength,
        "overdispersion": round(model.overdispersion, 4),
        "global_rate": rate_dict(model.global_rate),
        "rates": [rate_dict(rate) for rate in model.rates.values()],
        "competition_rates": [rate_dict(rate) for rate in model.competition_rates.values()],
        "evaluation": evaluation,
    }


__all__ = [
    "FxGModel",
    "ProviderCalibration",
    "Rate",
    "aggregate_fxg",
    "estimate_provider_xg",
    "evaluate_fxg",
    "evaluate_transfer",
    "fit_fxg",
    "fit_provider_calibration",
    "model_to_dict",
    "predict_fxg",
]
