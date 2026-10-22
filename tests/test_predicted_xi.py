from __future__ import annotations

import polars as pl

from fitba.analytics.matchday import _score, predict_lineup, score_players, select_formation
from fitba.settings import matchday, roles

FORMATION = "4-2-3-1"
SLOTS = ["GK", "LB", "CB", "CB", "RB", "CM", "CM", "LW", "AM", "RW", "ST"]
FAMILY = {
    "GK": "goalkeeper",
    "LB": "full_back",
    "RB": "full_back",
    "CB": "centre_back",
    "CM": "central_midfield",
    "LW": "wide_forward",
    "RW": "wide_forward",
    "AM": "attacking_midfield",
    "ST": "centre_forward",
}
GRID = {
    0: "1:1",
    1: "2:1",
    2: "2:2",
    3: "2:3",
    4: "2:4",
    5: "3:1",
    6: "3:2",
    7: "4:1",
    8: "4:2",
    9: "4:3",
    10: "5:1",
}


def _appearance(
    *,
    fixture: int,
    player_id: int,
    role: str,
    started: bool = True,
    minutes: int = 90,
) -> dict:
    return {
        "fixture_id": fixture,
        "date": f"2026-08-{fixture:02d}",
        "player_id": player_id,
        "player_key": f"api:player:{player_id}",
        "player_name": f"Player {player_id}",
        "team_id": 252,
        "team_name": "Aberdeen",
        "started": started,
        "minutes": minutes,
        "role_code": role,
        "role_family": FAMILY.get(role),
        "grid": GRID.get(SLOTS.index(role)) if started else None,
        "formation": FORMATION if started else None,
        "goals": 0,
        "assists": 0,
        "yellow_cards": 0,
        "red_cards": 0,
        "shirt_number": player_id,
        "position": (
            "Goalkeeper"
            if role == "GK"
            else "Defender"
            if role in {"LB", "CB", "RB"}
            else "Midfielder"
            if role in {"CM", "AM"}
            else "Attacker"
        ),
    }


def _window(fixtures: int = 6):
    rows = []
    for fixture in range(1, fixtures + 1):
        for index, role in enumerate(SLOTS):
            rows.append(_appearance(fixture=fixture, player_id=index + 1, role=role))
        # Substitutes who can cover roles.
        for offset, role in enumerate(["CB", "CM", "ST", "LW"], start=12):
            rows.append(
                _appearance(
                    fixture=fixture,
                    player_id=offset,
                    role=role,
                    started=False,
                    minutes=20,
                )
            )
    return pl.DataFrame(rows)


def _shapes(fixtures: int = 6):
    return pl.DataFrame(
        [
            {
                "fixture_id": fixture,
                "date": f"2026-08-{fixture:02d}",
                "team_id": 252,
                "formation": FORMATION,
                "formation_shape": FORMATION,
            }
            for fixture in range(1, fixtures + 1)
        ]
    )


def _squad(injured: set[int] | None = None, loan_out: set[int] | None = None):
    injured = injured or set()
    loan_out = loan_out or set()
    return pl.DataFrame(
        [
            {
                "player_id": player_id,
                "name": f"Player {player_id}",
                "number": player_id,
                "position_group": (
                    "GK"
                    if player_id == 1
                    else "D"
                    if player_id <= 5
                    else "M"
                    if player_id <= 9
                    else "F"
                ),
                "injured": player_id in injured,
                "status": "loan_out" if player_id in loan_out else "squad",
            }
            for player_id in range(1, 16)
        ]
    )


def test_select_formation_uses_recency_weighted_mode():
    rows = pl.DataFrame(
        [
            {"date": "2026-08-01", "formation": "4-2-3-1"},
            {"date": "2026-08-02", "formation": "4-2-3-1"},
            {"date": "2026-08-03", "formation": "4-3-3"},
            {"date": "2026-08-04", "formation": "4-2-3-1"},
        ]
    )
    result = select_formation(rows, window=4)
    assert result["formation"] == "4-2-3-1"
    assert result["confidence"] in {"medium", "high"}


def test_select_formation_none_is_unknown():
    result = select_formation(pl.DataFrame(), window=6)
    assert result["formation"] is None
    assert result["confidence"] == "unknown"


def test_predicted_lineup_fills_eleven_unique_slots():
    result = predict_lineup(
        _window(),
        _shapes(),
        team_id=252,
        roles_config=roles(),
        policy=matchday()["prediction"],
        squad=_squad(),
        fixtures_total=6,
        include_squad_only=True,
    )
    assert result["status"] == "available"
    assert result["formation"] == FORMATION
    assert result["filled"] == 11
    player_ids = [player["player_id"] for player in result["players"]]
    assert len(player_ids) == 11
    assert len(set(player_ids)) == 11
    assert result["players"][0]["role_code"] == "GK"
    assert len(result["contenders"]) >= 4
    assert len(result["contenders"]) <= 6
    assert not set(player_ids) & {contender["player_id"] for contender in result["contenders"]}


