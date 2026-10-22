from __future__ import annotations

import pytest

from fitba.analytics.xg import aggregate_fxg, evaluate_fxg, fit_fxg, predict_fxg

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


def test_empty_fit_raises() -> None:
    with pytest.raises(ValueError, match="no rows"):
        fit_fxg([], CONFIG)
