from __future__ import annotations

from typing import Any

from fitba.analytics.league_stats import build_league_rankings


def _table_row(
    team_id: str,
    name: str,
    position: int,
    played: int,
    gf: int,
    ga: int,
    points: int,
) -> dict[str, Any]:
    return {
        "team_id": team_id,
        "team_name": name,
        "position": position,
        "played": played,
        "gf": gf,
        "ga": ga,
        "points": points,
        "season": "2026-27",
    }


def _feature(
    match_id: str,
    team_id: str,
    opponent_id: str,
    *,
    fdco: float | None,
    api: float | None = None,
    possession: float | None = 50.0,
) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "season": "2026-27",
        "competition_id": "sco:premiership",
        "team_id": team_id,
        "opponent_id": opponent_id,
        "provider_xg_fdco": fdco,
        "provider_xg_api": api,
        "possession": possession,
    }


def _rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    table = [
        _table_row("sco:aberdeen", "Aberdeen", 1, 2, 4, 1, 6),
        _table_row("sco:beta", "Beta", 2, 2, 2, 2, 3),
        _table_row("sco:gamma", "Gamma", 3, 2, 1, 4, 0),
    ]
    features = [
        _feature("m1", "sco:aberdeen", "sco:beta", fdco=2.0, possession=60.0),
        _feature("m1", "sco:beta", "sco:aberdeen", fdco=1.0, possession=40.0),
        _feature("m2", "sco:aberdeen", "sco:gamma", fdco=None, api=1.0, possession=55.0),
        _feature("m2", "sco:gamma", "sco:aberdeen", fdco=0.5, possession=45.0),
        _feature("m3", "sco:beta", "sco:gamma", fdco=2.0, possession=50.0),
        _feature("m3", "sco:gamma", "sco:beta", fdco=1.0, possession=50.0),
    ]
    return table, features


def _build(
    table: list[dict[str, Any]],
    features: list[dict[str, Any]],
    **kwargs: Any,
) -> dict[str, Any]:
    kwargs.setdefault("min_team_matches", 2)
    return build_league_rankings(
        table_rows=table,
        features=features,
        season="2026-27",
        generated_at="2026-11-08T00:00:00+00:00",
        **kwargs,
    )


def test_rates_ranks_and_ties() -> None:
    table, features = _rows()
    result = _build(table, features)

    assert result["state"] == "available"
    assert result["reason"] is None
    assert result["league_size"] == 3
    assert result["matches"] == 3
    assert result["team_rows"] == 6

    aberdeen = result["aberdeen"]
    assert aberdeen["values"] == {
        "xg_for_pm": 1.5,
        "xg_against_pm": 0.75,
        "possession_pct": 57.5,
        "goals_for_pm": 2.0,
        "goals_against_pm": 0.5,
        "gd_pm": 1.5,
    }
    assert aberdeen["ranks"] == {
        "xg_for_pm": 1,
        "xg_against_pm": 1,
        "possession_pct": 1,
        "goals_for_pm": 1,
        "goals_against_pm": 1,
        "gd_pm": 1,
    }

    beta = next(team for team in result["teams"] if team["team_id"] == "sco:beta")
    gamma = next(team for team in result["teams"] if team["team_id"] == "sco:gamma")
    # xG for is tied at 1.50, so both share first and Gamma is third.
    assert beta["ranks"]["xg_for_pm"] == 1
    assert gamma["ranks"]["xg_for_pm"] == 3
    # xG against is tied at 1.50 for Beta and Gamma, so both share second.
    assert beta["ranks"]["xg_against_pm"] == 2
    assert gamma["ranks"]["xg_against_pm"] == 2


def test_xg_against_uses_the_opponent_row() -> None:
    table, features = _rows()
    result = _build(table, features)
    aberdeen = result["aberdeen"]
    # Aberdeen conceded 1.0 in m1 and 0.5 in m2; the opponent rows supply both.
    assert aberdeen["values"]["xg_against_pm"] == 0.75


def test_provider_xg_falls_back_to_api() -> None:
    table, features = _rows()
    result = _build(table, features)
    assert result["coverage"]["provider_xg"]["fdco_rows"] == 5
    assert result["coverage"]["provider_xg"]["api_fallback_rows"] == 1
    assert result["coverage"]["provider_xg"]["complete"] is True


def test_missing_possession_is_unknown_not_zero() -> None:
    table, features = _rows()
    features[0]["possession"] = None
    result = _build(table, features)

    assert result["state"] == "partial"
    assert result["reason"] == "possession_coverage_incomplete"
    aberdeen = result["aberdeen"]
    assert aberdeen["values"]["possession_pct"] is None
    assert aberdeen["ranks"]["possession_pct"] is None
    for team in result["teams"]:
        assert team["ranks"]["possession_pct"] is None


def test_incomplete_coverage_can_still_rank_when_policy_allows() -> None:
    table, features = _rows()
    features[0]["possession"] = None
    result = _build(table, features, require_complete_coverage=False)

    aberdeen = result["aberdeen"]
    assert aberdeen["ranks"]["xg_for_pm"] == 1
    assert aberdeen["ranks"]["possession_pct"] is None


def test_minimum_matches_suppresses_ranks() -> None:
    table, features = _rows()
    result = _build(table, features, min_team_matches=4)

    assert result["state"] == "partial"
    assert result["reason"] == "below_min_team_matches"
    assert all(rank is None for team in result["teams"] for rank in team["ranks"].values())


def test_teams_outside_the_league_table_are_ignored() -> None:
    table, features = _rows()
    features.append(_feature("m9", "sco:other", "sco:aberdeen", fdco=9.0))
    result = _build(table, features)

    assert result["team_rows"] == 6
    assert all(team["team_id"] != "sco:other" for team in result["teams"])


def test_fxg_context_is_labelled_and_not_ranked() -> None:
    table, features = _rows()
    context = {
        "scope": "season",
        "season": "2026-27",
        "fxg": 15.42,
        "goals": 12,
        "goals_minus_fxg": -3.42,
        "matches": 12,
    }
    result = _build(table, features, fxg_context=context)

    assert result["aberdeen"]["context"] == {
        "fxg": 15.42,
        "goals": 12,
        "goals_minus_fxg": -3.42,
        "matches": 12,
        "ranked": False,
        "label": "fitba fxG (local model, not ranked)",
        "note": "fitba fxG is a local model and is not part of the provider-xG league rank.",
    }


def test_fxg_context_from_another_season_is_dropped() -> None:
    table, features = _rows()
    result = _build(
        table,
        features,
        fxg_context={"scope": "season", "season": "2025-26", "fxg": 1.0, "goals": 1},
    )
    assert result["aberdeen"]["context"] is None


def test_no_league_table_is_unavailable() -> None:
    result = _build([], [])
    assert result["state"] == "unavailable"
    assert result["reason"] == "league_table_unavailable"
    assert result["aberdeen"] is None
