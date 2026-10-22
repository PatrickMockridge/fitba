from __future__ import annotations

import polars as pl

from fitba.analytics.matchday import (
    form_block,
    league_match_rows,
    percentile_rank,
    record,
    split_record,
    strength_block,
    strength_comparison,
    style_block,
    style_lean,
)
from fitba.settings import matchday


def _row(**overrides):
    base = {
        "match_id": "m1",
        "date": "2026-08-01",
        "season": "2026-27",
        "competition_id": "sco:premiership",
        "competition_name": "Premiership",
        "opponent_id": "sco:other",
        "opponent_name": "Other",
        "venue": "H",
        "gf": 2,
        "ga": 1,
        "result": "W",
        "points": 3,
        "shots_for": 12,
        "shots_against": 8,
        "shots_on_target_for": 5,
        "shots_on_target_against": 3,
        "corners_for": 6,
        "corners_against": 4,
        "fouls_for": 10,
        "fouls_against": 12,
        "yellow_for": 1,
        "yellow_against": 2,
        "red_for": 0,
        "red_against": 0,
    }
    base.update(overrides)
    return base


def test_percentile_rank_edges_and_ties():
    assert percentile_rank([1, 2, 3], 3) == 100
    assert percentile_rank([1, 2, 3], 1) == 0
    assert percentile_rank([1, 2, 3], 2) == 50
    assert percentile_rank([1, 2, 2, 3], 2) == 50
    assert percentile_rank([1], 1) is None
    assert percentile_rank([], 1) is None


def test_form_block_orders_results_and_splits_venue():
    rows = [
        _row(match_id="old", date="2026-08-01", result="W", points=3, gf=2, ga=0),
        _row(match_id="mid", date="2026-08-08", result="D", points=1, gf=1, ga=1, venue="A"),
        _row(match_id="new", date="2026-08-15", result="W", points=3, gf=3, ga=1, venue="A"),
    ]
    block = form_block(rows, n=2)
    assert block["form"] == "WD"
    assert [match["match_id"] for match in block["matches"]] == ["new", "mid"]
    assert block["recent"]["points"] == 4
    assert block["season_record"]["played"] == 3
    assert block["home"]["played"] == 1
    assert block["away"]["played"] == 2
    assert block["home"]["points"] == 3
    assert block["away"]["points"] == 4


def test_record_derives_shot_share_and_conversion():
    value = record([_row(shots_for=10, shots_against=10, gf=2, ga=1)])
    assert value["shots_for_pm"] == 10
    assert value["shot_share"] == 0.5
    assert value["conversion"] == 0.2


def test_split_record_filters_venue():
    rows = [_row(venue="H"), _row(venue="A", gf=0, ga=0, result="D", points=1)]
    assert split_record(rows, venue="H")["played"] == 1
    assert split_record(rows, venue="A")["points"] == 1
    assert split_record(rows)["played"] == 2


def _league_frame():
    rows = []
    for index, team in enumerate(["a", "b", "c", "d"]):
        for match in range(4):
            rows.append(
                _row(
                    match_id=f"{team}-{match}",
                    team_id=team,
                    opponent_id=f"x{index}",
                    gf=4 - index,
                    ga=index,
                    points=3 if index < 2 else 0,
                    shots_for=20 - index * 4,
                    shots_against=5 + index * 3,
                )
            )
    return pl.DataFrame(rows)


def test_strength_block_percentiles_and_comparison():
    league = _league_frame()
    table = pl.DataFrame(
        [
            {
                "team_id": "a",
                "team_name": "A",
                "position": 1,
                "played": 4,
                "points": 12,
                "gf": 16,
                "ga": 0,
                "gd": 16,
                "form": "WWWW",
            },
            {
                "team_id": "b",
                "team_name": "B",
                "position": 2,
                "played": 4,
                "points": 9,
                "gf": 12,
                "ga": 4,
                "gd": 8,
                "form": "WWWL",
            },
            {
                "team_id": "c",
                "team_name": "C",
                "position": 3,
                "played": 4,
                "points": 3,
                "gf": 8,
                "ga": 8,
                "gd": 0,
                "form": "LLLW",
            },
            {
                "team_id": "d",
                "team_name": "D",
                "position": 4,
                "played": 4,
                "points": 0,
                "gf": 4,
                "ga": 12,
                "gd": -8,
                "form": "LLLL",
            },
        ]
    )
    first = strength_block(
        table,
        team_id="a",
        league_rows=league,
        competition_id="sco:premiership",
        competition_name="Premiership",
        tier=1,
    )
    last = strength_block(
        table,
        team_id="d",
        league_rows=league,
        competition_id="sco:premiership",
        competition_name="Premiership",
        tier=1,
    )
    assert first["percentiles"]["ppg"] == 100
    assert last["percentiles"]["ppg"] == 0
    assert first["percentiles"]["ga_pg"] == 100
    assert last["percentiles"]["ga_pg"] == 0
    comparison = strength_comparison(first, last)
    assert comparison["edge"] == "aberdeen"
    assert comparison["cross_tier"] is False
    assert comparison["descriptor"] in {"clear edge", "large gap"}


