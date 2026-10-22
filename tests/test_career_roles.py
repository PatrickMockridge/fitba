from fitba.normalize.career import (
    career_role_summary,
    choose_display_role,
    current_role_slots,
    override_conditions,
)
from fitba.normalize.roles import role_family
from fitba.settings import roles as roles_config

CONFIG = roles_config()


def _row(
    code: str,
    starts: int,
    *,
    season: str = "2025-26",
    team: str = "Previous FC",
    scope: str = "previous_club",
) -> dict:
    return {
        "role_code": code,
        "role_family": role_family(CONFIG, code),
        "starts": starts,
        "season": season,
        "team_id": 10,
        "team_name": team,
        "scope": scope,
        "competition": "League",
    }


def _career(rows: list[dict], *, starts_total: int | None = None):
    total = sum(int(row["starts"]) for row in rows) if starts_total is None else starts_total
    return career_role_summary(
        rows,
        starts_total=total,
        starts_with_role=sum(int(row["starts"]) for row in rows),
        config=CONFIG,
        current_season="2026-27",
    )


def _current(code: str, starts: int, *, status: str = "observed") -> dict:
    family = role_family(CONFIG, code)
    return {
        "primary": CONFIG["roles"][code]["label"],
        "code": code,
        "family": family,
        "side": CONFIG["roles"][code]["side"],
        "status": status,
        "starts_with_role": starts,
        "starts_total": starts,
        "coverage": f"{starts}/{starts}",
        "roles": [
            {
                "code": code,
                "label": CONFIG["roles"][code]["label"],
                "family": family,
                "starts": starts,
                "minutes": starts * 90,
            }
        ],
        "unknown_reason": None,
        "source": {"id": "api_football", "method": "starting_xi_grid"},
    }


def _unknown_current() -> dict:
    return {
        "primary": None,
        "code": None,
        "family": None,
        "side": None,
        "status": "unknown",
        "starts_with_role": 0,
        "starts_total": 0,
        "coverage": "0/0",
        "roles": [],
        "unknown_reason": "no_starting_xi_role",
        "source": None,
    }


def test_equal_weighting_does_not_prefer_aberdeen():
    career = _career(
        [
            _row("CB", 10, season="2026-27", team="Aberdeen", scope="aberdeen"),
            _row("CB", 30, season="2025-26"),
        ]
    )
    assert career["status"] == "observed"
    assert career["dominant"]["code"] == "CB"
    assert career["dominant"]["share"] == 1.0
    current = _current("CB", 10)
    display = choose_display_role(current, career, config=CONFIG)
    assert display["source"] == "career"


def test_stray_starts_do_not_change_the_career_role():
    career = _career([_row("CB", 20), _row("ST", 1)])
    assert career["dominant"]["code"] == "CB"
    assert career["dominant"]["share"] > 0.9
    assert career["status"] == "observed"
    assert career["secondary"] == []


def test_low_evidence_is_provisional():
    career = _career([_row("CB", 3)])
    assert career["status"] == "low_evidence"
    assert career["dominant"]["provisional"] is True
    assert choose_display_role(_unknown_current(), career, config=CONFIG)["source"] == (
        "career_low_evidence"
    )


def test_even_split_is_mixed_not_a_false_primary():
    career = _career([_row("CB", 5), _row("CM", 5)])
    assert career["status"] == "mixed"
    assert career["dominant"] is not None
    display = choose_display_role(_current("CM", 5), career, config=CONFIG)
    assert display["source"] == "current_season"


def test_aberdeen_override_requires_a_clear_group_change():
    career = _career(
        [
            _row("CB", 15, season="2025-26"),
            _row("CB", 15, season="2024-25"),
        ]
    )
    current = _current("ST", 8)
    conditions = override_conditions(current, career, config=CONFIG)
    assert conditions["passes"] is True
    display = choose_display_role(current, career, config=CONFIG)
    assert display["source"] == "aberdeen_override"
    assert display["code"] == "ST"
    assert display["career_dominant"]["code"] == "CB"


