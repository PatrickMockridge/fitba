#!/usr/bin/env python3
"""CI guard for career role evidence, aggregates and the published eligibility.

The current-season role guard (`check_roles.py`) remains separate. This guard
checks the historical/career layer, the FM-style position slots, the
primary/secondary/stretch tiers and the display-role decision.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import polars as pl
import yaml

from fitba.normalize.career import (
    formation_policy_version,
    policy_version,
    season_weights,
    slot_for_role,
)
from fitba.normalize.roles import role_family, validate_config
from fitba.settings import aberdeen as aberdeen_config
from fitba.settings import source_ids as source_ids_config
from fitba.util.dates import current_season

ROOT = Path(__file__).resolve().parents[1]
ROLES = ROOT / "config" / "roles.yaml"
ROLE_NOTES = ROOT / "reference" / "role_notes.yaml"
CAREER = ROOT / "data" / "normalized" / "career"
SQUAD = ROOT / "web" / "data" / "generated" / "squad" / "aberdeen.json"
ROLE_ROWS = ROOT / "data" / "normalized" / "matches" / "player_roles.parquet"
VALID_SCOPES = {"aberdeen", "previous_club", "loan_club", "national_team", "unknown"}
VALID_STATES = {
    "complete",
    "partial_lineups",
    "capped",
    "no_fixtures",
    "no_starts",
    "no_stats_entry",
    "budget",
    "error",
}
VALID_CAREER_STATUS = {"observed", "low_evidence", "mixed", "unknown", "unavailable"}
VALID_DISPLAY = {
    "career",
    "aberdeen_override",
    "current_season",
    "career_low_evidence",
    "none",
}


def _load_parquet(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    frame = pl.read_parquet(path)
    return frame.to_dicts() if frame.height else []


def _check_evidence(
    rows: list[dict[str, Any]], config: dict[str, Any], policy: str, errors: list[str]
) -> None:
    seen: set[tuple[int, int, int]] = set()
    roles = config.get("roles") or {}
    for row in rows:
        pid = row.get("player_id")
        key = (int(pid), int(row.get("fixture_id") or 0), int(row.get("team_id") or 0))
        if key in seen:
            errors.append(f"{pid}: duplicate career evidence {key}")
        seen.add(key)
        if row.get("scope") not in VALID_SCOPES:
            errors.append(f"{pid}: invalid career scope {row.get('scope')!r}")
        if row.get("policy_version") != policy:
            errors.append(f"{pid}: career evidence uses a stale policy version")
        code = row.get("role_code")
        if row.get("role_status") == "observed":
            if not code:
                errors.append(f"{pid}: observed career row has no role code")
            elif code not in roles:
                errors.append(f"{pid}: unknown career role {code!r}")
            elif row.get("role_family") != role_family(config, str(code)):
                errors.append(f"{pid}: career role family mismatch")
            slot, _ = slot_for_role(config, str(code))
            if not slot:
                errors.append(f"{pid}: role {code!r} has no career slot")
        elif row.get("role_status") == "unknown":
            if code:
                errors.append(f"{pid}: unknown career row has a role code")
        else:
            errors.append(f"{pid}: invalid career role status {row.get('role_status')!r}")


def _check_aggregates(
    evidence: list[dict[str, Any]],
    aggregates: list[dict[str, Any]],
    config: dict[str, Any],
    current: str,
    errors: list[str],
) -> None:
    weights = season_weights(config, current)
    counts: dict[tuple[Any, ...], int] = defaultdict(int)
    for row in evidence:
        if not row.get("role_code"):
            continue
        counts[
            (
                int(row["player_id"]),
                str(row["season"]),
                row.get("team_id"),
                row.get("scope"),
                row.get("league_id"),
                row.get("competition"),
                row.get("role_code"),
            )
        ] += 1
    aggregate_counts: dict[tuple[Any, ...], int] = defaultdict(int)
    for row in aggregates:
        key = (
            int(row["player_id"]),
            str(row["season"]),
            row.get("team_id"),
            row.get("scope"),
            row.get("league_id"),
            row.get("competition"),
            row.get("role_code"),
        )
        starts = int(row.get("starts") or 0)
        aggregate_counts[key] += starts
        weight = float(weights.get(str(row.get("season")), 0.0))
        expected_weighted = starts * weight
        if abs(float(row.get("weighted_starts") or 0) - expected_weighted) > 0.001:
            errors.append(f"{row['player_id']}: weighted_starts mismatch")
    if counts != aggregate_counts:
        errors.append("career aggregate starts do not match evidence")


def _check_state(
    state: list[dict[str, Any]], config: dict[str, Any], policy: str, errors: list[str]
) -> None:
    for row in state:
        pid = row.get("player_id")
        if row.get("status") not in VALID_STATES:
            errors.append(f"{pid}: invalid career state {row.get('status')!r}")
        if row.get("policy_version") != policy:
            errors.append(f"{pid}: career state uses a stale policy version")
        if int(row.get("fixtures_checked") or 0) > int(row.get("fixtures_total") or 0):
            errors.append(f"{pid}: career fixtures_checked exceeds total")
        if int(row.get("starts_with_role") or 0) > int(row.get("starts_seen") or 0):
            errors.append(f"{pid}: career starts_with_role exceeds starts_seen")
        if row.get("scope") not in VALID_SCOPES:
            errors.append(f"{pid}: invalid state scope")


def _check_slots(player: dict[str, Any], config: dict[str, Any], errors: list[str]) -> None:
    pid = player.get("player_id")
    career = player.get("career_role") or {}
    display = player.get("display_role") or {}
    status = career.get("status")
    if status not in VALID_CAREER_STATUS:
        errors.append(f"{pid}: invalid career status {status!r}")
    slots_cfg = (config.get("career") or {}).get("slots") or {}
    slots = career.get("slots") or []
    total_starts = 0
    total_share = 0.0
    for row in slots:
        if row.get("slot") not in slots_cfg:
            errors.append(f"{pid}: published slot {row.get('slot')!r} is unknown")
        total_starts += int(row.get("starts") or 0)
        total_share += float(row.get("share") or 0)
        if row.get("tier") not in {"primary", "secondary", "stretch", "other"}:
            errors.append(f"{pid}: invalid published tier {row.get('tier')!r}")
    if slots and abs(total_share - 1.0) > 0.001:
        errors.append(f"{pid}: published slot shares do not sum to 1")
    if total_starts != int(career.get("starts_with_role") or 0):
        errors.append(f"{pid}: published slot starts do not match starts_with_role")
    primary = career.get("primary_slot")
    if status in {"observed", "low_evidence", "mixed"} and not primary:
        errors.append(f"{pid}: career status has no primary slot")
    if primary:
        if primary.get("slot") not in slots_cfg:
            errors.append(f"{pid}: primary slot is unknown")
        if primary.get("code") not in (config.get("roles") or {}):
            errors.append(f"{pid}: primary role code is unknown")
        if primary.get("family") != role_family(config, primary.get("code")):
            errors.append(f"{pid}: primary role family mismatch")
    source = display.get("source")
    if source not in VALID_DISPLAY:
        errors.append(f"{pid}: invalid display source {source!r}")
    if source == "career" and not primary:
        errors.append(f"{pid}: career display has no primary")
    if source == "aberdeen_override":
        current = player.get("role") or {}
        if current.get("status") not in {"observed", "partial"}:
            errors.append(f"{pid}: override without established current role")
        if current.get("family") == (primary or {}).get("family"):
            errors.append(f"{pid}: override has the same family")
    if source == "none" and display.get("code") is not None:
        errors.append(f"{pid}: none display has a code")


def _check_role_notes(players: list[dict[str, Any]], errors: list[str]) -> None:
    if not ROLE_NOTES.exists():
        errors.append("reference/role_notes.yaml is missing")
        return
    payload = yaml.safe_load(ROLE_NOTES.read_text(encoding="utf-8")) or {}
    keys = {str(player.get("player_key")) for player in players}
    valid_types = {
        "inside_forward",
        "inverted_full_back",
        "utility",
        "tactical_usage",
        "position_change",
    }
    for row in payload.get("players", []) or []:
        key = str(row.get("player_key") or "")
        if key not in keys:
            errors.append(f"role note uses unknown player_key {key!r}")
        if row.get("note_type") not in valid_types:
            errors.append(f"role note {key}: invalid note_type {row.get('note_type')!r}")
        if not str(row.get("note") or "").strip():
            errors.append(f"role note {key}: empty note")
        source = str(row.get("source") or "")
        source_ok = source.startswith(("http://", "https://")) or (
            source.startswith("docs/") and (ROOT / source).exists()
        )
        if not source_ok:
            errors.append(f"role note {key}: missing or invalid source")
        if not row.get("verified_at"):
            errors.append(f"role note {key}: missing verified_at")


def _check_published(config: dict[str, Any], errors: list[str]) -> int:
    if not SQUAD.exists():
        errors.append("squad payload is missing")
        return 0
    payload = json.loads(SQUAD.read_text(encoding="utf-8"))
    players = payload.get("players", [])
    for player in players:
        _check_slots(player, config, errors)
    return len(players)


def _check_current_crosswalk(
    evidence: list[dict[str, Any]], config: dict[str, Any], errors: list[str]
) -> None:
    team_id = int(source_ids_config()["teams"][aberdeen_config()["club_id"]]["api_football"])
    role_rows = _load_parquet(ROLE_ROWS)
    expected: dict[tuple[int, str], int] = defaultdict(int)
    for row in role_rows:
        if int(row.get("team_id") or 0) == team_id:
            expected[(int(row["player_id"]), str(row["role_code"]))] += int(row.get("starts") or 0)
    actual: dict[tuple[int, str], int] = defaultdict(int)
    for row in evidence:
        if (
            row.get("scope") == "aberdeen"
            and str(row.get("season")) == current_season()
            and row.get("role_code")
        ):
            actual[(int(row["player_id"]), str(row["role_code"]))] += 1
    if expected != actual:
        errors.append("current Aberdeen career evidence does not match player_roles")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--published-only", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    config = yaml.safe_load(ROLES.read_text(encoding="utf-8"))
    try:
        validate_config(config)
    except ValueError as exc:
        errors.append(f"role config: {exc}")
    policy = policy_version(config)
    evidence_policy = formation_policy_version(config)
    current = current_season()
    evidence: list[dict[str, Any]] = []
    if not args.published_only:
        evidence = _load_parquet(CAREER / "player_role_evidence.parquet")
        aggregates = _load_parquet(CAREER / "player_career_roles.parquet")
        state = _load_parquet(CAREER / "career_backfill_state.parquet")
        _check_evidence(evidence, config, evidence_policy, errors)
        _check_aggregates(evidence, aggregates, config, current, errors)
        _check_state(state, config, policy, errors)
        _check_current_crosswalk(evidence, config, errors)
        meta_path = CAREER / "career_roles_meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        for scan in meta.get("club_scans", []) or []:
            if int(scan.get("fixtures_checked") or 0) > int(scan.get("fixtures_total") or 0):
                errors.append(f"club scan {scan.get('season')}: checked exceeds total")
            if int(scan.get("starts_found") or 0) < 0:
                errors.append(f"club scan {scan.get('season')}: negative starts")
    players = _check_published(config, errors)
    published_players = (
        json.loads(SQUAD.read_text(encoding="utf-8")).get("players", []) if SQUAD.exists() else []
    )
    _check_role_notes(published_players, errors)
    if errors:
        print("Career role check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(
        "Career role check passed "
        f"({players} published players, {len(evidence)} evidence rows, "
        f"policy {policy})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
