from __future__ import annotations

import polars as pl

from fitba.analytics.scouting import build_pool_rows
from fitba.ingest.scouting_standings import _rows_for


def test_standings_pick_the_most_played_group() -> None:
    raw = [
        {
            "league": {
                "standings": [
                    [
                        {
                            "rank": 1,
                            "team": {"id": 1, "name": "Top"},
                            "points": 3,
                            "goalsDiff": 1,
                            "group": "Early",
                            "all": {"played": 1, "goals": {"for": 2, "against": 1}},
                        }
                    ],
                    [
                        {
                            "rank": 1,
                            "team": {"id": 1, "name": "Top"},
                            "points": 9,
                            "goalsDiff": 4,
                            "group": "Current",
                            "all": {"played": 3, "goals": {"for": 7, "against": 3}},
                        },
                        {
                            "rank": 2,
                            "team": {"id": 2, "name": "Bottom"},
                            "points": 0,
                            "goalsDiff": -4,
                            "group": "Current",
                            "all": {"played": 3, "goals": {"for": 3, "against": 7}},
                        },
                    ],
                ]
            }
        }
    ]
    rows = _rows_for(
        {"id": "test:league", "provider": {"api_football_id": 1}},
        "2026-27",
        raw,
        "2026-10-23T00:00:00Z",
    )
    assert len(rows) == 2
    assert rows[0]["group"] == "Current"
    assert rows[0]["ppg"] == 3.0
    assert rows[1]["ppg"] == 0.0


def test_conference_standings_are_merged_when_configured() -> None:
    raw = [
        {
            "league": {
                "standings": [
                    [
                        {
                            "rank": 1,
                            "team": {"id": 1, "name": "West One"},
                            "points": 9,
                            "goalsDiff": 4,
                            "group": "Western Conference",
                            "all": {"played": 3, "goals": {"for": 7, "against": 3}},
                        }
                    ],
                    [
                        {
                            "rank": 1,
                            "team": {"id": 2, "name": "East One"},
                            "points": 7,
                            "goalsDiff": 2,
                            "group": "Eastern Conference",
                            "all": {"played": 3, "goals": {"for": 5, "against": 3}},
                        }
                    ],
                ]
            }
        }
    ]
    rows = _rows_for(
        {
            "id": "usa:mls",
            "provider": {
                "api_football_id": 253,
                "merge_standings_groups": True,
            },
        },
        "2026",
        raw,
        "2026-10-27T00:00:00Z",
    )
    assert len(rows) == 2
    assert {row["team_name"] for row in rows} == {"West One", "East One"}
    assert {row["group"] for row in rows} == {
        "Western Conference",
        "Eastern Conference",
    }


def test_team_context_and_lift_are_joined_to_pool_rows() -> None:
    pool = pl.DataFrame(
        [
            {
                "player_id": 1,
                "name": "Good",
                "competition_id": "eng:league-one",
                "provider_league_id": 41,
                "team_id": 1,
                "team_name": "Top",
                "position_group": "MID",
                "minutes": 900,
                "rating": 7.5,
                "passes_total": 500,
                "pass_accuracy": 85.0,
            },
            {
                "player_id": 2,
                "name": "Hidden",
                "competition_id": "eng:league-one",
                "provider_league_id": 41,
                "team_id": 2,
                "team_name": "Bottom",
                "position_group": "MID",
                "minutes": 900,
                "rating": 7.0,
                "passes_total": 400,
                "pass_accuracy": 80.0,
            },
        ]
    )
    roles = pl.DataFrame(
        [
            {
                "player_id": player_id,
                "league_id": "eng:league-one",
                "role_family": "central_midfield",
                "role_family_share": 1.0,
                "role_status": "observed",
            }
            for player_id in (1, 2)
        ]
    )
    standings = pl.DataFrame(
        [
            {
                "provider_league_id": 41,
                "team_id": 1,
                "rank": 1,
                "points": 9,
                "played": 3,
                "ppg": 3.0,
            },
            {
                "provider_league_id": 41,
                "team_id": 2,
                "rank": 2,
                "points": 0,
                "played": 3,
                "ppg": 0.0,
            },
        ]
    )
    model = {
        "pool": {"min_minutes": 450, "min_cohort": 1, "fallback_group_min": 1},
        "archetypes": {"min_minutes": 450, "shrink_minutes": 450, "min_weight_coverage": 0.7},
    }
    rows = build_pool_rows(
        pool,
        roles,
        config={"families": {"central_midfield": {"label": "Centre midfield"}}},
        archetypes={"archetypes": {}},
        model=model,
        team_standings=standings,
        team_context_config={"underperforming_ppg_percentile_max": 40},
    )["eng:league-one"]
    bottom = next(row for row in rows if row["name"] == "Hidden")
    assert bottom["team_rank"] == 2
    assert bottom["team_points_percentile"] is not None
    assert bottom["team_points_percentile"] <= 40
    assert bottom["team_underperforming"] is True
    # The tiny test cohort is below the provider-rating percentile floor, so the
    # lift is correctly null rather than zero-filled.
    assert bottom["team_lift"] is None
