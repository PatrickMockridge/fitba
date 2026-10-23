"""Scouting pool and role backfill.

The pool is a licensed API-Football season-statistics snapshot for the leagues
in ``config/scouting/leagues.yaml``. Role families come from starting-XI grids
in ``/fixtures/lineups``; where the provider sends neither a formation nor a
grid, the player falls back to the provider position group and the coverage says
so. No role is inferred from a generic position, a shirt number or the bench.

Every request is cached by the API adapter. A full run is resumable: cached
responses cost no request, and ``--budget`` stops cleanly at the provider's
daily allowance. Raw responses are never published.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

import polars as pl

from fitba.normalize.player_stats import parse_stat_entry
from fitba.normalize.roles import (
    primary_role,
    role_family,
    role_for_grid,
    shape_from_formation,
    shape_from_grid,
    shape_key,
)
from fitba.settings import NORMALIZED_DIR, ensure_dirs, scouting_leagues
from fitba.settings import roles as roles_config
from fitba.sources import api_football
from fitba.util.dates import current_season, utc_now_iso

SCOUTING_DIR = NORMALIZED_DIR / "scouting"
PLAYER_SEASON_PATH = SCOUTING_DIR / "player_season.parquet"
POOL_META_PATH = SCOUTING_DIR / "meta.json"
LINEUPS_PATH = SCOUTING_DIR / "lineups.parquet"
PLAYER_ROLES_PATH = SCOUTING_DIR / "player_roles.parquet"
ROLES_STATE_PATH = SCOUTING_DIR / "roles_state.json"
PLAYED_STATUSES = {"FT", "AET", "PEN"}

POOL_COLUMNS = [
    "player_id",
    "player_key",
    "name",
    "full_name",
    "firstname",
    "lastname",
    "age",
    "birth_date",
    "nationality",
    "position_group",
    "competition_id",
    "competition",
    "league_slug",
    "country",
    "league_tier",
    "provider_league_id",
    "season",
    "team_id",
    "team_name",
    "teams",
    "multi_team",
    "scope",
    "appearances",
    "starts",
    "minutes",
    "goals",
    "assists",
    "yellow_cards",
    "red_cards",
    "rating",
    "shots_total",
    "shots_on",
    "passes_total",
    "passes_key",
    "pass_accuracy",
    "saves",
    "conceded",
    "tackles",
    "blocks",
    "interceptions",
    "duels_total",
    "duels_won",
    "dribbles_attempts",
    "dribbles_success",
    "fouls_drawn",
    "fouls_committed",
    "penalty_won",
    "penalty_committed",
    "penalty_scored",
    "penalty_missed",
    "penalty_saved",
    "ingested_at",
    "stale",
]

LINEUP_COLUMNS = [
    "fixture_id",
    "league_id",
    "season",
    "date",
    "team_id",
    "team_name",
    "player_id",
    "player_name",
    "grid",
    "role_code",
    "role_family",
    "ingested_at",
]

ROLE_COLUMNS = [
    "player_id",
    "player_key",
    "league_id",
    "season",
    "team_id",
    "team_name",
    "starts_total",
    "starts_with_role",
    "role_code",
    "role_family",
    "role_family_share",
    "role_status",
]

COUNT_FIELDS = [
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
    "duels_total",
    "duels_won",
    "dribbles_attempts",
    "dribbles_success",
    "fouls_drawn",
    "fouls_committed",
    "penalty_won",
    "penalty_committed",
    "penalty_scored",
    "penalty_missed",
    "penalty_saved",
]
POSITION_GROUPS = {
    "Goalkeeper": "GK",
    "Defender": "DEF",
    "Midfielder": "MID",
    "Attacker": "FWD",
}


def season_year(season: str) -> int:
    try:
        return int(str(season).split("-", 1)[0])
    except ValueError:
        return api_football.CURRENT_SEASON


def _leagues(*, include_disabled: bool = False) -> list[dict[str, Any]]:
    pool = (scouting_leagues() or {}).get("pool") or []
    return [
        item
        for item in pool
        if (include_disabled or bool(item.get("enabled")))
        and (item.get("provider") or {}).get("api_football_id") is not None
    ]


def _select_leagues(value: str | None) -> list[dict[str, Any]]:
    leagues = _leagues()
    if not value or value == "all":
        return leagues
    wanted = {part.strip() for part in str(value).split(",") if part.strip()}
    known = {str(item["id"]) for item in leagues}
    unknown = wanted - known
    if unknown:
        raise ValueError(f"unknown scouting leagues: {sorted(unknown)}")
    return [item for item in leagues if str(item["id"]) in wanted]


def _sum(rows: list[dict[str, Any]], field: str) -> int | None:
    values = [row.get(field) for row in rows if row.get(field) is not None]
    return sum(int(value) for value in values if value is not None) if values else None


def _weighted_accuracy(rows: list[dict[str, Any]]) -> float | None:
    weighted = 0.0
    weight = 0
    for row in rows:
        total = row.get("passes_total")
        accuracy = row.get("pass_accuracy")
        if total is None or accuracy is None:
            continue
        weighted += float(total) * float(accuracy)
        weight += int(total)
    return round(weighted / weight, 2) if weight else None


def _weighted_rating(rows: list[dict[str, Any]]) -> float | None:
    weighted = 0.0
    weight = 0
    for row in rows:
        rating = row.get("rating")
        appearances = row.get("appearances")
        if rating is None:
            continue
        count = int(appearances or 1)
        weighted += float(rating) * count
        weight += count
    return round(weighted / weight, 2) if weight else None


def _pool_row(
    raw: dict[str, Any],
    league: dict[str, Any],
    *,
    year: int,
    ingested_at: str,
) -> dict[str, Any] | None:
    player = raw.get("player") or {}
    player_id = player.get("id")
    if player_id is None:
        return None
    provider_id = int((league.get("provider") or {})["api_football_id"])
    entries: list[dict[str, Any]] = []
    for entry in raw.get("statistics") or []:
        entry_league = entry.get("league") or {}
        if int(entry_league.get("id") or 0) != provider_id:
            continue
        parsed = parse_stat_entry(
            player_id=int(player_id),
            player_key=f"api:player:{player_id}",
            entry=entry,
            scope="pool",
            season_year=year,
            ingested_at=ingested_at,
        )
        if parsed is not None:
            entries.append(parsed)
    if not entries:
        return None
    # A player may appear for more than one club in the same league; sum the
    # measurable output and keep the club with the most minutes as the display
    # club. The row is labelled multi_team rather than silently choosing one.
    by_minutes = sorted(entries, key=lambda row: int(row.get("minutes") or 0), reverse=True)
    primary = by_minutes[0]
    teams = sorted({str(row.get("team_name") or "") for row in entries if row.get("team_name")})
    row: dict[str, Any] = {
        "player_id": int(player_id),
        "player_key": f"api:player:{player_id}",
        "name": str(player.get("name") or ""),
        "full_name": " ".join(
            part
            for part in [str(player.get("firstname") or ""), str(player.get("lastname") or "")]
            if part
        )
        or str(player.get("name") or ""),
        "firstname": player.get("firstname"),
        "lastname": player.get("lastname"),
        "age": player.get("age"),
        "birth_date": (player.get("birth") or {}).get("date"),
        "nationality": player.get("nationality"),
        "position_group": "UNKNOWN",
        "competition_id": str(league["id"]),
        "competition": str(league["name"]),
        "league_slug": str(league["slug"]),
        "country": str(league.get("country") or ""),
        "league_tier": league.get("tier"),
        "provider_league_id": provider_id,
        "season": year,
        "team_id": primary.get("team_id"),
        "team_name": primary.get("team_name"),
        "teams": "|".join(teams),
        "multi_team": len(teams) > 1,
        "scope": "pool",
        "pass_accuracy": _weighted_accuracy(entries),
        "rating": _weighted_rating(entries),
        "ingested_at": ingested_at,
        "stale": False,
    }
    for field in COUNT_FIELDS:
        row[field] = _sum(entries, field)
    # The provider position is on the games block, not the parsed stat row.
    position = None
    for entry in raw.get("statistics") or []:
        if int((entry.get("league") or {}).get("id") or 0) == provider_id:
            position = (entry.get("games") or {}).get("position")
            if position:
                break
    row["position_group"] = POSITION_GROUPS.get(str(position or ""), "UNKNOWN")
    return row


def _fetch_players(
    provider_id: int, year: int, *, refresh: bool
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    page = 1
    total = 1
    while page <= total and page <= 80:
        payload = api_football.request_payload(
            "/players",
            ttl_hours=24,
            force=refresh,
            league=provider_id,
            season=year,
            page=page,
        )
        rows.extend(payload.get("response") or [])
        total = int((payload.get("paging") or {}).get("total") or 1)
        page += 1
    return rows, total


def ingest_pool(
    *,
    season: str | None = None,
    refresh: bool = False,
    league_ids: str | None = None,
) -> dict[str, Any]:
    ensure_dirs()
    SCOUTING_DIR.mkdir(parents=True, exist_ok=True)
    season_label = season or current_season()
    year = season_year(season_label)
    generated_at = utc_now_iso()
    leagues = _select_leagues(league_ids)
    all_rows: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    for league in leagues:
        provider = league.get("provider") or {}
        provider_id = int(provider["api_football_id"])
        record: dict[str, Any] = {
            "id": str(league["id"]),
            "slug": str(league["slug"]),
            "name": str(league["name"]),
            "country": str(league.get("country") or ""),
            "provider_league_id": provider_id,
            "player_stats": bool(provider.get("player_stats")),
            "lineups": bool(provider.get("lineups")),
            "status": "ok",
            "pages": 0,
            "rows": 0,
            "rated": 0,
            "with_minutes": 0,
            "error": None,
            "fetched_at": generated_at,
        }
        if not provider.get("player_stats"):
            record["status"] = "no_player_stats"
            coverage.append(record)
            continue
        try:
            raw_rows, pages = _fetch_players(provider_id, year, refresh=refresh)
            parsed = [
                row
                for row in (
                    _pool_row(item, league, year=year, ingested_at=generated_at)
                    for item in raw_rows
                )
                if row is not None and row.get("team_id") != 252
            ]
            record["pages"] = pages
            record["rows"] = len(parsed)
            record["rated"] = sum(1 for row in parsed if row.get("rating") is not None)
            record["with_minutes"] = sum(1 for row in parsed if (row.get("minutes") or 0) > 0)
            if not parsed:
                record["status"] = "no_player_stats"
            all_rows.extend(parsed)
        except Exception as error:  # noqa: BLE001 - one league must not stop the pool
            record["status"] = "error"
            record["error"] = f"{type(error).__name__}: {error}"
        coverage.append(record)

    # Keep the last good rows for a league that errored in this run, marked
    # stale. A failed refresh never silently deletes a league from the search.
    if POOL_META_PATH.exists() and PLAYER_SEASON_PATH.exists():
        try:
            previous = pl.read_parquet(PLAYER_SEASON_PATH)
        except Exception:  # noqa: BLE001
            previous = pl.DataFrame()
        failed = {item["id"] for item in coverage if item["status"] in {"error", "no_player_stats"}}
        if failed and previous.height:
            keep = previous.filter(pl.col("competition_id").is_in(sorted(failed))).with_columns(
                pl.lit(True).alias("stale")
            )
            if keep.height:
                all_rows.extend(keep.to_dicts())

    frame = pl.DataFrame(all_rows, infer_schema_length=None) if all_rows else pl.DataFrame()
    for column in POOL_COLUMNS:
        if column not in frame.columns:
            frame = frame.with_columns(pl.lit(None).alias(column))
    if frame.height:
        frame = frame.select(POOL_COLUMNS).unique(
            subset=["player_id", "competition_id"], keep="first", maintain_order=True
        )
    frame.write_parquet(PLAYER_SEASON_PATH)
    meta = {
        "schema_version": "1.0.0",
        "season": season_label,
        "season_year": year,
        "generated_at": generated_at,
        "leagues": coverage,
        "totals": {
            "leagues": len(coverage),
            "searchable": sum(1 for item in coverage if item["status"] == "ok"),
            "rows": frame.height,
            "rated": int(frame["rating"].drop_nulls().len()) if frame.height else 0,
        },
    }
    POOL_META_PATH.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def _fixtures(provider_id: int, year: int, *, refresh: bool) -> list[dict[str, Any]]:
    payload = api_football.request_payload(
        "/fixtures",
        ttl_hours=6,
        force=refresh,
        league=provider_id,
        season=year,
    )
    return list(payload.get("response") or [])


def _lineups(fixture_id: int, *, refresh: bool) -> list[dict[str, Any]]:
    return api_football.fixtures_lineups(fixture_id, ttl_hours=720, force=refresh)


def _role_rows_for_fixture(
    fixture: dict[str, Any],
    league: dict[str, Any],
    *,
    year: int,
    ingested_at: str,
    config: dict[str, Any],
    refresh: bool,
) -> tuple[list[dict[str, Any]], bool, set[str]]:
    fixture_id = int((fixture.get("fixture") or {}).get("id") or 0)
    date = (fixture.get("fixture") or {}).get("date")
    rows: list[dict[str, Any]] = []
    role_available = False
    unmapped: set[str] = set()
    for team in _lineups(fixture_id, refresh=refresh):
        team_info = team.get("team") or {}
        team_id = team_info.get("id")
        team_name = str(team_info.get("name") or "")
        starters = team.get("startXI") or []
        grids = [((item.get("player") or {}).get("grid")) for item in starters]
        shape = shape_from_grid(grids) or shape_from_formation(team.get("formation"))
        if shape is None:
            continue
        key = shape_key(shape)
        if not key or not (config.get("formations") or {}).get(key):
            if key:
                unmapped.add(key)
            continue
        for item in starters:
            player = item.get("player") or {}
            player_id = player.get("id")
            grid = player.get("grid")
            if player_id is None or not grid:
                continue
            code = role_for_grid(config, shape, grid)
            if not code:
                continue
            role_available = True
            rows.append(
                {
                    "fixture_id": fixture_id,
                    "league_id": str(league["id"]),
                    "season": year,
                    "date": date,
                    "team_id": team_id,
                    "team_name": team_name,
                    "player_id": int(player_id),
                    "player_name": str(player.get("name") or ""),
                    "grid": grid,
                    "role_code": code,
                    "role_family": role_family(config, code),
                    "ingested_at": ingested_at,
                }
            )
    return rows, role_available, unmapped


def _aggregate_roles(rows: list[dict[str, Any]], *, year: int) -> list[dict[str, Any]]:
    config = roles_config()
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(int(row["player_id"]), str(row["league_id"]))].append(row)
    out: list[dict[str, Any]] = []
    for (player_id, league_id), items in grouped.items():
        counts: dict[str, int] = defaultdict(int)
        team_counts: dict[tuple[Any, str], int] = defaultdict(int)
        for item in items:
            counts[str(item["role_code"])] += 1
            team_counts[(item.get("team_id"), str(item.get("team_name") or ""))] += 1
        starts_total = sum(counts.values())
        role_rows = [
            {"code": code, "starts": count, "minutes": 0} for code, count in counts.items()
        ]
        code, family = primary_role(role_rows, config)
        primary_team = max(team_counts, key=lambda key: (team_counts[key], str(key[1])))
        family_starts = sum(
            count for role_code, count in counts.items() if role_family(config, role_code) == family
        )
        out.append(
            {
                "player_id": player_id,
                "player_key": f"api:player:{player_id}",
                "league_id": league_id,
                "season": year,
                "team_id": primary_team[0],
                "team_name": primary_team[1],
                "starts_total": starts_total,
                "starts_with_role": starts_total,
                "role_code": code,
                "role_family": family,
                "role_family_share": round(family_starts / starts_total, 3)
                if starts_total
                else None,
                "role_status": "observed"
                if family and family_starts / max(starts_total, 1) >= 0.6
                else "mixed"
                if family
                else "unknown",
            }
        )
    return out


def ingest_roles(
    *,
    season: str | None = None,
    budget: int = 6500,
    refresh: bool = False,
    league_ids: str | None = None,
) -> dict[str, Any]:
    ensure_dirs()
    SCOUTING_DIR.mkdir(parents=True, exist_ok=True)
    season_label = season or current_season()
    year = season_year(season_label)
    generated_at = utc_now_iso()
    config = roles_config()
    leagues = [
        league
        for league in _select_leagues(league_ids)
        if (league.get("provider") or {}).get("player_stats")
    ]
    all_rows: list[dict[str, Any]] = []
    state: dict[str, Any] = {
        "schema_version": "1.0.0",
        "season": season_label,
        "season_year": year,
        "generated_at": generated_at,
        "leagues": [],
        "totals": {},
    }
    stop = False
    for league in leagues:
        provider_id = int((league.get("provider") or {})["api_football_id"])
        record: dict[str, Any] = {
            "id": str(league["id"]),
            "slug": str(league["slug"]),
            "fixtures_total": 0,
            "played": 0,
            "lineups_fetched": 0,
            "role_teams": 0,
            "role_unavailable_teams": 0,
            "unmapped_formations": [],
            "missing_fixtures": 0,
            "error": None,
            "updated_at": generated_at,
        }
        try:
            fixtures = _fixtures(provider_id, year, refresh=refresh)
            played = [
                item
                for item in fixtures
                if str(((item.get("fixture") or {}).get("status") or {}).get("short") or "")
                in PLAYED_STATUSES
            ]
            record["fixtures_total"] = len(fixtures)
            record["played"] = len(played)
            for fixture in played:
                if stop:
                    break
                if api_football.network_requests() >= budget:
                    stop = True
                    break
                fixture_id = (fixture.get("fixture") or {}).get("id")
                if fixture_id is None:
                    continue
                try:
                    rows, available, unmapped = _role_rows_for_fixture(
                        fixture,
                        league,
                        year=year,
                        ingested_at=generated_at,
                        config=config,
                        refresh=refresh,
                    )
                except Exception:  # noqa: BLE001 - a missing lineup is coverage, not a crash
                    record["missing_fixtures"] += 1
                    continue
                all_rows.extend(rows)
                record["lineups_fetched"] += 1
                record["role_teams"] += 1 if available else 0
                record["role_unavailable_teams"] += 0 if available else 1
                for shape in unmapped:
                    if shape not in record["unmapped_formations"]:
                        record["unmapped_formations"].append(shape)
        except Exception as error:  # noqa: BLE001
            record["error"] = f"{type(error).__name__}: {error}"
        state["leagues"].append(record)
        if stop:
            break

    lineups = pl.DataFrame(all_rows, infer_schema_length=None) if all_rows else pl.DataFrame()
    for column in LINEUP_COLUMNS:
        if column not in lineups.columns:
            lineups = lineups.with_columns(pl.lit(None).alias(column))
    if lineups.height:
        lineups = lineups.select(LINEUP_COLUMNS)
    lineups.write_parquet(LINEUPS_PATH)

    role_rows = _aggregate_roles(all_rows, year=year) if all_rows else []
    roles = pl.DataFrame(role_rows, infer_schema_length=None) if role_rows else pl.DataFrame()
    for column in ROLE_COLUMNS:
        if column not in roles.columns:
            roles = roles.with_columns(pl.lit(None).alias(column))
    if roles.height:
        roles = roles.select(ROLE_COLUMNS)
    roles.write_parquet(PLAYER_ROLES_PATH)

    state["totals"] = {
        "leagues": len(state["leagues"]),
        "played": sum(item["played"] for item in state["leagues"]),
        "lineups_fetched": sum(item["lineups_fetched"] for item in state["leagues"]),
        "role_players": roles.height,
        "requests": api_football.network_requests(),
        "budget": budget,
        "stopped_on_budget": stop,
    }
    ROLES_STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state


def scouting_status() -> dict[str, Any]:
    meta = (
        json.loads(POOL_META_PATH.read_text(encoding="utf-8")) if POOL_META_PATH.exists() else None
    )
    state = (
        json.loads(ROLES_STATE_PATH.read_text(encoding="utf-8"))
        if ROLES_STATE_PATH.exists()
        else None
    )
    return {"pool": meta, "roles": state}


__all__ = [
    "LINEUPS_PATH",
    "PLAYER_ROLES_PATH",
    "PLAYER_SEASON_PATH",
    "POOL_META_PATH",
    "ROLES_STATE_PATH",
    "ingest_pool",
    "ingest_roles",
    "scouting_status",
    "season_year",
]
