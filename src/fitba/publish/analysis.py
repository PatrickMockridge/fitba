"""Season overview payload.

The page is a projection of one document: current position and form, the next
fixtures, official and derived availability, measured season aims, a factual
squad-decision view and the category bridges. No claim cards, owner view,
benchmark or xG tables are emitted here.
"""

from __future__ import annotations

from typing import Any

from fitba.analytics.availability_rules import (
    absence_signals,
    card_summary,
    suspension_rows,
)
from fitba.normalize.schedule import load_schedule
from fitba.settings import analysis_policy
from fitba.settings import competitions as competitions_config

ABERDEEN_ID = 252


def _fixture(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "fixture_id": row.get("fixture_id"),
        "match_id": row.get("match_id"),
        "date": row.get("date"),
        "kickoff": row.get("kickoff"),
        "kickoff_tz": "Europe/London",
        "kickoff_status": row.get("kickoff_status"),
        "competition_id": row.get("competition_id"),
        "competition_name": row.get("competition_name"),
        "stage": row.get("stage"),
        "opponent_name": row.get("opponent_name"),
        "venue": "N" if row.get("neutral") else "H" if row.get("is_home") else "A",
        "neutral": bool(row.get("neutral")),
        "status": row.get("status"),
        "conflict_review": bool(row.get("conflict_review")),
        "source_id": "spfl" if "spfl" in (row.get("sources") or []) else "api_football",
    }


