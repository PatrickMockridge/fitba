"""Match-level appearances, roles, playing time and team shapes.

One pass over the current-season fixtures produces:

- an appearance row for every player on both teams, with the role derived from
  the starting-XI grid and the minutes split into started/on-as-substitute;
- per-match provider ratings and key stats;
- per-team kick-off shape rows;
- player-season role and playing-time aggregates.

Only the starting XI has a formation grid. A substitute gets playing time but no
role. A missing grid, an unmapped formation or an invalid slot yields an explicit
unknown rather than a guessed role.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

import polars as pl

from fitba.ingest.position_stats import (
    POSITION_COLUMNS,
    _match_length,
    appearance_intervals,
    compute_position_stats,
    fixture_contexts,
)
from fitba.normalize.roles import (
    formation_family,
    primary_role,
    role_family,
    role_for_grid,
    shape_counts,
    shape_from_formation,
    shape_from_grid,
    shape_key,
)
from fitba.settings import NORMALIZED_DIR, ensure_dirs
from fitba.settings import roles as roles_config
from fitba.sources.base import IngestResult
from fitba.util.dates import utc_now_iso

APPEARANCE_COLUMNS = [
    "player_id",
    "player_key",
    "player_name",
    "shirt_number",
    "position",
    "team_id",
    "team_name",
    "fixture_id",
    "competition",
    "season",
    "date",
    "opponent",
    "started",
    "on_minute",
    "off_minute",
    "minutes",
    "minutes_started",
    "minutes_as_sub",
    "role_code",
    "role_family",
    "role_status",
    "formation",
    "formation_shape",
    "shape_family",
    "cb_count",
    "wing_back_count",
    "dm_count",
    "forward_count",
    "grid",
    "role_source",
    "ingested_at",
]

PLAYER_MATCH_COLUMNS = [
    "player_id",
    "player_key",
    "player_name",
    "shirt_number",
    "position",
    "captain",
    "team_id",
    "fixture_id",
    "competition",
    "season",
    "date",
    "rating",
    "minutes",
    "substitute",
    "goals",
    "assists",
    "conceded",
    "saves",
    "shots_total",
    "shots_on",
    "passes_total",
    "pass_accuracy",
    "dribbles_attempts",
    "dribbles_success",
    "fouls_drawn",
    "fouls_committed",
    "penalty_won",
    "penalty_committed",
    "penalty_scored",
    "penalty_missed",
    "penalty_saved",
    "offsides",
    "tackles",
    "blocks",
    "interceptions",
    "duels_won",
    "passes_key",
    "yellow_cards",
    "red_cards",
    "ingested_at",
]

ROLE_COLUMNS = [
    "player_id",
    "player_key",
    "team_id",
    "season",
    "role_code",
    "role_family",
    "starts",
    "minutes",
    "ingested_at",
]

PLAYING_TIME_COLUMNS = [
    "player_id",
    "player_key",
    "team_id",
    "season",
    "competition",
    "starts",
    "sub_apps",
    "minutes",
    "minutes_started",
    "minutes_as_sub",
    "ingested_at",
]

TEAM_SHAPE_COLUMNS = [
    "team_id",
    "team_name",
    "fixture_id",
    "competition",
    "season",
    "date",
    "opponent",
    "formation",
    "formation_shape",
    "shape_family",
    "cb_count",
    "wing_back_count",
    "dm_count",
    "forward_count",
    "goals_for",
    "goals_against",
    "result",
    "saves",
    "ingested_at",
]


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace("%", ""))
    except (TypeError, ValueError):
        return None


def _rating(value: Any) -> float | None:
    rating = _float(value)
    return rating if rating and rating > 0 else None


def _fixture_teams(fixture: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    teams = fixture.get("teams") or {}
    return teams.get("home") or {}, teams.get("away") or {}


def _goals(fixture: dict[str, Any]) -> tuple[int | None, int | None]:
    goals = fixture.get("goals") or {}
    return _int(goals.get("home")), _int(goals.get("away"))


def _scores(fixture: dict[str, Any], team_id: int) -> tuple[int | None, int | None, str | None]:
    home_goals, away_goals = _goals(fixture)
    home, away = _fixture_teams(fixture)
    if (home.get("id") == team_id and home_goals is None) or (
        away.get("id") == team_id and away_goals is None
    ):
        return None, None, None
    is_home = home.get("id") == team_id
    goals_for = home_goals if is_home else away_goals
    goals_against = away_goals if is_home else home_goals
    if goals_for is None or goals_against is None:
        return None, None, None
    result = "W" if goals_for > goals_against else "D" if goals_for == goals_against else "L"
    return goals_for, goals_against, result


def _opponent(fixture: dict[str, Any], team_id: int) -> str:
    home, away = _fixture_teams(fixture)
    other = away if home.get("id") == team_id else home
    return str(other.get("name") or "Unknown opponent")


def _players_by_team(payload: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    output: dict[int, list[dict[str, Any]]] = {}
    for block in payload or []:
        team_id = (block.get("team") or {}).get("id")
        if team_id is None:
            continue
        output[int(team_id)] = block.get("players") or []
    return output


def _player_stats(entry: dict[str, Any]) -> dict[str, Any]:
    player = entry.get("player") or {}
    statistics = entry.get("statistics") or []
    stats = statistics[0] if statistics else {}
    games = stats.get("games") or {}
    goals = stats.get("goals") or {}
    cards = stats.get("cards") or {}
    tackles = stats.get("tackles") or {}
    duels = stats.get("duels") or {}
    passes = stats.get("passes") or {}
    shots = stats.get("shots") or {}
    dribbles = stats.get("dribbles") or {}
    fouls = stats.get("fouls") or {}
    penalty = stats.get("penalty") or {}
    direct_red = _int(cards.get("red"))
    second_yellow = _int(cards.get("yellowred"))
    red_cards = (
        None
        if direct_red is None and second_yellow is None
        else (direct_red or 0) + (second_yellow or 0)
    )
    return {
        "player_name": str(player.get("name") or "") or None,
        "shirt_number": _int(games.get("number")),
        "position": str(games.get("position") or "") or None,
        "captain": bool(games.get("captain")),
        "rating": _rating(games.get("rating")),
        "minutes": _int(games.get("minutes")),
        "substitute": bool(games.get("substitute")),
        "goals": _int(goals.get("total")),
        "assists": _int(goals.get("assists")),
        "conceded": _int(goals.get("conceded")),
        "saves": _int(goals.get("saves")),
        "shots_total": _int(shots.get("total")),
        "shots_on": _int(shots.get("on")),
        "passes_total": _int(passes.get("total")),
        "pass_accuracy": _int(passes.get("accuracy")),
        "dribbles_attempts": _int(dribbles.get("attempts")),
        "dribbles_success": _int(dribbles.get("success")),
        "fouls_drawn": _int(fouls.get("drawn")),
        "fouls_committed": _int(fouls.get("committed")),
        "penalty_won": _int(penalty.get("won")),
        "penalty_committed": _int(penalty.get("commited")),
        "penalty_scored": _int(penalty.get("scored")),
        "penalty_missed": _int(penalty.get("missed")),
        "penalty_saved": _int(penalty.get("saved")),
        "offsides": _int(stats.get("offsides")),
        "tackles": _int(tackles.get("total")),
        "blocks": _int(tackles.get("blocks")),
        "interceptions": _int(tackles.get("interceptions")),
        "duels_won": _int(duels.get("won")),
        "passes_key": _int(passes.get("key")),
        "yellow_cards": _int(cards.get("yellow")),
        "red_cards": red_cards,
    }


def _team_saves(players: list[dict[str, Any]]) -> int | None:
    values: list[int] = []
    for entry in players:
        saves = _int(_player_stats(entry).get("saves"))
        if saves is not None:
            values.append(saves)
    return sum(values) if values else None


def compute_match_data(
    contexts: list[dict[str, Any]],
    *,
    focus_team_id: int,
    season_year: int,
    ingested_at: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    role_config = config or roles_config()
    appearances: list[dict[str, Any]] = []
    match_stats: list[dict[str, Any]] = []
    team_shapes: list[dict[str, Any]] = []
    role_aggregates: dict[tuple[int, int, int, str], dict[str, Any]] = {}
    playing_aggregates: dict[tuple[int, int, int, str], dict[str, Any]] = {}

    fixtures_total = len(contexts)
    fixtures_with_lineups = 0
    fixtures_with_grid = 0
    fixtures_with_players = 0
    starts_total = 0
    starts_with_role = 0
    formations_seen: Counter[str] = Counter()
    unmapped_formations: set[str] = set()
    mismatches: list[dict[str, Any]] = []
    slot_errors: list[dict[str, Any]] = []

    for context in contexts:
        fixture = context.get("fixture") or {}
        fixture_id = (fixture.get("fixture") or {}).get("id")
        if fixture_id is None:
            continue
        fixture_id = int(fixture_id)
        lineups = context.get("lineups") or []
        events = context.get("events") or []
        players_payload = context.get("players") or []
        if not lineups:
            continue
        fixtures_with_lineups += 1
        if context.get("players_ok", True) and players_payload:
            fixtures_with_players += 1
        players_by_team = _players_by_team(players_payload)
        competition = str((fixture.get("league") or {}).get("name") or "Unknown competition")
        date = str((fixture.get("fixture") or {}).get("date") or "")
        season = _int((fixture.get("league") or {}).get("season")) or season_year
        match_length = _match_length(fixture)

        for lineup in lineups:
            team = lineup.get("team") or {}
            team_id = _int(team.get("id"))
            if team_id is None:
                continue
            team_name = str(team.get("name") or "Unknown team")
            starters = lineup.get("startXI") or []
            grid_shape = shape_from_grid(
                [(entry.get("player") or {}).get("grid") for entry in starters]
            )
            formation_shape = shape_from_formation(lineup.get("formation"))
            if grid_shape and formation_shape and grid_shape != formation_shape:
                mismatches.append(
                    {
                        "fixture_id": fixture_id,
                        "team_id": team_id,
                        "formation": lineup.get("formation"),
                        "grid_shape": shape_key(grid_shape),
                        "formation_shape": shape_key(formation_shape),
                    }
                )
            shape = grid_shape or formation_shape
            key = shape_key(shape)
            mapped = bool(key and key in (role_config.get("formations") or {}))
            if team_id == focus_team_id and grid_shape:
                fixtures_with_grid += 1
            if team_id == focus_team_id:
                formations_seen[key or "unknown"] += 1
                if key and not mapped:
                    unmapped_formations.add(key)

            counts = (
                shape_counts(role_config, key)
                if mapped
                else {
                    "cb_count": None,
                    "wing_back_count": None,
                    "dm_count": None,
                    "forward_count": None,
                }
            )
            intervals = appearance_intervals(
                lineup,
                events,
                team_id=team_id,
                match_length=match_length,
            )
            start_entries: dict[int, dict[str, Any]] = {}
            lineup_entries: dict[int, dict[str, Any]] = {}
            starter_ids = {
                _int((entry.get("player") or {}).get("id")) for entry in starters
            }
            for entry in [*starters, *(lineup.get("substitutes") or [])]:
                player = entry.get("player") or {}
                player_id = _int(player.get("id"))
                if player_id is None:
                    continue
                lineup_entry = {
                    "name": str(player.get("name") or "") or None,
                    "number": _int(player.get("number")),
                    "pos": player.get("pos"),
                    "grid": player.get("grid"),
                }
                lineup_entries[player_id] = lineup_entry
                if player_id in starter_ids:
                    start_entries[player_id] = {
                        "grid": player.get("grid"),
                        "pos": player.get("pos"),
                    }

            for player_id, (on_minute, off_minute, started) in intervals.items():
                minutes = max(0, off_minute - on_minute)
                if minutes < 0:
                    continue
                role_code = None
                role_source = None
                role_status = "unknown"
                grid = None
                if started:
                    entry = start_entries.get(player_id) or {}
                    grid = entry.get("grid")
                    if grid and mapped:
                        role_code = role_for_grid(role_config, key, grid)
                        if role_code:
                            role_source = "starting_xi_grid"
                            role_status = "observed"
                        else:
                            slot_errors.append(
                                {
                                    "fixture_id": fixture_id,
                                    "team_id": team_id,
                                    "player_id": player_id,
                                    "grid": grid,
                                    "shape": key,
                                }
                            )
                    elif entry.get("pos") == "G":
                        role_code = "GK"
                        role_source = "lineup_position"
                        role_status = "observed"
                family = role_family(role_config, role_code)
                if team_id == focus_team_id and started:
                    starts_total += 1
                    if role_code:
                        starts_with_role += 1

                lineup_entry = lineup_entries.get(player_id) or {}
                appearances.append(
                    {
                        "player_id": player_id,
                        "player_key": f"api:player:{player_id}",
                        "player_name": lineup_entry.get("name"),
                        "shirt_number": lineup_entry.get("number"),
                        "position": lineup_entry.get("pos"),
                        "team_id": team_id,
                        "team_name": team_name,
                        "fixture_id": fixture_id,
                        "competition": competition,
                        "season": season,
                        "date": date,
                        "opponent": _opponent(fixture, team_id),
                        "started": started,
                        "on_minute": on_minute,
                        "off_minute": off_minute,
                        "minutes": minutes,
                        "minutes_started": minutes if started else 0,
                        "minutes_as_sub": 0 if started else minutes,
                        "role_code": role_code,
                        "role_family": family,
                        "role_status": role_status,
                        "formation": lineup.get("formation"),
                        "formation_shape": key,
                        "shape_family": formation_family(shape),
                        "cb_count": counts["cb_count"],
                        "wing_back_count": counts["wing_back_count"],
                        "dm_count": counts["dm_count"],
                        "forward_count": counts["forward_count"],
                        "grid": grid,
                        "role_source": role_source,
                        "ingested_at": ingested_at,
                    }
                )

                if started and role_code:
                    role_key = (player_id, team_id, season, role_code)
                    role_row = role_aggregates.setdefault(
                        role_key,
                        {
                            "player_id": player_id,
                            "player_key": f"api:player:{player_id}",
                            "team_id": team_id,
                            "season": season,
                            "role_code": role_code,
                            "role_family": family,
                            "starts": 0,
                            "minutes": 0,
                            "ingested_at": ingested_at,
                        },
                    )
                    role_row["starts"] += 1
                    role_row["minutes"] += minutes

                playing_key = (player_id, team_id, season, competition)
                playing_row = playing_aggregates.setdefault(
                    playing_key,
                    {
                        "player_id": player_id,
                        "player_key": f"api:player:{player_id}",
                        "team_id": team_id,
                        "season": season,
                        "competition": competition,
                        "starts": 0,
                        "sub_apps": 0,
                        "minutes": 0,
                        "minutes_started": 0,
                        "minutes_as_sub": 0,
                        "ingested_at": ingested_at,
                    },
                )
                if started:
                    playing_row["starts"] += 1
                    playing_row["minutes_started"] += minutes
                else:
                    playing_row["sub_apps"] += 1
                    playing_row["minutes_as_sub"] += minutes
                playing_row["minutes"] += minutes

            goals_for, goals_against, result = _scores(fixture, team_id)
            team_shapes.append(
                {
                    "team_id": team_id,
                    "team_name": team_name,
                    "fixture_id": fixture_id,
                    "competition": competition,
                    "season": season,
                    "date": date,
                    "opponent": _opponent(fixture, team_id),
                    "formation": lineup.get("formation"),
                    "formation_shape": key,
                    "shape_family": formation_family(shape),
                    "cb_count": counts["cb_count"],
                    "wing_back_count": counts["wing_back_count"],
                    "dm_count": counts["dm_count"],
                    "forward_count": counts["forward_count"],
                    "goals_for": goals_for,
                    "goals_against": goals_against,
                    "result": result,
                    "saves": _team_saves(players_by_team.get(team_id, [])),
                    "ingested_at": ingested_at,
                }
            )

            for entry in players_by_team.get(team_id, []):
                player = entry.get("player") or {}
                player_id = _int(player.get("id"))
                if player_id is None:
                    continue
                stats = _player_stats(entry)
                match_stats.append(
                    {
                        "player_id": player_id,
                        "player_key": f"api:player:{player_id}",
                        "team_id": team_id,
                        "fixture_id": fixture_id,
                        "competition": competition,
                        "season": season,
                        "date": date,
                        **stats,
                        "ingested_at": ingested_at,
                    }
                )

    roles = list(role_aggregates.values())
    playing = list(playing_aggregates.values())
    role_players = {row["player_id"] for row in roles if int(row["team_id"]) == focus_team_id}
    starts_players = {
        row["player_id"]
        for row in appearances
        if row["team_id"] == focus_team_id and row["started"]
    }
    meta = {
        "fixtures_total": fixtures_total,
        "fixtures_with_lineups": fixtures_with_lineups,
        "fixtures_with_grid": fixtures_with_grid,
        "fixtures_with_players": fixtures_with_players,
        "starts_total": starts_total,
        "starts_with_role": starts_with_role,
        "players_with_starts": len(starts_players),
        "players_with_role": len(role_players),
        "formations_seen": dict(sorted(formations_seen.items())),
        "unmapped_formations": sorted(unmapped_formations),
        "formation_mismatches": mismatches,
        "slot_errors": slot_errors,
        "coverage": (
            "available"
            if fixtures_total
            and fixtures_with_lineups == fixtures_total
            and fixtures_with_grid == fixtures_total
            else "partial"
            if fixtures_with_lineups
            else "unavailable"
        ),
        "role_coverage": (
            "available"
            if starts_total and starts_with_role == starts_total
            else "partial"
            if starts_with_role
            else "unavailable"
        ),
        "note": (
            "Roles are derived from the starting-XI formation grid. "
            "Starts without a grid, unmapped formations and invalid slots are "
            "unknown, not inferred. Substitute appearances carry playing time "
            "but no role."
        ),
        "ingested_at": ingested_at,
    }
    return {
        "appearances": appearances,
        "match_stats": match_stats,
        "team_shapes": team_shapes,
        "roles": roles,
        "playing_time": playing,
        "meta": meta,
    }


def _frame(rows: list[dict[str, Any]], columns: list[str]) -> pl.DataFrame:
    return (
        pl.DataFrame(rows).select(columns)
        if rows
        else pl.DataFrame({column: [] for column in columns})
    )


def ingest_match_data(
    *,
    team_id: int,
    squad_ids: set[int],
    season_year: int,
    force: bool = False,
) -> IngestResult:
    ensure_dirs()
    try:
        contexts, errors = fixture_contexts(
            team_id=team_id,
            season_year=season_year,
            force=force,
        )
        now = utc_now_iso()
        position_rows, position_meta = compute_position_stats(
            contexts,
            team_id=team_id,
            squad_ids=squad_ids,
            ingested_at=now,
        )
        position_dir = NORMALIZED_DIR / "squad"
        position_dir.mkdir(parents=True, exist_ok=True)
        position_frame = _frame(position_rows, POSITION_COLUMNS)
        position_frame.write_parquet(position_dir / "aberdeen_position_stats.parquet")
        (position_dir / "position_stats_meta.json").write_text(
            json.dumps(position_meta, indent=2, default=str) + "\n",
            encoding="utf-8",
        )

        data = compute_match_data(
            contexts,
            focus_team_id=team_id,
            season_year=season_year,
            ingested_at=now,
        )
        output_dir = NORMALIZED_DIR / "matches"
        output_dir.mkdir(parents=True, exist_ok=True)
        _frame(data["appearances"], APPEARANCE_COLUMNS).write_parquet(
            output_dir / "player_appearances.parquet"
        )
        _frame(data["match_stats"], PLAYER_MATCH_COLUMNS).write_parquet(
            output_dir / "player_match_stats.parquet"
        )
        _frame(data["team_shapes"], TEAM_SHAPE_COLUMNS).write_parquet(
            output_dir / "team_shapes.parquet"
        )
        _frame(data["roles"], ROLE_COLUMNS).write_parquet(output_dir / "player_roles.parquet")
        _frame(data["playing_time"], PLAYING_TIME_COLUMNS).write_parquet(
            output_dir / "playing_time.parquet"
        )
        (output_dir / "match_roles_meta.json").write_text(
            json.dumps(data["meta"], indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        return IngestResult(
            source="api_football",
            status="ok",
            rows=len(data["appearances"]),
            path=str(output_dir / "player_appearances.parquet"),
            errors=errors or None,
            details={
                "position_stats": {
                    "fixtures_total": position_meta["fixtures_total"],
                    "fixtures_covered": position_meta["fixtures_covered"],
                    "coverage": position_meta["coverage"],
                    "rows": position_frame.height,
                },
                "match_data": data["meta"],
                "appearances": len(data["appearances"]),
                "match_stats": len(data["match_stats"]),
                "team_shapes": len(data["team_shapes"]),
            },
        )
    except Exception as exc:  # noqa: BLE001 - reported by the CLI
        return IngestResult(source="api_football", status="error", errors=[str(exc)])


def _load_frame(name: str, columns: list[str]) -> pl.DataFrame:
    path = NORMALIZED_DIR / "matches" / name
    if not path.exists():
        return pl.DataFrame({column: [] for column in columns})
    return pl.read_parquet(path)


def load_player_appearances() -> pl.DataFrame:
    return _load_frame("player_appearances.parquet", APPEARANCE_COLUMNS)


def load_player_match_stats() -> pl.DataFrame:
    return _load_frame("player_match_stats.parquet", PLAYER_MATCH_COLUMNS)


def load_team_shapes() -> pl.DataFrame:
    return _load_frame("team_shapes.parquet", TEAM_SHAPE_COLUMNS)


def load_player_roles() -> pl.DataFrame:
    return _load_frame("player_roles.parquet", ROLE_COLUMNS)


def load_playing_time() -> pl.DataFrame:
    return _load_frame("playing_time.parquet", PLAYING_TIME_COLUMNS)


def load_match_meta() -> dict[str, Any]:
    path = NORMALIZED_DIR / "matches" / "match_roles_meta.json"
    if not path.exists():
        return {
            "fixtures_total": 0,
            "fixtures_with_lineups": 0,
            "fixtures_with_grid": 0,
            "fixtures_with_players": 0,
            "starts_total": 0,
            "starts_with_role": 0,
            "players_with_starts": 0,
            "players_with_role": 0,
            "formations_seen": {},
            "unmapped_formations": [],
            "formation_mismatches": [],
            "slot_errors": [],
            "coverage": "unavailable",
            "role_coverage": "unavailable",
            "note": "Match roles have not been ingested.",
            "ingested_at": None,
        }
    return json.loads(path.read_text(encoding="utf-8"))


def playing_time_for(
    rows: list[dict[str, Any]],
    *,
    player_id: int,
    team_id: int,
    season_year: int,
) -> dict[str, Any]:
    """Build one player's playing-time block from normalized rows."""
    relevant = [
        row
        for row in rows
        if int(row["player_id"]) == player_id
        and int(row["team_id"]) == team_id
        and int(row["season"]) == season_year
    ]
    if not relevant:
        return {
            "starts": 0,
            "sub_apps": 0,
            "minutes": 0,
            "minutes_started": 0,
            "minutes_as_sub": 0,
            "coverage": "no_matches",
            "by_competition": [],
        }
    by_competition = [
        {
            "competition": row["competition"],
            "starts": int(row.get("starts") or 0),
            "sub_apps": int(row.get("sub_apps") or 0),
            "minutes": int(row.get("minutes") or 0),
            "minutes_started": int(row.get("minutes_started") or 0),
            "minutes_as_sub": int(row.get("minutes_as_sub") or 0),
        }
        for row in sorted(relevant, key=lambda item: str(item["competition"]))
    ]
    return {
        "starts": sum(row["starts"] for row in by_competition),
        "sub_apps": sum(row["sub_apps"] for row in by_competition),
        "minutes": sum(row["minutes"] for row in by_competition),
        "minutes_started": sum(row["minutes_started"] for row in by_competition),
        "minutes_as_sub": sum(row["minutes_as_sub"] for row in by_competition),
        "coverage": "available",
        "by_competition": by_competition,
    }


