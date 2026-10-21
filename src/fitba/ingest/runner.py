"""Ingest orchestration: fetch, normalise and persist match partitions."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import polars as pl

from fitba.normalize.teams import TeamRegistry, UnknownTeamError
from fitba.settings import NORMALIZED_DIR, REPORTS_DIR, ensure_dirs
from fitba.sources import football_data_uk
from fitba.sources.base import IngestResult
from fitba.util.dates import current_season, utc_now_iso

MATCH_COLUMNS = [
    "match_id",
    "competition_id",
    "competition_name",
    "season",
    "division",
    "date",
    "kickoff",
    "phase",
    "home_team_id",
    "home_team_name",
    "away_team_id",
    "away_team_name",
    "home_goals",
    "away_goals",
    "result",
    "home_ht_goals",
    "away_ht_goals",
    "ht_result",
    "referee",
    "home_shots",
    "away_shots",
    "home_shots_on_target",
    "away_shots_on_target",
    "home_fouls",
    "away_fouls",
    "home_corners",
    "away_corners",
    "home_yellow",
    "away_yellow",
    "home_red",
    "away_red",
    "source_id",
    "ingested_at",
]


@dataclass(slots=True)
class IngestReport:
    season: str
    results: list[IngestResult] = field(default_factory=list)
    unresolved_teams: list[str] = field(default_factory=list)
    written: list[str] = field(default_factory=list)

    @property
    def rows(self) -> int:
        return sum(result.rows for result in self.results)

    @property
    def has_errors(self) -> bool:
        return any(result.status != "ok" for result in self.results)

    def to_dict(self) -> dict[str, object]:
        return {
            "season": self.season,
            "generated_at": utc_now_iso(),
            "rows": self.rows,
            "has_errors": self.has_errors,
            "results": [asdict(result) for result in self.results],
            "unresolved_teams": sorted(set(self.unresolved_teams)),
            "written": self.written,
        }


def _team_map(
    registry: TeamRegistry, names: list[str], *, strict: bool
) -> tuple[dict[str, str], list[str]]:
    mapping: dict[str, str] = {}
    unresolved: list[str] = []
    for name in names:
        if not name:
            continue
        try:
            team_id = registry.resolve_or_raise(name)
        except UnknownTeamError:
            if strict:
                raise
            team_id = registry.provisional(name)
            unresolved.append(name)
        mapping[name] = team_id
    return mapping, unresolved


def normalize_matches(
    frame: pl.DataFrame,
    *,
    season: str,
    division: str,
    registry: TeamRegistry,
    strict_teams: bool = False,
) -> tuple[pl.DataFrame, list[str]]:
    competition = football_data_uk.DIVISIONS[division]
    competition_id = str(competition["id"])
    competition_name = str(competition["name"])
    competition_slug = competition_id.split(":", 1)[-1]

    names = sorted(
        {
            *(frame["home_team_raw"].drop_nulls().unique().to_list()),
            *(frame["away_team_raw"].drop_nulls().unique().to_list()),
        }
    )
    mapping, unresolved = _team_map(registry, names, strict=strict_teams)

    def _attach(column: str, id_column: str, name_column: str) -> pl.DataFrame:
        alias = pl.DataFrame({"raw_name": list(mapping.keys()), id_column: list(mapping.values())})
        return frame.join(alias, left_on=column, right_on="raw_name", how="left").with_columns(
            pl.col(id_column)
            .map_elements(registry.canonical_name, return_dtype=pl.String)
            .alias(name_column)
        )

    frame = _attach("home_team_raw", "home_team_id", "home_team_name")
    frame = _attach("away_team_raw", "away_team_id", "away_team_name")

    frame = frame.with_columns(
        pl.lit(competition_id).alias("competition_id"),
        pl.lit(competition_name).alias("competition_name"),
        pl.lit(season).alias("season"),
        pl.lit(division).alias("division"),
        pl.lit("regular").alias("phase"),
        pl.lit(utc_now_iso()).alias("ingested_at"),
        pl.concat_str(
            [
                pl.lit(competition_slug),
                pl.lit(season),
                pl.col("date").cast(pl.String),
                pl.col("home_team_id").str.split(":").list.last(),
                pl.col("away_team_id").str.split(":").list.last(),
            ],
            separator="-",
        ).alias("match_id"),
    )

    for column in MATCH_COLUMNS:
        if column not in frame.columns:
            frame = frame.with_columns(pl.lit(None).alias(column))
    return frame.select(MATCH_COLUMNS).sort(["date", "kickoff"], nulls_last=True), unresolved


def _partition_path(season: str, division: str) -> Path:
    return (
        NORMALIZED_DIR / "matches" / f"season={season}" / f"division={division}" / "matches.parquet"
    )


def rebuild_combined() -> Path | None:
    root = NORMALIZED_DIR / "matches"
    files = sorted(root.glob("season=*/division=*/matches.parquet"))
    if not files:
        return None
    frame = pl.concat(
        [pl.read_parquet(path) for path in files],
        how="vertical_relaxed",
    ).sort(["season", "date", "kickoff"], nulls_last=True)
    target = NORMALIZED_DIR / "matches.parquet"
    frame.write_parquet(target)
    return target


def ingest_season(
    season: str,
    *,
    divisions: list[str] | None = None,
    force: bool = False,
    strict_teams: bool = False,
) -> IngestReport:
    ensure_dirs()
    registry = TeamRegistry()
    divisions = divisions or list(football_data_uk.DIVISIONS)
    report = IngestReport(season=season)
    for division in divisions:
        source_result = football_data_uk.ingest(division, season, force=force)
        if source_result.status != "ok":
            report.results.append(source_result)
            continue
        try:
            raw = football_data_uk.load(division, season, force=False)
            normalized, unresolved = normalize_matches(
                raw,
                season=season,
                division=division,
                registry=registry,
                strict_teams=strict_teams,
            )
            path = _partition_path(season, division)
            path.parent.mkdir(parents=True, exist_ok=True)
            normalized.write_parquet(path)
            report.results.append(
                IngestResult(
                    source="football_data_uk",
                    status="ok",
                    rows=normalized.height,
                    path=str(path),
                    unresolved=unresolved,
                    details={
                        "division": division,
                        "competition": str(football_data_uk.DIVISIONS[division]["id"]),
                    },
                )
            )
            report.written.append(str(path))
            report.unresolved_teams.extend(unresolved)
        except Exception as exc:  # noqa: BLE001 - report and continue per source
            report.results.append(
                IngestResult(
                    source="football_data_uk",
                    status="error",
                    errors=[f"{division} {season}: {exc}"],
                )
            )
    combined = rebuild_combined()
    if combined:
        report.written.append(str(combined))
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / f"ingest-{season}-{current_season()}.json").write_text(
        json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    return report


def load_matches(seasons: list[str] | None = None) -> pl.DataFrame:
    root = NORMALIZED_DIR / "matches"
    files = sorted(root.glob("season=*/division=*/matches.parquet"))
    if not files:
        raise FileNotFoundError("no normalized matches; run `fitba ingest` first")
    frame = pl.concat([pl.read_parquet(path) for path in files], how="vertical_relaxed")
    if seasons:
        frame = frame.filter(pl.col("season").is_in(seasons))
    return frame
