from __future__ import annotations

from fitba.analytics.scouting import CohortIndex, build_rose
from fitba.publish.player_page import build_recent_matches
from fitba.settings import player_rose as load_player_rose
from fitba.settings import roles as roles_config

MODEL = {
    "pool": {
        "min_minutes": 450,
        "min_cohort": 3,
        "min_cohort_by_family": {"goalkeeper": 2},
        "fallback_group_min": 3,
    },
    "squad": {"min_minutes": 180},
}

CONFIG = {
    "min_petals": 4,
    "catalogue": {
        "goals_p90": {
            "label": "Goals /90",
            "short": "Goals",
            "unit": "per90",
            "direction": "positive",
        },
        "assists_p90": {
            "label": "Assists /90",
            "short": "Assists",
            "unit": "per90",
            "direction": "positive",
        },
        "shots_p90": {
            "label": "Shots /90",
            "short": "Shots",
            "unit": "per90",
            "direction": "positive",
        },
        "goals_assists_p90": {
            "label": "G+A /90",
            "short": "G+A",
            "unit": "per90",
            "direction": "positive",
        },
        "key_passes_p90": {
            "label": "Key passes /90",
            "short": "Key",
            "unit": "per90",
            "direction": "positive",
        },
        "dribbles_success_p90": {
            "label": "Dribbles /90",
            "short": "Dribbles",
            "unit": "per90",
            "direction": "positive",
        },
        "passes_completed_p90": {
            "label": "Passes /90",
            "short": "Passes",
            "unit": "per90",
            "direction": "positive",
        },
        "pass_completion_pct": {
            "label": "Pass completion",
            "short": "Pass %",
            "unit": "percent",
            "direction": "positive",
        },
        "tackles_p90": {
            "label": "Tackles /90",
            "short": "Tackles",
            "unit": "per90",
            "direction": "positive",
        },
        "interceptions_p90": {
            "label": "Interceptions /90",
            "short": "Intercepts",
            "unit": "per90",
            "direction": "positive",
        },
        "duel_win_pct": {
            "label": "Duels won",
            "short": "Duels %",
            "unit": "percent",
            "direction": "positive",
        },
        "saves_p90": {
            "label": "Saves /90",
            "short": "Saves",
            "unit": "per90",
            "direction": "positive",
        },
        "save_pct": {
            "label": "Save %",
            "short": "Save %",
            "unit": "percent",
            "direction": "positive",
        },
        "conceded_p90": {
            "label": "Conceded /90",
            "short": "Conceded",
            "unit": "per90",
            "direction": "negative",
        },
    },
    "overall": {
        "outfield": [
            "goals_p90",
            "assists_p90",
            "shots_p90",
            "key_passes_p90",
            "dribbles_success_p90",
            "passes_completed_p90",
            "pass_completion_pct",
            "tackles_p90",
            "interceptions_p90",
            "duel_win_pct",
        ],
        "goalkeeper": [
            "saves_p90",
            "save_pct",
            "conceded_p90",
            "passes_completed_p90",
            "pass_completion_pct",
        ],
    },
    "positions": {
        "goalkeeper": ["saves_p90", "save_pct", "conceded_p90", "pass_completion_pct"],
        "central_midfield": [
            "passes_completed_p90",
            "pass_completion_pct",
            "key_passes_p90",
            "assists_p90",
            "tackles_p90",
            "interceptions_p90",
            "goals_assists_p90",
        ],
    },
    "groups": {
        "goalkeeper": ["saves_p90", "save_pct", "conceded_p90", "pass_completion_pct"],
        "midfielder": [
            "passes_completed_p90",
            "pass_completion_pct",
            "key_passes_p90",
            "tackles_p90",
            "interceptions_p90",
            "dribbles_success_p90",
        ],
    },
}


def _row(player_id: int, *, family: str | None, group: str, **rates) -> dict:
    return {
        "player_id": player_id,
        "competition_id": "sco:premiership",
        "role_family": family,
        "position_group": group,
        "minutes": 900,
        "rates": rates,
    }


def _rates(**overrides) -> dict:
    rates = {
        "goals_p90": 0.2,
        "assists_p90": 0.1,
        "shots_p90": 1.0,
        "key_passes_p90": 1.0,
        "dribbles_success_p90": 1.0,
        "passes_completed_p90": 30.0,
        "pass_completion_pct": 80.0,
        "tackles_p90": 2.0,
        "interceptions_p90": 1.5,
        "duel_win_pct": 55.0,
        "saves_p90": 3.0,
        "save_pct": 75.0,
        "conceded_p90": 1.0,
    }
    rates.update(overrides)
    return rates


