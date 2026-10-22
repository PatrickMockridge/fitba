"""Pure transfer-register completeness audit.

The audit is deliberately report-only. It produces a review queue from data we
already hold; it does not claim that a row is missing. A reviewer resolves each
row against AFC, API-Football or Wikipedia and records accepted gaps in
``reference/transfer_gaps.yaml``.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

SENIORITIES = {"established", "fringe", "youth", "unclassified"}
GAP_STATUSES = {"open", "accepted", "resolved"}
VERIFICATION_AIDS = {"manual_third_party", "allowed_source", "none"}
AUDIT_WINDOWS = {"summer", "winter", "other"}


def _player_id(player_key: str | None) -> int | None:
    key = str(player_key or "")
    if not key.startswith("api:player:"):
        return None
    tail = key.rsplit(":", 1)[-1]
    return int(tail) if tail.isdigit() else None


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _seniority_config(config: dict[str, Any]) -> dict[str, Any]:
    return (config.get("audit") or {}).get("seniority") or {}


def classify_seniority(
    player: dict[str, Any],
    config: dict[str, Any],
    prior: dict[str, Any] | None = None,
) -> str:
    """Classify a current squad player or a prior-season snapshot row.

    Established: 5+ starts or 450+ minutes in the reference season, 10+ career
    starts with role evidence, or a first-team number with an appearance.
    Youth: under-21 with fewer than five appearances and under 10 career starts.
    """
    rules = _seniority_config(config)
    min_starts = _int(rules.get("established_min_starts") or 5)
    min_minutes = _int(rules.get("established_min_minutes") or 450)
    min_career = _int(rules.get("established_min_career_starts") or 10)
    youth_age = _int(rules.get("youth_max_age") or 20)
    youth_apps = _int(rules.get("youth_max_appearances") or 4) + 1

    age = player.get("age")
    if age is None and prior is not None:
        age = prior.get("age")
    number = player.get("number")

    if prior is not None:
        starts = _int(prior.get("starts"))
        appearances = max(_int(prior.get("appearances")), starts)
        minutes = _int(prior.get("minutes"))
        career_starts = 0
    else:
        playing_time = player.get("playing_time") or {}
        starts = _int(playing_time.get("starts"))
        appearances = starts + _int(playing_time.get("sub_apps"))
        minutes = _int(playing_time.get("minutes"))
        career = player.get("career_role") or {}
        career_starts = max(
            _int(career.get("starts_with_role")),
            _int((career.get("dominant") or {}).get("starts")),
        )

    if (
        age is not None
        and int(age) <= youth_age
        and appearances < youth_apps
        and career_starts < min_career
    ):
        return "youth"
    if starts >= min_starts or minutes >= min_minutes or career_starts >= min_career:
        return "established"
    if number is not None and appearances >= 1:
        return "established"
    if number is not None or appearances >= 1 or minutes >= 1 or starts >= 1:
        return "fringe"
    return "unclassified"


def _gap_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "player_key": row.get("player_key"),
        "player_name": row.get("player_name"),
        "direction": row.get("direction"),
        "season": row.get("season"),
        "window": row.get("window"),
        "seniority": row.get("seniority") or "unclassified",
        "status": row.get("status") or "open",
        "reason": row.get("reason"),
        "verification_aid": row.get("verification_aid") or "none",
        "checked_at": row.get("checked_at"),
        "transfer_id": row.get("transfer_id"),
    }


def build_transfer_audit(
    *,
    players: list[dict[str, Any]],
    prior_seasons: list[dict[str, Any]],
    transfers: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
    config: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    """Build the audit document from local data only."""
    audit_cfg = config.get("audit") or {}
    audit_start = str(audit_cfg.get("start_season") or "2024-25")
    gap_rows = [_gap_payload(row) for row in gaps or []]
    if not prior_seasons:
        return {
            "generated_at": generated_at,
            "audit_start": audit_start,
            "status": "unavailable",
            "snapshot_at": None,
            "summary": {
                "needs_review": {tier: 0 for tier in sorted(SENIORITIES)},
                "gaps": {status: 0 for status in sorted(GAP_STATUSES)},
                "positions": {"specified": 0, "unknown": 0},
            },
            "current_squad_arrivals": [],
            "prior_departures": [],
            "candidate_review": [],
            "windows": [],
            "gaps": gap_rows,
        }

    current_ids = {
        int(player["player_id"]) for player in players if player.get("player_id") is not None
    }
    prior_by_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in prior_seasons:
        pid = _int(row.get("player_id"))
        if pid:
            prior_by_id[pid].append(row)

    in_rows = [row for row in transfers if row.get("direction") == "in"]
    out_rows = [row for row in transfers if row.get("direction") == "out"]
    registered_in_keys = {str(row.get("player_key")) for row in in_rows}
    out_seasons: dict[str, list[str]] = defaultdict(list)
    for row in out_rows:
        out_seasons[str(row.get("player_key"))].append(str(row.get("season") or ""))
    loan_in_keys = {
        str(row.get("player_key")) for row in in_rows if row.get("transfer_kind") == "loan"
    }
    covered_in_keys = {
        str(row.get("player_key"))
        for row in gap_rows
        if row.get("direction") == "in" and row.get("status") in {"accepted", "resolved"}
    }
    covered_out_keys = {
        str(row.get("player_key"))
        for row in gap_rows
        if row.get("direction") == "out" and row.get("status") in {"accepted", "resolved"}
    }

    arrivals: list[dict[str, Any]] = []
    for player in players:
        key = str(player.get("player_key"))
        pid = _int(player.get("player_id"))
        if key in registered_in_keys or key in covered_in_keys or prior_by_id.get(pid):
            continue
        arrivals.append(
            {
                "player_key": key,
                "player_name": player.get("name"),
                "seniority": classify_seniority(player, config),
                "reason": "no registered arrival and no prior-season snapshot row",
            }
        )

    departures: list[dict[str, Any]] = []
    for pid, rows in prior_by_id.items():
        if pid in current_ids:
            continue
        latest = max(rows, key=lambda row: str(row.get("season") or ""))
        key = f"api:player:{pid}"
        if key in covered_out_keys:
            continue
        if any(season >= str(latest.get("season") or "") for season in out_seasons.get(key, [])):
            continue
        # A loan-in that ended is not a missing permanent departure.
        if key in loan_in_keys:
            continue
        departures.append(
            {
                "player_key": key,
                "player_name": latest.get("player_name"),
                "season": latest.get("season"),
                "seniority": classify_seniority({}, config, prior=latest),
                "reason": "prior-season player has no out row after that season",
            }
        )

    published_ids = {str(row.get("transfer_id")) for row in transfers}
    published_keys = {
        (str(row.get("player_key")), str(row.get("direction")), str(row.get("season")))
        for row in transfers
    }
    candidate_counts: Counter[tuple[str, str]] = Counter()
    for row in candidates or []:
        if row.get("verification_status") != "feed_only":
            continue
        if str(row.get("transfer_id")) in published_ids:
            continue
        key = (
            str(row.get("player_key")),
            str(row.get("direction")),
            str(row.get("season")),
        )
        if key in published_keys:
            continue
        if row.get("window") not in AUDIT_WINDOWS:
            continue
        if str(row.get("season") or "") < audit_start:
            continue
        candidate_counts[(str(row.get("season")), str(row.get("window")))] += 1

    windows: dict[tuple[str, str], dict[str, Any]] = {}
    for row in transfers:
        key = (str(row.get("season")), str(row.get("window")))
        bucket = windows.setdefault(
            key,
            {
                "key": f"{key[0]}-{key[1]}",
                "season": key[0],
                "window": key[1],
                "arrivals": 0,
                "departures": 0,
                "position_unknown": 0,
            },
        )
        if row.get("direction") == "in":
            bucket["arrivals"] += 1
        elif row.get("direction") == "out":
            bucket["departures"] += 1
        if not row.get("position") or row.get("position_source") == "unknown":
            bucket["position_unknown"] += 1

    gap_counts = Counter(row["status"] for row in gap_rows)
    needs_review = Counter(row["seniority"] for row in arrivals + departures)
    positions_unknown = sum(1 for row in transfers if not row.get("position"))
    snapshot_at = max((str(row.get("snapshot_at") or "") for row in prior_seasons), default="")

    return {
        "generated_at": generated_at,
        "audit_start": audit_start,
        "status": "ok",
        "snapshot_at": snapshot_at or None,
        "summary": {
            "needs_review": {tier: needs_review.get(tier, 0) for tier in sorted(SENIORITIES)},
            "gaps": {status: gap_counts.get(status, 0) for status in sorted(GAP_STATUSES)},
            "positions": {
                "specified": len(transfers) - positions_unknown,
                "unknown": positions_unknown,
            },
        },
        "current_squad_arrivals": sorted(
            arrivals, key=lambda row: (row["seniority"], row["player_name"] or "")
        ),
        "prior_departures": sorted(
            departures, key=lambda row: (row["seniority"], row["player_name"] or "")
        ),
        "candidate_review": [
            {
                "key": f"{season}-{window}",
                "season": season,
                "window": window,
                "count": count,
            }
            for (season, window), count in sorted(candidate_counts.items())
        ],
        "windows": sorted(windows.values(), key=lambda row: row["key"], reverse=True),
        "gaps": sorted(
            gap_rows,
            key=lambda row: (
                row["seniority"],
                row["status"],
                str(row.get("player_name") or ""),
            ),
        ),
    }
