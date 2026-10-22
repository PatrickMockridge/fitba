#!/usr/bin/env python3
"""Guard the local history coverage so a backfill cannot silently disappear."""

from __future__ import annotations

from fitba.ingest.history import HISTORY_DIR, history_coverage
from fitba.normalize.fixture_registry import build_fixture_registry


def main() -> int:
    if not HISTORY_DIR.exists():
        print(f"error: missing {HISTORY_DIR}; run the history backfill")
        return 1

    registry = build_fixture_registry()
    coverage = registry.coverage()
    errors: list[str] = []
    warnings: list[str] = []
    if coverage.total == 0:
        errors.append("fixture registry is empty")
    if coverage.played == 0:
        errors.append("fixture registry has no played fixtures")
    if coverage.with_league_alias < 200:
        warnings.append(
            f"only {coverage.with_league_alias} played fixtures have a league alias"
        )

    for season in sorted(coverage.by_season):
        report = history_coverage(season)
        if report["fixtures_total"] and report["fixtures_with_lineups"] == 0:
            errors.append(f"{season}: no lineups")
        if report["fixtures_total"] and report.get("fixtures_with_events", 0) == 0:
            warnings.append(f"{season}: no events")
        print(
            f"{season}: played={report['fixtures_total']} "
            f"lineups={report['fixtures_with_lineups']} "
            f"events={report['fixtures_with_events']} "
            f"player_stats={report['fixtures_with_player_stats']} "
            f"team_stats={report['fixtures_with_team_stats']}"
        )

    for warning in warnings:
        print(f"warning: {warning}")
    for error in errors:
        print(f"error: {error}")
    print(
        f"{'FAIL' if errors else 'PASS'} data coverage: "
        f"{coverage.played} played, {coverage.competitive} competitive, "
        f"{coverage.friendlies} friendlies"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
