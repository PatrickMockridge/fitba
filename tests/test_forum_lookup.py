from __future__ import annotations

import polars as pl

from fitba.ingest import forum


def _entry(
    name: str,
    key: str,
    *,
    status: str = forum.LOOKUP_SCOUTED,
    club: str | None = None,
) -> forum.GazetteerEntry:
    return forum.GazetteerEntry(
        name=name,
        player_key=key,
        position_group="MID",
        club=club,
        lookup_status=status,
        source="scouted_player",
    )


def test_local_resolution_matches_first_name_against_initial():
    entries = [
        _entry("B. Doak", "api:player:1", club="Bournemouth"),
        _entry("Ben Gannon Doak", "api:player:1", club="Bournemouth"),
    ]
    resolved = forum._resolve_local("Ben Doak", entries)
    assert resolved is not None
    assert resolved.player_key == "api:player:1"


def test_local_resolution_rejects_an_ambiguous_surname():
    entries = [
        _entry("Ben Doak", "api:player:1"),
        _entry("Billy Doak", "api:player:2"),
    ]
    assert forum._resolve_local("B. Doak", entries) is None


def test_gazetteer_tracks_ambiguous_full_names():
    gazetteer = forum.Gazetteer()
    gazetteer.add(forum.GazetteerEntry(name="Alex Smith", player_key="api:player:1"))
    gazetteer.add(forum.GazetteerEntry(name="Alex Smith", player_key="api:player:2"))
    assert gazetteer.match_full("Alex Smith") is None


def test_api_lookup_accepts_a_unique_profile(monkeypatch):
    monkeypatch.setattr(
        forum.api_football,
        "player_profiles_search",
        lambda _search: [
            {
                "player": {
                    "id": 10,
                    "name": "B. Doak",
                    "firstname": "Ben",
                    "age": 20,
                    "nationality": "Scotland",
                    "position": "Midfielder",
                }
            }
        ],
    )
    monkeypatch.setattr(
        forum,
        "_latest_club",
        lambda _player_id: ("Bournemouth", None),
    )
    cache: dict = {}
    found = forum._lookup_player("Ben Doak", cache)
    assert found is not None
    assert found["player_key"] == "api:player:10"
    assert found["club"] == "Bournemouth"
    assert found["lookup_status"] == forum.LOOKUP_API
    assert cache["ben doak"]["lookup_status"] == forum.LOOKUP_API


def test_api_lookup_records_ambiguity(monkeypatch):
    monkeypatch.setattr(
        forum.api_football,
        "player_profiles_search",
        lambda _search: [
            {"player": {"id": 10, "name": "B. Doak", "firstname": "Ben"}},
            {"player": {"id": 11, "name": "B. Doak", "firstname": "Billy"}},
        ],
    )
    cache: dict = {}
    assert forum._lookup_player("B. Doak", cache) is None
    assert cache["b. doak"]["lookup_status"] == forum.LOOKUP_AMBIGUOUS


def test_api_lookup_records_not_found(monkeypatch):
    monkeypatch.setattr(
        forum.api_football,
        "player_profiles_search",
        lambda _search: [],
    )
    cache: dict = {}
    assert forum._lookup_player("Ben Doak", cache) is None
    assert cache["ben doak"]["lookup_status"] == forum.LOOKUP_NOT_FOUND


def test_signal_carries_lookup_metadata():
    gazetteer = forum.Gazetteer()
    gazetteer.add(
        _entry("Ben Doak", "api:player:10", club="Bournemouth")
    )
    posts = pl.DataFrame(
        {
            "post_key": ["p1"],
            "topic_id": ["t1"],
            "text": ["Ben Doak would be a good signing."],
            "compound": [0.2],
        }
    )
    signals = forum.build_signals(
        posts,
        gazetteer,
        transfers=[],
        rumours=[],
        news_titles=[],
        affiliations=None,
    )
    assert len(signals) == 1
    signal = signals[0]
    assert signal["lookup_status"] == forum.LOOKUP_SCOUTED
    assert signal["lookup_source"] == "scouted_player"
    assert signal["current_club"] == "Bournemouth"
    assert signal["affiliation"] == "unknown"
