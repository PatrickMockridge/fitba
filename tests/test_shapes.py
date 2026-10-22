import polars as pl

from fitba.publish import shapes as shapes_module
from fitba.publish.shapes import shape_payload


def _frame(rows):
    return pl.DataFrame(rows)


def test_shape_payload_splits_kickoff_shape_and_reported_switches(monkeypatch):
    team_shapes = _frame(
        [
            {
                "team_id": 252,
                "team_name": "Aberdeen",
                "fixture_id": 1,
                "competition": "Premiership",
                "season": 2026,
                "date": "2026-08-01",
                "opponent": "Hearts",
                "formation": "4-2-3-1",
                "formation_shape": "4-2-3-1",
                "shape_family": "back_four",
                "cb_count": 2,
                "dm_count": 0,
                "goals_for": 2,
                "goals_against": 1,
                "result": "W",
                "saves": 3,
            },
            {
                "team_id": 252,
                "team_name": "Aberdeen",
                "fixture_id": 2,
                "competition": "Premiership",
                "season": 2026,
                "date": "2026-08-08",
                "opponent": "Dundee",
                "formation": "5-3-2",
                "formation_shape": "5-3-2",
                "shape_family": "back_five",
                "cb_count": 3,
                "dm_count": 0,
                "goals_for": 0,
                "goals_against": 2,
                "result": "L",
                "saves": 5,
            },
        ]
    )
    appearances = _frame(
        [
            {
                "team_id": 252,
                "season": 2026,
                "fixture_id": 1,
                "player_id": 10,
                "role_family": "centre_back",
                "started": True,
            },
            {
                "team_id": 252,
                "season": 2026,
                "fixture_id": 2,
                "player_id": 10,
                "role_family": "centre_back",
                "started": True,
            },
            {
                "team_id": 252,
                "season": 2026,
                "fixture_id": 2,
                "player_id": 11,
                "role_family": "centre_back",
                "started": True,
            },
            {
                "team_id": 252,
                "season": 2026,
                "fixture_id": 2,
                "player_id": 12,
                "role_family": "centre_back",
                "started": True,
            },
        ]
    )
    match_stats = _frame(
        [
            {"team_id": 252, "season": 2026, "fixture_id": 1, "player_id": 10, "rating": 7.0},
            {"team_id": 252, "season": 2026, "fixture_id": 2, "player_id": 10, "rating": 6.0},
            {"team_id": 252, "season": 2026, "fixture_id": 2, "player_id": 11, "rating": 6.5},
            {"team_id": 252, "season": 2026, "fixture_id": 2, "player_id": 12, "rating": 7.0},
        ]
    )
    monkeypatch.setattr(shapes_module, "load_team_shapes", lambda: team_shapes)
    monkeypatch.setattr(shapes_module, "load_player_appearances", lambda: appearances)
    monkeypatch.setattr(shapes_module, "load_player_match_stats", lambda: match_stats)
    monkeypatch.setattr(
        shapes_module,
        "load_match_meta",
        lambda: {"fixtures_with_grid": 2},
    )
    monkeypatch.setattr(
        shapes_module,
        "shape_notes",
        lambda: {
            "matches": [
                {
                    "fixture_id": 1,
                    "team_id": 252,
                    "minute": 60,
                    "from_shape": "4-2-3-1",
                    "to_shape": "4-4-2",
                    "source_url": "https://example.com/match",
                    "confidence": "reported",
                    "note": "Changed to a back four.",
                }
            ]
        },
    )

    payload = shape_payload(team_id=252, season_year=2026)
    assert payload["coverage"]["fixtures_with_shape"] == 2
    assert payload["coverage"]["fixtures_with_saves"] == 2
    assert payload["coverage"]["fixtures_with_cb_ratings"] == 2
    assert sum(row["matches"] for row in payload["formations"]) == 2
    by_shape = {row["formation"]: row for row in payload["formations"]}
    assert by_shape["4-2-3-1"]["cb_rating"] == 7.0
    assert by_shape["5-3-2"]["cb_rating"] == 6.5
    assert by_shape["5-3-2"]["saves_per_match"] == 5.0
    assert len(payload["matchday"]) == 2
    assert len(payload["reported_switches"]) == 1
    assert payload["reported_switches"][0]["from_shape"] == "4-2-3-1"
