"""Canonical team registry and alias resolution.

Source names never become canonical IDs. Unknown names are either rejected
(strict mode, used for table marts) or given a clearly provisional ID and
reported (backfill mode).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fitba.normalize.names import (
    normalize_name,
    slugify,
    team_slug,
    titlecase_club_name,
)
from fitba.settings import teams as teams_config


@dataclass(frozen=True, slots=True)
class Team:
    id: str
    name: str
    country: str = "Scotland"
    city: str | None = None
    aliases: tuple[str, ...] = ()

    @property
    def slug(self) -> str:
        return team_slug(self.id)


class UnknownTeamError(KeyError):
    """Raised when a source name cannot be resolved in strict mode."""


class TeamRegistry:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        payload = data if data is not None else teams_config()
        self._teams: dict[str, Team] = {}
        self._by_alias: dict[str, str] = {}
        for row in payload.get("teams", []):
            team = Team(
                id=row["id"],
                name=row["name"],
                country=row.get("country", "Scotland"),
                city=row.get("city"),
                aliases=tuple(row.get("aliases", [])),
            )
            if team.id in self._teams:
                raise ValueError(f"duplicate team id {team.id}")
            self._teams[team.id] = team
            for alias in (team.name, *team.aliases):
                key = normalize_name(alias)
                existing = self._by_alias.get(key)
                if existing is not None and existing != team.id:
                    raise ValueError(f"alias {alias!r} maps to both {existing} and {team.id}")
                self._by_alias[key] = team.id

    def get(self, team_id: str) -> Team:
        return self._teams[team_id]

    def canonical_name(self, team_id: str) -> str:
        team = self._teams.get(team_id)
        return team.name if team else team_id

    def display_name(self, raw: str) -> str:
        """Canonical name for a resolved club, else a title-cased fallback."""
        team_id = self.resolve(raw)
        if team_id is not None:
            return self.canonical_name(team_id)
        return titlecase_club_name(raw)

    def display_name_for_id(self, team_id: str | None, raw: str | None) -> str:
        """Use the canonical name for a resolved id; otherwise fix the raw name."""
        if team_id == "sco:free-agent" or normalize_name(str(raw or "")) == "free agent":
            return "Free agent"
        if team_id and not team_id.startswith("sco:provisional-"):
            team = self._teams.get(team_id)
            if team is not None:
                return team.name
        return titlecase_club_name(str(raw or "Unknown"))

    def resolve(self, raw: str) -> str | None:
        key = normalize_name(raw)
        if key in self._by_alias:
            return self._by_alias[key]
        # A few feed spellings add a club suffix or punctuation; try a light
        # suffix-stripped pass before declaring failure.
        stripped = key.removesuffix(" football club").removesuffix(" fc").strip()
        return self._by_alias.get(stripped)

    def resolve_or_raise(self, raw: str) -> str:
        team_id = self.resolve(raw)
        if team_id is None:
            raise UnknownTeamError(raw)
        return team_id

    def provisional(self, raw: str) -> str:
        return f"sco:provisional-{slugify(raw)}"

    def all(self) -> list[Team]:
        return sorted(self._teams.values(), key=lambda team: team.name)
