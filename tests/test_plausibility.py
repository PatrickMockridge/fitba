from fitba.normalize.transfer_plausibility import (
    is_suspect,
    screen_transfers,
    transfer_flags,
)


def _row(**overrides):
    row = {
        "transfer_id": "afc:test",
        "player_key": "api:player:625768",
        "player_name": "A. Morgan-Cummings",
        "direction": "in",
        "transfer_kind": "permanent",
        "from_club_id": "sco:provisional-potters-bar-town",
        "from_club_name": "Potters Bar Town",
        "position": None,
        "source_urls": ["https://en.wikipedia.org/wiki/2026%E2%80%9327_Aberdeen_F.C._season"],
    }
    row.update(overrides)
    return row


def test_false_pub_team_permanent_move_is_suspect():
    flags = transfer_flags(
        _row(),
        birth_dates={},
        markets=[{"club_name": "Potters Bar Town", "market": "unknown"}],
    )
    assert "unknown_source_club" in flags
    assert "no_player_profile" in flags
    assert "no_position" in flags
    assert "wikipedia_only" in flags
    assert "merged_name" in flags
    assert is_suspect(flags)


def test_known_profile_with_position_is_not_suspect():
    flags = transfer_flags(
        _row(
            player_name="Aaron Cummings",
            position="Midfielder",
            from_club_id="sco:elgin-city",
            from_club_name="Elgin City",
        ),
        birth_dates={"api:player:625768": "2007-01-01"},
        markets=[{"club_name": "Elgin City", "market": "scotland"}],
    )
    assert not is_suspect(flags)


def test_screen_splits_and_honours_acceptance():
    rows = [_row()]
    published, withheld = screen_transfers(
        rows,
        birth_dates={},
        markets=[{"club_name": "Potters Bar Town", "market": "unknown"}],
        accepted=set(),
    )
    assert not published
    assert len(withheld) == 1
    assert withheld[0]["plausibility_flags"]
    published, withheld = screen_transfers(
        rows,
        birth_dates={},
        markets=[{"club_name": "Potters Bar Town", "market": "unknown"}],
        accepted={"afc:test"},
    )
    assert len(published) == 1
    assert not withheld
