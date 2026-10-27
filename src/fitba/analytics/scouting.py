"""Scouting model: cohorts, rating percentiles, archetypes and the board.

All inputs are local normalized data. The model never fetches; the ingest
commands write the parquet, and the publish builder reads it. Unknown values
stay null and are never treated as zero.

The model is descriptive. Provider ratings are relative to a league and role
cohort, not a verdict; the archetypes are profiles built from fields the
licensed feed supplies, not positions or recommendations.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from math import floor
from statistics import NormalDist, fmean, median, pstdev
from typing import Any

import polars as pl

from fitba.analytics.percentiles import midrank_percentile
from fitba.analytics.player_facts import club_totals, stat_rows, totals
from fitba.settings import NORMALIZED_DIR
from fitba.settings import player_rose as load_player_rose
from fitba.settings import scouting_value as load_scouting_value

RATE_FIELDS = [
    "goals_p90",
    "assists_p90",
    "goals_assists_p90",
    "shots_p90",
    "dribbles_success_p90",
    "passes_completed_p90",
    "key_passes_p90",
    "tackles_p90",
    "interceptions_p90",
    "pass_completion_pct",
    "duel_win_pct",
    "dribble_success_pct",
    "conversion_pct",
    "save_pct",
    "conceded_p90",
    "saves_p90",
]



def per90(value: Any, minutes: Any) -> float | None:
    if value is None or minutes is None:
        return None
    minutes = int(minutes)
    if minutes <= 0:
        return None
    return round(float(value) * 90 / minutes, 2)


def ratio(numerator: Any, denominator: Any, *, scale: float = 100.0) -> float | None:
    if numerator is None or denominator is None:
        return None
    denominator = float(denominator)
    if denominator <= 0:
        return None
    return round(float(numerator) / denominator * scale, 2)


def player_rates(row: dict[str, Any]) -> dict[str, float | None]:
    minutes = row.get("minutes")
    goals = row.get("goals")
    assists = row.get("assists")
    contribution = None if goals is None and assists is None else (goals or 0) + (assists or 0)
    passes = row.get("passes_total")
    accuracy = row.get("pass_accuracy")
    completed = (
        float(passes) * float(accuracy) / 100.0
        if passes is not None and accuracy is not None
        else None
    )
    return {
        "goals_p90": per90(goals, minutes),
        "assists_p90": per90(assists, minutes),
        "goals_assists_p90": per90(contribution, minutes),
        "shots_p90": per90(row.get("shots_total"), minutes),
        "dribbles_success_p90": per90(row.get("dribbles_success"), minutes),
        "passes_completed_p90": per90(completed, minutes),
        "key_passes_p90": per90(row.get("passes_key"), minutes),
        "tackles_p90": per90(row.get("tackles"), minutes),
        "interceptions_p90": per90(row.get("interceptions"), minutes),
        "pass_completion_pct": round(float(accuracy), 2) if accuracy is not None else None,
        "duel_win_pct": ratio(row.get("duels_won"), row.get("duels_total")),
        "dribble_success_pct": ratio(row.get("dribbles_success"), row.get("dribbles_attempts")),
        "conversion_pct": ratio(goals, row.get("shots_total")),
        "save_pct": ratio(
            row.get("saves"),
            None
            if row.get("saves") is None and row.get("conceded") is None
            else (row.get("saves") or 0) + (row.get("conceded") or 0),
        ),
        "conceded_p90": per90(row.get("conceded"), minutes),
        "saves_p90": per90(row.get("saves"), minutes),
    }


def quantile(values: Iterable[float], q: float) -> float | None:
    items = sorted(float(value) for value in values)
    if not items:
        return None
    position = (len(items) - 1) * q
    low = floor(position)
    high = min(low + 1, len(items) - 1)
    fraction = position - low
    return items[low] + (items[high] - items[low]) * fraction


def robust_z(
    value: float,
    values: Iterable[float],
    *,
    winsor_low: float,
    winsor_high: float,
) -> float | None:
    items = sorted(float(item) for item in values)
    if not items:
        return None
    low = quantile(items, winsor_low)
    high = quantile(items, winsor_high)
    assert low is not None and high is not None
    clipped = [min(max(item, low), high) for item in items]
    point = min(max(float(value), low), high)
    centre = median(clipped)
    mad = median([abs(item - centre) for item in clipped])
    scale = 1.4826 * mad
    if scale <= 0:
        spread = pstdev(clipped)
        if spread <= 0:
            return 0.0
        return (point - fmean(clipped)) / spread
    return (point - centre) / scale


class CohortIndex:
    """Cohorts by league and role family, with rating and feature values."""

    def __init__(
        self,
        rows: list[dict[str, Any]],
        model: dict[str, Any],
        *,
        exclude_player_ids: set[int] | None = None,
    ):
        self.model = model
        self.exclude_player_ids = exclude_player_ids or set()
        self.rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        self.groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        self._values_cache: dict[tuple[str, str, str, int], list[float]] = {}
        self._group_values_cache: dict[tuple[str, str, str, int], list[float]] = {}
        for row in rows:
            player_id = row.get("player_id")
            if (
                self.exclude_player_ids
                and player_id is not None
                and int(player_id) in self.exclude_player_ids
            ):
                continue
            family = row.get("role_family")
            league = row.get("competition_id")
            group = _ROSE_GROUP_KEYS.get(str(row.get("position_group") or "").upper())
            if family and league:
                self.rows[(str(league), str(family))].append(row)
            if group and league:
                self.groups[(str(league), group)].append(row)

    def players(
        self,
        league: str,
        family: str,
        *,
        min_minutes: int,
        feature: str | None = None,
    ) -> list[dict[str, Any]]:
        out = []
        for row in self.rows.get((league, family), []):
            if int(row.get("minutes") or 0) < min_minutes:
                continue
            if feature is not None and row.get("rates", {}).get(feature) is None:
                continue
            out.append(row)
        return out

    def values(self, league: str, family: str, feature: str, *, min_minutes: int) -> list[float]:
        key = (league, family, feature, min_minutes)
        cached = self._values_cache.get(key)
        if cached is not None:
            return cached
        values = [
            float(row["rates"][feature])
            for row in self.players(league, family, min_minutes=min_minutes, feature=feature)
            if row.get("rates", {}).get(feature) is not None
        ]
        self._values_cache[key] = values
        return values

    def group_values(
        self, league: str, group: str, feature: str, *, min_minutes: int
    ) -> list[float]:
        key = (league, group, feature, min_minutes)
        cached = self._group_values_cache.get(key)
        if cached is not None:
            return cached
        values = [
            float(row["rates"][feature])
            for row in self.groups.get((league, group), [])
            if int(row.get("minutes") or 0) >= min_minutes
            and row.get("rates", {}).get(feature) is not None
        ]
        self._group_values_cache[key] = values
        return values


def rating_cohort(
    index: CohortIndex,
    league: str,
    family: str,
    *,
    min_minutes: int,
) -> list[float]:
    return [
        float(row["rating"])
        for row in index.players(league, family, min_minutes=min_minutes)
        if row.get("rating") is not None
    ]


def _min_cohort(model: dict[str, Any], family: str | None) -> int:
    pool = model.get("pool") or {}
    by_family = pool.get("min_cohort_by_family") or {}
    return int(by_family.get(family) or pool.get("min_cohort") or 25)


_ROSE_GROUP_KEYS = {
    "GK": "goalkeeper",
    "DEF": "defender",
    "MID": "midfielder",
    "FWD": "forward",
    "GOALKEEPER": "goalkeeper",
    "DEFENDER": "defender",
    "MIDFIELDER": "midfielder",
    "FORWARD": "forward",
}


def _rose_group(position_group: str | None) -> str | None:
    if not position_group:
        return None
    return _ROSE_GROUP_KEYS.get(str(position_group).upper())


def _rose_basis(
    *,
    league: str,
    family: str | None,
    group: str | None,
    index: CohortIndex,
    model: dict[str, Any],
    cohort_min_minutes: int,
) -> tuple[str, int]:
    pool = model.get("pool") or {}
    if family:
        size = len(index.players(league, family, min_minutes=cohort_min_minutes))
        if size >= _min_cohort(model, family):
            return "role_family", size
    if group:
        fallback_min = int(pool.get("fallback_group_min") or pool.get("min_cohort") or 15)
        size = len(
            [
                row
                for row in index.groups.get((league, group), [])
                if int(row.get("minutes") or 0) >= cohort_min_minutes
            ]
        )
        if size >= fallback_min:
            return "provider_group", size
    return "insufficient", 0


def _rose_axes(
    metrics: list[str],
    *,
    rates: dict[str, Any],
    league: str,
    family: str | None,
    group: str | None,
    basis: str,
    index: CohortIndex,
    model: dict[str, Any],
    catalogue: dict[str, Any],
    cohort_min_minutes: int,
) -> list[dict[str, Any]]:
    fallback_min = int(
        (model.get("pool") or {}).get("fallback_group_min")
        or (model.get("pool") or {}).get("min_cohort")
        or 15
    )
    axes: list[dict[str, Any]] = []
    for metric in metrics:
        definition = catalogue.get(metric) or {}
        value = rates.get(metric)
        percentile = None
        cohort_n = 0
        if value is not None and basis != "insufficient":
            if basis == "role_family" and family:
                cohort = index.values(league, family, metric, min_minutes=cohort_min_minutes)
                required = _min_cohort(model, family)
            elif basis == "provider_group" and group:
                cohort = index.group_values(league, group, metric, min_minutes=cohort_min_minutes)
                required = fallback_min
            else:
                cohort = []
                required = fallback_min
            cohort_n = len(cohort)
            point = -float(value) if definition.get("direction") == "negative" else float(value)
            values = (
                [-item for item in cohort] if definition.get("direction") == "negative" else cohort
            )
            if len(values) >= required:
                percentile = midrank_percentile(point, values)
        axes.append(
            {
                "metric": metric,
                "value": value,
                "percentile": percentile,
                "cohort_n": cohort_n,
            }
        )
    return axes


def _rose_figure(
    figure_id: str,
    label: str,
    axes: list[dict[str, Any]],
    *,
    min_petals: int,
    blocked: str | None,
) -> dict[str, Any]:
    available = sum(1 for axis in axes if axis.get("percentile") is not None)
    if blocked:
        status = "unavailable"
    elif available >= min_petals:
        status = "available"
    elif available:
        status = "partial"
    else:
        status = "unavailable"
    return {
        "id": figure_id,
        "label": label,
        "status": status,
        "axes": axes,
    }


def build_rose(
    rates: dict[str, Any],
    *,
    minutes: int,
    league: str,
    league_label: str,
    family: str | None,
    position_group: str | None,
    index: CohortIndex,
    model: dict[str, Any],
    config: dict[str, Any],
    player_min_minutes: int,
    cohort_min_minutes: int,
) -> dict[str, Any]:
    """Build the two-petal-set rose block for one player.

    Both figures use the same cohort. Values are league-only rates; missing
    values stay null and missing petals are not drawn at zero.
    """
    catalogue = config.get("catalogue") or {}
    group = _rose_group(position_group)
    overall_key = "goalkeeper" if family == "goalkeeper" or group == "goalkeeper" else "outfield"
    overall_metrics = list((config.get("overall") or {}).get(overall_key) or [])
    if family and family in (config.get("positions") or {}):
        position_metrics = list((config["positions"] or {}).get(family) or [])
    elif group and group in (config.get("groups") or {}):
        position_metrics = list((config["groups"] or {}).get(group) or [])
    else:
        position_metrics = []

    if minutes < player_min_minutes:
        reason = "below_min_minutes"
        basis, cohort_n = "insufficient", 0
    elif not family and not group:
        reason = "no_role"
        basis, cohort_n = "insufficient", 0
    else:
        reason = None
        basis, cohort_n = _rose_basis(
            league=league,
            family=family,
            group=group,
            index=index,
            model=model,
            cohort_min_minutes=cohort_min_minutes,
        )
        if basis == "insufficient":
            reason = "cohort_too_small"

    blocked = reason if basis == "insufficient" or minutes < player_min_minutes else None
    overall_axes = _rose_axes(
        overall_metrics,
        rates=rates,
        league=league,
        family=family,
        group=group,
        basis=basis,
        index=index,
        model=model,
        catalogue=catalogue,
        cohort_min_minutes=cohort_min_minutes,
    )
    position_axes = _rose_axes(
        position_metrics,
        rates=rates,
        league=league,
        family=family,
        group=group,
        basis=basis,
        index=index,
        model=model,
        catalogue=catalogue,
        cohort_min_minutes=cohort_min_minutes,
    )
    min_petals = int(config.get("min_petals") or 4)
    figures = [
        _rose_figure(
            "overall", "Overall profile", overall_axes, min_petals=min_petals, blocked=blocked
        ),
        _rose_figure(
            "position", "Position profile", position_axes, min_petals=min_petals, blocked=blocked
        ),
    ]
    if all(figure["status"] == "available" for figure in figures):
        status = "available"
    elif any(figure["status"] in {"available", "partial"} for figure in figures):
        status = "partial"
    else:
        status = "unavailable"
    if status == "unavailable" and reason is None:
        reason = "no_values"
    return {
        "status": status,
        "reason": reason,
        "league": league,
        "league_label": league_label,
        "minutes": minutes,
        "min_minutes": player_min_minutes,
        "cohort_min_minutes": cohort_min_minutes,
        "basis": basis,
        "cohort_n": cohort_n,
        "figures": figures,
    }


def archetype_scores(
    rates: dict[str, Any],
    *,
    league: str,
    family: str | None,
    minutes: int,
    index: CohortIndex,
    archetypes: dict[str, Any],
    model: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Score every applicable archetype; null when the profile is not meaningful."""
    out: dict[str, dict[str, Any]] = {}
    if not family:
        return out
    params = model.get("archetypes") or {}
    min_minutes = int(params.get("min_minutes") or 450)
    shrink = float(params.get("shrink_minutes") or 450)
    min_coverage = float(params.get("min_weight_coverage") or 0.7)
    low = float(params.get("winsor_low") or 0.01)
    high = float(params.get("winsor_high") or 0.99)
    for archetype_id, definition in (archetypes.get("archetypes") or {}).items():
        if family not in (definition.get("families") or []):
            continue
        weights = definition.get("features") or {}
        total_weight = sum(abs(float(weight)) for weight in weights.values())
        if total_weight <= 0:
            continue
        present: list[tuple[float, float]] = []
        for feature, weight in weights.items():
            point = rates.get(feature)
            if point is None:
                continue
            values = index.values(league, family, feature, min_minutes=min_minutes)
            if len(values) < 5:
                continue
            z = robust_z(float(point), values, winsor_low=low, winsor_high=high)
            if z is None:
                continue
            shrink_factor = int(minutes) / (int(minutes) + shrink) if minutes > 0 else 0.0
            present.append((float(weight), z * shrink_factor))
        coverage = sum(abs(weight) for weight, _ in present) / total_weight
        if coverage < min_coverage or not present:
            out[archetype_id] = {"score": None, "coverage": round(coverage, 3)}
            continue
        composite = sum(weight * z for weight, z in present) / sum(
            abs(weight) for weight, _ in present
        )
        out[archetype_id] = {
            "score": round(100.0 * NormalDist().cdf(composite), 1),
            "coverage": round(coverage, 3),
        }
    return out


