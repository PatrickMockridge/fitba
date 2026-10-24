"""Matchday payload builder.

The document owns the next fixture, both teams' form and style projections,
both predicted XIs and the matchup read. League tables, the Aberdeen season
summary and squad facts stay in their existing payloads and are joined by id
in the web build. A missing opponent snapshot degrades to explicit coverage
states; it never fabricates a lineup or a possession value.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal

import polars as pl
from pydantic import BaseModel, ConfigDict

from fitba.analytics.history import club_match_rows
from fitba.analytics.matchday import (
    form_block,
    league_match_rows,
    matchup_read,
    predict_lineup,
    strength_block,
    strength_comparison,
    style_block,
    style_lean,
)
from fitba.ingest.matchday import MATCHDAY_DIR, load_meta, next_fixture
from fitba.normalize.schedule import load_schedule
from fitba.settings import NORMALIZED_DIR, source_ids, source_registry
from fitba.settings import (
    aberdeen as aberdeen_config,
)
from fitba.settings import (
    competitions as competitions_config,
)
from fitba.settings import (
    matchday as matchday_policy,
)
from fitba.settings import (
    roles as roles_config,
)
from fitba.util.dates import season_start_year

SCHEMA_VERSION = "1.0.0"
ABERDEEN_API_ID = int(aberdeen_config()["api_football_id"])
STATE = Literal["fresh", "stale", "no_fixture", "unavailable"]
BASIS = Literal["measured", "inferred", "unknown"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceRef(StrictModel):
    id: str
    name: str
    url: str | None = None
    verified_at: str | None = None


class TeamRef(StrictModel):
    club_id: str
    api_team_id: int | None = None
    name: str
    short_name: str | None = None


class FixtureBlock(StrictModel):
    match_id: str
    competition_id: str
    competition_name: str
    stage: str | None = None
    season: str
    date: str
    kickoff: str | None = None
    home_team_id: str
    home_team_name: str
    away_team_id: str
    away_team_name: str
    venue: str
    opponent_id: str
    opponent_name: str
    status: str
    source_id: str | None = None


class FormMatch(StrictModel):
    match_id: str | None = None
    date: str
    opponent_id: str | None = None
    opponent_name: str | None = None
    venue: str | None = None
    gf: int
    ga: int
    result: str | None = None
    points: int
    competition_name: str | None = None


class FormBlock(StrictModel):
    basis: str
    sample: dict[str, Any]
    matches: list[FormMatch]
    form: str
    recent: dict[str, Any]
    form_points: int
    season_record: dict[str, Any]
    home: dict[str, Any]
    away: dict[str, Any]
    coverage: str
    note: str


class StyleBlock(StrictModel):
    matches: int
    coverage: str
    venue: str
    season: str | None = None
    shots_for_pm: float | None = None
    shots_against_pm: float | None = None
    shots_on_target_for_pm: float | None = None
    shots_on_target_against_pm: float | None = None
    corners_for_pm: float | None = None
    corners_against_pm: float | None = None
    fouls_for_pm: float | None = None
    fouls_against_pm: float | None = None
    yellow_for_pm: float | None = None
    yellow_against_pm: float | None = None
    red_for_pm: float | None = None
    red_against_pm: float | None = None
    goals_for_pm: float | None = None
    goals_against_pm: float | None = None
    shot_share: float | None = None
    conversion: float | None = None
    shot_accuracy: float | None = None
    goals_per_shot: float | None = None
    goals_per_shot_on_target: float | None = None
    percentiles: dict[str, float | None] = {}
    possession_for_pm: float | None = None
    possession_against_pm: float | None = None
    possession_unknown_reason: str | None = None
    recent_shot_shares: list[float] = []
    missing_stats: list[str] = []
    note: str | None = None
    reason: str | None = None


class LeanBlock(StrictModel):
    approach: str
    label: str
    confidence: str
    approach_index: float | None = None
    venue_index: float | None = None
    overall_index: float | None = None
    shot_share: float | None = None
    venue_matches: int = 0
    venue_used: bool = False
    evidence: list[str] = []
    basis: str
    interpretation: str
    missing_metrics: list[str] = []
    reason: str | None = None
    note: str | None = None


class StylePair(StrictModel):
    overall: StyleBlock
    venue: StyleBlock
    lean: LeanBlock


class StrengthTeam(StrictModel):
    status: str
    team_id: str
    team_name: str | None = None
    competition_id: str | None = None
    competition_name: str | None = None
    tier: int | None = None
    position: int | None = None
    played: int | None = None
    points: int | None = None
    ppg: float | None = None
    gf: int | None = None
    ga: int | None = None
    gd: int | None = None
    gf_pg: float | None = None
    ga_pg: float | None = None
    gd_pg: float | None = None
    form: str | None = None
    shots_for_pm: float | None = None
    shots_against_pm: float | None = None
    shot_share: float | None = None
    percentiles: dict[str, float | None] = {}
    ranks: dict[str, int | None] = {}
    league_size: int | None = None
    coverage: str | None = None
    sample_note: str | None = None
    reason: str | None = None


class LineupPlayer(StrictModel):
    player_id: int | None = None
    player_key: str | None = None
    name: str | None = None
    shirt_number: int | None = None
    href: str | None = None
    slot: str | None = None
    grid: str | None = None
    role_code: str | None = None
    role_label: str | None = None
    role_family: str | None = None
    role_fit: float | None = None
    score: float | None = None
    confidence: str = "unknown"
    starts: int | None = None
    minutes: int | None = None
    recency_start: float | None = None
    form: float | None = None
    recent_rating: float | None = None
    recent_rating_score: float | None = None
    rating_count: int | None = None
    rating_coverage: str | None = None
    last_seen: str | None = None
    reason: str | None = None
    position_group: str | None = None
    available: bool | None = None
    unavailable_reason: str | None = None
    status: str | None = None
    availability_status: str | None = None
    availability_confidence: str | None = None
    availability_source: str | None = None
    availability_source_url: str | None = None
    availability_verified_at: str | None = None
    availability_note: str | None = None
    availability_conflict: bool | None = None
    availability_downgrade: int | None = None


class LineupBlock(StrictModel):
    status: str
    reason: str | None = None
    basis: str | None = None
    team_id: int | str | None = None
    formation: str | None = None
    formation_confidence: str | None = None
    team_confidence: str | None = None
    filled: int = 0
    coverage: dict[str, Any] = {}
    selection: dict[str, Any] = {}
    disclaimer: str
    unavailable: list[dict[str, Any]] = []
    unknowns: list[str] = []
    availability: dict[str, Any] = {}
    selection_risks: list[dict[str, Any]] = []
    players: list[LineupPlayer] = []
    contenders: list[LineupPlayer] = []
    note: str | None = None
    assignment_note: str | None = None


class ReadBullet(StrictModel):
    text: str
    basis: BASIS


class ReadKey(StrictModel):
    label: str
    text: str
    basis: BASIS


class MatchupRead(StrictModel):
    headline: str
    bullets: list[ReadBullet]
    keys: list[ReadKey]
    basis: str
    note: str


class HeadToHead(StrictModel):
    date: str
    competition_name: str | None = None
    home_team_name: str
    away_team_name: str
    home_goals: int | None = None
    away_goals: int | None = None
    venue: str
    result: str | None = None


class MatchdayDocument(StrictModel):
    schema_version: str = SCHEMA_VERSION
    generated_at: str
    season: str
    state: STATE
    stale_reason: str | None = None
    served_generated_at: str | None = None
    fixture: FixtureBlock | None = None
    next_fixtures: list[FixtureBlock] = []
    teams: dict[str, TeamRef] = {}
    form_guide: dict[str, FormBlock] = {}
    head_to_head: list[HeadToHead] = []
    strength: dict[str, StrengthTeam] = {}
    strength_comparison: dict[str, Any] = {}
    styles: dict[str, StylePair] = {}
    predicted_lineups: dict[str, LineupBlock | None] = {}
    matchup_read: MatchupRead | None = None
    coverage: dict[str, Any] = {}
    sources: list[SourceRef] = []
    notes: str


def matchday_schema() -> dict[str, Any]:
    return MatchdayDocument.model_json_schema()


def _frame_or_none(path: Path) -> pl.DataFrame | None:
    if not path.exists():
        return None
    frame = pl.read_parquet(path)
    return frame if frame.height else None


def _read_snapshot(name: str, snapshot_dir: Path | None = None) -> pl.DataFrame | None:
    return _frame_or_none((snapshot_dir or MATCHDAY_DIR) / name)


def _fixture_from_snapshot(snapshot_dir: Path | None = None) -> dict[str, Any] | None:
    frame = _read_snapshot("upcoming.parquet", snapshot_dir)
    if frame is not None:
        return frame.to_dicts()[0]
    return next_fixture()


def _fixture_block(fixture: dict[str, Any]) -> FixtureBlock:
    return FixtureBlock(
        match_id=str(fixture.get("match_id") or ""),
        competition_id=str(fixture.get("competition_id") or ""),
        competition_name=str(fixture.get("competition_name") or ""),
        stage=fixture.get("stage"),
        season=str(fixture.get("season") or ""),
        date=str(fixture.get("date") or ""),
        kickoff=fixture.get("kickoff"),
        home_team_id=str(fixture.get("home_team_id") or ""),
        home_team_name=str(fixture.get("home_team_name") or ""),
        away_team_id=str(fixture.get("away_team_id") or ""),
        away_team_name=str(fixture.get("away_team_name") or ""),
        venue=str(fixture.get("venue") or ""),
        opponent_id=str(fixture.get("opponent_id") or ""),
        opponent_name=str(fixture.get("opponent_name") or ""),
        status=str(fixture.get("status") or ""),
        source_id=fixture.get("source_id"),
    )


def _team_competition(
    team_id: str,
    *,
    season: str,
    matches: pl.DataFrame,
    tables: dict[str, pl.DataFrame],
) -> tuple[str, dict[str, Any], pl.DataFrame, pl.DataFrame] | None:
    competitions = competitions_config().get("competitions", [])
    for competition in sorted(competitions, key=lambda item: int(item.get("tier") or 99)):
        table = tables.get(competition["id"])
        if table is None or not table.height:
            continue
        if not table.filter(pl.col("team_id") == team_id).height:
            continue
        team_ids = table["team_id"].to_list()
        league_rows = league_match_rows(
            matches,
            competition_id=competition["id"],
            season=season,
            team_ids=team_ids,
        )
        return competition["id"], competition, table, league_rows
    return None


def _team_ref(team_id: str, name: str) -> TeamRef:
    mapping = (source_ids().get("teams") or {}).get(team_id) or {}
    api_id = mapping.get("api_football") if isinstance(mapping, dict) else mapping
    return TeamRef(
        club_id=team_id,
        api_team_id=int(api_id) if api_id is not None else None,
        name=name,
        short_name=name,
    )


def _form_for(
    matches: pl.DataFrame,
    *,
    team_id: str,
    competition_id: str,
    competition_name: str,
    season: str,
) -> dict[str, Any]:
    subset = matches.filter(
        (pl.col("competition_id") == competition_id) & (pl.col("season") == season)
    )
    rows = club_match_rows(subset, team_id)
    return form_block(
        rows,
        n=5,
        competition_id=competition_id,
        competition_name=competition_name,
        season=season,
    )


def _styles_for(
    league_rows: pl.DataFrame,
    *,
    team_id: str,
    competition_id: str,
    season: str,
    venue: str,
) -> dict[str, Any]:
    policy = matchday_policy().get("style") or {}
    rows = league_rows.filter(pl.col("team_id") == team_id)
    overall = style_block(
        rows,
        season=season,
        competition_id=competition_id,
        league_rows=league_rows,
        team_id=team_id,
    )
    venue_profile = style_block(
        rows,
        venue=venue,
        season=season,
        competition_id=competition_id,
        league_rows=league_rows,
        team_id=team_id,
    )
    lean = style_lean(
        overall,
        venue_profile,
        policy=policy,
        venue_label="at home" if venue == "H" else "away",
    )
    return {"overall": overall, "venue": venue_profile, "lean": lean}


def _pick_player(player: dict[str, Any]) -> LineupPlayer:
    return LineupPlayer(
        player_id=player.get("player_id"),
        player_key=player.get("player_key"),
        name=player.get("name"),
        shirt_number=player.get("shirt_number"),
        href=player.get("href"),
        slot=player.get("slot"),
        grid=player.get("grid"),
        role_code=player.get("role_code"),
        role_label=player.get("role_label"),
        role_family=player.get("role_family"),
        role_fit=player.get("role_fit"),
        score=player.get("score"),
        confidence=str(player.get("confidence") or "unknown"),
        starts=player.get("starts"),
        minutes=player.get("minutes"),
        recency_start=player.get("recency_start"),
        form=player.get("form"),
        recent_rating=player.get("recent_rating"),
        recent_rating_score=player.get("recent_rating_score"),
        rating_count=player.get("rating_count"),
        rating_coverage=player.get("rating_coverage"),
        last_seen=player.get("last_seen"),
        reason=player.get("reason"),
        position_group=player.get("position_group"),
        available=player.get("available"),
        unavailable_reason=player.get("unavailable_reason"),
        status=player.get("status"),
        availability_status=player.get("availability_status"),
        availability_confidence=player.get("availability_confidence"),
        availability_source=player.get("availability_source"),
        availability_source_url=player.get("availability_source_url"),
        availability_verified_at=player.get("availability_verified_at"),
        availability_note=player.get("availability_note"),
        availability_conflict=player.get("availability_conflict"),
        availability_downgrade=player.get("availability_downgrade"),
    )


def _lineup_payload(block: dict[str, Any] | None, *, basis: str) -> LineupBlock | None:
    if block is None:
        return None
    return LineupBlock(
        status=str(block.get("status") or "unavailable"),
        reason=block.get("reason"),
        basis=basis,
        team_id=block.get("team_id"),
        formation=block.get("formation"),
        formation_confidence=block.get("formation_confidence"),
        team_confidence=block.get("team_confidence"),
        filled=int(block.get("filled") or 0),
        coverage=block.get("coverage") or {},
        selection=block.get("selection") or {},
        disclaimer=str(block.get("disclaimer") or ""),
        unavailable=block.get("unavailable") or [],
        unknowns=block.get("unknowns") or [],
        availability=block.get("availability") or {},
        selection_risks=block.get("selection_risks") or [],
        players=[_pick_player(player) for player in block.get("players") or []],
        contenders=[_pick_player(player) for player in block.get("contenders") or []],
        note=block.get("note"),
        assignment_note=block.get("assignment_note"),
    )


def _unavailable_lineup(reason: str, *, team_id: int | None = None) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "reason": reason,
        "team_id": team_id,
        "filled": 0,
        "coverage": {},
        "selection": {},
        "disclaimer": (
            "Predicted, not official team news. Based on recent starts, minutes, "
            "formation and position fit."
        ),
        "unavailable": [],
        "unknowns": ["No lineup sample is available in the local snapshot."],
        "availability": {},
        "selection_risks": [],
        "players": [],
        "contenders": [],
        "team_confidence": "unknown",
        "note": "No prediction is made without an observed lineup window.",
    }


def _aberdeen_appearances(
    season: str,
    *,
    squad_data: dict[str, Any],
) -> pl.DataFrame | None:
    path = NORMALIZED_DIR / "matches" / "player_appearances.parquet"
    if not path.exists():
        return None
    frame = pl.read_parquet(path)
    year = season_start_year(season)
    frame = frame.filter((pl.col("team_id") == ABERDEEN_API_ID) & (pl.col("season") == year))
    if not frame.height:
        return None
    stats_path = NORMALIZED_DIR / "matches" / "player_match_stats.parquet"
    stats: dict[tuple[int, int], dict[str, Any]] = {}
    if stats_path.exists():
        for row in pl.read_parquet(stats_path).to_dicts():
            stats[(int(row["fixture_id"]), int(row["player_id"]))] = row
    squad = {int(player["player_id"]): player for player in squad_data.get("players", [])}
    rows = []
    for row in frame.to_dicts():
        player = squad.get(int(row["player_id"]), {})
        match_stats = stats.get((int(row["fixture_id"]), int(row["player_id"])), {})
        row = {
            **row,
            "player_name": player.get("name"),
            "shirt_number": player.get("number"),
            "position": player.get("position_group") or player.get("position"),
            "goals": match_stats.get("goals") or 0,
            "assists": match_stats.get("assists") or 0,
            "rating": match_stats.get("rating"),
            "yellow_cards": match_stats.get("yellow_cards") or 0,
            "red_cards": match_stats.get("red_cards") or 0,
        }
        rows.append(row)
    return pl.DataFrame(rows)


def _aberdeen_lineup(
    *,
    season: str,
    matches: pl.DataFrame,
    squad_data: dict[str, Any],
    availability_payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    appearances = _aberdeen_appearances(season, squad_data=squad_data)
    if appearances is None:
        return _unavailable_lineup("no_local_lineups", team_id=ABERDEEN_API_ID)
    shapes_path = NORMALIZED_DIR / "matches" / "team_shapes.parquet"
    shapes = pl.DataFrame()
    if shapes_path.exists():
        shapes = pl.read_parquet(shapes_path).filter(
            (pl.col("team_id") == ABERDEEN_API_ID) & (pl.col("season") == season_start_year(season))
        )
    played = matches.filter(
        (pl.col("home_team_id") == "sco:aberdeen") | (pl.col("away_team_id") == "sco:aberdeen")
    ).height
    policy = matchday_policy().get("prediction") or {}
    availability_entries = {
        int(entry["player_id"]): entry
        for entry in (availability_payload or {}).get("entries", [])
        if entry.get("player_id") is not None and entry.get("in_squad", True)
    }
    availability_state = str(
        ((availability_payload or {}).get("coverage") or {}).get("status") or "unavailable"
    )
    return predict_lineup(
        appearances,
        shapes,
        team_id=ABERDEEN_API_ID,
        roles_config=roles_config(),
        policy=policy,
        squad=pl.DataFrame(squad_data.get("players", [])),
        fixtures_total=played,
        include_squad_only=True,
        recent_fixtures=int(matchday_policy().get("recent_fixtures") or 6),
        contenders=int(matchday_policy().get("contenders") or 6),
        availability=availability_entries,
        availability_state=availability_state,
        availability_as_of=(availability_payload or {}).get("as_of"),
        availability_source_ids=[
            source.get("id")
            for source in (availability_payload or {}).get("sources", [])
            if source.get("id")
        ],
    )


def _opponent_lineup(
    *,
    season: str,
    matches: pl.DataFrame,
    opponent_id: str,
    snapshot_dir: Path | None = None,
) -> dict[str, Any] | None:
    lineups = _read_snapshot("opponent_lineups.parquet", snapshot_dir)
    shapes = _read_snapshot("opponent_team_shapes.parquet", snapshot_dir)
    if lineups is None:
        return _unavailable_lineup("no_opponent_lineups")
    competition = _team_competition(
        opponent_id,
        season=season,
        matches=matches,
        tables=_tables_for(matches, season),
    )
    if competition is None:
        opponent_fixtures = _read_snapshot("opponent_fixtures.parquet", snapshot_dir)
        fixtures_total = int(opponent_fixtures.height if opponent_fixtures is not None else 0)
    else:
        _, _, table, _ = competition
        fixtures_total = int(table.filter(pl.col("team_id") == opponent_id)["played"].to_list()[0])
    policy = matchday_policy().get("prediction") or {}
    return predict_lineup(
        lineups,
        shapes if shapes is not None else pl.DataFrame(),
        team_id=int((load_meta(snapshot_dir).get("opponent") or {}).get("api_team_id") or 0),
        roles_config=roles_config(),
        policy=policy,
        fixtures_total=fixtures_total,
        include_squad_only=False,
        recent_fixtures=int(matchday_policy().get("recent_fixtures") or 6),
        contenders=int(matchday_policy().get("contenders") or 6),
    )


def _tables_for(matches: pl.DataFrame, season: str) -> dict[str, pl.DataFrame]:
    from fitba.analytics.tables import build_tables

    return build_tables(matches, season=season, config=competitions_config())


def _next_fixtures(
    *,
    after_date: str,
    season: str,
    limit: int = 5,
) -> list[FixtureBlock]:
    rows = []
    for row in load_schedule(season):
        if row.get("status") != "scheduled" or row.get("conflict_review"):
            continue
        if row.get("is_friendly"):
            continue
        if str(row.get("date") or "") <= after_date:
            continue
        rows.append(
            FixtureBlock(
                match_id=str(
                    row.get("fixture_id") or row.get("match_id") or row.get("schedule_key")
                ),
                competition_id=str(row.get("competition_id") or ""),
                competition_name=str(row.get("competition_name") or ""),
                stage=row.get("stage"),
                season=str(row.get("season") or season),
                date=str(row.get("date") or ""),
                kickoff=row.get("kickoff"),
                home_team_id=str(row.get("home_team_id") or ""),
                home_team_name=str(row.get("home_team_name") or ""),
                away_team_id=str(row.get("away_team_id") or ""),
                away_team_name=str(row.get("away_team_name") or ""),
                venue="N" if row.get("neutral") else "H" if row.get("is_home") else "A",
                opponent_id=str(row.get("opponent_id") or ""),
                opponent_name=str(row.get("opponent_name") or ""),
                status=str(row.get("status") or ""),
                source_id="spfl" if "spfl" in (row.get("sources") or []) else "api_football",
            )
        )
    rows.sort(key=lambda item: (item.date, item.kickoff or ""))
    return rows[:limit]


def _head_to_head(all_matches: pl.DataFrame, opponent_id: str) -> list[HeadToHead]:
    if all_matches.height == 0:
        return []
    frame = all_matches.filter(
        (pl.col("home_goals").is_not_null())
        & (
            ((pl.col("home_team_id") == "sco:aberdeen") & (pl.col("away_team_id") == opponent_id))
            | ((pl.col("away_team_id") == "sco:aberdeen") & (pl.col("home_team_id") == opponent_id))
        )
    ).sort("date", descending=True)
    output = []
    for row in frame.head(3).to_dicts():
        aberdeen_home = row["home_team_id"] == "sco:aberdeen"
        gf = row["home_goals"] if aberdeen_home else row["away_goals"]
        ga = row["away_goals"] if aberdeen_home else row["home_goals"]
        output.append(
            HeadToHead(
                date=str(row.get("date") or ""),
                competition_name=row.get("competition_name"),
                home_team_name=str(row.get("home_team_name") or ""),
                away_team_name=str(row.get("away_team_name") or ""),
                home_goals=row.get("home_goals"),
                away_goals=row.get("away_goals"),
                venue="H" if aberdeen_home else "A",
                result="W" if gf > ga else "D" if gf == ga else "L",
            )
        )
    return output


def _source_refs() -> list[SourceRef]:
    registry = (source_registry() or {}).get("sources") or {}
    output = []
    for source_id in ("spfl", "football_data_uk", "api_football"):
        item = registry.get(source_id)
        if not item:
            continue
        output.append(
            SourceRef(
                id=source_id,
                name=str(item.get("name") or source_id),
                url=item.get("url") or item.get("base_url"),
                verified_at=str(item.get("last_verified") or ""),
            )
        )
    return output


def _age_hours(generated_at: str | None) -> float | None:
    if not generated_at:
        return None
    try:
        generated = datetime.fromisoformat(generated_at)
    except ValueError:
        return None
    return round((datetime.now(UTC) - generated).total_seconds() / 3600, 1)


def _empty_document(
    *, season: str, generated_at: str, state: STATE, reason: str
) -> MatchdayDocument:
    return MatchdayDocument(
        generated_at=generated_at,
        season=season,
        state=state,
        stale_reason=reason,
        notes=(
            "No upcoming Aberdeen fixture is available, so no matchday projection is published."
            if state == "no_fixture"
            else "The matchday projection could not be built from local data."
        ),
    )


def build_matchday_payload(
    *,
    season: str,
    generated_at: str,
    matches: pl.DataFrame,
    all_matches: pl.DataFrame,
    tables: dict[str, pl.DataFrame],
    squad_data: dict[str, Any],
    availability: dict[str, Any] | None = None,
    snapshot_dir: Path | None = None,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the typed matchday document. Never raises for missing data."""
    fixture = _fixture_from_snapshot(snapshot_dir)
    if not fixture:
        return _empty_document(
            season=season,
            generated_at=generated_at,
            state="no_fixture",
            reason="no_scheduled_fixture",
        ).model_dump()

    fixture_date = str(fixture.get("date") or "")[:10]
    fixture_source = "snapshot"
    if fixture_date and fixture_date < date.today().isoformat():
        # The snapshot is a cache. Prefer the live merged schedule before
        # declaring that there is no fixture.
        live = next_fixture(season=season)
        if live:
            fixture = live
            fixture_date = str(live.get("date") or "")[:10]
            fixture_source = "live_schedule"
        else:
            return _empty_document(
                season=season,
                generated_at=generated_at,
                state="no_fixture",
                reason="fixture_date_passed",
            ).model_dump()

    meta = load_meta(snapshot_dir)
    opponent_id = str(fixture.get("opponent_id") or "")
    opponent_name = str(fixture.get("opponent_name") or opponent_id)
    aberdeen_name = "Aberdeen"
    teams = {
        "aberdeen": _team_ref("sco:aberdeen", aberdeen_name),
        "opponent": _team_ref(opponent_id, opponent_name),
    }

    aberdeen_comp = _team_competition(
        "sco:aberdeen",
        season=season,
        matches=matches,
        tables=tables,
    )
    opponent_comp = _team_competition(
        opponent_id,
        season=season,
        matches=matches,
        tables=tables,
    )
    if aberdeen_comp is None:
        return _empty_document(
            season=season,
            generated_at=generated_at,
            state="unavailable",
            reason="aberdeen_league_row_unavailable",
        ).model_dump()

    aberdeen_comp_id, aberdeen_comp_config, aberdeen_table, aberdeen_rows = aberdeen_comp
    form_guide: dict[str, Any] = {}
    styles: dict[str, Any] = {}
    strength: dict[str, Any] = {}
    predicted: dict[str, Any] = {}

    form_guide["aberdeen"] = _form_for(
        matches,
        team_id="sco:aberdeen",
        competition_id=aberdeen_comp_id,
        competition_name=str(aberdeen_comp_config.get("name") or aberdeen_comp_id),
        season=season,
    )
    aberdeen_venue = "H" if fixture.get("home_team_id") == "sco:aberdeen" else "A"
    styles["aberdeen"] = _styles_for(
        aberdeen_rows,
        team_id="sco:aberdeen",
        competition_id=aberdeen_comp_id,
        season=season,
        venue=aberdeen_venue,
    )
    strength["aberdeen"] = strength_block(
        aberdeen_table,
        team_id="sco:aberdeen",
        league_rows=aberdeen_rows,
        competition_id=aberdeen_comp_id,
        competition_name=str(aberdeen_comp_config.get("name") or aberdeen_comp_id),
        tier=aberdeen_comp_config.get("tier"),
    )
    predicted["aberdeen"] = _aberdeen_lineup(
        season=season,
        matches=matches,
        squad_data=squad_data,
        availability_payload=availability,
    )

    if opponent_comp is None:
        form_guide["opponent"] = form_block(
            pl.DataFrame(),
            n=5,
            competition_id=None,
            competition_name=None,
            season=season,
        )
        styles["opponent"] = {
            "overall": style_block(pl.DataFrame()),
            "venue": style_block(pl.DataFrame()),
            "lean": {
                "approach": "unknown",
                "label": "Unknown",
                "confidence": "low",
                "approach_index": None,
                "venue_index": None,
                "overall_index": None,
                "shot_share": None,
                "venue_matches": 0,
                "venue_used": False,
                "evidence": [],
                "basis": "measured",
                "interpretation": "inferred",
                "missing_metrics": [],
                "reason": "no_league_table",
                "note": "No current league table for the opponent.",
            },
        }
        strength["opponent"] = {
            "status": "unavailable",
            "team_id": opponent_id,
            "reason": "no_league_table",
        }
    else:
        opp_comp_id, opp_comp_config, opp_table, opp_rows = opponent_comp
        opponent_venue = "H" if fixture.get("home_team_id") == opponent_id else "A"
        form_guide["opponent"] = _form_for(
            matches,
            team_id=opponent_id,
            competition_id=opp_comp_id,
            competition_name=str(opp_comp_config.get("name") or opp_comp_id),
            season=season,
        )
        styles["opponent"] = _styles_for(
            opp_rows,
            team_id=opponent_id,
            competition_id=opp_comp_id,
            season=season,
            venue=opponent_venue,
        )
        strength["opponent"] = strength_block(
            opp_table,
            team_id=opponent_id,
            league_rows=opp_rows,
            competition_id=opp_comp_id,
            competition_name=str(opp_comp_config.get("name") or opp_comp_id),
            tier=opp_comp_config.get("tier"),
        )
        predicted["opponent"] = _opponent_lineup(
            season=season,
            matches=matches,
            opponent_id=opponent_id,
            snapshot_dir=snapshot_dir,
        )

    comparison = strength_comparison(strength["aberdeen"], strength["opponent"])
    read = matchup_read(
        fixture=fixture,
        aberdeen={
            "team": teams["aberdeen"].model_dump(),
            "style": styles["aberdeen"],
            "strength": strength["aberdeen"],
            "strength_comparison": comparison,
            "lineup": predicted["aberdeen"] or {},
        },
        opponent={
            "team": teams["opponent"].model_dump(),
            "style": styles["opponent"],
            "strength": strength["opponent"],
            "strength_comparison": comparison,
            "lineup": predicted["opponent"] or {},
        },
    )

    snapshot_state = str(meta.get("state") or "missing")
    age = _age_hours(meta.get("generated_at"))
    stale_after = float(matchday_policy().get("stale_after_hours") or 48)
    state: STATE = "fresh"
    stale_reason = None
    if snapshot_state in {"missing", "no_fixture", "unavailable"}:
        state = "unavailable"
        stale_reason = str(meta.get("reason") or "no_opponent_snapshot")
    elif age is not None and age > stale_after:
        state = "stale"
        stale_reason = f"snapshot_older_than_{int(stale_after)}h"

    lineup_blocks = {
        "aberdeen": _lineup_payload(predicted.get("aberdeen"), basis="local_lineups"),
        "opponent": _lineup_payload(predicted.get("opponent"), basis="provider_lineups"),
    }
    coverage = {
        "state": state,
        "fixture_source": fixture_source,
        "snapshot": {
            "state": snapshot_state,
            "generated_at": meta.get("generated_at"),
            "age_hours": age,
            "opponent_api_id": (meta.get("opponent") or {}).get("api_team_id"),
            "resolution": (meta.get("opponent") or {}).get("resolution"),
            "fixtures": (meta.get("coverage") or {}).get("fixtures"),
            "fixtures_with_lineups": (meta.get("coverage") or {}).get("fixtures_with_lineups"),
        },
        "lineups": {
            "aberdeen": (
                lineup_blocks["aberdeen"].status if lineup_blocks["aberdeen"] else "unavailable"
            ),
            "opponent": (
                lineup_blocks["opponent"].status if lineup_blocks["opponent"] else "unavailable"
            ),
        },
        "form": "league",
        "style": "shots_only",
        "possession": "unknown",
        "note": (
            "Form and style are league-only and opponent-unadjusted. "
            "Predicted XIs are projections from observed lineups, not team news. "
            "Possession is not used."
        ),
    }
    notes = (
        "Matchday projections are measured where marked and inferred where a "
        "model or comparison is used. The page is not a result prediction and "
        "not betting advice."
    )
    fixture_block = _fixture_block(fixture)
    for schedule_row in load_schedule(season):
        if (
            str(schedule_row.get("date") or "") == fixture_block.date
            and str(schedule_row.get("competition_id") or "") == fixture_block.competition_id
            and str(schedule_row.get("opponent_name") or "") == fixture_block.opponent_name
        ):
            fixture_block.venue = (
                "N" if schedule_row.get("neutral") else "H" if schedule_row.get("is_home") else "A"
            )
            fixture_block.stage = schedule_row.get("stage")
            fixture_block.competition_name = str(schedule_row.get("competition_name") or "")
            fixture_block.kickoff = schedule_row.get("kickoff") or fixture_block.kickoff
            break
    document = MatchdayDocument(
        generated_at=generated_at,
        season=season,
        state=state,
        stale_reason=stale_reason,
        served_generated_at=meta.get("generated_at"),
        fixture=fixture_block,
        next_fixtures=_next_fixtures(after_date=fixture_date, season=season),
        teams=teams,
        form_guide={key: FormBlock(**value) for key, value in form_guide.items()},
        head_to_head=_head_to_head(all_matches, opponent_id),
        strength={key: StrengthTeam(**value) for key, value in strength.items()},
        strength_comparison=comparison,
        styles={key: StylePair(**value) for key, value in styles.items()},
        predicted_lineups=lineup_blocks,
        matchup_read=MatchupRead(**read),
        coverage=coverage,
        sources=_source_refs(),
        notes=notes,
    )
    return document.model_dump()


def fallback_matchday_payload(
    previous: dict[str, Any] | None,
    *,
    generated_at: str,
    season: str,
    reason: str,
) -> dict[str, Any]:
    """Carry forward the last good document as stale, or publish a safe empty one."""
    if previous:
        fixture = previous.get("fixture") or {}
        fixture_date = str(fixture.get("date") or "")[:10]
        if fixture_date and fixture_date < date.today().isoformat():
            return _empty_document(
                season=season,
                generated_at=generated_at,
                state="no_fixture",
                reason="fixture_date_passed",
            ).model_dump()
        carried = {
            **previous,
            "generated_at": generated_at,
            "season": season,
            "served_generated_at": previous.get("generated_at"),
            "state": "stale",
            "stale_reason": reason,
        }
        try:
            return MatchdayDocument(**carried).model_dump()
        except Exception:  # noqa: BLE001 - a corrupt previous document is not reused
            pass
    return _empty_document(
        season=season,
        generated_at=generated_at,
        state="unavailable",
        reason=reason,
    ).model_dump()


__all__ = [
    "MatchdayDocument",
    "build_matchday_payload",
    "fallback_matchday_payload",
    "matchday_schema",
]
