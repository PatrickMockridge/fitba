from __future__ import annotations

import pytest
from pydantic import ValidationError

from fitba.publish.former_players import (
    FormerPlayersDocument,
    former_players_schema,
    former_seasons_schema,
)


def test_former_schemas_expose_expected_roots():
    index = former_players_schema()
    seasons = former_seasons_schema()
    assert {"players", "summary", "sell_on_watch", "development_scorecard"} <= set(
        index["properties"]
    )
    assert {"seasons", "coverage"} <= set(seasons["properties"])


def test_former_index_rejects_unknown_top_level_field():
    with pytest.raises(ValidationError):
        FormerPlayersDocument.model_validate(
            {
                "schema_version": "1.0.0",
                "club_id": "sco:aberdeen",
                "name": "Aberdeen",
                "season": "2026-27",
                "generated_at": "2026-10-24T00:00:00+00:00",
                "state": "unavailable",
                "served_generated_at": None,
                "definition": {},
                "coverage": {},
                "summary": {},
                "players": [],
                "sell_on_watch": {"clauses": [], "summary": {}},
                "development_scorecard": {},
                "sources": [],
                "notes": "test",
                "unexpected": True,
            }
        )
