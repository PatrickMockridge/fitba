"""Build the per-fixture broadcast and streaming document.

Every fact is curated from an official club or SPFL page. The builder never
reads a broadcaster schedule, an article body, a price or a stream URL, and it
never infers a broadcaster from kickoff, competition or a previous fixture.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from fitba.publish.epoch import EpochModel
from fitba.settings import CONFIG_DIR, load_yaml

SOURCE_INFO = {
    "afc_news": {
        "id": "afc_news",
        "name": "Aberdeen FC news",
        "url": "https://www.afc.co.uk/en/news",
        "attribution": "Aberdeen FC",
    },
    "spfl": {
        "id": "spfl",
        "name": "SPFL TV selections and fixture changes",
        "url": "https://spfl.co.uk/news/tv-selections-and-fixture-changes",
        "attribution": "SPFL",
    },
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class BroadcastOutlet(StrictModel):
    platform: str
    medium: Literal["video", "audio"]
    access: Literal["live", "ppv", "replay"]


class BroadcastSource(StrictModel):
    source_id: str
    url: str
    title: str
    verified_at: str
    confidence: Literal["confirmed", "reported", "curated", "unknown"]


class CuratedRegion(StrictModel):
    status: Literal["confirmed", "not_announced", "unknown"]
    outlets: list[BroadcastOutlet] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class CuratedFixture(StrictModel):
    fixture_id: int | str
    season: str
    date: str
    kickoff: str
    competition_id: str
    home_team_name: str
    away_team_name: str
    domestic: CuratedRegion
    international: CuratedRegion
    sources: list[BroadcastSource] = Field(default_factory=list)


class ReferenceDocument(StrictModel):
    version: int
    season: str
    updated_at: str
    fixtures: list[CuratedFixture] = Field(default_factory=list)


class RegionBlock(StrictModel):
    status: Literal["confirmed", "blackout_window", "not_announced", "unknown"]
    basis: Literal[
        "official_source",
        "rule",
        "not_curated",
        "fixture_conflict",
        "source_conflict",
    ]
    outlets: list[BroadcastOutlet] = Field(default_factory=list)
    note: str
    source_ids: list[str] = Field(default_factory=list)


class FixtureBlock(StrictModel):
    fixture_id: str
    season: str
    date: str
    kickoff: str | None
    kickoff_tz: str
    competition_id: str
    competition_name: str | None
    home_team_name: str | None
    away_team_name: str | None
    venue: str | None
    fixture_status: str
    state: Literal["curated", "derived", "fixture_conflict", "source_conflict"]
    domestic: RegionBlock
    international: RegionBlock
    sources: list[BroadcastSource] = Field(default_factory=list)


class BroadcastDocument(EpochModel):
    schema_version: str
    generated_at: str
    season: str
    timezone: str
    redtv_url: str
    fixtures: list[FixtureBlock]
    sources: list[dict[str, Any]]
    notes: str


def broadcast_schema() -> dict[str, Any]:
    return BroadcastDocument.model_json_schema()


def _copy(policy: dict[str, Any], key: str) -> str:
    value = str((policy.get("copy") or {}).get(key) or "").strip()
    if not value:
        raise ValueError(f"broadcast policy: missing copy {key}")
    return " ".join(value.split())


def _host(url: str) -> str:
    return urlparse(url).hostname or ""


def _validate_sources(
    row: CuratedFixture, policy: dict[str, Any]
) -> list[BroadcastSource]:
    allowed_ids = set(policy.get("allowed_source_ids") or [])
    allowed_hosts = set(policy.get("allowed_hosts") or [])
    source_hosts = policy.get("source_hosts") or {}
    max_title = int(policy.get("source_max_title_chars") or 160)
    for source in row.sources:
        if source.source_id not in allowed_ids:
            raise ValueError(f"broadcast {row.fixture_id}: unknown source {source.source_id}")
        if not source.url.startswith("https://"):
            raise ValueError(f"broadcast {row.fixture_id}: source URL must be HTTPS")
        host = _host(source.url)
        if host not in allowed_hosts or host not in set(
            source_hosts.get(source.source_id) or []
        ):
            raise ValueError(
                f"broadcast {row.fixture_id}: host {host!r} is not allowed for {source.source_id}"
            )
        if len(source.title) > max_title:
            raise ValueError(f"broadcast {row.fixture_id}: source title is too long")
        if not source.verified_at.startswith("20"):
            raise ValueError(f"broadcast {row.fixture_id}: invalid verified_at")
    return row.sources


def _confirmed_copy(policy: dict[str, Any], source_ids: list[str]) -> str:
    key = "curated_confirmed_spfl" if source_ids == ["spfl"] else "curated_confirmed_afc"
    return _copy(policy, key)


def _region_from_curated(
    region: CuratedRegion,
    *,
    policy: dict[str, Any],
    international: bool,
) -> RegionBlock:
    if region.status == "confirmed":
        if not region.outlets:
            raise ValueError("broadcast: confirmed region needs an outlet")
        if not region.source_ids:
            raise ValueError("broadcast: confirmed region needs a source id")
        return RegionBlock(
            status="confirmed",
            basis="official_source",
            outlets=region.outlets,
            note=_confirmed_copy(policy, region.source_ids),
            source_ids=region.source_ids,
        )
    if international:
        return RegionBlock(
            status="unknown",
            basis="official_source",
            outlets=[],
            note=_copy(policy, "curated_international_unknown"),
            source_ids=region.source_ids,
        )
    if region.status == "not_announced":
        note = _copy(policy, "curated_uk_unannounced")
    else:
        note = _copy(policy, "curated_uk_unknown")
    return RegionBlock(
        status=region.status,
        basis="official_source",
        outlets=[],
        note=note,
        source_ids=region.source_ids,
    )


def _withheld(
    *,
    policy: dict[str, Any],
    state: Literal["fixture_conflict", "source_conflict"],
) -> tuple[RegionBlock, RegionBlock]:
    key = "fixture_conflict" if state == "fixture_conflict" else "identity_conflict"
    note = _copy(policy, key)
    basis = "fixture_conflict" if state == "fixture_conflict" else "source_conflict"
    return (
        RegionBlock(status="unknown", basis=basis, note=note),
        RegionBlock(status="unknown", basis=basis, note=note),
    )


def _is_saturday_blackout(row: dict[str, Any], timezone: str) -> bool:
    value = str(row.get("date") or "")
    kickoff = str(row.get("kickoff") or "")
    if not value or not kickoff:
        return False
    try:
        local = datetime.fromisoformat(f"{value}T{kickoff}:00").replace(
            tzinfo=ZoneInfo(timezone)
        )
    except ValueError:
        return False
    return local.weekday() == 5 and local.time().strftime("%H:%M") == "15:00"


def _identity_matches(row: dict[str, Any], curated: CuratedFixture, season: str) -> bool:
    return (
        str(row.get("date") or "") == curated.date
        and str(row.get("kickoff") or "") == curated.kickoff
        and str(row.get("competition_id") or "") == curated.competition_id
        and str(row.get("home_team_name") or "") == curated.home_team_name
        and str(row.get("away_team_name") or "") == curated.away_team_name
        and str(row.get("season") or season) == curated.season
    )


def build_broadcast_payload(
    *,
    season: str,
    generated_at: str,
    scheduled_rows: list[dict[str, Any]],
    reference: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = policy or load_yaml(CONFIG_DIR / "broadcast.yaml")
    reference_config = reference if reference is not None else {}
    rules: dict[str, Any] = config or {}
    curated_document = (
        ReferenceDocument.model_validate(reference_config) if reference_config else None
    )
    curated: dict[str, CuratedFixture] = {}
    if curated_document:
        for row in curated_document.fixtures:
            key = str(row.fixture_id)
            if key in curated:
                raise ValueError(f"broadcast: duplicate fixture {key}")
            curated[key] = row

    timezone = str(rules.get("timezone") or "Europe/London")
    fixtures: list[FixtureBlock] = []
    for row in scheduled_rows:
        fixture_id = str(row.get("fixture_id") or "")
        if not fixture_id:
            continue
        match = curated.get(fixture_id)
        source_rows: list[BroadcastSource] = []
        if str(row.get("status") or "") == "conflict_review":
            domestic, international = _withheld(policy=rules, state="fixture_conflict")
            state = "fixture_conflict"
        elif match is not None and not _identity_matches(row, match, season):
            domestic, international = _withheld(policy=rules, state="source_conflict")
            state = "source_conflict"
        elif match is not None:
            source_rows = _validate_sources(match, rules)
            confirmed_sources = {
                source.source_id
                for source in source_rows
                if source.confidence == "confirmed"
            }
            for region in (match.domestic, match.international):
                if region.status == "confirmed" and not (
                    set(region.source_ids) & confirmed_sources
                ):
                    raise ValueError(
                        f"broadcast {fixture_id}: confirmed region needs a confirmed source"
                    )
            domestic = _region_from_curated(
                match.domestic, policy=rules, international=False
            )
            international = _region_from_curated(
                match.international, policy=rules, international=True
            )
            state = "curated"
        else:
            blackout = _is_saturday_blackout(row, timezone)
            domestic = RegionBlock(
                status="blackout_window" if blackout else "not_announced",
                basis="rule" if blackout else "not_curated",
                outlets=[],
                note=_copy(rules, "blackout_uk" if blackout else "uncurated_uk"),
            )
            international = RegionBlock(
                status="unknown",
                basis="not_curated",
                outlets=[],
                note=_copy(rules, "uncurated_international"),
            )
            state = "derived"
        fixtures.append(
            FixtureBlock(
                fixture_id=fixture_id,
                season=str(row.get("season") or season),
                date=str(row.get("date") or ""),
                kickoff=row.get("kickoff"),
                kickoff_tz=timezone,
                competition_id=str(row.get("competition_id") or ""),
                competition_name=row.get("competition_name"),
                home_team_name=row.get("home_team_name"),
                away_team_name=row.get("away_team_name"),
                venue=row.get("venue"),
                fixture_status=str(row.get("status") or ""),
                state=state,
                domestic=domestic,
                international=international,
                sources=source_rows,
            )
        )

    return BroadcastDocument(
        schema_version="1.0.0",
        generated_at=generated_at,
        season=season,
        timezone=timezone,
        redtv_url=str(rules.get("redtv_url") or "https://redtv.afc.co.uk/"),
        fixtures=fixtures,
        sources=[SOURCE_INFO["afc_news"], SOURCE_INFO["spfl"]],
        notes=_copy(rules, "document_note"),
    ).model_dump(mode="json")


__all__ = [
    "BroadcastDocument",
    "FixtureBlock",
    "broadcast_schema",
    "build_broadcast_payload",
]
