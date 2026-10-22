"""Historical record analytics.

Pure functions over the normalized match frame and the curated staff register.
No network, no file I/O. The publisher joins these results with the club history
and the transfer payload; the web never recomputes them.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from statistics import mean
from typing import Any

import polars as pl

from fitba.analytics.records import record_totals
from fitba.analytics.tables import league_row, playable_matches
from fitba.util.dates import seasons_between

LEAGUE_COMPETITION_IDS = {
    "sco:premiership",
    "sco:championship",
    "sco:league-one",
    "sco:league-two",
}

STAT_PAIRS = {
    "shots": ("home_shots", "away_shots"),
    "shots_on_target": ("home_shots_on_target", "away_shots_on_target"),
    "fouls": ("home_fouls", "away_fouls"),
    "corners": ("home_corners", "away_corners"),
    "yellow": ("home_yellow", "away_yellow"),
    "red": ("home_red", "away_red"),
}


def era_seasons(first: str, last: str) -> list[str]:
    """Inclusive season list for the era."""
    return seasons_between(first, last)


def _date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _boundary(value: Any, precision: str, *, end: bool) -> date | None:
    """Convert a curated boundary to a date, keeping month/year precision."""
    parsed = _date(value)
    if parsed is not None:
        return parsed
    text = str(value or "")
    if precision == "month" and len(text) >= 7:
        year, month = int(text[:4]), int(text[5:7])
        day = monthrange(year, month)[1] if end else 1
        return date(year, month, day)
    if precision == "year" and len(text) >= 4:
        year = int(text[:4])
        return date(year, 12, 31) if end else date(year, 1, 1)
    if precision == "season" and len(text) >= 7:
        year = int(text[:4])
        return date(year + 1, 6, 30) if end else date(year, 7, 1)
    return parsed


def flatten_stints(people: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per stint with the person's identity attached."""
    rows: list[dict[str, Any]] = []
    for person in people:
        for stint in person.get("stints") or []:
            rows.append(
                {
                    **stint,
                    "person_id": person.get("person_id"),
                    "name": person.get("name"),
                }
            )
    return rows


def club_match_rows(matches: pl.DataFrame, club_id: str) -> pl.DataFrame:
    """One Aberdeen-perspective row per playable match, with stat columns."""
    frame = playable_matches(matches)
    rows: list[dict[str, Any]] = []
    for row in frame.to_dicts():
        is_home = row.get("home_team_id") == club_id
        is_away = row.get("away_team_id") == club_id
        if not (is_home or is_away):
            continue
        gf = row.get("home_goals") if is_home else row.get("away_goals")
        ga = row.get("away_goals") if is_home else row.get("home_goals")
        if gf is None or ga is None:
            continue
        item: dict[str, Any] = {
            "match_id": row.get("match_id"),
            "date": str(row.get("date") or ""),
            "season": row.get("season"),
            "competition_id": row.get("competition_id"),
            "competition_name": row.get("competition_name"),
            "opponent_id": row.get("away_team_id") if is_home else row.get("home_team_id"),
            "opponent_name": row.get("away_team_name") if is_home else row.get("home_team_name"),
            "venue": "H" if is_home else "A",
            "gf": int(gf),
            "ga": int(ga),
            "result": "W" if gf > ga else "D" if gf == ga else "L",
            "points": 3 if gf > ga else 1 if gf == ga else 0,
        }
        for key, (home_col, away_col) in STAT_PAIRS.items():
            value = row.get(home_col) if is_home else row.get(away_col)
            against = row.get(away_col) if is_home else row.get(home_col)
            item[f"{key}_for"] = int(value) if value is not None else None
            item[f"{key}_against"] = int(against) if against is not None else None
        rows.append(item)
    if not rows:
        return pl.DataFrame()
    return pl.DataFrame(rows).sort("date")


def _record(rows: list[dict[str, Any]]) -> dict[str, Any]:
    totals = record_totals(rows)
    return {
        "played": totals["played"],
        "won": totals["won"],
        "drawn": totals["drawn"],
        "lost": totals["lost"],
        "gf": totals["gf"],
        "ga": totals["ga"],
        "points": totals["points"],
        "ppg": totals["ppg"],
        "first_match": rows[0]["date"] if rows else None,
        "last_match": rows[-1]["date"] if rows else None,
    }