def test_rose_config_metrics_are_in_the_catalogue() -> None:
    all_metrics = list((CONFIG["overall"] or {}).values())
    all_metrics += list((CONFIG["positions"] or {}).values())
    all_metrics += list((CONFIG["groups"] or {}).values())
    configured = {metric for metrics in all_metrics for metric in metrics}
    assert configured <= set(CONFIG["catalogue"])


def test_conceded_p90_is_inverted() -> None:
    rows = [
        _row(index, family="goalkeeper", group="GK", **_rates(conceded_p90=1.0 + index * 0.2))
        for index in range(6)
    ]
    index = CohortIndex(rows, MODEL)
    low = build_rose(
        _rates(conceded_p90=0.5),
        minutes=900,
        league="sco:premiership",
        league_label="Scottish Premiership",
        family="goalkeeper",
        position_group="GK",
        index=index,
        model=MODEL,
        config=CONFIG,
        player_min_minutes=180,
        cohort_min_minutes=450,
    )
    high = build_rose(
        _rates(conceded_p90=3.0),
        minutes=900,
        league="sco:premiership",
        league_label="Scottish Premiership",
        family="goalkeeper",
        position_group="GK",
        index=index,
        model=MODEL,
        config=CONFIG,
        player_min_minutes=180,
        cohort_min_minutes=450,
    )
    low_axis = next(
        axis
        for figure in low["figures"]
        if figure["id"] == "overall"
        for axis in figure["axes"]
        if axis["metric"] == "conceded_p90"
    )
    high_axis = next(
        axis
        for figure in high["figures"]
        if figure["id"] == "overall"
        for axis in figure["axes"]
        if axis["metric"] == "conceded_p90"
    )
    assert low_axis["percentile"] > high_axis["percentile"]


def test_provider_group_fallback_is_labelled() -> None:
    rows = [
        _row(index, family=None, group="MID", **_rates(passes_completed_p90=20 + index))
        for index in range(6)
    ]
    index = CohortIndex(rows, MODEL)
    rose = build_rose(
        _rates(passes_completed_p90=25.0),
        minutes=900,
        league="sco:premiership",
        league_label="Scottish Premiership",
        family=None,
        position_group="MID",
        index=index,
        model=MODEL,
        config=CONFIG,
        player_min_minutes=180,
        cohort_min_minutes=450,
    )
    assert rose["basis"] == "provider_group"
    assert rose["status"] in {"available", "partial"}
    assert rose["figures"][1]["axes"]


def test_below_minutes_is_unavailable_not_zero() -> None:
    rose = build_rose(
        _rates(),
        minutes=100,
        league="sco:premiership",
        league_label="Scottish Premiership",
        family="goalkeeper",
        position_group="GK",
        index=CohortIndex([], MODEL),
        model=MODEL,
        config=CONFIG,
        player_min_minutes=180,
        cohort_min_minutes=450,
    )
    assert rose["status"] == "unavailable"
    assert rose["reason"] == "below_min_minutes"
    assert all(figure["status"] == "unavailable" for figure in rose["figures"])


def test_recent_matches_project_opponent_score_and_stats() -> None:
    appearances = [
        {
            "player_id": 7,
            "team_id": 252,
            "fixture_id": 100,
            "season": 2026,
            "date": "2026-10-17T14:00:00+00:00",
            "competition": "Premiership",
            "opponent": "ST Mirren",
            "minutes": 90,
        }
    ]
    stats = [
        {"player_id": 7, "team_id": 252, "fixture_id": 100, "rating": 7.1, "goals": 1, "assists": 0}
    ]
    matches = [
        {
            "match_id": "x",
            "season": "2026-27",
            "date": "2026-10-17",
            "home_team_name": "Aberdeen",
            "away_team_name": "ST Mirren",
            "home_goals": 3,
            "away_goals": 1,
        }
    ]
    rows = build_recent_matches(
        appearances,
        stats,
        matches,
        player_id=7,
        season="2026-27",
    )
    assert len(rows) == 1
    assert rows[0]["opponent"] == "St Mirren"
    assert rows[0]["score_for"] == 3
    assert rows[0]["score_against"] == 1
    assert rows[0]["result"] == "W"
    assert rows[0]["rating"] == 7.1


def test_actual_config_covers_every_role_family() -> None:
    config = load_player_rose()
    roles = roles_config()
    assert set(config["positions"]) == set(roles["families"])
    configured = set(config["catalogue"])
    for metrics in (config["overall"] or {}).values():
        assert set(metrics) <= configured
    for metrics in (config["positions"] or {}).values():
        assert set(metrics) <= configured
    for metrics in (config["groups"] or {}).values():
        assert set(metrics) <= configured
