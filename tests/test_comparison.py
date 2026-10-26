from __future__ import annotations

import pytest

from fitba.publish.comparison import build_comparison_crosswalk

SQUAD = {
    "players": [
        {"player_id": 1141, "name": "M. Müller"},
        {"player_id": 108465, "name": "N. Guinness-Walker"},
        {"player_id": 57248, "name": "A. Aremu"},
    ]
}

PROFILE = [
    {
        "player_id": 1141,
        "name": "M. Müller",
        "role_family": "goalkeeper",
        "rating_percentile": 45.5,
        "cohort": {"basis": "role_family", "n": 11},
    },
    {
        "player_id": 108465,
        "name": "N. Guinness-Walker",
        "role_family": "full_back",
        "rating_percentile": 88.1,
        "cohort": {"basis": "role_family", "n": 21},
    },
]


def _row(player_id: int = 1141, **overrides) -> dict:
    row = {
        "player_key": f"api:player:{player_id}",
        "player_id": player_id,
        "league_slug": "sco-premiership",
        "role_family": "goalkeeper" if player_id == 1141 else "full_back",
        "cohort_basis": "role_family",
        "reviewed_by": "patrickmockridge",
        "reviewed_at": "2026-10-26",
        "notes": "Reviewed.",
    }
    row.update(overrides)
    return row


def _build(rows: list[dict]):
    return build_comparison_crosswalk(
        config={"reviewed": "2026-10-26", "owner": "owner", "players": rows},
        squad_data=SQUAD,
        scouting_squad=PROFILE,
    )


def test_a_reviewed_row_is_published_with_identity_fields_only() -> None:
    document = _build([_row()])
    assert document["state"] == "available"
    assert document["players"] == [
        {
            "player_id": 1141,
            "player_key": "api:player:1141",
            "league_slug": "sco-premiership",
            "role_family": "goalkeeper",
            "cohort_basis": "role_family",
            "reviewed_by": "patrickmockridge",
            "reviewed_at": "2026-10-26",
            "notes": "Reviewed.",
        }
    ]
    assert "minutes" not in document["players"][0]
    assert "percentile" not in document["players"][0]


def test_an_empty_allowlist_is_not_reviewed() -> None:
    document = _build([])
    assert document["state"] == "not_reviewed"
    assert document["players"] == []


def test_a_duplicate_or_unreviewed_row_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate or missing"):
        _build([_row(), _row()])
    with pytest.raises(ValueError, match="no reviewer"):
        _build([_row(reviewed_by="")])


def test_a_row_must_match_the_published_squad_and_role() -> None:
    with pytest.raises(ValueError, match="not on the current squad"):
        _build([_row(99)])
    with pytest.raises(ValueError, match="role_family does not match"):
        _build([_row(role_family="full_back")])
    with pytest.raises(ValueError, match="no published squad profile row"):
        _build([_row(57248, role_family="central_midfield")])


def test_only_the_premiership_league_is_accepted() -> None:
    with pytest.raises(ValueError, match="sco-premiership"):
        _build([_row(league_slug="eng-premier-league")])


def test_a_profiled_player_without_a_percentile_is_rejected() -> None:
    profile = [{**PROFILE[0], "rating_percentile": None}]
    with pytest.raises(ValueError, match="no published percentile"):
        build_comparison_crosswalk(
            config={"players": [_row()]},
            squad_data=SQUAD,
            scouting_squad=profile,
        )
