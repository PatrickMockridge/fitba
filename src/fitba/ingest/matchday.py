"""Bounded next-opponent snapshot for the matchday dashboard.

Only the next Aberdeen fixture is refreshed. The fetch is cache-first, capped
by request count and deliberately shallow: opponent fixtures, lineups and
events. Player ratings and possession are optional and are never required.
The daily publish reads the local snapshot and never imports this module's
network path.
"""

from __future__ import annotations

import json
import shutil
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import polars as pl

from fitba.ingest.fixtures import load_club_fixtures
from fitba.ingest.history import competition_id
from fitba.ingest.match_data import compute_match_data
from fitba.ingest.team_stats import parse_team_stats
from fitba.normalize.teams import TeamRegistry
from fitba.settings import NORMALIZED_DIR, ensure_dirs, source_ids
from fitba.settings import matchday as matchday_policy
from fitba.settings import roles as roles_config
from fitba.sources import api_football
from fitba.util.dates import season_start_year, utc_now_iso

MATCHDAY_DIR = NORMALIZED_DIR / "matchday"
PLAYED_STATUSES = {"FT", "AET", "PEN"}
SOURCE_ID = "api_football"
SCHEMA_VERSION = "1.0"

UPCOMING_COLUMNS = [
    "match_id",
    "competition_id",
    "competition_name",
    "stage",
    "season",
    "date",
    "kickoff",
    "home_team_id",
    "home_team_name",
    "away_team_id",
    "away_team_name",
    "venue",
    "opponent_id",
    "opponent_name",
    "status",
    "source_id",
    "ingested_at",
]

FIXTURE_COLUMNS = [
    "fixture_id",
    "date",
    "season",
    "competition_id",
    "competition_name",
    "round",
    "team_id",
    "team_name",
    "opponent_id",
    "opponent_name",
    "venue",
    "goals_for",
    "goals_against",
    "result",
    "status",
    "has_lineups",
    "has_events",
    "source_id",
    "ingested_at",
]

LINEUP_COLUMNS = [
    "fixture_id",
    "date",
    "season",
    "competition_id",
    "competition_name",
    "team_id",
    "team_name",
    "opponent_id",
    "opponent_name",
    "venue",
    "player_id",
    "player_key",
    "player_name",
    "shirt_number",
    "position",
    "started",
    "minutes",
    "role_code",
    "role_family",
    "role_status",
    "formation",
    "grid",
    "goals",
    "assists",
    "yellow_cards",
    "red_cards",
    "source_id",
    "ingested_at",
]

TEAM_SHAPE_COLUMNS = [
    "team_id",
    "team_name",
    "fixture_id",
    "date",
    "season",
    "competition_id",
    "competition_name",
    "opponent_id",
    "opponent_name",
    "venue",
    "formation",
    "formation_shape",
    "shape_family",
    "goals_for",
    "goals_against",
    "result",
    "source_id",
    "ingested_at",
]

PLAYER_FORM_COLUMNS = [
    "player_id",
    "player_key",
    "player_name",
    "shirt_number",
    "team_id",
    "team_name",
    "position",
    "appearances",
    "starts",
    "sub_apps",
    "minutes",
    "starts_last_5",
    "minutes_last_5",
    "goals",
    "assists",
    "last_seen",
    "primary_role_family",
    "role_codes",
    "source_id",
    "ingested_at",
]

TEAM_STAT_COLUMNS = [
    "fixture_id",
    "team_id",
    "team_name",
    "venue",
    "possession",
    "shots",
    "shots_on_target",
    "passes",
    "pass_accuracy",
    "corners",
    "fouls",
    "offsides",
    "yellow_cards",
    "red_cards",
    "saves",
    "source_id",
    "ingested_at",
]


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


