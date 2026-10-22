#!/usr/bin/env python3
"""CI guard for kick-off shapes, per-match stats and reported switches.

The shape view must distinguish the measured kick-off formation from a sourced
mid-game note. This guard checks the normalized tables and the published club
payload, and rejects a reported switch without a source.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import polars as pl
import yaml

from fitba.settings import aberdeen as aberdeen_config
from fitba.settings import source_ids as source_ids_config

ROOT = Path(__file__).resolve().parents[1]
ROLES = ROOT / "config" / "roles.yaml"
MATCHES = ROOT / "data" / "normalized" / "matches"
SHAPE_NOTES = ROOT / "reference" / "shape_notes.yaml"
CLUB = ROOT / "web" / "data" / "generated" / "clubs" / "aberdeen.json"


def _load(name: str) -> list[dict[str, Any]]:
    path = MATCHES / name
    if not path.exists():
        return []
    return pl.read_parquet(path).to_dicts()


def _valid_shapes(config: dict[str, Any]) -> set[str]:
    return set((config.get("formations") or {}).keys()) | {"unknown"}


def main() -> int:
    errors: list[str] = []
    config = yaml.safe_load(ROLES.read_text(encoding="utf-8"))
    shapes = _load("team_shapes.parquet")
    appearances = _load("player_appearances.parquet")
    match_stats = _load("player_match_stats.parquet")
    notes_payload = (
        yaml.safe_load(SHAPE_NOTES.read_text(encoding="utf-8")) if SHAPE_NOTES.exists() else {}
    )
    notes = notes_payload.get("matches", []) if notes_payload else []
    valid_shapes = _valid_shapes(config)
    club_id = str(aberdeen_config()["club_id"])
    team_id = int(source_ids_config()["teams"][club_id]["api_football"])

    if not shapes:
        errors.append("no team-shape rows were found")
    if not appearances:
        errors.append("no appearance rows were found")

    shape_by_fixture_team = {(int(row["fixture_id"]), int(row["team_id"])): row for row in shapes}
    starters_by_fixture_team: Counter[tuple[int, int]] = Counter()
    cb_by_fixture_team: Counter[tuple[int, int]] = Counter()
    dm_by_fixture_team: Counter[tuple[int, int]] = Counter()
    for row in appearances:
        key = (int(row["fixture_id"]), int(row["team_id"]))
        if row.get("started"):
            starters_by_fixture_team[key] += 1
            if row.get("role_family") == "centre_back":
                cb_by_fixture_team[key] += 1
            if row.get("role_family") == "defensive_midfield":
                dm_by_fixture_team[key] += 1

    for key, row in shape_by_fixture_team.items():
        if starters_by_fixture_team.get(key, 0) and starters_by_fixture_team[key] != 11:
            errors.append(f"{key}: shape row has {starters_by_fixture_team[key]} starters")
        if row.get("cb_count") is not None and int(row["cb_count"]) != cb_by_fixture_team.get(
            key, 0
        ):
            errors.append(f"{key}: cb_count does not match role rows")
        if row.get("dm_count") is not None and int(row["dm_count"]) != dm_by_fixture_team.get(
            key, 0
        ):
            errors.append(f"{key}: dm_count does not match role rows")
        if row.get("formation_shape") and row["formation_shape"] not in valid_shapes:
            errors.append(f"{key}: unknown formation shape {row['formation_shape']}")
        if int(row.get("goals_for") or 0) < 0 or int(row.get("goals_against") or 0) < 0:
            errors.append(f"{key}: negative goals")
        if row.get("result") not in {"W", "D", "L", None}:
            errors.append(f"{key}: invalid result {row.get('result')!r}")

    seen_stats: set[tuple[int, int, int]] = set()
    for row in match_stats:
        key = (int(row["fixture_id"]), int(row["team_id"]), int(row["player_id"]))
        if key in seen_stats:
            errors.append(f"{key}: duplicate per-match stat row")
        seen_stats.add(key)
        rating = row.get("rating")
        if rating is not None and not (0 < float(rating) <= 10):
            errors.append(f"{key}: rating outside 0-10")
        minutes = row.get("minutes")
        if minutes is not None and not (0 <= int(minutes) <= 120):
            errors.append(f"{key}: minutes outside 0-120")

    for index, row in enumerate(notes):
        prefix = f"shape note {index}"
        if not row.get("fixture_id"):
            errors.append(f"{prefix}: missing fixture_id")
        if not row.get("team_id"):
            errors.append(f"{prefix}: missing team_id")
        if not row.get("minute") or int(row["minute"]) < 1:
            errors.append(f"{prefix}: missing minute")
        if row.get("from_shape") not in valid_shapes:
            errors.append(f"{prefix}: invalid from_shape")
        if row.get("to_shape") not in valid_shapes:
            errors.append(f"{prefix}: invalid to_shape")
        if not str(row.get("source_url") or "").startswith(("http://", "https://")):
            errors.append(f"{prefix}: missing source URL")
        if row.get("confidence") not in {"reported", "confirmed"}:
            errors.append(f"{prefix}: invalid confidence")

    if CLUB.exists():
        club = json.loads(CLUB.read_text(encoding="utf-8"))
        shapes_payload = club.get("shapes") or {}
        formations = shapes_payload.get("formations") or []
        matchday = shapes_payload.get("matchday") or []
        coverage = shapes_payload.get("coverage") or {}
        if sum(int(row.get("matches") or 0) for row in formations) != len(matchday):
            errors.append("published shape matches do not equal matchday rows")
        if coverage.get("fixtures_total") not in (None, len(matchday)):
            errors.append("published shape coverage total does not match matchday rows")
        if len(shapes_payload.get("reported_switches") or []) != len(
            [row for row in notes if int(row.get("team_id") or 0) == team_id]
        ):
            errors.append("published reported switches do not match shape notes")
        for row in formations:
            if row.get("formation") not in valid_shapes:
                errors.append(f"published shape {row.get('formation')!r} is not mapped")

    if errors:
        print("Shape publication check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        "Shape publication check passed "
        f"({len(shapes)} team-shape rows, {len(match_stats)} per-match stat rows, "
        f"{len(notes)} reported switches)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
