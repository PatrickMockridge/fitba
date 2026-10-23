from fitba.publish.player_page import build_player_page, player_page_schema


def _player(**overrides):
    player = {
        "player_id": 1,
        "name": "T. Player",
        "full_name": "Test Player",
        "href": "/players/1/",
        "age": 24,
        "nationality": "Scotland",
        "number": 8,
        "status": "squad",
        "injured": False,
        "loan": None,
        "position": None,
        "attributes": {
            "preferred_foot": {
                "status": "unknown",
                "value": None,
                "unknown_reason": "not_sourced",
                "source": None,
            }
        },
        "role": {
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
        },
        "career_role": {
            "status": "unknown",
            "dominant": None,
            "primary_slot": None,
            "slots": [],
            "secondary_slots": [],
            "stretch_slots": [],
            "starts_total": 0,
            "starts_with_role": 0,
            "coverage": "0/0",
            "seasons_with_role": 0,
            "unknown_reason": "no_role_evidence",
            "seasons": [],
            "scopes": [],
            "history": [],
            "fm_label": "",
        },
        "display_role": {
            "code": None,
            "label": None,
            "family": None,
            "family_label": None,
            "side": None,
            "source": "none",
            "reason": "No starting-XI role evidence was found.",
            "starts": 0,
            "share": 0.0,
            "career_dominant": None,
        },
        "tactical_notes": [],
        "playing_time": {
            "starts": 0,
            "sub_apps": 0,
            "minutes": 0,
            "minutes_started": 0,
            "minutes_as_sub": 0,
            "coverage": "unavailable",
            "by_competition": [],
        },
        "stats_coverage": "unavailable",
        "stats_note": "No statistics.",
        "stats": [],
        "position_stats": [],
        "position_stats_coverage": "no_matches",
        "position_stats_note": "No matches.",
        "position_totals": None,
        "other_stats": [],
        "totals": None,
    }
    player.update(overrides)
    return player


def test_player_page_has_fixed_panels_and_no_foot_fallback():
    page = build_player_page(_player(), season="2026-27", generated_at="2026-10-21T00:00:00Z")
    assert page["panel_order"] == [
        "profile",
        "position",
        "playing_time",
        "performance",
        "availability",
        "recent_matches",
        "records",
    ]
    assert set(page["panels"]) == set(page["panel_order"])
    assert page["identity"]["preferred_foot"]["status"] == "unknown"
    assert page["identity"]["preferred_foot"]["value"] is None
    assert page["panels"]["records"]["status"] == "not_applicable"


def test_unknown_position_has_no_midfield_tiles():
    page = build_player_page(_player(), season="2026-27", generated_at="2026-10-21T00:00:00Z")
    performance = page["panels"]["performance"]["data"]
    assert performance["tiles"] == []
    assert performance["detail_columns"] == []
    assert page["warnings"][0]["code"] == "POSITION_UNKNOWN"


def test_schema_is_closed():
    schema = player_page_schema()
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["IdentityBlock"]["additionalProperties"] is False