def test_small_or_near_neighbour_current_sample_does_not_override():
    career = _career(
        [
            _row("CB", 15, season="2025-26"),
            _row("CB", 15, season="2024-25"),
        ]
    )
    small = _current("ST", 4)
    assert override_conditions(small, career, config=CONFIG)["passes"] is False
    near_neighbour = _current("LB", 8)
    assert override_conditions(near_neighbour, career, config=CONFIG)["passes"] is False


def test_no_aberdeen_starts_uses_the_career_role():
    career = _career([_row("RB", 12, scope="previous_club")])
    display = choose_display_role(_unknown_current(), career, config=CONFIG)
    assert display["source"] == "career"
    assert display["code"] == "RB"


def test_loan_club_evidence_is_career_evidence():
    career = _career([_row("DM", 9, season="2026-27", team="Loan FC", scope="loan_club")])
    display = choose_display_role(_unknown_current(), career, config=CONFIG)
    assert display["source"] == "career"
    assert display["family"] == "defensive_midfield"
    assert career["scopes"][0]["scope"] == "loan_club"


def test_unknown_everywhere_returns_no_display_role():
    career = _career([])
    display = choose_display_role(_unknown_current(), career, config=CONFIG)
    assert career["status"] == "unknown"
    assert display["source"] == "none"
    assert display["code"] is None


def test_full_back_and_wing_back_are_one_slot_and_two_groups():
    career = _career([_row("LB", 6), _row("LWB", 4), _row("CB", 1)])
    assert career["primary_slot"]["slot"] == "D_WB_L"
    assert career["primary_slot"]["groups"] == ["defender", "midfielder"]
    assert career["primary_slot"]["side"] == "left"
    assert career["fm_label"].startswith("D/WB L")
    assert any(row["slot"] == "D_C" and row["tier"] == "stretch" for row in career["slots"])


def test_dm_and_centre_mid_combine_on_the_same_side():
    career = _career([_row("DM", 6), _row("CM", 4)])
    assert career["primary_slot"]["slot"] == "DM_C"
    assert "DM/M C" in career["fm_label"]
    assert any(row["slot"] == "M_C" and row["tier"] == "secondary" for row in career["slots"])


def test_stretch_start_is_visible_but_not_primary():
    career = _career([_row("CB", 20), _row("ST", 1)])
    assert career["primary_slot"]["slot"] == "D_C"
    assert career["stretch_slots"][0]["slot"] == "ST_C"
    assert "defender" in career["broad_groups"]
    assert "attacker" in career["broad_groups"]


def test_olusanya_current_usage_overrides_career_striker():
    career = _career(
        [
            _row("ST", 6, season="2025-26"),
            _row("ST", 5, season="2024-25"),
        ]
    )
    current = {
        "primary": "Right winger",
        "code": "RW",
        "family": "wide_forward",
        "side": "right",
        "status": "observed",
        "starts_with_role": 7,
        "starts_total": 8,
        "coverage": "7/8",
        "roles": [
            {"code": "RW", "family": "wide_forward", "starts": 2, "minutes": 177},
            {"code": "AM", "family": "attacking_midfield", "starts": 2, "minutes": 180},
            {"code": "ST", "family": "centre_forward", "starts": 2, "minutes": 146},
            {"code": "LW", "family": "wide_forward", "starts": 1, "minutes": 71},
        ],
        "unknown_reason": None,
        "source": {"id": "api_football", "method": "starting_xi_grid"},
    }
    slots = current_role_slots(current, config=CONFIG)
    assert slots["primary_slot"]["slot"] == "AM_R"
    assert "AM R" in slots["fm_label"]
    conditions = override_conditions(current, career, config=CONFIG)
    assert conditions["passes"] is True
    display = choose_display_role(current, career, config=CONFIG)
    assert display["source"] == "aberdeen_override"
    assert display["code"] == "RW"
    assert career["primary_slot"]["slot"] == "ST_C"
