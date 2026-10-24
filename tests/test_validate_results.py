from __future__ import annotations

from datetime import date

import polars as pl
import pytest

from fitba.analytics.tables import build_tables
from fitba.ingest import api_results
from fitba.normalize import results
from fitba.validate.checks import validate_results


@pytest.fixture(autouse=True)
def _no_api_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_results, "load_api_results", lambda _season: pl.DataFrame())


def _matches() -> pl.DataFrame:
    rows = [
        {
            "match_id": "premiership-2026-27-2026-10-17-aberdeen-st-mirren",
            "competition_id": "sco:premiership",
            "competition_name": "Scottish Premiership",
            "season": "2026-27",
            "division": "SC0",
            "date": date(2026, 10, 17),
            "phase": "regular",
            "home_team_id": "sco:aberdeen",
            "home_team_name": "Aberdeen",
            "away_team_id": "sco:st-mirren",
            "away_team_name": "St Mirren",
            "home_goals": 3,
            "away_goals": 1,
            "result": "H",
            "source_id": "football_data_uk",
            "ingested_at": "2026-10-17T17:00:00+00:00",
        }
    ]
    return results.ensure_match_columns(pl.DataFrame(rows, infer_schema_length=None))


def _official(*, home: int = 1, away: int = 0) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "match_id": "spfl-2026-10-24",
                "competition_id": "sco:premiership",
                "competition_name": "William Hill Premiership",
                "season": "2026-27",
                "date": "2026-10-24",
                "kickoff": "15:00",
                "home_team_id": "sco:dundee-united",
                "home_team_name": "Dundee United",
                "away_team_id": "sco:aberdeen",
                "away_team_name": "Aberdeen",
                "home_goals": home,
                "away_goals": away,
                "status": "played",
                "source_id": "spfl",
                "ingested_at": "2026-10-24T17:00:00+00:00",
            }
        ],
        infer_schema_length=None,
    )


def _tables(matches: pl.DataFrame):
    from fitba.settings import competitions

    return build_tables(matches, season="2026-27", config=competitions())


def test_missing_official_result_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(results, "load_club_fixtures", lambda _club: _official())
    monkeypatch.setattr("fitba.ingest.fixtures.load_club_fixtures", lambda _club: _official())
    matches = _matches()
    checks = validate_results(matches, _tables(matches), season="2026-27")
    by_name = {check.name: check for check in checks}
    assert by_name["results.official_represented"].failed


def test_wrong_canonical_score_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(results, "load_club_fixtures", lambda _club: _official())
    monkeypatch.setattr("fitba.ingest.fixtures.load_club_fixtures", lambda _club: _official())
    report = results.OverlayReport()
    matches = results.overlay_club_results(_matches(), seasons=["2026-27"], report=report)
    # Simulate a persisted frame whose score disagrees with the official feed.
    matches = matches.with_columns(
        pl.when(pl.col("match_id") == "spfl-2026-10-24")
        .then(pl.lit(9).cast(pl.Int64))
        .otherwise(pl.col("home_goals"))
        .alias("home_goals")
    )
    checks = validate_results(matches, _tables(matches), season="2026-27", report=report)
    by_name = {check.name: check for check in checks}
    assert by_name["results.official_score"].failed


def test_table_count_mismatch_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(results, "load_club_fixtures", lambda _club: _official())
    monkeypatch.setattr("fitba.ingest.fixtures.load_club_fixtures", lambda _club: _official())
    report = results.OverlayReport()
    matches = results.overlay_club_results(_matches(), seasons=["2026-27"], report=report)
    tables = _tables(matches)
    tables["sco:premiership"] = tables["sco:premiership"].with_columns(
        (pl.col("played") + 1).alias("played")
    )
    checks = validate_results(matches, tables, season="2026-27", report=report)
    failures = {check.name for check in checks if check.failed}
    assert "results.table.sco:premiership.balance" in failures


def test_complete_record_passes(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(results, "load_club_fixtures", lambda _club: _official())
    monkeypatch.setattr("fitba.ingest.fixtures.load_club_fixtures", lambda _club: _official())
    report = results.OverlayReport()
    matches = results.overlay_club_results(_matches(), seasons=["2026-27"], report=report)
    checks = validate_results(matches, _tables(matches), season="2026-27", report=report)
    assert not [check for check in checks if check.failed]
