"""European league-phase player appearances for the scouting pool.

The domestic ``/players`` season endpoint mixes qualifiers and the league phase
and has no round dimension. This ingest uses the league-phase fixtures and the
per-fixture player endpoint, so "played in the league phase" means exactly that.

Only the three UEFA competitions are covered. The output is a positive-only
table; a player not found is ``none`` only when the run is complete, otherwise
``unknown``. No raw provider payload is published.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

import polars as pl

from fitba.settings import NORMALIZED_DIR, ensure_dirs
from fitba.sources import api_football
from fitba.util.dates import current_season, utc_now_iso

EUROPE_DIR = NORMALIZED_DIR / "scouting"
EUROPE_PATH = EUROPE_DIR / "europe_appearances.parquet"
EUROPE_META_PATH = EUROPE_DIR / "europe_meta.json"
EUROPEAN_LEAGUES = {
    2: ("uefa:champions-league", "UEFA Champions League"),
    3: ("uefa:europa-league", "UEFA Europa League"),
    848: ("uefa:conference-league", "UEFA Conference League"),
}
PLAYED_STATUSES = {"FT", "AET", "PEN"}
EUROPE_COLUMNS = [
    "player_id",
    "player_key",
    "player_name",
    "team_id",
    "team_name",
    "competition_id",
    "competition",
    "league_phase",
    "minutes",
    "appearances",
    "rating",
    "fixtures",
    "ingested_at",
]


def season_year(season: str) -> int:
    try:
        return int(str(season).split("-", 1)[0])
    except ValueError:
        return api_football.CURRENT_SEASON


def is_league_phase(round_name: Any) -> bool:
    return str(round_name or "").strip().casefold().startswith("league stage")


def _played(fixture: dict[str, Any]) -> bool:
    status = (fixture.get("fixture") or {}).get("status") or {}
    return str(status.get("short") or "") in PLAYED_STATUSES


def _fixture_players(
    fixture: dict[str, Any],
    *,
    competition_id: str,
    competition: str,
    refresh: bool,
) -> list[dict[str, Any]]:
    fixture_id = (fixture.get("fixture") or {}).get("id")
    if fixture_id is None:
        return []
    rows: list[dict[str, Any]] = []
    for team in api_football.fixtures_players(int(fixture_id), ttl_hours=720, force=refresh):
        team_info = team.get("team") or {}
        for entry in team.get("players") or []:
            player = entry.get("player") or {}
            stats = (entry.get("statistics") or [{}])[0]
            games = stats.get("games") or {}
            minutes = games.get("minutes")
            if minutes is None or int(minutes) <= 0:
                continue
            rating = games.get("rating")
            try:
                rating_value = float(str(rating)) if rating not in (None, "") else None
            except (TypeError, ValueError):
                rating_value = None
            player_id = player.get("id")
            if player_id is None:
                continue
            rows.append(
                {
                    "player_id": int(player_id),
                    "player_key": f"api:player:{player_id}",
                    "player_name": str(player.get("name") or ""),
                    "team_id": team_info.get("id"),
                    "team_name": str(team_info.get("name") or ""),
                    "competition_id": competition_id,
                    "competition": competition,
                    "league_phase": True,
                    "minutes": int(minutes),
                    "appearances": 1,
                    "rating": rating_value,
                }
            )
    return rows


def _aggregate(rows: list[dict[str, Any]], ingested_at: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(int(row["player_id"]), str(row["competition_id"]))].append(row)
    output: list[dict[str, Any]] = []
    for (player_id, competition_id), items in grouped.items():
        minutes = sum(int(item["minutes"]) for item in items)
        rated = [item for item in items if item.get("rating") is not None]
        rating = (
            round(
                sum(float(item["rating"]) * int(item["minutes"]) for item in rated)
                / max(1, sum(int(item["minutes"]) for item in rated)),
                2,
            )
            if rated
            else None
        )
        first = items[0]
        output.append(
            {
                "player_id": player_id,
                "player_key": first["player_key"],
                "player_name": first["player_name"],
                "team_id": first.get("team_id"),
                "team_name": first.get("team_name"),
                "competition_id": competition_id,
                "competition": first["competition"],
                "league_phase": True,
                "minutes": minutes,
                "appearances": len(items),
                "rating": rating,
                "fixtures": len(items),
                "ingested_at": ingested_at,
            }
        )
    return output


def ingest_europe(
    *,
    season: str | None = None,
    budget: int = 2000,
    refresh: bool = False,
) -> dict[str, Any]:
    ensure_dirs()
    EUROPE_DIR.mkdir(parents=True, exist_ok=True)
    season_label = season or current_season()
    year = season_year(season_label)
    generated_at = utc_now_iso()
    all_rows: list[dict[str, Any]] = []
    competitions: list[dict[str, Any]] = []
    stopped = False
    for league_id, (competition_id, competition) in EUROPEAN_LEAGUES.items():
        record: dict[str, Any] = {
            "competition_id": competition_id,
            "competition": competition,
            "provider_league_id": league_id,
            "fixtures_total": 0,
            "league_phase": 0,
            "played": 0,
            "fetched": 0,
            "missing": 0,
            "players": 0,
            "error": None,
        }
        try:
            payload = api_football.request_payload(
                "/fixtures",
                ttl_hours=6,
                force=refresh,
                league=league_id,
                season=year,
            )
            fixtures = list(payload.get("response") or [])
            record["fixtures_total"] = len(fixtures)
            phase = [
                item
                for item in fixtures
                if is_league_phase((item.get("league") or {}).get("round"))
            ]
            record["league_phase"] = len(phase)
            played = [item for item in phase if _played(item)]
            record["played"] = len(played)
            for fixture in played:
                if stopped or api_football.network_requests() >= budget:
                    stopped = True
                    break
                try:
                    rows = _fixture_players(
                        fixture,
                        competition_id=competition_id,
                        competition=competition,
                        refresh=refresh,
                    )
                except Exception:  # noqa: BLE001 - coverage, not a crash
                    record["missing"] += 1
                    continue
                if not rows:
                    record["missing"] += 1
                record["fetched"] += 1
                all_rows.extend(rows)
            record["players"] = len(
                {row["player_id"] for row in all_rows if row["competition_id"] == competition_id}
            )
            record["complete"] = record["fetched"] >= record["played"] and record["missing"] == 0
        except Exception as error:  # noqa: BLE001
            record["error"] = f"{type(error).__name__}: {error}"
            record["complete"] = False
        competitions.append(record)
        if stopped:
            break

    aggregated = _aggregate(all_rows, generated_at)
    frame = pl.DataFrame(aggregated, infer_schema_length=None) if aggregated else pl.DataFrame()
    for column in EUROPE_COLUMNS:
        if column not in frame.columns:
            frame = frame.with_columns(pl.lit(None).alias(column))
    if frame.height:
        frame = frame.select(EUROPE_COLUMNS)
    frame.write_parquet(EUROPE_PATH)
    complete = all(item.get("complete") for item in competitions) and len(competitions) == len(
        EUROPEAN_LEAGUES
    )
    meta = {
        "schema_version": "1.0.0",
        "season": season_label,
        "generated_at": generated_at,
        "coverage_complete": bool(complete),
        "competitions": competitions,
        "players": frame.height,
        "requests": api_football.network_requests(),
        "budget": budget,
        "stopped_on_budget": stopped,
    }
    EUROPE_META_PATH.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def load_europe_meta() -> dict[str, Any]:
    if not EUROPE_META_PATH.exists():
        return {}
    return json.loads(EUROPE_META_PATH.read_text(encoding="utf-8"))


def load_europe_appearances() -> pl.DataFrame:
    if not EUROPE_PATH.exists():
        return pl.DataFrame()
    return pl.read_parquet(EUROPE_PATH)


__all__ = [
    "EUROPEAN_LEAGUES",
    "EUROPE_META_PATH",
    "EUROPE_PATH",
    "ingest_europe",
    "is_league_phase",
    "load_europe_appearances",
    "load_europe_meta",
    "season_year",
]
