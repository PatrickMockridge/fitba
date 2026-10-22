from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from fitba.publish.needs import (
    NeedsDocument,
    build_needs_payload,
    fallback_needs_payload,
    needs_schema,
)

ROOT = Path(__file__).resolve().parents[1]


def _squad():
    families = [
        ("goalkeeper", 1),
        ("centre_back", 2),
        ("full_back", 3),
        ("central_midfield", 4),
        ("attacking_midfield", 5),
        ("wide_forward", 6),
        ("centre_forward", 7),
    ]
    return {
        "players": [
            {
                "player_id": player_id,
                "player_key": f"api:player:{player_id}",
                "name": f"Player {player_id}",
                "display_role": {"family": family},
                "role": {"family": family},
                "career_role": {"dominant": {"family": family}},
                "age": 24,
                "status": "squad",
                "playing_time": {"starts": 5, "minutes": 450, "sub_apps": 0},
            }
            for family, player_id in families
        ]
    }


def _themes():
    return {
        "themes": [
            {"theme_id": "family_balance", "metrics": {"groups": []}},
            {
                "theme_id": "cover_question",
                "metrics": {
                    "groups": [
                        {"group": "CB", "thin_rotation": False},
                        {"group": "FB/WB", "thin_rotation": True},
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
            for _ in range(3)
        ]
    )


def test_needs_payload_validates_and_has_no_targets():
    payload = build_needs_payload(
        season="2026-27",
        generated_at="2026-10-22T00:00:00+00:00",
        themes=_themes(),
        availability={"entries": []},
        squad_data=_squad(),
        transfers_data={"transfers": []},
        rumours=[],
        team_shapes=_shapes(),
    )
    assert NeedsDocument(**payload)
    assert len(payload["families"]) == 7
    for family in payload["families"]:
        assert "targets" not in family
        assert family["market_route"]["fee_expectation"] == "unknown"


def test_needs_schema_is_checked_in():
    checked_in = json.loads(
        (ROOT / "contracts" / "needs.schema.json").read_text(encoding="utf-8")
    )
    assert checked_in == needs_schema()


def test_needs_fallback_is_valid():
    fallback = fallback_needs_payload(
        None,
        generated_at="2026-10-22T00:00:00+00:00",
        season="2026-27",
        reason="build_failed",
    )
    assert NeedsDocument(**fallback)
    assert fallback["state"] == "unavailable"
