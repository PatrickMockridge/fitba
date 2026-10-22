"""Shared source-adapter types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol


class Capability(StrEnum):
    RESULTS = "results"
    FIXTURES = "fixtures"
    TEAM_MATCH_STATS = "team_match_stats"
    PLAYER_MATCH_STATS = "player_match_stats"
    EVENTS = "events"
    SHOTS = "shots"
    LINEUPS = "lineups"
    HEATMAPS = "heatmaps"
    MARKET_VALUES = "market_values"
    TRANSFERS = "transfers"
    LOANS = "loans"
    NEWS = "news"
    TEAM_ELO = "team_elo"
    FAN_SIGNAL = "fan_signal"
    SENTIMENT = "sentiment"
    PLAYER_ATTRIBUTES = "player_attributes"
    PLAYER_ROLES = "player_roles"
    INJURIES = "injuries"


class Lane(StrEnum):
    OPEN = "open"
    DERIVED_DISPLAY = "derived_display"
    # Reading a public page is fair use; this lane means the source may not be
    # ingested automatically or republished.
    NO_PUBLICATION = "no_publication"


@dataclass(slots=True)
class IngestResult:
    source: str
    status: str
    rows: int = 0
    path: str | None = None
    errors: list[str] | None = None
    unresolved: list[str] | None = None
    details: dict[str, Any] | None = None


class SourceAdapter(Protocol):
    name: str
    capabilities: set[Capability]
    lane: Lane

    def ingest(self, *args: Any, **kwargs: Any) -> IngestResult: ...
