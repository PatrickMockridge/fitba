"""Career role aggregation and display rules.

The career role is a distribution of starting appearances, not a single label.
Starts are equal-weighted by default across the configured seasons. The current
Aberdeen role only overrides the display label when it is clearly and obviously
different from the career record.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

from fitba.normalize.roles import (
    family_label,
    role_family,
    role_label,
    role_side,
)
from fitba.util.dates import previous_season, season_start_year


def career_seasons(current: str, count: int) -> list[str]:
    """Return the current season followed by the previous seasons."""
    seasons = [current]
    while len(seasons) < count:
        seasons.append(previous_season(seasons[-1]))
    return seasons


def season_weights(config: dict[str, Any], current: str) -> dict[str, float]:
    career = config.get("career") or {}
    seasons = career_seasons(current, int(career.get("seasons") or 1))
    weights = [float(value) for value in career.get("season_weights") or []]
    if len(weights) != len(seasons):
        weights = [1.0] * len(seasons)
    return dict(zip(seasons, weights, strict=True))


def policy_version(config: dict[str, Any]) -> str:
    payload = {
        "career": config.get("career") or {},
        "formations": config.get("formations") or {},
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:12]


def formation_policy_version(config: dict[str, Any]) -> str:
    """Policy version for role derivation only.

    Slot/override/eligibility changes do not invalidate a role observed from a
    formation grid; only a formation-map change does. Evidence rows use this
    version, while backfill state uses the full ``policy_version``.
    """
    encoded = json.dumps(config.get("formations") or {}, sort_keys=True, default=str).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()[:12]


def family_group(config: dict[str, Any], family: str | None) -> str | None:
    if not family:
        return None
    groups = (config.get("career") or {}).get("family_groups") or {}
    for name, members in groups.items():
        if family in members:
            return str(name)
    return None


def _family_order(config: dict[str, Any], family: str) -> int:
    return int(((config.get("families") or {}).get(family) or {}).get("order") or 999)


def _role_order(config: dict[str, Any], code: str) -> int:
    return int(((config.get("roles") or {}).get(code) or {}).get("order") or 999)


def slot_for_role(config: dict[str, Any], code: str | None) -> tuple[str | None, dict[str, Any]]:
    """Return the FM-style position slot for a role code."""
    if not code:
        return None, {}
    for key, slot in ((config.get("career") or {}).get("slots") or {}).items():
        if code in (slot.get("roles") or []):
            return str(key), slot
    return None, {}


def _share(value: float, total: float) -> float:
    return round(value / total, 4) if total else 0.0


def _fm_label(
    slot_rows: list[dict[str, Any]],
    *,
    tiers: set[str],
) -> str:
    """Build a readable FM-style label from slots, grouped by side."""
    side_order = {"centre": "C", "left": "L", "right": "R"}
    letters_by_side: dict[str, list[str]] = defaultdict(list)
    for row in slot_rows:
        if row.get("tier") not in tiers:
            continue
        fm = str(row.get("fm") or "")
        if not fm or fm == "GK":
            letters_by_side["GK"].append("GK")
            continue
        parts = fm.split(" ", 1)
        letters = parts[0].split("/")
        side = side_order.get(str(row.get("side") or ""), "")
        for letter in letters:
            if letter not in letters_by_side[side]:
                letters_by_side[side].append(letter)
    pieces: list[str] = []
    for side in ("C", "L", "R", "GK"):
        letters = letters_by_side.get(side)
        if not letters:
            continue
        pieces.append(f"{'/'.join(letters)} {side}" if side != "GK" else "GK")
    return " · ".join(pieces)


def _dominant_family(
    family_starts: dict[str, dict[str, float]], config: dict[str, Any]
) -> tuple[str | None, str | None]:
    if not family_starts:
        return None, None
    ranked = sorted(
        family_starts.items(),
        key=lambda item: (
            -item[1]["weighted"],
            -item[1]["starts"],
            _family_order(config, item[0]),
        ),
    )
    return ranked[0][0], (ranked[1][0] if len(ranked) > 1 else None)


def _dominant_slot_role(
    role_rows: dict[str, dict[str, float]], config: dict[str, Any]
) -> str | None:
    if not role_rows:
        return None
    code, _ = max(
        role_rows.items(),
        key=lambda item: (
            item[1]["weighted"],
            item[1]["starts"],
            -_role_order(config, item[0]),
        ),
    )
    return code


def _dominant_role(
    role_rows: dict[str, dict[str, float]], family: str | None, config: dict[str, Any]
) -> str | None:
    if not family:
        return None
    candidates = [
        (code, values) for code, values in role_rows.items() if role_family(config, code) == family
    ]
    if not candidates:
        return None
    code, _ = max(
        candidates,
        key=lambda item: (
            item[1]["weighted"],
            item[1]["starts"],
            -_role_order(config, item[0]),
        ),
    )
    return code


def career_role_summary(
    rows: list[dict[str, Any]],
    *,
    starts_total: int,
    starts_with_role: int,
    config: dict[str, Any],
    current_season: str,
) -> dict[str, Any]:
    """Build the career distribution from aggregate role rows.

    ``rows`` are aggregate rows with ``starts`` and role/season/team/scope
    fields. Shares use weighted starts; thresholds use raw starts.
    """
    weights = season_weights(config, current_season)
    career = config.get("career") or {}
    dominant_cfg = career.get("dominant") or {}
    role_rows: dict[str, dict[str, float]] = defaultdict(lambda: {"starts": 0.0, "weighted": 0.0})
    family_rows: dict[str, dict[str, float]] = defaultdict(lambda: {"starts": 0.0, "weighted": 0.0})
    family_roles: dict[str, dict[str, dict[str, float]]] = defaultdict(
        lambda: defaultdict(lambda: {"starts": 0.0, "weighted": 0.0})
    )
    slot_rows: dict[str, dict[str, float]] = defaultdict(lambda: {"starts": 0.0, "weighted": 0.0})
    slot_roles: dict[str, dict[str, dict[str, float]]] = defaultdict(
        lambda: defaultdict(lambda: {"starts": 0.0, "weighted": 0.0})
    )
    season_rows: dict[str, dict[str, Any]] = {}
    scope_rows: dict[str, dict[str, float]] = defaultdict(lambda: {"starts": 0.0, "weighted": 0.0})
    history: list[dict[str, Any]] = []

    for row in rows:
        code = str(row.get("role_code") or "")
        family = str(row.get("role_family") or role_family(config, code) or "")
        if not code or not family:
            continue
        starts = float(row.get("starts") or 0)
        if starts <= 0:
            continue
        season = str(row.get("season") or "")
        weight = float(weights.get(season, 0.0))
        weighted = starts * weight
        role_rows[code]["starts"] += starts
        role_rows[code]["weighted"] += weighted
        family_rows[family]["starts"] += starts
        family_rows[family]["weighted"] += weighted
        family_roles[family][code]["starts"] += starts
        family_roles[family][code]["weighted"] += weighted
        slot_key, _slot = slot_for_role(config, code)
        if slot_key:
            slot_rows[slot_key]["starts"] += starts
            slot_rows[slot_key]["weighted"] += weighted
            slot_roles[slot_key][code]["starts"] += starts
            slot_roles[slot_key][code]["weighted"] += weighted
        scope = str(row.get("scope") or "unknown")
        scope_rows[scope]["starts"] += starts
        scope_rows[scope]["weighted"] += weighted

        season_bucket = season_rows.setdefault(
            season,
            {
                "season": season,
                "season_year": season_start_year(season) if season else None,
                "starts_with_role": 0,
                "families": defaultdict(lambda: {"starts": 0.0, "weighted": 0.0}),
                "slots": defaultdict(lambda: {"starts": 0.0, "weighted": 0.0}),
                "scopes": defaultdict(lambda: {"starts": 0.0, "weighted": 0.0}),
            },
        )
        season_bucket["starts_with_role"] += int(starts)
        season_bucket["families"][family]["starts"] += starts
        season_bucket["families"][family]["weighted"] += weighted
        if slot_key:
            season_bucket["slots"][slot_key]["starts"] += starts
            season_bucket["slots"][slot_key]["weighted"] += weighted
        season_bucket["scopes"][scope]["starts"] += starts
        season_bucket["scopes"][scope]["weighted"] += weighted

        history.append(
            {
                "season": season,
                "team_id": row.get("team_id"),
                "team_name": row.get("team_name"),
                "scope": scope,
                "competition": row.get("competition"),
                "role_code": code,
                "role_label": role_label(config, code),
                "role_family": family,
                "starts": int(starts),
                "share": 0.0,
            }
        )

    total_weighted = sum(values["weighted"] for values in family_rows.values())
    total_starts = int(sum(values["starts"] for values in family_rows.values()))
    top_family, second_family = _dominant_family(family_rows, config)
    top_share = _share(family_rows[top_family]["weighted"], total_weighted) if top_family else 0.0
    second_share = (
        _share(family_rows[second_family]["weighted"], total_weighted) if second_family else 0.0
    )
    slot_defs = career.get("slots") or {}
    slot_order = {key: int((slot or {}).get("order") or 999) for key, slot in slot_defs.items()}
    slot_rank = sorted(
        slot_rows.items(),
        key=lambda item: (
            -item[1]["weighted"],
            -item[1]["starts"],
            slot_order.get(item[0], 999),
        ),
    )
    top_slot_starts = int(slot_rank[0][1]["starts"]) if slot_rank else 0
    top_slot_share = _share(slot_rank[0][1]["weighted"], total_weighted) if slot_rank else 0.0
    second_slot_share = (
        _share(slot_rank[1][1]["weighted"], total_weighted) if len(slot_rank) > 1 else 0.0
    )
    min_starts = int(dominant_cfg.get("min_family_starts") or 5)
    min_share = float(dominant_cfg.get("min_family_share") or 0.40)
    min_margin = float(dominant_cfg.get("min_margin") or 0.15)
    if total_starts == 0:
        status = "unknown"
    elif slot_rank:
        if top_slot_starts < min_starts or total_starts < min_starts:
            status = "low_evidence"
        elif top_slot_share < min_share or top_slot_share - second_slot_share < min_margin:
            status = "mixed"
        else:
            status = "observed"
    elif (
        top_family is None
        or family_rows[top_family]["starts"] < min_starts
        or total_starts < min_starts
    ):
        status = "low_evidence"
    elif top_share < min_share or top_share - second_share < min_margin:
        status = "mixed"
    else:
        status = "observed"

    dominant_code = _dominant_role(family_roles.get(top_family or "", {}), top_family, config)
    dominant = None
    if top_family and dominant_code:
        values = role_rows[dominant_code]
        dominant = {
            "code": dominant_code,
            "label": role_label(config, dominant_code),
            "family": top_family,
            "family_label": family_label(config, top_family),
            "side": role_side(config, dominant_code),
            "starts": int(values["starts"]),
            "weighted_starts": round(values["weighted"], 2),
            "share": _share(values["weighted"], total_weighted),
            "provisional": status in {"low_evidence", "mixed"},
        }

    family_shares = [
        {
            "family": family,
            "label": family_label(config, family),
            "starts": int(values["starts"]),
            "weighted_starts": round(values["weighted"], 2),
            "share": _share(values["weighted"], total_weighted),
        }
        for family, values in sorted(
            family_rows.items(), key=lambda item: _family_order(config, item[0])
        )
    ]
    role_shares = [
        {
            "code": code,
            "label": role_label(config, code),
            "family": role_family(config, code),
            "starts": int(values["starts"]),
            "weighted_starts": round(values["weighted"], 2),
            "share": _share(values["weighted"], total_weighted),
        }
        for code, values in sorted(role_rows.items(), key=lambda item: _role_order(config, item[0]))
    ]
    secondary = [
        share
        for share in family_shares
        if share["family"] != top_family
        and share["share"] >= float(dominant_cfg.get("min_secondary_share") or 0.10)
    ][: int(dominant_cfg.get("max_secondary_roles") or 2)]

    eligibility_cfg = career.get("eligibility") or {}
    secondary_share = float(eligibility_cfg.get("secondary_min_share") or 0.15)
    secondary_starts = int(eligibility_cfg.get("secondary_min_starts") or 3)
    stretch_starts = int(eligibility_cfg.get("stretch_min_starts") or 1)
    slot_share_rows: list[dict[str, Any]] = []
    primary_slot_key = None
    if slot_rows:
        primary_slot_key = max(
            slot_rows,
            key=lambda key: (
                slot_rows[key]["weighted"],
                slot_rows[key]["starts"],
                -slot_order.get(key, 999),
            ),
        )
    for key, values in sorted(slot_rows.items(), key=lambda item: slot_order.get(item[0], 999)):
        slot = slot_defs.get(key) or {}
        raw_starts = int(values["starts"])
        share = _share(values["weighted"], total_weighted)
        if key == primary_slot_key:
            tier = "primary"
        elif raw_starts >= secondary_starts and share >= secondary_share:
            tier = "secondary"
        elif raw_starts >= stretch_starts:
            tier = "stretch"
        else:
            tier = "other"
        slot_share_rows.append(
            {
                "slot": key,
                "label": slot.get("label") or key,
                "fm": slot.get("fm") or key,
                "side": slot.get("side"),
                "groups": slot.get("groups") or [],
                "starts": raw_starts,
                "weighted_starts": round(values["weighted"], 2),
                "share": share,
                "tier": tier,
            }
        )

    primary_slot = None
    if primary_slot_key:
        slot = slot_defs.get(primary_slot_key) or {}
        role_code = _dominant_slot_role(slot_roles.get(primary_slot_key, {}), config)
        slot_values = slot_rows[primary_slot_key]
        primary_slot = {
            "slot": primary_slot_key,
            "label": slot.get("label") or primary_slot_key,
            "fm": slot.get("fm") or primary_slot_key,
            "side": slot.get("side"),
            "groups": slot.get("groups") or [],
            "code": role_code,
            "role_label": role_label(config, role_code),
            "family": role_family(config, role_code),
            "starts": int(slot_values["starts"]),
            "weighted_starts": round(slot_values["weighted"], 2),
            "share": _share(slot_values["weighted"], total_weighted),
        }
    secondary_slots = [row for row in slot_share_rows if row["tier"] == "secondary"]
    stretch_slots = [row for row in slot_share_rows if row["tier"] == "stretch"]
    groups: list[str] = []
    sides: list[str] = []
    for row in slot_share_rows:
        if row["tier"] == "other":
            continue
        for group in row["groups"]:
            if group not in groups:
                groups.append(group)
        if row["side"] and row["side"] not in sides:
            sides.append(row["side"])
    fm_label = _fm_label(
        slot_share_rows,
        tiers={"primary", "secondary"},
    )
    stretch_label = _fm_label(
        slot_share_rows,
        tiers={"stretch"},
    )
    if not fm_label and primary_slot:
        fm_label = primary_slot["fm"]
    if stretch_label:
        fm_label += " (stretch: " + stretch_label + ")"

    seasons_payload = []
    for season, bucket in sorted(season_rows.items(), reverse=True):
        season_total = sum(item["weighted"] for item in bucket["families"].values())
        seasons_payload.append(
            {
                "season": season,
                "season_year": bucket["season_year"],
                "starts_with_role": bucket["starts_with_role"],
                "families": [
                    {
                        "family": family,
                        "label": family_label(config, family),
                        "starts": int(values["starts"]),
                        "share": _share(values["weighted"], season_total),
                    }
                    for family, values in sorted(
                        bucket["families"].items(),
                        key=lambda item: _family_order(config, item[0]),
                    )
                ],
                "slots": [
                    {
                        "slot": key,
                        "label": (slot_defs.get(key) or {}).get("label") or key,
                        "fm": (slot_defs.get(key) or {}).get("fm") or key,
                        "side": (slot_defs.get(key) or {}).get("side"),
                        "groups": (slot_defs.get(key) or {}).get("groups") or [],
                        "starts": int(values["starts"]),
                        "share": _share(values["weighted"], season_total),
                    }
                    for key, values in sorted(
                        bucket["slots"].items(),
                        key=lambda item: slot_order.get(item[0], 999),
                    )
                ],
                "scopes": [
                    {
                        "scope": scope,
                        "starts": int(values["starts"]),
                        "share": _share(values["weighted"], season_total),
                    }
                    for scope, values in sorted(bucket["scopes"].items())
                ],
            }
        )

    scopes_payload = [
        {
            "scope": scope,
            "label": {
                "aberdeen": "Aberdeen",
                "previous_club": "Previous club",
                "loan_club": "Loan club",
                "national_team": "National team",
                "unknown": "Unknown",
            }.get(scope, scope),
            "starts": int(values["starts"]),
            "share": _share(values["weighted"], total_weighted),
        }
        for scope, values in sorted(scope_rows.items())
    ]
    for row in history:
        row["share"] = next(
            (item["share"] for item in role_shares if item["code"] == row["role_code"]),
            0.0,
        )
    history.sort(
        key=lambda row: (
            str(row.get("season") or ""),
            str(row.get("team_name") or ""),
            _role_order(config, str(row.get("role_code") or "")),
        ),
        reverse=True,
    )

    coverage = f"{starts_with_role}/{starts_total}"
    return {
        "status": status,
        "dominant": dominant,
        "secondary": secondary,
        "top_families": [
            {
                "family": family,
                "label": family_label(config, family),
                "starts": int(values["starts"]),
                "share": _share(values["weighted"], total_weighted),
            }
            for family, values in sorted(
                family_rows.items(),
                key=lambda item: (-item[1]["weighted"], _family_order(config, item[0])),
            )
        ],
        "family_shares": family_shares,
        "role_shares": role_shares,
        "primary_slot": primary_slot,
        "slot_definitions": [
            {
                "slot": key,
                "label": (slot_defs.get(key) or {}).get("label") or key,
                "fm": (slot_defs.get(key) or {}).get("fm") or key,
                "side": (slot_defs.get(key) or {}).get("side"),
                "groups": (slot_defs.get(key) or {}).get("groups") or [],
                "order": slot_order.get(key, 999),
            }
            for key in sorted(slot_defs, key=lambda item: slot_order.get(item, 999))
        ],
        "slots": slot_share_rows,
        "eligibility": slot_share_rows,
        "secondary_slots": secondary_slots,
        "stretch_slots": stretch_slots,
        "broad_groups": groups,
        "sides": sides,
        "fm_label": fm_label,
        "starts_total": starts_total,
        "starts_with_role": starts_with_role,
        "coverage": coverage,
        "seasons_with_role": sum(1 for bucket in seasons_payload if bucket["starts_with_role"] > 0),
        "unknown_reason": ("no_role_evidence" if output_unknown(status) else None),
        "seasons": seasons_payload,
        "scopes": scopes_payload,
        "history": history,
        "policy": {
            "seasons": career.get("seasons"),
            "weights": career.get("season_weights"),
            "min_family_starts": min_starts,
            "min_family_share": min_share,
            "min_margin": min_margin,
        },
        "policy_version": policy_version(config),
        "note": (
            "Career starts are starting-XI observations from lineups, "
            "equal-weighted across the configured seasons. Substitute "
            "appearances are excluded; unknown-role starts count for coverage "
            "but not for shares."
        ),
    }


def output_unknown(status: str) -> bool:
    return status == "unknown"


def current_family_share(current_role: dict[str, Any]) -> float:
    roles = current_role.get("roles") or []
    total = sum(int(row.get("starts") or 0) for row in roles)
    if not total:
        return 0.0
    family = current_role.get("family")
    family_starts = sum(int(row.get("starts") or 0) for row in roles if row.get("family") == family)
    return round(family_starts / total, 4)


def current_role_slots(
    current_role: dict[str, Any],
    *,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Summarise the current role rows as FM-style slots.

    This lets a fluid current usage (for example right wing plus attacking
    midfield) be shown without turning it into one misleading label.
    """
    career = config.get("career") or {}
    eligibility = career.get("eligibility") or {}
    slot_defs = career.get("slots") or {}
    slot_order = {key: int((slot or {}).get("order") or 999) for key, slot in slot_defs.items()}
    starts_by_slot: dict[str, int] = defaultdict(int)
    roles = current_role.get("roles") or []
    for row in roles:
        key, _slot = slot_for_role(config, str(row.get("code") or ""))
        if key:
            starts_by_slot[key] += int(row.get("starts") or 0)
    total = sum(starts_by_slot.values())
    if not total:
        return {
            "slots": [],
            "fm_label": "",
            "broad_groups": [],
            "sides": [],
            "primary_slot": None,
        }
    # Current usage is a small sample; treat a role with at least 15% of the
    # current starts as secondary rather than requiring three starts.
    secondary_share = float(eligibility.get("secondary_min_share") or 0.15)
    stretch_starts = int(eligibility.get("stretch_min_starts") or 1)
    primary_code = str(current_role.get("code") or "")
    primary, _ = slot_for_role(config, primary_code)
    if not primary or primary not in starts_by_slot:
        primary = max(
            starts_by_slot,
            key=lambda key: (
                starts_by_slot[key],
                -slot_order.get(key, 999),
            ),
        )
    rows: list[dict[str, Any]] = []
    for key, starts in sorted(
        starts_by_slot.items(), key=lambda item: slot_order.get(item[0], 999)
    ):
        slot = slot_defs.get(key) or {}
        share = _share(starts, total)
        if key == primary:
            tier = "primary"
        elif share >= secondary_share:
            tier = "secondary"
        elif starts >= stretch_starts:
            tier = "stretch"
        else:
            tier = "other"
        rows.append(
            {
                "slot": key,
                "label": slot.get("label") or key,
                "fm": slot.get("fm") or key,
                "side": slot.get("side"),
                "groups": slot.get("groups") or [],
                "starts": starts,
                "share": share,
                "tier": tier,
            }
        )
    groups: list[str] = []
    sides: list[str] = []
    for row in rows:
        if row["tier"] == "other":
            continue
        for group in row["groups"]:
            if group not in groups:
                groups.append(group)
        if row["side"] and row["side"] not in sides:
            sides.append(row["side"])
    fm_label = _fm_label(rows, tiers={"primary", "secondary"})
    stretch = _fm_label(rows, tiers={"stretch"})
    if not fm_label:
        fm_label = next((row["fm"] for row in rows if row["tier"] == "primary"), "")
    if stretch:
        fm_label += " (stretch: " + stretch + ")"
    primary_row = next((row for row in rows if row["tier"] == "primary"), None)
    return {
        "slots": rows,
        "fm_label": fm_label,
        "broad_groups": groups,
        "sides": sides,
        "primary_slot": primary_row,
    }


