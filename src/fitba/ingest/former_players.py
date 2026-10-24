"""Bounded backfill and refresh of former-player post-Aberdeen records.

The published former-player payload reads these normalized tables only. The
job is cache-first, resumable and budgeted; it never runs inside ``publish``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import polars as pl

from fitba.analytics.former_players import former_player_rows
from fitba.ingest.transfers import published_transfers
from fitba.normalize.player_stats import parse_stat_entry
from fitba.normalize.transfer_history import parse_transfer_type
from fitba.settings import NORMALIZED_DIR, ensure_dirs, scouting_leagues
from fitba.settings import former_players as former_config
from fitba.sources import api_football
from fitba.sources.base import IngestResult
from fitba.util.dates import current_season, season_start_year, seasons_between, utc_now_iso

FORMER_DIR = NORMALIZED_DIR / "former_players"
PLAYERS_PATH = FORMER_DIR / "former_players.parquet"
SEASONS_PATH = FORMER_DIR / "post_seasons.parquet"
EVENTS_PATH = FORMER_DIR / "transfer_events.parquet"
STATE_PATH = FORMER_DIR / "backfill_state.parquet"
META_PATH = FORMER_DIR / "meta.json"

PLAYER_COLUMNS = [
    "player_key",
    "player_id",
    "player_name",
    "birth_date",
    "nationality",
    "position",
    "identity_status",
    "alias_keys",
    "departure_transfer_id",
    "departure_date",
    "departure_season",
    "departure_kind",
    "ingested_at",
]
SEASON_COLUMNS = [
    "player_key",
    "player_id",
    "season",
    "season_year",
    "team_id",
    "team_name",
    "competition",
    "league_id",
    "league_name",
    "country",
    "league_tier",
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
    "penalty_scored",
    "source",
    "ingested_at",
]
EVENT_COLUMNS = [
    "player_key",
    "player_id",
    "event_date",
    "type",
    "kind",
    "from_team_id",
    "from_team_name",
    "to_team_id",
    "to_team_name",
    "sequence",
    "ingested_at",
]
STATE_COLUMNS = [
    "player_id",
    "stage",
    "season_year",
    "status",
    "attempts",
    "last_error",
    "checked_at",
    "policy_version",
]

INTERNATIONAL_MARKERS = (
    "world cup",
    "euro championship",
    "european championship",
    "copa america",
    "nations league",
    "friendlies",
    "olympic",
    "confederations",
    "international",
)
EUROPEAN_MARKERS = (
    "champions league",
    "europa league",
    "conference league",
    "uefa super cup",
)
CUP_MARKERS = (
    "cup",
    "copa",
    "coppa",
    "coupe",
    "pokal",
    "trophy",
    "play-off",
    "playoff",
    "supercopa",
    "super cup",
    "supercup",
    "friendly",
    "friendlies",
)


def competition_scope(name: Any) -> str:
    """Classify a provider competition for league-only post-career totals.

    The provider repeats season totals across some cup entries (for example a
    domestic cup row carrying the league minutes and goals). Cup and European
    rows are therefore stored locally but excluded from the published
    post-career league record.
    """
    value = str(name or "").casefold()
    if any(marker in value for marker in EUROPEAN_MARKERS):
        return "europe"
    if any(marker in value for marker in CUP_MARKERS):
        return "cup"
    return "league"



def _paths() -> dict[str, Path]:
    return {
        "dir": FORMER_DIR,
        "players": PLAYERS_PATH,
        "seasons": SEASONS_PATH,
        "events": EVENTS_PATH,
        "state": STATE_PATH,
        "meta": META_PATH,
    }


def _load_rows(path: Path, columns: list[str]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    frame = pl.read_parquet(path)
    return frame.to_dicts() if frame.height else []


def _write_rows(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = (
        pl.DataFrame(rows, infer_schema_length=None).select(columns)
        if rows
        else pl.DataFrame({column: [] for column in columns})
    )
    temp = path.with_suffix(path.suffix + ".tmp")
    frame.write_parquet(temp)
    temp.replace(path)


def _write_meta(payload: dict[str, Any]) -> None:
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = META_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(META_PATH)


def load_former_meta() -> dict[str, Any]:
    if not META_PATH.exists():
        return {}
    try:
        return json.loads(META_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def load_former_players() -> pl.DataFrame:
    return pl.read_parquet(PLAYERS_PATH) if PLAYERS_PATH.exists() else pl.DataFrame()


def load_post_seasons() -> pl.DataFrame:
    return pl.read_parquet(SEASONS_PATH) if SEASONS_PATH.exists() else pl.DataFrame()


def load_transfer_events() -> pl.DataFrame:
    return pl.read_parquet(EVENTS_PATH) if EVENTS_PATH.exists() else pl.DataFrame()


def _policy_version(config: dict[str, Any]) -> str:
    encoded = json.dumps(config, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:12]


def _season_from_year(year: int) -> str:
    return f"{year}-{(year + 1) % 100:02d}"


def _league_map() -> dict[int, dict[str, Any]]:
    mapping: dict[int, dict[str, Any]] = {}
    for league_id, entry in (
        ((former_config().get("post_career") or {}).get("league_tiers") or {}).items()
    ):
        try:
            mapping[int(league_id)] = {
                "name": None,
                "country": entry.get("country"),
                "tier": entry.get("tier"),
            }
        except (TypeError, ValueError):
            continue
    for row in (scouting_leagues().get("pool") or []):
        provider = row.get("provider") or {}
        league_id = provider.get("api_football_id")
        if league_id is None:
            continue
        mapping[int(league_id)] = {
            "name": row.get("name"),
            "country": row.get("country"),
            "tier": row.get("tier"),
        }
    return mapping


def _is_international(league: dict[str, Any]) -> bool:
    country = str(league.get("country") or "").casefold()
    name = str(league.get("name") or "").casefold()
    if country in {"world", "europe", "south america", "africa", "asia", "oceania"}:
        return True
    return any(marker in name for marker in INTERNATIONAL_MARKERS)


def _api_id(player_key: str) -> int | None:
    if not player_key.startswith("api:player:"):
        return None
    try:
        return int(player_key.split(":")[-1])
    except ValueError:
        return None


def _fresh(checked_at: Any, ttl_hours: float) -> bool:
    if not checked_at:
        return False
    try:
        checked = datetime.fromisoformat(str(checked_at))
    except ValueError:
        return False
    if checked.tzinfo is None:
        checked = checked.replace(tzinfo=UTC)
    return datetime.now(UTC) - checked < timedelta(hours=ttl_hours)


def _player_profile(
    response: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not response:
        return None, []
    player = response[0].get("player") or {}
    statistics = response[0].get("statistics") or []
    return player, statistics


def _parse_seasons(
    *,
    player_key: str,
    player_id: int,
    statistics: list[dict[str, Any]],
    season_year: int,
    league_map: dict[int, dict[str, Any]],
    ingested_at: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in statistics:
        league = entry.get("league") or {}
        if _is_international(league):
            continue
        parsed = parse_stat_entry(
            player_id=player_id,
            player_key=player_key,
            entry=entry,
            scope="club",
            season_year=season_year,
            ingested_at=ingested_at,
        )
        if parsed is None:
            continue
        parsed["scope"] = competition_scope(parsed.get("competition"))
        league_id = (
            int(str(league.get("id"))) if league.get("id") is not None else None
        )
        meta = league_map.get(league_id or 0, {})
        rows.append(
            {
                **parsed,
                "season": _season_from_year(season_year),
                "season_year": season_year,
                "league_id": league_id,
                "league_name": meta.get("name") or league.get("name"),
                "country": meta.get("country") or league.get("country"),
                "league_tier": meta.get("tier"),
                "source": "api_football",
            }
        )
    return rows


def _parse_events(
    *,
    player_key: str,
    player_id: int,
    transfers: list[dict[str, Any]],
    ingested_at: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sequence, transfer in enumerate(transfers):
        teams = transfer.get("teams") or {}
        outgoing = teams.get("out") or {}
        incoming = teams.get("in") or {}
        raw_type = str(transfer.get("type") or "")
        rows.append(
            {
                "player_key": player_key,
                "player_id": player_id,
                "event_date": str(transfer.get("date") or "")[:10],
                "type": raw_type,
                "kind": parse_transfer_type(raw_type),
                "from_team_id": outgoing.get("id"),
                "from_team_name": outgoing.get("name"),
                "to_team_id": incoming.get("id"),
                "to_team_name": incoming.get("name"),
                "sequence": sequence,
                "ingested_at": ingested_at,
            }
        )
    return rows


def _state_map(rows: list[dict[str, Any]]) -> dict[tuple[int, str, int], dict[str, Any]]:
    return {
        (int(row["player_id"]), str(row["stage"]), int(row["season_year"])): row
        for row in rows
        if row.get("player_id") is not None
    }


def _state_key(stage: str, season_year: int) -> tuple[str, int]:
    return stage, season_year


def ingest_former_players(
    *,
    mode: str = "refresh",
    max_requests: int | None = None,
    force: bool = False,
    dry_run: bool = False,
    player_keys: list[str] | None = None,
    season: str | None = None,
) -> IngestResult:
    """Backfill or refresh post-Aberdeen seasons and transfer histories."""
    ensure_dirs()
    FORMER_DIR.mkdir(parents=True, exist_ok=True)
    config = former_config()
    career = config.get("post_career") or {}
    policy = _policy_version(config)
    target_season = season or current_season()
    current_year = season_start_year(target_season)
    budget = int(
        max_requests
        or (
            career.get("refresh_max_requests")
            if mode == "refresh"
            else career.get("backfill_max_requests")
        )
        or career.get("max_requests_per_run")
        or 400
    )
    api_football.set_min_interval(float(career.get("request_interval_seconds") or 0.3))
    api_football.reset_network_requests()
    from fitba.publish.squad import squad_payload

    transfers = published_transfers()
    squad = squad_payload(target_season)
    universe = former_player_rows(transfers, squad)
    if player_keys:
        wanted = set(player_keys)
        universe = [row for row in universe if row["player_key"] in wanted]
    existing_players = {
        str(row.get("player_key")): row for row in _load_rows(PLAYERS_PATH, PLAYER_COLUMNS)
    }
    existing_seasons = _load_rows(SEASONS_PATH, SEASON_COLUMNS)
    existing_events = _load_rows(EVENTS_PATH, EVENT_COLUMNS)
    state = _state_map(_load_rows(STATE_PATH, STATE_COLUMNS))
    league_map = _league_map()
    now = utc_now_iso()
    historical_ttl = float(career.get("historical_ttl_hours") or 720)
    current_ttl = float(career.get("current_season_ttl_hours") or 24)
    transfers_ttl = float(career.get("transfers_ttl_hours") or 168)
    errors: list[str] = []
    budget_exhausted = False
    calls = 0
    expected_seasons = 0
    processed_ids: set[int] = set()
    replace_season_ids: set[int] = set()
    replace_event_ids: set[int] = set()
    no_api: list[str] = []
    player_rows: list[dict[str, Any]] = []
    season_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    state_rows: list[dict[str, Any]] = []
    for item in universe:
        key = item["player_key"]
        departure = item["departure"]
        player_id = _api_id(key)
        base_player = {
            "player_key": key,
            "player_id": player_id,
            "player_name": departure.get("player_name"),
            "birth_date": None,
            "nationality": departure.get("nationality"),
            "position": departure.get("position"),
            "identity_status": item["identity_status"],
            "alias_keys": item.get("alias_keys") or [],
            "departure_transfer_id": departure.get("transfer_id"),
            "departure_date": departure.get("date_effective"),
            "departure_season": departure.get("season"),
            "departure_kind": departure.get("transfer_kind"),
            "ingested_at": now,
        }
        profile = dict(existing_players.get(key) or {})
        profile.update({k: v for k, v in base_player.items() if v is not None})
        if player_id is None:
            no_api.append(key)
            player_rows.append(profile)
            continue
        processed_ids.add(player_id)
        departure_year = season_start_year(str(departure.get("season") or target_season))
        years = list(range(departure_year, current_year + 1))
        expected_seasons += len(years)
        if dry_run:
            for year in years:
                state_key = (player_id, "profile", year)
                previous = state.get(state_key)
                if force or not previous or previous.get("policy_version") != policy:
                    calls += 1
            previous_transfers = state.get((player_id, "transfers", 0))
            if (
                force
                or not previous_transfers
                or previous_transfers.get("policy_version") != policy
            ):
                calls += 1
            player_rows.append(profile)
            continue
        for year in years:
            if api_football.network_requests() >= budget:
                budget_exhausted = True
                break
            state_key = (player_id, "profile", year)
            previous = state.get(state_key)
            ttl = current_ttl if year == current_year else historical_ttl
            if (
                not force
                and previous
                and previous.get("policy_version") == policy
                and previous.get("status") in {"complete", "no_data"}
                and _fresh(previous.get("checked_at"), ttl)
            ):
                continue
            try:
                response = api_football.player(
                    player_id,
                    season=year,
                    ttl_hours=ttl,
                    force=force,
                )
                player, statistics = _player_profile(response)
                if player:
                    birth = (player.get("birth") or {}).get("date")
                    if birth:
                        profile["birth_date"] = birth
                    if player.get("nationality"):
                        profile["nationality"] = player.get("nationality")
                    for entry in statistics:
                        position = ((entry.get("games") or {}).get("position"))
                        if position:
                            profile["position"] = position
                            break
                replace_season_ids.add(player_id)
                parsed_rows = _parse_seasons(
                    player_key=key,
                    player_id=player_id,
                    statistics=statistics,
                    season_year=year,
                    league_map=league_map,
                    ingested_at=now,
                )
                if parsed_rows:
                    season_rows.extend(parsed_rows)
                state_rows.append(
                    {
                        "player_id": player_id,
                        "stage": "profile",
                        "season_year": year,
                        "status": "complete" if parsed_rows else "no_data",
                        "attempts": int((previous or {}).get("attempts") or 0) + 1,
                        "last_error": None,
                        "checked_at": now,
                        "policy_version": policy,
                    }
                )
            except Exception as error:  # noqa: BLE001 - coverage, not a crash
                message = f"{key} {year}: {type(error).__name__}: {error}"
                errors.append(message)
                state_rows.append(
                    {
                        "player_id": player_id,
                        "stage": "profile",
                        "season_year": year,
                        "status": "error",
                        "attempts": int((previous or {}).get("attempts") or 0) + 1,
                        "last_error": message[:500],
                        "checked_at": now,
                        "policy_version": policy,
                    }
                )
            if api_football.network_requests() >= budget:
                budget_exhausted = True
                break
        previous_transfers = state.get((player_id, "transfers", 0))
        if (
            not force
            and previous_transfers
            and previous_transfers.get("policy_version") == policy
            and previous_transfers.get("status") in {"complete", "no_data"}
            and _fresh(previous_transfers.get("checked_at"), transfers_ttl)
        ):
            player_rows.append(profile)
            continue
        if api_football.network_requests() >= budget:
            budget_exhausted = True
            player_rows.append(profile)
            continue
        try:
            response = api_football.transfers(
                player_id=player_id,
                ttl_hours=transfers_ttl,
                force=force,
            )
            moves: list[dict[str, Any]] = []
            for entry in response:
                if isinstance(entry, dict) and isinstance(entry.get("transfers"), list):
                    moves.extend(entry["transfers"])
            replace_event_ids.add(player_id)
            parsed_events = _parse_events(
                player_key=key,
                player_id=player_id,
                transfers=moves,
                ingested_at=now,
            )
            event_rows.extend(parsed_events)
            state_rows.append(
                {
                    "player_id": player_id,
                    "stage": "transfers",
                    "season_year": 0,
                    "status": "complete" if parsed_events else "no_data",
                    "attempts": int((previous_transfers or {}).get("attempts") or 0) + 1,
                    "last_error": None,
                    "checked_at": now,
                    "policy_version": policy,
                }
            )
        except Exception as error:  # noqa: BLE001 - coverage, not a crash
            message = f"{key} transfers: {type(error).__name__}: {error}"
            errors.append(message)
            state_rows.append(
                {
                    "player_id": player_id,
                    "stage": "transfers",
                    "season_year": 0,
                    "status": "error",
                    "attempts": int((previous_transfers or {}).get("attempts") or 0) + 1,
                    "last_error": message[:500],
                    "checked_at": now,
                    "policy_version": policy,
                }
            )
        player_rows.append(profile)
    if dry_run:
        return IngestResult(
            source="former_players",
            status="dry_run",
            rows=len(universe),
            errors=[],
            details={"planned_requests": calls, "players": len(universe)},
        )
    # Replace rows only for players whose provider call succeeded. A skipped
    # TTL or an error keeps the previous local rows rather than erasing them.
    if replace_season_ids:
        existing_seasons = [
            row
            for row in existing_seasons
            if int(row.get("player_id") or -1) not in replace_season_ids
        ]
    if replace_event_ids:
        existing_events = [
            row
            for row in existing_events
            if int(row.get("player_id") or -1) not in replace_event_ids
        ]
    if replace_season_ids or replace_event_ids:
        touched = replace_season_ids | replace_event_ids
        for player_id in touched:
            for state_key in [key for key in state if key[0] == player_id]:
                state.pop(state_key, None)
    for row in state_rows:
        state[(int(row["player_id"]), str(row["stage"]), int(row["season_year"]))] = row
    all_players = {
        key: row for key, row in existing_players.items() if _api_id(key) not in processed_ids
    }
    all_players.update({str(row["player_key"]): row for row in player_rows})
    all_seasons = existing_seasons + season_rows
    all_events = existing_events + event_rows
    _write_rows(PLAYERS_PATH, list(all_players.values()), PLAYER_COLUMNS)
    _write_rows(SEASONS_PATH, all_seasons, SEASON_COLUMNS)
    _write_rows(EVENTS_PATH, all_events, EVENT_COLUMNS)
    _write_rows(STATE_PATH, list(state.values()), STATE_COLUMNS)
    profile_seasons = {
        (int(row["player_id"]), str(row["season"]))
        for row in all_seasons
        if row.get("player_id") is not None
        and row.get("season")
        and str(row.get("scope") or "league") == "league"
    }
    expected = 0
    for item in universe:
        player_id = _api_id(item["player_key"])
        if player_id is None:
            continue
        departure_year = season_start_year(str(item["departure"].get("season") or target_season))
        expected += len(seasons_between(_season_from_year(departure_year), target_season))
    present = len(profile_seasons)
    error_players = {
        int(row["player_id"])
        for row in state.values()
        if row.get("status") == "error" and int(row.get("season_year") or 0) != 0
    }
    transfer_histories = {
        int(row["player_id"])
        for row in state.values()
        if row.get("stage") == "transfers" and row.get("status") in {"complete", "no_data"}
    }
    current_present = len(
        {
            player_id
            for player_id, season in profile_seasons
            if season == target_season
        }
    )
    meta = {
        "schema_version": "1.0.0",
        "generated_at": now,
        "season": target_season,
        "policy_version": policy,
        "players_total": len(universe),
        "players_with_api_id": len(processed_ids),
        "players_without_api_id": len(no_api),
        "players_backfilled": len(processed_ids),
        "players_no_api_id": len(no_api),
        "players_error": len(error_players),
        "player_seasons_expected": expected,
        "player_seasons_present": present,
        "player_seasons_missing": max(0, expected - present),
        "transfer_histories_present": len(transfer_histories),
        "current_season_present": current_present,
        "network_requests": api_football.network_requests(),
        "budget": budget,
        "budget_exhausted": budget_exhausted,
        "errors": errors[:50],
        "note": (
            "Provider seasons after departure; missing seasons are gaps, not zero. "
            "No provider fee-like text is stored or published."
        ),
    }
    _write_meta(meta)
    status = "partial" if errors or budget_exhausted else "ok"
    return IngestResult(
        source="former_players",
        status=status,
        rows=len(universe),
        errors=errors[:20],
        details=meta,
    )


__all__ = [
    "EVENTS_PATH",
    "META_PATH",
    "PLAYERS_PATH",
    "SEASONS_PATH",
    "ingest_former_players",
    "load_former_meta",
    "load_former_players",
    "load_post_seasons",
    "load_transfer_events",
]
