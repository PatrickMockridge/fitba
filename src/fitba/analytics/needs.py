"""Squad-needs model: cover, replace, strengthen or monitor.

The model consumes the published themes, availability ledger, squad minutes,
transfer register and rumours. It emits role profiles and market routes, never
named targets, fees or wages. Measured depth drives the category; the curated
``squad_needs`` prior is shown separately and is not blended into an opaque
score.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from typing import Any

import polars as pl

from fitba.settings import aberdeen as aberdeen_config
from fitba.settings import needs_policy
from fitba.settings import roles as roles_config

FAMILIES = ("GK", "CB", "FB/WB", "MID", "AM/WM", "W", "ST")
THEME_FAMILIES = {
    "goalkeeper": "GK",
    "centre_back": "CB",
    "full_back": "FB/WB",
    "wing_back": "FB/WB",
    "defensive_midfield": "MID",
    "central_midfield": "MID",
    "attacking_midfield": "AM/WM",
    "wide_midfield": "AM/WM",
    "wide_forward": "W",
    "centre_forward": "ST",
}


def _rows(frame: pl.DataFrame | Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if frame is None:
        return []
    if isinstance(frame, pl.DataFrame):
        return frame.to_dicts() if frame.height else []
    return [dict(row) for row in frame]


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _mean(values: Iterable[float]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return round(sum(clean) / len(clean), 2) if clean else None


def _primary_family(player: dict[str, Any]) -> str | None:
    for key in ("display_role", "role"):
        family = (player.get(key) or {}).get("family")
        if family and family != "unknown":
            return THEME_FAMILIES.get(str(family), str(family))
    career = (player.get("career_role") or {}).get("dominant") or {}
    family = career.get("family")
    if family and family != "unknown":
        return THEME_FAMILIES.get(str(family), str(family))
    if str(player.get("position_group") or "").upper() == "GK":
        return "GK"
    return None


def _formation_slots(
    team_shapes: pl.DataFrame | Iterable[dict[str, Any]] | None,
    *,
    season_year: int,
) -> dict[str, float | None]:
    shapes = [
        row
        for row in _rows(team_shapes)
        if _int(row.get("team_id")) == 252
        and _int(row.get("season")) == season_year
        and row.get("formation")
    ]
    if not shapes:
        return {family: None for family in FAMILIES}
    counts: Counter[str] = Counter(
        str(row.get("formation_shape") or row.get("formation")) for row in shapes
    )
    total = sum(counts.values())
    slot_totals: dict[str, float] = defaultdict(float)
    for formation, count in counts.items():
        formation_map = (roles_config().get("formations") or {}).get(formation)
        if not formation_map:
            continue
        roles = roles_config().get("roles") or {}
        for row in formation_map:
            for role_code in row:
                family = THEME_FAMILIES.get(str((roles.get(role_code) or {}).get("family") or ""))
                if family:
                    slot_totals[family] += count
    return {
        family: round(slot_totals.get(family, 0) / total, 2) if total else None
        for family in FAMILIES
    }


def _curated_prior(family: str) -> float | None:
    prior = aberdeen_config().get("squad_needs") or {}
    if family in prior:
        return _float(prior[family])
    if family == "MID":
        values = [_float(prior.get("DM")), _float(prior.get("CM"))]
        clean = [value for value in values if value is not None]
        return round(sum(clean) / len(clean), 2) if clean else None
    if family == "AM/WM":
        return _float(prior.get("AM"))
    if family == "W":
        return _float(prior.get("W"))
    if family == "FB/WB":
        return _float(prior.get("FB"))
    return _float(prior.get(family))


def _family_rating_delta(themes: dict[str, Any] | None, family: str) -> float | None:
    for theme in (themes or {}).get("themes", []):
        if theme.get("theme_id") != "family_balance":
            continue
        for group in (theme.get("metrics") or {}).get("groups") or []:
            if group.get("family") == family:
                return _float(group.get("squad_rating_delta"))
    return None


def _cover_group(themes: dict[str, Any] | None, group: str) -> dict[str, Any] | None:
    for theme in (themes or {}).get("themes", []):
        if theme.get("theme_id") != "cover_question":
            continue
        for row in (theme.get("metrics") or {}).get("groups") or []:
            if row.get("group") == group:
                return row
    return None


def _active_outgoing_rumours(rumours: Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [
        row
        for row in (rumours or [])
        if row.get("direction") == "out"
        and row.get("status") == "active"
        and str(row.get("confidence") or "").lower() in {"medium", "high"}
    ]


def _squad_players(
    squad_data: dict[str, Any] | None,
    availability: dict[int, dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    output = []
    for player in (squad_data or {}).get("players", []):
        if player.get("status") == "loan_out":
            continue
        family = _primary_family(player)
        if family not in FAMILIES:
            continue
        player_id = _int(player.get("player_id"))
        if player_id is None:
            continue
        playing = player.get("playing_time") or {}
        availability_row = (availability or {}).get(player_id, {})
        status = str(availability_row.get("status") or "unknown")
        output.append(
            {
                "player_id": player_id,
                "name": player.get("name") or f"Player {player_id}",
                "family": family,
                "age": _int(player.get("age")),
                "starts": int(playing.get("starts") or 0),
                "minutes": int(playing.get("minutes") or 0),
                "sub_apps": int(playing.get("sub_apps") or 0),
                "availability_status": status,
                "availability_note": availability_row.get("note"),
                "availability_conflict": bool(availability_row.get("conflict")),
                "status": player.get("status"),
            }
        )
    return output


def _family_players(
    family: str,
    players: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [player for player in players if player["family"] == family]


def build_needs_document(
    *,
    season: str,
    generated_at: str,
    themes: dict[str, Any] | None,
    availability: dict[str, Any] | None,
    squad_data: dict[str, Any] | None,
    transfers: Iterable[dict[str, Any]] | None,
    rumours: Iterable[dict[str, Any]] | None,
    team_shapes: pl.DataFrame | Iterable[dict[str, Any]] | None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the seven-family needs document."""
    config = config or needs_policy()
    thresholds = config.get("thresholds") or {}
    families_config = config.get("families") or {}
    roster_config = config.get("roster") or {}
    market_config = config.get("market") or {}
    season_year = int(str(season).split("-", 1)[0]) if "-" in str(season) else 2026
    availability_entries = {
        int(entry["player_id"]): entry
        for entry in (availability or {}).get("entries", [])
        if entry.get("player_id") is not None
    }
    players = _squad_players(squad_data, availability_entries)
    slots = _formation_slots(team_shapes, season_year=season_year)
    outgoing = _active_outgoing_rumours(rumours)
    arrivals = {
        str(item.get("player_key") or ""): item
        for item in (transfers or [])
        if item.get("direction") == "in" and str(item.get("season")) == season
    }
    families = []
    for family in FAMILIES:
        family_config = families_config.get(family) or {}
        family_players = _family_players(family, players)
        expected_slots = slots.get(family)
        max_squad = int(family_config.get("max_squad") or 0)
        min_available = int(family_config.get("min_available") or 0)
        available_players = [
            player
            for player in family_players
            if player["availability_status"] not in {"out", "suspended"}
        ]
        ready = [
            player
            for player in family_players
            if player["starts"] >= int(thresholds.get("ready_starts") or 2)
            or player["minutes"] >= int(thresholds.get("ready_minutes") or 180)
        ]
        starters = [
            player
            for player in family_players
            if player["starts"] >= int(thresholds.get("starter_starts") or 5)
            or player["minutes"] >= int(thresholds.get("starter_minutes") or 450)
        ]
        trusted = [
            player
            for player in family_players
            if player["starts"] >= (thresholds.get("trusted_starts") or 3)
        ]
        projected_slots = max(1, round(expected_slots or 0))
        projected = sorted(
            family_players, key=lambda player: (-player["minutes"], -player["starts"])
        )[:projected_slots]
        total_minutes = sum(player["minutes"] for player in family_players)
        top_minutes = max((player["minutes"] for player in family_players), default=0)
        top_share = round(top_minutes / total_minutes, 2) if total_minutes else None
        required_depth = max(projected_slots, min_available)
        depth_gap = (
            _clamp(
                (required_depth + int(thresholds.get("cover_buffer") or 1) - len(available_players))
                / required_depth
            )
            if expected_slots is not None
            else None
        )
        quality_gap = (
            _clamp(
                1
                - (_mean(player["minutes"] for player in projected) or 0)
                / float(thresholds.get("quality_minutes") or 900)
            )
            if projected
            else None
        )
        projected_out = sum(
            1 for player in projected if player["availability_status"] in {"out", "suspended"}
        )
        projected_doubtful = sum(
            1 for player in projected if player["availability_status"] == "doubtful"
        )
        availability_risk = (
            round((projected_out + 0.5 * projected_doubtful) / projected_slots, 3)
            if expected_slots is not None
            else None
        )
        age_risk = (
            round(
                sum(1 for player in projected if (player["age"] or 0) >= 30) / len(projected),
                3,
            )
            if projected and family != "GK"
            else 0.0
            if projected
            else None
        )
        projected_shortfall = (
            max(0, required_depth - len(available_players)) if expected_slots is not None else None
        )
        measured_status = (
            "available"
            if total_minutes >= 450 and len(family_players) >= 2
            else "partial"
            if total_minutes
            else "unavailable"
        )
        measured_score = (
            round(
                100
                * (
                    0.30 * (depth_gap or 0)
                    + 0.20 * (quality_gap or 0)
                    + 0.10 * ((top_share or 0) if family != "GK" else 0)
                    + 0.25 * (availability_risk or 0)
                    + 0.15 * (age_risk or 0)
                ),
                1,
            )
            if measured_status != "unavailable"
            else None
        )
        family_rating_delta = _family_rating_delta(themes, family)
        cover_group = _cover_group(
            themes,
            "CB" if family == "CB" else "FB/WB" if family == "FB/WB" else "",
        )
        thin_rotation = (
            False
            if family == "GK"
            else len(trusted) < (thresholds.get("trusted_starts") or 3)
            if family not in {"CB", "FB/WB"}
            else bool((cover_group or {}).get("thin_rotation"))
        )
        concentration_high = family != "GK" and (
            (top_share or 0) >= float(thresholds.get("reliance_top_share") or 0.55)
        )
        replace_evidence = []
        for rumour in outgoing:
            player_key = str(rumour.get("player_key") or "")
            if not player_key:
                continue
            for player in family_players:
                if f"api:player:{player['player_id']}" == player_key and (
                    player["starts"] >= 5 or player["minutes"] >= 450
                ):
                    replace_evidence.append(
                        {
                            "type": "active_outgoing_rumour",
                            "player_id": player["player_id"],
                            "player_name": player["name"],
                            "note": str(rumour.get("claim") or ""),
                            "basis": "curated",
                            "source_urls": rumour.get("source_urls") or [],
                        }
                    )
        replace_watch = [
            {
                "type": "age_signal",
                "player_id": player["player_id"],
                "player_name": player["name"],
                "note": "Starter aged 30+; watch only, not a sale claim.",
                "basis": "measured",
            }
            for player in starters
            if (player["age"] or 0) >= 30
        ]
        replace_status = (
            "replace"
            if replace_evidence
            else "watch"
            if replace_watch
            else "unknown"
            if not roster_config.get("senior_squad_limit")
            else "none"
        )
        category = "none"
        if replace_evidence:
            category = "replace"
        elif measured_status == "unavailable":
            category = "unknown"
        elif (availability_risk or 0) > 0 and (
            (projected_shortfall or 0) >= 1
            or (depth_gap or 0) >= float(thresholds.get("depth_gap_cover") or 0.5)
            or (availability_risk or 0) >= float(thresholds.get("availability_risk_cover") or 0.25)
        ):
            category = "cover"
        elif (
            (
                family_rating_delta is not None
                and family_rating_delta <= float(thresholds.get("weak_family_delta") or -0.15)
            )
            or concentration_high
            or thin_rotation
            or (quality_gap or 0) >= float(thresholds.get("quality_gap_strengthen") or 0.35)
            or (age_risk or 0) >= float(thresholds.get("age_risk_strengthen") or 0.5)
        ):
            category = "strengthen"
        elif (measured_score or 0) >= 30:
            category = "monitor"
        urgency = "none"
        if category in {"cover", "replace", "strengthen"}:
            if (projected_shortfall or 0) >= 2 or projected_out >= 2:
                urgency = "critical"
            elif (projected_shortfall or 0) == 1 or projected_out >= 1 or category == "replace":
                urgency = "high"
            elif (measured_score or 0) >= 50 or category in {"cover", "strengthen"}:
                urgency = "medium"
            else:
                urgency = "low"
        known_availability = sum(
            1 for player in family_players if player["availability_status"] != "unknown"
        )
        availability_share = known_availability / len(family_players) if family_players else 0
        confidence = (
            "high"
            if measured_status == "available"
            and total_minutes >= 900
            and availability_share >= 0.8
            and not any(player["availability_conflict"] for player in family_players)
            else "medium"
            if total_minutes >= 450 and availability_share >= 0.5
            else "low"
            if measured_status != "unavailable"
            else "unknown"
        )
        market_primary = (
            "loan"
            if category == "cover"
            else "permanent"
            if category in {"replace", "strengthen"}
            else "none"
        )
        market_alternatives = ["free_agent"] if category in {"cover", "strengthen"} else []
        horizon = (
            "now"
            if category == "cover"
            else "long_term"
            if category in {"replace", "strengthen"}
            else None
        )
        drivers = []
        if depth_gap is not None and depth_gap >= 0.3:
            drivers.append("depth_gap")
        if quality_gap is not None and quality_gap >= 0.25:
            drivers.append("quality_gap")
        if availability_risk is not None and availability_risk > 0:
            drivers.append("availability_risk")
        if concentration_high:
            drivers.append("concentration")
        if age_risk is not None and age_risk >= 0.5:
            drivers.append("age_risk")
        if family_rating_delta is not None and family_rating_delta < 0:
            drivers.append("family_rating")
        if not drivers:
            drivers.append("stable")
        family_players_payload = []
        for player in family_players:
            arrival = arrivals.get(f"api:player:{player['player_id']}")
            family_players_payload.append(
                {
                    "player_id": player["player_id"],
                    "name": player["name"],
                    "role_family": family,
                    "starts": player["starts"],
                    "minutes": player["minutes"],
                    "sub_apps": player["sub_apps"],
                    "category": (
                        "unavailable"
                        if player["availability_status"] in {"out", "suspended"}
                        else "starter"
                        if player in starters
                        else "rotation"
                        if player in ready
                        else "fringe"
                    ),
                    "availability_status": player["availability_status"],
                    "availability_note": player["availability_note"],
                    "availability_conflict": player["availability_conflict"],
                    "arrival": arrival.get("date_effective") if arrival else None,
                    "arrival_kind": arrival.get("transfer_kind") if arrival else None,
                    "note": None,
                }
            )
        families.append(
            {
                "family": family,
                "label": str(family_config.get("label") or family),
                "category": category,
                "priority": None,
                "urgency": urgency,
                "measured_score": measured_score,
                "curated_prior": _curated_prior(family),
                "confidence": confidence,
                "basis": "measured" if measured_status != "unavailable" else "curated",
                "expected_slots": expected_slots,
                "measured": {
                    "status": measured_status,
                    "players": len(family_players),
                    "available_players": len(
                        [
                            player
                            for player in family_players
                            if player["availability_status"] not in {"out", "suspended"}
                        ]
                    ),
                    "starters": len(starters),
                    "rotation": len(
                        [
                            player
                            for player in family_players
                            if player in ready and player not in starters
                        ]
                    ),
                    "fringe": len([player for player in family_players if player not in ready]),
                    "ready_count": len(ready),
                    "trusted_count": len(trusted),
                    "total_minutes": total_minutes,
                    "top_share": top_share,
                    "concentration": top_share,
                    "depth_gap": depth_gap,
                    "quality_gap": quality_gap,
                    "availability_risk": availability_risk,
                    "age_risk": age_risk,
                    "projected_shortfall": projected_shortfall,
                },
                "evidence": [
                    {
                        "label": "Expected slots",
                        "value": expected_slots,
                        "note": "formation-weighted",
                        "basis": "measured",
                    },
                    {
                        "label": "Ready bodies",
                        "value": len(ready),
                        "note": "starts >= 2 or minutes >= 180",
                        "basis": "measured",
                    },
                    {
                        "label": "Top share",
                        "value": top_share,
                        "note": "share of family minutes",
                        "basis": "measured",
                    },
                    {
                        "label": "Curated prior",
                        "value": _curated_prior(family),
                        "note": "analyst intent, not measured evidence",
                        "basis": "curated",
                    },
                ],
                "drivers": drivers,
                "availability": [
                    {
                        "player_id": player["player_id"],
                        "name": player["name"],
                        "status": player["availability_status"],
                        "note": player["availability_note"],
                    }
                    for player in family_players
                    if player["availability_status"] != "unknown"
                ],
                "outgoing_risk": {
                    "level": replace_status,
                    "evidence": replace_evidence + replace_watch,
                    "note": "No contract or bid claim is made.",
                },
                "replace_status": replace_status,
                "scouting_groups": family_config.get("scouting_groups") or [],
                "role_profile": {
                    "label": str(family_config.get("label") or family),
                    "age_band": (aberdeen_config().get("budget") or {}).get("age_band") or [19, 28],
                    "min_effective_minutes": 900,
                    "coverage_floor": "event",
                    "key_traits": family_config.get("traits") or [],
                },
                "market_route": {
                    "primary": market_primary,
                    "alternatives": market_alternatives,
                    "horizon": horizon,
                    "fee_expectation": "unknown",
                    "budget_status": market_config.get("budget_status") or "ceiling_unset",
                    "wage_status": market_config.get("wage_status") or "not_public",
                    "note": ("Role-profile recommendation, not a target or a fee claim."),
                },
                "roster_space": {
                    "status": (
                        "requires_outgoing"
                        if max_squad and len(family_players) >= max_squad
                        else "space_unknown"
                    ),
                    "max_squad": max_squad,
                    "current": len(family_players),
                    "outgoing_first": family
                    in (roster_config.get("outgoing_first_families") or []),
                    "note": (
                        "A signing in this family needs an outgoing first."
                        if max_squad and len(family_players) >= max_squad
                        else "No public senior-squad or contract limit is known."
                    ),
                },
                "players": family_players_payload,
                "caveats": [
                    "Minutes are not proof of trust; availability is curated.",
                    "No contract, bid, wage or fee claim is made.",
                ],
                "links": [
                    {"label": "Squad", "href": "/squad/"},
                    {
                        "label": "Scouting profile",
                        "href": f"/scouting/#priority-{family.lower().replace('/', '-')}",
                    },
                    {"label": "Themes", "href": "/themes/"},
                ],
            }
        )
    families.sort(
        key=lambda row: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}.get(row["urgency"], 5),
            {"replace": 0, "cover": 1, "strengthen": 2, "monitor": 3, "unknown": 4, "none": 5}.get(
                row["category"], 6
            ),
            -(row["measured_score"] or 0),
            FAMILIES.index(row["family"]),
        )
    )
    for index, family in enumerate(families, start=1):
        family["priority"] = index
    counts = Counter(row["category"] for row in families)
    known = sum(1 for entry in availability_entries.values() if entry.get("status") != "unknown")
    document = {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "season": season,
        "club_id": "sco:aberdeen",
        "state": "fresh"
        if any(row["measured"]["status"] != "unavailable" for row in families)
        else "unavailable",
        "summary": {
            "families": len(families),
            "counts": dict(counts),
            "top_priority": families[0]["family"] if families else None,
            "availability_known": known,
            "availability_unknown": max(0, len(availability_entries) - known),
            "note": ("Role profiles and market routes only. No targets, fees or wages."),
        },
        "coverage": {
            "status": "partial" if known < len(availability_entries) else "available",
            "measured_families": sum(
                1 for row in families if row["measured"]["status"] != "unavailable"
            ),
            "availability": {
                "known": known,
                "unknown": max(0, len(availability_entries) - known),
            },
            "transfers": "available" if transfers else "unavailable",
            "rumours": "available" if rumours else "empty",
            "valuation": "inferred",
            "basis": "measured + curated prior",
        },
        "roster_space": {
            "status": "unknown",
            "senior_squad_limit": roster_config.get("senior_squad_limit"),
            "outgoing_first_families": roster_config.get("outgoing_first_families") or [],
            "net_add_allowed": None,
            "note": roster_config.get("note") or "The public registration limit is not known.",
        },
        "families": families,
        "sources": [],
        "notes": (
            "Needs are role profiles, not transfer targets. The curated prior is "
            "shown separately and is not blended into a verdict."
        ),
    }
    return document


__all__ = ["FAMILIES", "build_needs_document"]
