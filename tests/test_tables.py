import polars as pl

from fitba.analytics.tables import compute_table


def _matches() -> pl.DataFrame:
    rows = [
        ("m1", "2025-08-02", "A", "B", 2, 0),
        ("m2", "2025-08-02", "C", "D", 1, 0),
        ("m3", "2025-08-09", "A", "C", 1, 1),
        ("m4", "2025-08-09", "B", "D", 2, 1),
        ("m5", "2025-08-16", "A", "D", 3, 0),
        ("m6", "2025-08-16", "B", "C", 0, 0),
    ]
    return pl.DataFrame(
        {
            "match_id": [row[0] for row in rows],
            "competition_id": ["sco:test"] * len(rows),
            "season": ["2025-26"] * len(rows),
            "phase": ["regular"] * len(rows),
            "date": [row[1] for row in rows],
            "home_team_id": [f"sco:{row[2].lower()}" for row in rows],
            "home_team_name": [row[2] for row in rows],
            "away_team_id": [f"sco:{row[3].lower()}" for row in rows],
            "away_team_name": [row[3] for row in rows],
            "home_goals": [row[4] for row in rows],
            "away_goals": [row[5] for row in rows],
        }
    ).with_columns(pl.col("date").str.to_date())


def test_computed_table_order_and_totals():
    table = compute_table(
        _matches(), competition_id="sco:test", competition_name="Test League", season="2025-26"
    )
    assert table["team_name"].to_list() == ["A", "C", "B", "D"]
    assert table["position"].to_list() == [1, 2, 3, 4]
    a = table.row(0, named=True)
    assert (a["played"], a["won"], a["drawn"], a["lost"]) == (3, 2, 1, 0)
    assert (a["gf"], a["ga"], a["gd"], a["points"]) == (6, 1, 5, 7)
    assert a["form"] == "WDW"
    assert int(table["gf"].sum()) == int(table["ga"].sum())


def test_points_deduction_changes_order_and_is_exposed():
    table = compute_table(
        _matches(),
        competition_id="sco:test",
        competition_name="Test League",
        season="2025-26",
        deductions={"sco:a": 5},
    )
    assert table["team_name"].to_list() == ["C", "B", "A", "D"]
    a = table.filter(pl.col("team_name") == "A").row(0, named=True)
    assert (a["raw_points"], a["deduction"], a["points"]) == (7, 5, 2)


def test_excludes_playoffs_and_unplayed():
    matches = _matches().with_columns(
        pl.when(pl.col("match_id") == "m1")
        .then(pl.lit("playoff"))
        .otherwise(pl.col("phase"))
        .alias("phase"),
        pl.when(pl.col("match_id") == "m2")
        .then(pl.lit(None, dtype=pl.Int64))
        .otherwise(pl.col("home_goals"))
        .alias("home_goals"),
    )
    table = compute_table(
        matches, competition_id="sco:test", competition_name="Test League", season="2025-26"
    )
    # m1 (playoff) and m2 (unplayed) are excluded.
    assert int(table["played"].sum()) == 8
    assert table.filter(pl.col("team_name") == "D")["played"][0] == 2