def override_conditions(
    current_role: dict[str, Any],
    career: dict[str, Any],
    *,
    config: dict[str, Any],
) -> dict[str, Any]:
    override = (config.get("career") or {}).get("override") or {}
    current_family = current_role.get("family")
    career_family = (career.get("primary_slot") or career.get("dominant") or {}).get("family")
    current_starts = int(current_role.get("starts_with_role") or 0)
    current_share = current_family_share(current_role)
    career_starts = int(career.get("starts_with_role") or 0)
    career_seasons = int(career.get("seasons_with_role") or 0)
    career_family_share = next(
        (
            float(row.get("share") or 0)
            for row in career.get("family_shares") or []
            if row.get("family") == current_family
        ),
        0.0,
    )
    conditions = {
        "enabled": bool(override.get("enabled")),
        "current_starts": current_starts,
        "current_share": current_share,
        "career_starts": career_starts,
        "career_seasons": career_seasons,
        "career_status": career.get("status"),
        "career_family_share": career_family_share,
        "current_family": current_family,
        "career_family": career_family,
        "different_family": bool(
            current_family and career_family and current_family != career_family
        ),
        "different_group": bool(
            current_family
            and career_family
            and family_group(config, current_family) != family_group(config, career_family)
        ),
        "passes": False,
    }
    conditions["passes"] = bool(
        conditions["enabled"]
        and current_starts >= int(override.get("min_aberdeen_starts") or 5)
        and current_share >= float(override.get("min_aberdeen_share") or 0.65)
        and career_starts >= int(override.get("min_career_starts") or 10)
        and career_seasons >= int(override.get("min_career_seasons") or 2)
        and conditions["career_status"] == "observed"
        and career_family_share < float(override.get("max_career_share_of_current_family") or 0.15)
        and conditions["different_family"]
        and (
            conditions["different_group"]
            if bool(override.get("require_group_change", True))
            else True
        )
    )
    return conditions


