"""Build the public match record: one document and one page per played fixture."""

from __future__ import annotations

from typing import Any, Literal

import polars as pl
from pydantic import BaseModel, ConfigDict

from fitba.analytics.summary import build_summary
from fitba.ingest.history import (
    HISTORY_DIR,
    load_history_appearances,
    load_history_fixtures,
    load_history_player_match_stats,
    load_history_team_stats,
)
from fitba.ingest.match_extras import load_events, load_lineups
from fitba.normalize.fixture_registry import FixtureRecord, build_fixture_registry
from fitba.settings import MARTS_DIR, fixtures_policy
from fitba.util.dates import utc_now_iso

SCHEMA_VERSION = "1.0.0"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class SummaryBullet(StrictModel):
    text: str
    basis: str


class SummaryReconciliation(StrictModel):
    event_goals: int
    event_score: dict[str, int]
    final_score: dict[str, int]
    matched: bool


class SummaryBlock(StrictModel):
    headline: str
    basis: str
    bullets: list[SummaryBullet]
    reconciliation: SummaryReconciliation | None = None
    note: str


class StatsRow(StrictModel):
    key: str
    label: str
    home: Any = None
    away: Any = None
    source: str
    basis: str


class StatsBlock(StrictModel):
    home: dict[str, Any]
    away: dict[str, Any]
    rows: list[StatsRow]
    coverage: dict[str, str]


class XgSide(StrictModel):
    value: float | None = None
    low: float | None = None
    high: float | None = None
    provider: float | None = None


class XgBlock(StrictModel):
    available: bool
    home: XgSide | None = None
    away: XgSide | None = None
    model_id: str | None = None
    note: str | None = None


class TimelineRow(StrictModel):
    minute: int | None = None
    extra_minute: int | None = None
    team_name: str | None = None
    player_name: str | None = None
    assist_name: str | None = None
    event_type: str | None = None
    detail: str | None = None
    comments: str | None = None
    is_goal: bool
    is_own_goal: bool
    is_penalty: bool
    is_shootout: bool
    is_red_card: bool
    is_second_yellow: bool
    is_var: bool
    score_after: dict[str, int]


class LineupPlayer(StrictModel):
    player_id: int | None = None
    player_name: str | None = None
    shirt_number: int | None = None
    position: str | None = None
    role: str | None = None
    minutes: int | None = None
    grid: str | None = None
    on_minute: int | None = None


class LineupBlock(StrictModel):
    team_id: str
    team_name: str
    formation: str | None = None
    coach_name: str | None = None
    starters: list[LineupPlayer]
    substitutes: list[LineupPlayer]


class PlayerStat(StrictModel):
    player_id: int | None = None
    player_name: str | None = None
    team_id: int | None = None
    rating: float | None = None
    minutes: int | None = None
    goals: int | None = None
    assists: int | None = None
    shots_total: int | None = None
    shots_on: int | None = None
    passes_total: int | None = None
    pass_accuracy: int | None = None
    tackles: int | None = None
    duels_won: int | None = None
    yellow_cards: int | None = None
    red_cards: int | None = None


class FormRow(StrictModel):
    fixture_id: int
    date: str
    opponent_name: str
    venue: str
    goals_for: int | None = None
    goals_against: int | None = None
    href: str


class FormBlock(StrictModel):
    before: list[FormRow]
    after: list[FormRow]


class CoverageBlock(StrictModel):
    events: bool
    lineups: bool
    team_stats: bool
    player_stats: bool
    xg: bool
    depth: str
    note: str


class SourceRef(StrictModel):
    id: str
    name: str
    layer: str
    note: str