def _upcoming(schedule: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    rows = [
        _fixture(row)
        for row in schedule
        if row.get("status") == "scheduled"
        and not row.get("conflict_review")
        and not row.get("is_friendly")
    ]
    rows.sort(key=lambda item: (str(item.get("date") or ""), str(item.get("kickoff") or "")))
    return rows[:limit]


def _active_players(
    squad_data: dict[str, Any], availability: dict[str, Any]
) -> tuple[dict[int, dict], list[dict]]:
    players = {
        int(player["player_id"]): player
        for player in squad_data.get("players") or []
        if player.get("status") == "squad"
    }
    ledger = {
        int(entry["player_id"]): entry
        for entry in availability.get("entries") or []
        if entry.get("player_id") is not None
    }
    for player_id, entry in ledger.items():
        if player_id not in players and not entry.get("in_squad"):
            players[player_id] = {
                "player_id": player_id,
                "name": entry.get("player_name"),
                "status": "ledger_only",
                "display_role": {},
                "role": {},
                "totals": {},
            }
    return players, list(ledger.values())


def _official(active_ids: set[int], ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for entry in ledger:
        player_id = int(entry.get("player_id") or 0)
        if player_id not in active_ids or entry.get("status") == "unknown":
            continue
        rows.append(
            {
                "player_id": player_id,
                "player_name": entry.get("player_name"),
                "status": entry.get("status"),
                "reason": entry.get("reason"),
                "reason_category": entry.get("reason_category"),
                "expected_return": entry.get("expected_return"),
                "confidence": entry.get("confidence"),
                "source_id": entry.get("source_id"),
                "source_url": entry.get("source_url"),
                "verified_at": entry.get("verified_at"),
                "note": entry.get("note"),
            }
        )
    return rows


def _aims(
    *,
    table_row: dict[str, Any],
    table_rows: list[dict[str, Any]],
    schedule: list[dict[str, Any]],
    history: dict[str, Any],
) -> list[dict[str, Any]]:
    position = int(table_row.get("position") or 0)
    points = int(table_row.get("points") or 0)
    played = int(table_row.get("played") or 0)
    sixth = next((row for row in table_rows if int(row.get("position") or 0) == 6), {})
    third = next((row for row in table_rows if int(row.get("position") or 0) == 3), {})
    sixth_points = int(sixth.get("points") or 0)
    third_points = int(third.get("points") or 0)
    expectations = history.get("expectations") or {}
    cup = next(
        (
            row
            for row in schedule
            if row.get("competition_id") == "sco:league-cup"
            and row.get("status") == "scheduled"
            and not row.get("conflict_review")
        ),
        None,
    )
    league_note = "Analyst-set baseline, not a published club target."
    return [
        {
            "id": "league",
            "label": "Top six by the split",
            "target": "Top six",
            "current": f"{position}th, {points} points after {played}",
            "status": "on_track" if 0 < position <= 6 else "below",
            "gap": max(0, sixth_points - points),
            "basis": "measured",
            "note": f"{league_note} {expectations.get('baseline') or ''}".strip(),
        },
        {
            "id": "cup",
            "label": "League Cup run",
            "target": "Final",
            "current": (
                (
                    f"Semi-final v {cup.get('opponent_name')}, {cup.get('date')} "
                    f"at {cup.get('venue') or 'TBC'}"
                )
                if cup
                else "No scheduled League Cup tie"
            ),
            "status": "pending" if cup else "unknown",
            "gap": None,
            "basis": "measured",
            "note": "The League Cup carries no European place.",
        },
        {
            "id": "europe",
            "label": "European route",
            "target": "League places 1-3; 4th conditional",
            "current": f"{max(0, third_points - points)} points behind 3rd",
            "status": "context",
            "gap": max(0, third_points - points),
            "basis": "measured",
            "note": (
                "Scotland has four UEFA places; 4th only qualifies if the Scottish Cup "
                "winner is already in the top three. Subject to the final access list."
            ),
        },
    ]


def _squad_decisions(
    *,
    squad_data: dict[str, Any],
    scouting_hub: dict[str, Any],
    needs: dict[str, Any],
    table_row: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    settings = policy.get("squad_decisions") or {}
    min_cohort = int(settings.get("percentile_min_cohort") or 8)
    max_per_lens = int(settings.get("max_per_lens") or 3)
    played = max(1, int(table_row.get("played") or 0))
    team_minutes = played * 90
    hub_rows = {
        int(row["player_id"]): row
        for row in scouting_hub.get("squad") or []
        if row.get("player_id") is not None
    }
    family_players: dict[str, int] = {}
    for player in squad_data.get("players") or []:
        if player.get("status") != "squad":
            continue
        family = (player.get("display_role") or {}).get("family") or "unknown"
        family_players[family] = family_players.get(family, 0) + 1
    needs_by_family = {str(item.get("family")): item for item in needs.get("families") or []}
    rows: list[dict[str, Any]] = []
    for player in squad_data.get("players") or []:
        if player.get("status") != "squad":
            continue
        player_id = int(player["player_id"])
        hub = hub_rows.get(player_id) or {}
        minutes = int(hub.get("minutes") or 0)
        share = round(minutes / team_minutes, 3) if team_minutes else None
        age = player.get("age")
        family = (player.get("display_role") or {}).get("family")
        percent = hub.get("rating_percentile")
        cohort_n = (hub.get("cohort") or {}).get("n")
        if cohort_n is not None and int(cohort_n) < min_cohort:
            percent = None
        rows.append(
            {
                "player_id": player_id,
                "player_name": player.get("name"),
                "age": age,
                "role_label": (player.get("display_role") or {}).get("label"),
                "role_family": family,
                "minutes": minutes,
                "minutes_share": share,
                "rating_percentile": percent,
                "cohort_n": cohort_n,
                "role_depth": family_players.get(str(family), 0),
                "needs_priority": (needs_by_family.get(str(family)) or {}).get("priority"),
            }
        )
    peak = [
        row
        for row in rows
        if row.get("age") is not None
        and int(row["age"]) >= int(settings.get("peak_age_min") or 27)
        and int(row.get("minutes") or 0) >= int(settings.get("peak_minutes_min") or 450)
    ]
    low = [
        row
        for row in rows
        if row.get("age") is not None
        and int(row["age"]) >= int(settings.get("low_minutes_age_min") or 23)
        and row.get("minutes_share") is not None
        and float(row["minutes_share"]) < float(settings.get("low_minutes_share_max") or 0.25)
    ]
    loans = [
        {
            "player_id": player.get("player_id"),
            "player_name": player.get("name"),
            "club": ((player.get("loan") or {}).get("club")),
            "end_date": ((player.get("loan") or {}).get("end_date")),
            "status": "out on loan",
            "note": "Loan end date is not held.",
        }
        for player in squad_data.get("players") or []
        if player.get("status") == "loan_out"
    ]
    return {
        "denominator": {
            "team_matches": played,
            "team_minutes": team_minutes,
            "definition": "player league minutes / (team league matches x 90)",
        },
        "rows": rows,
        "lenses": {
            "peak_age_minutes": {
                "label": "Peak-age minutes",
                "definition": (
                    f"age {settings.get('peak_age_min')}+ and "
                    f"{settings.get('peak_minutes_min')}+ league minutes"
                ),
                "count": len(peak),
                "rows": sorted(peak, key=lambda row: -int(row.get("minutes") or 0))[:max_per_lens],
            },
            "low_minutes": {
                "label": "Low minutes share",
                "definition": (
                    f"age {settings.get('low_minutes_age_min')}+ and below "
                    f"{round(float(settings.get('low_minutes_share_max') or 0.25) * 100)}% "
                    "of team minutes"
                ),
                "count": len(low),
                "rows": sorted(low, key=lambda row: float(row.get("minutes_share") or 0))[
                    :max_per_lens
                ],
            },
        },
        "loans": loans,
        "contract": {
            "status": "unavailable",
            "note": (
                "No licensed contract-expiry, free-agent, wage, fee or release-clause data "
                "is held. Age is not a proxy for contract length."
            ),
        },
        "coverage": {
            "active_players": len(rows),
            "with_percentile": sum(1 for row in rows if row.get("rating_percentile") is not None),
            "without_stats": sum(1 for row in rows if not row.get("minutes")),
            "loans_out": len(loans),
        },
    }


def _bridges() -> list[dict[str, str]]:
    return [
        {
            "label": "Matchday",
            "href": "/matchday/",
            "summary": "Predicted XI, next six and the match read.",
        },
        {
            "label": "Matches",
            "href": "/matches/",
            "summary": "Results and the full remaining schedule.",
        },
        {
            "label": "Squad",
            "href": "/squad/",
            "summary": "Full roster, minutes, loans and role evidence.",
        },
        {
            "label": "Scouting",
            "href": "/scouting/",
            "summary": "Cross-league search and measured role gaps.",
        },
    ]


def build_analysis_payload(
    *,
    season: str,
    generated_at: str,
    squad_data: dict[str, Any],
    availability: dict[str, Any],
    matchday: dict[str, Any] | None,
    needs: dict[str, Any] | None,
    scouting_hub: dict[str, Any] | None,
    history_season: dict[str, Any] | None,
    table_rows: list[dict[str, Any]],
    table_row: dict[str, Any],
) -> dict[str, Any]:
    policy = analysis_policy()
    schedule = load_schedule(season)
    cards = card_summary(season)
    suspensions = suspension_rows(season, cards)
    absence = absence_signals(season, squad_data, availability, matchday)
    active_players, ledger = _active_players(squad_data, availability)
    active_ids = set(active_players)
    official = _official(active_ids, ledger)
    names = {
        int(player["player_id"]): player.get("name")
        for player in squad_data.get("players") or []
        if player.get("player_id") is not None
    }
    for entry in ledger:
        if entry.get("player_id") is not None:
            names.setdefault(int(entry["player_id"]), entry.get("player_name"))
    for row in suspensions:
        row["player_name"] = names.get(int(row["player_id"]))
    for row in absence["inferred"]:
        row["player_name"] = names.get(int(row["player_id"])) or row.get("player_name")
    for row in absence["selection"]:
        row["player_name"] = names.get(int(row["player_id"])) or row.get("player_name")
    loans_out = sum(
        1 for player in squad_data.get("players") or [] if player.get("status") == "loan_out"
    )
    unknown_count = max(0, len(active_ids) - len({entry["player_id"] for entry in official}))
    next_up = _upcoming(schedule, int(policy.get("next_up") or 3))
    bridges = _bridges()
    competitions = competitions_config().get("competitions") or []
    qualification_note = ""
    for competition in competitions:
        if competition.get("id") == "sco:premiership":
            qualification_note = str(competition.get("qualification_note") or "").strip()
            break
    payload = {
        "schema_version": "1.0.0",
        "season": season,
        "generated_at": generated_at,
        "state": "full" if table_row and next_up else "partial",
        "hero": {
            "position": table_row.get("position"),
            "played": table_row.get("played"),
            "points": table_row.get("points"),
            "goal_difference": table_row.get("gd"),
            "form": table_row.get("form"),
            "league_name": "Scottish Premiership",
        },
        "next_up": next_up,
        "availability": {
            "counts": {
                "active": len(active_ids),
                "out_official": sum(1 for entry in official if entry["status"] == "out"),
                "suspended_official": sum(
                    1 for entry in official if entry["status"] == "suspended"
                ),
                "doubtful": sum(1 for entry in official if entry["status"] == "doubtful"),
                "available": sum(1 for entry in official if entry["status"] == "available"),
                "returned": sum(1 for entry in official if entry["status"] == "returned"),
                "unknown": unknown_count,
                "loans_out": loans_out,
            },
            "official": official,
            "suspensions": suspensions,
            "inferred": absence["inferred"],
            "selection": absence["selection"],
            "coverage": {
                "ledger": availability.get("coverage"),
                "cards": cards.get("coverage"),
                "bench": absence["bench_coverage"],
                "window_fixtures": absence["window_fixtures"],
            },
            "note": (
                "Available means a verified ledger entry, not fit. Inferred rows are "
                "cause-not-published, not diagnosis."
            ),
        },
        "aims": _aims(
            table_row=table_row,
            table_rows=table_rows,
            schedule=schedule,
            history=history_season or {},
        ),
        "squad_decisions": _squad_decisions(
            squad_data=squad_data,
            scouting_hub=scouting_hub or {},
            needs=needs or {},
            table_row=table_row,
            policy=policy,
        ),
        "bridges": bridges,
        "coverage": {
            "schedule": {
                "rows": len(schedule),
                "scheduled": sum(1 for row in schedule if row.get("status") == "scheduled"),
                "conflicts": sum(1 for row in schedule if row.get("conflict_review")),
                "overdue": sum(1 for row in schedule if row.get("status") == "overdue"),
            },
            "availability": {
                "known": len(official),
                "unknown": unknown_count,
                "active": len(active_ids),
            },
            "cards": cards.get("coverage"),
            "bench": absence["bench_coverage"],
            "qualification": qualification_note,
            "limitations": [
                "No medical diagnosis is inferred from selection patterns.",
                "Suspension rules are watch/review-only until the current SFA protocol is sourced.",
                "No contract-expiry, free-agent, wage or fee data is held.",
                "Provider ratings are opaque and league-relative.",
            ],
        },
        "sources": ["afc_news", "api_football", "spfl"],
        "notes": "Season overview. Evidence, coverage and unknowns are shown beside each block.",
    }
    return payload


__all__ = ["build_analysis_payload"]
