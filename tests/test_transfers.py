from datetime import date

from fitba.ingest.transfers import (
    _dedupe,
    _excluded_candidate_ids,
    _is_pseudo_team,
    _parse_type,
    _transfer_season,
    _window_for,
)


def test_parse_transfer_types_and_fee_hints():
    assert _parse_type("Loan")[0:2] == ("loan", "loan")
    assert _parse_type("Return from loan")[0:2] == ("loan_return", "loan")
    assert _parse_type("Free agent")[0:2] == ("free", "free")
    assert _parse_type("Raise")[0] == "noise"
    assert _parse_type("Transfer")[0:2] == ("permanent", "unknown")
    kind, status, amount, currency, raw = _parse_type("€ 1M")
    assert (kind, status, amount, currency) == ("permanent", "feed_hint", 1_000_000, "EUR")
    assert raw == "€ 1M"


def test_transfer_season_puts_summer_may_june_in_the_new_season():
    assert _transfer_season(date(2024, 5, 29)) == "2024-25"
    assert _transfer_season(date(2024, 6, 30)) == "2024-25"
    assert _transfer_season(date(2026, 7, 1)) == "2026-27"
    assert _transfer_season(date(2025, 1, 4)) == "2024-25"
    assert _transfer_season(date(2024, 12, 3)) == "2024-25"
    assert _transfer_season(date(2026, 10, 8)) == "2026-27"


def test_windows():
    assert _window_for(date(2026, 6, 30)) == "summer"
    assert _window_for(date(2026, 1, 4)) == "winter"
    assert _window_for(date(2026, 10, 8)) == "other"


def test_pseudo_team_detection():
    assert _is_pseudo_team("Bratveit Per", "P. Kristian Bråtveit")
    assert _is_pseudo_team("McIntyre Tom", "T. Mcintyre")
    assert not _is_pseudo_team("Ross County", "N. Suman")


def test_dedupe_keeps_real_club_and_date_span():
    rows = [
        {
            "player_key": "api:player:1",
            "direction": "out",
            "transfer_kind": "free",
            "season": "2026-27",
            "from_club_id": "sco:aberdeen",
            "to_club_id": "sco:provisional-player",
            "date_effective": "2026-07-20",
            "date_announced": "2026-07-20",
        },
        {
            "player_key": "api:player:1",
            "direction": "out",
            "transfer_kind": "free",
            "season": "2026-27",
            "from_club_id": "sco:aberdeen",
            "to_club_id": "sco:haugesund",
            "date_effective": "2026-06-29",
            "date_announced": "2026-06-29",
        },
        {
            "player_key": "api:player:1",
            "direction": "out",
            "transfer_kind": "free",
            "season": "2026-27",
            "from_club_id": "sco:aberdeen",
            "to_club_id": "sco:haugesund",
            "date_effective": "2026-07-20",
            "date_announced": "2026-07-20",
        },
    ]
    result = _dedupe(rows)
    assert len(result) == 1
    assert result[0]["to_club_id"] == "sco:haugesund"
    assert result[0]["date_effective"] == "2026-07-20"
    assert result[0]["date_announced"] == "2026-06-29"


def test_false_provider_candidate_is_excluded():
    excluded = _excluded_candidate_ids()
    assert "afc:5d5cd277f72dad2a" in excluded
