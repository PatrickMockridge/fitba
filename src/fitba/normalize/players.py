"""Player identity registry.

The API-Football player id is the initial spine: it is stable across the
transfers, squad and player-stat endpoints. Curated entries in
``reference/players.yaml`` can give a player a human-readable canonical key and
cross-source aliases. Players without a curated entry still get a stable
``api:player:<id>`` key and are labelled API-resolved rather than curated.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from fitba.normalize.names import strip_accents
from fitba.settings import players as players_config

_PLAYER_PUNCT = re.compile(r"[^\w\s]")


def normalize_player_name(value: str) -> str:
    value = strip_accents(value).casefold()
    value = _PLAYER_PUNCT.sub(" ", value)
    return re.sub(r"\s+", " ", value).strip()


def player_slug(value: str) -> str:
    return normalize_player_name(value).replace(" ", "-")


@dataclass(frozen=True, slots=True)
class Player:
    player_key: str
    name: str
    aliases: tuple[str, ...] = ()
    dob: str | None = None
    nationality: str | None = None
    position: str | None = None
    shirt_number: int | None = None
    api_football_id: int | None = None
    status: str = "resolved"


class PlayerRegistry:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        payload = data if data is not None else players_config()
        self._players: dict[str, Player] = {}
        self._by_api: dict[int, str] = {}
        self._by_name: dict[str, str] = {}
        for row in payload.get("players", []):
            player = Player(
                player_key=row["player_key"],
                name=row["name"],
                aliases=tuple(row.get("aliases", [])),
                dob=str(row["dob"]) if row.get("dob") else None,
                nationality=row.get("nationality"),
                position=row.get("position"),
                shirt_number=row.get("shirt_number"),
                api_football_id=row.get("api_football_id"),
                status=row.get("status", "resolved"),
            )
            if player.player_key in self._players:
                raise ValueError(f"duplicate player_key {player.player_key}")
            self._players[player.player_key] = player
            if player.api_football_id is not None:
                self._by_api[int(player.api_football_id)] = player.player_key
            for alias in (player.name, *player.aliases):
                key = normalize_player_name(alias)
                existing = self._by_name.get(key)
                if existing is not None and existing != player.player_key:
                    raise ValueError(
                        f"player alias {alias!r} maps to {existing} and {player.player_key}"
                    )
                self._by_name[key] = player.player_key

    def resolve(
        self,
        *,
        api_football_id: int | None = None,
        name: str | None = None,
    ) -> Player:
        if api_football_id is not None:
            canonical = self._by_api.get(int(api_football_id))
            if canonical:
                # A curated canonical name always wins over a provider spelling.
                return self._players[canonical]
        if name:
            canonical = self._by_name.get(normalize_player_name(name))
            if canonical:
                return self._players[canonical]
        display_name = name or (
            f"Player {api_football_id}" if api_football_id else "Unknown player"
        )
        if api_football_id is not None:
            return Player(
                player_key=f"api:player:{int(api_football_id)}",
                name=display_name,
                api_football_id=int(api_football_id),
                status="api_resolved",
            )
        return Player(
            player_key=f"player:provisional-{player_slug(display_name)}",
            name=display_name,
            status="provisional",
        )

    def get(self, player_key: str) -> Player | None:
        return self._players.get(player_key)

    def all(self) -> list[Player]:
        return sorted(self._players.values(), key=lambda player: player.name)
