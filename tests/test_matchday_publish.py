from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import polars as pl

from fitba.analytics.tables import build_tables
from fitba.publish.matchday import (
    FixtureBlock,
    MatchdayDocument,
    build_matchday_payload,
    fallback_matchday_payload,
    matchday_schema,
)
from fitba.settings import competitions

ROOT = Path(__file__).resolve().parents[1]

FIXTURE = {
    "match_id": "spfl-premiership-2026-10-24-dundee-united-aberdeen",
    "competition_id": "sco:premiership",
    "competition_name": "Premiership",
    "stage": None,
    "season": "2026-27",
    "date": "2026-10-24",
    "kickoff": "15:00",
    "home_team_id": "sco:dundee-united",
    "home_team_name": "Dundee United",
    "away_team_id": "sco:aberdeen",
    "away_team_name": "Aberdeen",
    "venue": "A",
    "opponent_id": "sco:dundee-united",
    "opponent_name": "Dundee United",
    "status": "scheduled",
    "source_id": "spfl",
}

META = {
    "schema_version": "1.0",
    "state": "fresh",
    "reason": None,
    "generated_at": "2026-10-21T12:00:00+00:00",
    "club": "sco:aberdeen",
    "fixture": FIXTURE,
    "opponent": {
        "club_id": "sco:dundee-united",
        "api_team_id": 1386,
        "resolution": "source_ids",
        "name": "Dundee United",
    },
    "coverage": {"fixtures": 6, "fixtures_with_lineups": 6},
    "api_requests": 6,
    "errors": [],
    "warnings": [],
}


