"""Publish fxG model detail, match values and aggregates."""

from __future__ import annotations

from typing import Any

import polars as pl

from fitba.analytics.history import flatten_stints, manager_match_segments
from fitba.analytics.xg import (
    ProviderCalibration,
    aggregate_fxg,
    estimate_provider_xg,
    evaluate_fxg,
    fit_fxg,
    fit_provider_calibration,
    model_to_dict,
    predict_fxg,
)
from fitba.ingest.history import (
    HISTORY_DIR,
    load_history_fixtures,
    load_history_team_stats,
)
from fitba.ingest.runner import load_matches
from fitba.normalize.fixture_registry import ABERDEEN_ID, FixtureRecord, build_fixture_registry
from fitba.settings import history_staff, xg_policy
from fitba.util.dates import current_season, previous_season, utc_now_iso

SCHEMA_VERSION = "1.0.0"
SOURCES = [
    {
        "id": "football_data_uk",
        "name": "football-data.co.uk",
        "layer": "league_results",
        "note": "League shots, shots on target, goals and 2026-27 provider xG.",
    },
    {
        "id": "api_football",
        "name": "API-Football",
        "layer": "match_statistics",
        "note": "Cup and European team statistics, including provider xG where returned.",
    },
]


def _num(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _league_rows(matches: pl.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in matches.to_dicts():
        match_key = f"fdco:{row['match_id']}"
        common = {
            "match_key": match_key,
            "season": str(row.get("season")),
            "competition_id": str(row.get("competition_id")),
            "source": "football_data_uk",
            "provider_xg": None,
        }
        rows.append(
            {
                **common,
                "team_id": str(row.get("home_team_id")),
                "opponent_id": str(row.get("away_team_id")),
                "goals_for": _num(row.get("home_goals")),
                "shots": _num(row.get("home_shots")),
                "shots_on_target": _num(row.get("home_shots_on_target")),
                "provider_xg": _float(row.get("home_xg")),
            }
        )
        rows.append(
            {
                **common,
                "team_id": str(row.get("away_team_id")),
                "opponent_id": str(row.get("home_team_id")),
                "goals_for": _num(row.get("away_goals")),
                "shots": _num(row.get("away_shots")),
                "shots_on_target": _num(row.get("away_shots_on_target")),
                "provider_xg": _float(row.get("away_xg")),
            }
        )
    return rows


def _history_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not HISTORY_DIR.exists():
        return rows
    for path in sorted(HISTORY_DIR.glob("season=*")):
        if not path.is_dir():
            continue
        season = path.name.split("=", 1)[1]
        fixtures = load_history_fixtures(season)
        stats = load_history_team_stats(season)
        if not fixtures.height or not stats.height:
            continue
        fixture_by_id = {int(row["fixture_id"]): row for row in fixtures.to_dicts()}
        for row in stats.to_dicts():
            fixture = fixture_by_id.get(int(row["fixture_id"]))
            if fixture is None:
                continue
            competition_id = str(fixture.get("competition_id") or "")
            if competition_id == "sco:premiership":
                continue
            team_id = _num(row.get("team_id"))
            if team_id is None:
                continue
            home_id = _num(fixture.get("home_team_id"))
            away_id = _num(fixture.get("away_team_id"))
            goals_for = (
                _num(fixture.get("home_goals"))
                if team_id == home_id
                else _num(fixture.get("away_goals"))
            )
            rows.append(
                {
                    "match_key": f"api:{fixture['fixture_id']}",
                    "season": season,
                    "competition_id": competition_id,
                    "team_id": str(team_id),
                    "team_name": str(row.get("team_name") or ""),
                    "opponent_id": str(away_id if team_id == home_id else home_id),
                    "opponent_name": str(
                        fixture.get("away_team_name")
                        if team_id == home_id
                        else fixture.get("home_team_name")
                    ),
                    "goals_for": goals_for,
                    "shots": _num(row.get("shots")),
                    "shots_on_target": _num(row.get("shots_on_target")),
                    "provider_xg": _float(row.get("expected_goals")),
                    "source": "api_football",
                }
            )
    return rows


def _model_rows() -> list[dict[str, Any]]:
    return [*_league_rows(load_matches(None)), *_history_rows()]


def _team_rows(
    fixture: FixtureRecord,
    by_key_team: dict[tuple[str, str], dict[str, Any]],
    by_key_name: dict[tuple[str, str], dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    key = f"fdco:{fixture.match_id}" if fixture.match_id else f"api:{fixture.fixture_id}"
    if fixture.match_id:
        return (
            by_key_team.get((key, str(fixture.home_team_id))),
            by_key_team.get((key, str(fixture.away_team_id))),
        )
    return (
        by_key_name.get((key, fixture.home_team_name.casefold())),
        by_key_name.get((key, fixture.away_team_name.casefold())),
    )


def _prediction(row: dict[str, Any] | None, model: Any) -> dict[str, Any] | None:
    if row is None or row.get("shots_on_target") is None:
        return None
    return predict_fxg(model, row)


def _match_rows(
    registry: Any,
    model: Any,
    by_key_team: dict[tuple[str, str], dict[str, Any]],
    by_key_name: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for fixture in registry.played():
        home_row, away_row = _team_rows(fixture, by_key_team, by_key_name)
        home_pred = _prediction(home_row, model)
        away_pred = _prediction(away_row, model)
        rows_for_side = (
            (home_pred, away_pred)
            if fixture.home_team_id == ABERDEEN_ID
            else (away_pred, home_pred)
        )
        for_pred, against_pred = rows_for_side
        goals_for = fixture.home_goals if fixture.is_aberdeen_home else fixture.away_goals
        goals_against = fixture.away_goals if fixture.is_aberdeen_home else fixture.home_goals
        if fixture.is_aberdeen_home:
            provider_for = home_row.get("provider_xg") if home_row else None
            provider_against = away_row.get("provider_xg") if away_row else None
        else:
            provider_for = away_row.get("provider_xg") if away_row else None
            provider_against = home_row.get("provider_xg") if home_row else None
        output.append(
            {
                "fixture_id": fixture.fixture_id,
                "season": fixture.season,
                "date": fixture.date,
                "competition_id": fixture.competition_id,
                "opponent_id": fixture.opponent_id,
                "opponent_name": fixture.opponent_name,
                "venue": fixture.venue,
                "goals_for": goals_for,
                "goals_against": goals_against,
                "fxg_for": for_pred["fxg"] if for_pred else None,
                "fxg_for_low": for_pred["low"] if for_pred else None,
                "fxg_for_high": for_pred["high"] if for_pred else None,
                "fxg_against": against_pred["fxg"] if against_pred else None,
                "fxg_against_low": against_pred["low"] if against_pred else None,
                "fxg_against_high": against_pred["high"] if against_pred else None,
                "fxg_diff": (
                    round(for_pred["fxg"] - against_pred["fxg"], 3)
                    if for_pred and against_pred
                    else None
                ),
                "fxg_diff_low": (
                    round(for_pred["low"] - against_pred["high"], 3)
                    if for_pred and against_pred
                    else None
                ),
                "fxg_diff_high": (
                    round(for_pred["high"] - against_pred["low"], 3)
                    if for_pred and against_pred
                    else None
                ),
                "provider_xg_for": provider_for,
                "provider_xg_against": provider_against,
                "source": (home_row or away_row or {}).get("source"),
            }
        )
    return output


def _league_stats_rows(
    registry: Any,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_key_team = {(row["match_key"], row["team_id"]): row for row in rows}
    output: list[dict[str, Any]] = []
    for fixture in registry.played():
        if fixture.competition_id != "sco:premiership":
            continue
        key = f"fdco:{fixture.match_id}" if fixture.match_id else f"api:{fixture.fixture_id}"
        row = by_key_team.get((key, ABERDEEN_ID))
        if row is not None:
            output.append({**row, "fixture_id": fixture.fixture_id, "date": fixture.date})
    return output


def _aggregates(
    model: Any,
    registry: Any,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    league_rows = _league_stats_rows(registry, rows)
    output: list[dict[str, Any]] = []
    for season in sorted({str(row["season"]) for row in league_rows}):
        group = [row for row in league_rows if str(row["season"]) == season]
        aggregate = aggregate_fxg(model, group)
        output.append(
            {
                "scope": "season",
                "season": season,
                "competition_id": "sco:premiership",
                **aggregate,
            }
        )
    era = aggregate_fxg(model, league_rows)
    output.append(
        {
            "scope": "era",
            "season": "2019-20 to 2026-27",
            "competition_id": "sco:premiership",
            **era,
        }
    )
    recent = sorted(league_rows, key=lambda row: str(row.get("date") or ""))[-10:]
    output.append(
        {
            "scope": "last10",
            "season": "last 10 league matches",
            "competition_id": "sco:premiership",
            **aggregate_fxg(model, recent),
        }
    )
    return output


def _provider_calibration_pairs(
    rows: list[dict[str, Any]],
    model: Any,
    section: dict[str, Any],
) -> tuple[list[tuple[float, float]], int]:
    season = str(section.get("season") or "2026-27")
    competition_id = str(section.get("competition_id") or "sco:premiership")
    points: list[tuple[float, float]] = []
    for row in rows:
        if str(row.get("season")) != season:
            continue
        if str(row.get("competition_id")) != competition_id:
            continue
        if row.get("provider_xg") is None or row.get("shots_on_target") is None:
            continue
        prediction = predict_fxg(model, row)
        points.append((float(prediction["fxg"]), float(row["provider_xg"])))
    return points, len(points) // 2


def _provider_estimate_block(
    calibration: ProviderCalibration | None,
    section: dict[str, Any],
    *,
    reason: str | None = None,
) -> dict[str, Any]:
    season = str(section.get("season") or "2026-27")
    competition_id = str(section.get("competition_id") or "sco:premiership")
    sample = {
        "season": season,
        "competition_id": competition_id,
        "matches": calibration.sample_matches if calibration else 0,
        "team_rows": calibration.sample_team_rows if calibration else 0,
        "source": "football_data_uk",
    }
    limitations = [
        "This is an estimate, not provider xG.",
        (
            "Provider xG uses shot locations and a provider model; this record "
            "has no shot coordinates."
        ),
        (
            "The calibration is fit on 2026-27 league team rows only; applying "
            "it to earlier seasons assumes a stable relationship."
        ),
        "The calibration does not mean the provider-xG gate has passed.",
    ]
    if calibration is None:
        return {
            "status": "unavailable",
            "label": "Calibrated provider-xG estimate",
            "basis": "estimate",
            "method": "ols",
            "reason": reason or "insufficient provider-xG calibration rows",
            "sample": sample,
            "source": "football-data.co.uk 2026-27 SC0 HxG/AxG",
            "limitations": limitations,
        }
    return {
        "status": "available",
        "label": "Calibrated provider-xG estimate",
        "basis": "estimate",
        "method": "ols",
        "formula": "provider_xg_estimate = max(clamp_min, intercept + slope * fxg)",
        "coefficients": {
            "intercept": calibration.intercept,
            "slope": calibration.slope,
        },
        "clamp_min": calibration.clamp_min,
        "sample": sample,
        "in_sample_mae": calibration.in_sample_mae,
        "loocv_mae": calibration.loocv_mae,
        "max_loocv_error": calibration.max_loocv_error,
        "r2": calibration.r2,
        "loocv_basis": "team_row",
        "source": "football-data.co.uk 2026-27 SC0 HxG/AxG",
        "limitations": limitations,
    }


def _provider_basis(actual_matches: int, matches: int, estimate_matches: int) -> str:
    if matches and actual_matches == matches:
        return "actual"
    if actual_matches and actual_matches < matches:
        return "actual_partial"
    if matches and estimate_matches == matches:
        return "estimate"
    return "unavailable"


def _manager_split_row(
    segment: dict[str, Any],
    *,
    season: str,
    calibration: ProviderCalibration | None,
    target_season: str,
    prior_season: str,
    focus_person_id: str,
    scope: str = "manager_stint",
) -> dict[str, Any]:
    rows = segment.get("rows") or []
    matches = len(rows)
    fxg_for = sum(float(row["fxg_for"]) for row in rows if row.get("fxg_for") is not None)
    fxg_against = sum(
        float(row["fxg_against"]) for row in rows if row.get("fxg_against") is not None
    )
    fxg_for_count = sum(1 for row in rows if row.get("fxg_for") is not None)
    fxg_against_count = sum(1 for row in rows if row.get("fxg_against") is not None)
    goals_for = sum(int(row.get("goals_for") or 0) for row in rows)
    goals_against = sum(int(row.get("goals_against") or 0) for row in rows)
    actual = [
        row
        for row in rows
        if row.get("provider_xg_for") is not None and row.get("provider_xg_against") is not None
    ]
    actual_for = sum(float(row["provider_xg_for"]) for row in actual) if actual else None
    actual_against = sum(float(row["provider_xg_against"]) for row in actual) if actual else None
    estimates = [
        (
            estimate_provider_xg(calibration, row.get("fxg_for")),
            estimate_provider_xg(calibration, row.get("fxg_against")),
        )
        for row in rows
    ]
    estimate_pairs = [(f, a) for f, a in estimates if f is not None and a is not None]
    estimate_for = sum(f for f, _a in estimate_pairs) if estimate_pairs else None
    estimate_against = sum(a for _f, a in estimate_pairs) if estimate_pairs else None
    basis = _provider_basis(len(actual), matches, len(estimate_pairs))
    person_id = segment.get("person_id")
    role = (
        "current"
        if season == target_season and person_id == focus_person_id
        else "previous"
        if season == prior_season and person_id == focus_person_id
        else "context"
    )

    def rate(value: float | None) -> float | None:
        return round(value / matches, 3) if value is not None and matches else None

    return {
        "season": season,
        "competition_id": "sco:premiership",
        "scope": scope,
        "stint_id": segment.get("stint_id"),
        "person_id": person_id,
        "manager": segment.get("name"),
        "interim": bool(segment.get("interim")),
        "stint_start": segment.get("stint_start"),
        "stint_end": segment.get("stint_end"),
        "first_match": segment.get("first_match"),
        "last_match": segment.get("last_match"),
        "matches": matches,
        "fxg_for": round(fxg_for, 2) if fxg_for_count else None,
        "fxg_against": round(fxg_against, 2) if fxg_against_count else None,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "goals_minus_fxg_for": round(goals_for - fxg_for, 2) if fxg_for_count else None,
        "goals_minus_fxg_against": (
            round(goals_against - fxg_against, 2) if fxg_against_count else None
        ),
        "provider_actual_for": round(actual_for, 2) if actual_for is not None else None,
        "provider_actual_against": (
            round(actual_against, 2) if actual_against is not None else None
        ),
        "provider_actual_matches": len(actual),
        "provider_estimate_for": round(estimate_for, 2) if estimate_for is not None else None,
        "provider_estimate_against": (
            round(estimate_against, 2) if estimate_against is not None else None
        ),
        "provider_estimate_matches": len(estimate_pairs),
        "provider_basis": basis,
        "comparison_role": role,
        "per_match": {
            "fxg_for": rate(fxg_for if fxg_for_count else None),
            "fxg_against": rate(fxg_against if fxg_against_count else None),
            "goals_for": rate(float(goals_for)),
            "goals_against": rate(float(goals_against)),
            "goals_minus_fxg_for": (rate(goals_for - fxg_for) if fxg_for_count else None),
            "goals_minus_fxg_against": (
                rate(goals_against - fxg_against) if fxg_against_count else None
            ),
            "provider_actual_for": rate(actual_for),
            "provider_actual_against": rate(actual_against),
            "provider_estimate_for": rate(estimate_for),
            "provider_estimate_against": rate(estimate_against),
        },
        "coverage": {
            "matches": matches,
            "with_fxg": min(fxg_for_count, fxg_against_count),
            "with_provider_actual": len(actual),
            "with_provider_estimate": len(estimate_pairs),
            "note": (
                "League only; provider xG is actual where supplied and a calibrated "
                "estimate otherwise. They are never summed."
            ),
        },
    }


def _manager_splits(
    matches: list[dict[str, Any]],
    *,
    target_season: str,
    calibration: ProviderCalibration | None,
    focus_person_id: str,
) -> list[dict[str, Any]]:
    prior = previous_season(target_season)
    stints = flatten_stints(history_staff().get("people", []))
    league = pl.DataFrame(
        [
            row
            for row in matches
            if row.get("competition_id") == "sco:premiership"
            and row.get("season") in {target_season, prior}
        ]
    )
    output: list[dict[str, Any]] = []
    if league.height:
        for season in (target_season, prior):
            frame = league.filter(pl.col("season") == season)
            for segment in manager_match_segments(frame, stints):
                output.append(
                    _manager_split_row(
                        segment,
                        season=season,
                        calibration=calibration,
                        target_season=target_season,
                        prior_season=prior,
                        focus_person_id=focus_person_id,
                    )
                )
    if league.height:
        prior_rows = league.filter(pl.col("season") == prior).to_dicts()
        if prior_rows:
            context = {
                "rows": prior_rows,
                "stint_id": None,
                "person_id": None,
                "name": f"Full {prior}",
                "interim": False,
                "stint_start": None,
                "stint_end": None,
                "first_match": prior_rows[0].get("date"),
                "last_match": prior_rows[-1].get("date"),
            }
            output.append(
                _manager_split_row(
                    context,
                    season=prior,
                    calibration=calibration,
                    target_season=target_season,
                    prior_season=prior,
                    focus_person_id=focus_person_id,
                    scope="season_context",
                )
            )
    output.sort(
        key=lambda row: (
            0 if row["season"] == target_season else 1,
            1 if row.get("scope") == "season_context" else 0,
            str(row.get("first_match") or ""),
        )
    )
    return output


def build_xg_payload(
    *,
    season: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    config = xg_policy()
    rows = _model_rows()
    model = fit_fxg(rows, config)
    evaluation = evaluate_fxg(model, rows, config)
    registry = build_fixture_registry()
    by_key_team = {(row["match_key"], row["team_id"]): row for row in rows}
    by_key_name = {
        (row["match_key"], str(row.get("team_name") or "").casefold()): row
        for row in rows
        if row.get("team_name")
    }
    matches = _match_rows(registry, model, by_key_team, by_key_name)
    aggregates = _aggregates(model, registry, rows)
    with_fxg = sum(1 for row in matches if row["fxg_for"] is not None)
    with_provider = sum(1 for row in matches if row["provider_xg_for"] is not None)
    target_season = season or current_season()

    provider_section = config.get("provider_estimate") or {}
    points, sample_matches = _provider_calibration_pairs(rows, model, provider_section)
    try:
        calibration = fit_provider_calibration(
            points,
            season=str(provider_section.get("season") or "2026-27"),
            competition_id=str(provider_section.get("competition_id") or "sco:premiership"),
            sample_matches=sample_matches,
            min_team_rows=int(provider_section.get("min_team_rows") or 60),
            clamp_min=float(provider_section.get("clamp_min") or 0.0),
        )
    except Exception as error:  # noqa: BLE001 - calibration failure is visible, not fatal
        calibration = None
        calibration_reason = f"calibration_failed:{type(error).__name__}"
    else:
        calibration_reason = None
    provider_estimate = _provider_estimate_block(
        calibration,
        provider_section,
        reason=calibration_reason,
    )
    manager_splits = _manager_splits(
        matches,
        target_season=target_season,
        calibration=calibration,
        focus_person_id=str(provider_section.get("comparison_person_id") or ""),
    )
    prior_season = previous_season(target_season)
    league_rows = [row for row in matches if row.get("competition_id") == "sco:premiership"]
    coverage_provider_actual = {
        "total_matches": with_provider,
        "league_2026_27": sum(
            1
            for row in league_rows
            if row.get("season") == target_season and row.get("provider_xg_for") is not None
        ),
        "league_2025_26": sum(
            1
            for row in league_rows
            if row.get("season") == prior_season and row.get("provider_xg_for") is not None
        ),
        "conference_2025_26": sum(
            1
            for row in matches
            if row.get("season") == "2025-26"
            and row.get("competition_id") == "uefa:conference-league"
            and row.get("provider_xg_for") is not None
        ),
        "conference_2023_24": sum(
            1
            for row in matches
            if row.get("season") == "2023-24"
            and row.get("competition_id") == "uefa:conference-league"
            and row.get("provider_xg_for") is not None
        ),
        "note": (
            "The six 2025-26 Conference provider rows were under Thelin and are "
            "excluded from the league manager splits."
        ),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at or utc_now_iso(),
        "season": target_season,
        "state": "available",
        "model": model_to_dict(model, evaluation),
        "evaluation": evaluation,
        "matches": matches,
        "aggregates": aggregates,
        "provider_estimate": provider_estimate,
        "manager_splits": manager_splits,
        "coverage": {
            "matches": len(matches),
            "with_fxg": with_fxg,
            "with_provider_xg": with_provider,
            "missing_team_stats": len(matches) - with_fxg,
            "provider_actual": coverage_provider_actual,
            "manager_splits": {
                "seasons": [target_season, prior_season],
                "competition_id": "sco:premiership",
                "rows": len(manager_splits),
                "unattributed_matches": sum(
                    row.get("matches", 0)
                    for row in manager_splits
                    if row.get("person_id") is None and row.get("scope") == "manager_stint"
                ),
                "note": "League only. Managers are attributed by match date.",
            },
            "note": (
                "fxG needs shots on target. Missing provider team statistics are "
                "shown as unavailable, not zero."
            ),
        },
        "sources": SOURCES,
    }


def fallback_xg_payload(previous: dict[str, Any] | None, reason: str) -> dict[str, Any]:
    if previous:
        payload = dict(previous)
        payload["state"] = "stale"
        payload["stale_reason"] = reason
        return payload
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "season": current_season(),
        "state": "unavailable",
        "stale_reason": reason,
        "model": None,
        "evaluation": None,
        "matches": [],
        "aggregates": [],
        "coverage": {"matches": 0, "with_fxg": 0, "with_provider_xg": 0, "missing_team_stats": 0},
        "sources": SOURCES,
    }


__all__ = ["build_xg_payload", "fallback_xg_payload"]
