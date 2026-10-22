"""API-Football adapter.

Licensed base for the public competition layer. The key is read from
``API_FOOTBALL_KEY`` (loaded from the gitignored .env). Raw responses are cached
under .cache/api_football and never committed.

Coverage caveats (key-tested 2026-10-21):
- League Cup: full group stage + knockout fixtures, penalty scores; no standings.
- Scottish Cup: only the rounds the provider carries (50 of 136 ties at test time).
- Player stats: Premiership and covered European leagues; current lower-tier
  player stats were empty at test time.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, ClassVar

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from fitba.ingest.cache import CACHE_DIR
from fitba.sources.base import Capability, Lane
from fitba.util.dates import current_season, season_start_year

BASE = "https://v3.football.api-sports.io"
SCOTLAND_PREMIERSHIP = 179
SCOTLAND_CHAMPIONSHIP = 180
SCOTLAND_LEAGUE_CUP = 185
SCOTLAND_SCOTTISH_CUP = 181
SCOTLAND_LEAGUE_ONE = 183
SCOTLAND_LEAGUE_TWO = 184
SCOTLAND_LEAGUE_IDS = {
    "SC0": SCOTLAND_PREMIERSHIP,
    "SC1": SCOTLAND_CHAMPIONSHIP,
    "SC2": SCOTLAND_LEAGUE_ONE,
    "SC3": SCOTLAND_LEAGUE_TWO,
}
CURRENT_SEASON = season_start_year(current_season())
TIMEOUT = httpx.Timeout(45.0, connect=15.0)
MIN_INTERVAL_SECONDS = float(os.getenv("API_FOOTBALL_MIN_INTERVAL_SECONDS", "0.25"))
_last_request_at = 0.0
_network_requests = 0


class MissingAPIKeyError(RuntimeError):
    """API_FOOTBALL_KEY is not configured."""


class APIFootballError(RuntimeError):
    """The provider returned an error payload."""


class _RetryableStatus(httpx.HTTPStatusError):
    pass


def _api_key() -> str:
    key = os.environ.get("API_FOOTBALL_KEY")
    if not key:
        raise MissingAPIKeyError("API_FOOTBALL_KEY is not set; add it to the gitignored .env")
    return key


def _cache_path(path: str, params: dict[str, Any]) -> Path:
    digest = hashlib.sha1(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()[:16]
    slug = path.strip("/").replace("/", "_")
    return CACHE_DIR / "api_football" / slug / f"{digest}.json"


@retry(
    retry=retry_if_exception_type((httpx.HTTPError, _RetryableStatus)),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    reraise=True,
)
def _fetch(path: str, params: dict[str, Any]) -> dict[str, Any]:
    headers = {"x-apisports-key": _api_key()}
    with httpx.Client(base_url=BASE, headers=headers, timeout=TIMEOUT) as client:
        response = client.get(path, params=params)
        if response.status_code == 429 or response.status_code >= 500:
            raise _RetryableStatus(
                f"retryable status {response.status_code}",
                request=response.request,
                response=response,
            )
        response.raise_for_status()
        payload = response.json()
    errors = payload.get("errors") or {}
    if errors:
        raise APIFootballError(str(errors))
    return payload


def network_requests() -> int:
    """Number of actual API calls made in this process."""
    return _network_requests


def reset_network_requests() -> None:
    global _network_requests
    _network_requests = 0


def set_min_interval(seconds: float) -> None:
    global MIN_INTERVAL_SECONDS
    MIN_INTERVAL_SECONDS = max(0.0, float(seconds))


def _throttle() -> None:
    global _last_request_at
    wait = MIN_INTERVAL_SECONDS - (time.time() - _last_request_at)
    if wait > 0:
        time.sleep(wait)


def request_payload(
    path: str,
    *,
    ttl_hours: float = 6,
    force: bool = False,
    **params: Any,
) -> dict[str, Any]:
    path = path if path.startswith("/") else f"/{path}"
    cache = _cache_path(path, params)
    if not force and cache.exists():
        age = time.time() - cache.stat().st_mtime
        if age < ttl_hours * 3600:
            return json.loads(cache.read_text(encoding="utf-8"))
    global _last_request_at, _network_requests
    _throttle()
    _last_request_at = time.time()
    _network_requests += 1
    payload = _fetch(path, params)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def request(
    path: str,
    *,
    ttl_hours: float = 6,
    force: bool = False,
    **params: Any,
) -> list[dict[str, Any]]:
    return request_payload(path, ttl_hours=ttl_hours, force=force, **params).get("response", [])


def leagues(country: str = "Scotland", *, force: bool = False) -> list[dict[str, Any]]:
    return request("/leagues", ttl_hours=24, force=force, country=country)


def league_coverage(
    league_id: int,
    season: int = CURRENT_SEASON,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Provider coverage flags for one league/season, if advertised."""
    payload = request(
        "/leagues",
        ttl_hours=24,
        force=force,
        id=league_id,
        season=season,
    )
    for item in payload:
        for entry in item.get("seasons") or []:
            if int(entry.get("year") or 0) == int(season):
                return dict(entry.get("coverage") or {})
    return {}


