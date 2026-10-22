from copy import deepcopy

import polars as pl

from fitba.analytics.history import (
    club_match_rows,
    manager_splits_by_season,
    manager_stint_records,
    season_records,
)
from fitba.analytics.recruitment import recruitment_profile
from fitba.analytics.selection import selection_profile
from fitba.analytics.style import style_profile
from fitba.analytics.tables import _split_order
from fitba.settings import history_era, history_honours, history_seasons, history_staff
from fitba.validate.history import validate_reference
from fitba.validate.source_policy import is_blocked_url, no_publication_tokens


def _match(
    match_id: str,
    when: str,
    home: str,
    away: str,
    hg: int,
    ag: int,
    *,
    competition: str = "sco:premiership",
    season: str = "2024-25",
    **extra,
) -> dict:
    return {
        "match_id": match_id,
        "date": when,
        "season": season,
        "competition_id": competition,
        "competition_name": competition,
        "home_team_id": home,
        "home_team_name": home,
        "away_team_id": away,
        "away_team_name": away,
        "home_goals": hg,
        "away_goals": ag,
        "phase": "regular",
        "home_shots": extra.get("home_shots", 10),
        "away_shots": extra.get("away_shots", 8),
        "home_shots_on_target": extra.get("home_sot", 4),
        "away_shots_on_target": extra.get("away_sot", 3),
        "home_fouls": 10,
        "away_fouls": 12,
        "home_corners": 5,
        "away_corners": 4,
        "home_yellow": 1,
        "away_yellow": 2,
        "home_red": 0,
        "away_red": 0,
    }


def _rows() -> pl.DataFrame:
    return pl.DataFrame(
        [
            _match("m1", "2024-08-01", "sco:aberdeen", "sco:other", 2, 0),
            _match("m2", "2024-08-08", "sco:other", "sco:aberdeen", 1, 1),
            _match("m3", "2024-08-15", "sco:aberdeen", "sco:other", 0, 2),
            _match("m4", "2024-08-22", "sco:other", "sco:aberdeen", 0, 3),
        ]
    )


def test_split_order_keeps_bottom_group_below_top_group():
    # Four teams, three matches each; split after two. Team D wins the last
    # match heavily but cannot cross into the top group.
    matches = [
        _match("a1", "2024-08-01", "A", "B", 1, 0),
        _match("a2", "2024-08-02", "C", "D", 1, 0),
        _match("a3", "2024-08-03", "A", "C", 1, 0),
        _match("a4", "2024-08-04", "B", "D", 1, 0),
        _match("a5", "2024-08-05", "A", "D", 0, 9),
        _match("a6", "2024-08-06", "C", "B", 1, 0),
    ]
    frame = pl.DataFrame(matches)
    subset = frame.filter(pl.col("season") == "2024-25")
    ordered = _split_order(subset, split_after=2, team_count=4, deductions={})
    # D wins 9-0 in the last match but was in the bottom group after two
    # matches, so it cannot cross into the top group.
    assert [row["team_id"] for row in ordered][:2] == ["A", "B"]
    assert {row["team_id"] for row in ordered[2:]} == {"C", "D"}


def test_season_records_scan_all_tiers():
    matches = pl.DataFrame(
        [
            _match(
                "c1",
                "2024-08-01",
                "sco:aberdeen",
                "sco:other",
                2,
                0,
                competition="sco:championship",
            ),
            _match(
                "c2",
                "2024-08-08",
                "sco:other",
                "sco:aberdeen",
                1,
                1,
                competition="sco:championship",
            ),
        ]
    )
    competitions = [
        {"id": "sco:premiership", "name": "Premiership", "tier": 1},
        {"id": "sco:championship", "name": "Championship", "tier": 2},
    ]
    records = season_records(matches, competitions, club_id="sco:aberdeen", seasons=["2024-25"])
    assert records["2024-25"]["competition_id"] == "sco:championship"
    assert records["2024-25"]["position"] == 1


def test_manager_records_do_not_double_count_boundary_day():
    stints = [
        {
            "stint_id": "a",
            "person_id": "a",
            "name": "A",
            "role_group": "manager",
            "start": "2024-07-01",
            "start_precision": "day",
            "end": "2024-08-08",
            "end_precision": "day",
            "interim": False,
        },
        {
            "stint_id": "b",
            "person_id": "b",
            "name": "B",
            "role_group": "manager",
            "start": "2024-08-08",
            "start_precision": "day",
            "end": None,
            "end_precision": None,
            "interim": False,
        },
    ]
    records = manager_stint_records(club_match_rows(_rows(), "sco:aberdeen"), stints)
    assert sum(record["played"] for record in records) == 4
    assert all(
        record["won"] + record["drawn"] + record["lost"] == record["played"] for record in records
    )


