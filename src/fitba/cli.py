"""fitba command line."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Annotated

import polars as pl
import typer
from rich.console import Console
from rich.table import Table as RichTable

from fitba.analytics.tables import build_tables
from fitba.ingest.availability import (
    load_availability_meta,
    refresh_availability,
)
from fitba.ingest.career_roles import (
    ingest_career_roles,
    load_career_meta,
    refresh_career_roles,
)
from fitba.ingest.cups import ingest_cups
from fitba.ingest.fixtures import ingest_club_fixtures
from fitba.ingest.forum import ingest_forum
from fitba.ingest.history import (
    STAGES,
    history_coverage,
    ingest_history_season,
    load_state,
    probe_season,
)
from fitba.ingest.matchday import refresh_matchday
from fitba.ingest.matchday import status as matchday_status
from fitba.ingest.news import ingest_news
from fitba.ingest.runner import ingest_season, load_matches
from fitba.ingest.squad import ingest_squad
from fitba.ingest.transfer_audit import run_transfer_audit
from fitba.ingest.transfers import ingest_transfer_history, ingest_transfers
from fitba.publish.publish import publish as publish_data
from fitba.publish.squad import squad_payload
from fitba.settings import ROOT
from fitba.settings import competitions as competitions_config
from fitba.settings import source_ids as source_ids_config
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
def fixtures(
    club: Annotated[str, typer.Option(help="Club slug, e.g. aberdeen")] = "aberdeen",
    force: Annotated[bool, typer.Option(help="Ignore the HTML cache")] = False,
) -> None:
    """Ingest a club's league and cup fixtures/results from the SPFL feed."""
    result = ingest_club_fixtures(club, force=force)
    if result.status != "ok":
        console.print(f"[red]fixtures failed[/red]: {result.errors}")
        raise typer.Exit(code=1)
    console.print(f"{result.source}: {result.rows} fixtures/results -> {result.path}")
    if result.unresolved:
        console.print(f"[yellow]unresolved teams:[/yellow] {result.unresolved}")


@app.command()
def matchday(
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Refresh the next opponent snapshot"),
    ] = False,
    status: Annotated[
        bool,
        typer.Option("--status", help="Show the local snapshot state; no network"),
    ] = False,
    fixtures: Annotated[
        int | None,
        typer.Option(help="Override the number of opponent fixtures in the window"),
    ] = None,
    max_requests: Annotated[
        int | None,
        typer.Option(help="Override the provider request budget"),
    ] = None,
    force: Annotated[bool, typer.Option(help="Ignore cache freshness")] = False,
    dry_run: Annotated[
        bool,
        typer.Option(help="Report the plan without writing a snapshot"),
    ] = False,
) -> None:
    """Build or refresh the upcoming-matchday opponent snapshot."""
    if status or not refresh:
        info = matchday_status()
        fixture = info.get("fixture") or {}
        meta = info.get("meta") or {}
        if fixture:
            console.print(
                f"next: {fixture.get('home_team_name')} v "
                f"{fixture.get('away_team_name')} · {fixture.get('date')} "
                f"{fixture.get('kickoff') or ''} · {fixture.get('competition_name')}"
            )
        else:
            console.print("next: no scheduled fixture")
        if meta:
            coverage = meta.get("coverage") or {}
            console.print(
                f"snapshot: {meta.get('state', 'unknown')} · "
                f"{meta.get('generated_at', 'unknown')} · "
                f"{coverage.get('fixtures_with_lineups', 0)}/"
                f"{coverage.get('fixtures', 0)} lineups"
            )
            for warning in meta.get("warnings") or []:
                console.print(f"  [yellow]{warning}[/yellow]")
            for error in meta.get("errors") or []:
                console.print(f"  [red]{error}[/red]")
        else:
            console.print("snapshot: none")
        console.print(f"directory: {info.get('directory')}")
        return

    result = refresh_matchday(
        recent_fixtures=fixtures,
        max_requests=max_requests,
        force=force,
        dry_run=dry_run,
    )
    state = result.get("state")
    if result.get("status") == "error":
        console.print(f"[red]matchday refresh failed[/red]: {result.get('error')}")
        console.print(f"state: {state}; previous snapshot kept if present")
        raise typer.Exit(code=1)
    if result.get("reused"):
        console.print(
            f"matchday snapshot reused ({result.get('age_hours')}h old); use --force to refresh"
        )
        return
    if dry_run:
        console.print(
            f"dry run: {result.get('played', 0)} opponent fixtures; "
            f"~{result.get('estimated_requests', 0)} requests"
        )
        return
    meta = result.get("meta") or {}
    coverage = meta.get("coverage") or {}
    console.print(
        f"matchday: {state} · {result.get('requests', 0)} requests · "
        f"{coverage.get('fixtures_with_lineups', 0)}/{coverage.get('fixtures', 0)} lineups"
    )
    for warning in meta.get("warnings") or []:
        console.print(f"  [yellow]{warning}[/yellow]")