def injuries(
    *,
    league_id: int | None = None,
    team_id: int | None = None,
    season: int | None = None,
    fixture_id: int | None = None,
    date: str | None = None,
    ttl_hours: float = 6,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Provider injury/suspension snapshot.

    Current-season Scottish coverage is reported false; callers must gate on
    ``league_coverage`` before treating this as a feed.
    """
    params: dict[str, Any] = {}
    if league_id is not None:
        params["league"] = league_id
    if team_id is not None:
        params["team"] = team_id
    if season is not None:
        params["season"] = season
    if fixture_id is not None:
        params["fixture"] = fixture_id
    if date is not None:
        params["date"] = date
    if not params:
        raise ValueError("injuries() needs at least one filter")
    return request("/injuries", ttl_hours=ttl_hours, force=force, **params)


def fixtures(
    league_id: int,
    season: int = CURRENT_SEASON,
    *,
    ttl_hours: float = 1,
    force: bool = False,
    **filters: Any,
) -> list[dict[str, Any]]:
    return request(
        "/fixtures",
        ttl_hours=ttl_hours,
        force=force,
        league=league_id,
        season=season,
        **filters,
    )


def team_fixtures(
    team_id: int,
    season: int = CURRENT_SEASON,
    *,
    ttl_hours: float = 168,
    force: bool = False,
) -> list[dict[str, Any]]:
    """All fixtures for a team in a season, across competitions."""
    return request(
        "/fixtures",
        ttl_hours=ttl_hours,
        force=force,
        team=team_id,
        season=season,
    )


def fixtures_statistics(
    fixture_id: int,
    *,
    ttl_hours: float = 168,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Provider team statistics for one fixture, if the plan carries them."""
    return request(
        "/fixtures/statistics",
        ttl_hours=ttl_hours,
        force=force,
        fixture=fixture_id,
    )


def fixtures_rounds(
    league_id: int, season: int = CURRENT_SEASON, *, force: bool = False
) -> list[str]:
    response = request(
        "/fixtures/rounds",
        ttl_hours=24,
        force=force,
        league=league_id,
        season=season,
    )
    return [str(item) for item in response]


def standings(
    league_id: int, season: int = CURRENT_SEASON, *, force: bool = False
) -> list[dict[str, Any]]:
    return request(
        "/standings",
        ttl_hours=6,
        force=force,
        league=league_id,
        season=season,
    )


def fixtures_players(fixture_id: int, *, force: bool = False) -> list[dict[str, Any]]:
    return request("/fixtures/players", ttl_hours=12, force=force, fixture=fixture_id)


def fixtures_lineups(
    fixture_id: int, *, ttl_hours: float = 6, force: bool = False
) -> list[dict[str, Any]]:
    return request("/fixtures/lineups", ttl_hours=ttl_hours, force=force, fixture=fixture_id)


def fixtures_events(fixture_id: int, *, force: bool = False) -> list[dict[str, Any]]:
    return request("/fixtures/events", ttl_hours=6, force=force, fixture=fixture_id)


def players(
    league_id: int,
    season: int = CURRENT_SEASON,
    *,
    page: int = 1,
    force: bool = False,
) -> list[dict[str, Any]]:
    return request(
        "/players",
        ttl_hours=12,
        force=force,
        league=league_id,
        season=season,
        page=page,
    )


def players_by_team(
    team_id: int,
    season: int = CURRENT_SEASON,
    *,
    max_pages: int = 3,
    ttl_hours: float = 12,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Bounded team-season player snapshot, used by the transfer audit.

    The endpoint includes players who have since left, unlike the current-squad
    endpoint. It is deliberately capped and cached; it is not a bulk roster
    download.
    """
    rows: list[dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        payload = request_payload(
            "/players",
            ttl_hours=ttl_hours,
            force=force,
            team=team_id,
            season=season,
            page=page,
        )
        batch = payload.get("response") or []
        rows.extend(batch)
        paging = payload.get("paging") or {}
        total = int(paging.get("total") or 1)
        if not batch or page >= total:
            break
    return rows


def teams(search: str, *, force: bool = False) -> list[dict[str, Any]]:
    return request("/teams", ttl_hours=24, force=force, search=search)


def team(team_id: int, *, ttl_hours: float = 720, force: bool = False) -> list[dict[str, Any]]:
    return request("/teams", ttl_hours=ttl_hours, force=force, id=team_id)


def players_squads(team_id: int, *, force: bool = False) -> list[dict[str, Any]]:
    return request("/players/squads", ttl_hours=12, force=force, team=team_id)


def players_search(
    search: str,
    *,
    league_id: int | None = None,
    team_id: int | None = None,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Search the player catalogue by surname within a league or team.

    The API requires a league or team alongside ``search``. Used only to
    validate a name that already appears in a public source; it is not a bulk
    roster download. Results are cached for a week.
    """
    params: dict[str, Any] = {"search": search}
    if league_id is not None:
        params["league"] = league_id
        params["season"] = CURRENT_SEASON
    elif team_id is not None:
        params["team"] = team_id
    else:
        raise ValueError("players_search() needs a league_id or team_id")
    return request("/players", ttl_hours=168, force=force, **params)


def player(
    player_id: int,
    season: int = CURRENT_SEASON,
    *,
    ttl_hours: float = 12,
    force: bool = False,
) -> list[dict[str, Any]]:
    return request("/players", ttl_hours=ttl_hours, force=force, id=player_id, season=season)


def transfers(
    *,
    team_id: int | None = None,
    player_id: int | None = None,
    ttl_hours: float = 12,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Fetch the full transfer history for a team and/or player.

    API-Football has no season or page filter on /transfers; it returns the full
    history in one response. Callers filter by date.
    """
    if team_id is None and player_id is None:
        raise ValueError("transfers() needs a team_id or player_id")
    params: dict[str, Any] = {}
    if team_id is not None:
        params["team"] = team_id
    if player_id is not None:
        params["player"] = player_id
    return request("/transfers", ttl_hours=ttl_hours, force=force, **params)


class APIFootball:
    name = "api_football"
    capabilities: ClassVar[set[Capability]] = {
        Capability.RESULTS,
        Capability.FIXTURES,
        Capability.LINEUPS,
        Capability.PLAYER_MATCH_STATS,
        Capability.PLAYER_ROLES,
        Capability.TRANSFERS,
        Capability.LOANS,
        Capability.INJURIES,
    }
    lane = Lane.DERIVED_DISPLAY