def choose_display_role(
    current_role: dict[str, Any],
    career: dict[str, Any],
    *,
    config: dict[str, Any],
) -> dict[str, Any]:
    current_established = bool(
        current_role.get("status") in {"observed", "partial"}
        and int(current_role.get("starts_with_role") or 0) > 0
    )
    career_status = str(career.get("status") or "unavailable")
    primary = career.get("primary_slot") or career.get("dominant") or {}
    primary_code = primary.get("code")
    primary_label = primary.get("role_label") or primary.get("label")
    primary_family = primary.get("family")
    primary_family_label = family_label(config, primary_family)
    primary_side = primary.get("side")
    career_dominant = (
        {
            "code": primary_code,
            "label": primary_label,
            "family": primary_family,
            "family_label": primary_family_label,
            "side": primary_side,
            "starts": primary.get("starts"),
            "weighted_starts": primary.get("weighted_starts"),
            "share": primary.get("share"),
            "provisional": career_status in {"low_evidence", "mixed"},
        }
        if primary_code
        else None
    )
    conditions = override_conditions(current_role, career, config=config)

    if career_status == "observed" and conditions["passes"] and current_role.get("code"):
        return {
            "code": current_role.get("code"),
            "label": current_role.get("primary"),
            "family": current_role.get("family"),
            "family_label": family_label(config, current_role.get("family")),
            "side": current_role.get("side"),
            "source": "aberdeen_override",
            "reason": (
                "Aberdeen current role is established and clearly different from the career role."
            ),
            "starts": conditions["current_starts"],
            "share": conditions["current_share"],
            "career_dominant": career_dominant,
            "conditions": conditions,
        }
    if career_status == "observed" and career_dominant:
        return {
            "code": career_dominant.get("code"),
            "label": career_dominant.get("label"),
            "family": career_dominant.get("family"),
            "family_label": career_dominant.get("family_label"),
            "side": career_dominant.get("side"),
            "source": "career",
            "reason": "Career position is the dominant role across the recent seasons.",
            "starts": career_dominant.get("starts"),
            "share": career_dominant.get("share"),
            "career_dominant": career_dominant,
            "conditions": conditions,
        }
    if current_established and current_role.get("code"):
        return {
            "code": current_role.get("code"),
            "label": current_role.get("primary"),
            "family": current_role.get("family"),
            "family_label": family_label(config, current_role.get("family")),
            "side": current_role.get("side"),
            "source": "current_season",
            "reason": (
                "Career evidence is not strong enough to override the established Aberdeen role."
            ),
            "starts": conditions["current_starts"],
            "share": conditions["current_share"],
            "career_dominant": career_dominant,
            "conditions": conditions,
        }
    if career_dominant:
        return {
            "code": career_dominant.get("code"),
            "label": career_dominant.get("label"),
            "family": career_dominant.get("family"),
            "family_label": career_dominant.get("family_label"),
            "side": career_dominant.get("side"),
            "source": "career_low_evidence",
            "reason": "Career evidence is provisional but is the only role evidence.",
            "starts": career_dominant.get("starts"),
            "share": career_dominant.get("share"),
            "career_dominant": career_dominant,
            "conditions": conditions,
        }
    return {
        "code": None,
        "label": None,
        "family": None,
        "family_label": None,
        "side": None,
        "source": "none",
        "reason": "No starting-XI role evidence was found.",
        "starts": 0,
        "share": 0.0,
        "career_dominant": None,
        "conditions": conditions,
    }


__all__ = [
    "career_role_summary",
    "career_seasons",
    "choose_display_role",
    "current_family_share",
    "current_role_slots",
    "family_group",
    "formation_policy_version",
    "override_conditions",
    "policy_version",
    "season_weights",
    "slot_for_role",
]