@app.command()
def availability(
    refresh: Annotated[
        bool,
        typer.Option(
            "--refresh",
            help="Refresh the optional provider snapshot and merge the ledger",
        ),
    ] = False,
    force: Annotated[bool, typer.Option(help="Ignore the API cache")] = False,
) -> None:
    """Show or refresh the curated availability ledger."""
    if not refresh:
        meta = load_availability_meta()
        if not meta:
            console.print("availability: no snapshot; run `uv run fitba availability --refresh`")
            return
        console.print(
            f"availability: {meta.get('counts', {})} · "
            f"provider {((meta.get('provider') or {}).get('status'))} "
            f"({((meta.get('provider') or {}).get('reason'))})"
        )
        return
    meta = refresh_availability(
        squad_data=squad_payload(current_season()),
        force=force,
    )
    console.print(
        f"availability: {meta.get('counts', {})} · "
        f"provider {((meta.get('provider') or {}).get('status'))} "
        f"({((meta.get('provider') or {}).get('reason'))})"
    )


@app.command()
def cups(
    force: Annotated[bool, typer.Option(help="Ignore the API cache")] = False,
) -> None:
    """Ingest the League Cup and Scottish Cup from API-Football."""
    failed = False
    for result in ingest_cups(force=force):
        state = "ok" if result.status == "ok" else "FAIL"
        console.print(f"{result.source}: {result.rows} rows, {state}")
        if result.details:
            console.print(f"  {result.details}")
        if result.errors:
            failed = True
            console.print(f"  [red]{result.errors}[/red]")
    if failed:
        raise typer.Exit(code=1)


@app.command()
def transfers(
    force: Annotated[bool, typer.Option(help="Ignore the API cache")] = False,
    audit: Annotated[
        bool,
        typer.Option(
            "--audit",
            help="Refresh prior-season snapshots and write the completeness audit",
        ),
    ] = False,
) -> None:
    """Ingest Aberdeen transfer candidates and merge the curated register."""
    if audit:
        document, path = run_transfer_audit(force=force)
        summary = document.get("summary") or {}
        console.print(f"transfer audit: {document.get('status')} -> {path}")
        console.print(f"  needs review: {summary.get('needs_review')}")
        console.print(f"  gaps: {summary.get('gaps')}")
        return
    result = ingest_transfers(force=force)
    if result.status != "ok":
        console.print(f"[red]transfers failed[/red]: {result.errors}")
        raise typer.Exit(code=1)
    console.print(f"{result.source}: {result.rows} rows -> {result.path}")
    console.print(f"  {result.details}")


