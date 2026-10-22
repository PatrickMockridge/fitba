"""Position-specific match context from fixture lineups and events.

Player-season statistics give goals and assists but do not give an outfield
player's goals conceded, clean sheets or own goals. Those are reconstructed from
the current-season fixture lineups and events:

- goals conceded while the player was on the pitch;
- clean sheets (60+ minutes, zero conceded while on the pitch);
- own goals attributed to the player.

This is an event-reconstructed view, not tracking data. A fixture without both
lineups and events is excluded and the coverage is reported.
"""

from __future__ import annotations

import json
from typing import Any

import polars as pl

from fitba.normalize.competitions import canonical_from_league
from fitba.settings import (
    NORMALIZED_DIR,
    ensure_dirs,
)
from fitba.sources import api_football
from fitba.sources.base import IngestResult
from fitba.util.dates import utc_now_iso

LEAGUE_IDS = (179, 185, 181)  # Premiership, League Cup, Scottish Cup
PLAYED_STATUSES = {"FT", "AET", "PEN"}
RED_DETAILS = {"Red Card", "Second Yellow card"}

POSITION_COLUMNS = [
    "player_id",
    "player_key",
    "competition",
    "matches",
    "minutes_on_pitch",
    "conceded_on_pitch",
    "clean_sheets",
    "own_goals",
    "ingested_at",
]


def _event_minute(event: dict[str, Any]) -> int:
    time = event.get("time") or {}
    return int(time.get("elapsed") or 0)


def _match_length(fixture: dict[str, Any]) -> int:
    status = fixture.get("status") or {}
    if status.get("short") in {"AET", "PEN"} or int(status.get("elapsed") or 0) > 90:
        return 120
    return 90


def _team_lineup(lineups: list[dict[str, Any]], team_id: int) -> dict[str, Any] | None:
    for lineup in lineups:
        if (lineup.get("team") or {}).get("id") == team_id:
            return lineup
    return None


def appearance_intervals(
    lineup: dict[str, Any] | None,
    events: list[dict[str, Any]],
    *,
    team_id: int,
    match_length: int,
) -> dict[int, tuple[int, int, bool]]:
    """Return player_id -> (on_minute, off_minute, started) for one team."""
    if lineup is None:
        return {}
    intervals: dict[int, list[Any]] = {}
    for item in lineup.get("startXI", []) or []:
        player_id = (item.get("player") or {}).get("id")
        if player_id is not None:
            intervals[int(player_id)] = [0, match_length, True]

    ordered = sorted(
        events,
        key=lambda event: (
            _event_minute(event),
            (event.get("time") or {}).get("extra") or 0,
        ),
    )
    for event in ordered:
        if (event.get("team") or {}).get("id") != team_id:
            continue
        event_type = str(event.get("type") or "")
        detail = str(event.get("detail") or "")
        player_id = (event.get("player") or {}).get("id")
        assist_id = (event.get("assist") or {}).get("id")
        minute = _event_minute(event)
        if event_type == "subst":
            if player_id is not None and int(player_id) in intervals:
                intervals[int(player_id)][1] = minute
            if assist_id is not None:
                intervals[int(assist_id)] = [minute, match_length, False]
        elif event_type == "Card" and detail in RED_DETAILS:
            if player_id is not None and int(player_id) in intervals:
                intervals[int(player_id)][1] = minute

    return {
        player_id: (int(value[0]), int(value[1]), bool(value[2]))
        for player_id, value in intervals.items()
        if int(value[1]) >= int(value[0])
    }


def on_pitch_intervals(
    lineup: dict[str, Any] | None,
    events: list[dict[str, Any]],
    *,
    team_id: int,
    match_length: int,
) -> dict[int, tuple[int, int]]:
    """Return player_id -> (on_minute, off_minute) for one team in one match."""
    intervals = appearance_intervals(
        lineup,
        events,
        team_id=team_id,
        match_length=match_length,
    )
    return {player_id: (start, end) for player_id, (start, end, _started) in intervals.items()}


