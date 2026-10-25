from __future__ import annotations

import json

import polars as pl
import pytest

from fitba.ingest import matchday as matchday_ingest
from fitba.sources import api_football

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
    "ingested_at": "2026-10-21T00:00:00+00:00",
}

GRID = ["1:1", "2:1", "2:2", "2:3", "2:4", "3:1", "3:2", "3:3", "4:1", "4:2", "4:3"]
POS = ["G", "D", "D", "D", "D", "M", "M", "M", "F", "F", "F"]


def _lineup(team_id: int, team_name: str, *, offset: int = 0) -> dict:
    starters = []
    for index in range(11):
        starters.append(
            {
                "player": {
                    "id": offset + index + 1,
                    "name": f"{team_name} Player {index + 1}",
                    "number": index + 1,
                    "pos": POS[index],
                    "grid": GRID[index],
                }
            }
        )
    substitutes = [
        {
            "player": {
                "id": offset + 12,
                "name": f"{team_name} Sub 12",
                "number": 12,
                "pos": "M",
            }
        }
    ]
    return {
        "team": {"id": team_id, "name": team_name},
        "formation": "4-3-3",
        "startXI": starters,
        "substitutes": substitutes,
    }


def _api_fixture(fixture_id: int, day: int, *, home: bool = True) -> dict:
    return {
        "fixture": {
            "id": fixture_id,
            "date": f"2026-10-{day:02d}T14:00:00+00:00",
            "status": {"short": "FT"},
        },
        "teams": {
            "home": {"id": 1386 if home else 252, "name": "Dundee United" if home else "Aberdeen"},
            "away": {"id": 252 if home else 1386, "name": "Aberdeen" if home else "Dundee United"},
        },
        "goals": {"home": 2 if home else 1, "away": 1 if home else 2},
        "league": {
            "id": 179,
            "name": "Premiership",
            "season": 2026,
            "round": f"Regular Season - {day}",
        },
    }


def _patch_api(monkeypatch, *, fixtures: list[dict], lineups_by_id=None, events_by_id=None):
    state = {"requests": 0}

    def bump():
        state["requests"] += 1

    def team_fixtures(*args, **kwargs):
        bump()
        return fixtures

    def fixtures_lineups(fixture_id, **kwargs):
        bump()
        if lineups_by_id is not None:
            return lineups_by_id.get(fixture_id, [])
        return [
            _lineup(1386, "Dundee United"),
            _lineup(252, "Aberdeen", offset=100),
        ]

    def fixtures_events(fixture_id, **kwargs):
        bump()
        if events_by_id is not None:
            return events_by_id.get(fixture_id, [])
        return [
            {
                "time": {"elapsed": 20},
                "team": {"id": 1386},
                "player": {"id": 2},
                "assist": {"id": 3},
                "type": "Goal",
                "detail": "Normal Goal",
            },
            {
                "time": {"elapsed": 40},
                "team": {"id": 1386},
                "player": {"id": 4},
                "assist": {"id": None},
                "type": "Card",
                "detail": "Yellow Card",
            },
        ]

    monkeypatch.setattr(api_football, "team_fixtures", team_fixtures)
    monkeypatch.setattr(api_football, "fixtures_lineups", fixtures_lineups)
    monkeypatch.setattr(api_football, "fixtures_events", fixtures_events)
    monkeypatch.setattr(api_football, "fixtures_players", lambda *a, **k: bump() or [])
    monkeypatch.setattr(api_football, "fixtures_statistics", lambda *a, **k: bump() or [])
    monkeypatch.setattr(api_football, "network_requests", lambda: state["requests"])
    return state


@pytest.fixture(autouse=True)
def _patch_next_fixture(monkeypatch):
    monkeypatch.setattr(matchday_ingest, "next_fixture", lambda **kwargs: dict(FIXTURE))


def test_fixture_ratings_reads_the_opponent_block():
    payload = [
        {
            "team": {"id": 1, "name": "Aberdeen"},
            "players": [
                {
                    "player": {"id": 10, "name": "A. Aberdeen"},
                    "statistics": [{"games": {"rating": "7.1"}}],
                }
            ],
        },
        {
            "team": {"id": 2, "name": "Falkirk"},
            "players": [
                {
                    "player": {"id": 20, "name": "S. Bain"},
                    "statistics": [{"games": {"rating": "6.8"}}],
                },
                {
                    "player": {"id": 21, "name": "No Rating"},
                    "statistics": [{"games": {"rating": None}}],
                },
            ],
        },
    ]
    assert matchday_ingest._fixture_ratings(payload, team_id=2) == {20: 6.8}


