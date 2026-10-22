"""Backfill career role evidence from historical starting-XI lineups.

The current-season Aberdeen role layer already exists. This module adds prior
clubs, current loan clubs and national teams for the configured recent seasons.
It is deliberately capped, resumable and on-demand: the daily pipeline only
re-reads the normalized evidence, it does not fetch historical lineups.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import polars as pl

from fitba.ingest.match_data import load_player_appearances
from fitba.ingest.position_stats import LEAGUE_IDS
from fitba.ingest.squad import load_squad_players
from fitba.normalize.career import (
    career_seasons,
    formation_policy_version,
    policy_version,
    season_weights,
)
from fitba.normalize.roles import (
    role_family,
    role_for_grid,
    role_side,
    shape_from_formation,
    shape_from_grid,
    shape_key,
)
from fitba.settings import NORMALIZED_DIR, ensure_dirs
from fitba.settings import aberdeen as aberdeen_config
from fitba.settings import roles as roles_config
from fitba.settings import source_ids as source_ids_config
from fitba.sources import api_football
from fitba.sources.base import IngestResult
from fitba.util.dates import (
    current_season,
    season_bounds,
    season_start_year,
    utc_now_iso,
)

EVIDENCE_COLUMNS = [
    "player_id",
    "player_key",
    "season",
    "fixture_id",
    "date",
    "team_id",
    "team_name",
    "scope",
    "scope_source",
    "league_id",
    "competition",
    "role_code",
    "role_family",
    "side",
    "grid",
    "formation",
    "formation_shape",
    "role_status",
    "role_source",
    "unknown_reason",
    "policy_version",
    "ingested_at",
]

CAREER_COLUMNS = [
    "player_id",
    "player_key",
    "season",
    "team_id",
    "team_name",
    "scope",
    "scope_source",
    "league_id",
    "competition",
    "role_code",
    "role_family",
    "starts",
    "weighted_starts",
    "ingested_at",
]

STATE_COLUMNS = [
    "player_id",
    "season",
    "team_id",
    "team_name",
    "league_id",
    "competition",
    "fixtures_total",
    "fixtures_checked",
    "next_fixture_index",
    "fixtures_with_lineups",
    "starts_seen",
    "starts_with_role",
    "status",
    "policy_version",
    "scope",
    "scope_source",
    "checked_at",
    "note",
]

PLAYED_STATUSES = {"FT", "AET", "PEN"}
TERMINAL_STATES = {"complete", "partial_lineups", "no_fixtures", "no_starts"}


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _season_label(year: int) -> str:
    return f"{year}-{(year + 1) % 100:02d}"


def _season_year(season: str) -> int:
    return season_start_year(season)


def _parse_date(value: Any) -> date | None:
    text = str(value or "")[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _career_config() -> dict[str, Any]:
    return roles_config().get("career") or {}


def _paths() -> dict[str, Path]:
    directory = NORMALIZED_DIR / "career"
    return {
        "dir": directory,
        "evidence": directory / "player_role_evidence.parquet",
        "career": directory / "player_career_roles.parquet",
        "state": directory / "career_backfill_state.parquet",
        "meta": directory / "career_roles_meta.json",
    }


def _load_frame(path: Path, columns: list[str]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    frame = pl.read_parquet(path)
    return frame.to_dicts() if frame.height else []


def _write_frame(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = (
        pl.DataFrame(rows, infer_schema_length=None).select(columns)
        if rows
        else pl.DataFrame({column: [] for column in columns})
    )
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.write_parquet(temporary)
    os.replace(temporary, path)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _team_info(team_id: int, cache: dict[int, dict[str, Any]], *, force: bool) -> dict[str, Any]:
    if team_id in cache:
        return cache[team_id]
    try:
        rows = api_football.team(team_id, ttl_hours=720, force=force)
    except Exception:  # noqa: BLE001 - scope falls back to previous club
        cache[team_id] = {}
        return {}
    info = (rows[0].get("team") if rows else {}) or {}
    cache[team_id] = info
    return info


def _loan_intervals(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    transfers: list[dict[str, Any]] = []
    for record in records:
        transfers.extend(record.get("transfers") or [])
    transfers.sort(key=lambda row: str(row.get("date") or ""))
    intervals: list[dict[str, Any]] = []
    for index, row in enumerate(transfers):
        if "loan" not in str(row.get("type") or "").casefold():
            continue
        start = _parse_date(row.get("date"))
        if start is None:
            continue
        end = None
        if index + 1 < len(transfers):
            end = _parse_date(transfers[index + 1].get("date"))
        teams = row.get("teams") or {}
        team = teams.get("in") or {}
        team_id = _int(team.get("id"))
        if team_id is None:
            continue
        intervals.append({"team_id": team_id, "start": start, "end": end})
    return intervals


def _scope_for(
    *,
    team_id: int,
    season: str,
    loan_intervals: list[dict[str, Any]],
    team_cache: dict[int, dict[str, Any]],
    force: bool,
) -> tuple[str, str]:
    parent_team_id = int(source_ids_config()["teams"][aberdeen_config()["club_id"]]["api_football"])
    if team_id == parent_team_id:
        return "aberdeen", "club_id"
    info = _team_info(team_id, team_cache, force=force)
    if info.get("national"):
        return "national_team", "team_metadata"
    start, end = season_bounds(season)
    for interval in loan_intervals:
        if interval["team_id"] != team_id:
            continue
        if interval["start"] <= end and (interval["end"] is None or interval["end"] >= start):
            return "loan_club", "transfer_history"
    return "previous_club", "fallback"


def discover_candidates(
    player_id: int,
    *,
    current: str,
    config: dict[str, Any],
    force: bool,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Find the player's team/league/season entries for the recent window."""
    career = config.get("career") or {}
    seasons = career_seasons(current, int(career.get("seasons") or 1))
    cache: dict[int, dict[str, Any]] = {}
    errors: list[str] = []
    try:
        transfers = api_football.transfers(
            player_id=player_id,
            ttl_hours=float((career.get("refresh") or {}).get("transfers_ttl_days") or 7) * 24,
            force=force,
        )
    except Exception as exc:  # noqa: BLE001
        transfers = []
        errors.append(f"transfers {player_id}: {exc}")
    intervals = _loan_intervals(transfers)
    candidates: dict[tuple[str, int, int], dict[str, Any]] = {}
    include_national = bool(career.get("include_national_team", True))
    for season in seasons:
        year = _season_year(season)
        ttl = (
            float((career.get("refresh") or {}).get("historical_ttl_days") or 30) * 24
            if season != current
            else float((career.get("refresh") or {}).get("current_season_ttl_hours") or 24)
        )
        try:
            details = api_football.player(player_id, season=year, ttl_hours=ttl, force=force)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"player {player_id} season {season}: {exc}")
            continue
        if not details:
            continue
        for entry in details[0].get("statistics") or []:
            league = entry.get("league") or {}
            team = entry.get("team") or {}
            games = entry.get("games") or {}
            entry_season = _int(league.get("season"))
            if entry_season is not None and entry_season != year:
                continue
            team_id = _int(team.get("id"))
            league_id = _int(league.get("id"))
            if team_id is None or league_id is None:
                continue
            lineups = _int(games.get("lineups"))
            appearances = _int(games.get("appearences", games.get("appearances")))
            if lineups == 0 and not appearances:
                continue
            if lineups is None and not appearances:
                continue
            team_name = str(team.get("name") or "Unknown team")
            scope, scope_source = _scope_for(
                team_id=team_id,
                season=season,
                loan_intervals=intervals,
                team_cache=cache,
                force=force,
            )
            if scope == "national_team" and not include_national:
                continue
            key = (season, team_id, league_id)
            candidates[key] = {
                "player_id": player_id,
                "player_key": f"api:player:{player_id}",
                "season": season,
                "season_year": year,
                "team_id": team_id,
                "team_name": team_name,
                "league_id": league_id,
                "competition": str(league.get("name") or "Unknown competition"),
                "lineups": lineups or 0,
                "appearances": appearances or 0,
                "scope": scope,
                "scope_source": scope_source,
            }
    ordered = sorted(
        candidates.values(),
        key=lambda row: (-int(row.get("lineups") or 0), str(row["season"]), row["team_name"]),
    )
    return ordered, errors