def goal_events(
    events: list[dict[str, Any]],
    *,
    team_id: int,
    squad_ids: set[int],
) -> tuple[list[int], dict[int, int]]:
    """Return (minutes Aberdeen conceded, own goals by Aberdeen players)."""
    conceded: list[int] = []
    own_goals: dict[int, int] = {}
    for event in events:
        if str(event.get("type") or "") != "Goal":
            continue
        detail = str(event.get("detail") or "")
        event_team = (event.get("team") or {}).get("id")
        player_id = (event.get("player") or {}).get("id")
        minute = _event_minute(event)
        if "own goal" in detail.casefold():
            if player_id is not None and int(player_id) in squad_ids:
                conceded.append(minute)
                own_goals[int(player_id)] = own_goals.get(int(player_id), 0) + 1
            continue
        if event_team != team_id:
            conceded.append(minute)
    return conceded, own_goals


def compute_position_stats(
    contexts: list[dict[str, Any]],
    *,
    team_id: int,
    squad_ids: set[int],
    ingested_at: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: dict[tuple[int, str], dict[str, Any]] = {}
    covered = 0
    missing: list[dict[str, Any]] = []

    for context in contexts:
        fixture = context.get("fixture") or {}
        lineups = context.get("lineups") or []
        events = context.get("events") or []
        league = fixture.get("league") or {}
        _competition_id, competition = canonical_from_league(league)
        lineup = _team_lineup(lineups, team_id)
        if lineup is None or not context.get("events_ok", True):
            missing.append(
                {
                    "fixture_id": (fixture.get("fixture") or {}).get("id"),
                    "competition": competition,
                    "date": (fixture.get("fixture") or {}).get("date"),
                }
            )
            continue
        covered += 1
        match_length = _match_length(fixture)
        intervals = on_pitch_intervals(
            lineup,
            events,
            team_id=team_id,
            match_length=match_length,
        )
        conceded_minutes, own_goals = goal_events(
            events,
            team_id=team_id,
            squad_ids=squad_ids,
        )
        team_conceded = len(conceded_minutes)

        for player_id, (start, end) in intervals.items():
            if player_id not in squad_ids:
                continue
            minutes = max(0, end - start)
            if minutes <= 0:
                continue
            if end == match_length:
                conceded = sum(1 for minute in conceded_minutes if start <= minute <= end)
            else:
                conceded = sum(1 for minute in conceded_minutes if start <= minute < end)
            key = (player_id, competition)
            row = rows.setdefault(
                key,
                {
                    "player_id": player_id,
                    "player_key": f"api:player:{player_id}",
                    "competition": competition,
                    "matches": 0,
                    "minutes_on_pitch": 0,
                    "conceded_on_pitch": 0,
                    "clean_sheets": 0,
                    "own_goals": 0,
                    "ingested_at": ingested_at,
                },
            )
            row["matches"] += 1
            row["minutes_on_pitch"] += minutes
            row["conceded_on_pitch"] += conceded
            if team_conceded == 0 and conceded == 0 and minutes >= 60:
                row["clean_sheets"] += 1
            row["own_goals"] += own_goals.get(player_id, 0)

    total = len(contexts)
    coverage = (
        "available" if total and covered == total else "partial" if covered else "unavailable"
    )
    note = (
        "On-pitch goals conceded, clean sheets (60+ minutes, zero conceded while "
        f"on the pitch) and own goals are computed from fixture lineups and events "
        f"for {covered} of {total} competitive matches; friendlies are excluded."
    )
    if missing:
        note += (
            " Fixtures without lineups or events are excluded and the coverage is marked partial."
        )
    meta = {
        "scope": "competitive",
        "fixtures_total": total,
        "fixtures_covered": covered,
        "coverage": coverage,
        "note": note,
        "missing_fixtures": missing,
        "ingested_at": ingested_at,
    }
    return list(rows.values()), meta


def fixture_contexts(
    *,
    team_id: int,
    season_year: int,
    force: bool,
) -> tuple[list[dict[str, Any]], list[str]]:
    contexts: list[dict[str, Any]] = []
    errors: list[str] = []
    for league_id in LEAGUE_IDS:
        try:
            fixtures = api_football.fixtures(
                league_id,
                season_year,
                team=team_id,
                force=force,
            )
        except Exception as exc:  # noqa: BLE001 - a league can be unavailable
            errors.append(f"league {league_id}: {exc}")
            continue
        for fixture in fixtures:
            status = (fixture.get("fixture") or {}).get("status") or {}
            if status.get("short") not in PLAYED_STATUSES:
                continue
            fixture_id = (fixture.get("fixture") or {}).get("id")
            if fixture_id is None:
                continue
            lineups_ok = True
            try:
                lineups = api_football.fixtures_lineups(int(fixture_id), force=force)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"lineups {fixture_id}: {exc}")
                lineups = []
                lineups_ok = False
            events_ok = True
            try:
                events = api_football.fixtures_events(int(fixture_id), force=force)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"events {fixture_id}: {exc}")
                events = []
                events_ok = False
            players_ok = True
            try:
                players = api_football.fixtures_players(int(fixture_id), force=force)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"players {fixture_id}: {exc}")
                players = []
                players_ok = False
            contexts.append(
                {
                    "fixture": fixture,
                    "lineups": lineups,
                    "events": events,
                    "players": players,
                    "lineups_ok": lineups_ok,
                    "events_ok": events_ok,
                    "players_ok": players_ok,
                }
            )
    return contexts, errors


