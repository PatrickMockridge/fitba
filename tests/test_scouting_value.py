from __future__ import annotations

from fitba.analytics.scouting_value import (
    anchor_report,
    fit_value_model,
    validate_anchor,
    value_for_row,
)

ROLES = ["goalkeeper", "centre_back", "central_midfield", "centre_forward"]
LEAGUES = ["sco:premiership", "eng:championship", "eng:league-two"]
AGES = [20, 25, 32]


def _anchor(index: int) -> dict:
    return {
        "player_key": f"api:player:{1000 + index}",
        "player_name": f"Player {index}",
        "league_id": LEAGUES[index % len(LEAGUES)],
        "role_family": ROLES[index % len(ROLES)],
        "age_at_value": AGES[index % len(AGES)],
        "value_gbp": 100_000 + index * 50_000,
        "value_kind": "fee",
        "value_date": "2026-08-01",
        "performance_season": "2025-26",
        "performance_minutes": 900 + index * 10,
        "performance_rating": 6.5,
        "performance_adjusted_percentile": 20 + (index % 70),
        "performance_mapping": "same_season",
        "source_id": "wikipedia",
        "source_url": "https://en.wikipedia.org/wiki/2025-26_example_season",
        "source_title": "Example season",
        "verified_at": "2026-10-23",
        "confidence": "reported",
        "note": "test anchor",
    }


def test_valid_anchor_and_gate_fit():
    anchors = [_anchor(index) for index in range(60)]
    for anchor in anchors:
        assert validate_anchor(anchor) == []
    report = anchor_report(anchors)
    assert report["gate"]["passed"] is True
    model = fit_value_model(anchors)
    assert model["state"] == "ready"
    assert model["sample"] == 60
    assert model["coefficients"] is not None
    assert model["loocv_mae"] is not None
    row = {
        "adjusted_percentile": 70.0,
        "age": 25,
        "minutes": 1200,
        "role_family": "central_midfield",
    }
    band = value_for_row(model, row)
    assert band["value_low_gbp"] is not None
    assert band["value_high_gbp"] is not None
    assert band["value_low_gbp"] < band["value_high_gbp"]


def test_gate_fails_below_the_anchor_minimum():
    report = anchor_report([_anchor(index) for index in range(59)])
    assert report["gate"]["passed"] is False
    model = fit_value_model([_anchor(index) for index in range(59)])
    assert model["state"] == "awaiting_anchors"
    band = value_for_row(model, {"adjusted_percentile": 70.0, "age": 25, "minutes": 1200})
    assert band["value_low_gbp"] is None
    assert band["value_method"] == "awaiting_anchors"


def test_prohibited_source_and_time_mismatch_are_rejected():
    anchor = _anchor(0)
    anchor["source_url"] = "https://www.transfermarkt.com/player"
    assert any("prohibited" in error for error in validate_anchor(anchor))
    anchor = _anchor(0)
    anchor["performance_season"] = "2022-23"
    assert any("align" in error for error in validate_anchor(anchor))
