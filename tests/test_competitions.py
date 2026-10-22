from __future__ import annotations

from fitba.normalize.competitions import (
    FRIENDLY_NAME,
    canonical_from_league,
    canonical_name,
    competition_id_from_league,
    short_name,
)


def test_scottish_cup_provider_label_is_canonicalised() -> None:
    competition_id, name = canonical_from_league({"id": 181, "name": "FA Cup"})
    assert competition_id == "sco:scottish-cup"
    assert name == "Scottish Gas Men's Scottish Cup"
    assert short_name(competition_id) == "Scottish Cup"


def test_english_fa_cup_is_not_relabelled_as_scottish() -> None:
    competition_id = competition_id_from_league({"id": 45, "name": "FA Cup"})
    assert competition_id == "sco:other:fa-cup"
    assert canonical_name(competition_id, "FA Cup") == "FA Cup"


def test_premiership_and_league_cup_ids() -> None:
    assert competition_id_from_league({"id": 179, "name": "Premiership"}) == "sco:premiership"
    assert competition_id_from_league({"id": 185, "name": "League Cup"}) == "sco:league-cup"


def test_friendlies_are_one_canonical_label() -> None:
    competition_id, name = canonical_from_league({"id": 999, "name": "Friendlies Clubs"})
    assert competition_id == "sco:other:friendlies"
    assert name == FRIENDLY_NAME


def test_unknown_provider_name_is_title_cased_not_raw() -> None:
    assert canonical_name("sco:other:some-cup", "some cup") == "Some Cup"
