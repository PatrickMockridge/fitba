from __future__ import annotations

import polars as pl

from fitba.analytics.themes import (
    build_theme_document,
    cover_question,
    family_balance,
    leaky_boat,
    mission_check,
    shape_tradeoff,
)
from fitba.settings import themes as themes_config


def _squad() -> dict:
    players = [
        ("GK", 1, "goalkeeper"),
        ("CB1", 2, "centre_back"),
        ("CB2", 3, "centre_back"),
        ("CB3", 4, "centre_back"),
        ("FB1", 5, "full_back"),
        ("FB2", 6, "full_back"),
        ("WB1", 7, "wing_back"),
        ("CM1", 8, "central_midfield"),
        ("CM2", 9, "central_midfield"),
        ("W1", 10, "wide_forward"),
        ("W2", 11, "wide_forward"),
        ("ST1", 12, "centre_forward"),
        ("ST2", 13, "centre_forward"),
    ]
    return {
        "players": [
            {
                "player_id": player_id,
                "player_key": f"api:player:{player_id}",
                "name": name,
                "position_group": "GK"
                if family == "goalkeeper"
                else "DEF"
                if "back" in family or family in {"full_back", "wing_back"}
                else "MID"
                if "midfield" in family
                else "FWD",
                "status": "squad",
                "injured": False,
                "display_role": {"family": family},
                "role": {"family": family},
                "career_role": {"dominant": {"family": family}},
            }
            for name, player_id, family in players
        ]
    }


def _appearance(
    fixture_id: int,
    player_id: int,
    role_family: str,
    *,
    started: bool = True,
    minutes: int = 90,
    minutes_as_sub: int = 0,
    date: str = "2026-08-01",
    competition: str = "Premiership",
) -> dict:
    return {
        "fixture_id": fixture_id,
        "team_id": 252,
        "season": 2026,
        "competition": competition,
        "date": date,
        "player_id": player_id,
        "started": started,
        "minutes": minutes,
        "minutes_as_sub": minutes_as_sub,
        "role_family": role_family,
    }


def _stat(
    fixture_id: int,
    player_id: int,
    *,
    rating: float | None = 7.0,
    minutes: int | None = 90,
    substitute: bool = False,
    goals: int = 0,
    assists: int = 0,
) -> dict:
    return {
        "fixture_id": fixture_id,
        "team_id": 252,
        "season": 2026,
        "competition": "Premiership",
        "player_id": player_id,
        "rating": rating,
        "minutes": minutes,
        "substitute": substitute,
        "goals": goals,
        "assists": assists,
    }


def _matches() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "match_id": "m1",
                "phase": "regular",
                "season": "2026-27",
                "competition_id": "sco:premiership",
                "competition_name": "Premiership",
                "date": "2026-08-01",
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
            },
            {
                "match_id": "m2",
                "phase": "regular",
                "season": "2026-27",
                "competition_id": "sco:premiership",
                "competition_name": "Premiership",
                "date": "2026-08-08",
                "home_team_id": "sco:other",
                "home_team_name": "Other",
                "away_team_id": "sco:aberdeen",
                "away_team_name": "Aberdeen",
                "home_goals": 2,
                "away_goals": 0,
                "home_shots": 12,
                "away_shots": 8,
                "home_shots_on_target": 5,
                "away_shots_on_target": 2,
                "home_fouls": 9,
                "away_fouls": 11,
                "home_corners": 5,
                "away_corners": 3,
                "home_yellow": 2,
                "away_yellow": 1,
                "home_red": 0,
                "away_red": 0,
            },
        ]
    )


def test_family_balance_weights_ratings_by_minutes():
    apps = [
        _appearance(1, 1, "goalkeeper", minutes=90),
        _appearance(1, 2, "centre_back", minutes=90),
    ]
    stats = [
        _stat(1, 1, rating=6.0, minutes=90),
        _stat(1, 2, rating=8.0, minutes=90),
    ]
    result = family_balance(apps, stats, _squad(), config=themes_config())
    rows = {row["family"]: row for row in result["metrics"]["groups"]}
    assert result["status"] == "available"
    assert rows["GK"]["provider_rating"] == 6.0
    assert rows["CB"]["provider_rating"] == 8.0
    assert rows["CB"]["rating_sample"]["minutes"] == 90


