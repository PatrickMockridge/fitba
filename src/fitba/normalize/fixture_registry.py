"""Canonical fixture identity across API-Football, football-data.co.uk and cups.

A fixture page needs one key. API-Football supplies that key for the Cormack
era; football-data.co.uk supplies the league match id and the league stat row.
The join is deliberately strict: an ambiguous or missing league alias is an
error, not a guess. Cup and European fixtures keep their API key and have no
football-data.co.uk alias.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import polars as pl

from fitba.normalize.names import slugify
from fitba.normalize.teams import TeamRegistry
from fitba.settings import fixtures_policy

PLAYED_STATUSES = frozenset({"FT", "AET", "PEN"})
ABERDEEN_ID = "sco:aberdeen"


class FixtureRegistryError(ValueError):
    """Raised when fixture identity is ambiguous or inconsistent."""


@dataclass(frozen=True, slots=True)
class FixtureRecord:
    key: str
    fixture_id: int | None
    match_id: str | None
    season: str
    date: str
    competition_id: str
    competition_name: str
    round: str | None
    home_team_id: str
    home_team_name: str
    away_team_id: str
    away_team_name: str
    home_goals: int | None
    away_goals: int | None
    status: str
    venue_name: str | None = None
    referee: str | None = None
    home_ht_goals: int | None = None
    away_ht_goals: int | None = None
    home_penalties: int | None = None
    away_penalties: int | None = None
    extra_time: bool | None = None
    source_ids: dict[str, str] = field(default_factory=dict)

    @property
    def played(self) -> bool:
        return self.status in PLAYED_STATUSES

    @property
    def is_friendly(self) -> bool:
        return self.competition_id.startswith("sco:other:friendlies")

    @property
    def is_aberdeen_home(self) -> bool:
        return self.home_team_id == ABERDEEN_ID

    @property
    def is_aberdeen_away(self) -> bool:
        return self.away_team_id == ABERDEEN_ID

    @property
    def opponent_id(self) -> str:
        return self.away_team_id if self.is_aberdeen_home else self.home_team_id

    @property
    def opponent_name(self) -> str:
        return self.away_team_name if self.is_aberdeen_home else self.home_team_name

    @property
    def venue(self) -> str:
        return "H" if self.is_aberdeen_home else "A"

    @property
    def href(self) -> str | None:
        if not self.played or self.fixture_id is None:
            return None
        return f"/matches/{self.fixture_id}/"

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "fixture_id": self.fixture_id,
            "match_id": self.match_id,
            "season": self.season,
            "date": self.date,
            "competition_id": self.competition_id,
            "competition_name": self.competition_name,
            "round": self.round,
            "home_team_id": self.home_team_id,
            "home_team_name": self.home_team_name,
            "away_team_id": self.away_team_id,
            "away_team_name": self.away_team_name,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "status": self.status,
            "venue": self.venue,
            "venue_name": self.venue_name,
            "referee": self.referee,
            "home_ht_goals": self.home_ht_goals,
            "away_ht_goals": self.away_ht_goals,
            "home_penalties": self.home_penalties,
            "away_penalties": self.away_penalties,
            "extra_time": self.extra_time,
            "href": self.href,
            "source_ids": dict(self.source_ids),
        }


@dataclass(frozen=True, slots=True)
class FixtureCoverage:
    total: int
    played: int
    competitive: int
    friendlies: int
    with_league_alias: int
    by_season: dict[str, int]
    by_competition: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "played": self.played,
            "competitive": self.competitive,
            "friendlies": self.friendlies,
            "with_league_alias": self.with_league_alias,
            "by_season": dict(self.by_season),
            "by_competition": dict(self.by_competition),
        }


class FixtureRegistry:
    def __init__(self, fixtures: Iterable[FixtureRecord]) -> None:
        self.fixtures = tuple(sorted(fixtures, key=lambda item: (item.date, item.key)))
        self.by_key = {item.key: item for item in self.fixtures}
        self.by_fixture_id: dict[int, FixtureRecord] = {}
        self.by_match_id: dict[str, FixtureRecord] = {}
        for item in self.fixtures:
            if item.fixture_id is not None:
                existing = self.by_fixture_id.get(item.fixture_id)
                if existing is not None:
                    raise FixtureRegistryError(f"duplicate fixture_id {item.fixture_id}")
                self.by_fixture_id[item.fixture_id] = item
            if item.match_id:
                existing = self.by_match_id.get(item.match_id)
                if existing is not None:
                    raise FixtureRegistryError(f"duplicate match_id {item.match_id}")
                self.by_match_id[item.match_id] = item

    def played(self) -> tuple[FixtureRecord, ...]:
        return tuple(item for item in self.fixtures if item.played)

    def competitive(self) -> tuple[FixtureRecord, ...]:
        return tuple(item for item in self.played() if not item.is_friendly)

    def friendlies(self) -> tuple[FixtureRecord, ...]:
        return tuple(item for item in self.played() if item.is_friendly)

    def for_season(self, season: str) -> tuple[FixtureRecord, ...]:
        return tuple(item for item in self.fixtures if item.season == season)

    def get(self, fixture_id: int) -> FixtureRecord | None:
        return self.by_fixture_id.get(fixture_id)

    def coverage(self) -> FixtureCoverage:
        played = self.played()
        competitive = tuple(item for item in played if not item.is_friendly)
        by_season: dict[str, int] = {}
        by_competition: dict[str, int] = {}
        for item in played:
            by_season[item.season] = by_season.get(item.season, 0) + 1
            by_competition[item.competition_id] = by_competition.get(item.competition_id, 0) + 1
        return FixtureCoverage(
            total=len(self.fixtures),
            played=len(played),
            competitive=len(competitive),
            friendlies=len(played) - len(competitive),
            with_league_alias=sum(1 for item in played if item.match_id),
            by_season=dict(sorted(by_season.items())),
            by_competition=dict(
                sorted(by_competition.items(), key=lambda item: (-item[1], item[0]))
            ),
        )


def _parse_date(value: Any) -> date | None:
    text = str(value or "")[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _team_id(registry: TeamRegistry, name: str) -> str:
    resolved = registry.resolve(name)
    return resolved if resolved is not None else f"other:{slugify(name)}"


def _fdco_key(row: dict[str, Any]) -> tuple[date | None, str, str, str]:
    return (
        _parse_date(row.get("date")),
        str(row.get("competition_id") or ""),
        str(row.get("home_team_id") or ""),
        str(row.get("away_team_id") or ""),
    )


def _find_fdco(
    *,
    target: tuple[date | None, str, str, str],
    lookup: dict[tuple[date | None, str, str, str], list[dict[str, Any]]],
    tolerance_days: int,
) -> dict[str, Any] | None:
    target_date, competition_id, home_id, away_id = target
    if target_date is None:
        return None
    candidates: list[dict[str, Any]] = []
    for offset in range(-tolerance_days, tolerance_days + 1):
        key = (target_date + timedelta(days=offset), competition_id, home_id, away_id)
        candidates.extend(lookup.get(key, []))
    if len(candidates) > 1:
        ids = ", ".join(str(item.get("match_id")) for item in candidates)
        raise FixtureRegistryError(f"ambiguous football-data.co.uk match: {ids}")
    return candidates[0] if candidates else None


def _history_frames() -> dict[str, pl.DataFrame]:
    from fitba.ingest.history import HISTORY_DIR, load_history_fixtures

    frames: dict[str, pl.DataFrame] = {}
    if not HISTORY_DIR.exists():
        return frames
    for path in sorted(HISTORY_DIR.glob("season=*")):
        if not path.is_dir():
            continue
        season = path.name.split("=", 1)[1]
        frame = load_history_fixtures(season)
        if frame.height:
            frames[season] = frame
    return frames


def build_fixture_registry(
    *,
    history_frames: dict[str, pl.DataFrame] | None = None,
    match_rows: pl.DataFrame | None = None,
    team_registry: TeamRegistry | None = None,
    policy: dict[str, Any] | None = None,
) -> FixtureRegistry:
    """Build the canonical record from API history and league match rows."""
    config = policy if policy is not None else fixtures_policy()
    scope = config.get("scope") or {}
    matching = config.get("matching") or {}
    first_season = str(scope.get("first_season") or "2019-20")
    last_season = str(scope.get("last_season") or "2026-27")
    tolerance_days = int(matching.get("date_tolerance_days") or 0)
    overrides = matching.get("overrides") or {}

    teams = team_registry or TeamRegistry()
    frames = history_frames if history_frames is not None else _history_frames()

    if match_rows is None:
        from fitba.ingest.runner import load_matches

        match_rows = load_matches(None)

    league_rows: list[dict[str, Any]] = []
    if match_rows is not None and match_rows.height:
        league_rows = [
            row
            for row in match_rows.to_dicts()
            if row.get("home_team_id") == ABERDEEN_ID or row.get("away_team_id") == ABERDEEN_ID
        ]
    lookup: dict[tuple[date | None, str, str, str], list[dict[str, Any]]] = {}
    for row in league_rows:
        lookup.setdefault(_fdco_key(row), []).append(row)
    by_match_id = {str(row["match_id"]): row for row in league_rows if row.get("match_id")}

    fixtures: list[FixtureRecord] = []
    for season in sorted(frames):
        if season < first_season or season > last_season:
            continue
        for row in frames[season].to_dicts():
            fixture_id_raw = row.get("fixture_id")
            if fixture_id_raw is None:
                continue
            fixture_id = int(fixture_id_raw)
            home_name = str(row.get("home_team_name") or "Unknown")
            away_name = str(row.get("away_team_name") or "Unknown")
            home_id = _team_id(teams, home_name)
            away_id = _team_id(teams, away_name)
            home_display = (
                teams.canonical_name(home_id) if not home_id.startswith("other:") else home_name
            )
            away_display = (
                teams.canonical_name(away_id) if not away_id.startswith("other:") else away_name
            )
            competition_id = str(row.get("competition_id") or "sco:other:unknown")
            key = f"api:fixture:{fixture_id}"
            override = overrides.get(key)
            if override:
                try:
                    fdco = by_match_id[str(override)]
                except KeyError as error:
                    raise FixtureRegistryError(
                        f"{key}: override match_id {override!r} is not in the league record"
                    ) from error
            else:
                fdco = _find_fdco(
                    target=(
                        _parse_date(row.get("date")),
                        competition_id,
                        home_id,
                        away_id,
                    ),
                    lookup=lookup,
                    tolerance_days=tolerance_days,
                )
            match_id = str(fdco["match_id"]) if fdco and fdco.get("match_id") else None
            source_ids = {"api_football": str(fixture_id)}
            if match_id:
                source_ids["football_data_uk"] = match_id
            fixtures.append(
                FixtureRecord(
                    key=key,
                    fixture_id=fixture_id,
                    match_id=match_id,
                    season=season,
                    date=str(row.get("date") or "")[:10],
                    competition_id=competition_id,
                    competition_name=str(row.get("competition_name") or "Unknown competition"),
                    round=str(row.get("round") or "") or None,
                    home_team_id=home_id,
                    home_team_name=home_display,
                    away_team_id=away_id,
                    away_team_name=away_display,
                    home_goals=row.get("home_goals"),
                    away_goals=row.get("away_goals"),
                    status=str(row.get("status") or ""),
                    venue_name=row.get("venue"),
                    referee=row.get("referee"),
                    home_ht_goals=row.get("home_ht_goals"),
                    away_ht_goals=row.get("away_ht_goals"),
                    home_penalties=row.get("home_penalties"),
                    away_penalties=row.get("away_penalties"),
                    extra_time=row.get("extra_time"),
                    source_ids=source_ids,
                )
            )

    return FixtureRegistry(fixtures)


__all__ = [
    "ABERDEEN_ID",
    "PLAYED_STATUSES",
    "FixtureCoverage",
    "FixtureRecord",
    "FixtureRegistry",
    "FixtureRegistryError",
    "build_fixture_registry",
]
