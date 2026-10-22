"""League tables computed from match results.

Points, goal difference and goals scored are the primary sort. Clubs still tied
are separated by a mini-league of head-to-head results, then by name. Playoff
matches are excluded because the football-data.co.uk league CSVs do not contain
them; `phase` is retained so a future source can add them safely.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import polars as pl

from fitba.settings import competitions as competitions_config
from fitba.settings import disciplinary as disciplinary_config
from fitba.util.dates import utc_now_iso

TABLE_COLUMNS = [
    "position",
    "team_id",
    "team_name",
    "played",
    "won",
    "drawn",
    "lost",
    "gf",
    "ga",
    "gd",
    "raw_points",
    "deduction",
    "points",
    "form",
    "season",
    "competition_id",
    "competition_name",
    "updated_at",
]


def _playable(matches: pl.DataFrame) -> pl.DataFrame:
    required = {"home_team_id", "away_team_id", "home_goals", "away_goals"}
    missing = required - set(matches.columns)
    if missing:
        raise ValueError(f"match frame missing columns: {sorted(missing)}")
    return matches.filter(
        (pl.col("phase") == "regular")
        & pl.col("home_goals").is_not_null()
        & pl.col("away_goals").is_not_null()
        & pl.col("home_team_id").is_not_null()
        & pl.col("away_team_id").is_not_null()
    )


def playable_matches(matches: pl.DataFrame) -> pl.DataFrame:
    """Public alias for the playable-match filter."""
    return _playable(matches)


def team_match_rows(matches: pl.DataFrame) -> pl.DataFrame:
    """One row per team per match (home and away views concatenated)."""
    frame = _playable(matches)
    home = frame.select(
        pl.col("match_id"),
        pl.col("date"),
        pl.col("home_team_id").alias("team_id"),
        pl.col("home_team_name").alias("team_name"),
        pl.col("away_team_id").alias("opponent_id"),
        pl.lit("H").alias("venue"),
        pl.col("home_goals").alias("gf"),
        pl.col("away_goals").alias("ga"),
    )
    away = frame.select(
        pl.col("match_id"),
        pl.col("date"),
        pl.col("away_team_id").alias("team_id"),
        pl.col("away_team_name").alias("team_name"),
        pl.col("home_team_id").alias("opponent_id"),
        pl.lit("A").alias("venue"),
        pl.col("away_goals").alias("gf"),
        pl.col("home_goals").alias("ga"),
    )
    rows = pl.concat([home, away], how="vertical_relaxed")
    return rows.with_columns(
        pl.when(pl.col("gf") > pl.col("ga"))
        .then(pl.lit("W"))
        .when(pl.col("gf") == pl.col("ga"))
        .then(pl.lit("D"))
        .otherwise(pl.lit("L"))
        .alias("result"),
        pl.when(pl.col("gf") > pl.col("ga"))
        .then(3)
        .when(pl.col("gf") == pl.col("ga"))
        .then(1)
        .otherwise(0)
        .alias("points"),
    )


def _h2h_order(teams: list[dict[str, Any]], match_rows: pl.DataFrame) -> list[dict[str, Any]]:
    ids = {team["team_id"] for team in teams}
    mini = match_rows.filter(pl.col("team_id").is_in(ids) & pl.col("opponent_id").is_in(ids))
    if mini.height == 0:
        return sorted(teams, key=lambda team: team["team_name"])
    agg = (
        mini.group_by("team_id")
        .agg(
            pl.col("points").sum().alias("h2h_points"),
            (pl.col("gf").sum() - pl.col("ga").sum()).alias("h2h_gd"),
            pl.col("gf").sum().alias("h2h_gf"),
        )
        .to_dicts()
    )
    by_id = {row["team_id"]: row for row in agg}
    return sorted(
        teams,
        key=lambda team: (
            -by_id.get(team["team_id"], {}).get("h2h_points", 0),
            -by_id.get(team["team_id"], {}).get("h2h_gd", 0),
            -by_id.get(team["team_id"], {}).get("h2h_gf", 0),
            team["team_name"],
        ),
    )


def _rank(rows: pl.DataFrame, deductions: dict[str, int] | None = None) -> list[dict[str, Any]]:
    deductions = deductions or {}
    grouped = (
        rows.group_by("team_id", "team_name")
        .agg(
            pl.len().alias("played"),
            (pl.col("result") == "W").sum().alias("won"),
            (pl.col("result") == "D").sum().alias("drawn"),
            (pl.col("result") == "L").sum().alias("lost"),
            pl.col("gf").sum().alias("gf"),
            pl.col("ga").sum().alias("ga"),
            pl.col("points").sum().alias("raw_points"),
            pl.col("result").sort_by("date", descending=True).head(5).str.join("").alias("form"),
        )
        .with_columns((pl.col("gf") - pl.col("ga")).alias("gd"))
        .to_dicts()
    )
    for row in grouped:
        deduction = int(deductions.get(row["team_id"], 0))
        row["deduction"] = deduction
        row["points"] = row["raw_points"] - deduction
    buckets: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in grouped:
        buckets[(row["points"], row["gd"], row["gf"])].append(row)

    ordered: list[dict[str, Any]] = []
    for key in sorted(buckets, reverse=True):
        bucket = buckets[key]
        if len(bucket) == 1:
            ordered.extend(bucket)
        else:
            ordered.extend(_h2h_order(bucket, rows))
    return ordered


def _split_order(
    subset: pl.DataFrame,
    *,
    split_after: int,
    team_count: int,
    deductions: dict[str, int],
) -> list[dict[str, Any]]:
    """Rank a completed split season inside its top-six/bottom-six groups.

    The split membership is decided after the configured number of matches.
    The final positions are then ranked within each group using the full-season
    record, so a bottom-six team cannot be placed above a top-six team.
    """
    rows = team_match_rows(subset).sort(["team_id", "date"])
    rows = rows.with_columns(pl.col("date").cum_count().over("team_id").alias("team_match_no"))
    regular = rows.filter(pl.col("team_match_no") <= split_after)
    regular_ranked = _rank(regular, deductions)
    top_ids = {row["team_id"] for row in regular_ranked[: team_count // 2]}
    bottom_ids = {row["team_id"] for row in regular_ranked[team_count // 2 :]}
    full_ranked = _rank(rows, deductions)
    ordered = [row for row in full_ranked if row["team_id"] in top_ids]
    ordered.extend(row for row in full_ranked if row["team_id"] in bottom_ids)
    return ordered


def compute_table(
    matches: pl.DataFrame,
    *,
    competition_id: str,
    season: str,
    competition_name: str | None = None,
    deductions: dict[str, int] | None = None,
) -> pl.DataFrame:
    subset = matches.filter(
        (pl.col("competition_id") == competition_id) & (pl.col("season") == season)
    )
    if subset.height == 0:
        return pl.DataFrame({column: [] for column in TABLE_COLUMNS})
    if deductions is None:
        deductions = {}
        for entry in disciplinary_config().get("deductions", []):
            if entry["season"] == season and entry["competition_id"] == competition_id:
                deductions[entry["team_id"]] = deductions.get(entry["team_id"], 0) + int(
                    entry["points"]
                )
    competition = next(
        (
            item
            for item in competitions_config().get("competitions", [])
            if item.get("id") == competition_id
        ),
        None,
    )
    split_after = int((competition or {}).get("split_after_matches") or 0)
    team_count = int((competition or {}).get("teams") or 0)
    rows = team_match_rows(subset)
    max_played: Any = (
        rows.group_by("team_id").agg(pl.len().alias("played"))["played"].max()
        if rows.height
        else None
    )
    played_per_team = int(max_played) if max_played is not None else 0
    expected_matches = int((competition or {}).get("matches_per_season") or 0)
    full_season = bool(
        split_after
        and team_count
        and expected_matches
        and played_per_team
        and played_per_team * team_count >= expected_matches * 2
    )
    ordered = (
        _split_order(
            subset,
            split_after=split_after,
            team_count=team_count,
            deductions=deductions,
        )
        if full_season
        else _rank(rows, deductions)
    )
    updated_at = utc_now_iso()
    frame = pl.DataFrame(
        [
            {
                "position": index + 1,
                "team_id": row["team_id"],
                "team_name": row["team_name"],
                "played": row["played"],
                "won": row["won"],
                "drawn": row["drawn"],
                "lost": row["lost"],
                "gf": row["gf"],
                "ga": row["ga"],
                "gd": row["gd"],
                "raw_points": row["raw_points"],
                "deduction": row["deduction"],
                "points": row["points"],
                "form": row["form"],
                "season": season,
                "competition_id": competition_id,
                "competition_name": competition_name
                or competition_id.split(":", 1)[-1].replace("-", " ").title(),
                "updated_at": updated_at,
            }
            for index, row in enumerate(ordered)
        ],
        schema_overrides={
            "position": pl.Int64,
            "team_id": pl.String,
            "team_name": pl.String,
            "played": pl.Int64,
            "won": pl.Int64,
            "drawn": pl.Int64,
            "lost": pl.Int64,
            "gf": pl.Int64,
            "ga": pl.Int64,
            "gd": pl.Int64,
            "raw_points": pl.Int64,
            "deduction": pl.Int64,
            "points": pl.Int64,
            "form": pl.String,
            "season": pl.String,
            "competition_id": pl.String,
            "competition_name": pl.String,
            "updated_at": pl.String,
        },
    )
    return frame.select(TABLE_COLUMNS)


def league_row(
    matches: pl.DataFrame,
    *,
    competition_id: str,
    season: str,
    team_id: str,
    competition_name: str | None = None,
) -> dict[str, Any] | None:
    """Return one team's row from the same table logic used by the site."""
    table = compute_table(
        matches,
        competition_id=competition_id,
        competition_name=competition_name,
        season=season,
    )
    rows = table.filter(pl.col("team_id") == team_id)
    return rows.to_dicts()[0] if rows.height else None


def build_tables(
    matches: pl.DataFrame,
    *,
    season: str,
    config: dict[str, Any] | None = None,
) -> dict[str, pl.DataFrame]:
    config = config or competitions_config()
    tables: dict[str, pl.DataFrame] = {}
    for competition in config["competitions"]:
        competition_id = competition["id"]
        table = compute_table(
            matches,
            competition_id=competition_id,
            competition_name=competition["name"],
            season=season,
        )
        if table.height:
            tables[competition_id] = table
    return tables


def combined_tables(tables: dict[str, pl.DataFrame]) -> pl.DataFrame:
    if not tables:
        return pl.DataFrame({column: [] for column in TABLE_COLUMNS})
    return pl.concat(list(tables.values()), how="vertical_relaxed").sort(
        ["competition_id", "position"]
    )
