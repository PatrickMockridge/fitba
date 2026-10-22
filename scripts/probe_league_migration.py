#!/usr/bin/env python3
"""Probe the strict current-season league-results migration gate.

This script only writes a report. It never enables migration and never changes
the published source. A human reviews the report and flips
``config/league_migration.yaml`` only if every check passes.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

import polars as pl

from fitba.ingest.runner import load_matches
from fitba.normalize.teams import TeamRegistry
from fitba.settings import (
    competitions as competitions_config,
)
from fitba.settings import (
    league_migration as migration_config,
)
from fitba.sources import api_football
from fitba.util.dates import current_season, season_bounds, season_start_year, utc_now_iso

ROOT = Path(__file__).resolve().parents[1]
PLAYED_STATUSES = {"FT", "AET", "PEN"}


def _key(date_value: str, home: str, away: str) -> tuple[str, str, str]:
    return (date_value[:10], home, away)


def _api_rows(
    payload: list[dict[str, Any]], registry: TeamRegistry
) -> tuple[list[dict[str, Any]], list[str]]:
    rows = []
    unresolved = []
    for item in payload:
        fixture = item.get("fixture") or {}
        teams = item.get("teams") or {}
        goals = item.get("goals") or {}
        home = teams.get("home") or {}
        away = teams.get("away") or {}
        home_id = registry.resolve(str(home.get("name") or ""))
        away_id = registry.resolve(str(away.get("name") or ""))
        if home_id is None:
            unresolved.append(str(home.get("name") or "Unknown"))
            home_id = registry.provisional(str(home.get("name") or "Unknown"))
        if away_id is None:
            unresolved.append(str(away.get("name") or "Unknown"))
            away_id = registry.provisional(str(away.get("name") or "Unknown"))
        status = str((fixture.get("status") or {}).get("short") or "")
        rows.append(
            {
                "fixture_id": fixture.get("id"),
                "date": str(fixture.get("date") or "")[:10],
                "home_team_id": home_id,
                "away_team_id": away_id,
                "home_goals": goals.get("home"),
                "away_goals": goals.get("away"),
                "status": status,
                "played": status in PLAYED_STATUSES,
            }
        )
    return rows, unresolved


def _competition_key(competition: dict[str, Any]) -> str:
    return str(competition.get("id") or "")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default=current_season())
    args = parser.parse_args()
    season = args.season
    start, end = season_bounds(season)
    policy = migration_config() or {}
    report_path = ROOT / str(policy.get("report") or f"reports/league-migration/{season}.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        frame = load_matches([season])
    except FileNotFoundError:
        print("no normalized matches; run `uv run fitba ingest --season current` first")
        return 1
    registry = TeamRegistry()
    competitions = competitions_config().get("competitions", [])
    competition_by_code = {str(item.get("code")): item for item in competitions}
    checks = []
    competitions_report = []
    failures = []

    for division, league_id in api_football.SCOTLAND_LEAGUE_IDS.items():
        competition = competition_by_code.get(division)
        if not competition:
            failures.append(f"{division}: no competition config")
            continue
        competition_id = str(competition["id"])
        expected_matches = int(competition.get("matches_per_season") or 0)
        expected_teams = int(competition.get("teams") or 0)
        api_payload = api_football.fixtures(
            league_id,
            season=season_start_year(season),
            ttl_hours=6,
        )
        api_rows, unresolved = _api_rows(api_payload, registry)
        keys = [_key(row["date"], row["home_team_id"], row["away_team_id"]) for row in api_rows]
        duplicate_keys = len(keys) - len(set(keys))
        fd = frame.filter(
            (pl.col("competition_id") == competition_id) & (pl.col("season") == season)
        ).to_dicts()
        fd_played = [row for row in fd if row.get("home_goals") is not None]
        api_played = [row for row in api_rows if row["played"]]
        fd_keys = {
            _key(str(row["date"]), str(row["home_team_id"]), str(row["away_team_id"])): row
            for row in fd_played
        }
        api_keys = {
            _key(row["date"], row["home_team_id"], row["away_team_id"]): row for row in api_played
        }
        missing = sorted(set(fd_keys) - set(api_keys))
        extra = sorted(set(api_keys) - set(fd_keys))
        score_matches = 0
        for key, fd_row in fd_keys.items():
            api_row = api_keys.get(key)
            if api_row is None:
                continue
            api_home = api_row.get("home_goals")
            api_away = api_row.get("away_goals")
            if (
                api_home is not None
                and api_away is not None
                and int(fd_row["home_goals"]) == int(api_home)
                and int(fd_row["away_goals"]) == int(api_away)
            ):
                score_matches += 1
        score_agreement = round(score_matches / len(fd_played), 4) if fd_played else 0.0
        team_ids = {row["home_team_id"] for row in api_rows} | {
            row["away_team_id"] for row in api_rows
        }
        dates_in_bounds = all(
            start <= date.fromisoformat(row["date"]) <= end for row in api_rows if row["date"]
        )
        coverage = api_football.league_coverage(league_id, season=season_start_year(season))
        stats_available = False
        stats_note = "no played fixture to sample"
        stats_meta = bool((coverage.get("fixtures") or {}).get("statistics_fixtures"))
        if api_played:
            sample = api_football.fixtures_statistics(
                int(api_played[0]["fixture_id"]),
                ttl_hours=168,
            )
            stats_available = stats_meta and bool(sample)
            stats_note = (
                f"metadata {stats_meta}; sample fixture "
                f"{api_played[0]['fixture_id']}: {len(sample)} team blocks"
            )
        else:
            stats_note = f"metadata {stats_meta}; no played fixture to sample"
        checks_for_division = [
            ("fixture_count", len(api_rows) == expected_matches, len(api_rows)),
            ("team_count", len(team_ids) == expected_teams, len(team_ids)),
            ("unresolved_teams", not unresolved, len(unresolved)),
            ("duplicate_keys", duplicate_keys == 0, duplicate_keys),
            ("dates_in_bounds", dates_in_bounds, dates_in_bounds),
            (
                "every_played_result_matched",
                not missing,
                f"{len(missing)} missing",
            ),
            (
                "score_agreement",
                score_agreement == 1.0,
                score_agreement,
            ),
            (
                "team_match_stats",
                stats_available,
                stats_note,
            ),
        ]
        for check_id, passed, value in checks_for_division:
            checks.append(
                {
                    "id": f"{check_id}.{division}",
                    "status": "pass" if passed else "fail",
                    "value": value,
                }
            )
            if not passed:
                failures.append(f"{division}: {check_id} ({value})")
        competitions_report.append(
            {
                "division": division,
                "competition_id": competition_id,
                "provider_fixtures": len(api_rows),
                "expected_fixtures": expected_matches,
                "provider_teams": len(team_ids),
                "expected_teams": expected_teams,
                "fd_played": len(fd_played),
                "api_played": len(api_played),
                "matched_played": len(set(fd_keys) & set(api_keys)),
                "score_agreement": score_agreement,
                "missing_from_provider": [list(key) for key in missing[:10]],
                "extra_in_provider": [list(key) for key in extra[:10]],
                "unresolved_teams": sorted(set(unresolved)),
                "duplicate_keys": duplicate_keys,
                "coverage": coverage,
                "team_stats_sample": stats_note,
            }
        )

    gate_status = "pass" if not failures else "fail"
    report = {
        "season": season,
        "checked_at": utc_now_iso(),
        "gate": {
            "status": gate_status,
            "enabled": bool(policy.get("enabled")),
            "active_source": (
                "api_football"
                if gate_status == "pass" and policy.get("enabled")
                else str(policy.get("fallback") or "football_data_uk")
            ),
            "checks": checks,
            "failures": failures,
        },
        "competitions": competitions_report,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for check in checks:
        print(f"{check['status']:<5} {check['id']}: {check['value']}")
    print(f"gate: {gate_status} · report: {report_path}")
    if gate_status != "pass":
        print("Migration stays disabled; football-data remains primary.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
