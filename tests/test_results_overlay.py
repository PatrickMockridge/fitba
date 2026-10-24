from __future__ import annotations

from datetime import date

import polars as pl
import pytest

from fitba.analytics.tables import playable_matches
from fitba.normalize import results


def _base() -> pl.DataFrame:
    rows = [
        {
            "match_id": "premiership-2026-27-2026-10-17-aberdeen-st-mirren",
            "competition_id": "sco:premiership",
            "competition_name": "Scottish Premiership",
            "season": "2026-27",
            "division": "SC0",
            "date": date(2026, 10, 17),
            "kickoff": "15:00",
            "phase": "regular",
            "home_team_id": "sco:aberdeen",
            "home_team_name": "Aberdeen",
            "away_team_id": "sco:st-mirren",
            "away_team_name": "St Mirren",
            "home_goals": 3,
            "away_goals": 1,
            "result": "H",
            "home_shots": 12,
            "away_shots": 8,
            "source_id": "football_data_uk",
            "ingested_at": "2026-10-17T17:00:00+00:00",
        }
    ]
    return results.ensure_match_columns(pl.DataFrame(rows, infer_schema_length=None))


def _official(score: tuple[int, int] = (3, 2), *, date_value: str = "2026-10-24") -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "match_id": "spfl-premiership-2026-10-24-dundee-united-aberdeen",
                "competition_id": "sco:premiership",
                "competition_name": "William Hill Premiership",
                "season": "2026-27",
                "date": date_value,
                "kickoff": "15:00",
                "home_team_id": "sco:dundee-united",
                "home_team_name": "Dundee United",
                "away_team_id": "sco:aberdeen",
                "away_team_name": "Aberdeen",
                "home_goals": score[0],
                "away_goals": score[1],
                "status": "played",
                "source_id": "spfl",
                "ingested_at": "2026-10-24T17:00:00+00:00",
            }
        ],
        infer_schema_length=None,
    )


def test_official_result_appended_with_regular_phase(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(results, "load_club_fixtures", lambda _club: _official())
    report = results.OverlayReport()
    frame = results.overlay_club_results(_base(), seasons=["2026-27"], report=report)

    row = frame.filter(pl.col("match_id").str.contains("2026-10-24")).row(0, named=True)
    assert row["phase"] == "regular"
    assert row["status"] == "played"
    assert row["season"] == "2026-27"
    assert row["division"] == "SC0"
    assert row["result"] == "H"
    assert row["result_source"] == "spfl"
    assert row["stats_source"] is None
    assert report.appended == 1
    assert frame.height == 2
    assert playable_matches(frame).height == 2


def test_legacy_null_phase_is_repaired():
    frame = _base().with_columns(pl.lit(None, dtype=pl.String).alias("phase"))
    repaired = results.normalise_phase(frame)
    assert repaired["phase"].to_list() == ["regular"]
    assert playable_matches(repaired).height == 1


def test_existing_row_is_updated_without_duplication(monkeypatch: pytest.MonkeyPatch):
    base = _base().with_columns(
        pl.lit("sco:dundee-united").alias("home_team_id"),
        pl.lit("Dundee United").alias("home_team_name"),
        pl.lit("sco:aberdeen").alias("away_team_id"),
        pl.lit("Aberdeen").alias("away_team_name"),
        pl.lit(date(2026, 10, 24)).cast(pl.Date).alias("date"),
        pl.lit(None, dtype=pl.Int64).alias("home_goals"),
        pl.lit(None, dtype=pl.Int64).alias("away_goals"),
    )
    monkeypatch.setattr(results, "load_club_fixtures", lambda _club: _official())
    report = results.OverlayReport()
    frame = results.overlay_club_results(base, seasons=["2026-27"], report=report)
    assert frame.height == 1
    row = frame.row(0, named=True)
    assert (row["home_goals"], row["away_goals"], row["result"]) == (3, 2, "H")
    assert report.filled == 1


def test_conflicting_scores_keep_official_and_report(monkeypatch: pytest.MonkeyPatch):
    base = _base().with_columns(
        pl.lit("sco:dundee-united").alias("home_team_id"),
        pl.lit("Dundee United").alias("home_team_name"),
        pl.lit("sco:aberdeen").alias("away_team_id"),
        pl.lit("Aberdeen").alias("away_team_name"),
        pl.lit(date(2026, 10, 24)).cast(pl.Date).alias("date"),
        pl.lit(1).cast(pl.Int64).alias("home_goals"),
        pl.lit(1).cast(pl.Int64).alias("away_goals"),
    )
    monkeypatch.setattr(results, "load_club_fixtures", lambda _club: _official())
    report = results.OverlayReport()
    frame = results.overlay_club_results(base, seasons=["2026-27"], report=report)
    row = frame.row(0, named=True)
    assert (row["home_goals"], row["away_goals"]) == (3, 2)
    assert report.conflicts and report.conflicts[0]["official_goals"] == [3, 2]


def test_equal_score_is_matched(monkeypatch: pytest.MonkeyPatch):
    official = _official((3, 2))
    base = _base().with_columns(
        pl.lit("sco:dundee-united").alias("home_team_id"),
        pl.lit("Dundee United").alias("home_team_name"),
        pl.lit("sco:aberdeen").alias("away_team_id"),
        pl.lit("Aberdeen").alias("away_team_name"),
        pl.lit(date(2026, 10, 24)).cast(pl.Date).alias("date"),
        pl.lit(3).cast(pl.Int64).alias("home_goals"),
        pl.lit(2).cast(pl.Int64).alias("away_goals"),
        pl.lit("H").alias("result"),
    )
    monkeypatch.setattr(results, "load_club_fixtures", lambda _club: official)
    report = results.OverlayReport()
    frame = results.overlay_club_results(base, seasons=["2026-27"], report=report)
    assert frame.height == 1
    assert report.matched == 1
    assert report.conflicts == []


def test_dedupe_same_canonical_key():
    base = _base()
    duplicate = base.with_columns(
        pl.lit("spfl-duplicate").alias("match_id"),
        pl.lit("spfl").alias("source_id"),
        pl.lit("spfl").alias("result_source"),
    )
    merged = results.dedupe_matches(pl.concat([base, duplicate]))
    assert merged.height == 1
    assert merged["match_id"][0] == base["match_id"][0]


def test_cup_rows_are_not_appended(monkeypatch: pytest.MonkeyPatch):
    cup = _official().with_columns(
        pl.lit("sco:league-cup").alias("competition_id"),
        pl.lit("League Cup").alias("competition_name"),
    )
    official = pl.concat([_official(), cup])
    monkeypatch.setattr(results, "load_club_fixtures", lambda _club: official)
    report = results.OverlayReport()
    frame = results.overlay_club_results(_base(), seasons=["2026-27"], report=report)
    assert frame.height == 2
    assert report.appended == 1


def test_overlay_is_idempotent(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(results, "load_club_fixtures", lambda _club: _official())
    first = results.overlay_club_results(_base(), seasons=["2026-27"])
    second = results.overlay_club_results(first, seasons=["2026-27"])
    assert second.height == first.height
    assert second.filter(pl.col("date") == date(2026, 10, 24)).height == 1
