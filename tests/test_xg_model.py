from __future__ import annotations

import pytest

from fitba.analytics.xg import (
    aggregate_fxg,
    estimate_provider_xg,
    evaluate_fxg,
    fit_fxg,
    fit_provider_calibration,
    predict_fxg,
)

CONFIG = {
    "model_id": "test-fxg",
    "label": "fxG",
    "status": "experimental",
    "fit": {
        "before_season": "2026-27",
        "min_shots_on_target": 1,
        "prior_strength_sot": 10,
        "exclude_competition_prefixes": ["sco:other:friendlies"],
    },
    "interval": {"level": 0.8, "draws": 300, "seed": 7, "z": 1.2816},
    "evaluation": {
        "validation_season": "2026-27",
        "max_abs_bias": 1.0,
        "max_mae": 1.0,
        "calibration_slope_min": 0.1,
        "calibration_slope_max": 3.0,
    },
}


def _rows() -> list[dict]:
    rows = []
    for season, competition, sot, goals in (
        ("2024-25", "sco:premiership", 5, 1),
        ("2024-25", "sco:premiership", 8, 3),
        ("2025-26", "sco:premiership", 6, 2),
        ("2025-26", "sco:premiership", 4, 1),
    ):
        rows.append(
            {
                "season": season,
                "competition_id": competition,
                "goals_for": goals,
                "shots": sot + 4,
                "shots_on_target": sot,
                "provider_xg": None,
            }
        )
    return rows


def test_fit_predict_and_aggregate_are_ordered() -> None:
    model = fit_fxg(_rows(), CONFIG)
    prediction = predict_fxg(model, _rows()[0])
    assert prediction["low"] <= prediction["fxg"] <= prediction["high"]
    assert prediction["model_id"] == "test-fxg"

    aggregate = aggregate_fxg(model, _rows())
    assert aggregate["matches"] == 4
    assert aggregate["fxg"] is not None
    assert aggregate["low"] <= aggregate["fxg"] <= aggregate["high"]
    assert aggregate["goals"] == 7


def test_evaluation_uses_provider_xg_and_gate() -> None:
    rows = _rows()
    rows.extend(
        [
            {
                "season": "2026-27",
                "competition_id": "sco:premiership",
                "goals_for": 2,
                "shots": 9,
                "shots_on_target": 5,
                "provider_xg": 1.8,
            },
            {
                "season": "2026-27",
                "competition_id": "sco:premiership",
                "goals_for": 1,
                "shots": 7,
                "shots_on_target": 3,
                "provider_xg": 1.1,
            },
        ]
    )
    model = fit_fxg(rows, CONFIG)
    evaluation = evaluate_fxg(model, rows, CONFIG)
    assert evaluation["matches"] == 2
    assert evaluation["team_rows"] == 2
    assert evaluation["status"] in {"pass", "fail"}
    assert evaluation["bias"] is not None
    assert evaluation["mae"] is not None


def test_provider_calibration_recovers_an_exact_line() -> None:
    pairs = [(float(x), 0.5 + 0.7 * float(x)) for x in range(1, 71)]
    calibration = fit_provider_calibration(
        pairs,
        season="2026-27",
        competition_id="sco:premiership",
        sample_matches=35,
        min_team_rows=10,
    )
    assert calibration is not None
    assert calibration.intercept == pytest.approx(0.5)
    assert calibration.slope == pytest.approx(0.7)
    assert calibration.in_sample_mae == pytest.approx(0.0)
    assert calibration.loocv_mae == pytest.approx(0.0)
    assert calibration.sample_team_rows == 70
    assert calibration.sample_matches == 35


def test_provider_calibration_needs_enough_rows() -> None:
    calibration = fit_provider_calibration(
        [(1.0, 1.0), (2.0, 2.0)],
        season="2026-27",
        competition_id="sco:premiership",
        sample_matches=1,
        min_team_rows=10,
    )
    assert calibration is None


def test_provider_estimate_clamps_and_handles_unknowns() -> None:
    pairs = [(float(x), 0.5 + 0.7 * float(x)) for x in range(1, 71)]
    calibration = fit_provider_calibration(
        pairs,
        season="2026-27",
        competition_id="sco:premiership",
        sample_matches=35,
        min_team_rows=10,
    )
    assert calibration is not None
    assert estimate_provider_xg(calibration, 0.0) == pytest.approx(0.5)
    assert estimate_provider_xg(calibration, -10.0) == pytest.approx(0.0)
    assert estimate_provider_xg(calibration, None) is None
    assert estimate_provider_xg(None, 1.0) is None


def test_empty_fit_raises() -> None:
    with pytest.raises(ValueError, match="no rows"):
        fit_fxg([], CONFIG)