def _squad_stats(
    player: dict[str, Any],
    *,
    competition: str | None = None,
) -> dict[str, Any]:
    if competition is None:
        return club_totals(player) or {"rating": None}
    rows = stat_rows(player, scope="club", competition=competition)
    return totals(rows, scope="league") or {"rating": None}


def _history_seasons(current: str, limit: int) -> list[str]:
    root = NORMALIZED_DIR / "history"
    if not root.exists():
        return []
    seasons = sorted(
        (path.name.split("=", 1)[1] for path in root.glob("season=*") if "=" in path.name),
        reverse=True,
    )
    return [season for season in seasons if season < current][:limit]


ROSE_HISTORY_PATH = NORMALIZED_DIR / "scouting" / "rose_history.parquet"
ROSE_LEAGUE = "sco:premiership"
ROSE_LEAGUE_LABEL = "Scottish Premiership"
ROSE_HISTORY_COMPETITIONS = ("Premiership", "Scottish Premiership")


def season_label(year: int) -> str:
    return f"{int(year)}-{str(int(year) + 1)[-2:]}"


def _history_season_year(season: str) -> int | None:
    try:
        return int(str(season)[:4])
    except ValueError:
        return None


def _history_role(player_id: int, season: str) -> str | None:
    path = NORMALIZED_DIR / "history" / f"season={season}" / "appearances.parquet"
    if not path.exists():
        return None
    frame = pl.read_parquet(path).filter(
        (pl.col("player_id") == int(player_id)) & pl.col("role_family").is_not_null()
    )
    if not frame.height:
        return None
    counts = (
        frame.group_by(["role_family", "role_code"])
        .agg(pl.len().alias("starts"))
        .sort(["starts", "role_code"], descending=[True, False])
    )
    return str(counts.row(0, named=True)["role_family"])


