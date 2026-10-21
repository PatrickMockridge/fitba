"""Data-quality checks for matches and league tables."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import polars as pl

from fitba.analytics.tables import build_tables
from fitba.ingest.runner import load_matches
from fitba.settings import REPORTS_DIR
from fitba.settings import competitions as competitions_config
from fitba.util.dates import current_season, season_bounds, utc_now_iso


@dataclass(slots=True)
class CheckResult:
    name: str
    level: str  # ok | warning | error
    message: str
    value: Any = None

    @property
    def failed(self) -> bool:
        return self.level == "error"


def _result(
    name: str, condition: bool, message: str, *, warning: bool = False, value: Any = None
) -> CheckResult:
    if condition:
        return CheckResult(name, "ok", message, value)
    return CheckResult(name, "warning" if warning else "error", message, value)


def validate_matches(matches: pl.DataFrame, *, season: str) -> list[CheckResult]:
    checks: list[CheckResult] = []
    required = {
        "match_id",
        "competition_id",
        "season",
        "date",
        "home_team_id",
        "away_team_id",
        "home_goals",
        "away_goals",
        "result",
    }
    checks.append(
        _result(
            "matches.columns",
            required.issubset(set(matches.columns)),
            f"required columns present; missing={sorted(required - set(matches.columns))}",
        )
    )
    subset = matches.filter(pl.col("season") == season)
    checks.append(_result("matches.rows", subset.height > 0, f"{subset.height} rows for {season}"))

    if subset.height:
        duplicates = subset.height - subset["match_id"].n_unique()
        checks.append(
            _result(
                "matches.unique",
                duplicates == 0,
                f"{duplicates} duplicate match ids",
                value=duplicates,
            )
        )

        nulls = subset.select(
            pl.col("home_team_id").is_null().sum().alias("home"),
            pl.col("away_team_id").is_null().sum().alias("away"),
            pl.col("date").is_null().sum().alias("date"),
        ).to_dicts()[0]
        checks.append(
            _result(
                "matches.keys",
                sum(nulls.values()) == 0,
                f"null key fields: {nulls}",
                value=nulls,
            )
        )
        provisional = subset.filter(
            pl.col("home_team_id").str.starts_with("sco:provisional")
            | pl.col("away_team_id").str.starts_with("sco:provisional")
        ).height
        checks.append(
            _result(
                "matches.teams_resolved",
                provisional == 0,
                f"{provisional} matches use provisional team ids; "
                "add aliases to reference/teams.yaml",
                value=provisional,
            )
        )
        start, end = season_bounds(season)
        out_of_season = subset.filter((pl.col("date") < start) | (pl.col("date") > end)).height
        checks.append(
            _result(
                "matches.dates",
                out_of_season == 0,
                f"{out_of_season} dates outside {start}..{end}",
                value=out_of_season,
            )
        )
        bad_scores = subset.filter(
            (pl.col("home_goals") < 0)
            | (pl.col("away_goals") < 0)
            | (pl.col("home_goals") > 20)
            | (pl.col("away_goals") > 20)
        ).height
        checks.append(
            _result(
                "matches.scores",
                bad_scores == 0,
                f"{bad_scores} implausible scores",
                value=bad_scores,
            )
        )

    # Expected match counts. A completed season must have exactly the expected
    # number; the live season and COVID-curtailed seasons may have fewer.
    live = season == current_season()
    curtailed = competitions_config().get("validation", {}).get("curtailed", {})
    curtailed_divisions = set(curtailed.get(season, []))
    for competition in competitions_config()["competitions"]:
        comp_id = competition["id"]
        played = subset.filter(
            (pl.col("competition_id") == comp_id)
            & pl.col("home_goals").is_not_null()
            & pl.col("away_goals").is_not_null()
        ).height
        expected = int(competition["matches_per_season"])
        if live or competition["code"] in curtailed_divisions:
            checks.append(
                _result(
                    f"matches.count.{comp_id}",
                    played <= expected,
                    f"{played}/{expected} matches played (partial/curtailed season)",
                    warning=True,
                    value=played,
                )
            )
            teams = subset.filter(pl.col("competition_id") == comp_id)
            n_teams = len(
                set(teams["home_team_id"].drop_nulls().to_list())
                | set(teams["away_team_id"].drop_nulls().to_list())
            )
            checks.append(
                _result(
                    f"matches.teams.{comp_id}",
                    n_teams <= int(competition["teams"]),
                    f"{n_teams}/{competition['teams']} teams seen",
                    warning=True,
                    value=n_teams,
                )
            )
        else:
            checks.append(
                _result(
                    f"matches.count.{comp_id}",
                    played == expected,
                    f"{played}/{expected} matches in completed season",
                    value=played,
                )
            )
    return checks


def validate_tables(tables: dict[str, pl.DataFrame], *, season: str) -> list[CheckResult]:
    checks: list[CheckResult] = []
    expected_teams = {
        competition["id"]: int(competition["teams"])
        for competition in competitions_config()["competitions"]
    }
    live = season == current_season()
    for competition_id, table in tables.items():
        if table.height == 0:
            checks.append(CheckResult(f"table.{competition_id}", "warning", "empty table"))
            continue
        arithmetic = table.with_columns(
            (pl.col("won") * 3 + pl.col("drawn") - pl.col("deduction")).alias("expected_points"),
            (pl.col("won") + pl.col("drawn") + pl.col("lost")).alias("expected_played"),
        )
        bad_points = arithmetic.filter(pl.col("points") != pl.col("expected_points")).height
        bad_played = arithmetic.filter(pl.col("played") != pl.col("expected_played")).height
        checks.append(
            _result(
                f"table.{competition_id}.points",
                bad_points == 0,
                f"{bad_points} teams with points != 3W+D",
                value=bad_points,
            )
        )
        checks.append(
            _result(
                f"table.{competition_id}.played",
                bad_played == 0,
                f"{bad_played} teams with played != W+D+L",
                value=bad_played,
            )
        )
        goals_for = int(table["gf"].sum())
        goals_against = int(table["ga"].sum())
        checks.append(
            _result(
                f"table.{competition_id}.goals_balance",
                goals_for == goals_against,
                f"sum GF {goals_for} != sum GA {goals_against}",
                value={"gf": goals_for, "ga": goals_against},
            )
        )
        positions = table["position"].to_list()
        checks.append(
            _result(
                f"table.{competition_id}.positions",
                positions == list(range(1, table.height + 1)),
                "positions are contiguous from 1",
            )
        )
        if not live:
            checks.append(
                _result(
                    f"table.{competition_id}.team_count",
                    table.height == expected_teams.get(competition_id),
                    f"{table.height}/{expected_teams.get(competition_id)} teams",
                    value=table.height,
                )
            )
    return checks


def run_validation(*, season: str, strict: bool = False) -> dict[str, Any]:
    matches = load_matches([season])
    tables = build_tables(matches, season=season, config=competitions_config())
    checks = validate_matches(matches, season=season) + validate_tables(tables, season=season)
    errors = [check for check in checks if check.failed]
    warnings = [check for check in checks if check.level == "warning"]
    report = {
        "season": season,
        "generated_at": utc_now_iso(),
        "strict": strict,
        "status": "fail" if errors else "pass",
        "errors": len(errors),
        "warnings": len(warnings),
        "checks": [asdict(check) for check in checks],
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / f"validation-{season}.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def validate_published(directory: Path) -> list[CheckResult]:
    """Check committed JSON for size, provenance and forbidden fields."""
    checks: list[CheckResult] = []
    if not directory.exists():
        return [CheckResult("published.exists", "error", f"{directory} does not exist")]
    files = sorted(directory.rglob("*.json"))
    checks.append(
        _result("published.files", bool(files), f"{len(files)} JSON files", value=len(files))
    )
    oversized = [
        str(path.relative_to(directory)) for path in files if path.stat().st_size > 2_000_000
    ]
    checks.append(
        _result("published.size", not oversized, f"files over 2 MB: {oversized}", value=oversized)
    )
    forbidden = ("optapy", "raw_event", "source_row_id")
    hits: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            if token in text:
                hits.append(f"{path.name}:{token}")
    checks.append(
        _result("published.provenance", not hits, f"forbidden tokens: {hits}", value=hits)
    )
    return checks
