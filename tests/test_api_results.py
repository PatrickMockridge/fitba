from __future__ import annotations

from datetime import date

import polars as pl
import pytest

from fitba.ingest import api_results
from fitba.normalize import results


def _base() -> pl.DataFrame:
    rows = [
        {
            "match_id": "premiership-2026-27-2026-10-24-rangers-st-johnstone",
            "competition_id": "sco:premiership",
            "competition_name": "Scottish Premiership",
            "season": "2026-27",
            "division": "SC0",
            "date": date(2026, 10, 24),
            "phase": "regular",
            "home_team_id": "sco:rangers",
            "home_team_name": "Rangers",
            "away_team_id": "sco:st-johnstone",
            "away_team_name": "St Johnstone",
            "home_goals": 4,
            "away_goals": 0,
            "result": "H",
            "source_id": "football_data_uk",
            "result_source": "football_data_uk",
            "ingested_at": "2026-10-24T18:00:00+00:00",
        }
    ]
    return results.ensure_match_columns(pl.DataFrame(rows, infer_schema_length=None))


def _api(*, st_mirren: tuple[int, int] = (2, 1), rangers: tuple[int, int] = (4, 0)) -> pl.DataFrame:
    rows = [
        {
            "match_id": "api:fixture:1",
            "competition_id": "sco:premiership",
            "competition_name": "Scottish Premiership",
            "season": "2026-27",
            "division": "SC0",
            "date": "2026-10-24",
            "phase": "regular",
            "home_team_id": "sco:st-mirren",
            "home_team_name": "St Mirren",
            "away_team_id": "sco:dundee",
            "away_team_name": "Dundee",
            "home_goals": st_mirren[0],
            "away_goals": st_mirren[1],
            "result": "H",
            "source_id": "api_football",
            "result_source": "api_football",
            "status": "played",
            "ingested_at": "2026-10-24T18:00:00+00:00",
        },
        {
            "match_id": "api:fixture:2",
            "competition_id": "sco:premiership",
            "competition_name": "Scottish Premiership",
            "season": "2026-27",
            "division": "SC0",
            "date": "2026-10-24",
            "phase": "regular",
            "home_team_id": "sco:rangers",
            "home_team_name": "Rangers",
            "away_team_id": "sco:st-johnstone",
            "away_team_name": "St Johnstone",
            "home_goals": rangers[0],
            "away_goals": rangers[1],
            "result": "H",
            "source_id": "api_football",
            "result_source": "api_football",
            "status": "played",
            "ingested_at": "2026-10-24T18:00:00+00:00",
        },
    ]
    return results.ensure_match_columns(pl.DataFrame(rows, infer_schema_length=None))


def test_api_fills_a_missing_result(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api_results, "load_api_results", lambda _season: _api())
    report = results.OverlayReport()
    frame = results.overlay_league_results(_base(), seasons=["2026-27"], report=report)
    assert frame.height == 2
    assert report.api_appended == 1
    assert report.api_matched == 1
    added = frame.filter(pl.col("home_team_id") == "sco:st-mirren").row(0, named=True)
    assert (added["home_goals"], added["away_goals"], added["result"]) == (2, 1, "H")
    assert added["result_source"] == "api_football"
    assert added["phase"] == "regular"


def test_api_never_overrides_an_existing_score(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        api_results,
        "load_api_results",
        lambda _season: _api(st_mirren=(9, 9), rangers=(9, 9)),
    )
    report = results.OverlayReport()
    frame = results.overlay_league_results(_base(), seasons=["2026-27"], report=report)
    rangers = frame.filter(pl.col("home_team_id") == "sco:rangers").row(0, named=True)
    assert (rangers["home_goals"], rangers["away_goals"]) == (4, 0)
    assert report.api_conflicts
    assert report.api_conflicts[0]["api_goals"] == [9, 9]


def test_api_fills_a_null_score(monkeypatch: pytest.MonkeyPatch):
    base = _base().with_columns(
        pl.lit(None, dtype=pl.Int64).alias("home_goals"),
        pl.lit(None, dtype=pl.Int64).alias("away_goals"),
    )
    monkeypatch.setattr(api_results, "load_api_results", lambda _season: _api())
    report = results.OverlayReport()
    frame = results.overlay_league_results(base, seasons=["2026-27"], report=report)
    rangers = frame.filter(pl.col("home_team_id") == "sco:rangers").row(0, named=True)
    assert (rangers["home_goals"], rangers["away_goals"]) == (4, 0)
    assert report.api_filled == 1


def test_api_overlay_is_idempotent(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api_results, "load_api_results", lambda _season: _api())
    first = results.overlay_league_results(_base(), seasons=["2026-27"])
    second = results.overlay_league_results(first, seasons=["2026-27"])
    assert second.height == first.height
