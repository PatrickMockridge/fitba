"""Ingest the Aberdeen squad and current-season player statistics.

The squad is the current API-Football squad plus current loanees out from the
confirmed transfer register. Stats are per competition for the current season.
Missing data is labelled: a youth player with no statistics entries is
``unavailable``, not a set of zeroes, and a loanee's parent-club rows are never
presented as loan-club output.
"""

from __future__ import annotations

import re
from typing import Any

import polars as pl
from rapidfuzz.fuzz import token_set_ratio

from fitba.ingest.match_data import ingest_match_data
from fitba.ingest.player_attributes import ingest_player_attributes
from fitba.ingest.transfers import published_transfers
from fitba.normalize.names import strip_accents
from fitba.normalize.players import PlayerRegistry
from fitba.normalize.positions import squad_group
from fitba.settings import (
    NORMALIZED_DIR,
    ensure_dirs,
)
from fitba.settings import (
    aberdeen as aberdeen_config,
)
from fitba.settings import (
    source_ids as source_ids_config,
)
from fitba.sources import api_football
from fitba.sources.base import IngestResult
from fitba.util.dates import current_season, utc_now_iso

PLAYER_COLUMNS = [
    "player_id",
    "player_key",
    "name",
    "full_name",
    "firstname",
    "lastname",
    "birth_date",
    "age",
    "number",
    "position",
    "position_group",
    "nationality",
    "injured",
    "status",
    "loan_club",
    "loan_since",
    "loan_end_date",
    "stats_coverage",
    "stats_note",
    "ingested_at",
]

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

STATUS_ORDER = {"squad": 0, "loan_in": 1, "loan_out": 2}
POSITION_ORDER = {"GK": 0, "DEF": 1, "MID": 2, "FWD": 3}
PUNCT_RE = re.compile(r"[^\w\s]")
SPACE_RE = re.compile(r"\s+")


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


def _club_key(value: str) -> str:
    normalized = strip_accents(value).casefold()
    normalized = PUNCT_RE.sub(" ", normalized)
    return SPACE_RE.sub(" ", normalized).strip()


def _club_matches(api_name: str, loan_club: str) -> bool:
    left = _club_key(api_name)
    right = _club_key(loan_club)
    if not left or not right:
        return False
    if left == right or left in right or right in left:
        return True
    return token_set_ratio(left, right) >= 85


def _season_year(season: str) -> int:
    try:
        return int(season[:4])
    except ValueError:
        return api_football.CURRENT_SEASON