def test_refresh_writes_snapshot(tmp_path, monkeypatch):
    fixtures = [
        _api_fixture(1001, 1),
        _api_fixture(1002, 2),
        _api_fixture(1003, 3),
    ]
    state = _patch_api(monkeypatch, fixtures=fixtures)
    result = matchday_ingest.refresh_matchday(
        force=True, out_dir=tmp_path / "matchday", max_requests=20
    )
    assert result["status"] == "ok"
    assert result["state"] == "fresh"
    assert state["requests"] <= 20
    out = tmp_path / "matchday"
    assert (out / "upcoming.parquet").exists()
    assert (out / "opponent_lineups.parquet").exists()
    meta = json.loads((out / "meta.json").read_text())
    assert meta["coverage"]["fixtures"] == 3
    assert meta["coverage"]["fixtures_with_lineups"] == 3
    assert meta["opponent"]["api_team_id"] == 1386
    lineups = pl.read_parquet(out / "opponent_lineups.parquet")
    assert lineups.height > 0
    assert set(lineups["team_id"].unique().to_list()) == {1386}
    form = pl.read_parquet(out / "opponent_player_form.parquet")
    assert form.height > 0
    assert form.filter(pl.col("goals") > 0).height >= 1


def test_no_fixture_writes_empty_state(tmp_path, monkeypatch):
    monkeypatch.setattr(matchday_ingest, "next_fixture", lambda **kwargs: None)
    called = {"n": 0}
    monkeypatch.setattr(
        api_football, "team_fixtures", lambda *a, **k: called.__setitem__("n", called["n"] + 1)
    )
    result = matchday_ingest.refresh_matchday(force=True, out_dir=tmp_path / "matchday")
    assert result["state"] == "no_fixture"
    assert called["n"] == 0
    assert (tmp_path / "matchday" / "upcoming.parquet").exists()


def test_missing_opponent_id_is_partial(tmp_path, monkeypatch):
    fixture = {**FIXTURE, "opponent_id": "sco:unknown", "opponent_name": "Unknown"}
    monkeypatch.setattr(matchday_ingest, "next_fixture", lambda **kwargs: fixture)
    monkeypatch.setattr(api_football, "teams", lambda *a, **k: [])
    result = matchday_ingest.refresh_matchday(force=True, out_dir=tmp_path / "matchday")
    assert result["state"] == "partial"
    meta = json.loads((tmp_path / "matchday" / "meta.json").read_text())
    assert meta["reason"] == "missing_opponent_api_id"


def test_cached_snapshot_is_reused(tmp_path, monkeypatch):
    fixtures = [_api_fixture(1001, 1)]
    state = _patch_api(monkeypatch, fixtures=fixtures)
    first = matchday_ingest.refresh_matchday(
        force=True, out_dir=tmp_path / "matchday", max_requests=10
    )
    assert first["state"] == "fresh"
    requests_after_first = state["requests"]
    second = matchday_ingest.refresh_matchday(
        force=False, out_dir=tmp_path / "matchday", max_requests=10
    )
    assert second.get("reused") is True
    assert state["requests"] == requests_after_first


def test_budget_caps_the_window(tmp_path, monkeypatch):
    fixtures = [_api_fixture(1001 + index, index + 1) for index in range(5)]
    state = _patch_api(monkeypatch, fixtures=fixtures)
    result = matchday_ingest.refresh_matchday(
        force=True, out_dir=tmp_path / "matchday", max_requests=2
    )
    assert result["status"] == "ok"
    assert state["requests"] <= 2
    meta = result["meta"]
    assert any("budget" in warning for warning in meta["warnings"])


def test_partial_lineups_are_kept(tmp_path, monkeypatch):
    fixtures = [_api_fixture(1001, 1), _api_fixture(1002, 2)]
    _patch_api(
        monkeypatch,
        fixtures=fixtures,
        lineups_by_id={1001: [], 1002: [_lineup(1386, "Dundee United")]},
    )
    result = matchday_ingest.refresh_matchday(
        force=True, out_dir=tmp_path / "matchday", max_requests=10
    )
    assert result["state"] == "fresh"
    meta = result["meta"]
    assert meta["coverage"]["fixtures_with_lineups"] == 1
    assert meta["coverage"]["fixtures"] == 2
