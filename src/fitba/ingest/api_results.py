"""Current-season league results from API-Football.

football-data.co.uk is the primary league result feed, but it can lag a
matchday. The SPFL club feed closes that gap for Aberdeen only. This ingest
stores the complete provider fixture list for every SPFL tier so the canonical
layer can fill the other clubs' missing results and every league table and form
string has a justified input.

The stored rows are a fallback, not an override: an existing football-data
result is kept, and the official SPFL result still wins for Aberdeen.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import polars as pl

from fitba.normalize.results import MATCH_COLUMNS, ensure_match_columns
from fitba.normalize.teams import TeamRegistry, UnknownTeamError
from fitba.settings import NORMALIZED_DIR, ensure_dirs
from fitba.settings import competitions as competitions_config
from fitba.sources import api_football
from fitba.sources.base import IngestResult
from fitba.util.dates import season_start_year, utc_now_iso

LONDON = ZoneInfo("Europe/London")
PLAYED_STATUSES = {"FT", "AET", "PEN"}

RESULT_COLUMNS = [
    "match_id",
    "competition_id",
    "competition_name",
    "season",
    "division",
    "date",
    "kickoff",
    "phase",
    "home_team_id",
    "home_team_name",
    "away_team_id",
    "away_team_name",
    "home_goals",
    "away_goals",
    "result",
    "source_id",
    "ingested_at",
    "status",
    "result_source",
    "stats_source",
]


def results_path(season: str) -> Path:
    return NORMALIZED_DIR / "api_results" / f"season={season}" / "league_results.parquet"


def _local_date(value: Any) -> tuple[str | None, str | None]:
    if not isinstance(value, str) or not value:
        return None, None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None, None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    local = parsed.astimezone(LONDON)
    return local.date().isoformat(), local.strftime("%H:%M")


def _result(home: int, away: int) -> str:
    return "H" if home > away else "A" if home < away else "D"


def ingest_api_results(
    season: str,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> IngestResult:
    """Fetch and persist the complete provider fixture list for every league."""
    ensure_dirs()
    registry = TeamRegistry()
    year = season_start_year(season)
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    unresolved: set[str] = set()
    fetched = 0

    for competition in competitions_config()["competitions"]:
        league_id = competition.get("api_football_id")
        if league_id is None:
            continue
        try:
            items = api_football.fixtures(
                int(league_id),
                season=year,
                ttl_hours=1,
                force=force,
            )
        except Exception as error:  # noqa: BLE001 - report per league
            failures.append(f"{competition['id']}: {error}")
            continue
        fetched += len(items)
        for item in items:
            fixture = item.get("fixture") or {}
            status = fixture.get("status") or {}
            if str(status.get("short") or "") not in PLAYED_STATUSES:
                continue
            goals = item.get("goals") or {}
            home_goals = goals.get("home")
            away_goals = goals.get("away")
            if home_goals is None or away_goals is None:
                continue
            teams = item.get("teams") or {}
            home_name = str((teams.get("home") or {}).get("name") or "")
            away_name = str((teams.get("away") or {}).get("name") or "")
            try:
                home_id = registry.resolve_or_raise(home_name)
                away_id = registry.resolve_or_raise(away_name)
            except UnknownTeamError:
                unresolved.add(home_name or away_name)
                continue
            match_date, kickoff = _local_date(fixture.get("date"))
            if match_date is None:
                continue
            rows.append(
                {
                    "match_id": f"api:fixture:{fixture.get('id')}",
                    "competition_id": competition["id"],
                    "competition_name": competition["name"],
                    "season": season,
                    "division": competition["code"],
                    "date": match_date,
                    "kickoff": kickoff,
                    "phase": "regular",
                    "home_team_id": home_id,
                    "home_team_name": registry.canonical_name(home_id),
                    "away_team_id": away_id,
                    "away_team_name": registry.canonical_name(away_id),
                    "home_goals": int(home_goals),
                    "away_goals": int(away_goals),
                    "result": _result(int(home_goals), int(away_goals)),
                    "source_id": "api_football",
                    "ingested_at": utc_now_iso(),
                    "status": "played",
                    "result_source": "api_football",
                    "stats_source": None,
                }
            )

    path = results_path(season)
    if dry_run:
        return IngestResult(
            source="api_football",
            status="ok" if not failures else "error",
            rows=len(rows),
            path=str(path),
            errors=failures,
            unresolved=sorted(unresolved),
            details={"fetched": fetched, "played": len(rows), "dry_run": True},
        )

    if rows:
        frame = ensure_match_columns(pl.DataFrame(rows, infer_schema_length=None))
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.select([column for column in MATCH_COLUMNS if column in frame.columns]).write_parquet(
            path
        )
        combined = NORMALIZED_DIR / "api_results" / "league_results.parquet"
        frame.select(
            [column for column in MATCH_COLUMNS if column in frame.columns]
        ).write_parquet(combined)
    meta = {
        "season": season,
        "generated_at": utc_now_iso(),
        "fetched": fetched,
        "played": len(rows),
        "unresolved": sorted(unresolved),
        "errors": failures,
        "source": "api_football",
    }
    meta_path = NORMALIZED_DIR / "api_results" / "meta.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    return IngestResult(
        source="api_football",
        status="ok" if not failures else "error",
        rows=len(rows),
        path=str(path),
        errors=failures,
        unresolved=sorted(unresolved),
        details={"fetched": fetched, "played": len(rows), "meta": str(meta_path)},
    )


def load_api_results(season: str) -> pl.DataFrame:
    path = results_path(season)
    if not path.exists():
        return pl.DataFrame({column: [] for column in MATCH_COLUMNS})
    return pl.read_parquet(path)


__all__ = ["RESULT_COLUMNS", "ingest_api_results", "load_api_results", "results_path"]
