"""Publish fxG model detail, match values and aggregates."""

from __future__ import annotations

from typing import Any

import polars as pl

from fitba.analytics.xg import (
    aggregate_fxg,
    evaluate_fxg,
    fit_fxg,
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
from fitba.settings import xg_policy
from fitba.util.dates import current_season, utc_now_iso

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
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at or utc_now_iso(),
        "season": season or current_season(),
        "state": "available",
        "model": model_to_dict(model, evaluation),
        "evaluation": evaluation,
        "matches": matches,
        "aggregates": aggregates,
        "coverage": {
            "matches": len(matches),
            "with_fxg": with_fxg,
            "with_provider_xg": with_provider,
            "missing_team_stats": len(matches) - with_fxg,
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