CALIBRATED_CONFIG = {
    **CONFIG,
    "model_id": "test-fxg-2",
    "calibration": {
        "season": "2026-27",
        "competition_id": "sco:premiership",
        "min_team_rows": 6,
        "min_matches": 3,
    },
    "evaluation": {
        "method": "leave_one_match_out",
        "validation_season": "2026-27",
        "max_abs_bias": 1.0,
        "max_mae": 1.0,
        "calibration_slope_min": 0.1,
        "calibration_slope_max": 3.0,
    },
}


def _calibration_rows() -> list[dict]:
    rows = _rows()
    samples = [
        (5, 4, 1.8),
        (4, 2, 1.4),
        (6, 5, 2.1),
        (3, 3, 1.0),
        (5, 1, 1.5),
        (4, 6, 1.6),
    ]
    for index, (sot, off, provider) in enumerate(samples):
        rows.append(
            {
                "match_key": f"match-{index // 2}",
                "season": "2026-27",
                "competition_id": "sco:premiership",
                "goals_for": 1,
                "shots": sot + off,
                "shots_on_target": sot,
                "provider_xg": provider,
            }
        )
    return rows


def test_calibrated_model_differentiates_equal_sot() -> None:
    model = fit_fxg(_calibration_rows(), CALIBRATED_CONFIG)
    assert model.model_id == "test-fxg-2"
    assert model.coefficients is not None
    assert model.fit_team_rows == 6
    assert model.fit_season == "2026-27"
    assert model.calibration_evaluation is not None
    assert model.calibration_evaluation["method"] == "leave_one_match_out"
    low_sot = {"shots": 9, "shots_on_target": 5, "goals_for": 1}
    high_sot = {"shots": 13, "shots_on_target": 5, "goals_for": 1}
    low_prediction = predict_fxg(model, low_sot)
    high_prediction = predict_fxg(model, high_sot)
    assert low_prediction["basis"] in {"calibrated_shot_volume", "volume"}
    assert low_prediction["fxg"] != high_prediction["fxg"]
    assert low_prediction["low"] <= low_prediction["fxg"] <= low_prediction["high"]
    evaluation = evaluate_fxg(model, _calibration_rows(), CALIBRATED_CONFIG)
    assert evaluation["team_rows"] == 6
    assert evaluation["matches"] == 3


ENRICHED_CONFIG = {
    **CALIBRATED_CONFIG,
    "model_id": "test-fxg-3",
    "calibration": {
        "season": "2026-27",
        "competition_id": "sco:premiership",
        "min_team_rows": 6,
        "min_matches": 3,
        "min_zone_coverage": 0.8,
    },
    "penalty": {"xg": 0.76},
    "interval": {"level": 0.8, "bootstrap_draws": 20, "seed": 7, "z": 1.2816},
}


def _enriched_rows() -> list[dict]:
    rows = _rows()
    samples = [
        (6, 4, 2, 1, 0, 0),
        (4, 3, 2, 1, 0, 0),
        (7, 5, 2, 1, 0, 1),
        (3, 2, 3, 2, 1, 0),
        (5, 3, 3, 2, 1, 0),
        (8, 6, 2, 1, 0, 0),
    ]
    for index, (inside, outside, sot, off, blocked, penalties) in enumerate(samples):
        shots = inside + outside
        provider = 0.76 * penalties + 0.1 * inside + 0.08 * outside + 0.05 * sot
        rows.append(
            {
                "match_key": f"enriched-{index}",
                "season": "2026-27",
                "competition_id": "sco:premiership",
                "goals_for": 1,
                "shots": shots,
                "shots_on_target": sot,
                "shots_off": off,
                "shots_blocked": blocked,
                "shots_insidebox": inside,
                "shots_outsidebox": outside,
                "penalty_attempts": penalties,
                "penalty_goals": penalties,
                "penalty_missed": 0,
                "penalty_status": "available",
                "open_play_shots": shots - penalties,
                "open_play_sot": max(0, sot - penalties),
                "open_play_off": off,
                "open_play_blocked": blocked,
                "open_play_insidebox": max(0, inside - penalties),
                "open_play_outsidebox": outside,
                "zone_status": "available",
                "reconciliation_status": "ok",
                "provider_xg": provider,
                "provider_xg_open_play_fdco": provider - 0.76 * penalties,
            }
        )
    return rows


def test_enriched_model_has_penalties_and_two_ranges() -> None:
    model = fit_fxg(_enriched_rows(), ENRICHED_CONFIG)
    assert model.model_id == "test-fxg-3"
    assert model.specification in {"C", "A", "Z", "D", "E"}
    assert model.penalty_xg == pytest.approx(0.76)
    prediction = predict_fxg(model, _enriched_rows()[-1])
    assert prediction["goals_low"] <= prediction["goals_high"]
    assert prediction["low"] <= prediction["fxg"] <= prediction["high"]
    assert prediction["basis"] in {"zones", "volume"}
    aggregate = aggregate_fxg(model, _enriched_rows())
    assert aggregate["goals_low"] <= aggregate["goals_high"]
    assert aggregate["model_range_width"] is not None
