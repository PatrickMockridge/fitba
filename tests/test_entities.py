from __future__ import annotations

import pytest

from fitba.normalize.entities import (
    EntityRef,
    claim_href,
    club_href,
    entity_id,
    fixture_href,
    former_anchor,
    former_href,
    page_href,
    player_href,
    scouting_href,
    season_href,
    slug,
    staff_href,
)


def test_entity_id_rejects_an_unknown_type() -> None:
    with pytest.raises(ValueError):
        entity_id("nonsense", "value")


def test_player_href_requires_an_id() -> None:
    assert player_href(12) == "/players/12/"
    assert player_href("12") == "/players/12/"
    assert player_href(None) is None
    assert player_href("") is None


def test_one_profile_rule_for_every_player() -> None:
    # A current squad member and a scouted player share the scouting route;
    # only the current squad uses /players/.
    assert scouting_href(34) == "/scouting/player/34/"
    assert scouting_href(None) is None
    # A former player with an API id resolves to the shared profile; without
    # one it resolves to the former-player register anchor.
    assert former_href("Scott McKenna", 88) == "/former-players/#former-88"
    assert former_href("Scott McKenna") == "/former-players/#former-scott-mckenna"
    assert former_anchor("Scott McKenna") == "former-scott-mckenna"


def test_club_href_requires_a_current_scottish_table_row() -> None:
    assert club_href("sco:181", "sco:premiership") == "/scotland/premiership/#club-181"
    assert club_href("sco:provisional:181", "sco:premiership") is None
    assert club_href("eng:1", "sco:premiership") is None


def test_fixture_season_and_staff_hrefs() -> None:
    assert fixture_href(1556682) == "/matches/1556682/"
    assert fixture_href(None) is None
    assert season_href("2025-26") == "/history/2025-26/"
    assert staff_href("Jimmy Thelin") == "/history/#staff-jimmy-thelin"


def test_claim_href_uses_the_claims_surface() -> None:
    assert claim_href("team-now") == "/claims/#claim-team-now"
    assert claim_href("Defence / 2026") == "/claims/#claim-defence-2026"


def test_page_href_preserves_a_fragment_and_adds_a_trailing_slash() -> None:
    assert page_href("/") == "/"
    assert page_href("/scouting") == "/scouting/"
    assert page_href("/scouting/#priority-profiles") == "/scouting/#priority-profiles"
    assert page_href("search") == "/search/"


def test_slug_is_stable_and_accent_insensitive() -> None:
    assert slug("Kelle Roos") == "kelle-roos"
    assert slug("José Mourinho") == "jose-mourinho"
    assert slug("  ") == ""


def test_an_entity_without_a_href_is_not_indexable() -> None:
    entity = EntityRef(
        entity_id="club:eng:1",
        type="club",
        name="Example",
        href=None,
        indexable=True,
        no_href_reason="no_current_table_anchor",
    )
    payload = entity.to_dict()
    assert payload["indexable"] is False
    assert payload["href"] is None
    assert payload["no_href_reason"] == "no_current_table_anchor"