def role_block_for(
    rows: list[dict[str, Any]],
    *,
    player_id: int,
    team_id: int,
    season_year: int,
    starts_total: int,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one player's role block from normalized role rows."""
    role_config = config or roles_config()
    relevant = [
        row
        for row in rows
        if int(row["player_id"]) == player_id
        and int(row["team_id"]) == team_id
        and int(row["season"]) == season_year
    ]
    labels = {
        code: str((role_config.get("roles") or {}).get(code, {}).get("label") or code)
        for code in {str(row["role_code"]) for row in relevant}
    }
    roles = [
        {
            "code": str(row["role_code"]),
            "label": labels.get(str(row["role_code"]), str(row["role_code"])),
            "family": row["role_family"],
            "starts": int(row.get("starts") or 0),
            "minutes": int(row.get("minutes") or 0),
        }
        for row in relevant
    ]
    roles.sort(
        key=lambda item: (
            -item["starts"],
            -item["minutes"],
            int(((role_config.get("roles") or {}).get(item["code"]) or {}).get("order") or 999),
        )
    )
    code, family = primary_role(roles, role_config)
    if code:
        roles.sort(
            key=lambda item: (
                item["code"] != code,
                -item["starts"],
                -item["minutes"],
                int(((role_config.get("roles") or {}).get(item["code"]) or {}).get("order") or 999),
            )
        )
    if not code:
        return {
            "primary": None,
            "code": None,
            "family": None,
            "side": None,
            "status": "unknown",
            "starts_with_role": 0,
            "starts_total": starts_total,
            "coverage": f"0/{starts_total}",
            "roles": [],
            "unknown_reason": "no_starting_xi_role" if starts_total == 0 else "no_grid",
            "source": None,
        }
    side = (role_config.get("roles") or {}).get(code, {}).get("side")
    starts_with_role = _sum_starts(roles)
    status = "observed" if starts_with_role >= starts_total else "partial"
    return {
        "primary": labels.get(code, code),
        "code": code,
        "family": family,
        "side": side,
        "status": status,
        "starts_with_role": starts_with_role,
        "starts_total": starts_total,
        "coverage": f"{starts_with_role}/{starts_total}",
        "roles": roles,
        "unknown_reason": None,
        "source": {"id": "api_football", "method": "starting_xi_grid"},
    }


def _sum_starts(roles: list[dict[str, Any]]) -> int:
    return sum(int(row.get("starts") or 0) for row in roles)


__all__ = [
    "APPEARANCE_COLUMNS",
    "PLAYER_MATCH_COLUMNS",
    "PLAYING_TIME_COLUMNS",
    "ROLE_COLUMNS",
    "TEAM_SHAPE_COLUMNS",
    "compute_match_data",
    "ingest_match_data",
    "load_match_meta",
    "load_player_appearances",
    "load_player_match_stats",
    "load_player_roles",
    "load_playing_time",
    "load_team_shapes",
    "playing_time_for",
    "role_block_for",
]
