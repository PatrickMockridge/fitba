"""football-data.co.uk Scottish results adapter.

CSV pattern: https://www.football-data.co.uk/mmz4281/{season_code}/{div}.csv
Divisions: SC0 Premiership, SC1 Championship, SC2 League One, SC3 League Two.
Team-level only; no player or event data.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import polars as pl

from fitba.ingest.cache import cache_path, fetch
from fitba.sources.base import Capability, IngestResult, Lane
from fitba.util.dates import current_season, season_code

DIVISIONS: dict[str, dict[str, object]] = {
    "SC0": {"id": "sco:premiership", "name": "Scottish Premiership", "tier": 1},
    "SC1": {"id": "sco:championship", "name": "Scottish Championship", "tier": 2},
    "SC2": {"id": "sco:league-one", "name": "Scottish League One", "tier": 3},
    "SC3": {"id": "sco:league-two", "name": "Scottish League Two", "tier": 4},
}

STAT_COLUMNS = {
    "HS": "home_shots",
    "AS": "away_shots",
    "HST": "home_shots_on_target",
    "AST": "away_shots_on_target",
    "HF": "home_fouls",
    "AF": "away_fouls",
    "HC": "home_corners",
    "AC": "away_corners",
    "HY": "home_yellow",
    "AY": "away_yellow",
    "HR": "home_red",
    "AR": "away_red",
}

# Provider xG is present only in recent SC0 files. Keep it separate from the
# integer stat columns and leave it null everywhere else.
XG_COLUMNS = {
    "HxG": "home_xg",
    "AxG": "away_xg",
}


def url(division: str, season: str) -> str:
    if division not in DIVISIONS:
        raise ValueError(f"unknown division {division!r}; expected one of {sorted(DIVISIONS)}")
    return f"https://www.football-data.co.uk/mmz4281/{season_code(season)}/{division}.csv"


def download(division: str, season: str, *, force: bool = False) -> Path:
    ttl = 6.0 if season == current_season() else None
    return fetch(
        url(division, season),
        cache_path("football_data_uk", season, f"{division}.csv"),
        ttl_hours=ttl,
        force=force,
        expected_marker="Div",
    )


def _num(frame: pl.DataFrame, column: str) -> pl.Expr:
    if column not in frame.columns:
        return pl.lit(None, dtype=pl.Int64)
    return pl.col(column).cast(pl.Int64, strict=False)


def _float(frame: pl.DataFrame, column: str) -> pl.Expr:
    if column not in frame.columns:
        return pl.lit(None, dtype=pl.Float64)
    return pl.col(column).cast(pl.Float64, strict=False)


def _str(frame: pl.DataFrame, column: str) -> pl.Expr:
    if column not in frame.columns:
        return pl.lit(None, dtype=pl.String)
    return pl.col(column).cast(pl.String, strict=False)


def parse_csv(path: Path, season: str) -> pl.DataFrame:
    """Parse a downloaded Scottish CSV into the adapter's canonical columns."""
    raw = pl.read_csv(
        path,
        encoding="utf8-lossy",
        infer_schema_length=2000,
        null_values=[""],
        try_parse_dates=False,
    )
    raw.columns = [column.lstrip("﻿") for column in raw.columns]
    wanted = {"Div", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"}
    missing = wanted - set(raw.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")

    stats = [_num(raw, column).alias(alias) for column, alias in STAT_COLUMNS.items()]
    provider_xg = [_float(raw, column).alias(alias) for column, alias in XG_COLUMNS.items()]
    # Older seasons use dd/mm/yy; newer seasons use dd/mm/yyyy.
    date_text = pl.col("Date").cast(pl.String).str.strip_chars()
    date_expr = (
        pl.when(date_text.str.len_chars() == 8)
        .then(date_text.str.strptime(pl.Date, format="%d/%m/%y", strict=False))
        .otherwise(date_text.str.strptime(pl.Date, format="%d/%m/%Y", strict=False))
    )
    frame = raw.select(
        [
            _str(raw, "Div").alias("division"),
            date_expr.alias("date"),
            _str(raw, "Time").alias("kickoff"),
            _str(raw, "HomeTeam").alias("home_team_raw"),
            _str(raw, "AwayTeam").alias("away_team_raw"),
            _num(raw, "FTHG").alias("home_goals"),
            _num(raw, "FTAG").alias("away_goals"),
            _str(raw, "FTR").alias("result"),
            _num(raw, "HTHG").alias("home_ht_goals"),
            _num(raw, "HTAG").alias("away_ht_goals"),
            _str(raw, "HTR").alias("ht_result"),
            _str(raw, "Referee").alias("referee"),
            *stats,
            *provider_xg,
        ]
    )
    # Drop blank padding rows and any row whose date could not be parsed. A
    # dropped row is visible in the ingest report because the row count changes.
    frame = frame.filter(
        pl.col("date").is_not_null()
        & pl.col("home_team_raw").is_not_null()
        & pl.col("away_team_raw").is_not_null()
    )
    frame = frame.with_columns(
        pl.lit("football_data_uk").alias("source_id"),
        pl.lit(season).alias("season"),
    )
    return frame.sort(["date", "kickoff"], nulls_last=True)


def load(division: str, season: str, *, force: bool = False) -> pl.DataFrame:
    return parse_csv(download(division, season, force=force), season)


def ingest(division: str, season: str, *, force: bool = False) -> IngestResult:
    try:
        frame = load(division, season, force=force)
        return IngestResult(
            source="football_data_uk",
            status="ok",
            rows=frame.height,
            path=str(url(division, season)),
            details={
                "division": division,
                "season": season,
                "competition": DIVISIONS[division]["id"],
            },
        )
    except Exception as exc:  # noqa: BLE001 - reported by the runner
        return IngestResult(source="football_data_uk", status="error", errors=[str(exc)])


class FootballDataUK:
    name = "football_data_uk"
    capabilities: ClassVar[set[Capability]] = {
        Capability.RESULTS,
        Capability.TEAM_MATCH_STATS,
        Capability.FIXTURES,
    }
    lane = Lane.DERIVED_DISPLAY
