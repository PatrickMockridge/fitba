from __future__ import annotations

from fitba.analytics.scouting import CohortIndex


def _row(player_id: int, name: str, *, minutes: int = 600) -> dict:
    return {
        "player_id": player_id,
        "name": name,
        "competition_id": "sco:premiership",
        "role_family": "centre_back",
        "position_group": "DEFENDER",
        "minutes": minutes,
        "rating": 7.0,
        "rates": {"goals_p90": 0.1},
    }


def test_aberdeen_is_excluded_from_its_own_cohort() -> None:
    rows = [_row(1, "Aberdeen Player"), _row(2, "League Player")]
    index = CohortIndex(rows, {}, exclude_player_ids={1})
    names = [row["name"] for row in index.players(
        "sco:premiership", "centre_back", min_minutes=450
    )]
    assert names == ["League Player"]
    assert len(index.values("sco:premiership", "centre_back", "goals_p90", min_minutes=450)) == 1


def test_without_an_exclusion_the_cohort_keeps_every_row() -> None:
    rows = [_row(1, "Aberdeen Player"), _row(2, "League Player")]
    index = CohortIndex(rows, {})
    names = [row["name"] for row in index.players(
        "sco:premiership", "centre_back", min_minutes=450
    )]
    assert names == ["Aberdeen Player", "League Player"]


def test_the_minimum_minutes_gate_still_applies_after_exclusion() -> None:
    rows = [_row(1, "Aberdeen Player"), _row(2, "League Player", minutes=100)]
    index = CohortIndex(rows, {}, exclude_player_ids={1})
    assert index.players("sco:premiership", "centre_back", min_minutes=450) == []
