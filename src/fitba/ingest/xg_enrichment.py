"""League-wide shot-zone and penalty enrichment for the fxG calibration.

The record still has no shot coordinates. This module adds the best available
team-match inputs: shots inside/outside the box, blocked shots and penalty
attempts from API-Football, joined to the football-data provider-xG target for
the 2026-27 Premiership. It is a calibration input, not a published mart.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import polars as pl

from fitba.ingest.runner import load_matches
from fitba.ingest.team_stats import parse_team_stats
from fitba.normalize.names import slugify
from fitba.normalize.teams import TeamRegistry
from fitba.settings import NORMALIZED_DIR, ensure_dirs
from fitba.sources import api_football
from fitba.util.dates import utc_now_iso

COMPETITION_ID = "sco:premiership"
LEAGUE_ID = api_football.SCOTLAND_PREMIERSHIP
FEATURE_DIR = NORMALIZED_DIR / "xg"
FEATURE_PATH = FEATURE_DIR / "team_match_features.parquet"
META_PATH = FEATURE_DIR / "enrichment_meta.json"
PENALTY_XG = 0.76

FEATURE_COLUMNS = [
    "season",
    "competition_id",
    "match_id",
    "api_fixture_id",
    "date",
    "team_id",
    "api_team_id",
    "team_name",
    "opponent_id",
    "opponent_name",
    "venue",
    "goals_for",
    "goals_against",
    "shots",
    "shots_on_target",
    "shots_off",
    "shots_blocked",
    "shots_insidebox",
    "shots_outsidebox",
    "corners",
    "fouls",
    "yellow_cards",
    "red_cards",
    "possession",
    "passes",
    "pass_accuracy",
    "passes_pct",
    "penalty_attempts",
    "penalty_goals",
    "penalty_missed",
    "penalty_status",
    "open_play_shots",
    "open_play_sot",
    "open_play_off",
    "open_play_blocked",
    "open_play_insidebox",
    "open_play_outsidebox",
    "provider_xg_fdco",
    "provider_xg_api",
    "provider_xg_open_play_fdco",
    "stats_source",
    "events_source",
    "zone_status",
    "reconciliation_status",
    "fetched_at",
]


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).replace("%", "").strip()))
    except (TypeError, ValueError):
        return None


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def _parse_date(value: Any) -> date | None:
    text = str(value or "")[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _season_year(season: str) -> int:
    try:
        return int(str(season)[:4])
    except ValueError:
        return api_football.CURRENT_SEASON


def _canonical(teams: TeamRegistry, name: str) -> str:
    resolved = teams.resolve(name)
    return resolved if resolved is not None else f"other:{slugify(name)}"


def derive_penalty_counts(
    events: list[dict[str, Any]],
    teams: TeamRegistry,
) -> dict[str, dict[str, Any]]:
    """Count non-shootout penalty attempts by canonical team.

    API-Football puts a scored penalty in a Goal/Penalty event and a missed one
    in a Goal/Missed Penalty event. VAR "Penalty confirmed/cancelled" rows are
    diagnostics, not attempts. An empty event payload is unknown, not zero.
    """
    counts: dict[str, dict[str, Any]] = {}
    if not events:
        return counts
    for event in events:
        event_type = str(event.get("type") or "").casefold()
        detail = str(event.get("detail") or "").casefold()
        comments = str(event.get("comments") or "").casefold()
        if "shootout" in comments or "shootout" in detail:
            continue
        if event_type != "goal":
            continue
        if detail not in {"penalty", "missed penalty"}:
            continue
        team = (event.get("team") or {}).get("name") or ""
        team_id = _canonical(teams, team)
        row = counts.setdefault(
            team_id,
            {"attempts": 0, "goals": 0, "missed": 0, "status": "measured_zero"},
        )
        row["attempts"] += 1
        if detail == "penalty":
            row["goals"] += 1
        else:
            row["missed"] += 1
        row["status"] = "available"
    return counts


def derive_penalty_counts_from_rows(
    events: list[dict[str, Any]],
    teams: TeamRegistry,
) -> dict[tuple[int, str], dict[str, Any]]:
    """Penalty attempts from normalized history event rows."""
    counts: dict[tuple[int, str], dict[str, Any]] = {}
    for event in events or []:
        event_type = str(event.get("event_type") or "").casefold()
        detail = str(event.get("detail") or "").casefold()
        comments = str(event.get("comments") or "").casefold()
        if "shootout" in comments or "shootout" in detail:
            continue
        if event_type != "goal" or detail not in {"penalty", "missed penalty"}:
            continue
        fixture_id = _int(event.get("fixture_id"))
        if fixture_id is None:
            continue
        team_id = _canonical(teams, str(event.get("team_name") or ""))
        row = counts.setdefault(
            (fixture_id, team_id),
            {"attempts": 0, "goals": 0, "missed": 0, "status": "measured_zero"},
        )
        row["attempts"] += 1
        if detail == "penalty":
            row["goals"] += 1
        else:
            row["missed"] += 1
        row["status"] = "available"
    return counts


def derive_open_play_features(
    stats: dict[str, Any] | None,
    penalties: dict[str, Any] | None,
    *,
    goals_for: int | None,
) -> dict[str, Any]:
    if not stats:
        return {
            "shots": None,
            "shots_on_target": None,
            "shots_off": None,
            "shots_blocked": None,
            "shots_insidebox": None,
            "shots_outsidebox": None,
            "penalty_attempts": None,
            "penalty_goals": None,
            "penalty_missed": None,
            "penalty_status": "stats_unavailable",
            "open_play_shots": None,
            "open_play_sot": None,
            "open_play_off": None,
            "open_play_blocked": None,
            "open_play_insidebox": None,
            "open_play_outsidebox": None,
            "zone_status": "unavailable",
            "reconciliation_status": "stats_unavailable",
        }

    shots = _int(stats.get("shots"))
    sot = _int(stats.get("shots_on_target"))
    off = _int(stats.get("shots_off"))
    blocked = _int(stats.get("shots_blocked"))
    inside = _int(stats.get("shots_insidebox"))
    outside = _int(stats.get("shots_outsidebox"))

    attempts = _int((penalties or {}).get("attempts"))
    pen_goals = _int((penalties or {}).get("goals"))
    pen_missed = _int((penalties or {}).get("missed"))
    penalty_status = str((penalties or {}).get("status") or "unknown")

    if shots is not None and off is None and sot is not None:
        off = max(0, shots - sot - (blocked or 0))

    reconciliation = "ok"
    if (
        shots is not None
        and sot is not None
        and off is not None
        and blocked is not None
        and shots != sot + off + blocked
    ):
        reconciliation = "shots_mismatch"

    zone_status = "available"
    if inside is None or outside is None:
        zone_status = "unavailable"
    elif shots is not None and inside + outside != shots:
        zone_status = "zone_mismatch"

    if reconciliation != "ok" and zone_status == "available":
        zone_status = "reconciliation_mismatch"

    if attempts is not None and shots is not None and attempts > shots:
        penalty_status = "invalid"
        attempts = None
        pen_goals = None
        pen_missed = None
    if pen_goals is not None and goals_for is not None and pen_goals > goals_for:
        penalty_status = "invalid"
        attempts = None
        pen_goals = None
        pen_missed = None

    if attempts is None or sot is None or shots is None:
        open_shots = None
        open_sot = None
        open_off = None
        open_blocked = blocked
        open_inside = None
        open_outside = outside
    else:
        penalty_sot = attempts if sot >= attempts else (pen_goals or 0)
        open_sot = max(0, sot - penalty_sot)
        open_off = max(0, (off or 0) - (attempts - penalty_sot))
        open_blocked = blocked
        open_shots = (
            open_sot + open_off + (open_blocked or 0)
            if open_off is not None
            else max(0, shots - attempts)
        )
        max_open = max(0, shots - attempts)
        if open_shots > max_open:
            open_shots = max_open
            if open_off is not None:
                open_off = max(0, open_shots - open_sot - (open_blocked or 0))
        open_inside = max(0, (inside or 0) - attempts) if inside is not None else None
        open_outside = outside

    return {
        "shots": shots,
        "shots_on_target": sot,
        "shots_off": off,
        "shots_blocked": blocked,
        "shots_insidebox": inside,
        "shots_outsidebox": outside,
        "penalty_attempts": attempts,
        "penalty_goals": pen_goals,
        "penalty_missed": pen_missed,
        "penalty_status": penalty_status,
        "open_play_shots": open_shots,
        "open_play_sot": open_sot,
        "open_play_off": open_off,
        "open_play_blocked": open_blocked,
        "open_play_insidebox": open_inside,
        "open_play_outsidebox": open_outside,
        "zone_status": zone_status,
        "reconciliation_status": reconciliation,
    }


def _football_data_rows(season: str) -> list[dict[str, Any]]:
    frame = load_matches([season])
    frame = frame.filter(pl.col("competition_id") == COMPETITION_ID)
    return [
        {
            "match_id": str(row["match_id"]),
            "date": _parse_date(row.get("date")),
            "competition_id": COMPETITION_ID,
            "home_team_id": str(row.get("home_team_id")),
            "away_team_id": str(row.get("away_team_id")),
            "home_team_name": str(row.get("home_team_name") or ""),
            "away_team_name": str(row.get("away_team_name") or ""),
            "home_goals": _int(row.get("home_goals")),
            "away_goals": _int(row.get("away_goals")),
            "home_xg": _float(row.get("home_xg")),
            "away_xg": _float(row.get("away_xg")),
            "home_shots": _int(row.get("home_shots")),
            "away_shots": _int(row.get("away_shots")),
            "home_sot": _int(row.get("home_shots_on_target")),
            "away_sot": _int(row.get("away_shots_on_target")),
        }
        for row in frame.to_dicts()
    ]


def _find_fdco(
    api_fixture: dict[str, Any],
    rows: list[dict[str, Any]],
    teams: TeamRegistry,
    *,
    tolerance_days: int = 1,
) -> dict[str, Any] | None:
    fixture = api_fixture.get("fixture") or {}
    fixture_teams = api_fixture.get("teams") or {}
    target_date = _parse_date(fixture.get("date"))
    home = _canonical(teams, str((fixture_teams.get("home") or {}).get("name") or ""))
    away = _canonical(teams, str((fixture_teams.get("away") or {}).get("name") or ""))
    if target_date is None:
        return None
    candidates = [
        row
        for row in rows
        if row["date"] is not None
        and abs((row["date"] - target_date).days) <= tolerance_days
        and row["home_team_id"] == home
        and row["away_team_id"] == away
    ]
    if len(candidates) > 1:
        ids = ", ".join(row["match_id"] for row in candidates)
        raise ValueError(f"ambiguous football-data match for API fixture: {ids}")
    return candidates[0] if candidates else None


def _event_source(events: list[dict[str, Any]]) -> str:
    return "api_football" if events else "unavailable"


def enrich_premiership(
    season: str = "2026-27",
    *,
    league_id: int = LEAGUE_ID,
    max_requests: int = 120,
    refresh: bool = False,
) -> dict[str, Any]:
    """Fetch and write the league-wide enrichment table.

    The function is resumable and idempotent. It never calls ``force`` for the
    per-fixture statistics/events; completed-match responses have a long TTL.
    """
    ensure_dirs()
    season_year = _season_year(season)
    teams = TeamRegistry()
    fdco_rows = _football_data_rows(season)
    start_requests = api_football.network_requests()
    fixtures = api_football.fixtures(
        league_id, season_year, ttl_hours=6, force=refresh
    )
    finished = [
        item
        for item in fixtures
        if int((item.get("league") or {}).get("id") or 0) == int(league_id)
        and str((item.get("fixture") or {}).get("status", {}).get("short") or "")
        in {"FT", "AET", "PEN"}
    ]

    rows: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    missing_stats: list[int] = []
    missing_events: list[int] = []
    stopped_at_budget = False
    now = utc_now_iso()

    for item in finished:
        fixture = item.get("fixture") or {}
        fixture_id = _int(fixture.get("id"))
        if fixture_id is None:
            continue
        if api_football.network_requests() - start_requests >= max_requests:
            stopped_at_budget = True
            break
        stats_payload: list[dict[str, Any]] = []
        events_payload: list[dict[str, Any]] = []
        try:
            stats_payload = api_football.fixtures_statistics(
                fixture_id, ttl_hours=8760, force=False
            )
        except Exception:  # noqa: BLE001 - record the gap, do not stop the run
            missing_stats.append(fixture_id)
        try:
            events_payload = api_football.fixtures_events(fixture_id)
        except Exception:  # noqa: BLE001
            missing_events.append(fixture_id)

        fdco = _find_fdco(item, fdco_rows, teams)
        if fdco is None:
            fixture_teams = item.get("teams") or {}
            unmatched.append(
                {
                    "api_fixture_id": fixture_id,
                    "date": str(fixture.get("date") or "")[:10],
                    "home": str((fixture_teams.get("home") or {}).get("name") or ""),
                    "away": str((fixture_teams.get("away") or {}).get("name") or ""),
                }
            )
            continue

        stats_by_team = {
            row["team_id"]: row
            for row in parse_team_stats(stats_payload, fixture_id=fixture_id)
        }
        penalty_by_team = derive_penalty_counts(events_payload, teams)
        fixture_teams = item.get("teams") or {}
        goals = item.get("goals") or {}
        for side, home in (("home", True), ("away", False)):
            team_block = fixture_teams.get(side) or {}
            api_team_id = _int(team_block.get("id"))
            team_name = str(team_block.get("name") or "")
            if api_team_id is None:
                continue
            canonical = _canonical(teams, team_name)
            stats = stats_by_team.get(api_team_id)
            penalties = penalty_by_team.get(canonical)
            if events_payload and penalties is None:
                penalties = {
                    "attempts": 0,
                    "goals": 0,
                    "missed": 0,
                    "status": "measured_zero",
                }
            if stats is None:
                missing_stats.append(fixture_id)
            goals_for = _int(goals.get(side))
            goals_against = _int(goals.get("away" if home else "home"))
            features = derive_open_play_features(
                stats, penalties, goals_for=goals_for
            )
            provider = fdco.get("home_xg" if home else "away_xg")
            open_provider = (
                max(0.0, provider - PENALTY_XG * features["penalty_attempts"])
                if provider is not None and features["penalty_attempts"] is not None
                else None
            )
            rows.append(
                {
                    "season": season,
                    "competition_id": COMPETITION_ID,
                    "match_id": fdco["match_id"],
                    "api_fixture_id": fixture_id,
                    "date": str(fixture.get("date") or "")[:10],
                    "team_id": canonical,
                    "api_team_id": api_team_id,
                    "team_name": team_name,
                    "opponent_id": fdco["away_team_id" if home else "home_team_id"],
                    "opponent_name": fdco[
                        "away_team_name" if home else "home_team_name"
                    ],
                    "venue": "H" if home else "A",
                    "goals_for": goals_for,
                    "goals_against": goals_against,
                    **features,
                    "corners": _int((stats or {}).get("corners")),
                    "fouls": _int((stats or {}).get("fouls")),
                    "yellow_cards": _int((stats or {}).get("yellow_cards")),
                    "red_cards": _int((stats or {}).get("red_cards")),
                    "possession": _float((stats or {}).get("possession")),
                    "passes": _int((stats or {}).get("passes")),
                    "pass_accuracy": _int((stats or {}).get("pass_accuracy")),
                    "passes_pct": _float((stats or {}).get("passes_pct")),
                    "provider_xg_fdco": provider,
                    "provider_xg_api": _float((stats or {}).get("expected_goals")),
                    "provider_xg_open_play_fdco": (
                        round(open_provider, 3) if open_provider is not None else None
                    ),
                    "stats_source": "api_football" if stats else "unavailable",
                    "events_source": _event_source(events_payload),
                    "fetched_at": now,
                }
            )

    frame = pl.DataFrame(rows) if rows else pl.DataFrame()
    if rows:
        ordered = [column for column in FEATURE_COLUMNS if column in frame.columns]
        frame = frame.select(ordered)
    FEATURE_DIR.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(FEATURE_PATH)

    matched_fixtures = {row["api_fixture_id"] for row in rows}
    meta = {
        "season": season,
        "competition_id": COMPETITION_ID,
        "league_id": league_id,
        "generated_at": now,
        "fixtures_total": len(fixtures),
        "fixtures_finished": len(finished),
        "fixtures_with_rows": len(matched_fixtures),
        "team_rows": len(rows),
        "stats_available": sum(1 for row in rows if row["stats_source"] == "api_football"),
        "events_available": sum(1 for row in rows if row["events_source"] == "api_football"),
        "zones_available": sum(1 for row in rows if row["zone_status"] == "available"),
        "penalties_available": sum(
            1 for row in rows if row["penalty_status"] in {"available", "measured_zero"}
        ),
        "provider_xg_fdco": sum(
            1 for row in rows if row["provider_xg_fdco"] is not None
        ),
        "missing_stats_fixtures": sorted(set(missing_stats)),
        "missing_events_fixtures": sorted(set(missing_events)),
        "unmatched_fixtures": unmatched,
        "stopped_at_budget": stopped_at_budget,
        "network_requests": api_football.network_requests() - start_requests,
        "max_requests": max_requests,
        "feature_path": str(FEATURE_PATH),
    }
    META_PATH.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def load_enrichment(season: str | None = None) -> pl.DataFrame:
    if not FEATURE_PATH.exists():
        return pl.DataFrame()
    frame = pl.read_parquet(FEATURE_PATH)
    if season is not None:
        frame = frame.filter(pl.col("season") == season)
    return frame


def enrichment_by_match_team(
    season: str = "2026-27",
) -> dict[tuple[str, str], dict[str, Any]]:
    frame = load_enrichment(season)
    if not frame.height:
        return {}
    return {
        (str(row["match_id"]), str(row["team_id"])): row
        for row in frame.to_dicts()
    }


__all__ = [
    "FEATURE_COLUMNS",
    "FEATURE_PATH",
    "META_PATH",
    "derive_open_play_features",
    "derive_penalty_counts",
    "derive_penalty_counts_from_rows",
    "enrich_premiership",
    "enrichment_by_match_team",
    "load_enrichment",
]
