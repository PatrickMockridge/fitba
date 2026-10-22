"""Canonical competition labels and provider-league resolution.

Provider payloads use display names ("FA Cup", "Friendlies Clubs") that are not
fitba's public labels. This module is the single place that maps a competition
id, or an API-Football league payload, to the configured name and short name.
Public copy never reads the provider label directly.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fitba.normalize.names import slugify, titlecase_club_name
from fitba.settings import competitions as competitions_config
from fitba.settings import cups as cups_config

FRIENDLY_PREFIX = "sco:other:friendlies"
FRIENDLY_NAME = "Club friendlies"
FRIENDLY_SHORT = "Friendlies"
UNKNOWN_NAME = "Unknown competition"

# Competitions that are not part of the SPFL/cup configuration files.
STATIC_COMPETITIONS: dict[str, tuple[str, str]] = {
    "uefa:europa-league": ("UEFA Europa League", "Europa League"),
    "uefa:conference-league": ("UEFA Conference League", "Conference League"),
    "uefa:champions-league": ("UEFA Champions League", "Champions League"),
    FRIENDLY_PREFIX: (FRIENDLY_NAME, FRIENDLY_SHORT),
}

# Provider spellings that need an explicit mapping. The key is normalised.
PROVIDER_ALIASES: dict[str, str] = {
    "scottish cup": "sco:scottish-cup",
    "scottish gas mens scottish cup": "sco:scottish-cup",
    "premier sports cup": "sco:league-cup",
    "friendlies clubs": FRIENDLY_PREFIX,
    "friendlies": FRIENDLY_PREFIX,
    "club friendlies": FRIENDLY_PREFIX,
}


def _normalise(value: str) -> str:
    return " ".join(str(value or "").casefold().replace("&", " and ").split())


@lru_cache(maxsize=1)
def _catalogue() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in competitions_config().get("competitions") or []:
        if row.get("id"):
            rows[str(row["id"])] = row
    for row in cups_config().get("cups") or []:
        if row.get("id"):
            rows[str(row["id"])] = row
    return rows


def competition_id_from_league(league: dict[str, Any]) -> str:
    """Resolve an API-Football league payload to a canonical competition id."""
    league_id = int(league.get("id") or 0)
    name = str(league.get("name") or "")
    if league_id == 179:
        return "sco:premiership"
    if league_id == 185:
        return "sco:league-cup"
    if league_id == 181:
        return "sco:scottish-cup"
    folded = name.casefold()
    if "europa league" in folded:
        return "uefa:europa-league"
    if "conference league" in folded:
        return "uefa:conference-league"
    if "champions league" in folded:
        return "uefa:champions-league"
    alias = PROVIDER_ALIASES.get(_normalise(name))
    if alias is not None:
        return alias
    if folded.startswith("friendlies"):
        return FRIENDLY_PREFIX
    return f"sco:other:{slugify(name)}"


def _configured(competition_id: str) -> dict[str, Any] | None:
    return _catalogue().get(competition_id)


def canonical_name(competition_id: str, provider_name: str | None = None) -> str:
    """Public long name for a competition id, never a raw provider label."""
    row = _configured(competition_id)
    if row and row.get("name"):
        return str(row["name"])
    if competition_id.startswith(FRIENDLY_PREFIX):
        return FRIENDLY_NAME
    static = STATIC_COMPETITIONS.get(competition_id)
    if static:
        return static[0]
    alias = PROVIDER_ALIASES.get(_normalise(provider_name or ""))
    if alias and alias != competition_id:
        return canonical_name(alias)
    return titlecase_club_name(str(provider_name or UNKNOWN_NAME))


def short_name(competition_id: str, provider_name: str | None = None) -> str:
    """Public short name for navigation, chips and compact tables."""
    row = _configured(competition_id)
    if row:
        return str(row.get("short_name") or row.get("name") or UNKNOWN_NAME)
    if competition_id.startswith(FRIENDLY_PREFIX):
        return FRIENDLY_SHORT
    static = STATIC_COMPETITIONS.get(competition_id)
    if static:
        return static[1]
    return canonical_name(competition_id, provider_name)


def canonical_from_league(league: dict[str, Any]) -> tuple[str, str]:
    """Return the canonical (id, long name) for an API-Football league."""
    competition_id = competition_id_from_league(league)
    return competition_id, canonical_name(competition_id, str(league.get("name") or ""))


__all__ = [
    "FRIENDLY_NAME",
    "FRIENDLY_PREFIX",
    "canonical_from_league",
    "canonical_name",
    "competition_id_from_league",
    "short_name",
]