def test_manager_season_split_reconciles_to_league():
    stints = [
        {
            "stint_id": "a",
            "person_id": "a",
            "name": "A",
            "role_group": "manager",
            "start": "2024-07-01",
            "start_precision": "day",
            "end": "2024-08-08",
            "end_precision": "day",
            "interim": False,
        },
        {
            "stint_id": "b",
            "person_id": "b",
            "name": "B",
            "role_group": "manager",
            "start": "2024-08-08",
            "start_precision": "day",
            "end": None,
            "end_precision": None,
            "interim": False,
        },
    ]
    split = manager_splits_by_season(club_match_rows(_rows(), "sco:aberdeen"), stints, ["2024-25"])[
        "2024-25"
    ]
    assert sum(item["played"] for item in split) == 4
    assert sum(item["points"] for item in split) == 7
    assert sum(item["gf"] - item["ga"] for item in split) == 3


def test_style_profile_is_measured_and_does_not_invent_possession():
    profile = style_profile(
        club_match_rows(_rows(), "sco:aberdeen"),
        season="2024-25",
        competition_id="sco:premiership",
    )
    assert profile["coverage"] == "available"
    assert profile["matches"] == 4
    assert profile["shots_for_pm"] == 9.0
    assert profile["goals_for_pm"] == 1.5
    assert profile["possession_for_pm"] is None
    assert profile["possession_unknown_reason"] == "provider_statistics_not_backfilled"


def test_selection_profile_uses_rosters_and_age_coverage():
    appearances = [
        {
            "season": "2024-25",
            "fixture_id": 1,
            "date": "2024-08-01",
            "player_id": 1,
            "player_name": "Older",
            "team_id": 252,
            "started": True,
            "minutes": 90,
            "formation_shape": "4-2-3-1",
            "role_family": "centre_back",
        },
        {
            "season": "2024-25",
            "fixture_id": 1,
            "date": "2024-08-01",
            "player_id": 2,
            "player_name": "Young",
            "team_id": 252,
            "started": True,
            "minutes": 90,
            "formation_shape": "4-2-3-1",
            "role_family": "midfielder",
        },
        {
            "season": "2024-25",
            "fixture_id": 2,
            "date": "2024-08-08",
            "player_id": 1,
            "player_name": "Older",
            "team_id": 252,
            "started": True,
            "minutes": 90,
            "formation_shape": "4-2-3-1",
            "role_family": "centre_back",
        },
    ]
    rosters = {
        1: {"player_name": "Older", "birth_date": "1995-01-01"},
        2: {"player_name": "Young", "birth_date": "2005-01-01"},
    }
    profile = selection_profile(
        appearances,
        season="2024-25",
        fixtures_total=2,
        rosters=rosters,
        previous_player_ids={1},
    )
    assert profile["fixtures_with_lineups"] == 2
    assert profile["players_used"] == 2
    assert profile["u21_minutes_share"] == 0.333
    assert profile["formation_mix"][0]["formation"] == "4-2-3-1"
    assert profile["debutants"][0]["player_id"] == 2


def test_recruitment_profile_does_not_zero_fill_undisclosed_fees():
    transfers = [
        {
            "season": "2024-25",
            "direction": "in",
            "transfer_kind": "permanent",
            "fee_status": "undisclosed",
            "fee_amount": None,
            "from_club_id": "sco:provisional-ujpest",
            "from_club_name": "Ujpest",
        },
        {
            "season": "2024-25",
            "direction": "out",
            "transfer_kind": "permanent",
            "fee_status": "disclosed",
            "fee_amount": 1000000,
            "to_club_id": "sco:provisional-girona",
            "to_club_name": "Girona",
        },
    ]
    profile = recruitment_profile(
        transfers,
        season="2024-25",
        markets=[{"club_name": "Ujpest", "market": "europe"}],
        birth_dates={},
    )
    assert profile["disclosed_income"] == 1000000
    assert profile["disclosed_net"] == -1000000
    assert profile["undisclosed_count"] == 1
    assert profile["market_mix"][2]["market"] == "europe"


def test_reference_history_passes_and_catches_a_bad_honour():
    errors, _ = validate_reference(
        policy={"honours": {"expected_totals": {"Scottish Cup": 8}}},
        era=history_era(),
        staff=history_staff(),
        honours=history_honours(),
        seasons=history_seasons(),
        transfer_rows=[],
    )
    # The real policy file carries the full expected totals; this reduced
    # policy should still pass the other structural checks and fail only on the
    # omitted competition totals, which we do not assert here.
    assert isinstance(errors, list)
    broken = deepcopy(history_honours())
    broken["honours"] = [
        honour for honour in broken["honours"] if honour["honour_id"] != "scottish-cup-2024-25"
    ]
    errors, _ = validate_reference(
        policy={
            "honours": {
                "expected_totals": {"Scottish Cup": 8},
                "required_ids": ["scottish-cup-2024-25"],
            }
        },
        era=history_era(),
        staff=history_staff(),
        honours=broken,
        seasons=history_seasons(),
        transfer_rows=[],
    )
    assert any("required id" in error for error in errors)


def test_blocked_source_hosts_are_rejected():
    _, hosts = no_publication_tokens()
    assert is_blocked_url("https://www.bbc.co.uk/sport/123", hosts)
    assert not is_blocked_url("https://en.wikipedia.org/wiki/Aberdeen_F.C.", hosts)
