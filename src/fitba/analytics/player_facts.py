"""One home for player season totals, ratings and playing-time scope.

The squad table, player profile, scouting hub and needs board must not each
choose their own filters. Every total names its scope:

- ``all_competitions``: Aberdeen club rows, league and cups, friendlies out.
- ``league``: the Premiership subset, used for the league comparison.
- ``loan``: the registered loan club, never mixed into a club total.

A competition without player statistics is missing, not zero. The caller
publishes coverage rather than filling it from another competition.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from fitba.normalize.scope import is_friendly_competition

COUNT_FIELDS = (
    "appearances",
    "starts",
    "minutes",
    "goals",
    "assists",
    "yellow_cards",
    "red_cards",
    "shots_total",
    "shots_on",
    "passes_total",
    "passes_key",
    "saves",
    "tackles",
    "blocks",
    "interceptions",
    "duels_total",
    "duels_won",
    "dribbles_attempts",
    "conceded",
    "fouls_committed",
    "penalty_scored",
    "penalty_saved",
    "dribbles_success",
)
RATE_FIELDS = ("pass_accuracy", "dribbles_success", "duels_won", "penalty_missed")


def stat_rows(
    player: dict[str, Any],
    *,
    scope: str = "club",
    competition: str | None = None,
    exclude_friendlies: bool = True,
) -> list[dict[str, Any]]:
    """Filter a player's provider rows to one declared scope."""
    rows = []
    for row in player.get("stats") or []:
        if row.get("scope") != scope:
            continue
        if competition is not None and row.get("competition") != competition:
            continue
        if exclude_friendlies and is_friendly_competition(row.get("competition")):
            continue
        rows.append(row)
    return rows


def totals(rows: Iterable[dict[str, Any]], *, scope: str) -> dict[str, Any] | None:
    """Sum count fields and calculate the appearance-weighted provider rating."""
    items = list(rows)
    if not items:
        return None
    output: dict[str, Any] = {"scope": scope}
    for field in COUNT_FIELDS:
        values = [row.get(field) for row in items if row.get(field) is not None]
        output[field] = sum(int(value or 0) for value in values) if values else None
    rated = [
        (float(row["rating"]), int(row.get("appearances") or 0))
        for row in items
        if row.get("rating") is not None and int(row.get("appearances") or 0) > 0
    ]
    output["rating"] = (
        round(
            sum(rating * appearances for rating, appearances in rated)
            / sum(appearances for _, appearances in rated),
            2,
        )
        if rated
        else None
    )
    weighted_passes = 0
    weighted_accuracy = 0.0
    for row in items:
        total = row.get("passes_total")
        accuracy = row.get("pass_accuracy")
        if total is None or accuracy is None:
            continue
        weighted_passes += int(total)
        weighted_accuracy += float(total) * float(accuracy)
    output["pass_accuracy"] = (
        round(weighted_accuracy / weighted_passes, 2) if weighted_passes else None
    )
    return output


def club_totals(player: dict[str, Any]) -> dict[str, Any] | None:
    return totals(stat_rows(player, scope="club"), scope="all_competitions")


def league_totals(player: dict[str, Any]) -> dict[str, Any] | None:
    rows = [
        row
        for row in stat_rows(player, scope="club")
        if str(row.get("competition") or "") in {"Premiership", "Scottish Premiership"}
    ]
    return totals(rows, scope="league")


def loan_totals(player: dict[str, Any]) -> dict[str, Any] | None:
    return totals(stat_rows(player, scope="loan"), scope="loan")


def _canonical_competition(name: Any) -> str:
    text = str(name or "").strip().casefold()
    if text in {"premiership", "scottish premiership"}:
        return "scottish premiership"
    return text


def missing_output_competitions(player: dict[str, Any]) -> list[str]:
    """Competitions with Aberdeen appearances but no provider player output."""
    event_names = {
        str(row.get("competition"))
        for row in (player.get("playing_time") or {}).get("by_competition") or []
        if row.get("competition")
    }
    provider_keys = {
        _canonical_competition(row.get("competition"))
        for row in stat_rows(player, scope="club")
    }
    return sorted(
        name
        for name in event_names
        if _canonical_competition(name) not in provider_keys
    )


def playing_time(player: dict[str, Any]) -> dict[str, Any]:
    """Return the event-reconstructed Aberdeen all-competition playing time."""
    return dict(player.get("playing_time") or {})


__all__ = [
    "COUNT_FIELDS",
    "club_totals",
    "league_totals",
    "loan_totals",
    "missing_output_competitions",
    "playing_time",
    "stat_rows",
    "totals",
]
