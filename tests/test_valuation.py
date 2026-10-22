from fitba.analytics.valuation import (
    calibration_factor,
    estimate_transfer,
    parse_fee,
    summarise_valuations,
)


def test_parse_disclosed_reported_free_and_loan():
    assert (
        parse_fee({"fee_status": "disclosed", "fee_amount": 4_200_000, "fee_currency": "GBP"})[0]
        == 4_200_000
    )
    assert parse_fee({"fee_status": "undisclosed", "fee_raw": "Reported £3m"})[0] == 3_000_000
    assert parse_fee({"fee_status": "undisclosed", "fee_raw": "€ 300K"})[0] == 255_000
    assert parse_fee({"fee_status": "free", "fee_raw": "Free"})[0] == 0
    assert parse_fee({"fee_status": "loan", "fee_raw": "Loan"})[0] is None


def test_estimate_transfer_gives_range_not_point():
    estimate = estimate_transfer(
        {
            "player_key": "api:player:1",
            "direction": "out",
            "transfer_kind": "permanent",
            "to_club_id": "sco:provisional-girona",
            "to_club_name": "Girona",
            "position": "Attacker",
            "date_effective": "2024-08-15",
            "fee_status": "undisclosed",
            "fee_raw": "",
        },
        birth_dates={"api:player:1": "1999-06-01"},
        markets=[{"club_name": "Girona", "market": "europe"}],
        calibration=1.0,
    )
    assert estimate["basis"] == "modelled"
    assert estimate["fee_low_gbp"] < estimate["fee_high_gbp"]
    assert estimate["confidence"] in {"medium", "low"}
    assert estimate["market_value_low_gbp"] <= estimate["market_value_high_gbp"]


def test_free_transfer_has_zero_fee_but_a_value():
    estimate = estimate_transfer(
        {
            "player_key": "api:player:2",
            "direction": "in",
            "transfer_kind": "free",
            "from_club_id": "sco:provisional-ujpest",
            "from_club_name": "Ujpest",
            "position": "Midfielder",
            "date_effective": "2024-07-01",
            "fee_status": "free",
            "fee_raw": "Free",
        },
        birth_dates={"api:player:2": "1998-01-01"},
        markets=[{"club_name": "Ujpest", "market": "europe"}],
        calibration=1.0,
    )
    assert estimate["basis"] == "free"
    assert estimate["fee_low_gbp"] == 0
    assert estimate["fee_high_gbp"] == 0
    assert estimate["market_value_high_gbp"] > 0


def test_loan_fee_is_unknown_and_excluded_from_net():
    estimate = estimate_transfer(
        {
            "player_key": "api:player:3",
            "direction": "in",
            "transfer_kind": "loan",
            "from_club_id": "sco:provisional-millwall",
            "from_club_name": "Millwall",
            "position": "Attacker",
            "date_effective": "2024-08-01",
            "fee_status": "loan",
            "fee_raw": "Loan",
        },
        birth_dates={"api:player:3": "1997-01-01"},
        markets=[{"club_name": "Millwall", "market": "england"}],
        calibration=1.0,
    )
    assert estimate["basis"] == "loan"
    assert estimate["fee_low_gbp"] is None
    summary = summarise_valuations(
        [
            {
                "direction": "in",
                "transfer_kind": "loan",
                "fee_estimate": estimate,
            }
        ]
    )
    assert summary["counts"]["loan"] == 1
    assert summary["fee_low_gbp"] == 0
    assert summary["fee_high_gbp"] == 0


def test_calibration_uses_reported_anchors():
    rows = [
        {
            "direction": "out",
            "transfer_kind": "permanent",
            "to_club_id": "sco:provisional-liverpool",
            "to_club_name": "Liverpool",
            "position": "Defender",
            "date_effective": "2022-06-19",
            "fee_status": "undisclosed",
            "fee_raw": "Reported £3m",
            "player_key": "api:player:4",
        }
    ]
    factor, anchors = calibration_factor(
        rows,
        birth_dates={"api:player:4": "2003-06-01"},
        markets=[{"club_name": "Liverpool", "market": "england"}],
    )
    assert anchors == 1
    assert factor == 1.0


def test_net_range_signs_and_confidence():
    incoming = estimate_transfer(
        {
            "player_key": "api:player:5",
            "direction": "in",
            "transfer_kind": "permanent",
            "from_club_id": "sco:provisional-ujpest",
            "from_club_name": "Ujpest",
            "position": "Midfielder",
            "date_effective": "2024-07-01",
            "fee_status": "undisclosed",
            "fee_raw": "",
        },
        birth_dates={"api:player:5": "1998-01-01"},
        markets=[{"club_name": "Ujpest", "market": "europe"}],
        calibration=1.0,
    )
    outgoing = estimate_transfer(
        {
            "player_key": "api:player:6",
            "direction": "out",
            "transfer_kind": "permanent",
            "to_club_id": "sco:provisional-girona",
            "to_club_name": "Girona",
            "position": "Attacker",
            "date_effective": "2024-08-15",
            "fee_status": "disclosed",
            "fee_amount": 6_800_000,
            "fee_currency": "GBP",
        },
        birth_dates={"api:player:6": "1999-06-01"},
        markets=[{"club_name": "Girona", "market": "europe"}],
        calibration=1.0,
    )
    summary = summarise_valuations(
        [
            {"direction": "in", "transfer_kind": "permanent", "fee_estimate": incoming},
            {"direction": "out", "transfer_kind": "permanent", "fee_estimate": outgoing},
        ]
    )
    assert summary["fee_low_gbp"] < 0
    assert summary["fee_high_gbp"] < 0
    assert summary["counts"]["disclosed"] == 1
    assert summary["counts"]["modelled"] == 1
