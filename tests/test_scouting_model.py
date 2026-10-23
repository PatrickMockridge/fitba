from __future__ import annotations

from fitba.analytics.scouting import (
    CohortIndex,
    adjusted_percentile_for,
    adjusted_profile_for,
    archetype_scores,
    build_alignment,
    build_board,
    build_pool_rows,
    midrank_percentile,
    per90,
    player_rates,
    robust_z,
    scouting_value_index,
)

MODEL = {
    "pool": {"min_minutes": 450, "low_minutes": 900, "min_cohort": 1, "fallback_group_min": 1},
    "board": {
        "min_minutes": 300,
        "status_below": 40.0,
        "status_above": 60.0,
        "first_choice_minutes": 900,
        "first_choice_starts": 10,
        "prior_min_minutes": 450,
        "prior_seasons": 3,
    },
    "archetypes": {
        "winsor_low": 0.01,
        "winsor_high": 0.99,
        "shrink_minutes": 450,
        "min_minutes": 450,
        "min_weight_coverage": 0.7,
    },
    "squad": {"min_minutes": 180},
    "coverage": {"min_rated_players": 25},
}

ARCHETYPES = {
    "archetypes": {
        "deep_lying_playmaker": {
            "label": "Deep-lying playmaker",
            "families": ["central_midfield"],
            "features": {
                "passes_completed_p90": 0.5,
                "pass_completion_pct": 0.3,
                "key_passes_p90": 0.2,
            },
        }
    }
}

ROLES = {
    "families": {
        "centre_back": {"label": "Centre back", "order": 1},
        "central_midfield": {"label": "Centre midfield", "order": 5},
    },
    "roles": {"CB": {"label": "Centre back"}, "CM": {"label": "Centre midfield"}},
}


def _rate_row(player_id: int, rating: float, minutes: int = 900, passes: float = 40.0) -> dict:
    return {
        "player_id": player_id,
        "name": f"Player {player_id}",
        "competition_id": "sco:premiership",
        "team_id": 900 + player_id,
        "team_name": "Club",
        "position_group": "MID",
        "role_family": "central_midfield",
        "minutes": minutes,
        "rating": rating,
        "rates": {
            "passes_completed_p90": passes,
            "pass_completion_pct": 85.0,
            "key_passes_p90": 1.5,
        },
    }


def test_midrank_percentile_handles_ties():
    assert midrank_percentile(2, [1, 2, 3]) == 50.0
    assert midrank_percentile(2, [1, 2, 2, 3]) == 50.0
    assert midrank_percentile(1, [1, 2, 3]) == 16.7


def test_per90_and_rates_keep_missing_as_none():
    assert per90(5, 900) == 0.5
    assert per90(5, 0) is None
    rates = player_rates(
        {
            "minutes": 900,
            "goals": 5,
            "assists": 4,
            "passes_total": 500,
            "pass_accuracy": 80.0,
            "shots_total": 20,
        }
    )
    assert rates["goals_assists_p90"] == 0.9
    assert rates["passes_completed_p90"] == 40.0
    assert rates["pass_completion_pct"] == 80.0
    assert rates["conversion_pct"] == 25.0
    assert rates["save_pct"] is None


def test_robust_z_is_zero_for_a_constant_cohort():
    assert robust_z(5, [5, 5, 5], winsor_low=0.01, winsor_high=0.99) == 0.0


def test_archetype_renormalises_and_nulls_below_coverage():
    rows = [_rate_row(index, 6.8, passes=30 + index) for index in range(1, 8)]
    index = CohortIndex(rows, MODEL)
    scores = archetype_scores(
        rows[0]["rates"],
        league="sco:premiership",
        family="central_midfield",
        minutes=900,
        index=index,
        archetypes=ARCHETYPES,
        model=MODEL,
    )
    assert scores["deep_lying_playmaker"]["score"] is not None
    assert scores["deep_lying_playmaker"]["coverage"] == 1.0
    empty = archetype_scores(
        {"passes_completed_p90": 30.0},
        league="sco:premiership",
        family="central_midfield",
        minutes=900,
        index=index,
        archetypes=ARCHETYPES,
        model=MODEL,
    )
    assert empty["deep_lying_playmaker"]["score"] is None
    assert empty["deep_lying_playmaker"]["coverage"] == 0.5


