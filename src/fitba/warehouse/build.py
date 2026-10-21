"""Build the DuckDB warehouse and parquet marts from normalized matches."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import polars as pl

from fitba.analytics.tables import build_tables, combined_tables
from fitba.ingest.runner import load_matches
from fitba.settings import (
    MARTS_DIR,
    WAREHOUSE_DIR,
    WAREHOUSE_PATH,
    ensure_dirs,
)
from fitba.settings import (
    competitions as competitions_config,
)
from fitba.util.dates import utc_now_iso


@dataclass(slots=True)
class WarehouseReport:
    seasons: list[str]
    matches: int
    tables: int
    path: str
    marts: list[str]
    generated_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "seasons": self.seasons,
            "matches": self.matches,
            "tables": self.tables,
            "path": self.path,
            "marts": self.marts,
            "generated_at": self.generated_at,
        }


def _team_stats(matches: pl.DataFrame) -> pl.DataFrame:
    home = matches.select(
        pl.col("match_id"),
        pl.col("competition_id"),
        pl.col("season"),
        pl.col("home_team_id").alias("team_id"),
        pl.col("away_team_id").alias("opponent_id"),
        pl.lit("H").alias("venue"),
        pl.col("home_shots").alias("shots"),
        pl.col("home_shots_on_target").alias("shots_on_target"),
        pl.col("home_fouls").alias("fouls"),
        pl.col("home_corners").alias("corners"),
        pl.col("home_yellow").alias("yellow_cards"),
        pl.col("home_red").alias("red_cards"),
    )
    away = matches.select(
        pl.col("match_id"),
        pl.col("competition_id"),
        pl.col("season"),
        pl.col("away_team_id").alias("team_id"),
        pl.col("home_team_id").alias("opponent_id"),
        pl.lit("A").alias("venue"),
        pl.col("away_shots").alias("shots"),
        pl.col("away_shots_on_target").alias("shots_on_target"),
        pl.col("away_fouls").alias("fouls"),
        pl.col("away_corners").alias("corners"),
        pl.col("away_yellow").alias("yellow_cards"),
        pl.col("away_red").alias("red_cards"),
    )
    return pl.concat([home, away], how="vertical_relaxed").sort(["season", "match_id", "team_id"])


def build_warehouse(*, season: str | None = None) -> WarehouseReport:
    ensure_dirs()
    matches = load_matches([season] if season else None)
    seasons = sorted(matches["season"].unique().to_list())

    tables = []
    for current in seasons:
        season_tables = build_tables(matches, season=current, config=competitions_config())
        tables.extend(season_tables.values())
    table_frame = pl.concat(tables, how="vertical_relaxed") if tables else combined_tables({})

    team_stats = _team_stats(matches)

    MARTS_DIR.mkdir(parents=True, exist_ok=True)
    matches_path = MARTS_DIR / "matches.parquet"
    table_path = MARTS_DIR / "league_table.parquet"
    stats_path = MARTS_DIR / "team_match_stats.parquet"
    matches.write_parquet(matches_path)
    table_frame.write_parquet(table_path)
    team_stats.write_parquet(stats_path)

    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(WAREHOUSE_PATH))
    try:
        con.register("matches_df", matches)
        con.register("table_df", table_frame)
        con.register("stats_df", team_stats)
        con.execute("CREATE OR REPLACE TABLE fact_match_result AS SELECT * FROM matches_df")
        con.execute("CREATE OR REPLACE TABLE fact_team_match_stats AS SELECT * FROM stats_df")
        con.execute("CREATE OR REPLACE TABLE mart_league_table AS SELECT * FROM table_df")
        con.execute(
            "CREATE OR REPLACE VIEW dim_competition AS "
            "SELECT DISTINCT competition_id, competition_name FROM matches_df"
        )
        con.execute(
            "CREATE OR REPLACE VIEW dim_team AS "
            "SELECT team_id, team_name FROM ("
            "SELECT home_team_id AS team_id, home_team_name AS team_name FROM matches_df "
            "UNION "
            "SELECT away_team_id, away_team_name FROM matches_df)"
        )
        con.execute("CREATE OR REPLACE VIEW dim_season AS SELECT DISTINCT season FROM matches_df")
    finally:
        con.close()

    return WarehouseReport(
        seasons=seasons,
        matches=matches.height,
        tables=table_frame.height,
        path=str(WAREHOUSE_PATH),
        marts=[str(path) for path in (matches_path, table_path, stats_path)],
        generated_at=utc_now_iso(),
    )