def _history_position_group(player_id: int, season: str) -> str | None:
    year = _history_season_year(season)
    if year is not None and ROSE_HISTORY_PATH.exists():
        frame = pl.read_parquet(ROSE_HISTORY_PATH).filter(
            (pl.col("player_id") == int(player_id))
            & (pl.col("season") == year)
        )
        if frame.height:
            group = frame.row(0, named=True).get("position_group")
            if group and group != "UNKNOWN":
                return str(group)
    path = NORMALIZED_DIR / "history" / f"season={season}" / "player_match_stats.parquet"
    if path.exists():
        frame = pl.read_parquet(path).filter(pl.col("player_id") == int(player_id))
        if frame.height:
            position = str(frame.row(0, named=True).get("position") or "").upper()
            mapping = {"G": "GK", "D": "DEF", "M": "MID", "F": "FWD"}
            return mapping.get(position[0] if position else "")
    return None


def history_player_totals(player_id: int, season: str) -> dict[str, Any]:
    """Player totals for a prior season, preferring the full Premiership pool."""
    year = _history_season_year(season)
    if year is not None and ROSE_HISTORY_PATH.exists():
        pool = pl.read_parquet(ROSE_HISTORY_PATH).filter(
            (pl.col("player_id") == int(player_id))
            & (pl.col("season") == year)
            & (pl.col("competition_id") == ROSE_LEAGUE)
        )
        if pool.height:
            row = pool.row(0, named=True)
            return {**row, "source": "provider_pool"}
    path = NORMALIZED_DIR / "history" / f"season={season}" / "player_match_stats.parquet"
    if not path.exists():
        return {"source": "unavailable"}
    frame = pl.read_parquet(path).filter(
        (pl.col("player_id") == int(player_id))
        & pl.col("competition").is_in(ROSE_HISTORY_COMPETITIONS)
    )
    if not frame.height:
        return {"source": "unavailable"}
    totals: dict[str, Any] = {}
    for field in (
        "appearances",
        "starts",
        "minutes",
        "goals",
        "assists",
        "yellow_cards",
        "red_cards",
        "shots_total",
        "shots_on",
        "passes_total",
        "passes_key",
        "saves",
        "conceded",
        "tackles",
        "blocks",
        "interceptions",
        "duels_won",
        "dribbles_attempts",
        "dribbles_success",
        "fouls_drawn",
        "fouls_committed",
        "penalty_scored",
        "penalty_saved",
    ):
        if field in frame.columns:
            values = frame[field].drop_nulls()
            totals[field] = int(values.sum()) if values.len() else None
    totals["duels_total"] = None
    total_passes = 0.0
    weighted_accuracy = 0.0
    if "passes_total" in frame.columns and "pass_accuracy" in frame.columns:
        for row in frame.to_dicts():
            passes = row.get("passes_total")
            accuracy = row.get("pass_accuracy")
            if passes is not None and accuracy is not None:
                total_passes += float(passes)
                weighted_accuracy += float(passes) * float(accuracy)
    totals["pass_accuracy"] = (
        round(weighted_accuracy / total_passes, 2) if total_passes else None
    )
    ratings = frame["rating"].drop_nulls() if "rating" in frame.columns else []
    totals["rating"] = (
        round(fmean([float(value) for value in ratings]), 2)
        if len(ratings)
        else None
    )
    totals["source"] = "aberdeen_fixtures"
    return totals


