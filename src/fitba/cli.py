"""fitba command line."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table as RichTable

from fitba.analytics.tables import build_tables
from fitba.ingest.runner import ingest_season, load_matches
from fitba.publish.publish import publish as publish_data
from fitba.settings import ROOT
from fitba.settings import competitions as competitions_config
from fitba.util.dates import current_season, seasons_between, validate_season
from fitba.validate.checks import run_validation
from fitba.warehouse.build import build_warehouse

app = typer.Typer(no_args_is_help=True, help="Scottish football data, Aberdeen-first.")
console = Console()


def _parse_seasons(value: str) -> list[str]:
    if value == "current":
        return [current_season()]
    if value == "all":
        history = competitions_config()["history"]
        return seasons_between(str(history["default_backfill_from"]), current_season())
    return [validate_season(value)]


def _parse_divisions(value: str) -> list[str] | None:
    if value == "all":
        return None
    divisions = [part.strip().upper() for part in value.split(",") if part.strip()]
    valid = {"SC0", "SC1", "SC2", "SC3"}
    unknown = set(divisions) - valid
    if unknown:
        raise typer.BadParameter(f"unknown divisions: {sorted(unknown)}")
    return divisions


@app.command()
def probe() -> None:
    """Check source reachability, coverage and licensing flags."""
    script = ROOT / "scripts" / "probe_source.py"
    completed = subprocess.run([sys.executable, str(script)], check=False)
    raise typer.Exit(code=completed.returncode)


@app.command()
def ingest(
    season: Annotated[str, typer.Option(help="current, all, or a season like 2025-26")] = "current",
    divisions: Annotated[str, typer.Option(help="all or SC0,SC1,SC2,SC3")] = "all",
    force: Annotated[bool, typer.Option(help="Ignore the download cache")] = False,
    strict_teams: Annotated[bool, typer.Option(help="Fail on an unknown team name")] = False,
) -> None:
    """Download and normalise match results from football-data.co.uk."""
    seasons = _parse_seasons(season)
    division_list = _parse_divisions(divisions)
    total = 0
    failed = False
    for current in seasons:
        report = ingest_season(
            current,
            divisions=division_list,
            force=force,
            strict_teams=strict_teams,
        )
        total += report.rows
        state = "FAIL" if report.has_errors else "ok"
        console.print(f"{current}: {report.rows} rows, {state}")
        for result in report.results:
            if result.status != "ok":
                failed = True
                console.print(f"  [red]{result.source}[/red]: {result.errors}")
        if report.unresolved_teams:
            console.print(f"  [yellow]unresolved:[/yellow] {sorted(set(report.unresolved_teams))}")
    console.print(f"Total rows: {total}")
    if failed:
        raise typer.Exit(code=1)


@app.command()
def build(
    season: Annotated[str, typer.Option(help="all or a season like 2026-27")] = "all",
) -> None:
    """Build the DuckDB warehouse and parquet marts."""
    target = None if season == "all" else validate_season(season)
    report = build_warehouse(season=target)
    console.print(
        f"Warehouse: {report.path} | seasons={report.seasons} | "
        f"matches={report.matches} | table rows={report.tables}"
    )


@app.command()
def validate(
    season: Annotated[str, typer.Option(help="all or a season like 2026-27")] = "current",
    strict: Annotated[bool, typer.Option(help="Treat warnings as failures")] = False,
) -> None:
    """Run data-quality checks on matches and tables."""
    seasons = _parse_seasons(season)
    failed = False
    for current in seasons:
        report = run_validation(season=current, strict=strict)
        state = "PASS" if report["status"] == "pass" else "FAIL"
        console.print(
            f"{current}: {state} | checks={len(report['checks'])} "
            f"errors={report['errors']} warnings={report['warnings']}"
        )
        for check in report["checks"]:
            if check["level"] != "ok":
                console.print(f"  [{check['level']}] {check['name']}: {check['message']}")
        if report["status"] != "pass" and (report["errors"] or strict):
            failed = True
    if failed:
        raise typer.Exit(code=1)


@app.command()
def tables(
    season: Annotated[str, typer.Option(help="current or a season like 2025-26")] = "current",
    competition: Annotated[str, typer.Option(help="competition id or 'all'")] = "all",
) -> None:
    """Print computed league tables."""
    current = _parse_seasons(season)[0]
    matches = load_matches([current])
    computed = build_tables(matches, season=current, config=competitions_config())
    for competition_id, table in computed.items():
        if competition != "all" and competition != competition_id:
            continue
        rich = RichTable(title=f"{competition_id} {current}")
        for column in (
            "position",
            "team_name",
            "played",
            "won",
            "drawn",
            "lost",
            "gf",
            "ga",
            "gd",
            "deduction",
            "points",
            "form",
        ):
            rich.add_column(column)
        for row in table.to_dicts():
            rich.add_row(
                *[
                    str(row[column])
                    for column in (
                        "position",
                        "team_name",
                        "played",
                        "won",
                        "drawn",
                        "lost",
                        "gf",
                        "ga",
                        "gd",
                        "deduction",
                        "points",
                        "form",
                    )
                ]
            )
        console.print(rich)


@app.command()
def publish(
    season: Annotated[str, typer.Option(help="current or a season like 2026-27")] = "current",
    out: Annotated[Path | None, typer.Option(help="Override the output directory")] = None,
    profile: Annotated[str, typer.Option(help="Publication profile")] = "public",
) -> None:
    """Publish derived JSON into web/data/generated."""
    current = _parse_seasons(season)[0]
    report = publish_data(season=current, out=out, profile=profile)
    console.print(
        f"Published {report.files} files, {report.bytes} bytes -> {report.out} "
        f"(dataset {report.dataset_version})"
    )


@app.command()
def status() -> None:
    """Show the current pipeline state."""
    from fitba.settings import CACHE_DIR, WAREHOUSE_PATH, WEB_DATA_DIR

    console.print(f"current season: {current_season()}")
    console.print(f"cache: {CACHE_DIR} ({CACHE_DIR.exists()})")
    console.print(f"warehouse: {WAREHOUSE_PATH} ({WAREHOUSE_PATH.exists()})")
    console.print(f"web data: {WEB_DATA_DIR} ({WEB_DATA_DIR.exists()})")


if __name__ == "__main__":
    app()
