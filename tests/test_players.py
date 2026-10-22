from fitba.normalize.players import PlayerRegistry, normalize_player_name


def test_player_registry_api_spine_and_override():
    registry = PlayerRegistry(
        {
            "players": [
                {
                    "player_key": "sco:bojan-miovski",
                    "name": "Bojan Miovski",
                    "aliases": ["B. Miovski"],
                    "api_football_id": 123,
                }
            ]
        }
    )
    by_id = registry.resolve(api_football_id=123)
    assert by_id.player_key == "sco:bojan-miovski"
    assert by_id.status == "resolved"
    assert registry.resolve(api_football_id=123, name="Provider Spelling").name == "Bojan Miovski"

    by_name = registry.resolve(name="B. Miovski")
    assert by_name.player_key == "sco:bojan-miovski"

    unknown = registry.resolve(api_football_id=999, name="New Player")
    assert unknown.player_key == "api:player:999"
    assert unknown.status == "api_resolved"

    provisional = registry.resolve(name="Unknown Trialist")
    assert provisional.player_key.startswith("player:provisional-")


def test_player_name_normalization_does_not_use_club_abbreviations():
    assert normalize_player_name("B. Miovski") == "b miovski"
    assert normalize_player_name("St. Johnstone") == "st johnstone"
