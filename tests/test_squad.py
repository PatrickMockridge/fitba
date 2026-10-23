from fitba.ingest.squad import (
    _club_matches,
    _coverage,
    _scope_for,
)
from fitba.normalize.player_stats import parse_stat_entry, to_float, to_int, to_rating
from fitba.normalize.positions import position_group, squad_group
from fitba.publish.squad import PlayerLinkIndex, _totals


def _stat(**overrides):
    entry = {
        "league": {"name": "Premiership", "season": 2026},
        "team": {"id": 252, "name": "Aberdeen"},
        "games": {
            "appearences": 9,
            "lineups": 9,
            "minutes": 810,
            "position": "Goalkeeper",
            "rating": "7.34",
        },
        "goals": {"total": 0, "assists": 1, "saves": 37, "conceded": 8},
        "cards": {"yellow": 1, "red": 1, "yellowred": 1},
        "shots": {"total": 0, "on": 0},
        "passes": {"total": 300, "key": 2, "accuracy": "78%"},
    }
    entry.update(overrides)
    return parse_stat_entry(
        player_id=1,
        player_key="api:player:1",
        entry=entry,
        scope="club",
        season_year=2026,
        ingested_at="2026-10-21T00:00:00Z",
    )


def test_number_parsing_preserves_zero_and_rejects_missing():
    assert to_int(0) == 0
    assert to_int(None) is None
    assert to_int("") is None
    assert to_float("78%") == 78.0
    assert to_rating("0") is None
    assert to_rating("7.34") == 7.34


def test_stat_row_maps_api_typo_and_sums_red_cards():
    row = _stat()
    assert row is not None
    assert row["appearances"] == 9
    assert row["starts"] == 9
    assert row["minutes"] == 810
    assert row["assists"] == 1
    assert row["red_cards"] == 2
    assert row["pass_accuracy"] == 78.0
    assert row["rating"] == 7.34


def test_stat_row_rejects_other_seasons():
    row = _stat(league={"name": "Premiership", "season": 2025})
    assert row is None


def test_squad_and_detailed_position_groups():
    assert squad_group("Goalkeeper") == "GK"
    assert squad_group("Defender") == "DEF"
    assert squad_group("Midfielder") == "MID"
    assert squad_group("Attacker") == "FWD"
    assert squad_group(None) is None
    assert position_group("Defender") == "FB"
    assert position_group("Centre-Back") == "CB"


def test_loan_club_matching_handles_accents():
    assert _club_matches("Žilina", "Zilina")
    assert _club_matches("Dunfermline Athletic", "Dunfermline")
    assert not _club_matches("Cerezo Osaka", "Sanfrecce Hiroshima")


def test_scope_rules():
    entry = {"team": {"id": 252, "name": "Aberdeen"}}
    assert _scope_for(entry, status="squad", loan_club=None, parent_team_id=252) == "club"
    loan_entry = {"team": {"id": 999, "name": "Žilina"}}
    assert (
        _scope_for(loan_entry, status="loan_out", loan_club="Zilina", parent_team_id=252) == "loan"
    )
    assert (
        _scope_for(loan_entry, status="loan_out", loan_club="Ross County", parent_team_id=252)
        == "other"
    )


def test_coverage_unavailable_names_other_teams():
    stats = [
        {"scope": "other", "team_name": "Cerezo Osaka", "appearances": 4, "minutes": 52},
        {"scope": "other", "team_name": "Australia", "appearances": 8, "minutes": 473},
    ]
    coverage, note = _coverage(status="loan_out", stats=stats, loan_club="Sanfrecce Hiroshima")
    assert coverage == "unavailable"
    assert "Sanfrecce Hiroshima" in note
    assert "Cerezo Osaka" in note


def test_coverage_partial_when_minutes_missing():
    stats = [
        {"scope": "club", "team_name": "Aberdeen", "appearances": 3, "minutes": None},
    ]
    coverage, note = _coverage(status="squad", stats=stats, loan_club=None)
    assert coverage == "partial"
    assert "minutes" in note


def test_totals_sum_and_weightto_rating():
    rows = [
        {
            "appearances": 10,
            "starts": 10,
            "minutes": 900,
            "goals": 2,
            "assists": 1,
            "yellow_cards": 1,
            "red_cards": 0,
            "rating": 7.0,
        },
        {
            "appearances": 2,
            "starts": 0,
            "minutes": 60,
            "goals": 0,
            "assists": 0,
            "yellow_cards": 0,
            "red_cards": 0,
            "rating": 8.0,
        },
    ]
    totals = _totals(rows)
    assert totals["appearances"] == 12
    assert totals["minutes"] == 960
    assert totals["goals"] == 2
    assert totals["rating"] == 7.17


def _index() -> PlayerLinkIndex:
    return PlayerLinkIndex.from_payload(
        {
            "players": [
                {
                    "player_id": 1,
                    "player_key": "api:player:1",
                    "href": "/players/1/",
                    "name": "M. Müller",
                    "full_name": "Marius Müller",
                    "firstname": "Marius",
                    "lastname": "Müller",
                },
                {
                    "player_id": 2,
                    "player_key": "api:player:2",
                    "href": "/players/2/",
                    "name": "N. Devlin",
                    "full_name": "Nicky Devlin",
                    "firstname": "Nicky",
                    "lastname": "Devlin",
                },
                {
                    "player_id": 3,
                    "player_key": "api:player:3",
                    "href": "/players/3/",
                    "name": "C. Devlin",
                    "full_name": "Cameron Devlin",
                    "firstname": "Cameron",
                    "lastname": "Devlin",
                },
            ]
        }
    )


def test_player_links_full_name_and_unique_surname():
    index = _index()
    assert index.href("api:player:1") == "/players/1/"
    assert index.mentions("Marius Müller was excellent") == [
        {"name": "Marius Müller", "href": "/players/1/"}
    ]
    assert index.mentions("Müller was excellent") == [
        {"name": "Marius Müller", "href": "/players/1/"}
    ]


def test_player_links_full_names_for_ambiguous_surname():
    index = _index()
    mentions = index.mentions("Nicky Devlin and Cameron Devlin played")
    assert [item["href"] for item in mentions] == ["/players/2/", "/players/3/"]
    assert index.mentions("Devlin played") == []


def test_player_links_dedupe_by_player():
    index = _index()
    mentions = index.mentions("Marius Müller and Müller again")
    assert len(mentions) == 1