def _lineup_evidence(
    *,
    player_id: int,
    candidate: dict[str, Any],
    fixture: dict[str, Any],
    lineup: dict[str, Any],
    config: dict[str, Any],
    policy: str,
    now: str,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    starters = lineup.get("startXI") or []
    target = None
    for entry in starters:
        player = entry.get("player") or {}
        if _int(player.get("id")) == player_id:
            target = player
            break
    if target is None:
        return None, None, None
    grids = [(entry.get("player") or {}).get("grid") for entry in starters]
    grid_shape = shape_from_grid(grids)
    formation_shape = shape_from_formation(lineup.get("formation"))
    shape = grid_shape or formation_shape
    key = shape_key(shape)
    mapped = bool(key and key in (config.get("formations") or {}))
    role_code = None
    role_source = None
    unknown_reason = None
    grid = target.get("grid")
    if grid and mapped:
        role_code = role_for_grid(config, shape, grid)
        if role_code:
            role_source = "starting_xi_grid"
        else:
            unknown_reason = "invalid_slot"
    elif target.get("pos") == "G":
        role_code = "GK"
        role_source = "lineup_position"
        mapped = True
    else:
        unknown_reason = "unmapped_formation" if grid and shape and not mapped else "no_grid"
    fixture_meta = fixture.get("fixture") or {}
    fixture_id = _int(fixture_meta.get("id"))
    evidence = {
        "player_id": player_id,
        "player_key": f"api:player:{player_id}",
        "season": candidate["season"],
        "fixture_id": fixture_id,
        "date": str(fixture_meta.get("date") or "")[:10],
        "team_id": candidate["team_id"],
        "team_name": candidate["team_name"],
        "scope": candidate["scope"],
        "scope_source": candidate["scope_source"],
        "league_id": candidate["league_id"],
        "competition": candidate["competition"],
        "role_code": role_code,
        "role_family": role_family(config, role_code),
        "side": role_side(config, role_code),
        "grid": grid,
        "formation": lineup.get("formation"),
        "formation_shape": key,
        "role_status": "observed" if role_code else "unknown",
        "role_source": role_source,
        "unknown_reason": unknown_reason,
        "policy_version": policy,
        "ingested_at": now,
    }
    return evidence, role_code, key if grid_shape and not mapped else None


def ingest_candidate(
    *,
    candidate: dict[str, Any],
    config: dict[str, Any],
    policy: str,
    evidence_policy: str,
    current: str,
    force: bool,
    season_checked: dict[tuple[int, str], int],
    budget: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    career = config.get("career") or {}
    max_fixtures = int(career.get("max_fixtures_per_player_season") or 15)
    target_starts = int(career.get("target_starts") or 6)
    historical = candidate["season"] != current
    ttl = (
        float((career.get("refresh") or {}).get("historical_ttl_days") or 30) * 24
        if historical
        else 1.0
    )
    errors: list[str] = []
    try:
        fixtures = api_football.fixtures(
            int(candidate["league_id"]),
            int(candidate["season_year"]),
            team=int(candidate["team_id"]),
            ttl_hours=ttl,
            force=force,
        )
    except Exception as exc:  # noqa: BLE001
        return [], _state_row(candidate, "error", policy, note=str(exc)), [str(exc)]
    played = [
        fixture
        for fixture in fixtures
        if ((fixture.get("fixture") or {}).get("status") or {}).get("short") in PLAYED_STATUSES
    ]
    played.sort(
        key=lambda fixture: str((fixture.get("fixture") or {}).get("date") or ""),
        reverse=True,
    )
    evidence: list[dict[str, Any]] = []
    checked = 0
    with_lineups = 0
    starts_seen = 0
    starts_with_role = 0
    unmapped: str | None = None
    next_index = 0
    now = utc_now_iso()
    for index, fixture in enumerate(played):
        if budget is not None and api_football.network_requests() >= budget:
            return (
                evidence,
                _state_row(
                    candidate,
                    "budget",
                    policy,
                    fixtures_total=len(played),
                    fixtures_checked=checked,
                    next_fixture_index=index,
                    fixtures_with_lineups=with_lineups,
                    starts_seen=starts_seen,
                    starts_with_role=starts_with_role,
                    note="Request budget exhausted.",
                ),
                errors,
            )
        if season_checked[(candidate["player_id"], candidate["season"])] >= max_fixtures:
            return (
                evidence,
                _state_row(
                    candidate,
                    "capped",
                    policy,
                    fixtures_total=len(played),
                    fixtures_checked=checked,
                    next_fixture_index=index,
                    fixtures_with_lineups=with_lineups,
                    starts_seen=starts_seen,
                    starts_with_role=starts_with_role,
                    note=f"Season cap {max_fixtures} reached.",
                ),
                errors,
            )
        fixture_id = _int((fixture.get("fixture") or {}).get("id"))
        if fixture_id is None:
            continue
        try:
            lineups = api_football.fixtures_lineups(fixture_id, ttl_hours=ttl, force=force)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"lineups {fixture_id}: {exc}")
            checked += 1
            season_checked[(candidate["player_id"], candidate["season"])] += 1
            next_index = index + 1
            continue
        checked += 1
        season_checked[(candidate["player_id"], candidate["season"])] += 1
        next_index = index + 1
        lineup = next(
            (
                item
                for item in lineups
                if _int((item.get("team") or {}).get("id")) == int(candidate["team_id"])
            ),
            None,
        )
        if lineup is None:
            continue
        with_lineups += 1
        row, role_code, missing = _lineup_evidence(
            player_id=int(candidate["player_id"]),
            candidate=candidate,
            fixture=fixture,
            lineup=lineup,
            config=config,
            policy=evidence_policy,
            now=now,
        )
        if row is None:
            continue
        starts_seen += 1
        if role_code:
            starts_with_role += 1
        if missing and not unmapped:
            unmapped = missing
        evidence.append(row)
        if starts_with_role >= target_starts:
            return (
                evidence,
                _state_row(
                    candidate,
                    "complete",
                    policy,
                    fixtures_total=len(played),
                    fixtures_checked=checked,
                    next_fixture_index=next_index,
                    fixtures_with_lineups=with_lineups,
                    starts_seen=starts_seen,
                    starts_with_role=starts_with_role,
                    note=f"Target {target_starts} starts reached.",
                ),
                errors,
            )
    if not played:
        status = "no_fixtures"
    elif not with_lineups:
        status = "partial_lineups"
    elif starts_seen == 0:
        status = "no_starts"
    else:
        status = "complete"
    return (
        evidence,
        _state_row(
            candidate,
            status,
            policy,
            fixtures_total=len(played),
            fixtures_checked=checked,
            next_fixture_index=next_index,
            fixtures_with_lineups=with_lineups,
            starts_seen=starts_seen,
            starts_with_role=starts_with_role,
            note="All checked fixtures processed.",
        ),
        errors,
    )


def _state_row(
    candidate: dict[str, Any],
    status: str,
    policy: str,
    *,
    fixtures_total: int = 0,
    fixtures_checked: int = 0,
    next_fixture_index: int = 0,
    fixtures_with_lineups: int = 0,
    starts_seen: int = 0,
    starts_with_role: int = 0,
    note: str | None = None,
) -> dict[str, Any]:
    return {
        "player_id": candidate["player_id"],
        "season": candidate["season"],
        "team_id": candidate["team_id"],
        "team_name": candidate["team_name"],
        "league_id": candidate["league_id"],
        "competition": candidate["competition"],
        "fixtures_total": fixtures_total,
        "fixtures_checked": fixtures_checked,
        "next_fixture_index": next_fixture_index,
        "fixtures_with_lineups": fixtures_with_lineups,
        "starts_seen": starts_seen,
        "starts_with_role": starts_with_role,
        "status": status,
        "policy_version": policy,
        "scope": candidate["scope"],
        "scope_source": candidate["scope_source"],
        "checked_at": utc_now_iso(),
        "note": note,
    }


def current_evidence(
    *,
    config: dict[str, Any],
    policy: str,
    current: str,
    now: str,
) -> list[dict[str, Any]]:
    team_id = int(source_ids_config()["teams"][aberdeen_config()["club_id"]]["api_football"])
    season_year = _season_year(current)
    frame = load_player_appearances()
    rows = frame.to_dicts() if frame.height else []
    output: list[dict[str, Any]] = []
    for row in rows:
        if int(row.get("team_id") or 0) != team_id or int(row.get("season") or 0) != season_year:
            continue
        if not row.get("started"):
            continue
        code = row.get("role_code")
        output.append(
            {
                "player_id": int(row["player_id"]),
                "player_key": str(row["player_key"]),
                "season": current,
                "fixture_id": row.get("fixture_id"),
                "date": str(row.get("date") or "")[:10],
                "team_id": team_id,
                "team_name": row.get("team_name"),
                "scope": "aberdeen",
                "scope_source": "club_id",
                "league_id": None,
                "competition": row.get("competition"),
                "role_code": code,
                "role_family": row.get("role_family") or role_family(config, code),
                "side": role_side(config, code),
                "grid": row.get("grid"),
                "formation": row.get("formation"),
                "formation_shape": row.get("formation_shape"),
                "role_status": row.get("role_status") or ("observed" if code else "unknown"),
                "role_source": row.get("role_source"),
                "unknown_reason": None if code else "no_role_evidence",
                "policy_version": policy,
                "ingested_at": now,
            }
        )
    return output


def aggregate_evidence(
    evidence: list[dict[str, Any]],
    *,
    config: dict[str, Any],
    current: str,
    now: str,
) -> list[dict[str, Any]]:
    weights = season_weights(config, current)
    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in evidence:
        code = row.get("role_code")
        if not code:
            continue
        season = str(row.get("season") or "")
        key = (
            int(row["player_id"]),
            season,
            row.get("team_id"),
            row.get("scope"),
            row.get("league_id"),
            row.get("competition"),
            code,
        )
        bucket = grouped.setdefault(
            key,
            {
                "player_id": int(row["player_id"]),
                "player_key": str(row["player_key"]),
                "season": season,
                "team_id": row.get("team_id"),
                "team_name": row.get("team_name"),
                "scope": row.get("scope"),
                "scope_source": row.get("scope_source"),
                "league_id": row.get("league_id"),
                "competition": row.get("competition"),
                "role_code": code,
                "role_family": row.get("role_family") or role_family(config, code),
                "starts": 0,
                "weighted_starts": 0.0,
                "ingested_at": now,
            },
        )
        bucket["starts"] += 1
        bucket["weighted_starts"] += float(weights.get(season, 0.0))
    return list(grouped.values())


def scan_aberdeen_history(
    *,
    current: str,
    config: dict[str, Any],
    squad_ids: set[int],
    evidence_policy: str,
    budget: int | None,
    force: bool,
) -> tuple[dict[int, list[dict[str, Any]]], list[dict[str, Any]], list[str]]:
    """Scan prior Aberdeen seasons for every current squad starter.

    A player may have no provider stats entry for a prior season, or an entry
    whose lineups count is zero. Scanning the club's fixtures covers those
    players without asking each player's stats row for permission.
    """
    career = config.get("career") or {}
    seasons = career_seasons(current, int(career.get("seasons") or 1))[1:]
    parent_team_id = int(source_ids_config()["teams"][aberdeen_config()["club_id"]]["api_football"])
    ttl = float((career.get("refresh") or {}).get("historical_ttl_days") or 30) * 24
    max_fixtures = int((career.get("backfill") or {}).get("club_scan_max_fixtures") or 60)
    by_player: dict[int, list[dict[str, Any]]] = defaultdict(list)
    scans: list[dict[str, Any]] = []
    errors: list[str] = []
    now = utc_now_iso()

    for season in seasons:
        year = _season_year(season)
        fixtures_total = 0
        fixtures_checked = 0
        starts_found = 0
        season_errors: list[str] = []
        for league_id in LEAGUE_IDS:
            if budget is not None and api_football.network_requests() >= budget:
                season_errors.append("Request budget exhausted during club scan.")
                break
            try:
                fixtures = api_football.fixtures(
                    int(league_id),
                    year,
                    team=parent_team_id,
                    ttl_hours=ttl,
                    force=force,
                )
            except Exception as exc:  # noqa: BLE001
                season_errors.append(f"fixtures {season} league {league_id}: {exc}")
                continue
            played = [
                fixture
                for fixture in fixtures
                if ((fixture.get("fixture") or {}).get("status") or {}).get("short")
                in PLAYED_STATUSES
            ]
            played.sort(key=lambda fixture: str((fixture.get("fixture") or {}).get("date") or ""))
            fixtures_total += len(played)
            for fixture in played:
                if budget is not None and api_football.network_requests() >= budget:
                    season_errors.append("Request budget exhausted during club scan.")
                    break
                if fixtures_checked >= max_fixtures:
                    break
                fixture_meta = fixture.get("fixture") or {}
                fixture_id = _int(fixture_meta.get("id"))
                if fixture_id is None:
                    continue
                try:
                    lineups = api_football.fixtures_lineups(fixture_id, ttl_hours=ttl, force=force)
                except Exception as exc:  # noqa: BLE001
                    season_errors.append(f"lineups {fixture_id}: {exc}")
                    fixtures_checked += 1
                    continue
                fixtures_checked += 1
                lineup = next(
                    (
                        item
                        for item in lineups
                        if _int((item.get("team") or {}).get("id")) == parent_team_id
                    ),
                    None,
                )
                if lineup is None:
                    continue
                league = fixture.get("league") or {}
                candidate = {
                    "player_id": None,
                    "season": season,
                    "season_year": year,
                    "team_id": parent_team_id,
                    "team_name": "Aberdeen",
                    "league_id": int(league_id),
                    "competition": str(league.get("name") or "Unknown competition"),
                    "scope": "aberdeen",
                    "scope_source": "club_id",
                }
                for entry in lineup.get("startXI") or []:
                    player = entry.get("player") or {}
                    player_id = _int(player.get("id"))
                    if player_id is None or player_id not in squad_ids:
                        continue
                    candidate_row = {**candidate, "player_id": player_id}
                    row, _role_code, _missing = _lineup_evidence(
                        player_id=player_id,
                        candidate=candidate_row,
                        fixture=fixture,
                        lineup=lineup,
                        config=config,
                        policy=evidence_policy,
                        now=now,
                    )
                    if row is None:
                        continue
                    by_player[player_id].append(row)
                    starts_found += 1
            if fixtures_checked >= max_fixtures:
                break
        scans.append(
            {
                "season": season,
                "fixtures_total": fixtures_total,
                "fixtures_checked": fixtures_checked,
                "starts_found": starts_found,
                "errors": season_errors,
            }
        )
        errors.extend(f"{season}: {error}" for error in season_errors)
        if budget is not None and api_football.network_requests() >= budget:
            break
    return by_player, scans, errors


def _career_meta(
    *,
    evidence: list[dict[str, Any]],
    state: list[dict[str, Any]],
    config: dict[str, Any],
    current: str,
    budget: int | None,
    errors: list[str],
    started_at: str,
    club_scans: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    status_counts: dict[str, int] = defaultdict(int)
    for row in state:
        status_counts[str(row.get("status") or "unknown")] += 1
    unmapped: dict[str, int] = defaultdict(int)
    for row in evidence:
        if row.get("role_status") == "unknown":
            unmapped[str(row.get("unknown_reason") or "unknown")] += 1
    seasons = career_seasons(current, int((config.get("career") or {}).get("seasons") or 1))
    return {
        "generated_at": started_at,
        "status": "available" if evidence else "unavailable",
        "policy_version": policy_version(config),
        "seasons": seasons,
        "players": len({int(row["player_id"]) for row in evidence}),
        "pairs_total": len(state),
        "pairs_complete": status_counts.get("complete", 0),
        "pairs_skipped": 0,
        "pairs_capped": status_counts.get("capped", 0),
        "pairs_error": status_counts.get("error", 0),
        "pairs_budget": status_counts.get("budget", 0),
        "evidence_rows": len(evidence),
        "starts_with_role": sum(1 for row in evidence if row.get("role_code")),
        "network_requests": api_football.network_requests(),
        "budget": budget,
        "budget_exhausted": bool(budget and api_football.network_requests() >= budget),
        "unknown_reasons": dict(sorted(unmapped.items())),
        "club_scans": club_scans or [],
        "errors": errors[:50],
    }


def ingest_career_roles(
    *,
    current: str | None = None,
    player_ids: list[int] | None = None,
    max_requests: int | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> IngestResult:
    ensure_dirs()
    config = roles_config()
    career = config.get("career") or {}
    current = current or current_season()
    policy = policy_version(config)
    evidence_policy = formation_policy_version(config)
    budget = int(max_requests or (career.get("backfill") or {}).get("max_requests_per_run") or 1500)
    api_football.set_min_interval(
        float((career.get("backfill") or {}).get("request_interval_seconds") or 0.25)
    )
    api_football.reset_network_requests()
    paths = _paths()
    evidence = _load_frame(paths["evidence"], EVIDENCE_COLUMNS)
    state = _load_frame(paths["state"], STATE_COLUMNS)
    players = load_squad_players().to_dicts()
    if player_ids:
        players = [row for row in players if int(row["player_id"]) in set(player_ids)]
    errors: list[str] = []
    started_at = utc_now_iso()
    season_checked: dict[tuple[int, str], int] = defaultdict(int)
    state_by_key = {
        (
            int(row["player_id"]),
            str(row["season"]),
            int(row["team_id"]),
            int(row["league_id"]),
        ): row
        for row in state
    }
    dry_rows: list[dict[str, Any]] = []
    club_evidence: dict[int, list[dict[str, Any]]] = {}
    club_scans: list[dict[str, Any]] = []
    if not dry_run:
        club_evidence, club_scans, club_errors = scan_aberdeen_history(
            current=current,
            config=config,
            squad_ids={int(player["player_id"]) for player in players},
            evidence_policy=evidence_policy,
            budget=budget,
            force=force,
        )
        errors.extend(club_errors)
    for player in players:
        player_id = int(player["player_id"])
        candidates, discovery_errors = discover_candidates(
            player_id, current=current, config=config, force=force
        )
        errors.extend(discovery_errors)
        if dry_run:
            dry_rows.append(
                {
                    "player_id": player_id,
                    "name": player.get("name"),
                    "candidates": len(candidates),
                    "estimated_lineups": min(
                        int(career.get("max_fixtures_per_player_season") or 15),
                        sum(int(row.get("lineups") or 0) for row in candidates),
                    ),
                }
            )
            continue
        fresh_evidence: list[dict[str, Any]] = []
        fresh_state: list[dict[str, Any]] = []
        now = utc_now_iso()
        current_rows = current_evidence(
            config=config, policy=evidence_policy, current=current, now=now
        )
        fresh_evidence.extend(row for row in current_rows if int(row["player_id"]) == player_id)
        fresh_evidence.extend(club_evidence.get(player_id, []))
        for candidate in candidates:
            if candidate["scope"] == "aberdeen":
                # Current Aberdeen comes from player_appearances; prior
                # Aberdeen seasons come from the shared club scan.
                continue
            key = (
                player_id,
                str(candidate["season"]),
                int(candidate["team_id"]),
                int(candidate["league_id"]),
            )
            previous = state_by_key.get(key)
            if (
                not force
                and previous
                and previous.get("policy_version") == policy
                and previous.get("status") in TERMINAL_STATES
                and candidate["season"] != current
            ):
                fresh_state.append(previous)
                continue
            rows, state_row, candidate_errors = ingest_candidate(
                candidate=candidate,
                config=config,
                policy=policy,
                evidence_policy=evidence_policy,
                current=current,
                force=force,
                season_checked=season_checked,
                budget=budget,
            )
            fresh_evidence.extend(rows)
            fresh_state.append(state_row)
            errors.extend(candidate_errors)
            if api_football.network_requests() >= budget:
                break
        evidence = [row for row in evidence if int(row["player_id"]) != player_id] + fresh_evidence
        state = [row for row in state if int(row["player_id"]) != player_id] + fresh_state
        # Checkpoint after each player.
        _write_frame(paths["evidence"], evidence, EVIDENCE_COLUMNS)
        _write_frame(paths["state"], state, STATE_COLUMNS)
        if api_football.network_requests() >= budget:
            errors.append("Request budget exhausted; rerun to continue.")
            break
    if dry_run:
        return IngestResult(
            source="api_football",
            status="ok",
            rows=len(dry_rows),
            details={
                "dry_run": True,
                "budget": budget,
                "network_requests": api_football.network_requests(),
                "players": dry_rows,
            },
        )
    career_rows = aggregate_evidence(evidence, config=config, current=current, now=started_at)
    _write_frame(paths["evidence"], evidence, EVIDENCE_COLUMNS)
    _write_frame(paths["career"], career_rows, CAREER_COLUMNS)
    _write_frame(paths["state"], state, STATE_COLUMNS)
    meta = _career_meta(
        evidence=evidence,
        state=state,
        config=config,
        current=current,
        budget=budget,
        errors=errors,
        started_at=started_at,
        club_scans=club_scans,
    )
    _write_json(paths["meta"], meta)
    return IngestResult(
        source="api_football",
        status="ok",
        rows=len(evidence),
        path=str(paths["evidence"]),
        errors=errors or None,
        details=meta,
    )


def refresh_career_roles(*, current: str | None = None) -> IngestResult:
    """Rebuild the current Aberdeen slice and aggregates without network calls."""
    ensure_dirs()
    config = roles_config()
    current = current or current_season()
    evidence_policy = formation_policy_version(config)
    paths = _paths()
    now = utc_now_iso()
    evidence = _load_frame(paths["evidence"], EVIDENCE_COLUMNS)
    for row in evidence:
        # Slot/override policy changes do not change the role observed from a
        # formation grid; re-stamp the evidence to the formation policy.
        row["policy_version"] = evidence_policy
    evidence = [
        row
        for row in evidence
        if not (row.get("scope") == "aberdeen" and row.get("season") == current)
    ]
    evidence.extend(
        current_evidence(config=config, policy=evidence_policy, current=current, now=now)
    )
    career_rows = aggregate_evidence(evidence, config=config, current=current, now=now)
    state = _load_frame(paths["state"], STATE_COLUMNS)
    full_policy = policy_version(config)
    for row in state:
        # The backfill state is still valid when only slot/override policy
        # changes; formation-map changes should be followed by a backfill.
        row["policy_version"] = full_policy
    _write_frame(paths["evidence"], evidence, EVIDENCE_COLUMNS)
    _write_frame(paths["career"], career_rows, CAREER_COLUMNS)
    _write_frame(paths["state"], state, STATE_COLUMNS)
    previous_meta = load_career_meta()
    meta = _career_meta(
        evidence=evidence,
        state=state,
        config=config,
        current=current,
        budget=None,
        errors=[],
        started_at=now,
        club_scans=previous_meta.get("club_scans", []),
    )
    if previous_meta.get("generated_at"):
        meta["last_backfill"] = {
            key: previous_meta.get(key)
            for key in (
                "generated_at",
                "network_requests",
                "budget",
                "budget_exhausted",
                "pairs_complete",
                "pairs_capped",
                "pairs_error",
            )
        }
    _write_json(paths["meta"], meta)
    return IngestResult(
        source="api_football",
        status="ok",
        rows=len(evidence),
        path=str(paths["evidence"]),
        details=meta,
    )


def load_evidence() -> pl.DataFrame:
    path = _paths()["evidence"]
    if not path.exists():
        return pl.DataFrame({column: [] for column in EVIDENCE_COLUMNS})
    return pl.read_parquet(path)


def load_career_roles() -> pl.DataFrame:
    path = _paths()["career"]
    if not path.exists():
        return pl.DataFrame({column: [] for column in CAREER_COLUMNS})
    return pl.read_parquet(path)


def load_career_meta() -> dict[str, Any]:
    path = _paths()["meta"]
    if not path.exists():
        return {
            "generated_at": None,
            "policy_version": None,
            "seasons": [],
            "players": 0,
            "pairs_total": 0,
            "pairs_complete": 0,
            "pairs_capped": 0,
            "pairs_error": 0,
            "pairs_budget": 0,
            "evidence_rows": 0,
            "starts_with_role": 0,
            "network_requests": 0,
            "budget": None,
            "budget_exhausted": False,
            "unknown_reasons": {},
            "errors": [],
            "status": "unavailable",
            "unknown_reason": "career_backfill_not_run",
        }
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = [
    "CAREER_COLUMNS",
    "EVIDENCE_COLUMNS",
    "STATE_COLUMNS",
    "aggregate_evidence",
    "current_evidence",
    "discover_candidates",
    "ingest_career_roles",
    "load_career_meta",
    "load_career_roles",
    "load_evidence",
    "refresh_career_roles",
]