def test_strength_missing_table_is_unavailable():
    block = strength_block(
        pl.DataFrame(),
        team_id="a",
        league_rows=pl.DataFrame(),
        competition_id="sco:premiership",
        competition_name="Premiership",
        tier=1,
    )
    assert block["status"] == "unavailable"


def test_league_match_rows_carries_team_id():
    matches = pl.DataFrame(
        [
            {
                "match_id": "m1",
                "phase": "regular",
                "season": "2026-27",
                "competition_id": "sco:premiership",
                "competition_name": "Premiership",
                "date": "2026-08-01",
                "home_team_id": "sco:a",
                "home_team_name": "A",
                "away_team_id": "sco:b",
                "away_team_name": "B",
                "home_goals": 2,
                "away_goals": 1,
                "home_shots": 10,
                "away_shots": 8,
                "home_shots_on_target": 4,
                "away_shots_on_target": 3,
                "home_fouls": 9,
                "away_fouls": 11,
                "home_corners": 5,
                "away_corners": 3,
                "home_yellow": 1,
                "away_yellow": 2,
                "home_red": 0,
                "away_red": 0,
            }
        ]
    )
    rows = league_match_rows(
        matches,
        competition_id="sco:premiership",
        season="2026-27",
        team_ids=["sco:a", "sco:b"],
    )
    assert rows.height == 2
    assert set(rows["team_id"].to_list()) == {"sco:a", "sco:b"}


def test_style_block_and_lean_are_measured_and_explain_missing_possession():
    rows = [
        _row(date=f"2026-08-{day:02d}", shots_for=18, shots_against=8, gf=2) for day in range(1, 9)
    ]
    league = pl.DataFrame(
        [_row(team_id="a", shots_for=18, shots_against=8) for _ in range(5)]
        + [_row(team_id="b", shots_for=8, shots_against=18) for _ in range(5)]
    )
    profile = style_block(rows, season="2026-27", league_rows=league, team_id="a")
    assert profile["coverage"] == "available"
    assert profile["shot_share"] == 0.692
    assert profile["possession_for_pm"] is None
    assert profile["possession_unknown_reason"]
    lean = style_lean(
        profile,
        profile,
        policy=matchday()["style"],
        venue_label="at home",
    )
    assert lean["approach"] == "attack"
    assert lean["confidence"] == "high"
    assert lean["evidence"]


def test_style_lean_balanced_and_deep_and_low_sample():
    policy = matchday()["style"]
    balanced = {
        "matches": 9,
        "coverage": "available",
        "shot_share": 0.5,
        "recent_shot_shares": [0.5] * 5,
        "percentiles": {
            "shots_for_pm": 50,
            "shot_share": 50,
            "goals_for_pm": 50,
            "shots_on_target_for_pm": 50,
            "conversion": 50,
        },
    }
    assert style_lean(balanced, balanced, policy=policy)["approach"] == "balanced"

    deep = {
        "matches": 9,
        "coverage": "available",
        "shot_share": 0.4,
        "recent_shot_shares": [0.4] * 5,
        "percentiles": {
            "shots_for_pm": 20,
            "shot_share": 20,
            "goals_for_pm": 40,
            "shots_on_target_for_pm": 20,
            "conversion": 70,
        },
    }
    deep_lean = style_lean(deep, deep, policy=policy)
    assert deep_lean["approach"] == "sit_deep_counter"
    assert deep_lean["confidence"] == "high"

    low = {
        "matches": 2,
        "coverage": "partial",
        "shot_share": 0.4,
        "recent_shot_shares": [0.4, 0.4],
        "percentiles": {
            "shots_for_pm": 20,
            "shot_share": 20,
            "goals_for_pm": 20,
            "shots_on_target_for_pm": 20,
            "conversion": 20,
        },
    }
    low_lean = style_lean(low, low, policy=policy)
    assert low_lean["confidence"] == "low"


def test_style_lean_venue_sample_changes_index():
    policy = matchday()["style"]
    overall = {
        "matches": 9,
        "coverage": "available",
        "shot_share": 0.5,
        "recent_shot_shares": [0.5] * 5,
        "percentiles": {
            "shots_for_pm": 40,
            "shot_share": 40,
            "goals_for_pm": 40,
            "shots_on_target_for_pm": 40,
        },
    }
    venue = {
        "matches": 5,
        "coverage": "available",
        "shot_share": 0.6,
        "recent_shot_shares": [0.6] * 5,
        "percentiles": {
            "shots_for_pm": 80,
            "shot_share": 80,
            "goals_for_pm": 80,
            "shots_on_target_for_pm": 80,
        },
    }
    lean = style_lean(overall, venue, policy=policy, venue_label="at home")
    assert lean["venue_used"] is True
    assert lean["approach_index"] == 64.0
    assert lean["overall_index"] == 40.0