@app.command()
def history(
    status: Annotated[bool, typer.Option("--status", help="Show backfill state")] = False,
    probe_mode: Annotated[
        bool, typer.Option("--probe", help="Probe one season's provider coverage")
    ] = False,
    backfill: Annotated[
        bool, typer.Option("--backfill", help="Run the bounded lineup/statistics backfill")
    ] = False,
    backfill_transfers: Annotated[
        bool,
        typer.Option(
            "--backfill-transfers",
            help="Build the historical transfer candidate file",
        ),
    ] = False,
    season: Annotated[str | None, typer.Option(help="One season, e.g. 2019-20")] = None,
    from_season: Annotated[
        str, typer.Option("--from-season", help="First backfill season")
    ] = "2019-20",
    to_season: Annotated[str, typer.Option("--to-season", help="Last backfill season")] = "2025-26",
    stages: Annotated[
        str,
        typer.Option(
            help="Comma-separated stages: fixtures,lineups,events,rosters,players,team_stats"
        ),
    ] = "fixtures,lineups,events,rosters",
    max_requests: Annotated[
        int, typer.Option(help="Maximum provider requests per season run")
    ] = 200,
    dry_run: Annotated[bool, typer.Option(help="Plan without fetching lineups")] = False,
    force: Annotated[bool, typer.Option(help="Ignore the API cache")] = False,
    from_date: Annotated[
        str, typer.Option("--from", help="Historical transfer candidate start date")
    ] = "2019-07-01",
    max_profile_calls: Annotated[
        int, typer.Option(help="Optional profile enrichment cap for historical transfers")
    ] = 0,
) -> None:
    """Historical record backfill, status and transfer candidates."""
    if status:
        state = load_state()
        console.print(f"history state rows: {state.height}")
        if state.height:
            counts = state.group_by("status").agg(pl.len().alias("rows")).sort("status")
            console.print(counts)
        for season_name in seasons_between(from_season, current_season()):
            console.print(f"  {season_name}: {history_coverage(season_name)}")
        return
    if probe_mode:
        if not season:
            raise typer.BadParameter("--probe needs --season")
        console.print(probe_season(validate_season(season)))
        return
    if backfill_transfers:
        result = ingest_transfer_history(
            from_date=from_date,
            max_profile_calls=max_profile_calls,
            force=force,
        )
        if result.status != "ok":
            console.print(f"[red]history transfers failed[/red]: {result.errors}")
            raise typer.Exit(code=1)
        console.print(f"{result.source}: {result.rows} candidates -> {result.path}")
        console.print(f"  {result.details}")
        return
    if not backfill:
        console.print("Use --status, --probe --season 2019-20, --backfill or --backfill-transfers.")
        return
    selected_stages = tuple(part.strip() for part in stages.split(",") if part.strip())
    unknown = set(selected_stages) - set(STAGES)
    if unknown:
        raise typer.BadParameter(f"unknown stages: {sorted(unknown)}")
    season_names = (
        [validate_season(season)]
        if season
        else seasons_between(validate_season(from_season), validate_season(to_season))
    )
    club_id = "sco:aberdeen"
    team_id = int(source_ids_config()["teams"][club_id]["api_football"])
    for season_name in season_names:
        report = ingest_history_season(
            season_name,
            team_id=team_id,
            stages=selected_stages,
            max_requests=max_requests,
            force=force,
            dry_run=dry_run,
        )
        console.print(f"{season_name}: {report}")


@app.command()
def news(
    force: Annotated[bool, typer.Option(help="Ignore the HTML cache")] = False,
) -> None:
    """Ingest the Aberdeen FC news listing (headlines, dates, links)."""
    result = ingest_news(force=force)
    if result.status != "ok":
        console.print(f"[red]news failed[/red]: {result.errors}")
        raise typer.Exit(code=1)
    console.print(f"{result.source}: {result.rows} articles -> {result.path}")


@app.command()
def squad(
    force: Annotated[bool, typer.Option(help="Ignore the API cache")] = False,
) -> None:
    """Ingest the Aberdeen squad and current-season player stats."""
    result = ingest_squad(force=force)
    if result.status != "ok":
        console.print(f"[red]squad failed[/red]: {result.errors}")
        raise typer.Exit(code=1)
    console.print(f"{result.source}: {result.rows} players -> {result.path}")
    console.print(f"  {result.details}")