def _match(
    match_id: str,
    day: str,
    *,
    home: str,
    away: str,
    home_goals: int,
    away_goals: int,
    home_shots: int = 14,
    away_shots: int = 10,
) -> dict:
    return {
        "match_id": match_id,
        "phase": "regular",
        "season": "2026-27",
        "competition_id": "sco:premiership",
        "competition_name": "Premiership",
        "date": day,
        "home_team_id": home,
        "home_team_name": "Dundee United" if home == "sco:dundee-united" else "Aberdeen",
        "away_team_id": away,
        "away_team_name": "Aberdeen" if away == "sco:aberdeen" else "Dundee United",
        "home_goals": home_goals,
        "away_goals": away_goals,
        "home_shots": home_shots,
        "away_shots": away_shots,
        "home_shots_on_target": max(1, home_shots // 3),
        "away_shots_on_target": max(1, away_shots // 3),
        "home_fouls": 10,
        "away_fouls": 12,
        "home_corners": 5,
        "away_corners": 4,
        "home_yellow": 1,
        "away_yellow": 2,
        "home_red": 0,
        "away_red": 0,
    }


def _matches() -> pl.DataFrame:
    rows = []
    for index in range(5):
        rows.append(
            _match(
                f"m{index}",
                f"2026-09-{index + 1:02d}",
                home="sco:dundee-united" if index % 2 == 0 else "sco:aberdeen",
                away="sco:aberdeen" if index % 2 == 0 else "sco:dundee-united",
                home_goals=2 if index % 2 == 0 else 1,
                away_goals=1,
            )
        )
    return pl.DataFrame(rows)


def _squad() -> dict:
    return {
        "players": [
            {
                "player_id": player_id,
                "name": f"Aberdeen Player {player_id}",
                "number": player_id,
                "position_group": "GK" if player_id == 1 else "D",
                "status": "squad",
                "injured": False,
            }
            for player_id in range(1, 12)
        ]
    }


def test_document_builds_and_validates(monkeypatch, tmp_path):
    matches = _matches()
    tables = build_tables(matches, season="2026-27", config=competitions())
    monkeypatch.setattr(
        "fitba.publish.matchday._fixture_from_snapshot",
        lambda snapshot_dir=None: dict(FIXTURE),
    )
    monkeypatch.setattr("fitba.publish.matchday.load_meta", lambda snapshot_dir=None: dict(META))
    monkeypatch.setattr("fitba.publish.matchday._age_hours", lambda value: 1.0)
    monkeypatch.setattr("fitba.publish.matchday._fixture_passed", lambda fixture: False)
    document = build_matchday_payload(
        season="2026-27",
        generated_at="2026-10-22T10:00:00+00:00",
        matches=matches,
        all_matches=matches,
        tables=tables,
        squad_data=_squad(),
        snapshot_dir=tmp_path,
    )
    assert MatchdayDocument(**document)
    assert document["state"] == "fresh"
    assert document["fixture"]["match_id"] == FIXTURE["match_id"]
    assert set(document["form_guide"]) == {"aberdeen", "opponent"}
    assert set(document["styles"]) == {"aberdeen", "opponent"}
    assert set(document["strength"]) == {"aberdeen", "opponent"}
    assert document["predicted_lineups"]["opponent"] is None or (
        document["predicted_lineups"]["opponent"]["status"] == "unavailable"
    )
    assert document["sources"]
    assert document["matchup_read"]["headline"]


def test_no_fixture_document(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "fitba.publish.matchday._fixture_from_snapshot",
        lambda snapshot_dir=None: None,
    )
    document = build_matchday_payload(
        season="2026-27",
        generated_at="2026-10-22T10:00:00+00:00",
        matches=_matches(),
        all_matches=_matches(),
        tables=build_tables(_matches(), season="2026-27", config=competitions()),
        squad_data=_squad(),
        snapshot_dir=tmp_path,
    )
    assert document["state"] == "no_fixture"
    assert document["fixture"] is None
    assert MatchdayDocument(**document)


def test_passed_fixture_is_not_presented_as_upcoming(monkeypatch, tmp_path):
    passed = {**FIXTURE, "date": (date.today() - timedelta(days=1)).isoformat()}
    monkeypatch.setattr(
        "fitba.publish.matchday._fixture_from_snapshot",
        lambda snapshot_dir=None: dict(passed),
    )
    monkeypatch.setattr(
        "fitba.publish.matchday.next_fixture",
        lambda **kwargs: None,
    )
    document = build_matchday_payload(
        season="2026-27",
        generated_at="2026-10-22T10:00:00+00:00",
        matches=_matches(),
        all_matches=_matches(),
        tables=build_tables(_matches(), season="2026-27", config=competitions()),
        squad_data=_squad(),
        snapshot_dir=tmp_path,
    )
    assert document["state"] == "no_fixture"
    assert document["stale_reason"] == "fixture_date_passed"


def test_fallback_carries_previous_as_stale(monkeypatch):
    monkeypatch.setattr("fitba.publish.matchday._fixture_passed", lambda fixture: False)
    previous = MatchdayDocument(
        generated_at="2026-10-21T12:00:00+00:00",
        season="2026-27",
        state="fresh",
        fixture=FixtureBlock(**FIXTURE),
        notes="previous",
    ).model_dump()
    fallback = fallback_matchday_payload(
        previous,
        generated_at="2026-10-22T12:00:00+00:00",
        season="2026-27",
        reason="build_failed",
    )
    assert fallback["state"] == "stale"
    assert fallback["stale_reason"] == "build_failed"
    assert fallback["served_generated_at"] == "2026-10-21T12:00:00+00:00"
    assert MatchdayDocument(**fallback)


def test_fallback_without_previous_is_unavailable():
    fallback = fallback_matchday_payload(
        None,
        generated_at="2026-10-22T12:00:00+00:00",
        season="2026-27",
        reason="build_failed",
    )
    assert fallback["state"] == "unavailable"
    assert MatchdayDocument(**fallback)


def test_schema_is_checked_in():
    checked_in = json.loads(
        (ROOT / "contracts" / "matchday.schema.json").read_text(encoding="utf-8")
    )
    assert checked_in == matchday_schema()
