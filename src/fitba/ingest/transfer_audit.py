"""Fetch and cache the prior-season Aberdeen player snapshots used by the audit.

The transfer feed and the current squad cannot tell us who left. The
team-season endpoint includes players who have since departed, so two bounded
snapshots (2024-25 and 2025-26) give the audit a recall net. The snapshots are
fetched only by ``fitba transfers --audit`` and read locally by publish.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import polars as pl
import yaml

from fitba.ingest.transfers import published_transfers
from fitba.normalize.transfer_audit import build_transfer_audit
from fitba.settings import (
    NORMALIZED_DIR,
    REFERENCE_DIR,
    WEB_DATA_DIR,
    ensure_dirs,
)
from fitba.settings import (
    aberdeen as aberdeen_config,
)
from fitba.settings import (
    source_ids as source_ids_config,
)
from fitba.settings import (
    transfer_gaps as transfer_gaps_config,
)
from fitba.settings import (
    transfer_policy as transfer_policy_config,
)
from fitba.sources import api_football
from fitba.util.dates import utc_now_iso

PRIOR_SQUAD_COLUMNS = [
    "player_id",
    "player_name",
    "season",
    "team_id",
    "appearances",
    "starts",
    "minutes",
    "position",
    "age",
    "snapshot_at",
]


def prior_squads_path() -> Path:
    return NORMALIZED_DIR / "transfers" / "prior_squads.parquet"


def fetch_prior_squads(
    team_id: int, seasons: list[str], *, force: bool = False
) -> list[dict[str, Any]]:
    snapshot_at = utc_now_iso()
    rows: list[dict[str, Any]] = []
    for season in seasons:
        season_start = int(str(season)[:4])
        for item in api_football.players_by_team(team_id, season_start, force=force):
            player = item.get("player") or {}
            stats = [
                stat
                for stat in item.get("statistics", []) or []
                if int((stat.get("team") or {}).get("id") or 0) == team_id
            ]
            if not stats:
                continue
            games = [stat.get("games") or {} for stat in stats]
            position = next((game.get("position") for game in games if game.get("position")), None)
            rows.append(
                {
                    "player_id": int(player.get("id") or 0),
                    "player_name": str(player.get("name") or "Unknown player"),
                    "season": season,
                    "team_id": team_id,
                    "appearances": sum(int(game.get("appearences") or 0) for game in games),
                    "starts": sum(int(game.get("lineups") or 0) for game in games),
                    "minutes": sum(int(game.get("minutes") or 0) for game in games),
                    "position": position,
                    "age": player.get("age"),
                    "snapshot_at": snapshot_at,
                }
            )
    return rows


def write_prior_squads(rows: list[dict[str, Any]]) -> Path:
    path = prior_squads_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = (
        pl.DataFrame(
            [{column: row.get(column) for column in PRIOR_SQUAD_COLUMNS} for row in rows],
            infer_schema_length=200,
        )
        if rows
        else pl.DataFrame({column: [] for column in PRIOR_SQUAD_COLUMNS})
    )
    frame.select(PRIOR_SQUAD_COLUMNS).write_parquet(path)
    return path


def load_prior_squads() -> list[dict[str, Any]]:
    path = prior_squads_path()
    if not path.exists():
        return []
    frame = pl.read_parquet(path)
    return frame.to_dicts() if frame.height else []


def _load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def load_candidates() -> list[dict[str, Any]]:
    path = REFERENCE_DIR / "transfers.candidates.yaml"
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(payload.get("transfers", []))


def run_transfer_audit(*, force: bool = False) -> tuple[dict[str, Any], Path]:
    """Refresh the snapshots and write the generated audit document."""
    ensure_dirs()
    club_id = str(aberdeen_config()["club_id"])
    team_id = int(source_ids_config()["teams"][club_id]["api_football"])
    policy = transfer_policy_config() or {}
    audit_cfg = policy.get("audit") or {}
    seasons = [str(season) for season in audit_cfg.get("prior_seasons") or []]
    prior = fetch_prior_squads(team_id, seasons, force=force) if seasons else []
    write_prior_squads(prior)
    squad_payload = _load_json(WEB_DATA_DIR / "squad" / "aberdeen.json", {})
    gaps_payload = transfer_gaps_config() or {}
    audit = build_transfer_audit(
        players=list(squad_payload.get("players", [])),
        prior_seasons=prior,
        transfers=published_transfers(),
        candidates=load_candidates(),
        gaps=list(gaps_payload.get("gaps", [])),
        config=policy,
        generated_at=utc_now_iso(),
    )
    path = WEB_DATA_DIR / "transfers" / "aberdeen.audit.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit, path