def test_pool_rows_have_a_percentile_and_no_contract_fields():
    import polars as pl

    frame = pl.DataFrame(
        [
            {
                "player_id": index,
                "name": f"P{index}",
                "competition_id": "eng:league-two",
                "team_id": 100 + index,
                "team_name": "Club",
                "position_group": "MID",
                "minutes": 900,
                "rating": 6.0 + index / 10,
                "passes_total": 400,
                "pass_accuracy": 80.0,
            }
            for index in range(1, 6)
        ]
    )
    roles = pl.DataFrame(
        [
            {
                "player_id": index,
                "league_id": "eng:league-two",
                "role_family": "central_midfield",
                "role_family_share": 1.0,
                "role_status": "observed",
            }
            for index in range(1, 6)
        ]
    )
    rows = build_pool_rows(
        frame,
        roles,
        config={"families": {"central_midfield": {"label": "Centre midfield"}}},
        archetypes={"archetypes": {}},
        model=MODEL,
    )["eng:league-two"]
    assert len(rows) == 5
    assert rows[0]["rating_percentile"] == 90.0
    assert rows[0]["cohort_basis"] == "role_family"
    assert "contract" not in rows[0]


def test_board_layer_zero_reads_a_verified_absentee(monkeypatch):
    from fitba.analytics import scouting as module

    def fake_prior(player_id: int, *, current: str, model: dict):
        if player_id == 999:
            return [
                {
                    "season": "2024-25",
                    "minutes": 900,
                    "starts": 12,
                    "rating": 7.0,
                    "role_family": "centre_back",
                    "role_code": "CB",
                    "role_starts": 12,
                }
            ]
        return []

    monkeypatch.setattr(module, "prior_seasons", fake_prior)
    squad = {
        "players": [
            {
                "player_id": 1,
                "name": "Current CB",
                "status": "squad",
                "display_role": {"family": "centre_back", "label": "Centre back"},
                "role": {"family": "centre_back"},
                "availability": {"status": "unknown", "confidence": "unknown"},
                "stats": [
                    {
                        "scope": "club",
                        "competition": "Premiership",
                        "minutes": 900,
                        "appearances": 10,
                        "rating": 6.0,
                    }
                ],
            }
        ]
    }
    pool_rows = [_rate_row(index, 7.0, passes=45) for index in range(1, 10)]
    for row in pool_rows:
        row["role_family"] = "centre_back"
    board = build_board(
        squad_data=squad,
        pool_rows=pool_rows,
        index=CohortIndex(pool_rows, MODEL),
        season="2026-27",
        roles=ROLES,
        model=MODEL,
        availability_entries=[
            {
                "player_id": 999,
                "player_name": "Absent CB",
                "status": "out",
                "confidence": "confirmed",
                "source_url": "https://www.afc.co.uk/en/news/example",
                "verified_at": "2026-10-23",
            }
        ],
    )
    centre_backs = next(row for row in board["families"] if row["family"] == "centre_back")
    assert centre_backs["status"] == "below"
    assert centre_backs["reading"] == "cover"
    assert len(centre_backs["layer0"]) == 1
    assert centre_backs["layer0"][0]["name"] == "Absent CB"


def test_alignment_identity_and_weaker_league():
    rows = [
        {"competition_id": "sco:premiership", "role_family": "centre_back", "rating": 6.5},
        {"competition_id": "sco:premiership", "role_family": "centre_back", "rating": 6.8},
        {"competition_id": "sco:premiership", "role_family": "centre_back", "rating": 7.0},
        {"competition_id": "eng:league-two", "role_family": "centre_back", "rating": 6.0},
        {"competition_id": "eng:league-two", "role_family": "centre_back", "rating": 6.2},
        {"competition_id": "eng:league-two", "role_family": "centre_back", "rating": 6.4},
    ]
    model = {**MODEL, "pool": {**MODEL["pool"], "min_cohort": 2}}
    alignment = build_alignment(rows, model)
    prem, basis = adjusted_percentile_for(
        7.0, league="sco:premiership", family="centre_back", alignment=alignment
    )
    assert prem is None and basis == "identity"
    weaker, basis = adjusted_percentile_for(
        6.4, league="eng:league-two", family="centre_back", alignment=alignment
    )
    assert weaker is not None and weaker < 100 and basis == "role_family"
    assert (
        adjusted_profile_for(
            90.0, league="sco:premiership", family="centre_back", alignment=alignment
        )
        == 90.0
    )
    weaker_profile = adjusted_profile_for(
        90.0, league="eng:league-two", family="centre_back", alignment=alignment
    )
    assert weaker_profile is not None and weaker_profile < 90.0


def test_value_index_bounds_and_coverage():
    index = scouting_value_index(
        adjusted_percentile=80.0,
        age=25,
        minutes=1800,
        archetypes={"goal_contributor": {"score": 80.0, "adjusted_score": 75.0}},
        config={
            "index": {
                "weights": {"performance": 0.55, "age": 0.15, "minutes": 0.15, "profile": 0.15},
                "min_weight_coverage": 0.7,
                "minutes_full": 1800,
                "age_curve": [{"max_age": 27, "factor": 1.0}, {"max_age": 120, "factor": 0.3}],
            }
        },
    )
    assert 0 <= index["value_index"] <= 100
    assert index["value_index_coverage"] == 1.0
    assert set(index["value_index_drivers"]) == {"performance", "age", "minutes", "profile"}
