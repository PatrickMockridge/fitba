"""Within-league team rankings for the season overview.

The builder joins the current league table to provider team-match features and
produces per-team rates, within-league ranks, medians and leaders. It is a pure
function: the caller supplies the table, the feature rows and the fxG context.
No cross-league comparison is made, and provider xG is never blended with the
local fxG model.
"""

from __future__ import annotations

import statistics
from typing import Any

COMPETITION_ID = "sco:premiership"

# The order is the display order on /analysis/. Direction is a property of the
# statistic, not a verdict: possession is ranked high-to-low because it is a
# share, not because more possession is always better.
RANKING_METRICS: list[dict[str, Any]] = [
    {
        "id": "xg_for_pm",
        "label": "xG for / match",
        "source": "provider_xg",
        "source_label": "Provider xG",
        "value_type": "xg",
        "direction": "higher_is_better",
        "direction_label": "Higher is better",
        "decimals": 2,
    },
    {
        "id": "xg_against_pm",
        "label": "xG against / match",
        "source": "provider_xg",
        "source_label": "Provider xG",
        "value_type": "xg",
        "direction": "lower_is_better",
        "direction_label": "Lower is better",
        "decimals": 2,
    },
    {
        "id": "possession_pct",
        "label": "Possession",
        "source": "api_football",
        "source_label": "API-Football",
        "value_type": "percent",
        "direction": "higher_is_better",
        "direction_label": "Higher is better",
        "decimals": 2,
    },
    {
        "id": "goals_for_pm",
        "label": "Goals scored / match",
        "source": "league_table",
        "source_label": "League table",
        "value_type": "goals",
        "direction": "higher_is_better",
        "direction_label": "Higher is better",
        "decimals": 2,
    },
    {
        "id": "goals_against_pm",
        "label": "Goals conceded / match",
        "source": "league_table",
        "source_label": "League table",
        "value_type": "goals",
        "direction": "lower_is_better",
        "direction_label": "Lower is better",
        "decimals": 2,
    },
    {
        "id": "gd_pm",
        "label": "Goal difference / match",
        "source": "league_table",
        "source_label": "League table",
        "value_type": "goals",
        "direction": "higher_is_better",
        "direction_label": "Higher is better",
        "decimals": 2,
    },
]

METRIC_BY_ID = {metric["id"]: metric for metric in RANKING_METRICS}


def _float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _provider_xg(row: dict[str, Any]) -> float | None:
    """Use the published provider-xG precedence: football-data, then API."""
    value = _float(row.get("provider_xg_fdco"))
    if value is None:
        value = _float(row.get("provider_xg_api"))
    return value


def _round(value: float | None, decimals: int = 2) -> float | None:
    return None if value is None else round(value, decimals)


def _rate(total: float | None, played: int) -> float | None:
    if total is None or played <= 0:
        return None
    return _round(total / played)


def _rank(values: list[float | None], higher_is_better: bool) -> list[int | None]:
    if any(value is None for value in values):
        return [None for _ in values]
    ranks: list[int | None] = []
    for value in values:
        assert value is not None
        better = sum(
            1
            for other in values
            if other is not None and (other > value if higher_is_better else other < value)
        )
        ranks.append(1 + better)
    return ranks


def _leader_teams(
    teams: list[dict[str, Any]], metric_id: str, higher: bool
) -> list[dict[str, str]]:
    values = [
        team["values"].get(metric_id) for team in teams if team["values"].get(metric_id) is not None
    ]
    if not values:
        return []
    best = max(values) if higher else min(values)
    return [
        {"team_id": team["team_id"], "team_name": team["team_name"]}
        for team in teams
        if team["values"].get(metric_id) == best
    ]


def _unavailable(
    *,
    season: str,
    generated_at: str,
    competition_id: str,
    competition_name: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "state": "unavailable",
        "reason": reason,
        "competition_id": competition_id,
        "competition_name": competition_name,
        "season": season,
        "scope": "league_only",
        "scope_label": f"Within the {competition_name} only",
        "as_of": generated_at,
        "league_size": 0,
        "matches": 0,
        "team_rows": 0,
        "coverage": {
            "table": {"teams": 0, "matches": 0, "complete": False},
            "provider_xg": {
                "source": "football_data_uk+api_football",
                "label": "Provider xG (football-data.co.uk; API-Football fallback)",
                "team_rows": 0,
                "team_rows_total": 0,
                "complete": False,
            },
            "possession": {
                "source": "api_football",
                "label": "Provider-reported possession",
                "team_rows": 0,
                "team_rows_total": 0,
                "complete": False,
            },
        },
        "metrics": RANKING_METRICS,
        "aberdeen": None,
        "league": {},
        "teams": [],
        "note": (
            "League rankings are unavailable in this build. No cross-league comparison is made."
        ),
    }


