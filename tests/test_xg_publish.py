from __future__ import annotations

from fitba.analytics.xg import ProviderCalibration
from fitba.publish.xg import _manager_split_row, _provider_basis

CALIBRATION = ProviderCalibration(
    season="2026-27",
    competition_id="sco:premiership",
    intercept=0.5,
    slope=0.7,
    clamp_min=0.0,
    sample_matches=35,
    sample_team_rows=70,
    in_sample_mae=0.0,
    loocv_mae=0.0,
    max_loocv_error=0.0,
    r2=1.0,
)


def _row(
    *,
    fxg_for: float | None = 1.0,
    fxg_against: float | None = 2.0,
    provider_for: float | None = None,
    provider_against: float | None = None,
    goals_for: int = 1,
    goals_against: int = 1,
    date: str = "2026-08-01",
) -> dict:
    return {
        "date": date,
        "fxg_for": fxg_for,
        "fxg_against": fxg_against,
        "provider_xg_for": provider_for,
        "provider_xg_against": provider_against,
        "goals_for": goals_for,
        "goals_against": goals_against,
    }


def _segment(rows: list[dict], name: str = "Stephen Robinson") -> dict:
    return {
        "rows": rows,
        "stint_id": "stephen-robinson-manager-2026",
        "person_id": "stephen-robinson",
        "name": name,
        "interim": False,
        "stint_start": "2026-03-12",
        "stint_end": None,
        "first_match": rows[0]["date"],
        "last_match": rows[-1]["date"],
    }


def _split(rows: list[dict], **kwargs) -> dict:
    return _manager_split_row(
        _segment(rows),
        season="2026-27",
        calibration=CALIBRATION,
        target_season="2026-27",
        prior_season="2025-26",
        focus_person_id="stephen-robinson",
        **kwargs,
    )


def test_actual_provider_values_are_separate_from_the_estimate() -> None:
    split = _split(
        [
            _row(provider_for=1.2, provider_against=2.1),
            _row(provider_for=0.8, provider_against=1.9),
        ]
    )
    assert split["provider_basis"] == "actual"
    assert split["provider_actual_matches"] == 2
    assert split["provider_actual_for"] == 2.0
    assert split["provider_actual_against"] == 4.0
    assert split["provider_estimate_matches"] == 2
    assert split["provider_estimate_for"] == 2.4
    assert split["provider_estimate_against"] == 3.8


def test_estimated_provider_values_are_labelled() -> None:
    split = _split([_row(), _row()])
    assert split["provider_basis"] == "estimate"
    assert split["provider_actual_matches"] == 0
    assert split["provider_actual_for"] is None
    assert split["provider_estimate_matches"] == 2
    assert split["provider_estimate_for"] == 2.4


def test_partial_actual_coverage_is_not_filled_with_estimates() -> None:
    split = _split([_row(provider_for=1.2, provider_against=2.1), _row()])
    assert split["provider_basis"] == "actual_partial"
    assert split["provider_actual_matches"] == 1
    assert split["provider_actual_for"] == 1.2
    assert split["provider_estimate_matches"] == 2
    assert split["provider_estimate_for"] == 2.4


def test_missing_fxg_makes_the_provider_estimate_unavailable() -> None:
    split = _split([_row(fxg_for=None, fxg_against=None)])
    assert split["provider_basis"] == "unavailable"
    assert split["provider_estimate_for"] is None
    assert split["provider_estimate_matches"] == 0


def test_provider_basis_values() -> None:
    assert _provider_basis(2, 2, 2) == "actual"
    assert _provider_basis(1, 2, 2) == "actual_partial"
    assert _provider_basis(0, 2, 2) == "estimate"
    assert _provider_basis(0, 2, 0) == "unavailable"
