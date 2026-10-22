#!/usr/bin/env python3
"""CI guard for starting-XI roles, role history and playing time.

The checks run against the normalized match tables, not the front end. A role
can exist only for a starter with a mapped grid slot; a substitute never gets a
role; every observed formation shape must be in config/roles.yaml.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import polars as pl
import yaml

from fitba.normalize.roles import validate_config
from fitba.settings import aberdeen as aberdeen_config
from fitba.settings import source_ids as source_ids_config

ROOT = Path(__file__).resolve().parents[1]
ROLES = ROOT / "config" / "roles.yaml"
MATCHES = ROOT / "data" / "normalized" / "matches"


def _load(name: str) -> list[dict[str, Any]]:
    path = MATCHES / name
    if not path.exists():
        return []
    return pl.read_parquet(path).to_dicts()


def main() -> int:
    errors: list[str] = []
    config = yaml.safe_load(ROLES.read_text(encoding="utf-8"))
    try:
        validate_config(config)
    except ValueError as exc:
        errors.append(f"role config: {exc}")
        config = {"roles": {}, "formations": {}}
    roles = config.get("roles") or {}
    formations = config.get("formations") or {}

    club_id = str(aberdeen_config()["club_id"])
    team_id = int(source_ids_config()["teams"][club_id]["api_football"])

    appearances = _load("player_appearances.parquet")
    role_rows = _load("player_roles.parquet")
    playing_rows = _load("playing_time.parquet")
    meta_path = MATCHES / "match_roles_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    if not appearances:
        errors.append("no player appearances were found")
    if not role_rows:
        errors.append("no role rows were found")
    if not playing_rows:
        errors.append("no playing-time rows were found")

    starts_by_player: dict[tuple[int, int, int], int] = defaultdict(int)
    role_starts_by_player: dict[tuple[int, int, int], int] = defaultdict(int)
    role_minutes_by_player: dict[tuple[int, int, int], int] = defaultdict(int)
    minutes_started_by_player: dict[tuple[int, int, int], int] = defaultdict(int)
    formations_seen: set[str] = set()
    focus_starts = 0
    focus_starts_with_role = 0

    for row in appearances:
        pid = int(row["player_id"])
        tid = int(row["team_id"])
        season = int(row["season"])
        key = (pid, tid, season)
        started = bool(row.get("started"))
        role_code = row.get("role_code")
        shape = row.get("formation_shape")
        if shape:
            formations_seen.add(str(shape))
        if started:
            starts_by_player[key] += 1
            minutes_started_by_player[key] += int(row.get("minutes_started") or 0)
            if tid == team_id:
                focus_starts += 1
                if role_code:
                    focus_starts_with_role += 1
        if not started and role_code:
            errors.append(f"{pid}: substitute has role {role_code}")
        if role_code:
            definition = roles.get(str(role_code))
            if not definition:
                errors.append(f"{pid}: unknown role code {role_code}")
            else:
                if row.get("role_family") != definition.get("family"):
                    errors.append(f"{pid}: appearance role family mismatch")
                if row.get("role_status") != "observed":
                    errors.append(f"{pid}: role-bearing appearance is not observed")
                if row.get("role_source") not in {"starting_xi_grid", "lineup_position"}:
                    errors.append(f"{pid}: role-bearing appearance has no source")
            if not started:
                errors.append(f"{pid}: role assigned without a start")
        if started and not role_code and tid == team_id and row.get("grid"):
            errors.append(
                f"{pid}: starter at grid {row.get('grid')} has no role "
                f"(shape {row.get('formation_shape')})"
            )

    for code in formations_seen:
        if code not in formations and code != "None":
            errors.append(f"formation shape {code!r} is not mapped in config/roles.yaml")

    for row in role_rows:
        pid = int(row["player_id"])
        tid = int(row["team_id"])
        season = int(row["season"])
        key = (pid, tid, season)
        code = str(row.get("role_code") or "")
        definition = roles.get(code)
        if not definition:
            errors.append(f"{pid}: role row has unknown code {code}")
        elif row.get("role_family") != definition.get("family"):
            errors.append(f"{pid}: role row family mismatch")
        starts = int(row.get("starts") or 0)
        minutes = int(row.get("minutes") or 0)
        if starts <= 0:
            errors.append(f"{pid}: role row has no starts")
        if minutes < 0:
            errors.append(f"{pid}: role row has negative minutes")
        if starts > starts_by_player.get(key, 0):
            errors.append(f"{pid}: role starts exceed starts_total")
        role_starts_by_player[key] += starts
        role_minutes_by_player[key] += minutes

    for row in playing_rows:
        pid = int(row["player_id"])
        tid = int(row["team_id"])
        season = int(row["season"])
        key = (pid, tid, season)
        starts = int(row.get("starts") or 0)
        subs = int(row.get("sub_apps") or 0)
        minutes = int(row.get("minutes") or 0)
        started = int(row.get("minutes_started") or 0)
        as_sub = int(row.get("minutes_as_sub") or 0)
        if starts < 0 or subs < 0 or minutes < 0 or started < 0 or as_sub < 0:
            errors.append(f"{pid}: negative playing-time value")
        if started + as_sub != minutes:
            errors.append(f"{pid}: playing-time minutes split does not add up")
        if starts > starts_by_player.get(key, 0):
            errors.append(f"{pid}: playing-time starts exceed appearance starts")
        appearances_for_key = sum(
            1
            for item in appearances
            if int(item["player_id"]) == pid
            and int(item["team_id"]) == tid
            and int(item["season"]) == season
            and item.get("competition") == row.get("competition")
        )
        if starts + subs != appearances_for_key:
            errors.append(f"{pid}: starts + subs do not match appearances")

    for key, starts in starts_by_player.items():
        if key[1] != team_id:
            continue
        with_role = role_starts_by_player.get(key, 0)
        if with_role > starts:
            errors.append(f"{key[0]}: role starts exceed starts")
        if role_minutes_by_player.get(key, 0) > minutes_started_by_player.get(key, 0):
            errors.append(f"{key[0]}: role minutes exceed minutes started")

    if meta:
        if int(meta.get("starts_total") or 0) != focus_starts:
            errors.append("meta starts_total does not match appearances")
        if int(meta.get("starts_with_role") or 0) != focus_starts_with_role:
            errors.append("meta starts_with_role does not match appearances")
        if meta.get("unmapped_formations"):
            errors.append(f"unmapped formations: {meta['unmapped_formations']}")
        if meta.get("fixtures_with_grid", 0) > meta.get("fixtures_total", 0):
            errors.append("meta grid fixtures exceed total fixtures")

    if errors:
        print("Role publication check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        "Role publication check passed "
        f"({len(appearances)} appearances, {len(role_rows)} role rows, "
        f"{focus_starts_with_role}/{focus_starts} Aberdeen starts with a role, "
        f"{len(formations_seen)} formation shapes)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