def manager_stint_records(
    match_rows: pl.DataFrame,
    stints: list[dict[str, Any]],
    *,
    league_ids: set[str] | None = None,
    competition_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Career league records for manager stints.

    The default scope is the four SPFL league competitions, so the record still
    works if Aberdeen are in a lower tier. Matches in a gap between stints are
    not assigned to anyone.
    """
    if not match_rows.height:
        return []
    allowed = competition_ids or league_ids or LEAGUE_COMPETITION_IDS
    rows = [row for row in match_rows.to_dicts() if row.get("competition_id") in allowed]
    manager_stints = [stint for stint in stints if stint.get("role_group") == "manager"]
    manager_stints.sort(
        key=lambda stint: (
            str(stint.get("start") or ""),
            str(stint.get("stint_id") or ""),
        )
    )
    records: list[dict[str, Any]] = []
    claimed: set[str] = set()
    for stint in manager_stints:
        start = _boundary(stint.get("start"), str(stint.get("start_precision") or "day"), end=False)
        end = _boundary(stint.get("end"), str(stint.get("end_precision") or "day"), end=True)
        if start is None:
            continue
        assigned: list[dict[str, Any]] = []
        boundary = 0
        for row in rows:
            match_id = str(row.get("match_id"))
            if match_id in claimed:
                continue
            match_date = _date(row.get("date"))
            if match_date is None or match_date < start:
                continue
            if end is not None and match_date > end:
                continue
            assigned.append(row)
            claimed.add(match_id)
            if stint.get("start_precision") != "day" and match_date == start:
                boundary += 1
            if stint.get("end_precision") != "day" and match_date == end:
                boundary += 1
        record = _record(assigned)
        record.update(
            {
                "stint_id": stint.get("stint_id"),
                "person_id": stint.get("person_id"),
                "name": stint.get("name"),
                "interim": bool(stint.get("interim")),
                "start": stint.get("start"),
                "end": stint.get("end"),
                "start_precision": stint.get("start_precision"),
                "end_precision": stint.get("end_precision"),
                "boundary_matches": boundary,
                "scope": "league",
            }
        )
        records.append(record)
    records.sort(key=lambda item: (str(item.get("start") or ""), str(item.get("stint_id") or "")))
    return records


def manager_splits_by_season(
    match_rows: pl.DataFrame,
    stints: list[dict[str, Any]],
    seasons: list[str],
) -> dict[str, list[dict[str, Any]]]:
    """Season segments per manager stint, plus unattributed matches."""
    if not match_rows.height:
        return {season: [] for season in seasons}
    rows = [
        row for row in match_rows.to_dicts() if row.get("competition_id") in LEAGUE_COMPETITION_IDS
    ]
    output: dict[str, list[dict[str, Any]]] = {}
    for season in seasons:
        season_rows = [row for row in rows if row.get("season") == season]
        segments: list[dict[str, Any]] = []
        assigned_ids: set[str] = set()
        for stint in stints:
            if stint.get("role_group") != "manager":
                continue
            start = _boundary(
                stint.get("start"),
                str(stint.get("start_precision") or "day"),
                end=False,
            )
            end = _boundary(
                stint.get("end"),
                str(stint.get("end_precision") or "day"),
                end=True,
            )
            if start is None:
                continue
            segment = []
            for row in season_rows:
                match_id = str(row.get("match_id"))
                if match_id in assigned_ids:
                    continue
                match_date = _date(row.get("date"))
                if match_date is None or match_date < start:
                    continue
                if end is not None and match_date > end:
                    continue
                segment.append(row)
                assigned_ids.add(match_id)
            if not segment:
                continue
            item = _record(segment)
            item.update(
                {
                    "stint_id": stint.get("stint_id"),
                    "person_id": stint.get("person_id"),
                    "name": stint.get("name"),
                    "interim": bool(stint.get("interim")),
                    # The season segment is bounded by its first and last match,
                    # not by the full stint dates. A manager who left in January
                    # should not show a June end date on a completed-season page.
                    "start": item.get("first_match") or stint.get("start"),
                    "end": item.get("last_match") or stint.get("end"),
                    "stint_start": stint.get("start"),
                    "stint_end": stint.get("end"),
                }
            )
            segments.append(item)
        segments.sort(key=lambda item: str(item.get("first_match") or ""))
        unattributed = [row for row in season_rows if str(row.get("match_id")) not in assigned_ids]
        if unattributed:
            item = _record(unattributed)
            item.update(
                {
                    "stint_id": None,
                    "person_id": None,
                    "name": "Unattributed",
                    "interim": False,
                }
            )
            segments.append(item)
        output[season] = segments
    return output


def season_records(
    matches: pl.DataFrame,
    competitions: list[dict[str, Any]],
    *,
    club_id: str,
    seasons: list[str],
) -> dict[str, dict[str, Any]]:
    """League row per season, scanning every tier for the club."""
    output: dict[str, dict[str, Any]] = {}
    for season in seasons:
        found = None
        for competition in sorted(competitions, key=lambda item: int(item.get("tier") or 99)):
            row = league_row(
                matches,
                competition_id=competition["id"],
                competition_name=competition.get("name"),
                season=season,
                team_id=club_id,
            )
            if row:
                found = {
                    "season": season,
                    "competition_id": competition["id"],
                    "competition_name": competition.get("name"),
                    "tier": competition.get("tier"),
                    **row,
                }
                break
        if found:
            output[season] = found
    return output


def baseline_profile(
    matches: pl.DataFrame,
    competitions: list[dict[str, Any]],
    *,
    club_id: str,
    first: str,
    last: str,
) -> dict[str, Any]:
    """Compact league-only context before the era."""
    seasons = era_seasons(first, last)
    records = season_records(matches, competitions, club_id=club_id, seasons=seasons)
    rows = [records[season] for season in seasons if season in records]
    if not rows:
        return {"seasons": [], "count": 0, "note": "No pre-era league rows."}
    points = [int(row["points"]) for row in rows]
    positions = [int(row["position"]) for row in rows]
    return {
        "from": first,
        "to": last,
        "count": len(rows),
        "average_points": round(mean(points), 1),
        "best_position": min(positions),
        "worst_position": max(positions),
        "average_position": round(mean(positions), 1),
        "seasons": rows,
        "note": "League-only context. No cup or Europe detail.",
    }


def era_scorecard(
    *,
    seasons: list[str],
    season_records_by_season: dict[str, dict[str, Any]],
    manager_records: list[dict[str, Any]],
    honours: list[dict[str, Any]],
    recruitment: dict[str, Any] | None = None,
    selection: dict[str, Any] | None = None,
    style: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aggregate derived values for the era index. No composite score."""
    rows = [
        season_records_by_season[season] for season in seasons if season in season_records_by_season
    ]
    positions = [int(row["position"]) for row in rows]
    points = [int(row["points"]) for row in rows]
    managers = {
        record["person_id"]
        for record in manager_records
        if record.get("person_id") and record.get("played")
    }
    honour_counts: dict[str, int] = {}
    for honour in honours:
        key = str(honour.get("competition") or "Unknown")
        honour_counts[key] = honour_counts.get(key, 0) + 1
    return {
        "seasons": len(rows),
        "best_position": min(positions) if positions else None,
        "worst_position": max(positions) if positions else None,
        "average_position": round(mean(positions), 1) if positions else None,
        "average_points": round(mean(points), 1) if points else None,
        "manager_count": len(managers),
        "honours_total": len(honours),
        "honours_by_competition": honour_counts,
        "recruitment": recruitment,
        "selection": selection,
        "style": style,
    }


__all__ = [
    "LEAGUE_COMPETITION_IDS",
    "baseline_profile",
    "club_match_rows",
    "era_scorecard",
    "era_seasons",
    "flatten_stints",
    "manager_splits_by_season",
    "manager_stint_records",
    "season_records",
]
