"""Match-stat style proxies for the historical record.

These are opponent-unadjusted, team-level proxies from the football-data.co.uk
league rows. They are not a tactical model, not xG and not tracking data.
Possession/pass accuracy are included only when a provider team-statistics
backfill supplies them; a missing stat is unknown, never zero.
"""

from __future__ import annotations

from statistics import mean
from typing import Any

import polars as pl

STAT_KEYS = ("shots", "shots_on_target", "corners", "fouls", "yellow", "red")


def _mean(values: list[float]) -> float | None:
    return round(mean(values), 2) if values else None


def _rate(total: float | None, matches: int) -> float | None:
    return round(total / matches, 2) if total is not None and matches else None


def style_profile(
    match_rows: pl.DataFrame,
    *,
    season: str,
    competition_id: str | None = None,
) -> dict[str, Any]:
    """Aggregate the measured match-stat proxies for one season."""
    if not match_rows.height:
        return {
            "matches": 0,
            "coverage": "unavailable",
            "note": "No league match rows for this season.",
        }
    rows = [
        row
        for row in match_rows.to_dicts()
        if row.get("season") == season
        and (competition_id is None or row.get("competition_id") == competition_id)
    ]
    if not rows:
        return {
            "matches": 0,
            "coverage": "unavailable",
            "note": "No league match rows for this season and competition.",
        }
    matches = len(rows)
    output: dict[str, Any] = {"matches": matches}
    missing: list[str] = []
    for key in STAT_KEYS:
        for_values = [row[f"{key}_for"] for row in rows if row.get(f"{key}_for") is not None]
        against_values = [
            row[f"{key}_against"] for row in rows if row.get(f"{key}_against") is not None
        ]
        if not for_values:
            missing.append(key)
        output[f"{key}_for_pm"] = _rate(sum(for_values) if for_values else None, matches)
        output[f"{key}_against_pm"] = _rate(
            sum(against_values) if against_values else None, matches
        )
    shots = sum(row["shots_for"] for row in rows if row.get("shots_for") is not None)
    on_target = sum(
        row["shots_on_target_for"] for row in rows if row.get("shots_on_target_for") is not None
    )
    goals = sum(int(row["gf"]) for row in rows)
    output["shot_accuracy"] = round(on_target / shots, 3) if shots else None
    output["goals_per_shot"] = round(goals / shots, 3) if shots else None
    output["goals_per_shot_on_target"] = round(goals / on_target, 3) if on_target else None
    output["goals_for_pm"] = _rate(goals, matches)
    output["goals_against_pm"] = _rate(sum(int(row["ga"]) for row in rows), matches)
    output["possession_for_pm"] = None
    output["possession_against_pm"] = None
    output["possession_unknown_reason"] = "provider_statistics_not_backfilled"
    output["coverage"] = (
        "unavailable" if len(missing) == len(STAT_KEYS) else "partial" if missing else "available"
    )
    output["missing_stats"] = missing
    output["note"] = (
        "Opponent-unadjusted team proxies from league match rows. "
        "Not xG and not a tactical model. Possession is provider-reported only."
    )
    return output


def era_style_average(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    """Match-weighted average of the season style profiles."""
    usable = [profile for profile in profiles if int(profile.get("matches") or 0) > 0]
    if not usable:
        return {"seasons": 0, "coverage": "unavailable"}
    total_matches = sum(int(profile["matches"]) for profile in usable)
    keys = [
        "shots_for_pm",
        "shots_against_pm",
        "shots_on_target_for_pm",
        "shots_on_target_against_pm",
        "corners_for_pm",
        "corners_against_pm",
        "fouls_for_pm",
        "fouls_against_pm",
        "yellow_for_pm",
        "red_for_pm",
        "shot_accuracy",
        "goals_for_pm",
        "goals_against_pm",
    ]
    output: dict[str, Any] = {"seasons": len(usable), "matches": total_matches}
    for key in keys:
        weighted = [
            (float(profile[key]), int(profile["matches"]))
            for profile in usable
            if profile.get(key) is not None
        ]
        if not weighted:
            output[key] = None
            continue
        numerator = sum(value * matches for value, matches in weighted)
        denominator = sum(matches for _, matches in weighted)
        output[key] = round(numerator / denominator, 2)
    output["coverage"] = (
        "available"
        if all(profile.get("coverage") == "available" for profile in usable)
        else "partial"
    )
    return output


__all__ = ["STAT_KEYS", "era_style_average", "style_profile"]