def ingest_position_stats(
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
        rows, meta = compute_position_stats(
            contexts,
            team_id=team_id,
            squad_ids=squad_ids,
            ingested_at=now,
        )
        output_dir = NORMALIZED_DIR / "squad"
        output_dir.mkdir(parents=True, exist_ok=True)
        frame = (
            pl.DataFrame(rows).select(POSITION_COLUMNS)
            if rows
            else pl.DataFrame({column: [] for column in POSITION_COLUMNS})
        )
        frame.write_parquet(output_dir / "aberdeen_position_stats.parquet")
        (output_dir / "position_stats_meta.json").write_text(
            json.dumps(meta, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        return IngestResult(
            source="api_football",
            status="ok",
            rows=frame.height,
            path=str(output_dir / "aberdeen_position_stats.parquet"),
            errors=errors or None,
            details={
                "fixtures_total": meta["fixtures_total"],
                "fixtures_covered": meta["fixtures_covered"],
                "coverage": meta["coverage"],
                "rows": frame.height,
            },
        )
    except Exception as exc:  # noqa: BLE001 - reported by the CLI
        return IngestResult(source="api_football", status="error", errors=[str(exc)])


def load_position_stats() -> pl.DataFrame:
    path = NORMALIZED_DIR / "squad" / "aberdeen_position_stats.parquet"
    if not path.exists():
        return pl.DataFrame({column: [] for column in POSITION_COLUMNS})
    return pl.read_parquet(path)


def load_position_stats_meta() -> dict[str, Any]:
    path = NORMALIZED_DIR / "squad" / "position_stats_meta.json"
    if not path.exists():
        return {
            "fixtures_total": 0,
            "fixtures_covered": 0,
            "coverage": "unavailable",
            "note": "Position-specific match context has not been ingested.",
            "missing_fixtures": [],
            "ingested_at": None,
        }
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = [
    "POSITION_COLUMNS",
    "appearance_intervals",
    "compute_position_stats",
    "fixture_contexts",
    "goal_events",
    "ingest_position_stats",
    "load_position_stats",
    "load_position_stats_meta",
    "on_pitch_intervals",
]