class FixtureInfo(StrictModel):
    fixture_id: int
    season: str
    date: str
    competition_id: str
    competition_name: str
    round: str | None = None
    status: str
    venue: str
    venue_name: str | None = None
    referee: str | None = None
    home_team_id: str
    home_team_name: str
    away_team_id: str
    away_team_name: str
    home_goals: int | None = None
    away_goals: int | None = None
    home_ht_goals: int | None = None
    away_ht_goals: int | None = None
    home_penalties: int | None = None
    away_penalties: int | None = None
    extra_time: bool | None = None
    result: str
    aberdeen_result: str
    href: str


class FixtureDocument(StrictModel):
    schema_version: str
    generated_at: str
    fixture: FixtureInfo
    depth: Literal["full", "result", "score"]
    summary: SummaryBlock
    stats: StatsBlock
    xg: XgBlock
    timeline: list[TimelineRow]
    lineups: dict[str, LineupBlock | None]
    player_stats: list[PlayerStat]
    form: FormBlock
    coverage: CoverageBlock
    sources: list[SourceRef]
    links: dict[str, str | None]


def fixture_page_schema() -> dict[str, Any]:
    return FixtureDocument.model_json_schema()


SOURCES = [
    {
        "id": "api_football",
        "name": "API-Football",
        "layer": "match_events_and_lineups",
        "note": "Events, lineups, formations, player match stats and cup/European team stats.",
    },
    {
        "id": "football_data_uk",
        "name": "football-data.co.uk",
        "layer": "league_match_stats",
        "note": "League shots, shots on target, corners, fouls, cards and provider xG.",
    },
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
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_season_data() -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    if not HISTORY_DIR.exists():
        return output
    for path in sorted(HISTORY_DIR.glob("season=*")):
        if not path.is_dir():
            continue
        season = path.name.split("=", 1)[1]
        output[season] = {
            "fixtures": load_history_fixtures(season),
            "events": load_events(season),
            "lineups": load_lineups(season),
            "appearances": load_history_appearances(season),
            "player_stats": load_history_player_match_stats(season),
            "team_stats": load_history_team_stats(season),
        }
    return output


def _team_stats(
    fixture: FixtureRecord,
    *,
    league_stats: pl.DataFrame,
    api_stats: pl.DataFrame,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    home: dict[str, Any] = {}
    away: dict[str, Any] = {}
    source: dict[str, str] = {}
    fields = (
        "shots",
        "shots_on_target",
        "shots_off",
        "shots_blocked",
        "shots_insidebox",
        "shots_outsidebox",
        "possession",
        "passes",
        "pass_accuracy",
        "passes_pct",
        "corners",
        "fouls",
        "offsides",
        "yellow_cards",
        "red_cards",
        "saves",
        "xg",
        "expected_goals",
        "goals_prevented",
    )
    if fixture.match_id and league_stats.height:
        rows = league_stats.filter(pl.col("match_id") == fixture.match_id).to_dicts()
        for row in rows:
            side = "home" if row.get("team_id") == fixture.home_team_id else "away"
            target = home if side == "home" else away
            for key in fields:
                if key in row:
                    target[key] = row.get(key)
                    source[key] = "football_data_uk"
    if api_stats.height:
        rows = api_stats.filter(pl.col("fixture_id") == fixture.fixture_id).to_dicts()
        for row in rows:
            side = (
                "home"
                if str(row.get("team_name") or "").casefold()
                == str(fixture.home_team_name).casefold()
                else "away"
            )
            target = home if side == "home" else away
            for key in fields:
                if key in row and row.get(key) is not None:
                    target[key] = row.get(key)
                    source[key] = "api_football"
    if "xg" in home and "expected_goals" not in home:
        home["expected_goals"] = home["xg"]
        source["expected_goals"] = source.get("xg", "football_data_uk")
    if "xg" in away and "expected_goals" not in away:
        away["expected_goals"] = away["xg"]
        source["expected_goals"] = source.get("xg", "football_data_uk")
    return home, away, source


def _stat_rows(
    home: dict[str, Any], away: dict[str, Any], source: dict[str, str]
) -> list[dict[str, Any]]:
    labels = {
        "possession": "Possession",
        "shots": "Shots",
        "shots_on_target": "Shots on target",
        "shots_off": "Shots off target",
        "shots_blocked": "Blocked shots",
        "shots_insidebox": "Shots inside box",
        "shots_outsidebox": "Shots outside box",
        "passes": "Passes",
        "pass_accuracy": "Passes accurate",
        "passes_pct": "Pass accuracy",
        "corners": "Corners",
        "fouls": "Fouls",
        "offsides": "Offsides",
        "yellow_cards": "Yellow cards",
        "red_cards": "Red cards",
        "saves": "Saves",
        "expected_goals": "Provider xG",
        "goals_prevented": "Goals prevented",
    }
    rows: list[dict[str, Any]] = []
    for key, label in labels.items():
        home_value = home.get(key)
        away_value = away.get(key)
        if home_value is None and away_value is None:
            continue
        rows.append(
            {
                "key": key,
                "label": label,
                "home": home_value,
                "away": away_value,
                "source": source.get(key, "unknown"),
                "basis": "measured",
            }
        )
    return rows


def _timeline(events: pl.DataFrame, fixture: FixtureRecord) -> list[dict[str, Any]]:
    if not events.height:
        return []
    home_goals = 0
    away_goals = 0
    output: list[dict[str, Any]] = []
    for row in events.sort(["minute", "extra_minute"], nulls_last=True).to_dicts():
        raw_team = str(row.get("team_name") or "")
        if raw_team.casefold() == str(fixture.home_team_name).casefold():
            event_team = fixture.home_team_name
        elif raw_team.casefold() == str(fixture.away_team_name).casefold():
            event_team = fixture.away_team_name
        else:
            event_team = raw_team or None
        if row.get("is_goal") and not row.get("is_shootout"):
            side = "home" if event_team == fixture.home_team_name else "away"
            if row.get("is_own_goal"):
                side = "away" if side == "home" else "home"
            if side == "home":
                home_goals += 1
            else:
                away_goals += 1
        output.append(
            {
                "minute": row.get("minute"),
                "extra_minute": row.get("extra_minute"),
                "team_name": event_team,
                "player_name": row.get("player_name"),
                "assist_name": row.get("assist_name"),
                "event_type": row.get("event_type"),
                "detail": row.get("detail"),
                "comments": row.get("comments"),
                "is_goal": bool(row.get("is_goal")),
                "is_own_goal": bool(row.get("is_own_goal")),
                "is_penalty": bool(row.get("is_penalty")),
                "is_shootout": bool(row.get("is_shootout")),
                "is_red_card": bool(row.get("is_red_card")),
                "is_second_yellow": bool(row.get("is_second_yellow")),
                "is_var": bool(row.get("is_var")),
                "score_after": {"home": home_goals, "away": away_goals},
            }
        )
    return output


def _lineup_block(
    fixture: FixtureRecord,
    side: str,
    *,
    lineups: pl.DataFrame,
    appearances: pl.DataFrame,
) -> dict[str, Any] | None:
    team_name = fixture.home_team_name if side == "home" else fixture.away_team_name
    line_rows = (
        lineups.filter(pl.col("fixture_id") == fixture.fixture_id).to_dicts()
        if lineups.height
        else []
    )
    team_key = str(team_name).casefold()
    line = next(
        (
            row
            for row in line_rows
            if str(row.get("team_name") or "").casefold() == team_key
        ),
        None,
    )
    if line is None:
        return None
    people = (
        appearances.filter(pl.col("fixture_id") == fixture.fixture_id).to_dicts()
        if appearances.height
        else []
    )
    players = [
        row for row in people if str(row.get("team_name") or "").casefold() == team_key
    ]
    starters = [
        {
            "player_id": row.get("player_id"),
            "player_name": row.get("player_name"),
            "shirt_number": row.get("shirt_number"),
            "position": row.get("position"),
            "role": row.get("role_code"),
            "minutes": row.get("minutes"),
            "grid": row.get("grid"),
        }
        for row in players
        if row.get("started")
    ]
    substitutes = [
        {
            "player_id": row.get("player_id"),
            "player_name": row.get("player_name"),
            "shirt_number": row.get("shirt_number"),
            "position": row.get("position"),
            "minutes": row.get("minutes"),
            "on_minute": row.get("on_minute"),
        }
        for row in players
        if not row.get("started")
    ]
    return {
        "team_id": fixture.home_team_id if side == "home" else fixture.away_team_id,
        "team_name": team_name,
        "formation": line.get("formation"),
        "coach_name": line.get("coach_name"),
        "starters": starters,
        "substitutes": substitutes,
    }


def _player_stats_block(
    fixture: FixtureRecord, player_stats: pl.DataFrame
) -> list[dict[str, Any]]:
    if not player_stats.height:
        return []
    rows = player_stats.filter(pl.col("fixture_id") == fixture.fixture_id).to_dicts()
    return [
        {
            "player_id": row.get("player_id"),
            "player_name": row.get("player_name"),
            "team_id": row.get("team_id"),
            "rating": row.get("rating"),
            "minutes": row.get("minutes"),
            "goals": row.get("goals"),
            "assists": row.get("assists"),
            "shots_total": row.get("shots_total"),
            "shots_on": row.get("shots_on"),
            "passes_total": row.get("passes_total"),
            "pass_accuracy": row.get("pass_accuracy"),
            "tackles": row.get("tackles"),
            "duels_won": row.get("duels_won"),
            "yellow_cards": row.get("yellow_cards"),
            "red_cards": row.get("red_cards"),
        }
        for row in rows
    ]


def _form_context(
    registry: Any, fixture: FixtureRecord
) -> dict[str, Any]:
    played = [
        item
        for item in registry.played()
        if item.competition_id == fixture.competition_id and item.season == fixture.season
    ]
    index = next((i for i, item in enumerate(played) if item.key == fixture.key), None)
    if index is None:
        return {"before": [], "after": []}

    def item_payload(item: FixtureRecord) -> dict[str, Any]:
        return {
            "fixture_id": item.fixture_id,
            "date": item.date,
            "opponent_name": item.opponent_name,
            "venue": item.venue,
            "goals_for": item.home_goals if item.is_aberdeen_home else item.away_goals,
            "goals_against": item.away_goals if item.is_aberdeen_home else item.home_goals,
            "href": item.href,
        }

    return {
        "before": [item_payload(item) for item in played[max(0, index - 5) : index]],
        "after": [item_payload(item) for item in played[index + 1 : index + 6]],
    }


def _xg_block(fixture: FixtureRecord, xg_row: dict[str, Any] | None) -> dict[str, Any]:
    if not xg_row:
        return {"available": False}
    if fixture.is_aberdeen_home:
        home = {
            "value": xg_row.get("fxg_for"),
            "low": xg_row.get("fxg_for_low"),
            "high": xg_row.get("fxg_for_high"),
            "provider": xg_row.get("provider_xg_for"),
        }
        away = {
            "value": xg_row.get("fxg_against"),
            "low": xg_row.get("fxg_against_low"),
            "high": xg_row.get("fxg_against_high"),
            "provider": xg_row.get("provider_xg_against"),
        }
    else:
        home = {
            "value": xg_row.get("fxg_against"),
            "low": xg_row.get("fxg_against_low"),
            "high": xg_row.get("fxg_against_high"),
            "provider": xg_row.get("provider_xg_against"),
        }
        away = {
            "value": xg_row.get("fxg_for"),
            "low": xg_row.get("fxg_for_low"),
            "high": xg_row.get("fxg_for_high"),
            "provider": xg_row.get("provider_xg_for"),
        }
    return {
        "available": home["value"] is not None and away["value"] is not None,
        "home": home,
        "away": away,
        "model_id": xg_row.get("model_id"),
        "note": "fxG is fitba's shot-on-target model; provider xG is shown separately.",
    }


def _depth(available: dict[str, bool]) -> str:
    if available.get("events") and available.get("lineups") and available.get("team_stats"):
        if available.get("player_stats"):
            return "full"
        return "result"
    if available.get("events") and available.get("lineups"):
        return "result"
    return "score"


def build_fixture_payloads(
    *,
    generated_at: str | None = None,
    xg_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = fixtures_policy()
    page_config = config.get("pages") or {}
    summary_config = page_config.get("summary") or {}
    registry = build_fixture_registry()
    season_data = _load_season_data()
    league_stats_path = MARTS_DIR / "team_match_stats.parquet"
    league_stats = (
        pl.read_parquet(league_stats_path) if league_stats_path.exists() else pl.DataFrame()
    )
    xg_by_fixture = {
        int(item["fixture_id"]): item
        for item in (xg_payload or {}).get("matches") or []
        if item.get("fixture_id") is not None
    }
    documents: dict[int, dict[str, Any]] = {}
    index_rows: list[dict[str, Any]] = []
    for fixture in registry.played():
        if fixture.fixture_id is None:
            continue
        season = season_data.get(fixture.season) or {}
        events = season.get("events")
        lineups = season.get("lineups")
        appearances = season.get("appearances")
        player_stats = season.get("player_stats")
        api_stats = season.get("team_stats")
        events_frame = (
            events.filter(pl.col("fixture_id") == fixture.fixture_id)
            if events is not None and events.height
            else pl.DataFrame()
        )
        home_stats, away_stats, stat_source = _team_stats(
            fixture,
            league_stats=league_stats,
            api_stats=api_stats if api_stats is not None else pl.DataFrame(),
        )
        stats_available = bool(home_stats or away_stats)
        home_xg = _xg_block(fixture, xg_by_fixture.get(fixture.fixture_id))
        summary_stats = None
        if stats_available:
            summary_stats = {
                "home": {
                    "shots": home_stats.get("shots"),
                    "shots_on_target": home_stats.get("shots_on_target"),
                    "possession": home_stats.get("possession") or home_stats.get("passes_pct"),
                },
                "away": {
                    "shots": away_stats.get("shots"),
                    "shots_on_target": away_stats.get("shots_on_target"),
                    "possession": away_stats.get("possession") or away_stats.get("passes_pct"),
                },
            }
        summary_xg = None
        if home_xg.get("available"):
            summary_xg = {
                "home": home_xg["home"]["value"],
                "home_low": home_xg["home"]["low"],
                "home_high": home_xg["home"]["high"],
                "away": home_xg["away"]["value"],
                "away_low": home_xg["away"]["low"],
                "away_high": home_xg["away"]["high"],
            }
        fixture_payload = {
            "home_team_name": fixture.home_team_name,
            "away_team_name": fixture.away_team_name,
            "home_goals": fixture.home_goals,
            "away_goals": fixture.away_goals,
        }
        summary = build_summary(
            fixture=fixture_payload,
            events=events_frame.to_dicts() if events_frame.height else [],
            stats=summary_stats,
            xg=summary_xg,
            late_goal_minute=int(summary_config.get("late_goal_minute") or 85),
        )
        home_lineup = _lineup_block(
            fixture,
            "home",
            lineups=lineups if lineups is not None else pl.DataFrame(),
            appearances=appearances if appearances is not None else pl.DataFrame(),
        )
        away_lineup = _lineup_block(
            fixture,
            "away",
            lineups=lineups if lineups is not None else pl.DataFrame(),
            appearances=appearances if appearances is not None else pl.DataFrame(),
        )
        player_rows = _player_stats_block(
            fixture, player_stats if player_stats is not None else pl.DataFrame()
        )
        available = {
            "events": bool(events_frame.height),
            "lineups": home_lineup is not None and away_lineup is not None,
            "team_stats": stats_available,
            "player_stats": bool(player_rows),
            "xg": bool(home_xg.get("available")),
        }
        depth = _depth(available)
        result = (
            "W"
            if (fixture.home_goals or 0) > (fixture.away_goals or 0)
            else "L"
            if (fixture.home_goals or 0) < (fixture.away_goals or 0)
            else "D"
        )
        aberdeen_goals = fixture.home_goals if fixture.is_aberdeen_home else fixture.away_goals
        opponent_goals = fixture.away_goals if fixture.is_aberdeen_home else fixture.home_goals
        aberdeen_result = (
            "W"
            if (aberdeen_goals or 0) > (opponent_goals or 0)
            else "L"
            if (aberdeen_goals or 0) < (opponent_goals or 0)
            else "D"
        )
        document = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at or utc_now_iso(),
            "fixture": {
                "fixture_id": fixture.fixture_id,
                "season": fixture.season,
                "date": fixture.date,
                "competition_id": fixture.competition_id,
                "competition_name": fixture.competition_name,
                "round": fixture.round,
                "status": fixture.status,
                "venue": fixture.venue,
                "venue_name": fixture.venue_name,
                "referee": fixture.referee,
                "home_team_id": fixture.home_team_id,
                "home_team_name": fixture.home_team_name,
                "away_team_id": fixture.away_team_id,
                "away_team_name": fixture.away_team_name,
                "home_goals": fixture.home_goals,
                "away_goals": fixture.away_goals,
                "home_ht_goals": fixture.home_ht_goals,
                "away_ht_goals": fixture.away_ht_goals,
                "home_penalties": fixture.home_penalties,
                "away_penalties": fixture.away_penalties,
                "extra_time": fixture.extra_time,
                "result": result,
                "aberdeen_result": aberdeen_result,
                "href": fixture.href,
            },
            "depth": depth,
            "summary": summary,
            "stats": {
                "home": home_stats,
                "away": away_stats,
                "rows": _stat_rows(home_stats, away_stats, stat_source),
                "coverage": {
                    "shots": "available" if stats_available else "unavailable",
                    "possession": "available"
                    if home_stats.get("possession") is not None
                    else "unavailable",
                },
            },
            "xg": home_xg,
            "timeline": _timeline(events_frame, fixture),
            "lineups": {"home": home_lineup, "away": away_lineup},
            "player_stats": player_rows,
            "form": _form_context(registry, fixture),
            "coverage": {
                **available,
                "depth": depth,
                "note": "Missing classes are unavailable, not zero.",
            },
            "sources": SOURCES,
            "links": {
                "season": f"/history/{fixture.season}/",
                "competition": "/competitions/",
                "matches": "/matches/",
                "previous": None,
                "next": None,
            },
        }
        documents[fixture.fixture_id] = document
        index_rows.append(
            {
                "fixture_id": fixture.fixture_id,
                "season": fixture.season,
                "date": fixture.date,
                "competition_id": fixture.competition_id,
                "competition_name": fixture.competition_name,
                "home_team_name": fixture.home_team_name,
                "away_team_name": fixture.away_team_name,
                "home_goals": fixture.home_goals,
                "away_goals": fixture.away_goals,
                "result": result,
                "aberdeen_result": aberdeen_result,
                "depth": depth,
                "href": fixture.href,
            }
        )
    for index, row in enumerate(index_rows):
        if index > 0:
            documents[row["fixture_id"]]["links"]["previous"] = index_rows[index - 1]["href"]
        if index + 1 < len(index_rows):
            documents[row["fixture_id"]]["links"]["next"] = index_rows[index + 1]["href"]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at or utc_now_iso(),
        "count": len(index_rows),
        "fixtures": index_rows,
        "documents": documents,
    }


__all__ = ["build_fixture_payloads"]
