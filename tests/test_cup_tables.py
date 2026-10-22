from fitba.analytics.cup_tables import build_group_tables, infer_groups


def _fixtures():
    def row(home, away, hg, ag, hp=None, ap=None, status="played"):
        return {
            "home_team_id": home,
            "home_team_name": home.upper(),
            "away_team_id": away,
            "away_team_name": away.upper(),
            "home_goals": hg,
            "away_goals": ag,
            "home_penalties": hp,
            "away_penalties": ap,
            "status": status,
        }

    return [
        row("t1", "t2", 2, 0),
        row("t1", "t3", 1, 1, 4, 3),
        row("t1", "t4", 3, 0),
        row("t1", "t5", 1, 1, 3, 5),
        row("t2", "t3", 2, 1),
        row("t2", "t4", 1, 0),
        row("t2", "t5", 0, 2),
        row("t3", "t4", 2, 0),
        row("t3", "t5", 1, 1, 5, 4),
        row("t4", "t5", 2, 2, 4, 3),
    ]


def test_group_table_bonus_points_and_columns():
    fixtures = _fixtures()
    group_map = {f"t{index}": "Group A" for index in range(1, 6)}
    result = build_group_tables(fixtures, group_map=group_map)
    assert len(result["groups"]) == 1
    rows = {row["team_id"]: row for row in result["groups"][0]["rows"]}

    assert rows["t1"]["points"] == 9
    assert (rows["t1"]["won"], rows["t1"]["shootout_won"], rows["t1"]["shootout_lost"]) == (2, 1, 1)
    assert rows["t5"]["points"] == 7
    assert (rows["t5"]["won"], rows["t5"]["shootout_won"], rows["t5"]["shootout_lost"]) == (1, 1, 2)
    assert result["groups"][0]["rows"][0]["position"] == 1
    assert sum(row["points"] for row in rows.values()) == 30


def test_group_order_and_best_runner_up():
    fixtures = _fixtures()
    group_map = {f"t{index}": "Group A" for index in range(1, 6)}
    result = build_group_tables(fixtures, group_map=group_map)
    names = [row["team_id"] for row in result["groups"][0]["rows"]]
    assert names == ["t1", "t5", "t3", "t2", "t4"]
    assert result["group_winners"][0]["team_id"] == "t1"
    assert result["best_runners_up"][0]["team_id"] == "t5"


def test_infer_groups_from_fixture_graph():
    group_map = infer_groups(_fixtures())
    assert len(set(group_map.values())) == 1
    assert set(group_map) == {"t1", "t2", "t3", "t4", "t5"}
