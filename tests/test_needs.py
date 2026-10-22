from __future__ import annotations

import polars as pl

from fitba.analytics.needs import build_needs_document


def _squad(players):
    return {"players": players}


def _player(player_id, family, *, starts=0, minutes=0, age=24, status="squad"):
    return {
        "player_id": player_id,
        "player_key": f"api:player:{player_id}",
        "name": f"Player {player_id}",
        "display_role": {"family": family},
        "role": {"family": family},
        "career_role": {"dominant": {"family": family}},
        "age": age,
        "status": status,
        "playing_time": {
            "starts": starts,
            "minutes": minutes,
            "sub_apps": 0,
        },
    }


def _availability(*player_ids, status="out"):
    return {
        "entries": [
            {
                "player_id": player_id,
                "player_name": f"Player {player_id}",
                "status": status,
                "in_squad": True,
                "confidence": "confirmed",
                "source_id": "afc_news",
                "note": "Curated team news.",
            }
            for player_id in player_ids
        ]
    }


def _themes(*, fb_thin=True, fb_delta=None):
    return {
        "themes": [
            {
                "theme_id": "family_balance",
                "metrics": {
                    "groups": [
                        {
                            "family": "FB/WB",
                            "squad_rating_delta": fb_delta,
                        }
                    ]
                },
            },
            {
                "theme_id": "cover_question",
                "metrics": {
                    "groups": [
                        {"group": "FB/WB", "thin_rotation": fb_thin},
                        {"group": "CB", "thin_rotation": False},
                    ]
                },
            },
        ]
    }


def _shapes():
    return pl.DataFrame(
        [
            {
                "team_id": 252,
                "season": 2026,
                "formation": "4-2-3-1",
                "formation_shape": "4-2-3-1",
            }
            for _ in range(4)
        ]
    )


def _build(*, players, availability=None, rumours=None, themes=None):
    return build_needs_document(
        season="2026-27",
        generated_at="2026-10-22T00:00:00+00:00",
        themes=themes or _themes(),
        availability=availability or {"entries": []},
        squad_data=_squad(players),
        transfers=[],
        rumours=rumours or [],
        team_shapes=_shapes(),
    )


def test_fb_wb_thin_rotation_strengthens_without_cover():
    players = [
        _player(1, "full_back", starts=6, minutes=540),
        _player(2, "full_back", starts=1, minutes=90),
        _player(3, "full_back", starts=0, minutes=0),
        _player(4, "full_back", starts=0, minutes=0),
    ]
    document = _build(players=players)
    family = next(row for row in document["families"] if row["family"] == "FB/WB")
    assert family["category"] == "strengthen"
    assert family["market_route"]["primary"] == "permanent"
    assert family["market_route"]["fee_expectation"] == "unknown"
    assert "targets" not in family


def test_cb_cover_when_out_reduces_available_depth():
    players = [
        _player(1, "centre_back", starts=6, minutes=540),
        _player(2, "centre_back", starts=5, minutes=450),
        _player(3, "centre_back", starts=0, minutes=0),
    ]
    document = _build(
        players=players,
        availability=_availability(2),
    )
    family = next(row for row in document["families"] if row["family"] == "CB")
    assert family["category"] == "cover"
    assert family["urgency"] in {"critical", "high"}
    assert family["market_route"]["primary"] == "loan"


def test_replace_requires_active_outgoing_rumour():
    players = [_player(1, "centre_forward", starts=8, minutes=720)]
    without = _build(players=players)
    cbs = next(row for row in without["families"] if row["family"] == "ST")
    assert cbs["replace_status"] != "replace"

    with_rumour = _build(
        players=players,
        rumours=[
            {
                "direction": "out",
                "status": "active",
                "confidence": "medium",
                "player_key": "api:player:1",
                "claim": "A club is linked with the striker.",
                "source_urls": ["https://example.com/report"],
            }
        ],
    )
    st = next(row for row in with_rumour["families"] if row["family"] == "ST")
    assert st["category"] == "replace"
    assert st["market_route"]["primary"] == "permanent"


def test_goalkeeper_is_not_strengthened_for_top_share_or_age():
    players = [
        _player(1, "goalkeeper", starts=14, minutes=1260, age=32),
        _player(2, "goalkeeper", starts=0, minutes=0, age=23),
        _player(3, "goalkeeper", starts=0, minutes=0, age=21),
    ]
    document = _build(players=players)
    gk = next(row for row in document["families"] if row["family"] == "GK")
    assert gk["category"] == "none"
    assert gk["measured"]["top_share"] == 1.0
