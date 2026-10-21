"""Publish derived JSON for the web app.

Atomic: write a temp directory, validate the file sizes, then replace the live
directory. The manifest is written last. Raw/source-shaped feeds never enter
this directory.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import orjson
import polars as pl

from fitba.analytics.tables import build_tables
from fitba.ingest.runner import load_matches
from fitba.settings import (
    WEB_DATA_DIR,
    ensure_dirs,
    source_registry,
)
from fitba.settings import (
    aberdeen as aberdeen_config,
)
from fitba.settings import (
    competitions as competitions_config,
)
from fitba.util.dates import current_season, utc_now_iso

SCHEMA_VERSION = "1.0.0"
MAX_FILE_BYTES = 2_000_000


@dataclass(slots=True)
class PublishReport:
    out: str
    season: str
    files: int
    bytes: int
    dataset_version: str
    manifest: dict[str, Any] = field(default_factory=dict)


def _dumps(payload: Any) -> bytes:
    return orjson.dumps(payload, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS, default=str)


def _write(path: Path, payload: Any) -> dict[str, Any]:
    data = _dumps(payload)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"{path} is {len(data)} bytes, over the {MAX_FILE_BYTES} cap")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "path": str(path),
        "bytes": len(data),
        "checksum": "sha256:" + hashlib.sha256(data).hexdigest(),
    }


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return "nogit"


def _competition_slug(competition_id: str) -> str:
    return competition_id.split(":", 1)[-1]


def _table_payload(table: pl.DataFrame, competition: dict[str, Any], season: str) -> dict[str, Any]:
    return {
        "competition_id": competition["id"],
        "competition_name": competition["name"],
        "short_name": competition["short_name"],
        "tier": competition["tier"],
        "season": season,
        "rows": table.to_dicts(),
    }


def _aberdeen_payload(
    matches: pl.DataFrame,
    tables_by_season: dict[str, dict[str, pl.DataFrame]],
    season: str,
) -> dict[str, Any]:
    club_id = str(aberdeen_config()["club_id"])
    club_matches = matches.filter(
        (pl.col("home_team_id") == club_id) | (pl.col("away_team_id") == club_id)
    ).sort("date", descending=True)

    def result_row(row: dict[str, Any]) -> dict[str, Any]:
        is_home = row["home_team_id"] == club_id
        goals_for = row["home_goals"] if is_home else row["away_goals"]
        goals_against = row["away_goals"] if is_home else row["home_goals"]
        return {
            "match_id": row["match_id"],
            "date": row["date"],
            "competition_id": row["competition_id"],
            "opponent_id": row["away_team_id"] if is_home else row["home_team_id"],
            "opponent_name": row["away_team_name"] if is_home else row["home_team_name"],
            "venue": "H" if is_home else "A",
            "goals_for": goals_for,
            "goals_against": goals_against,
            "result": "W"
            if goals_for > goals_against
            else "D"
            if goals_for == goals_against
            else "L",
        }

    results = [result_row(row) for row in club_matches.to_dicts()]
    current_table = tables_by_season.get(season, {}).get("sco:premiership")
    table_row = None
    if current_table is not None and current_table.height:
        rows = current_table.filter(pl.col("team_id") == club_id)
        table_row = rows.to_dicts()[0] if rows.height else None

    history = []
    for history_season in sorted(tables_by_season, reverse=True):
        table = tables_by_season[history_season].get("sco:premiership")
        if table is None or not table.height:
            continue
        rows = table.filter(pl.col("team_id") == club_id)
        if rows.height:
            row = rows.to_dicts()[0]
            history.append(
                {
                    "season": history_season,
                    "position": row["position"],
                    "played": row["played"],
                    "points": row["points"],
                    "gd": row["gd"],
                    "form": row["form"],
                }
            )

    summary = None
    if table_row:
        summary = {
            key: table_row[key]
            for key in (
                "position",
                "played",
                "won",
                "drawn",
                "lost",
                "gf",
                "ga",
                "gd",
                "points",
                "form",
            )
        }

    return {
        "club_id": club_id,
        "name": aberdeen_config()["name"],
        "profile": {
            key: aberdeen_config().get(key)
            for key in ("nickname", "stadium", "city", "founded", "colours")
        },
        "budget": aberdeen_config().get("budget"),
        "squad_needs": aberdeen_config().get("squad_needs"),
        "style_intent": aberdeen_config().get("style_intent"),
        "season": season,
        "summary": summary,
        "results": results,
        "history": history,
        "coverage": "match",
        "notes": "Results and table data from football-data.co.uk; player/event layers pending.",
    }


def publish(
    *,
    season: str | None = None,
    out: Path | None = None,
    profile: str = "public",
) -> PublishReport:
    ensure_dirs()
    target = out or WEB_DATA_DIR
    all_matches = load_matches(None)
    seasons = sorted(all_matches["season"].unique().to_list())
    target_season = season or current_season()
    if target_season not in seasons:
        target_season = seasons[-1]
    matches = all_matches.filter(pl.col("season") == target_season)

    tables_by_season: dict[str, dict[str, pl.DataFrame]] = {
        current: build_tables(all_matches, season=current, config=competitions_config())
        for current in seasons
    }
    tables = tables_by_season[target_season]
    generated_at = utc_now_iso()
    dataset_version = f"{generated_at}-{_git_sha()}"

    temp = target.with_name(target.name + ".tmp")
    if temp.exists():
        shutil.rmtree(temp)
    temp.mkdir(parents=True, exist_ok=True)

    written: list[dict[str, Any]] = []
    marts: list[dict[str, Any]] = []
    for competition in competitions_config()["competitions"]:
        competition_id = competition["id"]
        table = tables.get(competition_id)
        if table is None or not table.height:
            continue
        slug = _competition_slug(competition_id)
        path = temp / "tables" / f"{slug}-{target_season}.json"
        info = _write(path, _table_payload(table, competition, target_season))
        written.append(info)
        marts.append(
            {
                "id": f"league_table.{competition_id}",
                "path": str(path.relative_to(temp)),
                "rows": table.height,
                "checksum": info["checksum"],
                "season": target_season,
            }
        )

    club_payload = _aberdeen_payload(matches, tables_by_season, target_season)
    club_info = _write(temp / "clubs" / "aberdeen.json", club_payload)
    written.append(club_info)
    marts.append(
        {
            "id": "club.sco:aberdeen",
            "path": "clubs/aberdeen.json",
            "rows": len(club_payload["results"]),
            "checksum": club_info["checksum"],
            "season": target_season,
        }
    )

    team_ids = sorted(
        set(matches["home_team_id"].drop_nulls().to_list())
        | set(matches["away_team_id"].drop_nulls().to_list())
    )
    team_names = {
        row["team_id"]: row["team_name"]
        for row in matches.select(
            pl.col("home_team_id").alias("team_id"),
            pl.col("home_team_name").alias("team_name"),
        )
        .unique()
        .to_dicts()
    }
    team_names.update(
        {
            row["team_id"]: row["team_name"]
            for row in matches.select(
                pl.col("away_team_id").alias("team_id"),
                pl.col("away_team_name").alias("team_name"),
            )
            .unique()
            .to_dicts()
        }
    )
    search = [
        {
            "type": "club",
            "id": team_id,
            "name": team_names.get(team_id, team_id),
            "slug": team_id.split(":", 1)[-1],
        }
        for team_id in team_ids
        if not team_id.startswith("sco:provisional")
    ]
    written.append(_write(temp / "search-index.json", search))

    coverage = {
        "season": target_season,
        "competitions": [
            {
                "id": competition["id"],
                "name": competition["name"],
                "matches": int(
                    matches.filter(
                        (pl.col("competition_id") == competition["id"])
                        & (pl.col("season") == target_season)
                        & pl.col("home_goals").is_not_null()
                    ).height
                ),
                "expected_matches": competition["matches_per_season"],
                "coverage": "match",
                "events": 0,
                "player_stats": 0,
            }
            for competition in competitions_config()["competitions"]
        ],
    }
    written.append(_write(temp / "coverage.json", coverage))
    written.append(_write(temp / "seasons.json", {"seasons": seasons, "current": target_season}))

    sources = []
    for source_id, source in source_registry()["sources"].items():
        if source_id != "football_data_uk":
            continue
        sources.append(
            {
                "id": source_id,
                "name": source["name"],
                "lane": source["lane"],
                "status": "ok",
                "rows": matches.height,
                "last_verified": source.get("last_verified"),
                "attribution": source.get("attribution"),
            }
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset_version": dataset_version,
        "generated_at": generated_at,
        "season": target_season,
        "profile": profile,
        "sources": sources,
        "marts": marts,
        "validation": {"status": "not_run"},
        "coverage": coverage,
        "files": [
            {
                "path": str(Path(info["path"]).relative_to(temp)),
                "bytes": info["bytes"],
                "checksum": info["checksum"],
            }
            for info in written
        ],
    }
    manifest_info = _write(temp / "manifest.json", manifest)
    written.append(manifest_info)

    # Atomic replace. Restore the previous directory if the rename fails.
    old = target.with_name(target.name + ".old")
    if old.exists():
        shutil.rmtree(old)
    if target.exists():
        target.rename(old)
    try:
        temp.rename(target)
    except Exception:
        if old.exists() and not target.exists():
            old.rename(target)
        raise
    if old.exists():
        shutil.rmtree(old)

    total_bytes = sum(int(info["bytes"]) for info in written)
    return PublishReport(
        out=str(target),
        season=target_season,
        files=len(written),
        bytes=total_bytes,
        dataset_version=dataset_version,
        manifest=manifest,
    )
