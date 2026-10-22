"""Ingest the League Cup and Scottish Cup from API-Football."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import polars as pl

from fitba.analytics.cup_tables import build_group_tables, infer_groups
from fitba.normalize.teams import TeamRegistry
from fitba.settings import NORMALIZED_DIR, ensure_dirs
from fitba.settings import cups as cups_config
from fitba.sources import api_football
from fitba.sources.base import IngestResult
from fitba.util.dates import utc_now_iso

CUP_COLUMNS = [
    "match_id",
    "competition_id",
    "competition_name",
    "season",
    "round",
    "round_order",
    "api_round",
    "group",
    "date",
    "kickoff",
    "home_team_id",
    "home_team_name",
    "away_team_id",
    "away_team_name",
    "home_goals",
    "away_goals",
    "home_penalties",
    "away_penalties",
    "status",
    "winner_team_id",
    "extra_time",
    "venue",
    "source_id",
    "ingested_at",
]

PLAYED = {"FT", "AET", "PEN"}
SCHEDULED = {"NS", "TBD"}
LIVE = {"1H", "HT", "2H", "ET", "LIVE"}


def _cup(cup_id: str) -> dict[str, Any]:
    for cup in cups_config().get("cups", []):
        if cup["id"] == cup_id:
            return cup
    raise KeyError(cup_id)


def _season_label(year: int) -> str:
    return f"{year}-{(year + 1) % 100:02d}"


def _status(short: str) -> str:
    if short in PLAYED:
        return "played"
    if short in SCHEDULED:
        return "scheduled"
    if short in LIVE:
        return "live"
    if short == "PST":
        return "postponed"
    if short in {"CANC", "ABD"}:
        return "abandoned"
    return short.lower()


def _round_for(cup: dict[str, Any], api_round: str, match_date: date) -> tuple[str, int]:
    for window in cup.get("round_windows", []):
        if window["start"] <= match_date <= window["end"]:
            return str(window["name"]), int(window["order"])
    mapped = cup.get("round_map", {}).get(api_round)
    if mapped:
        for official in cup.get("official_rounds", []):
            if official["name"] == mapped:
                return mapped, int(official["order"])
        return mapped, 99
    return api_round, 99


def _resolve_team(registry: TeamRegistry, raw: str) -> tuple[str, str]:
    team_id = registry.resolve(raw)
    if team_id is None:
        return registry.provisional(raw), raw
    return team_id, registry.canonical_name(team_id)


def _normalise(
    item: dict[str, Any],
    cup: dict[str, Any],
    registry: TeamRegistry,
) -> dict[str, Any]:
    fixture = item.get("fixture") or {}
    teams = item.get("teams") or {}
    league = item.get("league") or {}
    goals = item.get("goals") or {}
    score = item.get("score") or {}
    status_raw = (fixture.get("status") or {}).get("short") or "TBD"
    status = _status(status_raw)
    iso = fixture.get("date") or ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        match_date = dt.date()
        kickoff = dt.strftime("%H:%M")
    except ValueError:
        match_date = date.today()
        kickoff = None

    api_round = str(league.get("round") or "unknown")
    round_name, round_order = _round_for(cup, api_round, match_date)
    home_raw = str((teams.get("home") or {}).get("name") or "Unknown").strip()
    away_raw = str((teams.get("away") or {}).get("name") or "Unknown").strip()
    home_id, home_name = _resolve_team(registry, home_raw)
    away_id, away_name = _resolve_team(registry, away_raw)

    fulltime = score.get("fulltime") or {}
    home_goals = goals.get("home")
    away_goals = goals.get("away")
    if home_goals is None and fulltime:
        home_goals = fulltime.get("home")
        away_goals = fulltime.get("away")
    penalty = score.get("penalty") or {}
    extratime = score.get("extratime") or {}

    winner = None
    if (teams.get("home") or {}).get("winner"):
        winner = home_id
    elif (teams.get("away") or {}).get("winner"):
        winner = away_id

    return {
        "match_id": f"api-{fixture.get('id')}",
        "competition_id": cup["id"],
        "competition_name": cup["name"],
        "season": _season_label(int(league.get("season") or api_football.CURRENT_SEASON)),
        "round": round_name,
        "round_order": round_order,
        "api_round": api_round,
        "group": None,
        "date": match_date,
        "kickoff": kickoff,
        "home_team_id": home_id,
        "home_team_name": home_name,
        "away_team_id": away_id,
        "away_team_name": away_name,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "home_penalties": penalty.get("home"),
        "away_penalties": penalty.get("away"),
        "status": status,
        "winner_team_id": winner,
        "extra_time": bool(
            status_raw in {"AET", "PEN"}
            or (extratime.get("home") is not None and extratime.get("away") is not None)
        ),
        "venue": (fixture.get("venue") or {}).get("name"),
        "source_id": "api_football",
        "ingested_at": utc_now_iso(),
    }


def _frame(rows: list[dict[str, Any]]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame({column: [] for column in CUP_COLUMNS})
    return pl.DataFrame(rows).select(CUP_COLUMNS).sort(["date", "kickoff"], nulls_last=True)


def _upsert(slug: str, rows: list[dict[str, Any]]) -> tuple[pl.DataFrame, str]:
    path = NORMALIZED_DIR / "cups" / f"{slug}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = _frame(rows)
    if path.exists():
        existing = pl.read_parquet(path)
        frame = pl.concat([existing, frame], how="vertical_relaxed")
    frame = frame.unique(subset=["match_id"], keep="last").sort(
        ["date", "kickoff"], nulls_last=True
    )
    frame.write_parquet(path)
    return frame, str(path)


def ingest_league_cup(*, force: bool = False) -> IngestResult:
    ensure_dirs()
    cup = _cup("sco:league-cup")
    registry = TeamRegistry()
    try:
        items = api_football.fixtures(api_football.SCOTLAND_LEAGUE_CUP, force=force)
        rows = [_normalise(item, cup, registry) for item in items]
        group_fixtures = [row for row in rows if row["round"] == "Group Stage"]
        group_map = infer_groups(group_fixtures)
        groups = sorted(set(group_map.values()))
        if len(groups) != int(cup["groups"]):
            raise ValueError(f"expected {cup['groups']} groups, inferred {len(groups)}")
        counts = {
            group: sum(1 for value in group_map.values() if value == group) for group in groups
        }
        if any(count != int(cup["teams_per_group"]) for count in counts.values()):
            raise ValueError(f"group team counts are not {cup['teams_per_group']}: {counts}")
        for row in rows:
            if row["round"] == "Group Stage":
                row["group"] = group_map.get(row["home_team_id"])
        frame, path = _upsert("league-cup", rows)
        return IngestResult(
            source="api_football",
            status="ok",
            rows=frame.height,
            path=path,
            details={
                "competition": cup["id"],
                "groups": len(groups),
                "group_matches": len(group_fixtures),
            },
        )
    except Exception as exc:  # noqa: BLE001 - reported to the CLI
        return IngestResult(source="api_football", status="error", errors=[str(exc)])


def ingest_scottish_cup(*, force: bool = False) -> IngestResult:
    ensure_dirs()
    cup = _cup("sco:scottish-cup")
    registry = TeamRegistry()
    try:
        items = api_football.fixtures(api_football.SCOTLAND_SCOTTISH_CUP, force=force)
        rows = [_normalise(item, cup, registry) for item in items]
        frame, path = _upsert("scottish-cup", rows)
        present = sorted({(row["round_order"], row["round"]) for row in rows})
        return IngestResult(
            source="api_football",
            status="ok",
            rows=frame.height,
            path=path,
            details={
                "competition": cup["id"],
                "official_ties": cup.get("total_ties"),
                "licensed_ties": len(rows),
                "rounds": [name for _, name in present],
            },
        )
    except Exception as exc:  # noqa: BLE001 - reported to the CLI
        return IngestResult(source="api_football", status="error", errors=[str(exc)])


def ingest_cups(*, force: bool = False) -> list[IngestResult]:
    return [ingest_league_cup(force=force), ingest_scottish_cup(force=force)]


def load_cup_fixtures(slug: str) -> pl.DataFrame:
    path = NORMALIZED_DIR / "cups" / f"{slug}.parquet"
    if not path.exists():
        return pl.DataFrame({column: [] for column in CUP_COLUMNS})
    return pl.read_parquet(path)


def league_cup_summary(rows: pl.DataFrame | None = None) -> dict[str, Any]:
    cup = _cup("sco:league-cup")
    frame = load_cup_fixtures("league-cup") if rows is None else rows
    fixtures = frame.to_dicts() if frame.height else []
    group_fixtures = [row for row in fixtures if row["round"] == "Group Stage"]
    group_map = infer_groups(group_fixtures) if group_fixtures else {}
    tables = (
        build_group_tables(group_fixtures, group_map=group_map)
        if group_fixtures
        else {
            "groups": [],
            "group_winners": [],
            "best_runners_up": [],
        }
    )
    group_teams = set(group_map)
    r16_teams = {
        team
        for row in fixtures
        if row["round"] == "Round of 16"
        for team in (row["home_team_id"], row["away_team_id"])
    }
    byes = sorted(r16_teams - group_teams)
    byes_rows = [
        {
            "team_id": team_id,
            "team_name": next(
                (row["home_team_name"] for row in fixtures if row["home_team_id"] == team_id),
                next(
                    (row["away_team_name"] for row in fixtures if row["away_team_id"] == team_id),
                    team_id,
                ),
            ),
        }
        for team_id in byes
    ]
    scheduled = sorted(
        [row for row in fixtures if row["status"] == "scheduled"],
        key=lambda row: (str(row["date"]), row["kickoff"] or ""),
    )
    qualifier_ids = {
        row["team_id"] for row in [*tables["group_winners"], *tables["best_runners_up"]]
    } | set(byes)
    mismatch = sorted(qualifier_ids ^ r16_teams) if r16_teams else []
    return {
        "cup": cup,
        "fixtures": fixtures,
        "group_map": group_map,
        "groups": tables["groups"],
        "group_winners": tables["group_winners"],
        "best_runners_up": tables["best_runners_up"],
        "byes": byes_rows,
        "scheduled": scheduled,
        "validation": {
            "qualifiers_match_r16": bool(r16_teams) and not mismatch,
            "qualifier_count": len(qualifier_ids),
            "mismatch": mismatch,
        },
    }


def scottish_cup_summary(rows: pl.DataFrame | None = None) -> dict[str, Any]:
    cup = _cup("sco:scottish-cup")
    frame = load_cup_fixtures("scottish-cup") if rows is None else rows
    fixtures = frame.to_dicts() if frame.height else []
    present = sorted({(row["round_order"], row["round"]) for row in fixtures})
    present_names = {name for _, name in present}
    missing = [
        official
        for official in cup.get("official_rounds", [])
        if official["name"] not in present_names
    ]
    scheduled = sorted(
        [row for row in fixtures if row["status"] == "scheduled"],
        key=lambda row: (str(row["date"]), row["kickoff"] or ""),
    )
    return {
        "cup": cup,
        "fixtures": fixtures,
        "rounds_present": [{"name": name, "order": order} for order, name in present],
        "missing_rounds": missing,
        "scheduled": scheduled,
    }
