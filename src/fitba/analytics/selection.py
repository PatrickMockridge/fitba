"""Team-selection metrics from historical lineups.

The input is a normalized appearance table, one row per player per fixture.
Ages come from the season roster (or a birth date where available). Missing
lineups or ages produce partial/unavailable states; they are never filled with
a squad average.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from statistics import mean
from typing import Any


def _date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _age_at(birth: Any, match_date: date | None) -> int | None:
    born = _date(birth)
    if born is None or match_date is None:
        return None
    return (
        match_date.year - born.year - ((match_date.month, match_date.day) < (born.month, born.day))
    )


def _age_band(age: int | None) -> str:
    if age is None:
        return "unknown"
    if age < 21:
        return "u21"
    if age < 25:
        return "21-24"
    if age < 30:
        return "25-29"
    return "30+"


def selection_profile(
    appearances: list[dict[str, Any]],
    *,
    season: str,
    fixtures_total: int | None = None,
    rosters: dict[int, dict[str, Any]] | None = None,
    previous_player_ids: set[int] | None = None,
    min_lineup_coverage: float = 0.6,
    min_age_coverage: float = 0.5,
) -> dict[str, Any]:
    """Aggregate formation, age, minutes and debut metrics for a season."""
    rows = [row for row in appearances if str(row.get("season")) == str(season)]
    if not rows:
        return {
            "status": "unavailable",
            "reason": "no_lineups",
            "note": "No lineup rows are available for this season.",
        }
    rosters = rosters or {}
    fixtures: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        fixtures[row.get("fixture_id")].append(row)
    fixtures_with_lineups = len(fixtures)

    formation_counts: Counter[str] = Counter()
    starter_ages: list[float] = []
    age_minutes: Counter[str] = Counter()
    total_known_minutes = 0
    players: dict[int, dict[str, Any]] = {}
    debutants: list[dict[str, Any]] = []

    for _fixture_id, fixture_rows in fixtures.items():
        formation = next(
            (row.get("formation_shape") for row in fixture_rows if row.get("formation_shape")),
            None,
        )
        formation_counts[str(formation or "unknown")] += 1
        match_date = _date(next((row.get("date") for row in fixture_rows), None))
        fixture_ages: list[int] = []
        for row in fixture_rows:
            player_id = row.get("player_id")
            minutes = int(row.get("minutes") or 0)
            started = bool(row.get("started"))
            roster = rosters.get(int(player_id)) if player_id is not None else None
            age = None
            if roster:
                birth = roster.get("birth_date") or roster.get("birth")
                age = _age_at(birth, match_date)
                if age is None and roster.get("age") is not None:
                    age = int(roster["age"])
            if started and age is not None:
                fixture_ages.append(age)
            if age is not None and minutes > 0:
                age_minutes[_age_band(age)] += minutes
                total_known_minutes += minutes
            if player_id is not None:
                player_name = row.get("player_name") or (roster or {}).get("player_name")
                item = players.setdefault(
                    int(player_id),
                    {
                        "player_id": int(player_id),
                        "player_name": player_name,
                        "starts": 0,
                        "minutes": 0,
                        "role_family": row.get("role_family"),
                        "age": age,
                    },
                )
                item["starts"] += 1 if started else 0
                item["minutes"] += minutes
                if item.get("age") is None and age is not None:
                    item["age"] = age
        if fixture_ages:
            starter_ages.append(mean(fixture_ages))
        if previous_player_ids is not None:
            for row in fixture_rows:
                player_id = row.get("player_id")
                if player_id is None:
                    continue
                if int(player_id) not in previous_player_ids and not any(
                    int(item["player_id"]) == int(player_id) for item in debutants
                ):
                    debutants.append(
                        {
                            "player_id": int(player_id),
                            "player_name": row.get("player_name")
                            or (rosters.get(int(player_id)) or {}).get("player_name"),
                            "date": row.get("date"),
                        }
                    )

    known_age_players = sum(1 for item in players.values() if item.get("age") is not None)
    lineup_coverage = round(fixtures_with_lineups / fixtures_total, 3) if fixtures_total else None
    age_coverage = round(known_age_players / len(players), 3) if players else None
    status = "available"
    if lineup_coverage is not None and lineup_coverage < min_lineup_coverage:
        status = "partial"
    if age_coverage is not None and age_coverage < min_age_coverage:
        status = "partial"
    return {
        "status": status,
        "fixtures_total": fixtures_total,
        "fixtures_with_lineups": fixtures_with_lineups,
        "lineup_coverage": lineup_coverage,
        "formation_mix": [
            {
                "formation": formation,
                "fixtures": count,
                "share": round(count / fixtures_with_lineups, 3),
            }
            for formation, count in formation_counts.most_common()
        ],
        "players_used": len(players),
        "average_starter_age": round(mean(starter_ages), 2) if starter_ages else None,
        "age_coverage": age_coverage,
        "u21_minutes_share": (
            round(age_minutes["u21"] / total_known_minutes, 3) if total_known_minutes else None
        ),
        "minutes_by_age_band": {
            key: {
                "minutes": age_minutes.get(key, 0),
                "share": round(age_minutes.get(key, 0) / total_known_minutes, 3)
                if total_known_minutes
                else None,
            }
            for key in ("u21", "21-24", "25-29", "30+")
        },
        "unknown_age_minutes": age_minutes.get("unknown", 0),
        "top_by_starts": sorted(
            players.values(), key=lambda item: (-item["starts"], -item["minutes"])
        )[:11],
        "debutants": sorted(debutants, key=lambda item: str(item.get("date") or "")),
        "debut_basis": "covered_history" if previous_player_ids is not None else "not_computed",
        "note": (
            "Formation is the kick-off shape. Ages use the season roster or a known "
            "birth date; missing ages are excluded, not filled. Top-by-starts is "
            "not a claim that those players started together."
        ),
    }


__all__ = ["selection_profile"]
