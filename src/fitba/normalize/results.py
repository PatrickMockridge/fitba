"""Canonical match-result layer.

Every published result, table, form string, history record and coverage count
reads the frame produced here. The football-data.co.uk partitions are the base
record; the official SPFL club feed fills or corrects Aberdeen league results
that football-data has not published yet (or published differently).

Rules:

* An official row is appended only for an Aberdeen league fixture in a
  competition the football-data feed covers. No other club, and no cup match,
  is invented from the club feed.
* Appended rows are complete match rows with ``phase = "regular"``. This is the
  field the standings and form filters use; a null phase silently removes a
  result from every table-driven surface.
* The official score wins. A disagreement is reported, never hidden.
* The overlay is idempotent: the base frame is read from the partitions on
  every call and is never mutated in place.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import polars as pl

from fitba.ingest.fixtures import load_club_fixtures
from fitba.settings import fixtures_policy
from fitba.sources import football_data_uk
from fitba.util.dates import utc_now_iso

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
    "home_xg",
    "away_xg",
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
    "status",
    "result_source",
    "stats_source",
]

LEAGUE_COMPETITION_IDS = {
    str(definition["id"]) for definition in football_data_uk.DIVISIONS.values()
}


@dataclass(slots=True)
class OverlayEvent:
    """One official fixture considered by the overlay."""

    outcome: str
    date: str
    home_team_id: str | None
    away_team_id: str | None
    match_id: str | None = None
    official_goals: tuple[int, int] | None = None
    canonical_goals: tuple[int, int] | None = None
    source: str = "spfl"

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "date": self.date,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "match_id": self.match_id,
            "official_goals": list(self.official_goals) if self.official_goals else None,
            "canonical_goals": list(self.canonical_goals) if self.canonical_goals else None,
            "source": self.source,
        }


@dataclass(slots=True)
class OverlayReport:
    """Audit record for the overlay and duplicate merge."""

    club: str = "aberdeen"
    precedence: str = "spfl"
    official_fixtures: int = 0
    matched: int = 0
    filled: int = 0
    appended: int = 0
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    api_matched: int = 0
    api_filled: int = 0
    api_appended: int = 0
    api_conflicts: list[dict[str, Any]] = field(default_factory=list)
    duplicates_merged: int = 0
    duplicate_ids: list[str] = field(default_factory=list)
    unmatched_official: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def record(self, event: OverlayEvent) -> None:
        if event.outcome == "matched":
            self.matched += 1
        elif event.outcome == "filled":
            self.filled += 1
        elif event.outcome == "appended":
            self.appended += 1
        elif event.outcome == "conflict":
            self.conflicts.append(event.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "club": self.club,
            "precedence": self.precedence,
            "official_fixtures": self.official_fixtures,
            "matched": self.matched,
            "filled": self.filled,
            "appended": self.appended,
            "conflicts": self.conflicts,
            "api_matched": self.api_matched,
            "api_filled": self.api_filled,
            "api_appended": self.api_appended,
            "api_conflicts": self.api_conflicts,
            "duplicates_merged": self.duplicates_merged,
            "duplicate_ids": self.duplicate_ids,
            "unmatched_official": self.unmatched_official,
            "error": self.error,
        }


def _results_config() -> dict[str, Any]:
    policy = fixtures_policy() or {}
    return policy.get("results") or {}


def official_competition_ids() -> set[str]:
    configured = _results_config().get("official_competitions")
    if configured:
        return {str(item) for item in configured}
    return {"sco:premiership"}


def goal_tolerance_days() -> int:
    try:
        return max(0, int(_results_config().get("date_tolerance_days") or 1))
    except (TypeError, ValueError):
        return 1


def _goals(row: dict[str, Any]) -> tuple[int, int] | None:
    home = row.get("home_goals")
    away = row.get("away_goals")
    if home is None or away is None:
        return None
    try:
        return int(home), int(away)
    except (TypeError, ValueError):
        return None


def _result_for(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "H"
    if home_goals < away_goals:
        return "A"
    return "D"


def _date_value(value: Any) -> date | None:
    text = str(value or "")[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def canonical_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row.get("competition_id") or ""),
        str(row.get("season") or ""),
        str(row.get("date") or "")[:10],
        str(row.get("home_team_id") or ""),
        str(row.get("away_team_id") or ""),
    )


def _team_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("competition_id") or ""),
        str(row.get("home_team_id") or ""),
        str(row.get("away_team_id") or ""),
    )


def ensure_match_columns(frame: pl.DataFrame) -> pl.DataFrame:
    """Add every canonical match column and derive the result status."""
    if frame.height == 0:
        return pl.DataFrame({column: [] for column in MATCH_COLUMNS})
    for column in MATCH_COLUMNS:
        if column not in frame.columns:
            frame = frame.with_columns(pl.lit(None).alias(column))
    goals_present = pl.col("home_goals").is_not_null() & pl.col("away_goals").is_not_null()
    frame = frame.with_columns(
        pl.when(pl.col("status").is_not_null())
        .then(pl.col("status"))
        .when(goals_present)
        .then(pl.lit("played"))
        .otherwise(pl.lit("scheduled"))
        .alias("status"),
        pl.coalesce(pl.col("result_source"), pl.col("source_id")).alias("result_source"),
        pl.when(pl.col("stats_source").is_not_null())
        .then(pl.col("stats_source"))
        .when(
            (pl.col("source_id") == "football_data_uk")
            & pl.col("home_shots").is_not_null()
        )
        .then(pl.lit("football_data_uk"))
        .otherwise(pl.lit(None))
        .alias("stats_source"),
    )
    return frame


def normalise_phase(frame: pl.DataFrame) -> pl.DataFrame:
    """Fill a missing phase for league rows.

    A persisted or appended league result with a null phase is otherwise
    invisible to ``playable_matches`` and every standings/form computation.
    Cup rows are left alone: their phase is not interchangeable with
    ``regular``.
    """
    if frame.height == 0 or "phase" not in frame.columns:
        return frame
    league_ids = sorted(LEAGUE_COMPETITION_IDS)
    missing = pl.col("phase").is_null() | (pl.col("phase") == "")
    league = pl.col("competition_id").is_in(league_ids)
    played = pl.col("home_goals").is_not_null() & pl.col("away_goals").is_not_null()
    return frame.with_columns(
        pl.when(missing & league & played)
        .then(pl.lit("regular"))
        .otherwise(pl.col("phase"))
        .alias("phase")
    )


def official_played_rows(
    club_frame: pl.DataFrame,
    *,
    seasons: Iterable[str] | None = None,
    competition_ids: Iterable[str] | None = None,
) -> pl.DataFrame:
    """Played official club rows for the configured league competitions."""
    if club_frame.height == 0:
        return club_frame
    allowed_competitions = {str(item) for item in (competition_ids or official_competition_ids())}
    allowed_seasons = {str(item) for item in seasons} if seasons else None
    frame = club_frame.filter(
        (pl.col("status") == "played")
        & pl.col("home_goals").is_not_null()
        & pl.col("away_goals").is_not_null()
        & pl.col("competition_id").is_in(sorted(allowed_competitions))
    )
    if allowed_seasons is not None:
        frame = frame.filter(pl.col("season").is_in(sorted(allowed_seasons)))
    return frame


def _division_for(competition_id: str) -> str | None:
    for division, definition in football_data_uk.DIVISIONS.items():
        if str(definition.get("id")) == competition_id:
            return division
    return None


def _row_for_official(item: dict[str, Any]) -> dict[str, Any]:
    goals = _goals(item)
    if goals is None:  # pragma: no cover - filtered by official_played_rows
        raise ValueError("official row has no score")
    home_goals, away_goals = goals
    competition_id = str(item.get("competition_id") or "")
    return {
        "match_id": str(
            item.get("match_id") or f"spfl-{item.get('date')}-{item.get('away_team_id')}"
        ),
        "competition_id": competition_id,
        "competition_name": item.get("competition_name"),
        "season": item.get("season"),
        "division": _division_for(competition_id),
        "date": _date_value(item.get("date")) or str(item.get("date") or "")[:10],
        "kickoff": item.get("kickoff"),
        "phase": "regular",
        "home_team_id": item.get("home_team_id"),
        "home_team_name": item.get("home_team_name"),
        "away_team_id": item.get("away_team_id"),
        "away_team_name": item.get("away_team_name"),
        "home_goals": home_goals,
        "away_goals": away_goals,
        "result": _result_for(home_goals, away_goals),
        "home_ht_goals": None,
        "away_ht_goals": None,
        "ht_result": None,
        "referee": None,
        "home_shots": None,
        "away_shots": None,
        "home_shots_on_target": None,
        "away_shots_on_target": None,
        "home_xg": None,
        "away_xg": None,
        "home_fouls": None,
        "away_fouls": None,
        "home_corners": None,
        "away_corners": None,
        "home_yellow": None,
        "away_yellow": None,
        "home_red": None,
        "away_red": None,
        "source_id": "spfl",
        "ingested_at": item.get("ingested_at") or utc_now_iso(),
        "status": "played",
        "result_source": "spfl",
        "stats_source": None,
    }


def _within_tolerance(left: Any, right: Any, days: int) -> bool:
    if days <= 0:
        return str(left)[:10] == str(right)[:10]
    first = _date_value(left)
    second = _date_value(right)
    if first is None or second is None:
        return False
    return abs((first - second).days) <= days


def overlay_club_results(
    frame: pl.DataFrame,
    *,
    club_slug: str = "aberdeen",
    seasons: Iterable[str] | None = None,
    report: OverlayReport | None = None,
) -> pl.DataFrame:
    """Fill or append official Aberdeen league results onto the match frame."""
    report = report or OverlayReport(club=club_slug, precedence="spfl")
    try:
        club = load_club_fixtures(club_slug)
    except Exception as exc:  # noqa: BLE001 - base frame remains usable
        report.error = f"club fixture feed unavailable: {exc}"
        return frame
    if club.height == 0:
        report.error = "club fixture feed empty"
        return frame
    allowed_seasons = {str(item) for item in seasons} if seasons else set(
        frame["season"].unique().to_list()
    ) if frame.height and "season" in frame.columns else set()
    official = official_played_rows(club, seasons=allowed_seasons or None)
    report.official_fixtures = official.height
    if not official.height:
        return frame

    rows = frame.to_dicts()
    by_key = {canonical_key(row): index for index, row in enumerate(rows)}
    by_teams: dict[tuple[str, str, str], list[int]] = {}
    for index, row in enumerate(rows):
        by_teams.setdefault(_team_key(row), []).append(index)
    tolerance = goal_tolerance_days()
    max_season = str(frame["season"].max()) if frame.height and "season" in frame.columns else ""
    changed = False

    for item in official.to_dicts():
        official_goals = _goals(item)
        if official_goals is None:
            continue
        event = OverlayEvent(
            outcome="appended",
            date=str(item.get("date") or "")[:10],
            home_team_id=item.get("home_team_id"),
            away_team_id=item.get("away_team_id"),
            official_goals=official_goals,
        )
        index = by_key.get(canonical_key(item))
        if index is None:
            for candidate in by_teams.get(_team_key(item), []):
                if _within_tolerance(rows[candidate].get("date"), item.get("date"), tolerance):
                    index = candidate
                    break
        if index is not None:
            row = rows[index]
            base_goals = _goals(row)
            event.match_id = row.get("match_id")
            event.canonical_goals = base_goals
            if base_goals is None:
                event.outcome = "filled"
            elif base_goals == official_goals:
                event.outcome = "matched"
            else:
                event.outcome = "conflict"
            row.update(
                {
                    "home_goals": official_goals[0],
                    "away_goals": official_goals[1],
                    "result": _result_for(*official_goals),
                    "status": "played",
                    "phase": row.get("phase") or "regular",
                    "result_source": "spfl",
                    "source_id": "spfl",
                    "ingested_at": item.get("ingested_at") or row.get("ingested_at"),
                }
            )
            changed = True
            report.record(event)
            continue

        season = str(item.get("season") or "")
        if allowed_seasons and season not in allowed_seasons:
            event.outcome = "unmatched"
            report.unmatched_official.append(event.to_dict())
            continue
        if not allowed_seasons and max_season and season and season != max_season:
            event.outcome = "unmatched"
            report.unmatched_official.append(event.to_dict())
            continue
        new_row = _row_for_official(item)
        rows.append(new_row)
        by_key[canonical_key(new_row)] = len(rows) - 1
        by_teams.setdefault(_team_key(new_row), []).append(len(rows) - 1)
        event.match_id = new_row["match_id"]
        report.record(event)
        changed = True

    if not changed:
        return frame
    return pl.DataFrame(rows, infer_schema_length=None)


def overlay_league_results(
    frame: pl.DataFrame,
    *,
    seasons: Iterable[str] | None = None,
    report: OverlayReport | None = None,
) -> pl.DataFrame:
    """Fill missing league results from the provider fixture snapshot.

    The provider rows are a fallback, never an override. An existing
    football-data result is kept; the official SPFL result already won for
    Aberdeen in the previous overlay. A disagreement is recorded rather than
    silently replacing a published score.
    """
    from fitba.ingest.api_results import load_api_results

    report = report or OverlayReport()
    if frame.height == 0 or "season" not in frame.columns:
        return frame
    allowed = {str(item) for item in seasons} if seasons else set(
        frame["season"].unique().to_list()
    )
    rows = frame.to_dicts()
    by_key = {canonical_key(row): index for index, row in enumerate(rows)}
    changed = False
    for season in sorted(allowed):
        api = load_api_results(season)
        if api.height == 0:
            continue
        for item in api.to_dicts():
            api_goals = _goals(item)
            if api_goals is None:
                continue
            index = by_key.get(canonical_key(item))
            if index is None:
                new_row = dict(item)
                parsed = _date_value(new_row.get("date"))
                if parsed is not None:
                    new_row["date"] = parsed
                new_row.update(
                    {
                        "phase": new_row.get("phase") or "regular",
                        "status": "played",
                        "result_source": "api_football",
                        "stats_source": None,
                    }
                )
                rows.append(new_row)
                by_key[canonical_key(new_row)] = len(rows) - 1
                report.api_appended += 1
                changed = True
                continue
            row = rows[index]
            base_goals = _goals(row)
            if base_goals is None:
                row.update(
                    {
                        "home_goals": api_goals[0],
                        "away_goals": api_goals[1],
                        "result": _result_for(*api_goals),
                        "status": "played",
                        "phase": row.get("phase") or "regular",
                        "result_source": "api_football",
                    }
                )
                report.api_filled += 1
                changed = True
            elif base_goals == api_goals:
                report.api_matched += 1
            else:
                report.api_conflicts.append(
                    {
                        "date": str(item.get("date"))[:10],
                        "home_team_id": item.get("home_team_id"),
                        "away_team_id": item.get("away_team_id"),
                        "canonical_goals": list(base_goals),
                        "api_goals": list(api_goals),
                    }
                )
    return pl.DataFrame(rows, infer_schema_length=None) if changed else frame


def dedupe_matches(
    frame: pl.DataFrame,
    *,
    report: OverlayReport | None = None,
) -> pl.DataFrame:
    """Merge duplicate match ids or canonical keys into one row."""
    if frame.height == 0:
        return frame
    report = report or OverlayReport()
    rows = frame.to_dicts()
    grouped: dict[tuple[str, str, str, str, str], list[int]] = {}
    for index, row in enumerate(rows):
        grouped.setdefault(canonical_key(row), []).append(index)
    keep: list[dict[str, Any]] = []
    merged = 0
    for indexes in grouped.values():
        if len(indexes) == 1:
            keep.append(rows[indexes[0]])
            continue
        merged += len(indexes) - 1
        primary = next(
            (
                rows[index]
                for index in indexes
                if str(rows[index].get("source_id") or "") == "football_data_uk"
            ),
            rows[indexes[0]],
        )
        merged_row = dict(primary)
        for index in indexes:
            candidate = rows[index]
            if str(candidate.get("result_source") or "") == "spfl":
                for column in ("home_goals", "away_goals", "result", "status"):
                    if candidate.get(column) is not None:
                        merged_row[column] = candidate.get(column)
                merged_row["result_source"] = "spfl"
            for column, value in candidate.items():
                if merged_row.get(column) is None and value is not None:
                    merged_row[column] = value
        keep.append(merged_row)
        report.duplicate_ids.append(str(merged_row.get("match_id") or ""))
    report.duplicates_merged += merged
    if merged == 0:
        return frame
    return pl.DataFrame(keep, infer_schema_length=None)


def overlay_official_scores(
    rows: Sequence[dict[str, Any]],
    official_rows: pl.DataFrame,
    *,
    key_fn: Callable[[dict[str, Any]], tuple[str, str, str]],
    date_tolerance_days: int | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Apply official scores to API-shaped fixture rows by canonical team key.

    The history fixture frame uses API team names, not football-data ids, so it
    is matched on the display names supplied by the caller's ``key_fn`` and a
    configurable date tolerance. Returns the rows and the number updated.
    """
    if not rows or official_rows.height == 0:
        return list(rows), 0
    tolerance = goal_tolerance_days() if date_tolerance_days is None else date_tolerance_days
    output = [dict(row) for row in rows]
    index_by_key: dict[tuple[str, str, str], list[int]] = {}
    for index, row in enumerate(output):
        index_by_key.setdefault(key_fn(row), []).append(index)
    updated = 0
    for item in official_rows.to_dicts():
        goals = _goals(item)
        if goals is None:
            continue
        key = (
            str(item.get("competition_id") or ""),
            str(item.get("home_team_name") or ""),
            str(item.get("away_team_name") or ""),
        )
        candidates = index_by_key.get(key, [])
        if not candidates:
            continue
        target = next(
            (
                index
                for index in candidates
                if _within_tolerance(output[index].get("date"), item.get("date"), tolerance)
            ),
            None,
        )
        if target is None:
            continue
        output[target].update(
            {
                "status": "FT",
                "home_goals": goals[0],
                "away_goals": goals[1],
            }
        )
        updated += 1
    return output, updated


__all__ = [
    "LEAGUE_COMPETITION_IDS",
    "MATCH_COLUMNS",
    "OverlayEvent",
    "OverlayReport",
    "canonical_key",
    "dedupe_matches",
    "ensure_match_columns",
    "goal_tolerance_days",
    "normalise_phase",
    "official_competition_ids",
    "official_played_rows",
    "overlay_club_results",
    "overlay_official_scores",
]
