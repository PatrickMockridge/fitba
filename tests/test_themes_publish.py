from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from fitba.publish.themes import (
    ThemesDocument,
    build_themes_payload,
    fallback_themes_payload,
    themes_schema,
)
from fitba.settings import themes as themes_config

ROOT = Path(__file__).resolve().parents[1]


def _squad() -> dict:
    return {
        "players": [
            {
                "player_id": player_id,
                "player_key": f"api:player:{player_id}",
                "name": f"Player {player_id}",
                "display_role": {"family": family},
                "role": {"family": family},
                "status": "squad",
                "injured": False,
            }
            for player_id, family in [
                (1, "goalkeeper"),
                (2, "centre_back"),
                (3, "centre_back"),
                (4, "full_back"),
                (5, "wide_forward"),
                (6, "centre_forward"),
            ]
        ]
    }


def _appearances() -> pl.DataFrame:
    rows = []
    for fixture in (1, 2):
        for player_id, family in [
            (1, "goalkeeper"),
            (2, "centre_back"),
            (3, "centre_back"),
            (4, "full_back"),
            (5, "wide_forward"),
            (6, "centre_forward"),
        ]:
            rows.append(
                {
                    "fixture_id": fixture,
                    "team_id": 252,
                    "season": 2026,
                    "competition": "Premiership",
                    "player_id": player_id,
                    "started": True,
                    "minutes": 90,
                    "minutes_as_sub": 0,
                    "role_family": family,
                }
            )
    return pl.DataFrame(rows)


def _stats() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "fixture_id": fixture,
                "team_id": 252,
                "season": 2026,
                "competition": "Premiership",
                "player_id": player_id,
                "rating": 7.0,
                "minutes": 90,
                "substitute": False,
                "goals": 1 if player_id == 6 else 0,
                "assists": 0,
            }
            for fixture in (1, 2)
            for player_id in (1, 2, 3, 4, 5, 6)
        ]
    )


def _shapes() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "fixture_id": fixture,
                "team_id": 252,
                "season": 2026,
                "shape_family": "back_four",
                "cb_count": 2,
                "formation": "4-2-3-1",
                "goals_for": 2,
                "goals_against": 1,
                "result": "W" if fixture == 1 else "L",
                "saves": 3,
            }
            for fixture in (1, 2)
        ]
    )


def _matches() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "match_id": f"m{fixture}",
                "phase": "regular",
                "season": "2026-27",
                "competition_id": "sco:premiership",
                "competition_name": "Premiership",
                "date": f"2026-08-0{fixture}",
                "home_team_id": "sco:aberdeen",
                "home_team_name": "Aberdeen",
                "away_team_id": "sco:other",
                "away_team_name": "Other",
                "home_goals": 2,
                "away_goals": 1,
                "home_shots": 14,
                "away_shots": 9,
                "home_shots_on_target": 5,
                "away_shots_on_target": 3,
                "home_fouls": 10,
                "away_fouls": 12,
                "home_corners": 6,
                "away_corners": 4,
                "home_yellow": 1,
                "away_yellow": 2,
                "home_red": 0,
                "away_red": 0,
            }
            for fixture in (1, 2)
        ]
    )


def _history():
    index = {
        "era": {
            "pillars": [
                {"id": f"p{index}", "title": f"Pillar {index}", "statement": "x", "evidence": []}
                for index in range(5)
            ]
        },
        "scorecard": {"best_position": 3, "worst_position": 10},
    }
    season = {
        "recruitment": {"arrivals": 15, "departures": 25, "median_age": 26.4},
        "selection": {"u21_minutes_share": 0.082, "players_used": 37},
    }
    return index, season


def test_document_builds_and_validates():
    index, season = _history()
    document = build_themes_payload(
        season="2026-27",
        generated_at="2026-10-22T00:00:00+00:00",
        matches=_matches(),
        squad_data=_squad(),
        transfers_data={"transfers": []},
        history_index=index,
        history_season=season,
        appearances=_appearances(),
        match_stats=_stats(),
        team_shapes=_shapes(),
        config=themes_config(),
    )
    assert ThemesDocument(**document)
    assert len(document["themes"]) == 5
    assert sum(1 for theme in document["themes"] if theme["horizon"] == "season") == 4
    assert sum(1 for theme in document["themes"] if theme["horizon"] == "mission") == 1
    for theme in document["themes"]:
        for player in theme["players"]:
            assert "rating" not in player


def test_empty_frames_still_produce_a_valid_document():
    index, season = _history()
    document = build_themes_payload(
        season="2026-27",
        generated_at="2026-10-22T00:00:00+00:00",
        matches=pl.DataFrame(),
        squad_data={"players": []},
        transfers_data={"transfers": []},
        history_index=index,
        history_season=season,
        appearances=pl.DataFrame(),
        match_stats=pl.DataFrame(),
        team_shapes=pl.DataFrame(),
        config=themes_config(),
    )
    assert ThemesDocument(**document)
    assert document["state"] in {"partial", "unavailable"}


def test_fallback_carries_previous_as_stale():
    index, season = _history()
    previous = build_themes_payload(
        season="2026-27",
        generated_at="2026-10-22T00:00:00+00:00",
        matches=_matches(),
        squad_data=_squad(),
        transfers_data={"transfers": []},
        history_index=index,
        history_season=season,
        appearances=_appearances(),
        match_stats=_stats(),
        team_shapes=_shapes(),
        config=themes_config(),
    )
    fallback = fallback_themes_payload(
        previous,
        generated_at="2026-10-23T00:00:00+00:00",
        season="2026-27",
        reason="themes_build_failed",
    )
    assert fallback["state"] == "stale"
    assert fallback["stale_reason"] == "themes_build_failed"
    assert fallback["served_generated_at"] == "2026-10-22T00:00:00+00:00"
    assert ThemesDocument(**fallback)


def test_fallback_without_previous_is_unavailable():
    fallback = fallback_themes_payload(
        None,
        generated_at="2026-10-23T00:00:00+00:00",
        season="2026-27",
        reason="themes_build_failed",
    )
    assert fallback["state"] == "unavailable"
    assert ThemesDocument(**fallback)


def test_schema_is_checked_in():
    checked_in = json.loads((ROOT / "contracts" / "themes.schema.json").read_text(encoding="utf-8"))
    assert checked_in == themes_schema()
