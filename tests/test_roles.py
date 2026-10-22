from fitba.ingest.match_data import playing_time_for, role_block_for
from fitba.normalize.roles import (
    formation_family,
    primary_role,
    role_for_grid,
    shape_counts,
    shape_from_formation,
    shape_from_grid,
    shape_key,
    validate_config,
)
from fitba.settings import roles as roles_config

CONFIG = roles_config()
GRID_4231 = ["1:1", "2:1", "2:2", "2:3", "2:4", "3:1", "3:2", "4:1", "4:2", "4:3", "5:1"]


def test_formation_maps_to_grid_slots():
    shape = shape_from_formation("4-2-3-1")
    assert shape == (1, 4, 2, 3, 1)
    assert role_for_grid(CONFIG, shape, "2:1") == "LB"
    assert role_for_grid(CONFIG, shape, "2:2") == "CB"
    assert role_for_grid(CONFIG, shape, "2:4") == "RB"
    assert role_for_grid(CONFIG, shape, "4:2") == "AM"
    assert role_for_grid(CONFIG, shape, "4:3") == "RW"
    assert role_for_grid(CONFIG, shape, "5:1") == "ST"


def test_grid_shape_requires_a_full_xi_with_a_keeper():
    assert shape_from_grid(GRID_4231) == (1, 4, 2, 3, 1)
    assert shape_from_grid(GRID_4231[:-1]) is None
    assert shape_from_grid([None, *GRID_4231[1:]]) is None
    alternate = shape_from_grid([*GRID_4231[:-1], "5:2"])
    assert alternate is not None
    assert shape_key(alternate) == "4-2-3-1"


def test_grid_shape_rejects_malformed_or_non_contiguous_rows():
    assert shape_from_grid([*GRID_4231[:5], "9:1", *GRID_4231[6:]]) is None
    assert shape_from_grid([*GRID_4231[:5], "x", *GRID_4231[6:]]) is None


def test_null_or_unmapped_grid_is_unknown_not_guessed():
    shape = shape_from_formation("4-2-3-1")
    assert role_for_grid(CONFIG, shape, None) is None
    assert role_for_grid(CONFIG, "9-1", "2:1") is None
    assert role_for_grid(CONFIG, None, "2:1") is None


def test_formation_string_and_grid_shape_agree():
    for formation, shape in (
        ("4-2-3-1", (1, 4, 2, 3, 1)),
        ("4-1-4-1", (1, 4, 1, 4, 1)),
        ("3-5-2", (1, 3, 5, 2)),
        ("5-3-2", (1, 5, 3, 2)),
        ("4-1-3-2", (1, 4, 1, 3, 2)),
    ):
        assert shape_from_formation(formation) == shape
        assert shape_key(shape) == formation
        assert formation_family(shape) in {"back_three", "back_four", "back_five"}


def test_shape_counts_follow_the_role_map():
    counts = shape_counts(CONFIG, "5-3-2")
    assert counts["cb_count"] == 3
    assert counts["wing_back_count"] == 2
    assert counts["dm_count"] == 0
    assert counts["forward_count"] == 2
    counts = shape_counts(CONFIG, "4-1-4-1")
    assert counts["cb_count"] == 2
    assert counts["dm_count"] == 1
    assert counts["forward_count"] == 1


def test_primary_role_uses_family_then_minutes_then_order():
    cadden = [
        {"code": "RB", "starts": 6, "minutes": 523},
        {"code": "RWB", "starts": 4, "minutes": 360},
        {"code": "AM", "starts": 1, "minutes": 116},
    ]
    assert primary_role(cadden, CONFIG) == ("RB", "full_back")
    olusanya = [
        {"code": "AM", "starts": 2, "minutes": 180},
        {"code": "RW", "starts": 2, "minutes": 177},
        {"code": "ST", "starts": 2, "minutes": 146},
        {"code": "LW", "starts": 1, "minutes": 71},
    ]
    assert primary_role(olusanya, CONFIG) == ("RW", "wide_forward")
    ntelo = [
        {"code": "ST", "starts": 2, "minutes": 92},
        {"code": "RW", "starts": 2, "minutes": 129},
    ]
    assert primary_role(ntelo, CONFIG) == ("RW", "wide_forward")


def test_role_config_is_valid_and_roles_have_consistent_side():
    validate_config(CONFIG)
    for code, role in CONFIG["roles"].items():
        assert role["family"] in CONFIG["families"], code
        assert role["side"] in {None, "left", "right", "central"}, code


def test_role_block_unknown_without_starts():
    block = role_block_for(
        [],
        player_id=1,
        team_id=252,
        season_year=2026,
        starts_total=0,
        config=CONFIG,
    )
    assert block["status"] == "unknown"
    assert block["primary"] is None
    assert block["unknown_reason"] == "no_starting_xi_role"


def test_role_block_derives_side_from_the_primary_role():
    rows = [
        {
            "player_id": 1,
            "team_id": 252,
            "season": 2026,
            "role_code": "RB",
            "role_family": "full_back",
            "starts": 6,
            "minutes": 523,
        },
        {
            "player_id": 1,
            "team_id": 252,
            "season": 2026,
            "role_code": "RWB",
            "role_family": "wing_back",
            "starts": 4,
            "minutes": 360,
        },
    ]
    block = role_block_for(
        rows,
        player_id=1,
        team_id=252,
        season_year=2026,
        starts_total=10,
        config=CONFIG,
    )
    assert block["code"] == "RB"
    assert block["side"] == "right"
    assert block["status"] == "observed"
    assert block["coverage"] == "10/10"
    assert block["roles"][0]["starts"] == 6


def test_playing_time_splits_starts_and_subs():
    rows = [
        {
            "player_id": 1,
            "team_id": 252,
            "season": 2026,
            "competition": "Premiership",
            "starts": 2,
            "sub_apps": 1,
            "minutes": 210,
            "minutes_started": 180,
            "minutes_as_sub": 30,
        },
        {
            "player_id": 1,
            "team_id": 252,
            "season": 2026,
            "competition": "League Cup",
            "starts": 1,
            "sub_apps": 0,
            "minutes": 90,
            "minutes_started": 90,
            "minutes_as_sub": 0,
        },
    ]
    block = playing_time_for(rows, player_id=1, team_id=252, season_year=2026)
    assert block["starts"] == 3
    assert block["sub_apps"] == 1
    assert block["minutes"] == 300
    assert block["minutes_started"] == 270
    assert block["minutes_as_sub"] == 30
    assert len(block["by_competition"]) == 2