def load_rose_history_indices(model: dict[str, Any]) -> dict[str, CohortIndex]:
    if not ROSE_HISTORY_PATH.exists():
        return {}
    frame = pl.read_parquet(ROSE_HISTORY_PATH)
    output: dict[str, CohortIndex] = {}
    for year in frame["season"].unique().to_list():
        rows: list[dict[str, Any]] = []
        season_rows = frame.filter(
            (pl.col("season") == year)
            & (pl.col("competition_id") == ROSE_LEAGUE)
            & (pl.col("team_id") != 252)
        )
        for row in season_rows.to_dicts():
            if row.get("position_group") in {None, "UNKNOWN"}:
                continue
            rows.append(
                {
                    **row,
                    "competition_id": ROSE_LEAGUE,
                    "season": season_label(int(year)),
                    "role_family": None,
                    "rates": player_rates(row),
                }
            )
        if rows:
            output[season_label(int(year))] = CohortIndex(rows, model)
    return output


def _fallback_rose(
    player: dict[str, Any],
    *,
    season: str,
    current_rose: dict[str, Any],
    history: dict[str, CohortIndex],
    model: dict[str, Any],
    config: dict[str, Any],
    player_min: int,
    cohort_min: int,
) -> dict[str, Any]:
    if (
        current_rose.get("status") != "unavailable"
        or current_rose.get("reason") != "below_min_minutes"
    ):
        return current_rose
    limit = int((model.get("board") or {}).get("prior_seasons") or 3)
    prior = _history_seasons(season, limit)
    for prior_season in prior:
        totals = history_player_totals(int(player["player_id"]), prior_season)
        if int(totals.get("minutes") or 0) < player_min:
            continue
        index = history.get(prior_season)
        if index is None:
            continue
        family = _history_role(int(player["player_id"]), prior_season)
        group = _history_position_group(int(player["player_id"]), prior_season)
        group = group or player.get("position_group")
        rose = build_rose(
            player_rates(totals),
            minutes=int(totals.get("minutes") or 0),
            league=ROSE_LEAGUE,
            league_label=ROSE_LEAGUE_LABEL,
            family=family,
            position_group=group,
            index=index,
            model=model,
            config=config,
            player_min_minutes=player_min,
            cohort_min_minutes=cohort_min,
        )
        if rose.get("status") == "unavailable":
            continue
        rose.update(
            {
                "season_used": prior_season,
                "cohort_season": prior_season,
                "fallback": True,
                "fallback_reason": "current_season_below_min_minutes",
                "fallback_note": (
                    f"Showing {prior_season} statistics — no {season} Premiership "
                    f"minutes above the {player_min}-minute threshold."
                ),
            }
        )
        return rose
    return current_rose


def prior_seasons(
    player_id: int,
    *,
    current: str,
    model: dict[str, Any],
) -> list[dict[str, Any]]:
    params = model.get("board") or {}
    limit = int(params.get("prior_seasons") or 3)
    root = NORMALIZED_DIR / "history"
    out: list[dict[str, Any]] = []
    for season in _history_seasons(current, limit):
        path = root / f"season={season}" / "player_match_stats.parquet"
        if not path.exists():
            continue
        frame = pl.read_parquet(path).filter(pl.col("player_id") == player_id)
        if not frame.height:
            continue
        minutes = int(frame["minutes"].sum() or 0)
        starts = frame.filter(pl.col("substitute") == False).height  # noqa: E712
        rated = frame.filter(pl.col("rating").is_not_null()).with_columns(
            pl.col("rating").cast(pl.Float64)
        )
        role_family = None
        role_code = None
        role_starts = 0
        appearances = root / f"season={season}" / "appearances.parquet"
        if appearances.exists():
            role_rows = pl.read_parquet(appearances).filter(
                (pl.col("player_id") == player_id) & pl.col("role_family").is_not_null()
            )
            if role_rows.height:
                counts = (
                    role_rows.group_by(["role_family", "role_code"])
                    .agg(pl.len().alias("starts"))
                    .sort(["starts", "role_code"], descending=[True, False])
                )
                top = counts.row(0, named=True)
                role_family = top["role_family"]
                role_code = top["role_code"]
                role_starts = int(top["starts"])
        mean_rating = rated["rating"].mean() if rated.height else None
        rating = round(float(mean_rating), 2) if isinstance(mean_rating, (int, float)) else None
        out.append(
            {
                "season": season,
                "minutes": minutes,
                "starts": starts,
                "rating": rating,
                "role_family": role_family,
                "role_code": role_code,
                "role_starts": role_starts,
            }
        )
    return out


def _first_choice(prior: dict[str, Any], model: dict[str, Any]) -> bool:
    params = model.get("board") or {}
    return int(prior.get("starts") or 0) >= int(params.get("first_choice_starts") or 10) or int(
        prior.get("minutes") or 0
    ) >= int(params.get("first_choice_minutes") or 900)


def _prior_for_display(
    history: list[dict[str, Any]], model: dict[str, Any]
) -> dict[str, Any] | None:
    threshold = int((model.get("board") or {}).get("prior_min_minutes") or 450)
    for item in history:
        if int(item.get("minutes") or 0) >= threshold:
            return item
    return history[0] if history else None


def _availability_payload(player: dict[str, Any]) -> dict[str, Any]:
    availability = player.get("availability") or {}
    return {
        "status": availability.get("status") or "unknown",
        "confidence": availability.get("confidence") or "unknown",
        "source_id": availability.get("source_id"),
        "source_url": availability.get("source_url"),
        "verified_at": availability.get("verified_at"),
        "note": availability.get("note"),
        "stale": bool(availability.get("stale")),
    }