def test_family_balance_missing_rating_is_null_not_zero():
    apps = [_appearance(1, 2, "centre_back", minutes=90)]
    stats = [_stat(1, 2, rating=None, minutes=90)]
    result = family_balance(apps, stats, _squad(), config=themes_config())
    rows = {row["family"]: row for row in result["metrics"]["groups"]}
    assert rows["CB"]["provider_rating"] is None
    assert result["status"] == "partial"


def test_family_balance_applies_aliases_and_goals_by_primary_family():
    apps = [_appearance(1, 10, "wide_forward", minutes=90)]
    stats = [
        _stat(1, 668797, rating=7.0, minutes=90, goals=2),
    ]
    squad = _squad()
    # Add the canonical id used by the squad.
    squad["players"][9]["player_id"] = 44982
    squad["players"][9]["player_key"] = "api:player:44982"
    result = family_balance(apps, stats, squad, config=themes_config())
    rows = {row["family"]: row for row in result["metrics"]["groups"]}
    assert rows["W"]["goals"] == 2


def _shapes() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "fixture_id": 1,
                "team_id": 252,
                "season": 2026,
                "shape_family": "back_four",
                "cb_count": 2,
                "formation": "4-2-3-1",
                "goals_for": 2,
                "goals_against": 1,
                "result": "W",
                "saves": 3,
            },
            {
                "fixture_id": 2,
                "team_id": 252,
                "season": 2026,
                "shape_family": "back_five",
                "cb_count": 3,
                "formation": "5-3-2",
                "goals_for": 0,
                "goals_against": 2,
                "result": "L",
                "saves": 6,
            },
            {
                "fixture_id": 3,
                "team_id": 252,
                "season": 2026,
                "shape_family": None,
                "cb_count": None,
                "formation": None,
                "goals_for": 1,
                "goals_against": 0,
                "result": "W",
                "saves": None,
            },
        ]
    )


def test_shape_tradeoff_splits_wing_backs_and_wide_forwards():
    apps = [
        _appearance(1, 5, "full_back"),
        _appearance(1, 10, "wide_forward"),
        _appearance(1, 11, "wide_forward"),
        _appearance(2, 7, "wing_back"),
        _appearance(2, 4, "centre_back"),
    ]
    stats = [
        _stat(1, 10, rating=7.0, minutes=90),
        _stat(1, 12, rating=None, minutes=None, substitute=True),
    ]
    result = shape_tradeoff(_shapes(), apps, stats, _squad(), config=themes_config())
    groups = {row["group"]: row for row in result["metrics"]["groups"]}
    assert groups["two_cb"]["wf_starts_pm"] == 2.0
    assert groups["three_cb"]["wb_starts_pm"] == 1.0
    assert groups["three_cb"]["wf_starts_pm"] == 0.0
    assert result["metrics"]["coverage"]["unknown_shapes"] == 1
    assert result["status"] == "available"


def test_cover_question_tiers_concentration_and_curated_note():
    apps = [
        _appearance(1, 2, "centre_back", minutes=540),
        _appearance(1, 3, "centre_back", minutes=90),
        _appearance(1, 5, "full_back", minutes=540),
        _appearance(1, 6, "full_back", minutes=30),
    ]
    stats = [
        _stat(1, 4, rating=None, minutes=None, substitute=True),
        _stat(1, 6, rating=None, minutes=None, substitute=True),
    ]
    transfers = [
        {
            "direction": "in",
            "season": "2026-27",
            "player_key": "api:player:2",
            "date_effective": "2026-07-01",
            "transfer_kind": "free",
        }
    ]
    result = cover_question(
        apps,
        stats,
        _squad(),
        transfers,
        config=themes_config(),
        curated_notes=[{"player_id": 4, "note": "Curated recovery note."}],
    )
    groups = {row["group"]: row for row in result["metrics"]["groups"]}
    cb = groups["CB"]
    assert cb["starters"] >= 1
    assert cb["thin_rotation"] is True
    assert cb["arrivals"] == 1
    assert result["metrics"]["coverage"]["bench_rows"] == 2
    assert result["metrics"]["curated_notes"][0]["note"] == "Curated recovery note."
    assert result["status"] == "available"


