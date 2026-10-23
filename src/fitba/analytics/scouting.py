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

from fitba.normalize.scope import is_friendly_competition
from fitba.settings import NORMALIZED_DIR
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
]

COUNT_FIELDS = [
    "appearances",
    "starts",
    "minutes",
    "goals",
    "assists",
    "shots_total",
    "passes_total",
    "passes_key",
    "tackles",
    "interceptions",
    "duels_total",
    "duels_won",
    "dribbles_attempts",
    "dribbles_success",
    "saves",
    "conceded",
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


def midrank_percentile(value: float, values: Iterable[float]) -> float | None:
    items = [float(item) for item in values]
    if not items:
        return None
    below = sum(1 for item in items if item < value)
    equal = sum(1 for item in items if item == value)
    return round((below + 0.5 * equal) / len(items) * 100.0, 1)


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

    def __init__(self, rows: list[dict[str, Any]], model: dict[str, Any]):
        self.model = model
        self.rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            family = row.get("role_family")
            league = row.get("competition_id")
            if family and league:
                self.rows[(str(league), str(family))].append(row)

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
        return [
            float(row["rates"][feature])
            for row in self.players(league, family, min_minutes=min_minutes, feature=feature)
            if row.get("rates", {}).get(feature) is not None
        ]


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


def _squad_stats(player: dict[str, Any]) -> dict[str, Any]:
    rows = [
        row
        for row in player.get("stats") or []
        if row.get("scope") == "club" and not is_friendly_competition(row.get("competition"))
    ]
    totals: dict[str, Any] = {}
    for field in COUNT_FIELDS:
        values = [row.get(field) for row in rows if row.get(field) is not None]
        totals[field] = sum(int(value) for value in values) if values else None
    rated = [
        (float(row["rating"]), int(row.get("appearances") or 0))
        for row in rows
        if row.get("rating") is not None and int(row.get("appearances") or 0) > 0
    ]
    if rated:
        weight = sum(appearances for _, appearances in rated)
        totals["rating"] = round(
            sum(rating * appearances for rating, appearances in rated) / weight, 2
        )
    else:
        totals["rating"] = None
    weighted_passes = 0
    weighted_accuracy = 0.0
    for row in rows:
        total = row.get("passes_total")
        accuracy = row.get("pass_accuracy")
        if total is None or accuracy is None:
            continue
        weighted_passes += int(total)
        weighted_accuracy += float(total) * float(accuracy)
    totals["pass_accuracy"] = (
        round(weighted_accuracy / weighted_passes, 2) if weighted_passes else None
    )
    return totals


def _history_seasons(current: str, limit: int) -> list[str]:
    root = NORMALIZED_DIR / "history"
    if not root.exists():
        return []
    seasons = sorted(
        (path.name.split("=", 1)[1] for path in root.glob("season=*") if "=" in path.name),
        reverse=True,
    )
    return [season for season in seasons if season < current][:limit]


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
    squad_ids: set[int] = set()
    for player in squad_data.get("players") or []:
        if player.get("status") == "loan_out":
            continue
        player_id = int(player["player_id"])
        squad_ids.add(player_id)
        display = player.get("display_role") or {}
        role = player.get("role") or {}
        family = display.get("family") or role.get("family")
        if not family:
            continue
        totals = _squad_stats(player)
        history = prior_seasons(player_id, current=season, model=model)
        prior = _prior_for_display(history, model)
        family_players[family].append(
            {
                "player_id": player_id,
                "name": player.get("name"),
                "role_label": display.get("label") or role.get("label"),
                "minutes": int(totals.get("minutes") or 0),
                "appearances": totals.get("appearances"),
                "rating": totals.get("rating"),
                "rates": player_rates(totals),
                "availability": _availability_payload(player),
                "prior": prior,
                "prior_history": history,
                "first_choice": bool(prior and _first_choice(prior, model)),
            }
        )

    # A verified absentee can be missing from the provider squad snapshot. The
    # ledger keeps him visible; his role comes from prior starting-XI evidence,
    # never from a generic position or a guess.
    unassigned: list[dict[str, Any]] = []
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
        minutes = int(totals.get("minutes") or 0)
        if minutes < min_minutes:
            continue
        cohort = (
            rating_cohort(index, "sco:premiership", family, min_minutes=pool_min) if family else []
        )
        percentile = (
            midrank_percentile(float(totals["rating"]), cohort)
            if totals.get("rating") is not None and len(cohort) >= _min_cohort(model, family)
            else None
        )
        rates = player_rates(totals)
        out.append(
            {
                "player_id": player["player_id"],
                "name": player.get("name"),
                "role_family": family,
                "role_label": display.get("label") or role.get("label"),
                "minutes": minutes,
                "rating": totals.get("rating"),
                "rating_percentile": percentile,
                "goals": totals.get("goals"),
                "assists": totals.get("assists"),
                "rates": rates,
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


def build_pool_rows(
    pool: pl.DataFrame,
    role_rows: pl.DataFrame,
    *,
    config: dict[str, Any],
    archetypes: dict[str, Any],
    model: dict[str, Any],
    value_config: dict[str, Any] | None = None,
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
        row["flags"] = [
            flag
            for flag, present in (
                ("low_minutes", minutes < low_minutes),
                ("role_unknown", not family),
                ("no_rating", row.get("rating") is None),
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
) -> list[dict[str, Any]]:
    candidates = [
        row
        for row in rows
        if (row.get("archetypes") or {}).get(archetype_id, {}).get(score_key) is not None
        and (row["archetypes"][archetype_id].get("coverage") or 0) >= min_coverage
    ]
    candidates.sort(
        key=lambda row: (
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
    "build_squad_profile",
    "midrank_percentile",
    "per90",
    "player_rates",
    "prior_seasons",
    "quantile",
    "ratio",
    "robust_z",
    "top_profiles",
]
