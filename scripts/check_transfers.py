#!/usr/bin/env python3
"""CI guard for the published transfers payload and completeness audit.

Structural problems fail the guard. Open completeness gaps are reported but do
not fail: the audit is deliberately report-only, with seniority deciding how
prominently a gap is shown.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

from fitba.ingest.transfers import withheld_transfers
from fitba.settings import sell_on_clauses as sell_on_config
from fitba.settings import transfer_plausibility as plausibility_config
from fitba.validate.source_policy import is_blocked_url, no_publication_tokens

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "web" / "data" / "generated" / "transfers" / "aberdeen.json"
AUDIT = ROOT / "web" / "data" / "generated" / "transfers" / "aberdeen.audit.json"
GAPS = ROOT / "reference" / "transfer_gaps.yaml"
POSITIONS = ROOT / "reference" / "transfer_player_positions.yaml"

POSITION_SOURCES = {"curated", "squad", "api_player_stats", "career_role", "unknown"}
UNKNOWN_REASONS = {
    "no_allowed_source",
    "player_not_found",
    "youth_no_profile",
    "conflicting_sources",
    "budget",
    "historical_scope",
}
SENIORITIES = {"established", "fringe", "youth"}
GAP_STATUSES = {"open", "accepted", "resolved"}
VERIFICATION_AIDS = {"manual_third_party", "allowed_source", "none"}
REQUIRED_MOVES = [
    ("api:player:303519", "in", "2026-27", "summer"),  # Mouloua
    ("api:player:44982", "in", "2026-27", "summer"),  # Lewis Smith
    ("api:player:394703", "in", "2025-26", "summer"),  # Frame
    ("api:player:20323", "in", "2025-26", "other"),  # Bwomono
    ("api:player:195870", "out", "2026-27", "summer"),  # Keskinen
    ("api:player:373297", "out", "2026-27", "summer"),  # Kjartansson
    ("api:player:137129", "out", "2025-26", "winter"),  # Aouchiche loan return
    ("api:player:15644", "out", "2025-26", "other"),  # Nilsen
    ("api:player:350876", "out", "2025-26", "winter"),  # Polvara
]


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def main() -> int:
    if not PAYLOAD.exists():
        print(f"missing {PAYLOAD}")
        return 1
    data = _load(PAYLOAD)
    rows = data.get("transfers", [])
    windows = data.get("windows", [])
    groups = data.get("window_groups") or {}
    errors: list[str] = []
    warnings: list[str] = []

    ids = [row.get("transfer_id") for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("duplicate transfer ids")

    blocked_ids, blocked_hosts = no_publication_tokens()
    for row in rows:
        transfer_id = row.get("transfer_id")
        if row.get("verification_status") not in {"confirmed", "curated"}:
            errors.append(f"{transfer_id}: status {row.get('verification_status')}")
        if not row.get("source_urls"):
            errors.append(f"{transfer_id}: no source URLs")
        for url in row.get("source_urls") or []:
            if is_blocked_url(str(url), blocked_hosts):
                errors.append(f"{transfer_id}: source not allowed for publication {url!r}")
        for source_id in row.get("source_ids") or []:
            if source_id in blocked_ids:
                errors.append(f"{transfer_id}: source not allowed for publication {source_id!r}")
        if row.get("fee_amount") == 0:
            errors.append(f"{transfer_id}: fee amount is zero")
        if row.get("fee_status") == "undisclosed" and row.get("fee_display") != "Undisclosed":
            errors.append(f"{transfer_id}: undisclosed fee display mismatch")
        if row.get("fee_status") == "free" and row.get("fee_display") != "Free":
            errors.append(f"{transfer_id}: free fee display mismatch")
        if row.get("fee_status") == "loan" and row.get("fee_display") != "Loan":
            errors.append(f"{transfer_id}: loan fee display mismatch")

        position = row.get("position")
        source = row.get("position_source")
        reason = row.get("position_unknown_reason")
        if source not in POSITION_SOURCES:
            errors.append(f"{transfer_id}: invalid position source {source!r}")
        if position and not source:
            errors.append(f"{transfer_id}: position has no source")
        if not position:
            if source != "unknown":
                errors.append(f"{transfer_id}: missing position is not marked unknown")
            if reason not in UNKNOWN_REASONS:
                errors.append(f"{transfer_id}: missing position reason {reason!r}")

        estimate = row.get("fee_estimate") or {}
        basis = estimate.get("basis")
        if basis not in {"disclosed", "reported", "free", "loan", "modelled", "unknown"}:
            errors.append(f"{transfer_id}: invalid fee basis {basis!r}")
        fee_low = estimate.get("fee_low_gbp")
        fee_high = estimate.get("fee_high_gbp")
        if fee_low is not None and fee_low < 0:
            errors.append(f"{transfer_id}: negative fee low")
        if fee_high is not None and fee_high < 0:
            errors.append(f"{transfer_id}: negative fee high")
        if fee_low is not None and fee_high is not None and fee_low > fee_high:
            errors.append(f"{transfer_id}: fee range reversed")
        if basis in {"disclosed", "reported"} and not estimate.get("source_urls"):
            errors.append(f"{transfer_id}: {basis} fee has no source")
        if basis == "loan" and (fee_low is not None or fee_high is not None):
            errors.append(f"{transfer_id}: loan fee should be unknown")
        if basis == "free" and (fee_low != 0 or fee_high != 0):
            errors.append(f"{transfer_id}: free transfer should have zero fee")
        if basis == "modelled" and estimate.get("confidence") not in {"low", "medium"}:
            errors.append(f"{transfer_id}: modelled fee confidence {estimate.get('confidence')!r}")

    if data.get("summary", {}).get("total") != len(rows):
        errors.append("summary total does not match rows")

    for window in windows:
        if window.get("disclosed_spend", 0) < 0 or window.get("disclosed_income", 0) < 0:
            errors.append(f"{window.get('key')}: negative disclosed fee total")

    window_keys = {window.get("key") for window in windows}
    grouped: list[str] = []
    for group_name in ("recent", "further", "out_of_window", "upcoming"):
        for key in groups.get(group_name) or []:
            grouped.append(key)
            if key not in window_keys:
                errors.append(f"window group {group_name}: unknown key {key!r}")
            window = next((item for item in windows if item.get("key") == key), {})
            if group_name == "out_of_window" and window.get("window") != "other":
                errors.append(f"window group out_of_window: {key!r} is not an other window")
            if group_name != "out_of_window" and window.get("window") == "other":
                errors.append(f"window group {group_name}: {key!r} is an other window")
            if group_name == "upcoming" and window.get("state") != "upcoming":
                errors.append(f"window group upcoming: {key!r} is not upcoming")
            if group_name in {"recent", "further"} and window.get("state") == "upcoming":
                errors.append(f"window group {group_name}: {key!r} is upcoming")
    if len(grouped) != len(set(grouped)):
        errors.append("a window appears in more than one group")
    if set(grouped) != window_keys:
        errors.append("window groups do not cover every published window")
    recent = [
        next((item for item in windows if item.get("key") == key), {})
        for key in groups.get("recent") or []
    ]
    if len(recent) < 4:
        errors.append("recent group has fewer than four windows")
    if sum(1 for window in recent if window.get("window") == "summer") < 2:
        errors.append("recent group has fewer than two summer windows")
    if sum(1 for window in recent if window.get("window") == "winter") < 2:
        errors.append("recent group has fewer than two winter windows")

    for player_key, direction, season, window in REQUIRED_MOVES:
        matches = [
            row
            for row in rows
            if row.get("player_key") == player_key
            and row.get("direction") == direction
            and row.get("season") == season
            and row.get("window") == window
        ]
        if len(matches) != 1:
            errors.append(
                f"required move {player_key} {direction} {season} {window} has {len(matches)} rows"
            )

    positions = _load_yaml(POSITIONS) if POSITIONS.exists() else {}
    for row in positions.get("players", []) or []:
        key = row.get("player_key")
        if not row.get("position"):
            errors.append(f"position register {key}: no position")
        if not row.get("source_urls"):
            errors.append(f"position register {key}: no source URLs")
        if not row.get("verified_at"):
            errors.append(f"position register {key}: no verified_at")
        for url in row.get("source_urls") or []:
            if is_blocked_url(str(url), blocked_hosts):
                errors.append(
                    f"position register {key}: source not allowed for publication {url!r}"
                )

    gaps_payload = _load_yaml(GAPS) if GAPS.exists() else {}
    gap_rows = gaps_payload.get("gaps", []) or []
    for row in gap_rows:
        label = row.get("player_key") or row.get("player_name") or "gap"
        if row.get("seniority") not in SENIORITIES:
            errors.append(f"{label}: invalid gap seniority {row.get('seniority')!r}")
        if row.get("status") not in GAP_STATUSES:
            errors.append(f"{label}: invalid gap status {row.get('status')!r}")
        if row.get("verification_aid") not in VERIFICATION_AIDS:
            errors.append(f"{label}: invalid verification_aid {row.get('verification_aid')!r}")
        if row.get("status") in {"accepted", "resolved"}:
            if not str(row.get("reason") or "").strip():
                errors.append(f"{label}: accepted/resolved gap has no reason")
            if not row.get("checked_at"):
                errors.append(f"{label}: accepted/resolved gap has no checked_at")
        if row.get("status") == "resolved" and not row.get("transfer_id"):
            errors.append(f"{label}: resolved gap has no transfer_id")
        for url in row.get("source_urls") or []:
            if is_blocked_url(str(url), blocked_hosts):
                errors.append(f"{label}: gap source not allowed for publication {url!r}")

    valuation = data.get("valuation") or {}
    if valuation:
        low = valuation.get("fee_low_gbp")
        high = valuation.get("fee_high_gbp")
        if low is not None and high is not None and low > high:
            errors.append("valuation net range is reversed")
        counts = valuation.get("counts") or {}
        if sum(int(value) for value in counts.values()) != len(rows):
            errors.append("valuation counts do not cover every transfer row")
        for side in ("spend", "income"):
            side_low = valuation.get(f"{side}_low_gbp")
            side_high = valuation.get(f"{side}_high_gbp")
            if side_low is not None and side_high is not None and side_low > side_high:
                errors.append(f"valuation {side} range is reversed")

    plausibility = data.get("plausibility") or {}
    accepted_rows = (plausibility_config() or {}).get("accepted", []) or []
    for row in accepted_rows:
        label = row.get("transfer_id") or "plausibility acceptance"
        if not row.get("reason") or not row.get("checked_at"):
            errors.append(f"{label}: accepted plausibility row needs reason and checked_at")
        if not row.get("source_urls"):
            errors.append(f"{label}: accepted plausibility row needs a public source")
        for url in row.get("source_urls") or []:
            if is_blocked_url(str(url), blocked_hosts):
                errors.append(f"{label}: plausibility source not allowed {url!r}")
    actual_withheld = len(withheld_transfers())
    if int(plausibility.get("withheld", -1)) != actual_withheld:
        errors.append("published plausibility withheld count is stale")

    clause_config = sell_on_config() or {}
    clause_rows = clause_config.get("clauses", []) or []
    clause_ids = [str(row.get("clause_id")) for row in clause_rows]
    if len(clause_ids) != len(set(clause_ids)):
        errors.append("duplicate sell-on clause ids")
    transfer_ids = {str(row.get("transfer_id")) for row in rows}
    for clause in clause_rows:
        label = clause.get("clause_id") or clause.get("player_name") or "sell-on"
        if clause.get("transfer_id") not in transfer_ids:
            errors.append(f"{label}: sell-on transfer_id not in register")
        pct = clause.get("sell_on_pct")
        if pct is not None and not (0 <= float(pct) <= 100):
            errors.append(f"{label}: sell-on percentage out of range")
        if clause.get("basis") not in {"profit", "gross_fee", "unknown"}:
            errors.append(f"{label}: invalid sell-on basis {clause.get('basis')!r}")
        if clause.get("confidence") not in {"confirmed", "reported", "unknown"}:
            errors.append(f"{label}: invalid sell-on confidence")
        if clause.get("confidence") == "confirmed" and not clause.get("source_urls"):
            errors.append(f"{label}: confirmed sell-on has no source URL")
        if clause.get("confidence") == "reported" and not (
            clause.get("source_urls") or clause.get("verification_aid") == "manual_third_party"
        ):
            errors.append(f"{label}: reported sell-on has no source or finding aid")
        for url in clause.get("source_urls") or []:
            if is_blocked_url(str(url), blocked_hosts):
                errors.append(f"{label}: sell-on source not allowed for publication {url!r}")
    published_clauses = data.get("sell_on_clauses") or []
    if {str(row.get("clause_id")) for row in published_clauses} != set(clause_ids):
        errors.append("published sell-on clauses do not match the register")
    sell_on_summary = data.get("sell_on_summary") or {}
    if int(sell_on_summary.get("total", 0)) != len(published_clauses):
        errors.append("sell-on summary total does not match clauses")

    if not AUDIT.exists():
        warnings.append("audit document is missing; run `fitba transfers --audit`")
    else:
        audit = _load(AUDIT)
        if audit.get("status") not in {"ok", "unavailable"}:
            errors.append(f"audit status {audit.get('status')!r}")
        summary = audit.get("summary") or {}
        needs = summary.get("needs_review") or {}
        audit_gaps = summary.get("gaps") or {}
        arrivals = audit.get("current_squad_arrivals") or []
        departures = audit.get("prior_departures") or []
        if sum(int(needs.get(tier, 0)) for tier in needs) != len(arrivals) + len(departures):
            errors.append("audit needs_review counts do not match review rows")
        if sum(int(audit_gaps.get(status, 0)) for status in audit_gaps) != len(
            audit.get("gaps") or []
        ):
            errors.append("audit gap counts do not match gap rows")
        audit_windows = {row.get("key") for row in audit.get("windows") or []}
        expected_audit_windows = {
            window["key"] for window in windows if window.get("state") != "upcoming"
        }
        if audit.get("status") == "ok" and audit_windows != expected_audit_windows:
            errors.append("audit windows do not match published non-upcoming windows")
        positions_summary = summary.get("positions") or {}
        if int(positions_summary.get("specified", 0)) + int(
            positions_summary.get("unknown", 0)
        ) != len(rows):
            errors.append("audit position counts do not match transfer rows")
        if audit.get("status") == "unavailable":
            warnings.append("audit snapshot is unavailable; run `fitba transfers --audit`")
        elif int((needs or {}).get("established", 0)):
            warnings.append(f"{needs.get('established')} established-senior move(s) need review")
        elif int((needs or {}).get("fringe", 0)):
            warnings.append(f"{needs.get('fringe')} fringe-senior move(s) need review")

    if errors:
        print("Transfer publication check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(
        f"Transfer publication check passed ({len(rows)} rows, "
        f"{data.get('summary', {}).get('confirmed', 0)} confirmed, "
        f"{len(windows)} windows)"
    )
    for warning in warnings:
        print(f"  warning: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
