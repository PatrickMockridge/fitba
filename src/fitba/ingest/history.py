"""Historical lineup, roster and team-statistics backfill.

This is an on-demand, bounded, resumable local ingest. The daily publish never
imports this module; it reads the normalized parquet and degrades to explicit
coverage states. Raw API payloads stay in the gitignored cache.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import polars as pl

from fitba.ingest.match_data import (
    APPEARANCE_COLUMNS,
    PLAYER_MATCH_COLUMNS,
    TEAM_SHAPE_COLUMNS,
    compute_match_data,
)
from fitba.ingest.match_extras import (
    EVENT_COLUMNS,
    LINEUP_COLUMNS,
    load_events,
    load_lineups,
    normalize_events,
    normalize_lineups,
)
from fitba.ingest.team_stats import TEAM_STAT_FIELDS, parse_team_stats
from fitba.settings import NORMALIZED_DIR, ensure_dirs, history_policy
from fitba.settings import roles as roles_config
from fitba.sources import api_football
from fitba.util.dates import season_start_year, utc_now_iso

HISTORY_DIR = NORMALIZED_DIR / "history"
STATE_PATH = HISTORY_DIR / "backfill_state.parquet"
META_PATH = HISTORY_DIR / "backfill_meta.json"

STAGES = ("fixtures", "lineups", "events", "rosters", "players", "team_stats")
DEFAULT_STAGES = ("fixtures", "lineups", "events", "rosters")
PLAYED_STATUSES = {"FT", "AET", "PEN"}
TTL_HOURS = float((history_policy().get("backfill") or {}).get("cache_ttl_hours") or 168)

STATE_COLUMNS = [
    "season",
    "stage",
    "fixture_id",
    "status",
    "attempts",
    "last_error",
    "checked_at",
]

FIXTURE_COLUMNS = [
    "fixture_id",
    "season",
    "date",
    "status",
    "competition_id",
    "competition_name",
    "round",
    "home_team_id",
    "home_team_name",
    "away_team_id",
    "away_team_name",
    "home_goals",
    "away_goals",
    "home_ht_goals",
    "away_ht_goals",
    "home_penalties",
    "away_penalties",
    "extra_time",
    "venue",
    "referee",
    "is_home",
    "is_away",
]

ROSTER_COLUMNS = [
    "season",
    "player_id",
    "player_name",
    "age",
    "birth_date",
    "nationality",
    "position",
]

TEAM_STAT_COLUMNS = ["season", *TEAM_STAT_FIELDS]


def _season_dir(season: str) -> Path:
    return HISTORY_DIR / f"season={season}"


def _write_frame(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = (
        pl.DataFrame(rows, infer_schema_length=None).select(columns)
        if rows
        else pl.DataFrame({column: [] for column in columns})
    )
    frame.write_parquet(path)


def _read_frame(path: Path, columns: list[str]) -> pl.DataFrame:
    if not path.exists():
        return pl.DataFrame({column: [] for column in columns})
    frame = pl.read_parquet(path)
    return frame.select([column for column in columns if column in frame.columns])


def load_state() -> pl.DataFrame:
    return _read_frame(STATE_PATH, STATE_COLUMNS)


def _state_map() -> dict[tuple[str, str, int], dict[str, Any]]:
    frame = load_state()
    return {
        (str(row["season"]), str(row["stage"]), int(row["fixture_id"])): row
        for row in frame.to_dicts()
    }


def _write_state(state: dict[tuple[str, str, int], dict[str, Any]]) -> None:
    rows = [state[key] for key in sorted(state, key=lambda item: (item[0], item[1], item[2]))]
    _write_frame(STATE_PATH, rows, STATE_COLUMNS)


def _set_state(
    state: dict[tuple[str, str, int], dict[str, Any]],
    *,
    season: str,
    stage: str,
    fixture_id: int,
    status: str,
    error: str | None = None,
) -> None:
    key = (season, stage, fixture_id)
    previous = state.get(key) or {}
    state[key] = {
        "season": season,
        "stage": stage,
        "fixture_id": fixture_id,
        "status": status,
        "attempts": int(previous.get("attempts") or 0) + 1,
        "last_error": error,
        "checked_at": utc_now_iso(),
    }
    _write_state(state)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "unknown"


def competition_id(league: dict[str, Any]) -> str:
    league_id = int(league.get("id") or 0)
    name = str(league.get("name") or "")
    if league_id == 179:
        return "sco:premiership"
    if league_id == 185:
        return "sco:league-cup"
    if league_id == 181:
        return "sco:scottish-cup"
    if "europa league" in name.casefold():
        return "uefa:europa-league"
    if "conference league" in name.casefold():
        return "uefa:conference-league"
    return f"sco:other:{_slug(name)}"


def _fixture_rows(
    payload: list[dict[str, Any]], *, season: str, team_id: int
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in payload:
        fixture = item.get("fixture") or {}
        teams = item.get("teams") or {}
        goals = item.get("goals") or {}
        score = item.get("score") or {}
        league = item.get("league") or {}
        fixture_id = fixture.get("id")
        if fixture_id is None:
            continue
        home = teams.get("home") or {}
        away = teams.get("away") or {}
        halftime = score.get("halftime") or {}
        extratime = score.get("extratime") or {}
        penalty = score.get("penalty") or {}
        venue = fixture.get("venue") or {}
        rows.append(
            {
                "fixture_id": int(fixture_id),
                "season": season,
                "date": str(fixture.get("date") or ""),
                "status": str((fixture.get("status") or {}).get("short") or ""),
                "competition_id": competition_id(league),
                "competition_name": str(league.get("name") or "Unknown competition"),
                "round": str(league.get("round") or ""),
                "home_team_id": home.get("id"),
                "home_team_name": home.get("name"),
                "away_team_id": away.get("id"),
                "away_team_name": away.get("name"),
                "home_goals": goals.get("home"),
                "away_goals": goals.get("away"),
                "home_ht_goals": halftime.get("home"),
                "away_ht_goals": halftime.get("away"),
                "home_penalties": penalty.get("home"),
                "away_penalties": penalty.get("away"),
                "extra_time": bool(extratime.get("home") is not None),
                "venue": str(venue.get("name") or "") or None,
                "referee": str(fixture.get("referee") or "") or None,
                "is_home": home.get("id") == team_id,
                "is_away": away.get("id") == team_id,
            }
        )
    return rows


def _ingest_fixtures(
    season: str,
    *,
    team_id: int,
    state: dict[tuple[str, str, int], dict[str, Any]],
    force: bool,
) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    payload = api_football.team_fixtures(
        team_id,
        season=season_start_year(season),
        ttl_hours=TTL_HOURS,
        force=force,
    )
    rows = _fixture_rows(payload, season=season, team_id=team_id)
    _write_frame(_season_dir(season) / "fixtures.parquet", rows, FIXTURE_COLUMNS)
    _set_state(
        state,
        season=season,
        stage="fixtures",
        fixture_id=0,
        status="complete" if rows else "unavailable",
    )
    return rows, {int(item["fixture"]["id"]): item for item in payload if item.get("fixture")}


def _roster_rows(payload: list[dict[str, Any]], season: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in payload:
        player = item.get("player") or {}
        if player.get("id") is None:
            continue
        statistics = item.get("statistics") or []
        position = None
        if statistics:
            position = (statistics[0].get("games") or {}).get("position")
        birth = player.get("birth") or {}
        age = player.get("age")
        rows.append(
            {
                "season": season,
                "player_id": int(player["id"]),
                "player_name": str(player.get("name") or ""),
                "age": int(age) if age is not None else None,
                "birth_date": str(birth.get("date") or "") or None,
                "nationality": str(player.get("nationality") or "") or None,
                "position": str(position) if position is not None else None,
            }
        )
    return rows


def _parse_team_stats(
    season: str, fixture_id: int, payload: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    return [
        {"season": season, **row}
        for row in parse_team_stats(payload, fixture_id=fixture_id)
    ]


def probe_season(season: str, *, team_id: int | None = None) -> dict[str, Any]:
    """Report provider availability for one season without writing history data."""
    policy = history_policy()
    club_id = "sco:aberdeen"
    from fitba.settings import source_ids

    team = int(team_id or source_ids()["teams"][club_id]["api_football"])
    payload = api_football.team_fixtures(
        team, season=season_start_year(season), ttl_hours=TTL_HOURS
    )
    rows = _fixture_rows(payload, season=season, team_id=team)
    played = [row for row in rows if row["status"] in PLAYED_STATUSES]
    probe = {
        "season": season,
        "fixtures": len(rows),
        "played": len(played),
        "competitions": sorted({row["competition_id"] for row in rows}),
    }
    if played:
        fixture_id = played[0]["fixture_id"]
        lineups = api_football.fixtures_lineups(fixture_id, ttl_hours=TTL_HOURS)
        events = api_football.fixtures_events(fixture_id)
        players = api_football.fixtures_players(fixture_id)
        stats = api_football.fixtures_statistics(fixture_id, ttl_hours=TTL_HOURS)
        probe["probe_fixture"] = fixture_id
        probe["lineups"] = len(lineups)
        probe["events"] = len(events)
        probe["player_teams"] = len(players)
        probe["stat_teams"] = len(stats)
    roster = api_football.players_by_team(
        team, season=season_start_year(season), max_pages=3, ttl_hours=TTL_HOURS
    )
    probe["roster"] = len(roster)
    probe["min_lineup_coverage"] = (policy.get("backfill") or {}).get("min_lineup_coverage")
    return probe


def ingest_history_season(
    season: str,
    *,
    team_id: int,
    stages: tuple[str, ...] = DEFAULT_STAGES,
    max_requests: int = 200,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Fetch a bounded slice of one season and write normalized history parquet."""
    ensure_dirs()
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    state = _state_map()
    start_requests = api_football.network_requests()
    fixtures, raw_by_id = _ingest_fixtures(season, team_id=team_id, state=state, force=force)
    played = [row for row in fixtures if row["status"] in PLAYED_STATUSES]
    report: dict[str, Any] = {
        "season": season,
        "fixtures": len(fixtures),
        "played": len(played),
        "stages": list(stages),
        "dry_run": dry_run,
        "requests": 0,
    }
    if dry_run:
        report["requests"] = api_football.network_requests() - start_requests
        return report

    contexts: list[dict[str, Any]] = []
    team_stats: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    lineup_rows: list[dict[str, Any]] = []
    stop = False
    for fixture in played:
        fixture_id = int(fixture["fixture_id"])
        raw_fixture = raw_by_id.get(fixture_id)
        if raw_fixture is None:
            continue
        context = {"fixture": raw_fixture, "lineups": [], "events": [], "players": []}
        for stage in ("lineups", "events", "players", "team_stats"):
            if stage not in stages and stage in ("players", "team_stats"):
                continue
            if api_football.network_requests() - start_requests >= max_requests:
                stop = True
                break
            key = (season, stage, fixture_id)
            previous = state.get(key) or {}
            if previous.get("status") == "complete" and not force:
                # Rebuild from cache for compute_match_data.
                if stage == "lineups":
                    context["lineups"] = api_football.fixtures_lineups(
                        fixture_id, ttl_hours=TTL_HOURS
                    )
                elif stage == "events":
                    context["events"] = api_football.fixtures_events(fixture_id)
                elif stage == "players":
                    context["players"] = api_football.fixtures_players(fixture_id)
                continue
            try:
                if stage == "lineups":
                    context["lineups"] = api_football.fixtures_lineups(
                        fixture_id, ttl_hours=TTL_HOURS, force=force
                    )
                    status = "complete" if context["lineups"] else "unavailable"
                elif stage == "events":
                    context["events"] = api_football.fixtures_events(fixture_id, force=force)
                    status = "complete"
                elif stage == "players":
                    context["players"] = api_football.fixtures_players(fixture_id, force=force)
                    status = "complete" if context["players"] else "unavailable"
                else:
                    stats = api_football.fixtures_statistics(
                        fixture_id, ttl_hours=TTL_HOURS, force=force
                    )
                    team_stats.extend(_parse_team_stats(season, fixture_id, stats))
                    status = "complete" if stats else "unavailable"
                _set_state(
                    state,
                    season=season,
                    stage=stage,
                    fixture_id=fixture_id,
                    status=status,
                )
            except Exception as exc:  # noqa: BLE001 - local ingest reports the error
                _set_state(
                    state,
                    season=season,
                    stage=stage,
                    fixture_id=fixture_id,
                    status="error",
                    error=f"{type(exc).__name__}: {exc}",
                )
        if context.get("events"):
            event_rows.extend(
                normalize_events(
                    context["events"],
                    fixture_id=fixture_id,
                    season=season,
                    ingested_at=utc_now_iso(),
                )
            )
        if context.get("lineups"):
            lineup_rows.extend(
                normalize_lineups(
                    context["lineups"],
                    fixture_id=fixture_id,
                    season=season,
                    ingested_at=utc_now_iso(),
                )
            )
            contexts.append(context)
        if stop:
            break

    if "rosters" in stages:
        try:
            roster = api_football.players_by_team(
                team_id,
                season=season_start_year(season),
                max_pages=3,
                ttl_hours=TTL_HOURS,
                force=force,
            )
            roster_rows = _roster_rows(roster, season)
            _write_frame(_season_dir(season) / "rosters.parquet", roster_rows, ROSTER_COLUMNS)
            _set_state(
                state,
                season=season,
                stage="rosters",
                fixture_id=0,
                status="complete" if roster_rows else "unavailable",
            )
        except Exception as exc:  # noqa: BLE001
            _set_state(
                state,
                season=season,
                stage="rosters",
                fixture_id=0,
                status="error",
                error=f"{type(exc).__name__}: {exc}",
            )

    if event_rows:
        _write_frame(
            _season_dir(season) / "events.parquet",
            event_rows,
            EVENT_COLUMNS,
        )
    if lineup_rows:
        _write_frame(
            _season_dir(season) / "lineups.parquet",
            lineup_rows,
            LINEUP_COLUMNS,
        )
    if contexts:
        data = compute_match_data(
            contexts,
            focus_team_id=team_id,
            season_year=season_start_year(season),
            ingested_at=utc_now_iso(),
            config=roles_config(),
        )
        # compute_match_data stores the provider season year (2019); the history
        # layer uses the canonical season string (2019-20).
        for key in ("appearances", "match_stats", "team_shapes"):
            for row in data.get(key) or []:
                row["season"] = season
        _write_frame(
            _season_dir(season) / "appearances.parquet",
            data["appearances"],
            APPEARANCE_COLUMNS,
        )
        _write_frame(
            _season_dir(season) / "player_match_stats.parquet",
            data["match_stats"],
            PLAYER_MATCH_COLUMNS,
        )
        _write_frame(
            _season_dir(season) / "team_shapes.parquet",
            data["team_shapes"],
            TEAM_SHAPE_COLUMNS,
        )
    if team_stats:
        _write_frame(
            _season_dir(season) / "team_match_stats.parquet",
            team_stats,
            TEAM_STAT_COLUMNS,
        )

    meta = {
        "season": season,
        "fixtures": len(fixtures),
        "played": len(played),
        "fixtures_with_lineups": len(contexts),
        "fixtures_with_events": len({row["fixture_id"] for row in event_rows}),
        "fixtures_with_players": sum(1 for context in contexts if context.get("players")),
        "fixtures_with_team_stats": len({row["fixture_id"] for row in team_stats}),
        "stages": list(stages),
        "requests": api_football.network_requests() - start_requests,
        "stopped_at_budget": stop,
        "checked_at": utc_now_iso(),
    }
    (_season_dir(season) / "meta.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    report.update(meta)
    _write_global_meta()
    return report


def _write_global_meta() -> None:
    seasons = sorted(
        path.name.split("=", 1)[1] for path in HISTORY_DIR.glob("season=*") if path.is_dir()
    )
    payload = {
        "seasons": seasons,
        "updated_at": utc_now_iso(),
        "state": load_state().to_dicts() if load_state().height else [],
    }
    META_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_history_fixtures(season: str) -> pl.DataFrame:
    return _read_frame(_season_dir(season) / "fixtures.parquet", FIXTURE_COLUMNS)


def load_history_appearances(season: str) -> pl.DataFrame:
    return _read_frame(_season_dir(season) / "appearances.parquet", APPEARANCE_COLUMNS)


def load_history_rosters(season: str) -> pl.DataFrame:
    return _read_frame(_season_dir(season) / "rosters.parquet", ROSTER_COLUMNS)


def load_history_team_stats(season: str) -> pl.DataFrame:
    return _read_frame(_season_dir(season) / "team_match_stats.parquet", TEAM_STAT_COLUMNS)


def load_history_player_match_stats(season: str) -> pl.DataFrame:
    return _read_frame(_season_dir(season) / "player_match_stats.parquet", PLAYER_MATCH_COLUMNS)


def history_coverage(season: str) -> dict[str, Any]:
    fixtures = load_history_fixtures(season)
    appearances = load_history_appearances(season)
    rosters = load_history_rosters(season)
    stats = load_history_team_stats(season)
    events = load_events(season)
    lineups = load_lineups(season)
    player_stats = load_history_player_match_stats(season)
    if not fixtures.height:
        return {
            "status": "unavailable",
            "fixtures_total": 0,
            "fixtures_with_lineups": 0,
            "fixtures_with_events": 0,
            "fixtures_with_player_stats": 0,
            "fixtures_with_team_stats": 0,
            "lineup_coverage": None,
            "rosters": 0,
            "team_stats": 0,
            "events": 0,
            "player_stats": 0,
            "note": "Historical backfill has not run for this season.",
        }
    played = fixtures.filter(pl.col("status").is_in(list(PLAYED_STATUSES)))
    with_lineups = appearances.select("fixture_id").unique().height if appearances.height else 0
    with_events = events.select("fixture_id").unique().height if events.height else 0
    with_player_stats = (
        player_stats.select("fixture_id").unique().height if player_stats.height else 0
    )
    with_team_stats = stats.select("fixture_id").unique().height if stats.height else 0
    total = played.height
    return {
        "status": (
            "available"
            if total and with_lineups == total
            else "partial"
            if with_lineups
            else "unavailable"
        ),
        "fixtures_total": total,
        "fixtures_with_lineups": with_lineups,
        "fixtures_with_events": with_events,
        "fixtures_with_player_stats": with_player_stats,
        "fixtures_with_team_stats": with_team_stats,
        "lineup_coverage": round(with_lineups / total, 3) if total else None,
        "rosters": rosters.height,
        "team_stats": stats.height,
        "events": events.height,
        "player_stats": player_stats.height,
        "lineups": lineups.height,
        "note": (
            "Historical lineups, events and statistics are a bounded local "
            "backfill; missing data is shown as unavailable."
        ),
    }


def load_all_history() -> dict[str, Any]:
    """Load every season's normalized history for publication."""
    seasons: dict[str, Any] = {}
    if not HISTORY_DIR.exists():
        return {"seasons": seasons}
    for path in sorted(HISTORY_DIR.glob("season=*")):
        if not path.is_dir():
            continue
        season = path.name.split("=", 1)[1]
        seasons[season] = {
            "fixtures": load_history_fixtures(season),
            "appearances": load_history_appearances(season),
            "events": load_events(season),
            "lineups": load_lineups(season),
            "player_match_stats": load_history_player_match_stats(season),
            "rosters": load_history_rosters(season),
            "team_stats": load_history_team_stats(season),
            "coverage": history_coverage(season),
        }
    return {"seasons": seasons}


__all__ = [
    "DEFAULT_STAGES",
    "HISTORY_DIR",
    "STAGES",
    "competition_id",
    "history_coverage",
    "ingest_history_season",
    "load_all_history",
    "load_history_appearances",
    "load_history_fixtures",
    "load_history_player_match_stats",
    "load_history_rosters",
    "load_history_team_stats",
    "load_state",
    "probe_season",
]
