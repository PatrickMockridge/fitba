"""Shared parsing for API-Football player-season statistics.

One parser feeds both the Aberdeen squad ingest and the scouting player pool.
The field names are the provider's; the canonical rate helpers live in the
scouting analytics module. Unknown values stay ``None`` and are never zero-filled.
"""

from __future__ import annotations

from typing import Any

STAT_COLUMNS = [
    "player_id",
    "player_key",
    "scope",
    "competition",
    "team_id",
    "team_name",
    "season",
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
]


def to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace("%", ""))
    except (TypeError, ValueError):
        return None


def to_rating(value: Any) -> float | None:
    rating = to_float(value)
    return rating if rating and rating > 0 else None


def parse_stat_entry(
    *,
    player_id: int,
    player_key: str,
    entry: dict[str, Any],
    scope: str,
    season_year: int,
    ingested_at: str,
) -> dict[str, Any] | None:
    """Parse one API-Football ``statistics`` entry, or None for another season."""
    league = entry.get("league") or {}
    team = entry.get("team") or {}
    entry_season = to_int(league.get("season"))
    if entry_season is not None and entry_season != season_year:
        return None
    games = entry.get("games") or {}
    goals = entry.get("goals") or {}
    cards = entry.get("cards") or {}
    shots = entry.get("shots") or {}
    passes = entry.get("passes") or {}
    tackles = entry.get("tackles") or {}
    duels = entry.get("duels") or {}
    dribbles = entry.get("dribbles") or {}
    fouls = entry.get("fouls") or {}
    penalty = entry.get("penalty") or {}
    direct_red = to_int(cards.get("red"))
    second_yellow = to_int(cards.get("yellowred"))
    red_cards = (
        None
        if direct_red is None and second_yellow is None
        else (direct_red or 0) + (second_yellow or 0)
    )
    return {
        "player_id": player_id,
        "player_key": player_key,
        "scope": scope,
        "competition": str(league.get("name") or "Unknown competition"),
        "team_id": to_int(team.get("id")),
        "team_name": str(team.get("name") or "Unknown team"),
        "season": entry_season or season_year,
        "appearances": to_int(games.get("appearences", games.get("appearances"))),
        "starts": to_int(games.get("lineups")),
        "minutes": to_int(games.get("minutes")),
        "goals": to_int(goals.get("total")),
        "assists": to_int(goals.get("assists")),
        "yellow_cards": to_int(cards.get("yellow")),
        "red_cards": red_cards,
        "rating": to_rating(games.get("rating")),
        "shots_total": to_int(shots.get("total")),
        "shots_on": to_int(shots.get("on")),
        "passes_total": to_int(passes.get("total")),
        "passes_key": to_int(passes.get("key")),
        "pass_accuracy": to_float(passes.get("accuracy")),
        "saves": to_int(goals.get("saves")),
        "conceded": to_int(goals.get("conceded")),
        "tackles": to_int(tackles.get("total")),
        "blocks": to_int(tackles.get("blocks")),
        "interceptions": to_int(tackles.get("interceptions")),
        "duels_total": to_int(duels.get("total")),
        "duels_won": to_int(duels.get("won")),
        "dribbles_attempts": to_int(dribbles.get("attempts")),
        "dribbles_success": to_int(dribbles.get("success")),
        "fouls_drawn": to_int(fouls.get("drawn")),
        "fouls_committed": to_int(fouls.get("committed")),
        "penalty_won": to_int(penalty.get("won")),
        "penalty_committed": to_int(penalty.get("commited")),
        "penalty_scored": to_int(penalty.get("scored")),
        "penalty_missed": to_int(penalty.get("missed")),
        "penalty_saved": to_int(penalty.get("saved")),
        "ingested_at": ingested_at,
    }
