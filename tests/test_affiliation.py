from __future__ import annotations

from fitba.analytics.affiliation import AffiliationIndex, is_return_link, is_target


def _squad() -> dict:
    return {
        "players": [
            {"player_key": "api:player:1", "name": "Current One", "status": "squad"},
            {"player_key": "api:player:2", "name": "Loan Two", "status": "loan_out"},
        ],
        "excluded_players": [{"player_key": "api:player:3", "name": "Excluded Three"}],
    }


def test_affiliation_precedence_and_name_match():
    index = AffiliationIndex.from_payloads(
        squad=_squad(), former_keys={"api:player:4"}
    )
    assert index.affiliation_for("api:player:1") == ("current_squad", "key")
    assert index.affiliation_for("api:player:2") == ("loan_out", "key")
    assert index.affiliation_for("api:player:3") == ("current_non_official", "key")
    assert index.affiliation_for("api:player:4") == ("former_player", "key")
    assert index.affiliation_for("api:player:9") == ("external_target", "key")
    assert index.affiliation_for("", "Current One") == ("current_squad", "name_match")
    assert index.affiliation_for("", "Nobody") == ("unknown", "none")


def test_former_affiliation_wins_over_lingering_excluded_profile():
    squad = _squad()
    squad["excluded_players"].append({"player_key": "api:player:5", "name": "Former Five"})
    index = AffiliationIndex.from_payloads(
        squad=squad, former_keys={"api:player:5"}
    )
    assert index.affiliation_for("api:player:5") == ("former_player", "key")


def test_target_and_return_labels_are_directional():
    assert is_target("external_target", "in") is True
    assert is_target("external_target", "out") is False
    assert is_target("former_player", "in") is False
    assert is_return_link("former_player", "in") is True
    assert is_return_link("former_player", "out") is False
