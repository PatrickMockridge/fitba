"""Shape and balance view for a team's covered fixtures.

The licensed lineup feed gives the kick-off formation, not the shape after a
substitution. This module aggregates the kick-off shapes and joins provider
per-match ratings for centre-backs and saves for the goalkeeper. Reported
mid-game switches come only from the curated shape notes and are kept separate
from the kick-off counts.
"""

from __future__ import annotations

from statistics import mean
from typing import Any

from fitba.ingest.match_data import (
    load_match_meta,
    load_player_appearances,
    load_player_match_stats,
    load_team_shapes,
)
from fitba.normalize.teams import TeamRegistry
from fitba.settings import shape_notes


def _mean(values: list[float]) -> float | None:
    return round(mean(values), 2) if values else None


def shape_payload(*, team_id: int, season_year: int) -> dict[str, Any]:
    registry = TeamRegistry()
    shapes_frame = load_team_shapes()
    apps_frame = load_player_appearances()
    stats_frame = load_player_match_stats()
    meta = load_match_meta()

    if not shapes_frame.height:
        return {
            "coverage": {"status": "unavailable", "note": "Team-shape data has not been ingested."},
            "formations": [],
            "matchday": [],
            "reported_switches": [],
        }

    shapes = [
        row
        for row in shapes_frame.to_dicts()
        if int(row.get("team_id") or 0) == team_id and int(row.get("season") or 0) == season_year
    ]
    fixture_ids = {int(row["fixture_id"]) for row in shapes}

    cb_apps = []
    if apps_frame.height:
        cb_apps = [
            row
            for row in apps_frame.to_dicts()
            if int(row.get("team_id") or 0) == team_id
            and int(row.get("season") or 0) == season_year
            and row.get("role_family") == "centre_back"
            and row.get("started")
        ]
    ratings: dict[tuple[int, int], float] = {}
    if stats_frame.height:
        by_player_fixture = {
            (int(row["fixture_id"]), int(row["player_id"])): row.get("rating")
            for row in stats_frame.to_dicts()
            if int(row.get("team_id") or 0) == team_id
            and int(row.get("season") or 0) == season_year
            and row.get("rating") is not None
        }
        for row in cb_apps:
            key = (int(row["fixture_id"]), int(row["player_id"]))
            rating = by_player_fixture.get(key)
            if rating is not None:
                ratings[key] = float(rating)

    fixture_ratings: dict[int, list[float]] = {}
    for (fixture_id, _player_id), rating in ratings.items():
        fixture_ratings.setdefault(fixture_id, []).append(rating)

    formations: dict[str, dict[str, Any]] = {}
    matchday: list[dict[str, Any]] = []
    for row in sorted(shapes, key=lambda item: str(item.get("date") or "")):
        key = str(row.get("formation_shape") or "unknown")
        bucket = formations.setdefault(
            key,
            {
                "formation": key,
                "shape_family": row.get("shape_family"),
                "cb_count": row.get("cb_count"),
                "dm_count": row.get("dm_count"),
                "matches": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
                "saves": [],
                "cb_ratings": [],
            },
        )
        bucket["matches"] += 1
        result = row.get("result")
        bucket["wins"] += 1 if result == "W" else 0
        bucket["draws"] += 1 if result == "D" else 0
        bucket["losses"] += 1 if result == "L" else 0
        bucket["goals_for"] += int(row.get("goals_for") or 0)
        bucket["goals_against"] += int(row.get("goals_against") or 0)
        if row.get("saves") is not None:
            bucket["saves"].append(int(row["saves"]))
        if fixture_ratings.get(int(row["fixture_id"])):
            bucket["cb_ratings"].append(mean(fixture_ratings[int(row["fixture_id"])]))
        matchday.append(
            {
                "fixture_id": row["fixture_id"],
                "date": row["date"],
                "competition": row["competition"],
                "opponent": registry.display_name(str(row.get("opponent") or "")),
                "formation": row.get("formation"),
                "formation_shape": row.get("formation_shape"),
                "shape_family": row.get("shape_family"),
                "cb_count": row.get("cb_count"),
                "dm_count": row.get("dm_count"),
                "goals_for": row.get("goals_for"),
                "goals_against": row.get("goals_against"),
                "result": row.get("result"),
                "saves": row.get("saves"),
                "cb_rating": _mean(fixture_ratings.get(int(row["fixture_id"]), [])),
            }
        )

    formation_rows = []
    for bucket in formations.values():
        saves = bucket.pop("saves")
        cb_ratings = bucket.pop("cb_ratings")
        bucket["saves_total"] = sum(saves) if saves else None
        bucket["saves_per_match"] = round(sum(saves) / len(saves), 2) if saves else None
        bucket["cb_rating"] = _mean(cb_ratings)
        bucket["goals_against_per_match"] = round(bucket["goals_against"] / bucket["matches"], 2)
        formation_rows.append(bucket)
    formation_rows.sort(key=lambda item: (-item["matches"], str(item["formation"])))

    notes = shape_notes().get("matches", []) if shape_notes() else []
    reported = [
        {
            "fixture_id": row.get("fixture_id"),
            "minute": row.get("minute"),
            "from_shape": row.get("from_shape"),
            "to_shape": row.get("to_shape"),
            "source_url": row.get("source_url"),
            "confidence": row.get("confidence"),
            "note": row.get("note"),
        }
        for row in notes
        if int(row.get("team_id") or 0) == team_id
        and int(row.get("fixture_id") or 0) in fixture_ids
    ]

    with_shape = sum(1 for row in shapes if row.get("formation_shape"))
    with_saves = sum(1 for row in shapes if row.get("saves") is not None)
    with_ratings = sum(1 for row in shapes if fixture_ratings.get(int(row["fixture_id"])))
    return {
        "coverage": {
            "status": (
                "available"
                if with_shape == len(shapes)
                else "partial"
                if with_shape
                else "unavailable"
            ),
            "fixtures_total": len(shapes),
            "fixtures_with_shape": with_shape,
            "fixtures_with_saves": with_saves,
            "fixtures_with_cb_ratings": with_ratings,
            "grid_covered": int(meta.get("fixtures_with_grid") or 0),
            "note": (
                "Kick-off shape only. The feed does not report a formation "
                "change after a substitution; reported switches are shown "
                "separately and are never inferred. Provider ratings are "
                "labelled, not re-modelled. Goals conceded and saves are "
                "per match, not adjusted for opponent strength."
            ),
        },
        "formations": formation_rows,
        "matchday": matchday,
        "reported_switches": sorted(reported, key=lambda item: int(item.get("minute") or 0)),
    }


__all__ = ["shape_payload"]
