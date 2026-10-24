from __future__ import annotations

from fitba.ingest.former_players import _api_id, competition_scope


def test_competition_scope_excludes_cups_and_europe_from_league_totals():
    assert competition_scope("Serie A") == "league"
    assert competition_scope("Premiership") == "league"
    assert competition_scope("FA Cup") == "cup"
    assert competition_scope("Copa del Rey") == "cup"
    assert competition_scope("Champions League") == "europe"


def test_api_id_only_for_api_player_keys():
    assert _api_id("api:player:123") == 123
    assert _api_id("curated:player:example") is None
    assert _api_id("api:player:not-a-number") is None