def _loan_maps(season: str) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Latest current-season move per player; only a latest loan is a live loan.

    A player who went out on loan and then returned, or then left permanently,
    is not tagged as a current loanee.
    """
    latest: dict[str, dict[str, Any]] = {}
    for row in published_transfers():
        if row.get("season") != season:
            continue
        key = str(row.get("player_key") or "")
        if not key:
            continue
        current = latest.get(key)
        if current is None or (
            str(row.get("date_effective") or ""),
            str(row.get("transfer_id") or ""),
        ) > (
            str(current.get("date_effective") or ""),
            str(current.get("transfer_id") or ""),
        ):
            latest[key] = row

    outs = {
        key: row
        for key, row in latest.items()
        if row.get("transfer_kind") == "loan" and row.get("direction") == "out"
    }
    ins = {
        key: row
        for key, row in latest.items()
        if row.get("transfer_kind") == "loan" and row.get("direction") == "in"
    }
    return outs, ins


def _stat_row(
    *,
    player_id: int,
    player_key: str,
    entry: dict[str, Any],
    scope: str,
    season_year: int,
    ingested_at: str,
) -> dict[str, Any] | None:
    league = entry.get("league") or {}
    team = entry.get("team") or {}
    entry_season = _int(league.get("season"))
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
    direct_red = _int(cards.get("red"))
    second_yellow = _int(cards.get("yellowred"))
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
        "team_id": _int(team.get("id")),
        "team_name": str(team.get("name") or "Unknown team"),
        "season": entry_season or season_year,
        "appearances": _int(games.get("appearences", games.get("appearances"))),
        "starts": _int(games.get("lineups")),
        "minutes": _int(games.get("minutes")),
        "goals": _int(goals.get("total")),
        "assists": _int(goals.get("assists")),
        "yellow_cards": _int(cards.get("yellow")),
        "red_cards": red_cards,
        "rating": _rating(games.get("rating")),
        "shots_total": _int(shots.get("total")),
        "shots_on": _int(shots.get("on")),
        "passes_total": _int(passes.get("total")),
        "passes_key": _int(passes.get("key")),
        "pass_accuracy": _float(passes.get("accuracy")),
        "saves": _int(goals.get("saves")),
        "conceded": _int(goals.get("conceded")),
        "tackles": _int(tackles.get("total")),
        "blocks": _int(tackles.get("blocks")),
        "interceptions": _int(tackles.get("interceptions")),
        "duels_total": _int(duels.get("total")),
        "duels_won": _int(duels.get("won")),
        "dribbles_attempts": _int(dribbles.get("attempts")),
        "dribbles_success": _int(dribbles.get("success")),
        "fouls_drawn": _int(fouls.get("drawn")),
        "fouls_committed": _int(fouls.get("committed")),
        "penalty_won": _int(penalty.get("won")),
        "penalty_committed": _int(penalty.get("commited")),
        "penalty_scored": _int(penalty.get("scored")),
        "penalty_missed": _int(penalty.get("missed")),
        "penalty_saved": _int(penalty.get("saved")),
        "ingested_at": ingested_at,
    }


def _scope_for(
    entry: dict[str, Any],
    *,
    status: str,
    loan_club: str | None,
    parent_team_id: int,
) -> str:
    team = entry.get("team") or {}
    team_id = _int(team.get("id"))
    team_name = str(team.get("name") or "")
    if status in {"squad", "loan_in"} and team_id == parent_team_id:
        return "club"
    if status == "loan_out" and loan_club and _club_matches(team_name, loan_club):
        return "loan"
    return "other"


def _coverage(
    *,
    status: str,
    stats: list[dict[str, Any]],
    loan_club: str | None,
) -> tuple[str, str]:
    scope = "loan" if status == "loan_out" else "club"
    relevant = [row for row in stats if row["scope"] == scope]
    other_teams = sorted({row["team_name"] for row in stats if row["scope"] == "other"})

    if not relevant:
        if status == "loan_out" and loan_club:
            note = f"No 2026-27 statistics for {loan_club} in the licensed feed."
        else:
            note = "No 2026-27 player statistics in the licensed feed."
        if other_teams:
            note += f" The feed lists records for {', '.join(other_teams)}."
        return "unavailable", note

    partial = any(
        (row.get("appearances") or 0) > 0 and row.get("minutes") is None for row in relevant
    )
    if status == "loan_out" and loan_club:
        note = f"Loan-club statistics from {loan_club}."
    else:
        note = "Current-season statistics from the licensed feed."
    if partial:
        note += " Some minutes are missing from the source."
        return "partial", note
    return "available", note


def _player_row(
    *,
    player_id: int,
    player_key: str,
    fallback_name: str,
    fallback_position: str | None,
    fallback_age: int | None,
    number: int | None,
    status: str,
    loan: dict[str, Any] | None,
    details: list[dict[str, Any]],
    season_year: int,
    parent_team_id: int,
    ingested_at: str,
    player_registry: PlayerRegistry,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    profile = (details[0].get("player") if details else {}) or {}
    entries = (details[0].get("statistics") if details else []) or []
    source_name = str(profile.get("name") or fallback_name)
    resolved = player_registry.resolve(api_football_id=player_id, name=source_name)
    if resolved.status == "resolved":
        name = resolved.name
        parts = name.split(" ", 1)
        firstname = parts[0] or None
        lastname = parts[1] if len(parts) > 1 else None
        full_name = name
    else:
        name = source_name
        firstname = str(profile.get("firstname") or "").strip() or None
        lastname = str(profile.get("lastname") or "").strip() or None
        full_name = f"{firstname} {lastname}".strip() if firstname and lastname else name
    birth = profile.get("birth") or {}
    birth_date = str(birth.get("date") or "") or None
    loan_club = str(loan.get("to_club_name") or loan.get("from_club_name") or "") if loan else None
    if status == "loan_out" and loan:
        loan_club = str(loan.get("to_club_name") or "")
    if status == "loan_in" and loan:
        loan_club = str(loan.get("from_club_name") or "")

    stats: list[dict[str, Any]] = []
    position = resolved.position or fallback_position
    number = number if number is not None else resolved.shirt_number
    for entry in entries:
        scope = _scope_for(
            entry,
            status=status,
            loan_club=loan_club,
            parent_team_id=parent_team_id,
        )
        row = _stat_row(
            player_id=player_id,
            player_key=player_key,
            entry=entry,
            scope=scope,
            season_year=season_year,
            ingested_at=ingested_at,
        )
        if row is not None:
            stats.append(row)
        games_position = (entry.get("games") or {}).get("position")
        if position is None and games_position:
            position = str(games_position)

    coverage, note = _coverage(status=status, stats=stats, loan_club=loan_club)
    age = _int(profile.get("age")) or fallback_age
    row = {
        "player_id": player_id,
        "player_key": player_key,
        "name": name,
        "full_name": full_name,
        "firstname": firstname,
        "lastname": lastname,
        "birth_date": birth_date,
        "age": age,
        "number": number,
        "position": position,
        "position_group": squad_group(position),
        "nationality": profile.get("nationality") or resolved.nationality,
        "injured": bool(profile.get("injured")) if profile else False,
        "status": status,
        "loan_club": loan_club,
        "loan_since": str(loan.get("date_effective")) if loan else None,
        "loan_end_date": loan.get("loan_end_date") if loan else None,
        "stats_coverage": coverage,
        "stats_note": note,
        "ingested_at": ingested_at,
    }
    return row, stats


def ingest_squad(*, force: bool = False) -> IngestResult:
    ensure_dirs()
    try:
        club_id = str(aberdeen_config()["club_id"])
        parent_team_id = int(source_ids_config()["teams"][club_id]["api_football"])
        season = current_season()
        season_year = _season_year(season)
        loan_outs, loan_ins = _loan_maps(season)
        player_registry = PlayerRegistry()
        now = utc_now_iso()

        squad_records: list[dict[str, Any]] = []
        for item in api_football.players_squads(parent_team_id, force=force):
            squad_records.extend(item.get("players", []))

        players: list[dict[str, Any]] = []
        stats: list[dict[str, Any]] = []
        seen: set[str] = set()

        for record in squad_records:
            player_id = _int(record.get("id"))
            if player_id is None:
                continue
            player_key = f"api:player:{player_id}"
            seen.add(player_key)
            loan = loan_ins.get(player_key)
            status = "loan_in" if loan else "squad"
            try:
                details = api_football.player(player_id, season=season_year, force=force)
            except Exception:  # noqa: BLE001 - one player is not fatal
                details = []
            row, player_stats = _player_row(
                player_id=player_id,
                player_key=player_key,
                fallback_name=str(record.get("name") or f"Player {player_id}"),
                fallback_position=record.get("position"),
                fallback_age=_int(record.get("age")),
                number=_int(record.get("number")),
                status=status,
                loan=loan,
                details=details,
                season_year=season_year,
                parent_team_id=parent_team_id,
                ingested_at=now,
                player_registry=player_registry,
            )
            players.append(row)
            stats.extend(player_stats)

        for player_key, loan in loan_outs.items():
            if player_key in seen:
                continue
            player_id = _int(player_key.split(":")[-1])
            if player_id is None:
                continue
            try:
                details = api_football.player(player_id, season=season_year, force=force)
            except Exception:  # noqa: BLE001
                details = []
            row, player_stats = _player_row(
                player_id=player_id,
                player_key=player_key,
                fallback_name=str(loan.get("player_name") or f"Player {player_id}"),
                fallback_position=loan.get("position"),
                fallback_age=None,
                number=None,
                status="loan_out",
                loan=loan,
                details=details,
                season_year=season_year,
                parent_team_id=parent_team_id,
                ingested_at=now,
                player_registry=player_registry,
            )
            players.append(row)
            stats.extend(player_stats)

        players.sort(
            key=lambda row: (
                STATUS_ORDER.get(str(row["status"]), 9),
                POSITION_ORDER.get(str(row["position_group"]), 9),
                str(row["name"]),
            )
        )

        output_dir = NORMALIZED_DIR / "squad"
        output_dir.mkdir(parents=True, exist_ok=True)
        player_frame = (
            pl.DataFrame(players).select(PLAYER_COLUMNS)
            if players
            else pl.DataFrame({column: [] for column in PLAYER_COLUMNS})
        )
        stat_frame = (
            pl.DataFrame(stats).select(STAT_COLUMNS)
            if stats
            else pl.DataFrame({column: [] for column in STAT_COLUMNS})
        )
        player_frame.write_parquet(output_dir / "aberdeen_players.parquet")
        stat_frame.write_parquet(output_dir / "aberdeen_stats.parquet")

        match_result = ingest_match_data(
            team_id=parent_team_id,
            squad_ids={int(row["player_id"]) for row in players},
            season_year=season_year,
            force=force,
        )
        attribute_result = ingest_player_attributes(players, force=force)

        return IngestResult(
            source="api_football",
            status="ok",
            rows=player_frame.height,
            path=str(output_dir / "aberdeen_players.parquet"),
            details={
                "season": season,
                "squad": sum(1 for row in players if row["status"] == "squad"),
                "loans_out": sum(1 for row in players if row["status"] == "loan_out"),
                "loans_in": sum(1 for row in players if row["status"] == "loan_in"),
                "stats_rows": stat_frame.height,
                "stats_unavailable": sum(
                    1 for row in players if row["stats_coverage"] == "unavailable"
                ),
                "match_data": match_result.details,
                "match_data_errors": match_result.errors,
                "player_attributes": attribute_result.details,
                "player_attributes_errors": attribute_result.errors,
            },
        )
    except Exception as exc:  # noqa: BLE001 - reported by the CLI
        return IngestResult(source="api_football", status="error", errors=[str(exc)])


def load_squad_players() -> pl.DataFrame:
    path = NORMALIZED_DIR / "squad" / "aberdeen_players.parquet"
    if not path.exists():
        return pl.DataFrame({column: [] for column in PLAYER_COLUMNS})
    return pl.read_parquet(path)


def load_squad_stats() -> pl.DataFrame:
    path = NORMALIZED_DIR / "squad" / "aberdeen_stats.parquet"
    if not path.exists():
        return pl.DataFrame({column: [] for column in STAT_COLUMNS})
    return pl.read_parquet(path)


__all__ = [
    "PLAYER_COLUMNS",
    "STAT_COLUMNS",
    "ingest_squad",
    "load_squad_players",
    "load_squad_stats",
]