def build_board(
    *,
    squad_data: dict[str, Any],
    pool_rows: list[dict[str, Any]],
    index: CohortIndex,
    season: str,
    roles: dict[str, Any],
    model: dict[str, Any],
    availability_entries: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    params = model.get("board") or {}
    board_min = int(params.get("min_minutes") or 300)
    pool_min = int((model.get("pool") or {}).get("min_minutes") or 450)
    below = float(params.get("status_below") or 40.0)
    above = float(params.get("status_above") or 60.0)
    families = sorted(
        (roles.get("families") or {}).items(), key=lambda item: int(item[1].get("order") or 0)
    )
    family_labels = {str(key): str(value.get("label") or key) for key, value in families}
    role_labels = {
        str(code): str(value.get("label") or code)
        for code, value in (roles.get("roles") or {}).items()
    }
    family_players: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unassigned: list[dict[str, Any]] = []
    squad_ids: set[int] = set()
    for player in squad_data.get("players") or []:
        if player.get("status") == "loan_out":
            continue
        player_id = int(player["player_id"])
        squad_ids.add(player_id)
        display = player.get("display_role") or {}
        role = player.get("role") or {}
        totals = _squad_stats(player)
        history = prior_seasons(player_id, current=season, model=model)
        prior = _prior_for_display(history, model)
        family = display.get("family") or role.get("family")
        if not family and prior:
            family = prior.get("role_family")
        row = {
            "player_id": player_id,
            "name": player.get("name"),
            "role_label": display.get("label")
            or role.get("label")
            or (role_labels.get(str((prior or {}).get("role_code") or "")) if prior else None)
            or (family_labels.get(str(family)) if family else "Role not observed"),
            "minutes": int(totals.get("minutes") or 0),
            "appearances": totals.get("appearances"),
            "rating": totals.get("rating"),
            "rates": player_rates(totals),
            "availability": _availability_payload(player),
            "prior": prior,
            "prior_history": history,
            "first_choice": bool(prior and _first_choice(prior, model)),
        }
        if family:
            family_players[str(family)].append(row)
        elif str((row["availability"] or {}).get("status") or "unknown") != "unknown":
            # A verified absentee with no current or prior role still belongs in
            # layer 0; hiding him because the role is unknown defeats the point.
            unassigned.append({**row, "family": None, "family_label": "Role not observed"})

    # A verified absentee can be missing from the provider squad snapshot. The
    # ledger keeps him visible; his role comes from prior starting-XI evidence,
    # never from a generic position or a guess.
    for entry in availability_entries or []:
        player_id = entry.get("player_id")
        if player_id is None or int(player_id) in squad_ids:
            continue
        status = str(entry.get("status") or "unknown")
        if status == "unknown":
            continue
        history = prior_seasons(int(player_id), current=season, model=model)
        prior = _prior_for_display(history, model)
        family = prior.get("role_family") if prior else None
        row = {
            "player_id": int(player_id),
            "name": entry.get("player_name"),
            "role_label": role_labels.get(str((prior or {}).get("role_code") or ""))
            or (family_labels.get(str(family)) if family else "Role not observed"),
            "minutes": 0,
            "appearances": 0,
            "rating": None,
            "rates": {},
            "availability": {
                "status": status,
                "confidence": entry.get("confidence") or "unknown",
                "source_id": entry.get("source_id"),
                "source_url": entry.get("source_url"),
                "verified_at": entry.get("verified_at"),
                "note": entry.get("note"),
                "stale": bool(entry.get("stale")),
            },
            "prior": prior,
            "prior_history": history,
            "first_choice": bool(prior and _first_choice(prior, model)),
        }
        if family:
            family_players[str(family)].append(row)
        else:
            unassigned.append({**row, "family": None, "family_label": "Role not observed"})

    out: list[dict[str, Any]] = []
    for family, definition in families:
        all_players = family_players.get(family, [])
        players = [player for player in all_players if int(player["minutes"]) >= board_min]
        players.sort(key=lambda item: (-int(item["minutes"]), str(item["name"])))
        rated = [
            (float(player["rating"]), int(player.get("appearances") or 1))
            for player in players
            if player.get("rating") is not None
        ]
        average = (
            round(
                sum(rating * appearances for rating, appearances in rated)
                / sum(appearances for _, appearances in rated),
                2,
            )
            if rated
            else None
        )
        cohort = rating_cohort(index, "sco:premiership", family, min_minutes=pool_min)
        cohort_ok = len(cohort) >= _min_cohort(model, family)
        percentile = (
            midrank_percentile(average, cohort) if average is not None and cohort_ok else None
        )
        status = "insufficient"
        if average is not None and cohort_ok:
            if percentile is not None and percentile < below:
                status = "below"
            elif percentile is not None and percentile > above:
                status = "above"
            else:
                status = "at"
        layer0 = [player for player in all_players if player["availability"]["status"] != "unknown"]
        layer0.sort(
            key=lambda item: (
                {"out": 0, "doubtful": 1, "suspended": 2, "returned": 3, "available": 4}.get(
                    str(item["availability"]["status"]), 9
                ),
                str(item["name"]),
            )
        )
        absent_first_choice = [
            player
            for player in layer0
            if player["availability"]["status"] in {"out", "doubtful"} and player["first_choice"]
        ]
        reading = "insufficient"
        if status == "below":
            if len(absent_first_choice) >= 2:
                reading = "hold"
            elif len(absent_first_choice) == 1:
                reading = "cover"
            else:
                reading = "structural"
        elif status in {"at", "above"}:
            reading = "none"
        out.append(
            {
                "family": family,
                "label": definition.get("label") or family,
                "players": players,
                "player_count": len(players),
                "minutes": sum(int(player["minutes"]) for player in players),
                "average_rating": average,
                "rating_percentile": percentile,
                "cohort": {
                    "league_id": "sco:premiership",
                    "role_family": family,
                    "n": len(cohort),
                    "median": round(median(cohort), 2) if cohort else None,
                    "min_minutes": pool_min,
                    "basis": "role_family",
                },
                "status": status,
                "reading": reading,
                "layer0": layer0,
                "absent_first_choice": len(absent_first_choice),
                "drivers": [
                    driver
                    for driver, present in (
                        ("rating_below_cohort", status == "below"),
                        ("first_choice_out", bool(absent_first_choice)),
                        ("small_cohort", len(cohort) < _min_cohort(model, family)),
                        ("small_sample", len(players) < 2),
                    )
                    if present
                ],
            }
        )
    return {
        "league_id": "sco:premiership",
        "families": out,
        "unassigned_layer0": unassigned,
        "summary": {
            "families": len(out),
            "below_cohort": sum(1 for row in out if row["status"] == "below"),
            "cover_readings": sum(1 for row in out if row["reading"] == "cover"),
            "structural_readings": sum(1 for row in out if row["reading"] == "structural"),
            "insufficient": sum(1 for row in out if row["status"] == "insufficient"),
            "layer0_players": sum(len(row["layer0"]) for row in out) + len(unassigned),
        },
    }


def build_squad_profile(
    *,
    squad_data: dict[str, Any],
    index: CohortIndex,
    roles: dict[str, Any],
    archetypes: dict[str, Any],
    model: dict[str, Any],
    roses: dict[int, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    min_minutes = int((model.get("squad") or {}).get("min_minutes") or 180)
    pool_min = int((model.get("pool") or {}).get("min_minutes") or 450)
    order = {
        name: int(item.get("order") or 0) for name, item in (roles.get("families") or {}).items()
    }
    out: list[dict[str, Any]] = []
    for player in squad_data.get("players") or []:
        if player.get("status") == "loan_out":
            continue
        display = player.get("display_role") or {}
        role = player.get("role") or {}
        family = display.get("family") or role.get("family")
        totals = _squad_stats(player)
        league = _squad_stats(player, competition="Premiership")
        minutes = int(league.get("minutes") or 0)
        if minutes < min_minutes:
            continue
        cohort = (
            rating_cohort(index, "sco:premiership", family, min_minutes=pool_min) if family else []
        )
        percentile = (
            midrank_percentile(float(league["rating"]), cohort)
            if league.get("rating") is not None and len(cohort) >= _min_cohort(model, family)
            else None
        )
        rates = player_rates(totals)
        out.append(
            {
                "player_id": player["player_id"],
                "name": player.get("name"),
                "role_family": family,
                "role_label": display.get("label") or role.get("label"),
                "minutes": totals.get("minutes") or minutes,
                "minutes_scope": "all_competitions",
                "league_minutes": minutes,
                "rating": totals.get("rating"),
                "league_rating": league.get("rating"),
                "rating_percentile": percentile,
                "goals": totals.get("goals"),
                "assists": totals.get("assists"),
                "rates": rates,
                "rose": (roses or {}).get(int(player["player_id"])),
                "archetypes": archetype_scores(
                    rates,
                    league="sco:premiership",
                    family=family,
                    minutes=minutes,
                    index=index,
                    archetypes=archetypes,
                    model=model,
                ),
                "cohort": {
                    "n": len(cohort),
                    "basis": "role_family" if family else "unknown",
                },
            }
        )
    out.sort(
        key=lambda item: (
            order.get(str(item["role_family"]), 99),
            -int(item["minutes"]),
            str(item["name"]),
        )
    )
    return out


def build_squad_roses(
    *,
    squad_data: dict[str, Any],
    index: CohortIndex,
    model: dict[str, Any],
    config: dict[str, Any],
    season: str,
) -> dict[int, dict[str, Any]]:
    """Build a rose block for every squad player, with a prior-season fallback.

    The current-season rose is always preferred. A player below the current
    minutes gate may use the most recent prior Premiership season with a
    same-season cohort; the season is stamped on the block and shown in the UI.
    """
    player_min = int((model.get("squad") or {}).get("min_minutes") or 180)
    cohort_min = int((model.get("pool") or {}).get("min_minutes") or 450)
    history = load_rose_history_indices(model)
    out: dict[int, dict[str, Any]] = {}
    for player in [
        *(squad_data.get("players") or []),
        *(squad_data.get("excluded_players") or []),
    ]:
        display = player.get("display_role") or {}
        role = player.get("role") or {}
        family = display.get("family") or role.get("family")
        totals = _squad_stats(player, competition="Premiership")
        minutes = int(totals.get("minutes") or 0)
        current = build_rose(
            player_rates(totals),
            minutes=minutes,
            league="sco:premiership",
            league_label="Scottish Premiership",
            family=family,
            position_group=player.get("position_group"),
            index=index,
            model=model,
            config=config,
            player_min_minutes=player_min,
            cohort_min_minutes=cohort_min,
        )
        current.update(
            {
                "season_used": season,
                "cohort_season": season,
                "fallback": False,
                "fallback_reason": None,
                "fallback_note": None,
            }
        )
        if current.get("status") == "unavailable" and current.get("reason") == "below_min_minutes":
            current = _fallback_rose(
                player,
                season=season,
                current_rose=current,
                history=history,
                model=model,
                config=config,
                player_min=player_min,
                cohort_min=cohort_min,
            )
            if not current.get("fallback") and current.get("status") == "unavailable":
                current["fallback_reason"] = "no_prior_premiership_season"
                current["fallback_note"] = (
                    f"No prior Premiership season met the {player_min}-minute "
                    "profile threshold."
                )
        out[int(player["player_id"])] = current
    return out


def robust_scale(values: Iterable[float]) -> float | None:
    items = [float(value) for value in values]
    if len(items) < 2:
        return None
    centre = median(items)
    mad = median([abs(item - centre) for item in items])
    scale = 1.4826 * mad
    if scale <= 0:
        spread = pstdev(items)
        scale = spread if spread > 0 else 0.0
    return scale if scale > 0 else None


def cohort_stats(values: Iterable[float]) -> dict[str, Any]:
    items = [float(value) for value in values]
    if not items:
        return {"n": 0, "median": None, "scale": None}
    scale = robust_scale(items)
    return {
        "n": len(items),
        "median": round(median(items), 3),
        "scale": round(scale, 3) if scale is not None else None,
    }


def build_alignment(rows: list[dict[str, Any]], model: dict[str, Any]) -> dict[str, Any]:
    """Observed league/role cohorts for the cross-league equivalence map."""
    by_league_family: dict[tuple[str, str], list[float]] = defaultdict(list)
    by_league_all: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        rating = row.get("rating")
        league = str(row.get("competition_id") or "")
        if rating is None or not league:
            continue
        by_league_all[league].append(float(rating))
        family = row.get("role_family")
        if family:
            by_league_family[(league, str(family))].append(float(rating))
    leagues = sorted({league for league in by_league_all})
    families = sorted({family for _, family in by_league_family})
    output: dict[str, Any] = {
        "reference_league": "sco:premiership",
        "min_cohort": int((model.get("pool") or {}).get("min_cohort") or 15),
        "leagues": {},
    }
    for league in leagues:
        output["leagues"][league] = {
            "all": cohort_stats(by_league_all[league]),
            "families": {
                family: cohort_stats(by_league_family.get((league, family), []))
                for family in families
            },
        }
    reference = output["reference_league"]
    output["reference_values"] = {
        "all": [float(value) for value in by_league_all.get(reference, [])],
        "families": {
            family: [float(value) for value in by_league_family.get((reference, family), [])]
            for family in families
        },
    }
    return output


def _reference_stats(alignment: dict[str, Any], family: str | None) -> dict[str, Any]:
    reference = alignment["leagues"].get(alignment["reference_league"]) or {}
    if family:
        stats = (reference.get("families") or {}).get(family) or {}
        if stats.get("n", 0) >= alignment.get("min_cohort", 15):
            return stats
    return reference.get("all") or {}


def _league_stats(
    alignment: dict[str, Any], league: str, family: str | None
) -> tuple[dict[str, Any], str]:
    league_row = alignment["leagues"].get(league) or {}
    if family:
        stats = (league_row.get("families") or {}).get(family) or {}
        if stats.get("n", 0) >= alignment.get("min_cohort", 15):
            return stats, "role_family"
    return league_row.get("all") or {}, "league_all_roles"


def _reference_values(alignment: dict[str, Any], family: str | None) -> list[float]:
    values = alignment.get("reference_values") or {}
    if family:
        family_values = (values.get("families") or {}).get(family) or []
        if len(family_values) >= alignment.get("min_cohort", 15):
            return [float(value) for value in family_values]
    return [float(value) for value in values.get("all") or []]


def adjusted_percentile_for(
    rating: float | None,
    *,
    league: str,
    family: str | None,
    alignment: dict[str, Any],
) -> tuple[float | None, str]:
    """Map a rating into the actual Premiership cohort distribution."""
    if rating is None:
        return None, "unavailable"
    if league == alignment["reference_league"]:
        return None, "identity"
    reference = _reference_stats(alignment, family)
    league_stats, basis = _league_stats(alignment, league, family)
    ref_median = reference.get("median")
    ref_scale = reference.get("scale")
    league_scale = league_stats.get("scale")
    values = _reference_values(alignment, family)
    if ref_median is None or ref_scale is None or league_scale is None or not values:
        return None, "unavailable"
    scale_factor = float(ref_scale) / float(league_scale)
    equivalent = float(ref_median) + (float(rating) - float(ref_median)) * scale_factor
    return midrank_percentile(equivalent, values), basis


def adjusted_profile_for(
    score: float | None,
    *,
    league: str,
    family: str | None,
    alignment: dict[str, Any],
) -> float | None:
    if score is None:
        return None
    if league == alignment["reference_league"]:
        return round(float(score), 1)
    reference = _reference_stats(alignment, family)
    league_stats, _ = _league_stats(alignment, league, family)
    ref_median = reference.get("median")
    ref_scale = reference.get("scale")
    league_median = league_stats.get("median")
    if ref_median is None or ref_scale is None or league_median is None:
        return None
    clipped = min(0.999, max(0.001, float(score) / 100.0))
    z = NormalDist().inv_cdf(clipped)
    z_equiv = z + (float(league_median) - float(ref_median)) / float(ref_scale)
    return round(100.0 * NormalDist().cdf(z_equiv), 1)


def age_curve(age: int | None, config: dict[str, Any]) -> float | None:
    if age is None:
        return None
    bands = (config.get("index") or {}).get("age_curve") or []
    for band in bands:
        if int(age) <= int(band.get("max_age") or 999):
            return float(band.get("factor") or 0.0)
    return 0.3


def scouting_value_index(
    *,
    adjusted_percentile: float | None,
    age: int | None,
    minutes: int,
    archetypes: dict[str, dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    """0-100 performance/league/age/minutes ordering; never a currency value."""
    index_config = config.get("index") or {}
    weights = index_config.get("weights") or {}
    total_weight = sum(float(value) for value in weights.values()) or 1.0
    components: dict[str, float] = {}
    if adjusted_percentile is not None:
        components["performance"] = float(adjusted_percentile) / 100.0
    age_value = age_curve(age, config)
    if age_value is not None:
        components["age"] = age_value
    minutes_full = float(index_config.get("minutes_full") or 1800)
    if minutes > 0:
        components["minutes"] = min(1.0, float(minutes) / minutes_full)
    profile_scores = [
        float(value["adjusted_score"])
        for value in archetypes.values()
        if value.get("adjusted_score") is not None
    ]
    if profile_scores:
        components["profile"] = max(profile_scores) / 100.0
    available_weight = sum(float(weights.get(key) or 0.0) for key in components)
    coverage = available_weight / total_weight
    if not components or coverage < float(index_config.get("min_weight_coverage") or 0.7):
        return {
            "value_index": None,
            "value_index_coverage": round(coverage, 3),
            "value_index_drivers": sorted(components),
            "value_index_basis": "measured inputs, modelled weights",
        }
    value = sum(float(weights[key]) * value for key, value in components.items()) / (
        available_weight or 1.0
    )
    return {
        "value_index": round(100.0 * value, 1),
        "value_index_coverage": round(coverage, 3),
        "value_index_drivers": sorted(components),
        "value_index_basis": "measured inputs, modelled weights",
    }


def scouting_priority_for(
    *,
    value_index: float | None,
    age: int | None,
    europe_status: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Aberdeen scouting preferences: U23 boost and European shop-window discount."""
    params = config.get("priority") or {}
    age_multiplier = 1.0
    if age is not None and int(age) <= int(params.get("u23_max_age") or 23):
        age_multiplier = float(params.get("u23_multiplier") or 1.0)
    europe_multiplier = (
        float(params.get("europe_multiplier") or 1.0) if europe_status == "qualified" else 1.0
    )
    priority = (
        round(float(value_index) * age_multiplier * europe_multiplier, 1)
        if value_index is not None
        else None
    )
    return {
        "age_multiplier": age_multiplier,
        "europe_multiplier": europe_multiplier,
        "scouting_priority": priority,
    }


def build_pool_rows(
    pool: pl.DataFrame,
    role_rows: pl.DataFrame,
    *,
    config: dict[str, Any],
    archetypes: dict[str, Any],
    model: dict[str, Any],
    value_config: dict[str, Any] | None = None,
    rose_config: dict[str, Any] | None = None,
    europe_rows: pl.DataFrame | None = None,
    europe_meta: dict[str, Any] | None = None,
    current_clubs: pl.DataFrame | None = None,
    team_standings: pl.DataFrame | None = None,
    team_context_config: dict[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Prepare compact per-league search rows, rates, percentiles and profiles."""
    if pool.height == 0:
        return {}
    role_map: dict[tuple[int, str], dict[str, Any]] = {}
    if role_rows.height:
        for row in role_rows.to_dicts():
            role_map[(int(row["player_id"]), str(row["league_id"]))] = row
    min_minutes = int((model.get("pool") or {}).get("min_minutes") or 450)
    low_minutes = int((model.get("pool") or {}).get("low_minutes") or 900)
    team_settings = team_context_config or {}
    team_threshold = float(team_settings.get("underperforming_ppg_percentile_max") or 40)
    team_map: dict[tuple[int, int], dict[str, Any]] = {}
    if team_standings is not None and team_standings.height:
        # A conference-based league (MLS) is compared within its conference, so
        # rank, cohort size and PPG percentile describe the same set. Leagues
        # without groups keep one league-wide cohort.
        teams_by_group: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
        for standing in team_standings.to_dicts():
            if standing.get("ppg") is not None:
                key = (
                    int(standing.get("provider_league_id") or 0),
                    str(standing.get("group") or ""),
                )
                teams_by_group[key].append(standing)
        for (provider_league_id, group), team_cohort in teams_by_group.items():
            values = [float(item["ppg"]) for item in team_cohort]
            for standing in team_cohort:
                percentile = midrank_percentile(float(standing["ppg"]), values)
                team_map[(provider_league_id, int(standing["team_id"]))] = {
                    "team_rank": standing.get("rank"),
                    "team_points": standing.get("points"),
                    "team_played": standing.get("played"),
                    "team_ppg": standing.get("ppg"),
                    "team_count": len(team_cohort),
                    "team_group": group or None,
                    "team_points_percentile": percentile,
                    "team_underperforming": (
                        percentile is not None and percentile <= team_threshold
                    ),
                    "team_context_status": "available" if percentile is not None else "unknown",
                }
    rows: list[dict[str, Any]] = []
    for raw in pool.to_dicts():
        minutes = int(raw.get("minutes") or 0)
        if minutes < min_minutes:
            continue
        role = role_map.get((int(raw["player_id"]), str(raw["competition_id"]))) or {}
        family = role.get("role_family")
        row = dict(raw)
        row["role_family"] = family
        row["role_family_share"] = role.get("role_family_share")
        row["role_status"] = role.get("role_status") or "unknown"
        row["rates"] = player_rates(raw)
        rows.append(row)
    index = CohortIndex(rows, model)
    alignment = build_alignment(rows, model)
    value_settings = value_config or load_scouting_value()
    rose_settings = rose_config or load_player_rose()
    priority_settings = value_settings.get("priority") or {}
    europe_minutes_threshold = int(priority_settings.get("europe_minutes_threshold") or 90)
    europe_complete = bool((europe_meta or {}).get("coverage_complete"))
    club_map: dict[int, dict[str, Any]] = {}
    if current_clubs is not None and current_clubs.height:
        for item in current_clubs.to_dicts():
            player_id = item.get("player_id")
            if player_id is not None:
                club_map[int(player_id)] = item
    europe_map: dict[int, dict[str, Any]] = {}
    if europe_rows is not None and europe_rows.height:
        grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for item in europe_rows.to_dicts():
            grouped[int(item["player_id"])].append(item)
        for player_id, items in grouped.items():
            minutes = sum(int(item.get("minutes") or 0) for item in items)
            appearances = sum(int(item.get("appearances") or 0) for item in items)
            competitions = sorted({str(item.get("competition")) for item in items})
            rated = [item for item in items if item.get("rating") is not None]
            rating = (
                round(
                    sum(float(item["rating"]) * int(item.get("minutes") or 1) for item in rated)
                    / max(1, sum(int(item.get("minutes") or 1) for item in rated)),
                    2,
                )
                if rated
                else None
            )
            europe_map[player_id] = {
                "minutes": minutes,
                "appearances": appearances,
                "competitions": competitions,
                "rating": rating,
            }
    by_league: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        league = str(row["competition_id"])
        family = row.get("role_family")
        minutes = int(row.get("minutes") or 0)
        basis = "role_family"
        cohort: list[float] = []
        if family:
            cohort = rating_cohort(index, league, family, min_minutes=min_minutes)
            if len(cohort) < _min_cohort(model, family):
                cohort = []
        if not cohort:
            group = str(row.get("position_group") or "UNKNOWN")
            # A provider-group fallback needs a different cohort key. Build it
            # from rows in the same league and group, never across leagues.
            group_rows = [
                other
                for other in rows
                if other["competition_id"] == league
                and other.get("position_group") == group
                and int(other.get("minutes") or 0) >= min_minutes
                and other.get("rating") is not None
            ]
            cohort = [float(other["rating"]) for other in group_rows]
            basis = "provider_group"
        percentile = (
            midrank_percentile(float(row["rating"]), cohort)
            if row.get("rating") is not None and len(cohort) >= 5
            else None
        )
        row["rating_percentile"] = percentile
        row["cohort_basis"] = basis if percentile is not None else "insufficient"
        row["cohort_n"] = len(cohort)
        adjusted, adjustment_basis = adjusted_percentile_for(
            row.get("rating"),
            league=league,
            family=family,
            alignment=alignment,
        )
        if adjustment_basis == "identity":
            adjusted = percentile
        row["adjusted_percentile"] = adjusted
        row["adjustment_basis"] = adjustment_basis
        team = team_map.get((int(row.get("provider_league_id") or 0), int(row.get("team_id") or 0)))
        if team is None:
            row["team_context_status"] = "unknown"
            row["team_lift"] = None
        else:
            row.update(team)
            row["team_lift"] = (
                round(float(adjusted) - float(team["team_points_percentile"]), 1)
                if adjusted is not None and team.get("team_points_percentile") is not None
                else None
            )
        row["rose"] = build_rose(
            row["rates"],
            minutes=minutes,
            league=league,
            league_label=str(row.get("competition") or league),
            family=family,
            position_group=row.get("position_group"),
            index=index,
            model=model,
            config=rose_settings,
            player_min_minutes=min_minutes,
            cohort_min_minutes=min_minutes,
        )
        row["archetypes"] = archetype_scores(
            row["rates"],
            league=league,
            family=family,
            minutes=minutes,
            index=index,
            archetypes=archetypes,
            model=model,
        )
        for archetype in row["archetypes"].values():
            archetype["adjusted_score"] = adjusted_profile_for(
                archetype.get("score"),
                league=league,
                family=family,
                alignment=alignment,
            )
        row.update(
            scouting_value_index(
                adjusted_percentile=adjusted,
                age=row.get("age"),
                minutes=minutes,
                archetypes=row["archetypes"],
                config=value_settings,
            )
        )
        europe = europe_map.get(int(row["player_id"]))
        if europe is not None:
            raw_minutes = europe["minutes"]
            europe_minutes = int(raw_minutes) if raw_minutes is not None else 0
            europe_status = (
                "qualified" if europe_minutes >= europe_minutes_threshold else "below_threshold"
            )
            europe_competitions = europe["competitions"]
            europe_appearances: int | None = europe["appearances"]
        elif europe_complete:
            europe_minutes = 0
            europe_status = "none"
            europe_competitions = []
            europe_appearances = 0
        else:
            europe_minutes = None
            europe_status = "unknown"
            europe_competitions = []
            europe_appearances = None
        current = club_map.get(int(row["player_id"]))
        stats_club = str(row.get("team_name") or "Unknown club")
        if current and current.get("current_team_name"):
            row["current_club"] = str(current["current_team_name"])
            row["current_club_id"] = current.get("current_team_id")
            row["current_league_id"] = current.get("current_league_id")
            row["current_league_name"] = current.get("current_league_name")
            row["current_club_status"] = current.get("status") or "transferred"
            row["current_club_source"] = "transfer_feed"
            row["transferred_at"] = current.get("transfer_date")
        else:
            row["current_club"] = stats_club
            row["current_club_id"] = row.get("team_id")
            row["current_league_id"] = row.get("competition_id")
            row["current_league_name"] = row.get("competition")
            row["current_club_status"] = "stats"
            row["current_club_source"] = "stats_snapshot"
            row["transferred_at"] = None
        row["stats_club"] = stats_club
        row["european_league_phase_minutes"] = europe_minutes
        row["european_league_phase_appearances"] = europe_appearances
        row["european_league_phase_competitions"] = europe_competitions
        row["european_status"] = europe_status
        row.update(
            scouting_priority_for(
                value_index=row.get("value_index"),
                age=row.get("age"),
                europe_status=europe_status,
                config=value_settings,
            )
        )
        row["flags"] = [
            flag
            for flag, present in (
                ("low_minutes", minutes < low_minutes),
                ("role_unknown", not family),
                ("no_rating", row.get("rating") is None),
                ("european_shop_window", europe_status == "qualified"),
            )
            if present
        ]
        by_league[league].append(row)
    for items in by_league.values():
        items.sort(
            key=lambda item: (
                -(item["rating_percentile"] if item["rating_percentile"] is not None else -1),
                -int(item["minutes"]),
                str(item["name"]),
            )
        )
    return dict(by_league)


def top_profiles(
    rows: list[dict[str, Any]],
    archetype_id: str,
    *,
    limit: int = 5,
    min_coverage: float = 0.7,
    score_key: str = "score",
    rank_key: str | None = None,
) -> list[dict[str, Any]]:
    candidates = [
        row
        for row in rows
        if (row.get("archetypes") or {}).get(archetype_id, {}).get(score_key) is not None
        and (row["archetypes"][archetype_id].get("coverage") or 0) >= min_coverage
    ]
    ranking = rank_key or score_key
    candidates.sort(
        key=lambda row: (
            -(float(row[ranking]) if row.get(ranking) is not None else -1.0),
            -float(row["archetypes"][archetype_id][score_key]),
            -int(row["minutes"]),
        )
    )
    return candidates[:limit]


__all__ = [
    "RATE_FIELDS",
    "CohortIndex",
    "archetype_scores",
    "build_board",
    "build_pool_rows",
    "build_rose",
    "build_squad_profile",
    "build_squad_roses",
    "midrank_percentile",
    "per90",
    "player_rates",
    "prior_seasons",
    "quantile",
    "ratio",
    "robust_z",
    "top_profiles",
]