@app.command()
def forum(
    limit: Annotated[int, typer.Option(help="Maximum topics to sample")] = 8,
    days: Annotated[int, typer.Option(help="Only topics published in this window")] = 365,
    enrich: Annotated[
        bool, typer.Option(help="Validate candidate names against Scottish league squads")
    ] = True,
    force: Annotated[bool, typer.Option(help="Ignore the HTML cache")] = False,
) -> None:
    """Sample AFC Chat Rumour Mill first pages for fan signal (reference use)."""
    result = ingest_forum(limit=limit, days=days, enrich=enrich, force=force)
    if result.status != "ok":
        console.print(f"[red]forum failed[/red]: {result.errors}")
        raise typer.Exit(code=1)
    console.print(f"{result.source}: {result.rows} posts -> {result.path}")
    console.print(f"  {result.details}")


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
    require_validation: Annotated[
        bool, typer.Option(help="Fail the publish if validation reports an error")
    ] = False,
) -> None:
    """Publish derived JSON into web/data/generated."""
    current = _parse_seasons(season)[0]
    report = publish_data(
        season=current,
        out=out,
        profile=profile,
        require_validation=require_validation,
    )
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


career_app = typer.Typer(no_args_is_help=True, help="Career role history.")
app.add_typer(career_app, name="career")


@career_app.command("backfill")
def career_backfill(
    player: Annotated[
        list[int] | None, typer.Option(help="Only these API player ids (repeatable)")
    ] = None,
    max_requests: Annotated[
        int | None, typer.Option(help="Override the per-run request budget")
    ] = None,
    force: Annotated[bool, typer.Option(help="Ignore cached/complete state")] = False,
    dry_run: Annotated[bool, typer.Option(help="List candidates without fetching lineups")] = False,
) -> None:
    """Backfill historical starting-XI role evidence, capped and resumable."""
    result = ingest_career_roles(
        player_ids=player,
        max_requests=max_requests,
        force=force,
        dry_run=dry_run,
    )
    if result.status != "ok":
        console.print(f"[red]career backfill failed[/red]: {result.errors}")
        raise typer.Exit(code=1)
    details = result.details or {}
    if dry_run:
        console.print(f"dry run: {result.rows} players")
        for row in details.get("players", []):
            console.print(
                f"  {row['name']} ({row['player_id']}): {row['candidates']} candidates, "
                f"~{row['estimated_lineups']} lineup calls"
            )
        console.print(
            f"budget: {details.get('budget')} · network calls: {details.get('network_requests')}"
        )
        return
    console.print(
        f"career evidence: {result.rows} starts · "
        f"{details.get('pairs_complete', 0)} complete · "
        f"{details.get('pairs_capped', 0)} capped · "
        f"{details.get('pairs_error', 0)} errors · "
        f"{details.get('network_requests', 0)} network calls"
    )
    if result.errors:
        console.print(f"[yellow]{len(result.errors)} warnings[/yellow]")


@career_app.command("refresh")
def career_refresh() -> None:
    """Rebuild the current Aberdeen career slice locally; no network calls."""
    result = refresh_career_roles()
    if result.status != "ok":
        console.print(f"[red]career refresh failed[/red]: {result.errors}")
        raise typer.Exit(code=1)
    console.print(f"career evidence refreshed locally: {result.rows} starts")


@career_app.command("status")
def career_status() -> None:
    """Show career backfill coverage and policy state."""
    meta = load_career_meta()
    if not meta.get("generated_at"):
        console.print("career backfill has not run")
        return
    console.print(
        f"policy {meta.get('policy_version')} · seasons {meta.get('seasons')} · "
        f"{meta.get('players', 0)} players · {meta.get('evidence_rows', 0)} starts"
    )
    console.print(
        f"pairs: {meta.get('pairs_complete', 0)} complete, "
        f"{meta.get('pairs_capped', 0)} capped, "
        f"{meta.get('pairs_error', 0)} errors, "
        f"{meta.get('pairs_budget', 0)} budget"
    )
    console.print(
        f"network: {meta.get('network_requests', 0)} / {meta.get('budget')} · "
        f"budget_exhausted={meta.get('budget_exhausted')}"
    )
    if meta.get("unknown_reasons"):
        console.print(f"unknown reasons: {meta['unknown_reasons']}")
    if meta.get("errors"):
        console.print(f"warnings: {len(meta['errors'])}")


if __name__ == "__main__":
    app()
