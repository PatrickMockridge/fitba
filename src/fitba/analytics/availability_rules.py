"""Derived availability signals for the season overview.

The official AFC ledger is the only injury source. This module adds two clearly
separate derived signals: competition-scoped card/suspension watches and
selection-based absence signals from named matchday squads. It never converts a
two-game omission into a medical claim.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fitba.ingest.match_data import load_player_squads
from fitba.ingest.match_extras import load_events
from fitba.normalize.schedule import load_schedule
from fitba.settings import suspensions as suspension_config

ABERDEEN_ID = 252
COMPETITIVE_COMPETITIONS = {"sco:premiership", "sco:league-cup", "sco:scottish-cup"}


def _fixture_map(season: str) -> dict[int, dict[str, Any]]:
    return {
        int(row["fixture_id"]): row
        for row in load_schedule(season)
        if row.get("fixture_id") is not None
    }


def _next_fixture(
    schedule: list[dict[str, Any]], competition_id: str, after: str | None
) -> dict[str, Any] | None:
    candidates = [
        row
        for row in schedule
        if row.get("competition_id") == competition_id
        and row.get("status") == "scheduled"
        and not row.get("conflict_review")
        and (after is None or str(row.get("date") or "") > after)
    ]
    return min(candidates, key=lambda row: str(row.get("date") or "")) if candidates else None


def card_summary(season: str) -> dict[str, Any]:
    """Cautions and reds by player/competition, with second yellows reconciled."""
    events = load_events(season)
    fixtures = _fixture_map(season)
    by_fixture: dict[tuple[int, int], dict[str, Any]] = defaultdict(
        lambda: {"yellows": [], "reds": [], "competition": None, "date": None}
    )
    for row in events.to_dicts() if events.height else []:
        if int(row.get("team_id") or 0) != ABERDEEN_ID:
            continue
        if str(row.get("event_type") or "").casefold() != "card":
            continue
        fixture_id = int(row.get("fixture_id") or 0)
        fixture = fixtures.get(fixture_id) or {}
        if str(fixture.get("competition_id") or "") not in COMPETITIVE_COMPETITIONS:
            continue
        player_id = row.get("player_id")
        if player_id is None:
            continue
        entry = by_fixture[(int(player_id), fixture_id)]
        entry["competition"] = fixture.get("competition_id")
        entry["date"] = fixture.get("date")
        detail = str(row.get("detail") or "").casefold()
        if "red" in detail:
            entry["reds"].append(row)
        elif "yellow" in detail:
            entry["yellows"].append(row)

    per_player: dict[tuple[int, str], dict[str, Any]] = defaultdict(
        lambda: {
            "cautions": 0,
            "reds": 0,
            "red_type": None,
            "last_date": None,
            "last_fixture_id": None,
        }
    )
    for (player_id, _fixture_id), entry in by_fixture.items():
        competition = str(entry["competition"])
        row = per_player[(player_id, competition)]
        yellows = entry["yellows"]
        reds = entry["reds"]
        if reds:
            row["reds"] += len(reds)
            row["red_type"] = "second_yellow" if len(yellows) >= 2 else "straight_red"
            if len(yellows) >= 2:
                row["cautions"] += 1
            else:
                row["cautions"] += len(yellows)
        else:
            row["cautions"] += len(yellows)
        row["last_date"] = max(str(row["last_date"] or ""), str(entry["date"] or ""))
        row["last_fixture_id"] = _fixture_id

    played = defaultdict(int)
    covered = defaultdict(int)
    event_fixture_ids = {
        int(row.get("fixture_id") or 0) for row in (events.to_dicts() if events.height else [])
    }
    for fixture in fixtures.values():
        competition = str(fixture.get("competition_id") or "")
        if competition not in COMPETITIVE_COMPETITIONS or fixture.get("status") != "played":
            continue
        played[competition] += 1
        if int(fixture["fixture_id"]) in event_fixture_ids:
            covered[competition] += 1
    return {
        "players": {
            f"{player_id}:{competition}": value
            for (player_id, competition), value in per_player.items()
        },
        "coverage": {
            competition: {
                "played": played[competition],
                "covered": covered[competition],
                "complete": covered[competition] >= played[competition],
            }
            for competition in COMPETITIVE_COMPETITIONS
        },
    }


def suspension_rows(
    season: str,
    cards: dict[str, Any],
    *,
    as_of: str | None = None,
) -> list[dict[str, Any]]:
    schedule = load_schedule(season)
    config = suspension_config().get("competitions") or {}
    rows: list[dict[str, Any]] = []
    for key, value in (cards.get("players") or {}).items():
        player_id, competition = key.split(":", 1)
        rule = config.get(competition) or {}
        coverage = (cards.get("coverage") or {}).get(competition) or {}
        thresholds = rule.get("yellow_thresholds") or []
        cautions = int(value.get("cautions") or 0)
        reds = int(value.get("reds") or 0)
        status = "none"
        threshold = None
        reason = None
        if reds:
            status = "review_required"
            reason = "red_card"
        elif thresholds:
            for item in thresholds:
                count = int(item.get("count") or 0)
                if cautions >= count:
                    threshold = count
                    break
            if threshold is not None:
                status = "projected" if rule.get("verified") else "review_required"
                reason = "accumulation"
            elif thresholds and cautions >= int(thresholds[0].get("count") or 0) - 1:
                status = "watch"
                threshold = int(thresholds[0].get("count") or 0)
                reason = "accumulation"
        if status == "none":
            continue
        if not coverage.get("complete") and status in {"projected", "watch"}:
            status = "review_required"
        next_fixture = _next_fixture(schedule, competition, value.get("last_date"))
        rows.append(
            {
                "player_id": int(player_id),
                "competition_id": competition,
                "competition_name": rule.get("label") or competition,
                "cautions": cautions,
                "threshold": threshold,
                "reds": reds,
                "red_type": value.get("red_type"),
                "reason": reason,
                "status": status,
                "rule_verified": bool(rule.get("verified")),
                "rule_source": rule.get("source_url"),
                "effective_days": rule.get("effective_days"),
                "last_card_date": value.get("last_date"),
                "next_fixture": (
                    {
                        "fixture_id": next_fixture.get("fixture_id"),
                        "date": next_fixture.get("date"),
                        "competition_id": next_fixture.get("competition_id"),
                        "opponent_name": next_fixture.get("opponent_name"),
                    }
                    if next_fixture
                    else None
                ),
            }
        )
    return rows


def absence_signals(
    season: str,
    squad_data: dict[str, Any],
    availability: dict[str, Any],
    matchday: dict[str, Any] | None,
) -> dict[str, Any]:
    squads = load_player_squads()
    schedule = load_schedule(season)
    fixtures = {
        int(row["fixture_id"]): row
        for row in schedule
        if row.get("fixture_id") is not None
        and row.get("status") == "played"
        and not row.get("is_friendly")
    }
    squad_rows = squads.to_dicts() if squads.height else []
    covered = {
        int(row["fixture_id"])
        for row in squad_rows
        if int(row.get("team_id") or 0) == ABERDEEN_ID and row.get("bench_complete")
    }
    recent = sorted(
        covered,
        key=lambda fixture_id: str(fixtures.get(fixture_id, {}).get("date") or ""),
        reverse=True,
    )[:6]
    by_player: dict[int, dict[int, str]] = defaultdict(dict)
    for row in squad_rows:
        if int(row.get("team_id") or 0) != ABERDEEN_ID:
            continue
        player_id = int(row.get("player_id") or 0)
        if player_id:
            by_player[player_id][int(row.get("fixture_id") or 0)] = str(row.get("squad_status"))
    ledger = {int(entry["player_id"]): entry for entry in availability.get("entries") or []}
    inferred: list[dict[str, Any]] = []
    selection: list[dict[str, Any]] = []
    for player in squad_data.get("players") or []:
        if player.get("status") != "squad":
            continue
        player_id = int(player["player_id"])
        entry = ledger.get(player_id) or {}
        if entry.get("status") in {"out", "suspended", "doubtful", "available", "returned"}:
            continue
        statuses = [
            by_player.get(player_id, {}).get(fixture_id, "not_in_squad") for fixture_id in recent
        ]
        in_squad = sum(1 for status in statuses if status in {"starter", "sub_used", "sub_unused"})
        starts = sum(1 for status in statuses if status == "starter")
        bench = sum(1 for status in statuses if status in {"sub_used", "sub_unused"})
        if (
            len(recent) >= 2
            and statuses[0] == "not_in_squad"
            and statuses[1] == "not_in_squad"
            and in_squad >= 5
            and (starts >= 1 or bench >= 3)
        ):
            inferred.append(
                {
                    "player_id": player_id,
                    "player_name": player.get("name"),
                    "role_label": (player.get("display_role") or {}).get("label"),
                    "fixtures": [
                        {
                            "fixture_id": fixture_id,
                            "date": fixtures.get(fixture_id, {}).get("date"),
                            "competition": fixtures.get(fixture_id, {}).get("competition_name"),
                        }
                        for fixture_id in recent[:2]
                    ],
                    "in_squad_of_six": in_squad,
                    "starts_of_six": starts,
                    "bench_of_six": bench,
                    "confidence": "medium",
                    "basis": "inferred",
                    "note": "Not in the last two matchday squads; reason not published.",
                }
            )
    contenders = ((matchday or {}).get("predicted_lineups") or {}).get("aberdeen") or {}
    for item in contenders.get("contenders") or []:
        confidence = str(item.get("confidence") or "unknown")
        if confidence not in {"high", "medium"}:
            continue
        if item.get("available") is False or item.get("status") in {"out", "suspended"}:
            continue
        selection.append(
            {
                "player_id": item.get("player_id"),
                "player_name": item.get("name"),
                "role_label": item.get("role_label"),
                "confidence": confidence,
                "score": item.get("score"),
                "basis": "projection",
                "note": "Predicted contender; not team news.",
            }
        )
    return {
        "inferred": inferred,
        "selection": selection[:3],
        "window_fixtures": recent,
        "bench_coverage": {
            "fixtures": len(recent),
            "named_bench_complete": len(covered),
        },
    }


__all__ = ["absence_signals", "card_summary", "suspension_rows"]
