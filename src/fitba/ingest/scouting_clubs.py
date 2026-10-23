"""Current-club resolution for the scouting pool.

The domestic ``/players?league=`` row names the club where the player produced
his season statistics, not necessarily where he plays now. This ingest reads the
provider transfer feed for every team represented in the pool and keeps each
player's latest recorded move on or before the snapshot date.

It is deliberately labelled: a player with no later transfer keeps the stats
club with ``source: stats_snapshot``; a later move is ``source: transfer_feed``.
The feed can miss a subsequent move that does not involve a pool team, so the
page says "current club from the provider transfer feed".
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import polars as pl

from fitba.ingest.scouting import PLAYER_SEASON_PATH
from fitba.settings import NORMALIZED_DIR, ensure_dirs
from fitba.sources import api_football
from fitba.util.dates import utc_now_iso

SCOUTING_DIR = NORMALIZED_DIR / "scouting"
CURRENT_CLUBS_PATH = SCOUTING_DIR / "current_clubs.parquet"
CURRENT_CLUBS_META_PATH = SCOUTING_DIR / "current_clubs_meta.json"
CURRENT_CLUB_COLUMNS = [
    "player_id",
    "player_name",
    "current_team_id",
    "current_team_name",
    "current_league_id",
    "current_league_name",
    "previous_team_id",
    "previous_team_name",
    "transfer_date",
    "transfer_type",
    "status",
    "ingested_at",
]
FREE_AGENT_NAMES = {"without club", "free agent", "free agents"}
RETIRED_NAMES = {"retired"}


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _status_for(transfer: dict[str, Any], current_name: str) -> str:
    name = current_name.strip().casefold()
    if name in RETIRED_NAMES:
        return "retired"
    if name in FREE_AGENT_NAMES:
        return "free_agent"
    transfer_type = str(transfer.get("type") or "").casefold()
    if "back from loan" in transfer_type or "loan end" in transfer_type:
        return "transferred"
    if "loan" in transfer_type:
        return "loan"
    return "transferred"


def latest_transfer(transfers: list[dict[str, Any]], *, today: date) -> dict[str, Any] | None:
    """Return the latest transfer on or before today, or None."""
    candidates: list[tuple[date, dict[str, Any]]] = []
    for transfer in transfers:
        moved = _parse_date(transfer.get("date"))
        if moved is None or moved > today:
            continue
        candidates.append((moved, transfer))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def load_pool_teams() -> dict[int, dict[str, Any]]:
    if not PLAYER_SEASON_PATH.exists():
        return {}
    frame = pl.read_parquet(PLAYER_SEASON_PATH).select(
        ["team_id", "team_name", "competition_id", "competition"]
    )
    teams: dict[int, dict[str, Any]] = {}
    for row in frame.unique(subset=["team_id"]).to_dicts():
        team_id = row.get("team_id")
        if team_id is None:
            continue
        teams[int(team_id)] = {
            "team_name": row.get("team_name"),
            "competition_id": row.get("competition_id"),
            "competition": row.get("competition"),
        }
    return teams


def ingest_current_clubs(
    *, budget: int = 1000, refresh: bool = False, today: date | None = None
) -> dict[str, Any]:
    ensure_dirs()
    SCOUTING_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = today or date.today()
    generated_at = utc_now_iso()
    teams = load_pool_teams()
    pool_by_id = teams
    latest_by_player: dict[int, dict[str, Any]] = {}
    errors: list[str] = []
    fetched = 0
    for team_id in sorted(teams):
        if api_football.network_requests() >= budget:
            break
        try:
            payload = api_football.request_payload(
                "/transfers",
                ttl_hours=24,
                force=refresh,
                team=team_id,
            )
            fetched += 1
        except Exception as error:  # noqa: BLE001 - coverage, not a crash
            errors.append(f"{team_id}: {type(error).__name__}: {error}")
            continue
        for entry in payload.get("response") or []:
            player = entry.get("player") or {}
            player_id = player.get("id")
            if player_id is None:
                continue
            transfer = latest_transfer(entry.get("transfers") or [], today=snapshot)
            if transfer is None:
                continue
            current = latest_by_player.get(int(player_id))
            current_date = _parse_date((current or {}).get("date"))
            transfer_date = _parse_date(transfer.get("date"))
            if current is None or (
                transfer_date is not None and (current_date is None or transfer_date > current_date)
            ):
                latest_by_player[int(player_id)] = {
                    "player_name": player.get("name"),
                    "date": transfer.get("date"),
                    "type": transfer.get("type"),
                    "teams": transfer.get("teams") or {},
                }
    pool_ids: set[int] = set()
    if PLAYER_SEASON_PATH.exists():
        pool_ids = {
            int(value)
            for value in pl.read_parquet(PLAYER_SEASON_PATH)["player_id"].unique().to_list()
            if value is not None
        }
    rows: list[dict[str, Any]] = []
    for player_id, item in latest_by_player.items():
        teams_block = item.get("teams") or {}
        incoming = teams_block.get("in") or {}
        outgoing = teams_block.get("out") or {}
        current_id = incoming.get("id")
        current_name = str(incoming.get("name") or "")
        pool_team = pool_by_id.get(int(current_id)) if current_id is not None else None
        rows.append(
            {
                "player_id": player_id,
                "player_name": item.get("player_name"),
                "current_team_id": current_id,
                "current_team_name": current_name or "Unknown club",
                "current_league_id": (pool_team or {}).get("competition_id"),
                "current_league_name": (pool_team or {}).get("competition"),
                "previous_team_id": outgoing.get("id"),
                "previous_team_name": outgoing.get("name"),
                "transfer_date": item.get("date"),
                "transfer_type": item.get("type"),
                "status": _status_for(item, current_name),
                "ingested_at": generated_at,
            }
        )
    frame = pl.DataFrame(rows, infer_schema_length=None) if rows else pl.DataFrame()
    for column in CURRENT_CLUB_COLUMNS:
        if column not in frame.columns:
            frame = frame.with_columns(pl.lit(None).alias(column))
    if frame.height:
        frame = frame.select(CURRENT_CLUB_COLUMNS)
    frame.write_parquet(CURRENT_CLUBS_PATH)
    meta = {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "snapshot_date": snapshot.isoformat(),
        "teams_total": len(teams),
        "teams_fetched": fetched,
        "players": len(pool_ids & {int(row["player_id"]) for row in rows}),
        "transfer_players": frame.height,
        "requests": api_football.network_requests(),
        "budget": budget,
        "errors": errors[:50],
        "note": (
            "Current club from the provider transfer feed for pool teams. A player "
            "without a later transfer keeps the stats club with source stats_snapshot. "
            "A subsequent move that does not involve a pool team may be missing."
        ),
    }
    CURRENT_CLUBS_META_PATH.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def load_current_clubs() -> pl.DataFrame:
    if not CURRENT_CLUBS_PATH.exists():
        return pl.DataFrame()
    return pl.read_parquet(CURRENT_CLUBS_PATH)


def load_current_clubs_meta() -> dict[str, Any]:
    if not CURRENT_CLUBS_META_PATH.exists():
        return {}
    return json.loads(CURRENT_CLUBS_META_PATH.read_text(encoding="utf-8"))


__all__ = [
    "CURRENT_CLUBS_META_PATH",
    "CURRENT_CLUBS_PATH",
    "ingest_current_clubs",
    "latest_transfer",
    "load_current_clubs",
    "load_current_clubs_meta",
    "load_pool_teams",
]
