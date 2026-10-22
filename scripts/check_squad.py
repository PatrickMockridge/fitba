#!/usr/bin/env python3
"""CI guard for the published squad payload and site-wide player links."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "web" / "data" / "generated"
ROLES = ROOT / "config" / "roles.yaml"
SQUAD = GENERATED / "squad" / "aberdeen.json"
TRANSFERS = GENERATED / "transfers" / "aberdeen.json"
RUMOURS = GENERATED / "rumours" / "aberdeen.json"
PROFILE = GENERATED / "rumours" / "profile.json"
FORUM = GENERATED / "forum" / "afc_chat.json"
CLUB = GENERATED / "clubs" / "aberdeen.json"

VALID_STATUS = {"squad", "loan_out", "loan_in"}
VALID_COVERAGE = {"available", "partial", "unavailable"}
VALID_SCOPE = {"club", "loan", "other"}
TOTAL_FIELDS = [
    "appearances",
    "starts",
    "minutes",
    "goals",
    "assists",
    "yellow_cards",
    "red_cards",
    "saves",
    "tackles",
    "blocks",
    "interceptions",
    "duels_won",
    "fouls_committed",
    "penalty_scored",
    "penalty_saved",
    "shots_total",
    "shots_on",
    "passes_key",
    "dribbles_success",
]
POSITION_FIELDS = ["matches", "minutes_on_pitch", "conceded_on_pitch", "clean_sheets", "own_goals"]
VALID_ROLE_STATUS = {"observed", "partial", "unknown"}
VALID_PLAYING_COVERAGE = {"available", "partial", "unavailable", "not_applicable"}
VALID_ROLE_COVERAGE = {"available", "partial", "unavailable"}
VALID_CAREER_STATUS = {"observed", "low_evidence", "mixed", "unknown", "unavailable"}
VALID_DISPLAY_SOURCES = {
    "career",
    "aberdeen_override",
    "current_season",
    "career_low_evidence",
    "none",
}
VALID_TIERS = {"primary", "secondary", "stretch", "other"}


def _load(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _href_set(squad: dict[str, Any]) -> set[str]:
    return {str(player["href"]) for player in squad.get("players", [])}


def _check_hrefs(payload: Any, hrefs: set[str], where: str, errors: list[str]) -> None:
    if not isinstance(payload, dict):
        return
    for player in payload.get("transfers", []):
        href = player.get("player_href")
        if href and href not in hrefs:
            errors.append(f"{where}: unknown transfer player_href {href}")
    for rumour in payload.get("rumours", []):
        href = rumour.get("player_href")
        if href and href not in hrefs:
            errors.append(f"{where}: unknown rumour player_href {href}")
        for mention in rumour.get("player_mentions", []):
            if mention.get("href") not in hrefs:
                errors.append(f"{where}: unknown rumour mention {mention.get('href')}")
    for signal in payload.get("signals", []):
        href = signal.get("player_href")
        if href and href not in hrefs:
            errors.append(f"{where}: unknown signal player_href {href}")
    for topic in payload.get("topics", []):
        for mention in topic.get("player_mentions", []):
            if mention.get("href") not in hrefs:
                errors.append(f"{where}: unknown topic mention {mention.get('href')}")
    for article in payload.get("news", []):
        for mention in article.get("player_mentions", []):
            if mention.get("href") not in hrefs:
                errors.append(f"{where}: unknown news mention {mention.get('href')}")


def _check_playing_time(player: dict[str, Any], playing: dict[str, Any], errors: list[str]) -> None:
    pid = player.get("player_id")
    coverage = playing.get("coverage")
    if coverage not in VALID_PLAYING_COVERAGE:
        errors.append(f"{pid}: invalid playing-time coverage {coverage!r}")
    fields = ("starts", "sub_apps", "minutes", "minutes_started", "minutes_as_sub")
    for field in fields:
        if not isinstance(playing.get(field), int) or playing.get(field, -1) < 0:
            errors.append(f"{pid}: playing-time {field} is not a non-negative int")
    rows = playing.get("by_competition") or []
    for field in fields:
        expected = sum(int(row.get(field) or 0) for row in rows)
        if int(playing.get(field) or 0) != expected:
            errors.append(f"{pid}: playing-time {field} does not match competitions")
    if int(playing.get("minutes_started") or 0) + int(playing.get("minutes_as_sub") or 0) != int(
        playing.get("minutes") or 0
    ):
        errors.append(f"{pid}: playing-time minutes split does not add up")
    if coverage in {"unavailable", "not_applicable"} and rows:
        errors.append(f"{pid}: unavailable playing time has competition rows")
    if coverage == "available" and not rows and player.get("status") != "loan_out":
        errors.append(f"{pid}: available playing time has no competition rows")


def _check_role(
    player: dict[str, Any],
    role: dict[str, Any],
    playing: dict[str, Any],
    roles_config: dict[str, Any],
    errors: list[str],
) -> None:
    pid = player.get("player_id")
    status = role.get("status")
    if status not in VALID_ROLE_STATUS:
        errors.append(f"{pid}: invalid role status {status!r}")
        return
    role_defs = roles_config.get("roles") or {}
    starts_total = int(role.get("starts_total") or 0)
    starts_with_role = int(role.get("starts_with_role") or 0)
    if starts_total != int(playing.get("starts") or 0):
        errors.append(f"{pid}: role starts_total does not match playing-time starts")
    if starts_with_role > starts_total:
        errors.append(f"{pid}: role starts_with_role exceeds starts_total")
    rows = role.get("roles") or []
    if status == "unknown":
        if role.get("primary") is not None or role.get("code") is not None:
            errors.append(f"{pid}: unknown role has a primary value")
        if rows:
            errors.append(f"{pid}: unknown role has role rows")
        if not role.get("unknown_reason"):
            errors.append(f"{pid}: unknown role has no reason")
        return
    code = str(role.get("code") or "")
    definition = role_defs.get(code)
    if not definition:
        errors.append(f"{pid}: role code {code!r} is not in config/roles.yaml")
        return
    if role.get("family") != definition.get("family"):
        errors.append(f"{pid}: role family does not match config")
    if role.get("side") != definition.get("side"):
        errors.append(f"{pid}: role side does not match config")
    if status == "observed" and starts_with_role != starts_total:
        errors.append(f"{pid}: observed role does not cover every start")
    if status == "partial" and not (0 < starts_with_role < starts_total):
        errors.append(f"{pid}: partial role coverage is inconsistent")
    if not rows:
        errors.append(f"{pid}: known role has no role history")
        return
    total_role_starts = 0
    total_role_minutes = 0
    for row in rows:
        row_code = str(row.get("code") or "")
        row_def = role_defs.get(row_code)
        if not row_def:
            errors.append(f"{pid}: role history has unknown code {row_code!r}")
            continue
        if row.get("family") != row_def.get("family"):
            errors.append(f"{pid}: role history family mismatch for {row_code}")
        if int(row.get("starts") or 0) <= 0:
            errors.append(f"{pid}: role history {row_code} has no starts")
        total_role_starts += int(row.get("starts") or 0)
        total_role_minutes += int(row.get("minutes") or 0)
    if total_role_starts != starts_with_role:
        errors.append(f"{pid}: role history starts do not match starts_with_role")
    if total_role_minutes > int(playing.get("minutes_started") or 0):
        errors.append(f"{pid}: role history minutes exceed minutes started")
    source = role.get("source")
    if not isinstance(source, dict) or source.get("id") != "api_football":
        errors.append(f"{pid}: known role has no API-Football source")


def _check_career_role(
    player: dict[str, Any],
    career: dict[str, Any],
    display: dict[str, Any],
    roles_config: dict[str, Any],
    errors: list[str],
) -> None:
    pid = player.get("player_id")
    status = career.get("status")
    if status not in VALID_CAREER_STATUS:
        errors.append(f"{pid}: invalid career status {status!r}")
    slots_cfg = (roles_config.get("career") or {}).get("slots") or {}
    slots = career.get("slots") or []
    primary = career.get("primary_slot")
    if status in {"observed", "low_evidence", "mixed"} and not primary:
        errors.append(f"{pid}: career status {status} has no primary slot")
    if primary:
        if primary.get("slot") not in slots_cfg:
            errors.append(f"{pid}: primary career slot is not in config")
        if primary.get("code") not in (roles_config.get("roles") or {}):
            errors.append(f"{pid}: primary career role code is unknown")
    total_starts = 0
    total_share = 0.0
    for row in slots:
        if row.get("slot") not in slots_cfg:
            errors.append(f"{pid}: career slot {row.get('slot')!r} is not in config")
        if row.get("tier") not in VALID_TIERS:
            errors.append(f"{pid}: invalid career tier {row.get('tier')!r}")
        if int(row.get("starts") or 0) < 0:
            errors.append(f"{pid}: negative career starts")
        total_starts += int(row.get("starts") or 0)
        total_share += float(row.get("share") or 0)
    if slots and abs(total_share - 1.0) > 0.001:
        errors.append(f"{pid}: career slot shares do not sum to 1")
    if total_starts != int(career.get("starts_with_role") or 0):
        errors.append(f"{pid}: career slot starts do not match starts_with_role")
    if int(career.get("starts_with_role") or 0) > int(career.get("starts_total") or 0):
        errors.append(f"{pid}: career starts_with_role exceeds starts_total")
    if career.get("status") == "unknown" and slots:
        errors.append(f"{pid}: unknown career has slots")
    source = display.get("source")
    if source not in VALID_DISPLAY_SOURCES:
        errors.append(f"{pid}: invalid display-role source {source!r}")
    if source == "aberdeen_override":
        current = player.get("role") or {}
        if current.get("status") not in {"observed", "partial"}:
            errors.append(f"{pid}: override without an established current role")
        if current.get("family") == (primary or {}).get("family"):
            errors.append(f"{pid}: override has the same current and career family")
    if source == "career" and not primary:
        errors.append(f"{pid}: career display without a primary slot")
    if source == "none" and display.get("code") is not None:
        errors.append(f"{pid}: no-role display has a code")
    if display.get("code") and display.get("code") not in (roles_config.get("roles") or {}):
        errors.append(f"{pid}: display role code is unknown")


def main() -> int:
    if not SQUAD.exists():
        print(f"missing {SQUAD}")
        return 1
    squad = json.loads(SQUAD.read_text(encoding="utf-8"))
    players = squad.get("players", [])
    roles_config = yaml.safe_load(ROLES.read_text(encoding="utf-8"))
    errors: list[str] = []
    if not players:
        errors.append("squad payload is empty; run `uv run fitba squad` and republish")
    if not squad.get("attributes_meta"):
        errors.append("missing attributes_meta; run `uv run fitba squad` and republish")

    ids = [player.get("player_id") for player in players]
    keys = [player.get("player_key") for player in players]
    hrefs = _href_set(squad)
    if len(ids) != len(set(ids)):
        errors.append("duplicate player ids")
    if len(keys) != len(set(keys)):
        errors.append("duplicate player keys")
    if len(hrefs) != len(players):
        errors.append("duplicate or missing player hrefs")

    for player in players:
        pid = player.get("player_id")
        if player.get("href") != f"/players/{pid}/":
            errors.append(f"{pid}: href does not match /players/{pid}/")
        if player.get("status") not in VALID_STATUS:
            errors.append(f"{pid}: invalid status {player.get('status')!r}")
        if player.get("stats_coverage") not in VALID_COVERAGE:
            errors.append(f"{pid}: invalid coverage {player.get('stats_coverage')!r}")
        if "photo" in player:
            errors.append(f"{pid}: photo field must not be published")
        if "birth_date" in player:
            errors.append(f"{pid}: birth date must not be published")
        if not isinstance(player.get("attributes"), dict):
            errors.append(f"{pid}: missing preferred-foot block")
        role = player.get("role")
        playing = player.get("playing_time")
        if not isinstance(role, dict):
            errors.append(f"{pid}: missing role block")
        if not isinstance(playing, dict):
            errors.append(f"{pid}: missing playing-time block")
        if isinstance(role, dict) and isinstance(playing, dict):
            _check_playing_time(player, playing, errors)
            _check_role(player, role, playing, roles_config, errors)
        career = player.get("career_role")
        display = player.get("display_role")
        if not isinstance(career, dict):
            errors.append(f"{pid}: missing career-role block")
        if not isinstance(display, dict):
            errors.append(f"{pid}: missing display-role block")
        if isinstance(career, dict) and isinstance(display, dict):
            _check_career_role(player, career, display, roles_config, errors)
        status = player.get("status")
        loan = player.get("loan")
        if status == "squad" and loan is not None:
            errors.append(f"{pid}: squad player has a loan object")
        if status in {"loan_out", "loan_in"} and not (loan and loan.get("club")):
            errors.append(f"{pid}: loan player has no loan club")

        stats = player.get("stats", [])
        if any(row.get("scope") not in VALID_SCOPE for row in stats):
            errors.append(f"{pid}: invalid stat scope")
        if status == "loan_out":
            if any(row.get("scope") == "club" for row in stats):
                errors.append(f"{pid}: loanee has parent-club rows in primary stats")
            if player.get("stats_coverage") == "available" and not any(
                row.get("scope") == "loan" for row in stats
            ):
                errors.append(f"{pid}: loan coverage available with no loan rows")
        elif any(row.get("scope") != "club" for row in stats):
            errors.append(f"{pid}: squad player has non-club rows in primary stats")

        position_rows = player.get("position_stats", [])
        competitions = [row.get("competition") for row in position_rows]
        if len(competitions) != len(set(competitions)):
            errors.append(f"{pid}: duplicate position-stat competitions")
        position_totals = player.get("position_totals")
        if position_rows and position_totals is None:
            errors.append(f"{pid}: position rows without position totals")
        if not position_rows and position_totals is not None:
            errors.append(f"{pid}: position totals without position rows")
        if position_totals is not None:
            for field in POSITION_FIELDS:
                expected = sum(int(row.get(field) or 0) for row in position_rows)
                if int(position_totals.get(field) or 0) != expected:
                    errors.append(f"{pid}: position totals {field} mismatch")
        if player.get("position_stats_coverage") not in {
            "available",
            "partial",
            "unavailable",
            "no_matches",
        }:
            errors.append(f"{pid}: invalid position stats coverage")

        totals = player.get("totals")
        if player.get("stats_coverage") == "unavailable":
            if totals is not None:
                errors.append(f"{pid}: unavailable coverage has non-null totals")
        else:
            if totals is None:
                errors.append(f"{pid}: available coverage has null totals")
            else:
                for field in TOTAL_FIELDS:
                    expected = sum(int(row.get(field) or 0) for row in stats)
                    if int(totals.get(field) or 0) != expected:
                        errors.append(f"{pid}: totals {field} mismatch")

    summary = squad.get("summary", {})
    expected = {
        "total_players": len(players),
        "squad_size": sum(1 for player in players if player.get("status") != "loan_out"),
        "loans_out": sum(1 for player in players if player.get("status") == "loan_out"),
        "loans_in": sum(1 for player in players if player.get("status") == "loan_in"),
        "stats_unavailable": sum(
            1 for player in players if player.get("stats_coverage") == "unavailable"
        ),
        "attributes_foot_known": sum(
            1
            for player in players
            if (player.get("attributes") or {}).get("preferred_foot", {}).get("status") == "known"
        ),
        "attributes_unknown": sum(
            1 for player in players if (player.get("attributes") or {}).get("coverage") == "unknown"
        ),
        "attributes_conflicts": sum(
            1
            for player in players
            if (player.get("attributes") or {}).get("coverage") == "conflict"
        ),
        "roles_observed": sum(
            1 for player in players if (player.get("role") or {}).get("status") == "observed"
        ),
        "roles_partial": sum(
            1 for player in players if (player.get("role") or {}).get("status") == "partial"
        ),
        "roles_unknown": sum(
            1 for player in players if (player.get("role") or {}).get("status") == "unknown"
        ),
        "playing_time_available": sum(
            1
            for player in players
            if (player.get("playing_time") or {}).get("coverage") == "available"
        ),
        "playing_time_unavailable": sum(
            1
            for player in players
            if (player.get("playing_time") or {}).get("coverage")
            in {"unavailable", "not_applicable"}
        ),
        "career_roles_observed": sum(
            1 for player in players if (player.get("career_role") or {}).get("status") == "observed"
        ),
        "career_roles_low_evidence": sum(
            1
            for player in players
            if (player.get("career_role") or {}).get("status") == "low_evidence"
        ),
        "career_roles_mixed": sum(
            1 for player in players if (player.get("career_role") or {}).get("status") == "mixed"
        ),
        "career_roles_unknown": sum(
            1 for player in players if (player.get("career_role") or {}).get("status") == "unknown"
        ),
        "career_roles_unavailable": sum(
            1
            for player in players
            if (player.get("career_role") or {}).get("status") == "unavailable"
        ),
        "display_overrides": sum(
            1
            for player in players
            if (player.get("display_role") or {}).get("source") == "aberdeen_override"
        ),
    }
    for field, value in expected.items():
        if summary.get(field) != value:
            errors.append(f"summary {field}: {summary.get(field)} != {value}")
    if sum((summary.get("by_position") or {}).values()) != len(players):
        errors.append("summary by_position does not sum to players")
    if sum((summary.get("by_role_family") or {}).values()) != len(players):
        errors.append("summary by_role_family does not sum to players")
    if sum((summary.get("by_role_family_squad") or {}).values()) != summary.get("squad_size"):
        errors.append("summary by_role_family_squad does not sum to the squad")
    if sum((summary.get("by_primary_group") or {}).values()) != len(players):
        errors.append("summary by_primary_group does not sum to players")
    if sum((summary.get("by_primary_side") or {}).values()) != len(players):
        errors.append("summary by_primary_side does not sum to players")
    if sum((summary.get("by_status") or {}).values()) != len(players):
        errors.append("summary by_status does not sum to players")
    own_goals = sum(
        int((player.get("position_totals") or {}).get("own_goals") or 0) for player in players
    )
    if summary.get("own_goals_total") != own_goals:
        errors.append("summary own_goals_total does not match player rows")
    if summary.get("position_stats_coverage") not in {
        "available",
        "partial",
        "unavailable",
    }:
        errors.append("summary has invalid position_stats_coverage")
    meta = squad.get("position_stats_meta") or {}
    if meta.get("coverage") not in {"available", "partial", "unavailable"}:
        errors.append("position_stats_meta has invalid coverage")
    total = int(meta.get("fixtures_total") or 0)
    covered = int(meta.get("fixtures_covered") or 0)
    if covered > total:
        errors.append("position stats covered more fixtures than total")
    if summary.get("fixtures_total") != total:
        errors.append("summary fixtures_total does not match metadata")
    if summary.get("fixtures_covered") != covered:
        errors.append("summary fixtures_covered does not match metadata")
    expected_coverage = (
        "available" if total and covered == total else "partial" if covered else "unavailable"
    )
    if meta.get("coverage") != expected_coverage:
        errors.append("position stats coverage does not match fixture counts")

    role_meta = squad.get("role_meta") or {}
    if role_meta.get("role_coverage") not in VALID_ROLE_COVERAGE:
        errors.append("role_meta has invalid role_coverage")
    if summary.get("role_coverage") != role_meta.get("role_coverage"):
        errors.append("summary role_coverage does not match role_meta")
    if role_meta.get("fixtures_with_grid", 0) > role_meta.get("fixtures_total", 0):
        errors.append("role_meta grid fixtures exceed total fixtures")
    if role_meta.get("starts_with_role", 0) > role_meta.get("starts_total", 0):
        errors.append("role_meta starts_with_role exceeds starts_total")

    for path, where in (
        (TRANSFERS, "transfers"),
        (RUMOURS, "rumours"),
        (PROFILE, "profile"),
        (FORUM, "forum"),
        (CLUB, "club"),
    ):
        payload = _load(path)
        if payload is not None:
            _check_hrefs(payload, hrefs, where, errors)

    if errors:
        print("Squad publication check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        "Squad publication check passed "
        f"({len(players)} players, {summary.get('squad_size', 0)} squad, "
        f"{summary.get('loans_out', 0)} loans out, "
        f"{summary.get('stats_unavailable', 0)} coverage gaps, "
        f"{len(hrefs)} player links)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