def test_leaky_boat_goal_mix_and_attack_share():
    apps = [_appearance(1, 10, "wide_forward")]
    stats = [
        _stat(1, 10, rating=7.0, minutes=90, goals=2),
        _stat(1, 12, rating=7.0, minutes=90, goals=1),
        _stat(1, 2, rating=7.0, minutes=90, goals=1),
    ]
    result = leaky_boat(_matches(), stats, apps, _squad(), season="2026-27", config=themes_config())
    assert result["status"] == "available"
    assert result["metrics"]["season"]["points"] == 3
    assert result["metrics"]["goals_by_family"]["attack"] == 3
    assert result["metrics"]["goals_by_family"]["total"] == 4
    assert result["metrics"]["goals_by_family"]["attack_share"] == 0.75


def test_mission_check_uses_history_and_pillars():
    history_index = {
        "era": {
            "label": "The Cormack era",
            "pillars": [
                {"id": "trading", "title": "Trading", "statement": "Buy low", "evidence": []},
                {"id": "pathway", "title": "Pathway", "statement": "Play young", "evidence": []},
            ],
        },
        "scorecard": {"best_position": 3, "worst_position": 10},
    }
    history_season = {
        "recruitment": {
            "arrivals": 15,
            "departures": 25,
            "median_age": 26.4,
        },
        "selection": {"u21_minutes_share": 0.082, "players_used": 37},
    }
    result = mission_check(
        history_index,
        history_season,
        [
            {
                "direction": "in",
                "season": "2026-27",
                "position": "Defender",
                "player_name": "A Defender",
                "from_club_name": "Other",
                "date_effective": "2026-07-01",
                "transfer_kind": "free",
            }
        ],
        season="2026-27",
        config=themes_config(),
    )
    assert result["status"] == "available"
    assert result["metrics"]["recruitment"]["arrivals"] == 15
    assert len(result["metrics"]["pillars"]) == 2
    assert result["metrics"]["defensive_arrivals"][0]["player_name"] == "A Defender"
    assert result["metrics"]["coverage"]["ratings_used"] is False


def test_mission_check_missing_history_is_unavailable():
    result = mission_check({}, {}, [], season="2026-27", config=themes_config())
    assert result["status"] == "unavailable"
    assert "unavailable" in result["read"].lower()


def test_build_theme_document_has_four_season_one_mission():
    apps = [_appearance(1, 2, "centre_back"), _appearance(1, 10, "wide_forward")]
    stats = [
        _stat(1, 2, rating=7.0, minutes=90),
        _stat(1, 10, rating=7.0, minutes=90, goals=1),
    ]
    result = build_theme_document(
        appearances=apps,
        match_stats=stats,
        team_shapes=_shapes(),
        matches=_matches(),
        squad_data=_squad(),
        transfers=[],
        history_index={
            "era": {"pillars": []},
            "scorecard": {},
        },
        history_season={
            "recruitment": {"arrivals": 1, "departures": 1},
            "selection": {"u21_minutes_share": 0.1, "players_used": 20},
        },
        season="2026-27",
        generated_at="2026-10-22T00:00:00+00:00",
        config=themes_config(),
    )
    assert result["state"] in {"fresh", "partial"}
    assert len(result["themes"]) == 5
    assert sum(1 for theme in result["themes"] if theme["horizon"] == "season") == 4
    assert sum(1 for theme in result["themes"] if theme["horizon"] == "mission") == 1
    assert result["scope"]["season_weight"] == 80
    assert result["scope"]["mission_weight"] == 20
