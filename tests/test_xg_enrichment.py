from __future__ import annotations

from fitba.ingest.xg_enrichment import (
    derive_open_play_features,
    derive_penalty_counts,
    derive_penalty_counts_from_rows,
)
from fitba.normalize.teams import TeamRegistry


def _event(event_type: str, detail: str, team: str, comments: str = "") -> dict:
    return {
        "type": event_type,
        "detail": detail,
        "comments": comments,
        "team": {"name": team},
    }


def test_penalty_attempts_exclude_var_and_shootouts() -> None:
    teams = TeamRegistry()
    events = [
        _event("Goal", "Penalty", "Aberdeen"),
        _event("Goal", "Missed Penalty", "Aberdeen"),
        _event("Var", "Penalty confirmed", "Aberdeen"),
        _event("Goal", "Penalty", "Aberdeen", "Penalty Shootout"),
    ]
    counts = derive_penalty_counts(events, teams)
    row = counts["sco:aberdeen"]
    assert row["attempts"] == 2
    assert row["goals"] == 1
    assert row["missed"] == 1
    assert row["status"] == "available"


def test_open_play_features_remove_penalties_and_keep_partition() -> None:
    stats = {
        "shots": 11,
        "shots_on_target": 3,
        "shots_off": 4,
        "shots_blocked": 4,
        "shots_insidebox": 7,
        "shots_outsidebox": 4,
    }
    features = derive_open_play_features(
        stats,
        {"attempts": 1, "goals": 1, "missed": 0, "status": "available"},
        goals_for=2,
    )
    assert features["open_play_shots"] == 10
    assert features["open_play_sot"] == 2
    assert features["open_play_insidebox"] == 6
    assert features["open_play_sot"] + features["open_play_off"] + features[
        "open_play_blocked"
    ] == features["open_play_shots"]


def test_open_play_features_handle_missing_stats() -> None:
    features = derive_open_play_features(None, None, goals_for=None)
    assert features["shots"] is None
    assert features["zone_status"] == "unavailable"
    assert features["penalty_status"] == "stats_unavailable"


def test_penalty_counts_from_normalized_rows() -> None:
    teams = TeamRegistry()
    rows = [
        {
            "fixture_id": 1,
            "team_name": "Aberdeen",
            "event_type": "goal",
            "detail": "Penalty",
            "comments": None,
        },
        {
            "fixture_id": 1,
            "team_name": "Aberdeen",
            "event_type": "goal",
            "detail": "Missed Penalty",
            "comments": None,
        },
        {
            "fixture_id": 1,
            "team_name": "Aberdeen",
            "event_type": "var",
            "detail": "Penalty confirmed",
            "comments": None,
        },
    ]
    counts = derive_penalty_counts_from_rows(rows, teams)
    assert counts[(1, "sco:aberdeen")]["attempts"] == 2