def test_availability_out_and_loan_out_players_are_excluded():
    squad = _squad(loan_out={12})
    result = predict_lineup(
        _window(),
        _shapes(),
        team_id=252,
        roles_config=roles(),
        policy=matchday()["prediction"],
        squad=squad,
        fixtures_total=6,
        include_squad_only=True,
        availability={
            5: {
                "status": "out",
                "confidence": "confirmed",
                "source_id": "afc_news",
                "note": "Official team-news entry.",
            }
        },
        availability_state="partial",
    )
    player_ids = [player["player_id"] for player in result["players"]]
    assert 5 not in player_ids
    assert 12 not in player_ids
    unavailable = {item["player_id"] for item in result["unavailable"]}
    assert 5 in unavailable


def test_provider_injured_flag_alone_does_not_exclude():
    squad = _squad(injured={5})
    result = predict_lineup(
        _window(),
        _shapes(),
        team_id=252,
        roles_config=roles(),
        policy=matchday()["prediction"],
        squad=squad,
        fixtures_total=6,
        include_squad_only=True,
    )
    unavailable = {item["player_id"] for item in result["unavailable"]}
    assert 5 not in unavailable
    assert result["availability"]["state"] == "unavailable"


def test_low_coverage_downgrades_confidence():
    result = predict_lineup(
        _window(fixtures=1),
        _shapes(fixtures=1),
        team_id=252,
        roles_config=roles(),
        policy=matchday()["prediction"],
        squad=_squad(),
        fixtures_total=9,
        include_squad_only=True,
    )
    assert result["status"] == "unavailable"
    assert result["reason"] == "insufficient_lineups"


def test_no_formation_is_not_assumed():
    result = predict_lineup(
        _window(),
        pl.DataFrame(),
        team_id=252,
        roles_config=roles(),
        policy=matchday()["prediction"],
        squad=_squad(),
        fixtures_total=6,
        include_squad_only=True,
    )
    assert result["status"] == "unavailable"
    assert result["reason"] == "no_observed_formation"
    assert result["formation"] is None


def test_recent_ratings_are_a_selection_input():
    rows = []
    for fixture, rating_a, rating_b in [(1, 6.0, 8.0), (2, 6.2, 8.4)]:
        rows.append(
            {
                **_appearance(fixture=fixture, player_id=1, role="ST"),
                "rating": rating_a,
            }
        )
        rows.append(
            {
                **_appearance(fixture=fixture, player_id=2, role="ST"),
                "rating": rating_b,
            }
        )
    scored = score_players(pl.DataFrame(rows), window=2, include_squad_only=False)
    by_id = {player["player_id"]: player for player in scored["players"]}
    assert by_id[1]["recent_rating"] == 6.13
    assert by_id[2]["recent_rating"] == 8.27
    assert by_id[2]["rating_coverage"] == "available"
    assert by_id[2]["recent_rating_score"] > by_id[1]["recent_rating_score"]


def test_form_and_rating_weights_change_the_score():
    policy = matchday()["prediction"]
    low = {
        "start_rate": 0.5,
        "recency_start": 0.5,
        "minute_share": 0.5,
        "form": 0.1,
        "recent_rating_score": 0.1,
    }
    high = {
        "start_rate": 0.5,
        "recency_start": 0.5,
        "minute_share": 0.5,
        "form": 0.9,
        "recent_rating_score": 0.9,
    }
    assert _score(high, 0.5, policy) > _score(low, 0.5, policy)


def test_missing_rating_does_not_break_scoring():
    rows = [_appearance(fixture=1, player_id=1, role="ST")]
    scored = score_players(pl.DataFrame(rows), window=1, include_squad_only=False)
    player = scored["players"][0]
    assert player["recent_rating"] is None
    assert player["rating_coverage"] == "unavailable"
    assert _score(player, 1.0, matchday()["prediction"]) > 0


def test_unmapped_formation_is_unavailable():
    shapes = _shapes().with_columns(pl.lit("9-1-0").alias("formation"))
    result = predict_lineup(
        _window(),
        shapes,
        team_id=252,
        roles_config=roles(),
        policy=matchday()["prediction"],
        squad=_squad(),
        fixtures_total=6,
        include_squad_only=True,
    )
    assert result["status"] == "unavailable"
    assert result["reason"] == "formation_unmapped"
