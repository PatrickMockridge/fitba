"""Ingest and persist club fixtures/results across competitions."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

from fitba.normalize.teams import TeamRegistry
from fitba.settings import NORMALIZED_DIR, ensure_dirs
from fitba.sources import spfl
from fitba.sources.base import IngestResult

CLUB_FIXTURE_COLUMNS = [
    "match_id",
    "competition_id",
    "competition_name",
    "season",
    "date",
    "kickoff",
    "home_team_id",
    "home_team_name",
    "away_team_id",
    "away_team_name",
    "home_goals",
    "away_goals",
    "status",
    "source_id",
    "ingested_at",
]


def fixtures_path(club_slug: str) -> Path:
    return NORMALIZED_DIR / "club_fixtures" / f"{club_slug}.parquet"


def _normalise(frame: pl.DataFrame, registry: TeamRegistry) -> tuple[pl.DataFrame, list[str]]:
    unresolved: list[str] = []
    for side in ("home", "away"):
        raw = f"{side}_team_raw"
        ids: list[str] = []
        for name in frame[raw].to_list():
            resolved = registry.resolve(name)
            if resolved is None:
                unresolved.append(name)
                resolved = registry.provisional(name)
            ids.append(resolved)
        frame = frame.with_columns(pl.Series(f"{side}_team_id", ids, dtype=pl.String))
        frame = frame.with_columns(
            pl.col(f"{side}_team_id")
            .map_elements(registry.canonical_name, return_dtype=pl.String)
            .alias(f"{side}_team_name")
        )
    return frame.select(CLUB_FIXTURE_COLUMNS), unresolved


def ingest_club_fixtures(club_slug: str = "aberdeen", *, force: bool = False) -> IngestResult:
    ensure_dirs()
    source = spfl.ingest(club_slug, force=force)
    if source.status != "ok":
        return source
    try:
        frame = spfl.load(club_slug)
        registry = TeamRegistry()
        normalized, unresolved = _normalise(frame, registry)

        path = fixtures_path(club_slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            existing = pl.read_parquet(path)
            normalized = pl.concat([existing, normalized], how="vertical_relaxed")
        normalized = normalized.unique(subset=["match_id"], keep="last")
        # Scheduled rows whose date has passed are stale: the fixture was either
        # played (and will appear as a result) or postponed.
        normalized = normalized.filter(
            (pl.col("status") == "played") | (pl.col("date") >= date.today())
        )
        normalized = normalized.sort(["date", "kickoff"], nulls_last=True)
        normalized.write_parquet(path)
        return IngestResult(
            source="spfl",
            status="ok",
            rows=normalized.height,
            path=str(path),
            unresolved=sorted(set(unresolved)),
            details={"club": club_slug},
        )
    except Exception as exc:  # noqa: BLE001 - reported to the CLI
        return IngestResult(source="spfl", status="error", errors=[str(exc)])


def load_club_fixtures(club_slug: str = "aberdeen") -> pl.DataFrame:
    path = fixtures_path(club_slug)
    if not path.exists():
        return pl.DataFrame({column: [] for column in CLUB_FIXTURE_COLUMNS})
    return pl.read_parquet(path)
