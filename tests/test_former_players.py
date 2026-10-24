from __future__ import annotations

from fitba.analytics.former_players import (
    aberdeen_record,
    development_summary,
    former_player_rows,
    last_playing_season,
    post_career_record,
    sell_on_watch,
    vs_aberdeen_record,
)
from fitba.normalize.teams import TeamRegistry


def _transfer(
    *,
    tid: str,
    key: str,
    name: str = "A Player",
    direction: str = "out",
    kind: str = "permanent",
    date_effective: str = "2022-07-01",
    season: str = "2022-23",
    window: str = "summer",
    to_club: str = "Example FC",
    fee_status: str = "undisclosed",
) -> dict:
    return {
        "transfer_id": tid,
        "player_key": key,
        "player_name": name,
        "direction": direction,
        "transfer_kind": kind,
        "date_effective": date_effective,
        "date_announced": date_effective,
        "season": season,
        "window": window,
        "to_club_id": f"sco:provisional-{to_club.casefold().replace(' ', '-')}",
        "to_club_name": to_club,
        "from_club_id": "sco:aberdeen",
        "from_club_name": "Aberdeen",
        "fee_status": fee_status,
        "verification_status": "curated",
    }


def test_universe_excludes_current_loans_returns_and_merges_identity():
    transfers = [
        _transfer(tid="a", key="api:player:1", name="Current Player"),
        _transfer(tid="b", key="api:player:2", name="Loan Player"),
        _transfer(tid="c", key="api:player:3", name="Returned Player"),
        _transfer(
            tid="d",
            key="api:player:3",
            name="Returned Player",
            direction="in",
            kind="loan",
            date_effective="2023-01-01",
            season="2022-23",
            window="winter",
            to_club="Aberdeen",
        ),
        _transfer(tid="e", key="curated:player:example", name="D. McGeouch",
                  date_effective="2022-05-31"),
        _transfer(tid="f", key="api:player:5", name="D. McGeouch",
                  date_effective="2022-11-21"),
    ]
    squad = {
        "players": [
            {"player_key": "api:player:1", "name": "Current Player", "status": "squad"},
            {"player_key": "api:player:2", "name": "Loan Player", "status": "loan_out"},
        ]
    }
    rows = former_player_rows(transfers, squad)
    keys = {row["player_key"] for row in rows}
    assert "api:player:1" not in keys
    assert "api:player:2" not in keys
    assert "api:player:3" not in keys
    mcgeouch = next(row for row in rows if row["player_key"] == "api:player:5")
    assert mcgeouch["identity_status"] == "merged_duplicate"
    assert mcgeouch["alias_keys"] == ["curated:player:example"]
    assert mcgeouch["departure"]["date_effective"] == "2022-05-31"


def test_last_playing_season_respects_window():
    assert last_playing_season({"season": "2024-25", "window": "summer"}) == "2023-24"
    assert last_playing_season({"season": "2024-25", "window": "winter"}) == "2024-25"
    assert last_playing_season({"season": "2024-25", "window": "other"}) == "2024-25"


def test_aberdeen_record_counts_bench_separately_and_keeps_proxy_unknown():
    appearances = [
        {"player_key": "api:player:1", "team_name": "Aberdeen", "competition": "Premiership",
         "season": "2021-22", "fixture_id": 1, "started": True, "minutes": 90,
         "date": "2022-01-01"},
        {"player_key": "api:player:1", "team_name": "Aberdeen", "competition": "Premiership",
         "season": "2021-22", "fixture_id": 2, "started": False, "minutes": 0,
         "date": "2022-01-08"},
        {"player_key": "api:player:1", "team_name": "Aberdeen", "competition": "Premiership",
         "season": "2021-22", "fixture_id": 3, "started": False, "minutes": 30,
         "date": "2022-01-15"},
    ]
    stats = [
        {"player_key": "api:player:1", "fixture_id": 1, "goals": 1, "assists": 0, "rating": 7.0},
        {"player_key": "api:player:1", "fixture_id": 3, "goals": 0, "assists": 1, "rating": 6.0},
    ]
    record = aberdeen_record(
        appearances,
        stats,
        player_key="api:player:1",
        departure={"season": "2022-23", "window": "summer", "date_effective": "2022-07-01"},
        birth_date="2002-01-01",
        arrival={"season": "2018-19"},
        config={"coverage": {"register_from": "2019-20"}, "development": {}},
    )
    assert record["squad_selections"] == 3
    assert record["appearances"] == 2
    assert record["starts"] == 1
    assert record["sub_apps"] == 1
    assert record["minutes"] == 120
    assert record["final_season"]["coverage"] == "measured"
    assert record["developed_here"] == "unknown"


