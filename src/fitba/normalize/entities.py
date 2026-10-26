"""Canonical reader-facing entity identity and href construction.

The published UI must never assemble a player, club, fixture or claim link by
hand. This module owns the one namespace and the one route precedence, so the
same identity resolves to the same destination everywhere.

The one-profile rule is explicit:

* current squad player -> ``/players/<id>/``
* former player with an API id -> ``/scouting/player/<id>/``
* scouted player -> ``/scouting/player/<id>/``
* former player without a profile -> the former-player register anchor

No third player profile route is allowed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from fitba.normalize.names import strip_accents

ENTITY_TYPES = (
    "page",
    "club",
    "player",
    "fixture",
    "season",
    "staff",
    "claim",
)

_SLUG_PUNCT = re.compile(r"[^a-z0-9]+")


def slug(value: Any) -> str:
    text = strip_accents(str(value or "")).casefold()
    return _SLUG_PUNCT.sub("-", text).strip("-")


def entity_id(kind: str, value: str) -> str:
    if kind not in ENTITY_TYPES:
        raise ValueError(f"unknown entity type: {kind}")
    return f"{kind}:{value}"


def player_href(player_id: int | str | None) -> str | None:
    if player_id is None or str(player_id).strip() == "":
        return None
    return f"/players/{player_id}/"


def scouting_href(player_id: int | str | None) -> str | None:
    if player_id is None or str(player_id).strip() == "":
        return None
    return f"/scouting/player/{player_id}/"


def former_anchor(player_key: str, player_id: int | str | None = None) -> str:
    if player_id is not None and str(player_id).strip():
        return f"former-{player_id}"
    return f"former-{slug(player_key)}"


def former_href(player_key: str, player_id: int | str | None = None) -> str:
    return f"/former-players/#{former_anchor(player_key, player_id)}"


def club_href(team_id: str, competition_id: str) -> str | None:
    """Current-table club destination, or None when no public club page exists."""
    if not team_id.startswith("sco:") or team_id.startswith("sco:provisional"):
        return None
    tier = str(competition_id).split(":", 1)[-1]
    if not tier:
        return None
    return f"/scotland/{tier}/#club-{team_id.split(':', 1)[-1]}"


def fixture_href(fixture_id: int | str | None) -> str | None:
    if fixture_id is None or str(fixture_id).strip() == "":
        return None
    return f"/matches/{fixture_id}/"


def season_href(season: str) -> str:
    return f"/history/{season}/"


def staff_href(person_id: str) -> str:
    return f"/history/#staff-{slug(person_id)}"


def claim_href(claim_id: str) -> str:
    return f"/claims/#claim-{slug(claim_id)}"


def page_href(path: str) -> str:
    value = str(path or "/")
    if not value.startswith("/"):
        value = f"/{value}"
    base, _, fragment = value.partition("#")
    base = base if base.endswith("/") else f"{base}/"
    return f"{base}#{fragment}" if fragment else base


@dataclass(frozen=True, slots=True)
class EntityRef:
    entity_id: str
    type: str
    name: str
    href: str | None
    href_kind: str = "primary"
    aliases: tuple[str, ...] = ()
    external_ids: dict[str, str] | None = None
    routes: dict[str, str] | None = None
    indexable: bool = True
    no_href_reason: str | None = None
    search_group: str | None = None
    sitemap: bool = False
    source_layers: tuple[str, ...] = ()
    league: str | None = None
    role_family: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "type": self.type,
            "name": self.name,
            "aliases": list(self.aliases),
            "external_ids": dict(self.external_ids or {}),
            "href": self.href,
            "href_kind": self.href_kind,
            "routes": dict(self.routes or {}),
            "indexable": self.indexable and self.href is not None,
            "no_href_reason": self.no_href_reason,
            "search_group": self.search_group or self.type,
            "sitemap": self.sitemap,
            "source_layers": list(self.source_layers),
            "league": self.league,
            "role_family": self.role_family,
        }


__all__ = [
    "ENTITY_TYPES",
    "EntityRef",
    "claim_href",
    "club_href",
    "entity_id",
    "fixture_href",
    "former_anchor",
    "former_href",
    "page_href",
    "player_href",
    "scouting_href",
    "season_href",
    "slug",
    "staff_href",
]