def _fxg_context(context: dict[str, Any] | None, season: str) -> dict[str, Any] | None:
    if not context:
        return None
    if str(context.get("season") or "") != season:
        return None
    if str(context.get("scope") or "") != "season":
        return None
    fxg = _float(context.get("fxg"))
    goals = _float(context.get("goals"))
    goals_minus_fxg = _float(context.get("goals_minus_fxg"))
    matches = context.get("matches")
    if fxg is None or goals is None:
        return None
    return {
        "fxg": _round(fxg),
        "goals": int(goals) if goals.is_integer() else _round(goals),
        "goals_minus_fxg": _round(goals_minus_fxg),
        "matches": int(matches) if matches is not None else None,
        "ranked": False,
        "label": "fitba fxG (local model, not ranked)",
        "note": ("fitba fxG is a local model and is not part of the provider-xG league rank."),
    }


def build_league_rankings(
    *,
    table_rows: list[dict[str, Any]],
    features: list[dict[str, Any]] | None,
    season: str,
    competition_id: str = COMPETITION_ID,
    competition_name: str = "Scottish Premiership",
    team_id: str = "sco:aberdeen",
    generated_at: str = "",
    min_team_matches: int = 4,
    require_complete_coverage: bool = True,
    fxg_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    table_by_team = {
        str(row.get("team_id")): row for row in table_rows if row.get("team_id") is not None
    }
    if not table_by_team or team_id not in table_by_team:
        return _unavailable(
            season=season,
            generated_at=generated_at,
            competition_id=competition_id,
            competition_name=competition_name,
            reason="league_table_unavailable",
        )

    scoped_features: list[dict[str, Any]] = []
    for row in features or []:
        row_team = str(row.get("team_id") or "")
        if row_team not in table_by_team:
            continue
        if row.get("season") is not None and str(row["season"]) != season:
            continue
        if row.get("competition_id") is not None and str(row["competition_id"]) != competition_id:
            continue
        scoped_features.append(row)

    lookup = {
        (str(row.get("match_id")), str(row.get("team_id"))): row
        for row in scoped_features
        if row.get("match_id") is not None
    }
    teams: list[dict[str, Any]] = []
    provider_rows = 0
    provider_rows_expected = 0
    fdco_rows = 0
    api_fallback_rows = 0
    possession_rows = 0
    possession_rows_expected = 0
    xg_against_complete = True
    all_possession_rows = True

    for table_row in sorted(
        table_by_team.values(), key=lambda item: int(item.get("position") or 999)
    ):
        current_id = str(table_row.get("team_id"))
        played = int(table_row.get("played") or 0)
        own_rows = [row for row in scoped_features if str(row.get("team_id")) == current_id]
        own_rows.sort(key=lambda item: str(item.get("date") or ""))

        xg_for_values: list[float] = []
        xg_against_values: list[float] = []
        possession_values: list[float] = []
        for row in own_rows:
            own_xg = _provider_xg(row)
            if own_xg is not None:
                xg_for_values.append(own_xg)
                provider_rows += 1
                if _float(row.get("provider_xg_fdco")) is not None:
                    fdco_rows += 1
                elif _float(row.get("provider_xg_api")) is not None:
                    api_fallback_rows += 1
            opponent = lookup.get((str(row.get("match_id")), str(row.get("opponent_id"))))
            opponent_xg = _provider_xg(opponent or {})
            if opponent_xg is not None:
                xg_against_values.append(opponent_xg)
            possession = _float(row.get("possession"))
            if possession is not None:
                possession_values.append(possession)
                possession_rows += 1

        provider_rows_expected += played
        possession_rows_expected += played
        xg_for_complete = len(xg_for_values) == played
        xg_against_team_complete = len(xg_against_values) == played
        possession_team_complete = len(possession_values) == played
        if not xg_against_team_complete:
            xg_against_complete = False
        if not possession_team_complete:
            all_possession_rows = False

        goals_for = int(table_row.get("gf") or 0)
        goals_against = int(table_row.get("ga") or 0)
        values = {
            "xg_for_pm": _rate(sum(xg_for_values), played) if xg_for_complete else None,
            "xg_against_pm": (
                _rate(sum(xg_against_values), played) if xg_against_team_complete else None
            ),
            "possession_pct": (
                _round(statistics.mean(possession_values)) if possession_team_complete else None
            ),
            "goals_for_pm": _rate(float(goals_for), played),
            "goals_against_pm": _rate(float(goals_against), played),
            "gd_pm": _rate(float(goals_for - goals_against), played),
        }
        teams.append(
            {
                "team_id": current_id,
                "team_name": table_row.get("team_name"),
                "position": table_row.get("position"),
                "played": played,
                "points": table_row.get("points"),
                "values": values,
                "ranks": {metric["id"]: None for metric in RANKING_METRICS},
            }
        )

    provider_complete = (
        provider_rows == provider_rows_expected
        and provider_rows_expected > 0
        and xg_against_complete
    )
    possession_complete = (
        possession_rows == possession_rows_expected
        and possession_rows_expected > 0
        and all_possession_rows
    )
    table_complete = bool(teams) and all(int(team["played"]) > 0 for team in teams)
    aberdeen = next((team for team in teams if team["team_id"] == team_id), None)
    played = int(table_by_team[team_id].get("played") or 0)
    below_minimum = played < min_team_matches
    covered = provider_complete and possession_complete and table_complete
    state = "available" if covered and not below_minimum else "partial"
    reason = None
    if below_minimum:
        reason = "below_min_team_matches"
    elif not provider_complete:
        reason = "provider_coverage_incomplete"
    elif not possession_complete:
        reason = "possession_coverage_incomplete"
    elif not table_complete:
        reason = "league_table_incomplete"

    ranks_enabled = not below_minimum and (state == "available" or not require_complete_coverage)
    if ranks_enabled and aberdeen is not None:
        for metric in RANKING_METRICS:
            metric_id = metric["id"]
            higher = metric["direction"] == "higher_is_better"
            values = [team["values"].get(metric_id) for team in teams]
            ranks = _rank(values, higher)
            for team, rank in zip(teams, ranks, strict=False):
                team["ranks"][metric_id] = rank

    league: dict[str, Any] = {}
    for metric in RANKING_METRICS:
        metric_id = metric["id"]
        higher = metric["direction"] == "higher_is_better"
        values = [
            team["values"].get(metric_id)
            for team in teams
            if team["values"].get(metric_id) is not None
        ]
        if not values:
            league[metric_id] = {
                "median": None,
                "mean": None,
                "ranked_teams": 0,
                "leader_value": None,
                "leader_teams": [],
            }
            continue
        best = max(values) if higher else min(values)
        league[metric_id] = {
            "median": _round(statistics.median(values)),
            "mean": _round(statistics.mean(values)),
            "ranked_teams": len(values),
            "leader_value": _round(best),
            "leader_teams": _leader_teams(teams, metric_id, higher),
        }

    team_rows = len(scoped_features)
    matches = len(
        {str(row.get("match_id")) for row in scoped_features if row.get("match_id") is not None}
    )
    note = (
        "Ranks are within the Scottish Premiership only. Provider xG is one "
        "provider's model, not fitba fxG; the two are never blended. Possession "
        "is provider-reported and is not used in the matchday style lean."
    )
    context = _fxg_context(fxg_context, season)
    if aberdeen is not None:
        aberdeen["context"] = context
    return {
        "state": state,
        "reason": reason,
        "competition_id": competition_id,
        "competition_name": competition_name,
        "season": season,
        "scope": "league_only",
        "scope_label": f"Within the {competition_name} only",
        "as_of": generated_at,
        "league_size": len(teams),
        "matches": matches,
        "team_rows": team_rows,
        "coverage": {
            "table": {
                "teams": len(teams),
                "matches": sum(int(team["played"]) for team in teams) // 2,
                "complete": table_complete,
            },
            "provider_xg": {
                "source": "football_data_uk+api_football",
                "label": "Provider xG (football-data.co.uk; API-Football fallback)",
                "team_rows": provider_rows,
                "team_rows_total": provider_rows_expected,
                "fdco_rows": fdco_rows,
                "api_fallback_rows": api_fallback_rows,
                "complete": provider_complete,
            },
            "possession": {
                "source": "api_football",
                "label": "Provider-reported possession",
                "team_rows": possession_rows,
                "team_rows_total": possession_rows_expected,
                "complete": possession_complete,
                "note": (
                    "Possession can sum to 99 or 101 on a single match; the "
                    "season average is descriptive."
                ),
            },
        },
        "metrics": RANKING_METRICS,
        "aberdeen": aberdeen,
        "league": league,
        "teams": teams,
        "note": note,
    }


__all__ = ["COMPETITION_ID", "RANKING_METRICS", "build_league_rankings"]