def _frame(rows: list[dict[str, Any]], columns: list[str]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame({column: [] for column in columns})
    frame = pl.DataFrame(rows, infer_schema_length=None)
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        frame = frame.with_columns([pl.lit(None).alias(column) for column in missing])
    return frame.select(columns)


def _write_frame(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    _frame(rows, columns).write_parquet(path)


def _api_team_id(club_id: str, name: str | None = None) -> tuple[int | None, str]:
    mapping = (source_ids().get("teams") or {}).get(club_id) or {}
    value = mapping.get("api_football") if isinstance(mapping, dict) else mapping
    if value is not None:
        return int(value), "source_ids"
    if not name:
        return None, "missing"
    # One bounded search, only for an exact Scottish-name match. The result is
    # recorded as a warning and is never written back to the reference file.
    try:
        candidates = api_football.teams(search=name)
    except Exception:  # noqa: BLE001 - a provider failure means "not resolved"
        return None, "search_failed"
    matches = []
    for item in candidates:
        team = item.get("team") or {}
        if str(team.get("country") or "").casefold() != "scotland":
            continue
        if str(team.get("name") or "").casefold() == str(name).casefold():
            matches.append(item)
    if len(matches) == 1:
        return _int((matches[0].get("team") or {}).get("id")), "search"
    return None, "search_ambiguous" if matches else "search_not_found"


def _safe_date(value: Any) -> str:
    return str(value or "")[:10]


def _next_from_frame(
    frame: pl.DataFrame,
    *,
    club_id: str,
    today: date,
) -> dict[str, Any] | None:
    if frame.height == 0:
        return None
    rows = []
    for row in frame.to_dicts():
        if str(row.get("status") or "").casefold() not in {"scheduled", "upcoming", "tbd"}:
            continue
        if _safe_date(row.get("date")) < today.isoformat():
            continue
        home_id = row.get("home_team_id")
        away_id = row.get("away_team_id")
        if club_id not in {home_id, away_id}:
            continue
        venue = "H" if home_id == club_id else "A"
        opponent_id = away_id if venue == "H" else home_id
        opponent_name = row.get("away_team_name") if venue == "H" else row.get("home_team_name")
        rows.append(
            {
                "match_id": row.get("match_id"),
                "competition_id": row.get("competition_id"),
                "competition_name": row.get("competition_name"),
                "stage": row.get("stage") or row.get("round"),
                "season": row.get("season"),
                "date": _safe_date(row.get("date")),
                "kickoff": row.get("kickoff"),
                "home_team_id": home_id,
                "home_team_name": row.get("home_team_name"),
                "away_team_id": away_id,
                "away_team_name": row.get("away_team_name"),
                "venue": venue,
                "opponent_id": opponent_id,
                "opponent_name": opponent_name,
                "status": row.get("status"),
                "source_id": row.get("source_id")
                or (
                    "spfl" if str(row.get("match_id") or "").startswith("spfl") else "api_football"
                ),
                "ingested_at": row.get("ingested_at") or utc_now_iso(),
            }
        )
    if not rows:
        return None
    rows.sort(key=lambda item: (item["date"], str(item.get("kickoff") or "")))
    return rows[0]


def next_fixture(
    *,
    club_slug: str = "aberdeen",
    club_id: str = "sco:aberdeen",
    today: date | None = None,
) -> dict[str, Any] | None:
    """Earliest scheduled Aberdeen fixture, club feed first, cups second."""
    today = today or date.today()
    fixture = _next_from_frame(
        load_club_fixtures(club_slug),
        club_id=club_id,
        today=today,
    )
    if fixture:
        return fixture
    cups_dir = NORMALIZED_DIR / "cups"
    frames = []
    if cups_dir.exists():
        for path in sorted(cups_dir.glob("*.parquet")):
            frame = pl.read_parquet(path)
            if {"home_team_id", "away_team_id", "date"} <= set(frame.columns):
                frames.append(frame)
    if not frames:
        return None
    combined = pl.concat(frames, how="vertical_relaxed")
    return _next_from_frame(
        combined,
        club_id=club_id,
        today=today,
    )


def load_meta(out_dir: Path | None = None) -> dict[str, Any]:
    path = (out_dir or MATCHDAY_DIR) / "meta.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_snapshot(
    out_dir: Path,
    *,
    upcoming: list[dict[str, Any]],
    fixtures: list[dict[str, Any]],
    lineups: list[dict[str, Any]],
    shapes: list[dict[str, Any]],
    player_form: list[dict[str, Any]],
    team_stats: list[dict[str, Any]],
    meta: dict[str, Any],
) -> None:
    """Write the complete snapshot through a temp directory, meta last."""
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    temp = out_dir.with_name(f"{out_dir.name}.tmp")
    backup = out_dir.with_name(f"{out_dir.name}.bak")
    if temp.exists():
        shutil.rmtree(temp)
    temp.mkdir(parents=True)
    _write_frame(temp / "upcoming.parquet", upcoming, UPCOMING_COLUMNS)
    _write_frame(temp / "opponent_fixtures.parquet", fixtures, FIXTURE_COLUMNS)
    _write_frame(temp / "opponent_lineups.parquet", lineups, LINEUP_COLUMNS)
    _write_frame(temp / "opponent_team_shapes.parquet", shapes, TEAM_SHAPE_COLUMNS)
    _write_frame(temp / "opponent_player_form.parquet", player_form, PLAYER_FORM_COLUMNS)
    _write_frame(temp / "opponent_team_stats.parquet", team_stats, TEAM_STAT_COLUMNS)
    (temp / "meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if backup.exists():
        shutil.rmtree(backup)
    if out_dir.exists():
        out_dir.rename(backup)
    try:
        temp.rename(out_dir)
    except Exception:
        if backup.exists() and not out_dir.exists():
            backup.rename(out_dir)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def _empty_snapshot(
    out_dir: Path,
    *,
    fixture: dict[str, Any] | None,
    state: str,
    reason: str | None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    generated_at = utc_now_iso()
    meta = {
        "schema_version": SCHEMA_VERSION,
        "state": state,
        "reason": reason,
        "generated_at": generated_at,
        "club": "sco:aberdeen",
        "fixture": fixture,
        "opponent": None,
        "coverage": {},
        "api_requests": 0,
        "errors": [],
        "warnings": warnings or [],
    }
    _write_snapshot(
        out_dir,
        upcoming=[fixture] if fixture else [],
        fixtures=[],
        lineups=[],
        shapes=[],
        player_form=[],
        team_stats=[],
        meta=meta,
    )
    return meta


def _lineup_players(
    lineups: list[dict[str, Any]],
    *,
    team_id: int,
) -> dict[int, dict[str, Any]]:
    players: dict[int, dict[str, Any]] = {}
    for lineup in lineups:
        team = lineup.get("team") or {}
        if _int(team.get("id")) != team_id:
            continue
        for group in ("startXI", "substitutes"):
            for entry in lineup.get(group) or []:
                player = entry.get("player") or {}
                player_id = _int(player.get("id"))
                if player_id is None:
                    continue
                players[player_id] = {
                    "name": player.get("name"),
                    "shirt_number": _int(player.get("number")),
                    "position": player.get("pos"),
                }
    return players


def _event_totals(
    events: list[dict[str, Any]],
    *,
    fixture_id: int,
    team_id: int,
) -> dict[int, dict[str, int]]:
    totals: dict[int, dict[str, int]] = {}
    for event in events:
        team = event.get("team") or {}
        if _int(team.get("id")) != team_id:
            continue
        event_type = str(event.get("type") or "")
        detail = str(event.get("detail") or "")
        player = event.get("player") or {}
        player_id = _int(player.get("id"))
        if player_id is None:
            continue
        row = totals.setdefault(
            player_id,
            {"goals": 0, "assists": 0, "yellow_cards": 0, "red_cards": 0},
        )
        if (
            event_type == "Goal"
            and "missed penalty" not in detail.casefold()
            and "own goal" not in detail.casefold()
        ):
            row["goals"] += 1
        assist = event.get("assist") or {}
        assist_id = _int(assist.get("id"))
        if event_type == "Goal" and assist_id is not None and assist_id != player_id:
            totals.setdefault(
                assist_id,
                {"goals": 0, "assists": 0, "yellow_cards": 0, "red_cards": 0},
            )["assists"] += 1
        if event_type == "Card":
            if "red" in detail.casefold():
                row["red_cards"] += 1
            elif "yellow" in detail.casefold():
                row["yellow_cards"] += 1
    return totals


def _parse_team_stats(
    payload: list[dict[str, Any]],
    *,
    fixture_id: int,
    opponent_api_id: int,
    venue: str,
    ingested_at: str,
) -> list[dict[str, Any]]:
    rows = []
    for parsed in parse_team_stats(payload, fixture_id=fixture_id):
        if parsed["team_id"] != opponent_api_id:
            continue
        rows.append(
            {
                "fixture_id": fixture_id,
                "team_id": parsed["team_id"],
                "team_name": parsed["team_name"],
                "venue": venue,
                "possession": parsed["possession"],
                "shots": parsed["shots"],
                "shots_on_target": parsed["shots_on_target"],
                "passes": parsed["passes"],
                "pass_accuracy": parsed["passes_pct"],
                "corners": parsed["corners"],
                "fouls": parsed["fouls"],
                "offsides": parsed["offsides"],
                "yellow_cards": parsed["yellow_cards"],
                "red_cards": parsed["red_cards"],
                "saves": parsed["saves"],
                "source_id": SOURCE_ID,
                "ingested_at": ingested_at,
            }
        )
    return rows


def _player_form_rows(
    lineups: list[dict[str, Any]],
    *,
    team_id: int,
    ingested_at: str,
) -> list[dict[str, Any]]:
    if not lineups:
        return []
    fixtures = []
    for fixture_id in {str(row["fixture_id"]) for row in lineups}:
        rows = [row for row in lineups if str(row["fixture_id"]) == fixture_id]
        if rows:
            fixtures.append((str(rows[0].get("date") or ""), fixture_id))
    fixtures.sort(reverse=True)
    last_five = {fixture for _, fixture in fixtures[:5]}
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in lineups:
        grouped.setdefault(int(row["player_id"]), []).append(row)
    output = []
    for player_id, rows in grouped.items():
        rows.sort(key=lambda row: str(row.get("date") or ""), reverse=True)
        role_codes = Counter(str(row["role_code"]) for row in rows if row.get("role_code"))
        families = Counter(str(row["role_family"]) for row in rows if row.get("role_family"))
        first = rows[0]
        output.append(
            {
                "player_id": player_id,
                "player_key": first.get("player_key"),
                "player_name": first.get("player_name"),
                "shirt_number": first.get("shirt_number"),
                "team_id": team_id,
                "team_name": first.get("team_name"),
                "position": first.get("position"),
                "appearances": len(rows),
                "starts": sum(1 for row in rows if row.get("started")),
                "sub_apps": sum(1 for row in rows if not row.get("started")),
                "minutes": sum(int(row.get("minutes") or 0) for row in rows),
                "starts_last_5": sum(
                    1 for row in rows if row.get("started") and str(row["fixture_id"]) in last_five
                ),
                "minutes_last_5": sum(
                    int(row.get("minutes") or 0)
                    for row in rows
                    if str(row["fixture_id"]) in last_five
                ),
                "goals": sum(int(row.get("goals") or 0) for row in rows),
                "assists": sum(int(row.get("assists") or 0) for row in rows),
                "last_seen": first.get("date"),
                "primary_role_family": families.most_common(1)[0][0] if families else None,
                "role_codes": ",".join(sorted(role_codes)),
                "source_id": SOURCE_ID,
                "ingested_at": ingested_at,
            }
        )
    output.sort(key=lambda row: (-row["starts"], -row["minutes"], row["player_name"] or ""))
    return output


def _opponent_played_fixtures(
    payload: list[dict[str, Any]],
    *,
    opponent_api_id: int,
    limit: int,
) -> list[dict[str, Any]]:
    rows = []
    for item in payload:
        fixture = item.get("fixture") or {}
        status = str((fixture.get("status") or {}).get("short") or "")
        if status not in PLAYED_STATUSES:
            continue
        teams = item.get("teams") or {}
        home = teams.get("home") or {}
        away = teams.get("away") or {}
        home_id = _int(home.get("id"))
        away_id = _int(away.get("id"))
        if opponent_api_id not in {home_id, away_id}:
            continue
        goals = item.get("goals") or {}
        is_home = home_id == opponent_api_id
        rows.append(
            {
                "raw": item,
                "fixture_id": _int(fixture.get("id")),
                "date": str(fixture.get("date") or ""),
                "status": status,
                "competition_id": competition_id(item.get("league") or {}),
                "competition_name": str((item.get("league") or {}).get("name") or ""),
                "round": str((item.get("league") or {}).get("round") or ""),
                "venue": "H" if is_home else "A",
                "goals_for": goals.get("home") if is_home else goals.get("away"),
                "goals_against": goals.get("away") if is_home else goals.get("home"),
            }
        )
    rows.sort(key=lambda row: row["date"], reverse=True)
    return rows[:limit]


def refresh_matchday(
    *,
    club_slug: str = "aberdeen",
    recent_fixtures: int | None = None,
    max_requests: int | None = None,
    force: bool = False,
    dry_run: bool = False,
    out_dir: Path | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Refresh the next opponent snapshot. Never raises for provider failures."""
    ensure_dirs()
    policy = matchday_policy()
    out_dir = out_dir or MATCHDAY_DIR
    recent_fixtures = int(recent_fixtures or policy.get("recent_fixtures") or 6)
    max_requests = int(max_requests or policy.get("max_api_requests") or 24)
    refresh_after = float(policy.get("refresh_after_hours") or 20)
    include_players = bool(policy.get("include_players"))
    include_statistics = bool(policy.get("include_statistics"))

    fixture = next_fixture(club_slug=club_slug, today=today)
    if not fixture:
        meta = _empty_snapshot(
            out_dir,
            fixture=None,
            state="no_fixture",
            reason="no_scheduled_fixture",
        )
        return {"status": "ok", "state": "no_fixture", "meta": meta, "requests": 0}

    previous = load_meta(out_dir)
    previous_fixture = (previous.get("fixture") or {}).get("match_id")
    if not force and previous_fixture == fixture.get("match_id") and previous.get("generated_at"):
        from datetime import UTC, datetime

        try:
            generated = datetime.fromisoformat(str(previous["generated_at"]))
            age_hours = (datetime.now(UTC) - generated).total_seconds() / 3600
        except ValueError:
            age_hours = refresh_after + 1
        if age_hours < refresh_after:
            return {
                "status": "ok",
                "state": previous.get("state", "fresh"),
                "reused": True,
                "age_hours": round(age_hours, 1),
                "meta": previous,
                "requests": 0,
            }

    opponent_id = str(fixture.get("opponent_id") or "")
    opponent_name = str(fixture.get("opponent_name") or "")
    opponent_api_id, resolution = _api_team_id(opponent_id, opponent_name)
    warnings: list[str] = []
    if resolution == "search":
        warnings.append(
            f"Opponent API id for {opponent_name} resolved by search; "
            "add it to reference/source_ids.yaml after verification."
        )
    if opponent_api_id is None:
        meta = {
            "schema_version": SCHEMA_VERSION,
            "state": "partial",
            "reason": "missing_opponent_api_id",
            "generated_at": utc_now_iso(),
            "club": "sco:aberdeen",
            "fixture": fixture,
            "opponent": {
                "club_id": opponent_id,
                "api_team_id": None,
                "resolution": resolution,
                "name": opponent_name,
            },
            "coverage": {},
            "api_requests": 0,
            "errors": [],
            "warnings": warnings,
        }
        _write_snapshot(
            out_dir,
            upcoming=[fixture],
            fixtures=[],
            lineups=[],
            shapes=[],
            player_form=[],
            team_stats=[],
            meta=meta,
        )
        return {"status": "ok", "state": "partial", "meta": meta, "requests": 0}

    season = str(fixture.get("season") or "")
    season_year = season_start_year(season)
    start_requests = api_football.network_requests()
    try:
        payload = api_football.team_fixtures(
            opponent_api_id,
            season=season_year,
            ttl_hours=168,
            force=force,
        )
        played = _opponent_played_fixtures(
            payload,
            opponent_api_id=opponent_api_id,
            limit=recent_fixtures,
        )
        if dry_run:
            return {
                "status": "ok",
                "state": "dry_run",
                "fixture": fixture,
                "opponent": {
                    "club_id": opponent_id,
                    "api_team_id": opponent_api_id,
                    "resolution": resolution,
                    "name": opponent_name,
                },
                "played": len(played),
                "estimated_requests": 1 + 2 * len(played),
                "requests": api_football.network_requests() - start_requests,
            }

        registry = TeamRegistry()
        ingested_at = utc_now_iso()
        contexts: list[dict[str, Any]] = []
        fixture_rows: list[dict[str, Any]] = []
        lineup_rows: list[dict[str, Any]] = []
        team_stats_rows: list[dict[str, Any]] = []
        capped = False
        for item in played:
            fixture_id = int(item["fixture_id"])
            if api_football.network_requests() - start_requests >= max_requests:
                capped = True
                break
            lineups = api_football.fixtures_lineups(fixture_id, ttl_hours=6, force=force)
            if api_football.network_requests() - start_requests >= max_requests:
                capped = True
                events: list[dict[str, Any]] = []
            else:
                events = api_football.fixtures_events(fixture_id, force=force)
            players: list[dict[str, Any]] = []
            stats: list[dict[str, Any]] = []
            if include_players and api_football.network_requests() - start_requests < max_requests:
                players = api_football.fixtures_players(fixture_id, force=force)
            if (
                include_statistics
                and api_football.network_requests() - start_requests < max_requests
            ):
                stats = api_football.fixtures_statistics(fixture_id, force=force)
            contexts.append(
                {
                    "fixture": item["raw"],
                    "lineups": lineups,
                    "events": events,
                    "players": players,
                    "players_ok": bool(players),
                }
            )
            other_name = (
                ((item["raw"].get("teams") or {}).get("away") or {}).get("name")
                if item["venue"] == "H"
                else ((item["raw"].get("teams") or {}).get("home") or {}).get("name")
            )
            other_id = registry.resolve(str(other_name or ""))
            if other_id is None:
                other_id = registry.provisional(str(other_name or "Unknown"))
            fixture_rows.append(
                {
                    "fixture_id": fixture_id,
                    "date": _safe_date(item["date"]),
                    "season": season,
                    "competition_id": item["competition_id"],
                    "competition_name": item["competition_name"],
                    "round": item["round"],
                    "team_id": opponent_api_id,
                    "team_name": opponent_name,
                    "opponent_id": other_id,
                    "opponent_name": registry.display_name_for_id(other_id, other_name),
                    "venue": item["venue"],
                    "goals_for": item["goals_for"],
                    "goals_against": item["goals_against"],
                    "result": (
                        "W"
                        if item["goals_for"] is not None
                        and item["goals_against"] is not None
                        and item["goals_for"] > item["goals_against"]
                        else "D"
                        if item["goals_for"] is not None
                        and item["goals_against"] is not None
                        and item["goals_for"] == item["goals_against"]
                        else "L"
                        if item["goals_for"] is not None and item["goals_against"] is not None
                        else None
                    ),
                    "status": item["status"],
                    "has_lineups": bool(lineups),
                    "has_events": bool(events),
                    "source_id": SOURCE_ID,
                    "ingested_at": ingested_at,
                }
            )
            if lineups:
                names = _lineup_players(lineups, team_id=opponent_api_id)
                totals = _event_totals(events, fixture_id=fixture_id, team_id=opponent_api_id)
                for lineup in lineups:
                    team = lineup.get("team") or {}
                    if _int(team.get("id")) != opponent_api_id:
                        continue
                    for group in ("startXI", "substitutes"):
                        for entry in lineup.get(group) or []:
                            player = entry.get("player") or {}
                            player_id = _int(player.get("id"))
                            if player_id is None:
                                continue
                            event = totals.get(player_id, {})
                            lineup_rows.append(
                                {
                                    "fixture_id": fixture_id,
                                    "date": _safe_date(item["date"]),
                                    "season": season,
                                    "competition_id": item["competition_id"],
                                    "competition_name": item["competition_name"],
                                    "team_id": opponent_api_id,
                                    "team_name": opponent_name,
                                    "opponent_id": other_id,
                                    "opponent_name": registry.display_name_for_id(
                                        other_id, other_name
                                    ),
                                    "venue": item["venue"],
                                    "player_id": player_id,
                                    "player_key": f"api:player:{player_id}",
                                    "player_name": (names.get(player_id) or {}).get("name")
                                    or player.get("name"),
                                    "shirt_number": (names.get(player_id) or {}).get("shirt_number")
                                    or _int(player.get("number")),
                                    "position": (names.get(player_id) or {}).get("position")
                                    or player.get("pos"),
                                    "started": group == "startXI",
                                    "minutes": None,
                                    "role_code": None,
                                    "role_family": None,
                                    "role_status": None,
                                    "formation": lineup.get("formation"),
                                    "grid": player.get("grid"),
                                    "goals": event.get("goals", 0),
                                    "assists": event.get("assists", 0),
                                    "yellow_cards": event.get("yellow_cards", 0),
                                    "red_cards": event.get("red_cards", 0),
                                    "source_id": SOURCE_ID,
                                    "ingested_at": ingested_at,
                                }
                            )
            if stats:
                team_stats_rows.extend(
                    _parse_team_stats(
                        stats,
                        fixture_id=fixture_id,
                        opponent_api_id=opponent_api_id,
                        venue=item["venue"],
                        ingested_at=ingested_at,
                    )
                )

        computed = compute_match_data(
            contexts,
            focus_team_id=opponent_api_id,
            season_year=season_year,
            ingested_at=ingested_at,
            config=roles_config(),
        )
        minutes_by_player = {
            (int(row["fixture_id"]), int(row["player_id"])): int(row["minutes"] or 0)
            for row in computed["appearances"]
            if int(row["team_id"]) == opponent_api_id
        }
        roles_by_player = {
            (int(row["fixture_id"]), int(row["player_id"])): (
                row.get("role_code"),
                row.get("role_family"),
                row.get("role_status"),
            )
            for row in computed["appearances"]
            if int(row["team_id"]) == opponent_api_id
        }
        for row in lineup_rows:
            key = (int(row["fixture_id"]), int(row["player_id"]))
            row["minutes"] = minutes_by_player.get(key, 0 if row["started"] else None)
            role_code, role_family, role_status = roles_by_player.get(key, (None, None, None))
            row["role_code"] = role_code
            row["role_family"] = role_family
            row["role_status"] = role_status
        lineup_rows = [
            row
            for row in lineup_rows
            if row.get("player_id") is not None
            and (row.get("started") or (row.get("minutes") or 0) > 0)
        ]
        shape_rows = [
            {
                **row,
                "season": season,
                "competition_id": next(
                    (
                        fixture_row["competition_id"]
                        for fixture_row in fixture_rows
                        if fixture_row["fixture_id"] == int(row["fixture_id"])
                    ),
                    None,
                ),
                "competition_name": next(
                    (
                        fixture_row["competition_name"]
                        for fixture_row in fixture_rows
                        if fixture_row["fixture_id"] == int(row["fixture_id"])
                    ),
                    None,
                ),
                "opponent_id": next(
                    (
                        fixture_row["opponent_id"]
                        for fixture_row in fixture_rows
                        if fixture_row["fixture_id"] == int(row["fixture_id"])
                    ),
                    None,
                ),
                "opponent_name": next(
                    (
                        fixture_row["opponent_name"]
                        for fixture_row in fixture_rows
                        if fixture_row["fixture_id"] == int(row["fixture_id"])
                    ),
                    None,
                ),
                "venue": next(
                    (
                        fixture_row["venue"]
                        for fixture_row in fixture_rows
                        if fixture_row["fixture_id"] == int(row["fixture_id"])
                    ),
                    None,
                ),
                "source_id": SOURCE_ID,
            }
            for row in computed["team_shapes"]
            if int(row["team_id"]) == opponent_api_id
        ]
        player_form = _player_form_rows(
            lineup_rows, team_id=opponent_api_id, ingested_at=ingested_at
        )
        fixtures_with_lineups = sum(1 for row in fixture_rows if row["has_lineups"])
        fixtures_with_events = sum(1 for row in fixture_rows if row["has_events"])
        coverage = {
            "fixtures": len(fixture_rows),
            "fixtures_with_lineups": fixtures_with_lineups,
            "fixtures_with_events": fixtures_with_events,
            "lineup_coverage": (
                round(fixtures_with_lineups / len(fixture_rows), 3) if fixture_rows else None
            ),
            "players": len(player_form),
            "team_stats": len(team_stats_rows),
        }
        if capped:
            warnings.append(f"Request budget {max_requests} reached; the snapshot is partial.")
        if fixtures_with_lineups == 0:
            warnings.append("No opponent lineups were available for the window.")
        meta = {
            "schema_version": SCHEMA_VERSION,
            "state": "fresh" if fixtures_with_lineups else "partial",
            "reason": None if fixtures_with_lineups else "no_lineups",
            "generated_at": ingested_at,
            "club": "sco:aberdeen",
            "fixture": fixture,
            "opponent": {
                "club_id": opponent_id,
                "api_team_id": opponent_api_id,
                "resolution": resolution,
                "name": opponent_name,
            },
            "coverage": coverage,
            "api_requests": api_football.network_requests() - start_requests,
            "errors": [],
            "warnings": warnings,
        }
        _write_snapshot(
            out_dir,
            upcoming=[fixture],
            fixtures=fixture_rows,
            lineups=lineup_rows,
            shapes=shape_rows,
            player_form=player_form,
            team_stats=team_stats_rows,
            meta=meta,
        )
        return {
            "status": "ok",
            "state": meta["state"],
            "meta": meta,
            "requests": meta["api_requests"],
        }
    except Exception as error:  # noqa: BLE001 - provider failures must not stop the pipeline
        existing = load_meta(out_dir)
        result = {
            "status": "error",
            "state": "stale" if existing else "unavailable",
            "error": str(error),
            "requests": api_football.network_requests() - start_requests,
        }
        if existing:
            result["meta"] = existing
        else:
            meta = {
                "schema_version": SCHEMA_VERSION,
                "state": "unavailable",
                "reason": "provider_error",
                "generated_at": utc_now_iso(),
                "club": "sco:aberdeen",
                "fixture": fixture,
                "opponent": {
                    "club_id": opponent_id,
                    "api_team_id": opponent_api_id,
                    "resolution": resolution,
                    "name": opponent_name,
                },
                "coverage": {},
                "api_requests": api_football.network_requests() - start_requests,
                "errors": [str(error)],
                "warnings": warnings,
            }
            _write_snapshot(
                out_dir,
                upcoming=[fixture],
                fixtures=[],
                lineups=[],
                shapes=[],
                player_form=[],
                team_stats=[],
                meta=meta,
            )
            result["meta"] = meta
        return result


def status() -> dict[str, Any]:
    """Local snapshot status; no network."""
    meta = load_meta()
    fixture = next_fixture()
    return {"fixture": fixture, "meta": meta, "directory": str(MATCHDAY_DIR)}


__all__ = [
    "MATCHDAY_DIR",
    "load_meta",
    "next_fixture",
    "refresh_matchday",
    "status",
]