def test_post_career_uses_league_rows_only_and_labels_current():
    seasons = [
        {"player_key": "api:player:1", "season": "2024-25", "season_year": 2024,
         "team_name": "Example FC", "competition": "League", "country": "England",
         "league_tier": 2, "scope": "league", "appearances": 20, "starts": 18,
         "minutes": 1600, "goals": 4, "assists": 2, "rating": 7.0},
        {"player_key": "api:player:1", "season": "2024-25", "season_year": 2024,
         "team_name": "Example FC", "competition": "Cup", "country": "England",
         "league_tier": None, "scope": "cup", "appearances": 2, "starts": 2,
         "minutes": 180, "goals": 9, "assists": 9, "rating": 9.0},
        {"player_key": "api:player:1", "season": "2025-26", "season_year": 2025,
         "team_name": "Example FC", "competition": "League", "country": "England",
         "league_tier": 2, "scope": "league", "appearances": 10, "starts": 8,
         "minutes": 700, "goals": 2, "assists": 1, "rating": 6.8},
    ]
    record = post_career_record(
        seasons,
        [],
        player_key="api:player:1",
        departure={"season": "2024-25", "date_effective": "2024-07-01",
                   "to_club_name": "Example FC"},
        birth_date=None,
        config={},
        current_season="2025-26",
        teams=TeamRegistry(),
        markets=[],
    )
    assert record["totals"]["minutes"] == 2300
    assert record["totals"]["goals"] == 6
    assert record["totals"]["seasons_with_data"] == 2
    assert record["current"]["coverage"] == "current"
    assert record["current"]["club_name"] == "Example FC"


def test_sell_on_receipt_requires_all_inputs_and_computes_gross_fee():
    clause = {
        "clause_id": "sell-on-example",
        "transfer_id": "t1",
        "player_key": "api:player:1",
        "player_name": "A Player",
        "buyer_club_name": "Buyer FC",
        "sale_date": "2022-07-01",
        "sell_on_pct": 20.0,
        "basis": "gross_fee",
        "confidence": "confirmed",
        "source_urls": ["https://en.wikipedia.org/wiki/Example"],
    }
    events = {
        "api:player:1": [
            {"date": "2024-07-01", "type": "Transfer", "kind": "permanent",
             "teams": {"out": {"name": "Buyer FC"}, "in": {"name": "Next FC"}}}
        ]
    }
    fees = [
        {"event_id": "e1", "clause_id": "sell-on-example", "player_key": "api:player:1",
         "subsequent_transfer_date": "2024-07-01", "to_club_name": "Next FC",
         "fee_status": "disclosed", "fee_amount": 1000000, "fee_currency": "GBP",
         "source_urls": ["https://en.wikipedia.org/wiki/Example"]}
    ]
    watch = sell_on_watch(
        [clause],
        [],
        events,
        fees,
        config={"sell_on": {"fx_to_gbp": {"GBP": 1.0}}},
    )
    receipt = watch["clauses"][0]["receipt"]
    assert receipt["status"] == "computed"
    assert receipt["receipt_gbp"] == 200000
    assert watch["summary"]["computed"] == 1

    missing = sell_on_watch(
        [{**clause, "sell_on_pct": None}], [], events, fees,
        config={"sell_on": {"fx_to_gbp": {"GBP": 1.0}}},
    )
    assert missing["clauses"][0]["receipt"]["status"] == "missing_inputs"
    assert "percentage" in missing["clauses"][0]["receipt"]["missing_inputs"]


def test_vs_aberdeen_and_development_summary():
    appearances = [
        {"player_key": "api:player:1", "opponent": "Aberdeen", "team_name": "Example FC",
         "date": "2024-10-01", "started": True, "minutes": 90, "fixture_id": 10},
        {"player_key": "api:player:1", "opponent": "Other", "team_name": "Example FC",
         "date": "2024-10-08", "started": True, "minutes": 90, "fixture_id": 11},
    ]
    stats = [{"player_key": "api:player:1", "fixture_id": 10, "goals": 1, "assists": 0}]
    vs = vs_aberdeen_record(appearances, stats, player_key="api:player:1", after="2024-07-01")
    assert vs["appearances"] == 1
    assert vs["goals"] == 1
    players = [
        {"age_at_exit": 22, "departure": {"fee_status": "disclosed", "season": "2024-25"},
         "aberdeen": {"developed_here": "yes"},
         "post_career": {"totals": {"minutes": 1000, "seasons_with_data": 1},
                         "top_flight_abroad": True, "at_rival": False}},
        {"age_at_exit": 29, "departure": {"fee_status": "free", "season": "2024-25"},
         "aberdeen": {"developed_here": "no"}, "post_career": {"totals": {"minutes": 0}}},
    ]
    summary = development_summary(players, config={"development": {"young_exit_age_max": 23}})
    assert summary["cohorts"]["all"]["players"] == 2
    assert summary["cohorts"]["young"]["players"] == 1
    assert summary["cohorts"]["developed_here"]["players"] == 1
