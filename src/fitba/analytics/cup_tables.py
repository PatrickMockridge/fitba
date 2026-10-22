"""League Cup group tables.

The licensed feed does not publish group standings for the League Cup, so the
tables are computed from the group fixtures using the official rules:

- 3 points for a win;
- 1 point for a draw plus 1 bonus point to the penalty shoot-out winner;
- tie-breaks: goal difference, goals scored, away goals, matches won, away
  matches won, head-to-head, then name.

The group letters are assigned by the ingestion layer from the fixture graph;
the licensed feed does not expose the official draw letters.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def _empty_row(team_id: str, team_name: str, group: str) -> dict[str, Any]:
    return {
        "group": group,
        "team_id": team_id,
        "team_name": team_name,
        "played": 0,
        "won": 0,
        "shootout_won": 0,
        "shootout_lost": 0,
        "drawn": 0,
        "lost": 0,
        "gf": 0,
        "ga": 0,
        "gd": 0,
        "away_gf": 0,
        "away_wins": 0,
        "points": 0,
        "position": 0,
    }


def _add_match(
    rows: dict[str, dict[str, Any]],
    home_id: str,
    away_id: str,
    home_goals: int,
    away_goals: int,
    home_pens: int | None,
    away_pens: int | None,
) -> None:
    home = rows.get(home_id)
    away = rows.get(away_id)
    if home is None or away is None:
        return
    home["played"] += 1
    away["played"] += 1
    home["gf"] += home_goals
    home["ga"] += away_goals
    away["gf"] += away_goals
    away["ga"] += home_goals
    away["away_gf"] += away_goals

    if home_goals > away_goals:
        home["won"] += 1
        home["points"] += 3
        away["lost"] += 1
    elif away_goals > home_goals:
        away["won"] += 1
        away["away_wins"] += 1
        away["points"] += 3
        home["lost"] += 1
    elif home_pens is not None and away_pens is not None:
        home["drawn"] += 1
        away["drawn"] += 1
        home["points"] += 1
        away["points"] += 1
        if home_pens > away_pens:
            home["shootout_won"] += 1
            away["shootout_lost"] += 1
            home["points"] += 1
        else:
            away["shootout_won"] += 1
            home["shootout_lost"] += 1
            away["points"] += 1
    else:
        home["drawn"] += 1
        away["drawn"] += 1
        home["points"] += 1
        away["points"] += 1


def _h2h_key(team_id: str, tied_ids: set[str], fixtures: list[dict[str, Any]]) -> tuple:
    """Mini-table points/GD/GF among the tied teams, used only as a last resort."""
    points = gd = gf = 0
    for fixture in fixtures:
        if fixture.get("status") != "played":
            continue
        home, away = fixture["home_team_id"], fixture["away_team_id"]
        if home not in tied_ids or away not in tied_ids:
            continue
        hg, ag = fixture["home_goals"], fixture["away_goals"]
        hp, ap = fixture.get("home_penalties"), fixture.get("away_penalties")
        if hg != ag:
            points += 3
        else:
            points += 1
            if (
                hp is not None
                and ap is not None
                and ((home == team_id and hp > ap) or (away == team_id and ap > hp))
            ):
                points += 1
        if home == team_id:
            gf += hg
            gd += hg - ag
        elif away == team_id:
            gf += ag
            gd += ag - hg
    return (points, gd, gf)


def _sort_group(rows: list[dict[str, Any]], fixtures: list[dict[str, Any]]) -> None:
    def base_key(row: dict[str, Any]) -> tuple:
        return (
            -row["points"],
            -row["gd"],
            -row["gf"],
            -row["away_gf"],
            -row["won"],
            -row["away_wins"],
            row["team_name"],
        )

    rows.sort(key=base_key)
    # Resolve exact ties with the head-to-head mini-table, then name.
    start = 0
    while start < len(rows):
        end = start + 1
        while end < len(rows) and base_key(rows[end])[:6] == base_key(rows[start])[:6]:
            end += 1
        if end - start > 1:
            tied = rows[start:end]
            tied_ids = {row["team_id"] for row in tied}
            tied.sort(
                key=lambda row: (
                    tuple(-value for value in _h2h_key(row["team_id"], tied_ids, fixtures)),
                    row["team_name"],
                )
            )
            rows[start:end] = tied
        start = end


def build_group_tables(
    fixtures: list[dict[str, Any]],
    *,
    group_map: dict[str, str],
) -> dict[str, Any]:
    """Return group tables, winners and the best three runners-up.

    ``group_map`` maps team_id -> group label. Fixtures must already be
    normalized with home/away team ids, goals, penalties and status.
    """
    rows_by_group: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for fixture in fixtures:
        if fixture.get("status") != "played":
            continue
        group = group_map.get(fixture["home_team_id"]) or group_map.get(fixture["away_team_id"])
        if not group:
            continue
        if fixture["home_team_id"] not in rows_by_group[group]:
            rows_by_group[group][fixture["home_team_id"]] = _empty_row(
                fixture["home_team_id"], fixture["home_team_name"], group
            )
        if fixture["away_team_id"] not in rows_by_group[group]:
            rows_by_group[group][fixture["away_team_id"]] = _empty_row(
                fixture["away_team_id"], fixture["away_team_name"], group
            )
        _add_match(
            rows_by_group[group],
            fixture["home_team_id"],
            fixture["away_team_id"],
            int(fixture["home_goals"]),
            int(fixture["away_goals"]),
            fixture.get("home_penalties"),
            fixture.get("away_penalties"),
        )

    groups: list[dict[str, Any]] = []
    winners: list[dict[str, Any]] = []
    runners_up: list[dict[str, Any]] = []
    for group in sorted(rows_by_group):
        rows = list(rows_by_group[group].values())
        for row in rows:
            row["gd"] = row["gf"] - row["ga"]
        _sort_group(rows, fixtures)
        for index, row in enumerate(rows, 1):
            row["position"] = index
        groups.append({"id": group, "rows": rows})
        if rows:
            winners.append({**rows[0], "group": group})
        if len(rows) > 1:
            runners_up.append({**rows[1], "group": group})

    def runner_key(row: dict[str, Any]) -> tuple:
        return (
            -row["points"],
            -row["gd"],
            -row["gf"],
            -row["away_gf"],
            -row["won"],
            -row["away_wins"],
            row["team_name"],
        )

    best_runners_up = sorted(runners_up, key=runner_key)[:3]
    return {
        "groups": groups,
        "group_winners": winners,
        "best_runners_up": best_runners_up,
    }


def infer_groups(fixtures: list[dict[str, Any]]) -> dict[str, str]:
    """Infer groups from the group-fixture graph (each group is a 5-team clique)."""
    adjacency: dict[str, set[str]] = defaultdict(set)
    names: dict[str, str] = {}
    for fixture in fixtures:
        home, away = fixture["home_team_id"], fixture["away_team_id"]
        adjacency[home].add(away)
        adjacency[away].add(home)
        names[home] = fixture["home_team_name"]
        names[away] = fixture["away_team_name"]

    components: list[list[str]] = []
    seen: set[str] = set()
    for team in adjacency:
        if team in seen:
            continue
        stack = [team]
        component: list[str] = []
        seen.add(team)
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbour in adjacency[current]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
        components.append(component)

    components.sort(key=lambda component: min(names.get(team, team) for team in component))
    labels = [chr(ord("A") + index) for index in range(len(components))]
    return {
        team: f"Group {label}"
        for label, component in zip(labels, components, strict=False)
        for team in component
    }
