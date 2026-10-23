"""League standings for the scouting team-context lens.

One `/standings` request per enabled scouting league. The provider returns one
or more groups; we choose the group with the most played rounds (the current
table) and keep every team once. Coverage is explicit: a league without
standings is unknown, not a zero-strength team.
"""

from __future__ import annotations

import json
from typing import Any

import polars as pl

from fitba.settings import NORMALIZED_DIR, ensure_dirs, scouting_leagues
from fitba.sources import api_football
from fitba.util.dates import current_season, season_start_year, utc_now_iso

STANDINGS_PATH = NORMALIZED_DIR / "scouting" / "team_standings.parquet"
META_PATH = NORMALIZED_DIR / "scouting" / "team_standings_meta.json"

TEAM_COLUMNS = [
    "competition_id",
    "provider_league_id",
    "season",
    "team_id",
    "team_name",
    "rank",
    "points",
    "played",
    "goals_for",
    "goals_against",
    "goal_diff",
    "ppg",
    "group",
    "updated_at",
    "source_id",
    "ingested_at",
]


def _group(rows: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    groups = [group for group in rows if group]
    if not groups:
        return []
    return max(
        groups,
        key=lambda group: (
            max(int(row.get("all", {}).get("played") or 0) for row in group),
            len(group),
        ),
    )


def _rows_for(
    league: dict[str, Any], season: str, raw: list[dict[str, Any]], ingested_at: str
) -> list[dict[str, Any]]:
    provider_league_id = int((league.get("provider") or {}).get("api_football_id") or 0)
    league_payload = (raw[0].get("league") if raw else {}) or {}
    standings = league_payload.get("standings") or []
    chosen = _group(standings)
    out: list[dict[str, Any]] = []
    for row in chosen:
        team = row.get("team") or {}
        team_id = team.get("id")
        if team_id is None:
            continue
        played = int((row.get("all") or {}).get("played") or 0)
        points = int(row.get("points") or 0)
        goals = (row.get("all") or {}).get("goals") or {}
        out.append(
            {
                "competition_id": str(league.get("id") or ""),
                "provider_league_id": provider_league_id,
                "season": season,
                "team_id": int(team_id),
                "team_name": str(team.get("name") or ""),
                "rank": int(row.get("rank") or 0),
                "points": points,
                "played": played,
                "goals_for": int(goals.get("for") or 0),
                "goals_against": int(goals.get("against") or 0),
                "goal_diff": int(row.get("goalsDiff") or 0),
                "ppg": round(points / played, 3) if played else None,
                "group": str(row.get("group") or ""),
                "updated_at": str(row.get("update") or ""),
                "source_id": "api_football",
                "ingested_at": ingested_at,
            }
        )
    return out


def ingest_standings(*, season: str | None = None, refresh: bool = False) -> dict[str, Any]:
    ensure_dirs()
    target = season or current_season()
    season_year = season_start_year(target)
    ingested_at = utc_now_iso()
    leagues = [item for item in scouting_leagues().get("pool") or [] if item.get("enabled")]
    rows: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    requests = 0
    for league in leagues:
        provider_id = (league.get("provider") or {}).get("api_football_id")
        if provider_id is None:
            coverage.append(
                {
                    "id": league.get("id"),
                    "name": league.get("name"),
                    "status": "unknown",
                    "teams": 0,
                    "error": "no provider league id",
                }
            )
            continue
        try:
            raw = api_football.standings(int(provider_id), season_year, force=refresh)
            requests += 1
            league_rows = _rows_for(league, target, raw, ingested_at)
            if not league_rows:
                coverage.append(
                    {
                        "id": league.get("id"),
                        "name": league.get("name"),
                        "status": "no_standings",
                        "teams": 0,
                    }
                )
                continue
            rows.extend(league_rows)
            coverage.append(
                {
                    "id": league.get("id"),
                    "name": league.get("name"),
                    "status": "ok",
                    "teams": len(league_rows),
                    "group": league_rows[0].get("group"),
                    "played": max(row["played"] for row in league_rows),
                }
            )
        except Exception as error:  # noqa: BLE001 - coverage is published, not hidden
            coverage.append(
                {
                    "id": league.get("id"),
                    "name": league.get("name"),
                    "status": "error",
                    "teams": 0,
                    "error": str(error)[:240],
                }
            )
    meta = {
        "season": target,
        "generated_at": ingested_at,
        "leagues": coverage,
        "totals": {
            "leagues": len(coverage),
            "with_standings": sum(1 for item in coverage if item.get("status") == "ok"),
            "teams": len(rows),
            "requests": requests,
        },
        "note": (
            "League tables from the licensed provider. The group with the most played "
            "rounds is used; a league without a table is unknown, not zero-strength."
        ),
    }
    STANDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _frame(rows).write_parquet(STANDINGS_PATH)
    META_PATH.write_text(json.dumps(meta, indent=2, default=str) + "\n", encoding="utf-8")
    return meta


def _frame(rows: list[dict[str, Any]]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame({column: [] for column in TEAM_COLUMNS})
    return pl.DataFrame(rows).select(TEAM_COLUMNS)


def load_standings() -> pl.DataFrame:
    if not STANDINGS_PATH.exists():
        return pl.DataFrame({column: [] for column in TEAM_COLUMNS})
    try:
        return pl.read_parquet(STANDINGS_PATH).select(TEAM_COLUMNS)
    except (OSError, pl.exceptions.ComputeError):
        return pl.DataFrame({column: [] for column in TEAM_COLUMNS})


def load_standings_meta() -> dict[str, Any] | None:
    try:
        return json.loads(META_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


__all__ = [
    "STANDINGS_PATH",
    "TEAM_COLUMNS",
    "ingest_standings",
    "load_standings",
    "load_standings_meta",
]
