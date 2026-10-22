"""Pure matchday analytics: form, strength, style lean and predicted XIs.

The module has no network or filesystem access. It consumes the same league
match rows and provider lineup rows as the rest of the site, and returns
JSON-ready dictionaries. A missing input is an explicit coverage state, never a
zero or a guessed value.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from typing import Any

import polars as pl

from fitba.analytics.history import club_match_rows
from fitba.analytics.style import style_profile

FORM_WINDOW = 5

CONFIDENCE_ORDER = {"unknown": 0, "low": 1, "medium": 2, "high": 3}

LEAN_LABELS = {
    "attack": "Attack",
    "balanced": "Balanced",
    "sit_deep_counter": "Sit deep and counter",
    "unknown": "Unknown",
}

POSITION_GROUP = {
    "goalkeeper": "GK",
    "keeper": "GK",
    "gk": "GK",
    "g": "GK",
    "defender": "D",
    "defence": "D",
    "defense": "D",
    "def": "D",
    "d": "D",
    "midfielder": "M",
    "midfield": "M",
    "mid": "M",
    "m": "M",
    "attacker": "F",
    "forward": "F",
    "fwd": "F",
    "striker": "F",
    "f": "F",
}


def _label_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _rows(frame: pl.DataFrame | Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if frame is None:
        return []
    if isinstance(frame, pl.DataFrame):
        return frame.to_dicts() if frame.height else []
    return [dict(row) for row in frame]


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None


def _mean(values: Iterable[float]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return round(sum(clean) / len(clean), 2) if clean else None


def _rate(total: float | None, matches: int) -> float | None:
    return round(total / matches, 2) if total is not None and matches else None


def _ordinal(value: int) -> str:
    suffix = "th" if 10 <= value % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def percentile_rank(values: Iterable[float | None], value: float | None) -> int | None:
    """Percentile rank in a league distribution, 0-100.

    Ties take the midpoint. The maximum is 100 and the minimum is 0. A sample
    smaller than two returns ``None`` rather than a made-up number.
    """
    if value is None:
        return None
    clean = [float(item) for item in values if item is not None]
    if len(clean) < 2:
        return None
    below = sum(1 for item in clean if item < value)
    equal = sum(1 for item in clean if item == value) - 1
    rank = 100 * (below + 0.5 * max(equal, 0)) / (len(clean) - 1)
    return max(0, min(100, round(rank)))


def record(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """W-D-L, points and per-match rates for a set of club-perspective rows."""
    items = list(rows)
    played = len(items)
    won = sum(1 for row in items if row.get("result") == "W")
    drawn = sum(1 for row in items if row.get("result") == "D")
    lost = sum(1 for row in items if row.get("result") == "L")
    points = sum(int(row.get("points") or 0) for row in items)
    gf = sum(int(row.get("gf") or 0) for row in items)
    ga = sum(int(row.get("ga") or 0) for row in items)
    shots_for = sum(int(row.get("shots_for") or 0) for row in items)
    shots_against = sum(int(row.get("shots_against") or 0) for row in items)
    sot_for = sum(int(row.get("shots_on_target_for") or 0) for row in items)
    sot_against = sum(int(row.get("shots_on_target_against") or 0) for row in items)
    corners_for = sum(int(row.get("corners_for") or 0) for row in items)
    corners_against = sum(int(row.get("corners_against") or 0) for row in items)
    fouls_for = sum(int(row.get("fouls_for") or 0) for row in items)
    fouls_against = sum(int(row.get("fouls_against") or 0) for row in items)
    shot_total = shots_for + shots_against
    return {
        "played": played,
        "won": won,
        "drawn": drawn,
        "lost": lost,
        "points": points,
        "ppg": round(points / played, 2) if played else None,
        "gf": gf,
        "ga": ga,
        "gd": gf - ga,
        "gf_pg": _rate(gf, played),
        "ga_pg": _rate(ga, played),
        "goals_for_pm": _rate(gf, played),
        "goals_against_pm": _rate(ga, played),
        "gd_pg": round((gf - ga) / played, 2) if played else None,
        "shots_for_pm": _rate(shots_for, played),
        "shots_against_pm": _rate(shots_against, played),
        "shots_on_target_for_pm": _rate(sot_for, played),
        "shots_on_target_against_pm": _rate(sot_against, played),
        "corners_for_pm": _rate(corners_for, played),
        "corners_against_pm": _rate(corners_against, played),
        "fouls_for_pm": _rate(fouls_for, played),
        "fouls_against_pm": _rate(fouls_against, played),
        "shot_share": round(shots_for / shot_total, 3) if shot_total else None,
        "conversion": round(gf / shots_for, 3) if shots_for else None,
        "shot_accuracy": round(sot_for / shots_for, 3) if shots_for else None,
        "matches_with_shots": sum(1 for row in items if row.get("shots_for") is not None),
    }


def split_record(
    rows: Iterable[dict[str, Any]],
    *,
    venue: str | None = None,
) -> dict[str, Any]:
    """Record and shot rates for one venue (``H``/``A``) or all matches."""
    filtered = [
        row for row in rows if venue is None or str(row.get("venue") or "").upper() == venue.upper()
    ]
    return record(filtered)


def form_block(
    rows: pl.DataFrame | Iterable[dict[str, Any]],
    *,
    n: int = FORM_WINDOW,
    venue: str | None = None,
    competition_id: str | None = None,
    competition_name: str | None = None,
    season: str | None = None,
) -> dict[str, Any]:
    """Last-``n`` league results plus season home/away splits."""
    items = _rows(rows)
    filtered = [
        row
        for row in items
        if (venue is None or str(row.get("venue") or "").upper() == venue.upper())
        and (competition_id is None or row.get("competition_id") == competition_id)
        and (season is None or str(row.get("season")) == season)
    ]
    filtered.sort(key=lambda row: str(row.get("date") or ""), reverse=True)
    recent = filtered[:n]
    matches = [
        {
            "match_id": row.get("match_id"),
            "date": str(row.get("date") or ""),
            "opponent_id": row.get("opponent_id"),
            "opponent_name": row.get("opponent_name"),
            "venue": row.get("venue"),
            "gf": int(row.get("gf") or 0),
            "ga": int(row.get("ga") or 0),
            "result": row.get("result"),
            "points": int(row.get("points") or 0),
            "competition_name": row.get("competition_name"),
        }
        for row in recent
    ]
    overall = record(filtered)
    home = split_record(filtered, venue="H")
    away = split_record(filtered, venue="A")
    recent_record = record(recent)
    return {
        "basis": "league",
        "sample": {
            "matches": len(recent),
            "season_matches": len(filtered),
            "competition_id": competition_id,
            "competition_name": competition_name,
            "season": season,
            "note": f"Last {len(recent)} of {len(filtered)} league matches.",
        },
        "matches": matches,
        "form": "".join(str(row.get("result") or "?") for row in recent),
        "recent": recent_record,
        "form_points": recent_record["points"],
        "season_record": overall,
        "home": home,
        "away": away,
        "coverage": "available" if filtered else "unavailable",
        "note": (
            "League only. Home and away splits use every league match in the "
            "sample, not just the last five."
        ),
    }


def league_match_rows(
    matches: pl.DataFrame,
    *,
    competition_id: str,
    season: str,
    team_ids: Iterable[str],
) -> pl.DataFrame:
    """Club-perspective rows for every team in one league season."""
    subset = matches.filter(
        (pl.col("competition_id") == competition_id) & (pl.col("season") == season)
    )
    frames = []
    for team_id in team_ids:
        frame = club_match_rows(subset, team_id)
        if frame.height:
            frames.append(frame.with_columns(pl.lit(team_id).alias("team_id")))
    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="vertical_relaxed")


def _team_metric_rows(
    league_rows: pl.DataFrame | Iterable[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _rows(league_rows):
        grouped[str(row.get("team_id"))].append(row)
    return {team_id: record(rows) for team_id, rows in grouped.items()}


def strength_block(
    table: pl.DataFrame | Iterable[dict[str, Any]],
    *,
    team_id: str,
    league_rows: pl.DataFrame | Iterable[dict[str, Any]],
    competition_id: str,
    competition_name: str,
    tier: int | None,
) -> dict[str, Any]:
    """Minimal league row plus within-league percentiles."""
    rows = _rows(table)
    row = next((item for item in rows if item.get("team_id") == team_id), None)
    if row is None:
        return {
            "status": "unavailable",
            "team_id": team_id,
            "competition_id": competition_id,
            "reason": "no_league_table",
        }
    metrics = _team_metric_rows(league_rows)
    values = list(metrics.values())
    played = int(row.get("played") or 0)
    points = int(row.get("points") or 0)
    gf = int(row.get("gf") or 0)
    ga = int(row.get("ga") or 0)
    ppg = round(points / played, 2) if played else None
    own = metrics.get(team_id, {})
    shots_for = own.get("shots_for_pm")
    shots_against = own.get("shots_against_pm")
    shot_share = own.get("shot_share")
    gd_pg = round((gf - ga) / played, 2) if played else None

    ppg_values = [
        round(int(item.get("points") or 0) / int(item.get("played") or 1), 2)
        for item in rows
        if int(item.get("played") or 0) > 0
    ]
    gf_values = [
        round(int(item.get("gf") or 0) / int(item.get("played") or 1), 2)
        for item in rows
        if int(item.get("played") or 0) > 0
    ]
    ga_values = [
        round(int(item.get("ga") or 0) / int(item.get("played") or 1), 2)
        for item in rows
        if int(item.get("played") or 0) > 0
    ]
    gd_values = [
        round(
            (int(item.get("gf") or 0) - int(item.get("ga") or 0)) / int(item.get("played") or 1),
            2,
        )
        for item in rows
        if int(item.get("played") or 0) > 0
    ]
    shots_values = [
        item.get("shots_for_pm") for item in values if item.get("shots_for_pm") is not None
    ]
    share_values = [item.get("shot_share") for item in values if item.get("shot_share") is not None]

    ga_percentile = percentile_rank(ga_values, (ga / played) if played else None)
    percentiles = {
        "ppg": percentile_rank(ppg_values, ppg),
        "gf_pg": percentile_rank(gf_values, (gf / played) if played else None),
        "ga_pg": 100 - ga_percentile if ga_percentile is not None else None,
        "gd_pg": percentile_rank(gd_values, gd_pg),
        "shots_for_pm": percentile_rank(shots_values, shots_for),
        "shot_share": percentile_rank(share_values, shot_share),
    }
    return {
        "status": "available",
        "team_id": team_id,
        "team_name": row.get("team_name"),
        "competition_id": competition_id,
        "competition_name": competition_name,
        "tier": tier,
        "position": row.get("position"),
        "played": played,
        "points": points,
        "ppg": ppg,
        "gf": gf,
        "ga": ga,
        "gd": gf - ga,
        "gf_pg": round(gf / played, 2) if played else None,
        "ga_pg": round(ga / played, 2) if played else None,
        "gd_pg": gd_pg,
        "form": row.get("form"),
        "shots_for_pm": shots_for,
        "shots_against_pm": shots_against,
        "shot_share": shot_share,
        "percentiles": percentiles,
        "coverage": "available" if played >= 4 else "partial",
        "sample_note": f"{played} league matches.",
    }


def strength_comparison(aberdeen: dict[str, Any], opponent: dict[str, Any]) -> dict[str, Any]:
    """Compare two strength blocks without implying a result."""
    if aberdeen.get("status") != "available" or opponent.get("status") != "available":
        return {
            "status": "unavailable",
            "reason": "one_or_both_tables_unavailable",
            "cross_tier": False,
        }
    aberdeen_ppg = aberdeen.get("ppg")
    opponent_ppg = opponent.get("ppg")
    gap = (
        round(float(aberdeen_ppg) - float(opponent_ppg), 2)
        if aberdeen_ppg is not None and opponent_ppg is not None
        else None
    )
    absolute = abs(gap) if gap is not None else None
    if absolute is None:
        descriptor = "unknown"
    elif absolute < 0.15:
        descriptor = "similar"
    elif absolute < 0.35:
        descriptor = "modest edge"
    elif absolute < 0.7:
        descriptor = "clear edge"
    else:
        descriptor = "large gap"
    if gap is None or absolute is None or absolute < 0.15:
        edge = "even"
    elif gap > 0:
        edge = "aberdeen"
    else:
        edge = "opponent"
    played = min(int(aberdeen.get("played") or 0), int(opponent.get("played") or 0))
    confidence = "high" if played >= 8 else "medium" if played >= 4 else "low"
    cross_tier = aberdeen.get("competition_id") != opponent.get("competition_id")
    return {
        "status": "available",
        "position_gap": int(aberdeen.get("position") or 0) - int(opponent.get("position") or 0),
        "ppg_gap": gap,
        "descriptor": descriptor,
        "edge": edge,
        "confidence": confidence,
        "cross_tier": cross_tier,
        "tier_gap": (
            int(aberdeen.get("tier") or 0) - int(opponent.get("tier") or 0)
            if aberdeen.get("tier") is not None and opponent.get("tier") is not None
            else None
        ),
        "note": (
            "Cross-tier comparison: raw values only; percentiles are not like-for-like."
            if cross_tier
            else "Same league: percentiles use the current league table sample."
        ),
    }


def _percentile_for_team(
    league_rows: pl.DataFrame | Iterable[dict[str, Any]],
    *,
    team_id: str,
    metric: str,
    venue: str | None,
) -> int | None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _rows(league_rows):
        if venue is not None and str(row.get("venue") or "").upper() != venue.upper():
            continue
        grouped[str(row.get("team_id"))].append(row)
    values: dict[str, float] = {}
    for key, rows in grouped.items():
        rates = record(rows)
        value = rates.get(metric)
        if value is not None:
            values[key] = float(value)
    return percentile_rank(values.values(), values.get(team_id))


def style_block(
    rows: pl.DataFrame | Iterable[dict[str, Any]],
    *,
    venue: str | None = None,
    season: str | None = None,
    competition_id: str | None = None,
    league_rows: pl.DataFrame | Iterable[dict[str, Any]] | None = None,
    team_id: str | None = None,
    n: int = FORM_WINDOW,
) -> dict[str, Any]:
    """Measured shot proxies for overall or one venue, with league percentiles."""
    items = [
        row
        for row in _rows(rows)
        if (venue is None or str(row.get("venue") or "").upper() == venue.upper())
        and (competition_id is None or row.get("competition_id") == competition_id)
        and (season is None or str(row.get("season")) == season)
    ]
    if not items:
        return {
            "matches": 0,
            "coverage": "unavailable",
            "venue": venue,
            "reason": "no_matches",
            "possession_for_pm": None,
            "possession_against_pm": None,
            "possession_unknown_reason": "not_dependable_in_provider_statistics",
            "note": "No league match rows for this sample.",
        }
    sample_season = str(items[0].get("season") or season or "")
    profile = style_profile(
        pl.DataFrame(items),
        season=sample_season,
        competition_id=None,
    )
    profile["season"] = sample_season
    profile["venue"] = venue or "all"
    profile["matches"] = len(items)
    profile["shot_share"] = (
        round(profile["shots_for_pm"] / (profile["shots_for_pm"] + profile["shots_against_pm"]), 3)
        if profile.get("shots_for_pm") is not None
        and profile.get("shots_against_pm") is not None
        and (profile["shots_for_pm"] + profile["shots_against_pm"]) > 0
        else None
    )
    profile["recent_shot_shares"] = [
        round(
            float(row.get("shots_for") or 0)
            / (float(row.get("shots_for") or 0) + float(row.get("shots_against") or 0)),
            3,
        )
        for row in sorted(items, key=lambda item: str(item.get("date") or ""), reverse=True)[:n]
        if (float(row.get("shots_for") or 0) + float(row.get("shots_against") or 0)) > 0
    ]
    if league_rows is not None and team_id:
        profile["percentiles"] = {
            metric: _percentile_for_team(league_rows, team_id=team_id, metric=metric, venue=venue)
            for metric in (
                "shots_for_pm",
                "shots_against_pm",
                "shot_share",
                "goals_for_pm",
                "goals_against_pm",
                "shots_on_target_for_pm",
                "corners_for_pm",
                "fouls_for_pm",
                "conversion",
                "shot_accuracy",
            )
        }
    else:
        profile["percentiles"] = {}
    profile["possession_unknown_reason"] = "not_dependable_in_provider_statistics"
    profile["possession_for_pm"] = None
    profile["possession_against_pm"] = None
    profile["note"] = (
        "Opponent-unadjusted shot proxies from league match rows. Not xG and "
        "not a tactical model. Possession is unknown and is not used."
    )
    return profile


def _consistency(recent: list[float], shot_share: float | None) -> int:
    if shot_share is None:
        return 0
    side = shot_share >= 0.5
    return sum(1 for value in recent[:5] if (value >= 0.5) == side)


def style_lean(
    overall: dict[str, Any],
    venue: dict[str, Any],
    *,
    policy: dict[str, Any],
    venue_label: str | None = None,
) -> dict[str, Any]:
    """Three-way approach from measured shot percentiles."""
    weights = {
        "shots_for_pm": float(policy.get("weights", {}).get("shots_for", 0.40)),
        "shot_share": float(policy.get("weights", {}).get("shot_share", 0.25)),
        "goals_for_pm": float(policy.get("weights", {}).get("goals_for", 0.20)),
        "shots_on_target_for_pm": float(policy.get("weights", {}).get("shots_on_target_for", 0.15)),
    }

    def index_for(profile: dict[str, Any]) -> tuple[float | None, list[str]]:
        percentiles = profile.get("percentiles") or {}
        used: list[tuple[float, float]] = []
        missing: list[str] = []
        for metric, weight in weights.items():
            value = percentiles.get(metric)
            if value is None:
                missing.append(metric)
            else:
                used.append((float(value), weight))
        if len(used) < 2:
            return None, missing
        total = sum(weight for _, weight in used)
        return round(sum(value * weight for value, weight in used) / total, 1), missing

    overall_index, missing = index_for(overall)
    venue_index, venue_missing = index_for(venue)
    if overall_index is None:
        return {
            "approach": "unknown",
            "label": LEAN_LABELS["unknown"],
            "confidence": "low",
            "approach_index": None,
            "venue_index": None,
            "overall_index": None,
            "evidence": [],
            "basis": "measured",
            "interpretation": "inferred",
            "reason": "insufficient_style_metrics",
            "missing_metrics": missing,
        }

    venue_matches = int(venue.get("matches") or 0)
    venue_min = int(policy.get("venue_min_matches", 3))
    use_venue = venue_index is not None and venue_matches >= venue_min
    if use_venue and venue_index is not None:
        combined = round(
            float(policy.get("venue_weight", 0.6)) * venue_index
            + float(policy.get("overall_weight", 0.4)) * overall_index,
            1,
        )
    else:
        combined = overall_index
    shot_share = (venue if use_venue else overall).get("shot_share")
    attack_threshold = float(policy.get("attack_index", 60))
    counter_threshold = float(policy.get("counter_index", 40))
    attack_share = float(policy.get("attack_shot_share", 0.50))
    counter_share = float(policy.get("counter_shot_share", 0.48))

    upper_percentiles = overall.get("percentiles") or {}
    counter_signal = (
        (upper_percentiles.get("goals_for_pm") or 0) >= 40
        or (upper_percentiles.get("shots_on_target_for_pm") or 0) >= 40
        or (upper_percentiles.get("conversion") or 0) >= 60
    )
    if combined >= attack_threshold and shot_share is not None and shot_share >= attack_share:
        approach = "attack"
    elif combined <= counter_threshold and shot_share is not None and shot_share <= counter_share:
        approach = "sit_deep_counter"
    else:
        approach = "balanced"

    matches = int(overall.get("matches") or 0)
    full_coverage = overall.get("coverage") == "available"
    consistent = _consistency(overall.get("recent_shot_shares") or [], overall.get("shot_share"))
    if matches >= 8 and full_coverage and consistent >= 4 and venue_matches >= venue_min:
        confidence = "high"
    elif matches >= 4 and consistent >= 3:
        confidence = "medium"
    else:
        confidence = "low"
    if use_venue and venue.get("coverage") != "available":
        confidence = "low" if confidence == "high" else confidence
    if approach == "sit_deep_counter" and not counter_signal:
        confidence = "low"

    def pct(profile: dict[str, Any], key: str) -> str:
        value = (profile.get("percentiles") or {}).get(key)
        return f"{_ordinal(int(value))} percentile" if value is not None else "percentile unknown"

    evidence = []
    if overall.get("shots_for_pm") is not None:
        evidence.append(
            f"{overall['shots_for_pm']:.1f} shots per match ({pct(overall, 'shots_for_pm')})"
        )
    if overall.get("shot_share") is not None:
        evidence.append(f"shot share {overall['shot_share'] * 100:.0f}%")
    if overall.get("goals_for_pm") is not None:
        evidence.append(
            f"{overall['goals_for_pm']:.2f} goals per match ({pct(overall, 'goals_for_pm')})"
        )
    if use_venue and venue.get("shots_for_pm") is not None:
        evidence.append(
            f"{venue_label or 'in this venue'}: {venue['shots_for_pm']:.1f} shots "
            f"per match in {venue_matches} matches"
        )
    elif venue_matches:
        evidence.append(
            f"Venue sample is {venue_matches} matches; the overall profile carries the read."
        )
    if approach == "sit_deep_counter" and not counter_signal:
        evidence.append(
            "Low volume and low shot share, but the counter punch is not "
            "established by goals or shot quality."
        )
    if missing:
        evidence.append("Missing metrics: " + ", ".join(sorted(set(missing))))

    return {
        "approach": approach,
        "label": LEAN_LABELS[approach],
        "confidence": confidence,
        "approach_index": combined,
        "venue_index": venue_index,
        "overall_index": overall_index,
        "shot_share": shot_share,
        "venue_matches": venue_matches,
        "venue_used": use_venue,
        "evidence": evidence,
        "basis": "measured",
        "interpretation": "inferred",
        "missing_metrics": sorted(set(missing + venue_missing)),
        "note": (
            "Shot proxies only. Not xG, not a tactical model, and possession is "
            "unknown. The lean describes the measured profile; it is not a "
            "prediction of the result."
        ),
    }


def select_formation(
    shape_rows: pl.DataFrame | Iterable[dict[str, Any]],
    *,
    window: int = 6,
    recency_weights: list[float] | None = None,
) -> dict[str, Any]:
    """Recency-weighted mode of observed formations."""
    rows = [row for row in _rows(shape_rows) if row.get("formation") or row.get("formation_shape")]
    rows.sort(key=lambda row: str(row.get("date") or ""), reverse=True)
    rows = rows[:window]
    if not rows:
        return {
            "formation": None,
            "confidence": "unknown",
            "basis": "unobserved",
            "matches": 0,
            "window": window,
            "note": "No observed formation in the lineup window.",
        }
    weights = recency_weights or [float(window - index) for index in range(window)]
    totals: dict[str, float] = defaultdict(float)
    counts: Counter[str] = Counter()
    first_seen: dict[str, int] = {}
    for index, row in enumerate(rows):
        formation = str(row.get("formation") or row.get("formation_shape"))
        weight = float(weights[index]) if index < len(weights) else 1.0
        totals[formation] += weight
        counts[formation] += 1
        first_seen.setdefault(formation, index)
    ordered = sorted(
        totals,
        key=lambda formation: (-totals[formation], first_seen[formation]),
    )
    formation = ordered[0]
    total_weight = sum(totals.values())
    share = totals[formation] / total_weight if total_weight else 0.0
    if share >= 0.6 and counts[formation] >= 4:
        confidence = "high"
    elif share >= 0.35 and counts[formation] >= 2:
        confidence = "medium"
    else:
        confidence = "low"
    return {
        "formation": formation,
        "confidence": confidence,
        "basis": "observed",
        "matches": counts[formation],
        "window": len(rows),
        "weighted_share": round(share, 3),
        "formations_seen": dict(counts.most_common()),
        "note": f"Most common formation in the last {len(rows)} lineups.",
    }


def _position_group(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    return POSITION_GROUP.get(text)


def _fixture_order(
    appearances: pl.DataFrame | Iterable[dict[str, Any]],
    *,
    window: int,
) -> list[str]:
    fixtures: dict[str, str] = {}
    for row in _rows(appearances):
        fixture_id = row.get("fixture_id")
        if fixture_id is None:
            continue
        fixtures[str(fixture_id)] = str(row.get("date") or "")
    return [
        fixture
        for fixture, _ in sorted(fixtures.items(), key=lambda item: item[1], reverse=True)[:window]
    ]


def score_players(
    appearances: pl.DataFrame | Iterable[dict[str, Any]],
    *,
    window: int = 6,
    recency_weights: list[float] | None = None,
    squad: pl.DataFrame | Iterable[dict[str, Any]] | None = None,
    include_squad_only: bool = False,
    availability: dict[int, dict[str, Any]] | None = None,
    availability_state: str = "unavailable",
) -> dict[str, Any]:
    """Aggregate observed player selection and form over the lineup window."""
    rows = _rows(appearances)
    fixtures = _fixture_order(rows, window=window)
    fixture_index = {fixture: index for index, fixture in enumerate(fixtures)}
    weights = recency_weights or [float(window - index) for index in range(window)]
    weight_for = {
        fixture: float(weights[index]) if index < len(weights) else 1.0
        for fixture, index in fixture_index.items()
    }
    total_weight = sum(weight_for.values())
    squad_by_id = {
        int(item["player_id"]): item for item in _rows(squad) if item.get("player_id") is not None
    }
    players: dict[int, dict[str, Any]] = {}
    for row in rows:
        fixture = str(row.get("fixture_id"))
        if fixture not in fixture_index:
            continue
        player_id = _int(row.get("player_id"))
        if player_id is None:
            continue
        entry = players.setdefault(
            player_id,
            {
                "player_id": player_id,
                "player_key": row.get("player_key") or f"api:player:{player_id}",
                "name": row.get("player_name") or f"Player {player_id}",
                "starts": 0,
                "appearances": 0,
                "minutes": 0,
                "goals": 0,
                "assists": 0,
                "yellow_cards": 0,
                "red_cards": 0,
                "started_fixtures": [],
                "minutes_by_fixture": {},
                "role_codes": Counter(),
                "role_families": Counter(),
                "last_seen": str(row.get("date") or ""),
                "position_group": _position_group(row.get("position")),
                "shirt_number": _int(row.get("shirt_number")),
                "_weighted_starts": 0.0,
                "_weighted_minutes": 0.0,
                "_weighted_involvement": 0.0,
                "_weighted_rating": 0.0,
                "_rating_weight": 0.0,
                "rating_count": 0,
                "_weighted_played": 0.0,
            },
        )
        started = _label_bool(row.get("started"))
        entry["appearances"] += 1
        entry["starts"] += 1 if started else 0
        entry["minutes"] += int(row.get("minutes") or 0)
        entry["goals"] += int(row.get("goals") or 0)
        entry["assists"] += int(row.get("assists") or 0)
        entry["yellow_cards"] += int(row.get("yellow_cards") or 0)
        entry["red_cards"] += int(row.get("red_cards") or 0)
        if started:
            entry["started_fixtures"].append(fixture)
        entry["minutes_by_fixture"][fixture] = int(row.get("minutes") or 0)
        role_code = row.get("role_code")
        role_family = row.get("role_family")
        if role_code:
            entry["role_codes"][str(role_code)] += 1
        if role_family:
            entry["role_families"][str(role_family)] += 1
        if row.get("player_name"):
            entry["name"] = row["player_name"]
        if row.get("shirt_number") is not None:
            entry["shirt_number"] = _int(row.get("shirt_number"))
        if entry.get("position_group") is None:
            entry["position_group"] = _position_group(row.get("position"))
        weight = weight_for[fixture]
        entry["_weighted_played"] += weight
        entry["_weighted_starts"] += weight if started else 0.0
        entry["_weighted_minutes"] += weight * min(int(row.get("minutes") or 0) / 90.0, 1.0)
        involvement = int(row.get("goals") or 0) + 0.5 * int(row.get("assists") or 0)
        entry["_weighted_involvement"] += weight * involvement
        rating = _number(row.get("rating"))
        if rating is not None:
            entry["_weighted_rating"] += weight * rating
            entry["_rating_weight"] += weight
            entry["rating_count"] += 1

    if include_squad_only:
        for player_id, item in squad_by_id.items():
            if player_id in players or item.get("status") == "loan_out":
                continue
            players[player_id] = {
                "player_id": player_id,
                "player_key": item.get("player_key") or f"api:player:{player_id}",
                "name": item.get("name") or f"Player {player_id}",
                "starts": 0,
                "appearances": 0,
                "minutes": 0,
                "goals": 0,
                "assists": 0,
                "yellow_cards": 0,
                "red_cards": 0,
                "started_fixtures": [],
                "minutes_by_fixture": {},
                "role_codes": Counter(),
                "role_families": Counter(),
                "last_seen": None,
                "position_group": _position_group(
                    item.get("position_group") or item.get("position")
                ),
                "shirt_number": _int(item.get("number")),
                "_weighted_starts": 0.0,
                "_weighted_minutes": 0.0,
                "_weighted_involvement": 0.0,
                "_weighted_rating": 0.0,
                "_rating_weight": 0.0,
                "rating_count": 0,
                "_weighted_played": 0.0,
            }

    output = []
    fixture_count = len(fixtures)
    for entry in players.values():
        squad_row = squad_by_id.get(entry["player_id"], {})
        if entry["name"].startswith("Player ") and squad_row.get("name"):
            entry["name"] = squad_row["name"]
        observed = fixture_count > 0 and entry["appearances"] > 0
        start_rate = entry["starts"] / fixture_count if fixture_count else 0.0
        minute_share = min(1.0, entry["minutes"] / (90.0 * fixture_count)) if fixture_count else 0.0
        recency_start = entry["_weighted_starts"] / total_weight if total_weight else 0.0
        recency_minute_share = entry["_weighted_minutes"] / total_weight if total_weight else 0.0
        goal_involvement = (
            min(1.0, entry["_weighted_involvement"] / max(total_weight, 1.0))
            if total_weight
            else 0.0
        )
        form = 0.7 * recency_minute_share + 0.3 * goal_involvement
        recent_rating = (
            round(entry["_weighted_rating"] / entry["_rating_weight"], 2)
            if entry["_rating_weight"]
            else None
        )
        recent_rating_score = (
            max(0.0, min(1.0, (recent_rating - 6.0) / 2.0)) if recent_rating is not None else None
        )
        rating_coverage = (
            "available"
            if fixture_count and entry["rating_count"] >= max(1, int(fixture_count * 0.6))
            else "partial"
            if entry["rating_count"]
            else "unavailable"
        )
        role_code = entry["role_codes"].most_common(1)[0][0] if entry["role_codes"] else None
        role_family = (
            entry["role_families"].most_common(1)[0][0] if entry["role_families"] else None
        )
        injured = _label_bool(squad_row.get("injured")) if squad_row else False
        squad_status = squad_row.get("status")
        availability_row = (availability or {}).get(entry["player_id"], {})
        availability_status = str(availability_row.get("status") or "unknown")
        if availability_status not in {
            "out",
            "doubtful",
            "suspended",
            "returned",
            "available",
            "unknown",
        }:
            availability_status = "unknown"
        availability_downgrade = 0
        available = squad_status != "loan_out"
        unavailable_reason = None
        if availability_status in {"out", "suspended"}:
            available = False
            unavailable_reason = f"availability_{availability_status}"
        elif squad_status == "loan_out":
            unavailable_reason = "loan_out"
        elif availability_status == "doubtful":
            availability_downgrade = 1
        elif availability_row.get("conflict"):
            availability_downgrade = 2
        elif availability_row.get("stale") or (
            availability_status == "unknown" and availability_state == "partial"
        ):
            availability_downgrade = 1
        output.append(
            {
                "player_id": entry["player_id"],
                "player_key": entry["player_key"],
                "name": entry["name"],
                "shirt_number": entry["shirt_number"],
                "position_group": entry["position_group"],
                "role_code": role_code,
                "role_family": role_family,
                "appearances": entry["appearances"],
                "starts": entry["starts"],
                "minutes": entry["minutes"],
                "goals": entry["goals"],
                "assists": entry["assists"],
                "yellow_cards": entry["yellow_cards"],
                "red_cards": entry["red_cards"],
                "start_rate": round(start_rate, 3),
                "minute_share": round(minute_share, 3),
                "recency_start": round(recency_start, 3),
                "recency_minute_share": round(recency_minute_share, 3),
                "form": round(form, 3),
                "recent_rating": recent_rating,
                "recent_rating_score": (
                    round(recent_rating_score, 3) if recent_rating_score is not None else None
                ),
                "rating_count": entry["rating_count"],
                "rating_coverage": rating_coverage,
                "last_seen": entry["last_seen"],
                "observed": observed,
                "injured": injured,
                "available": available,
                "unavailable_reason": unavailable_reason,
                "status": squad_status,
                "availability_status": availability_status,
                "availability_confidence": availability_row.get("confidence"),
                "availability_source": availability_row.get("source_id"),
                "availability_source_url": availability_row.get("source_url"),
                "availability_verified_at": availability_row.get("verified_at"),
                "availability_note": availability_row.get("note"),
                "availability_conflict": bool(availability_row.get("conflict")),
                "availability_downgrade": availability_downgrade,
                "href": f"/players/{entry['player_id']}/" if squad_row else None,
            }
        )
    output.sort(
        key=lambda item: (
            item["recency_start"],
            item["start_rate"],
            item["minutes"],
            item["name"],
        ),
        reverse=True,
    )
    return {
        "fixtures": fixtures,
        "fixture_count": fixture_count,
        "players": output,
        "note": (
            f"Selection window: last {fixture_count} matches with lineups. "
            "Availability is taken from the curated team-news ledger; a "
            "provider injury boolean is not team news."
        ),
    }


def _role_fit(
    target: str,
    player: dict[str, Any],
    *,
    policy: dict[str, Any],
) -> float:
    adjacency = policy.get("role_adjacency") or {}
    role_code = player.get("role_code")
    if role_code and target in (adjacency.get(str(role_code)) or {}):
        return float(adjacency[str(role_code)][target])
    group = player.get("position_group")
    if group:
        group_fit = (policy.get("position_group_fit") or {}).get(str(group)) or {}
        if target in group_fit:
            return float(group_fit[target])
    return 0.0


def _slot_list(formation: str, roles_config: dict[str, Any]) -> list[dict[str, Any]] | None:
    formation_map = (roles_config.get("formations") or {}).get(formation)
    if not formation_map:
        return None
    roles = roles_config.get("roles") or {}
    slots = []
    for row_index, row in enumerate(formation_map):
        for column_index, role_code in enumerate(row):
            slots.append(
                {
                    "slot": f"{row_index + 1}:{column_index + 1}",
                    "grid": f"{row_index + 1}:{column_index + 1}",
                    "row": row_index,
                    "column": column_index,
                    "role_code": role_code,
                    "role_label": (roles.get(role_code) or {}).get("label", role_code),
                    "role_family": (roles.get(role_code) or {}).get("family"),
                }
            )
    return slots


def _score(components: dict[str, Any], role_fit: float, policy: dict[str, Any]) -> float:
    weights = policy.get("scoring") or {}
    values = {
        "start_rate": float(components.get("start_rate") or 0),
        "recency_start": float(components.get("recency_start") or 0),
        "minute_share": float(components.get("minute_share") or 0),
        "role_fit": float(role_fit or 0),
        "form": float(components.get("form") or 0),
        "recent_rating": components.get("recent_rating_score"),
    }
    defaults = {
        "start_rate": 0.22,
        "recency_start": 0.18,
        "minute_share": 0.10,
        "role_fit": 0.15,
        "form": 0.20,
        "recent_rating": 0.15,
    }
    available = [
        (float(weights.get(key, defaults[key])), float(value))
        for key, value in values.items()
        if value is not None
    ]
    total_weight = sum(weight for weight, _ in available)
    if not total_weight:
        return 0.0
    return sum(weight * value for weight, value in available) / total_weight


def assign_lineup(
    candidates: list[dict[str, Any]],
    *,
    formation: str,
    roles_config: dict[str, Any],
    policy: dict[str, Any],
    contenders: int = 6,
) -> dict[str, Any]:
    """Assign observed candidates to formation slots, greedily and visibly."""
    slots = _slot_list(formation, roles_config)
    if slots is None:
        return {
            "status": "unavailable",
            "reason": "formation_unmapped",
            "formation": formation,
            "players": [],
            "contenders": [],
            "filled": 0,
            "note": f"Formation {formation} is not mapped in config/roles.yaml.",
        }
    available = [
        player
        for player in candidates
        if player.get("observed")
        and int(player.get("minutes") or 0) > 0
        and player.get("available", True)
    ]
    assigned: set[int] = set()
    picks: list[dict[str, Any]] = []
    contenders_by_slot: list[dict[str, Any]] = []
    min_role_fit = float(policy.get("min_role_fit", 0.3))
    for slot in slots:
        target = str(slot["role_code"])
        scored = []
        for player in available:
            if player["player_id"] in assigned:
                continue
            fit = _role_fit(target, player, policy=policy)
            score = _score(player, fit, policy)
            slot_score = score * (0.5 + 0.5 * fit)
            if target == "GK" and not (
                player.get("role_family") == "goalkeeper" or player.get("position_group") == "GK"
            ):
                continue
            scored.append((slot_score, fit, score, player))
        scored.sort(key=lambda item: (-item[0], -item[1], -item[2]))
        eligible = [item for item in scored if item[1] >= min_role_fit]
        chosen = eligible[0] if eligible else (scored[0] if scored else None)
        if chosen is None:
            picks.append(
                {
                    **slot,
                    "player_id": None,
                    "name": None,
                    "role_fit": None,
                    "score": None,
                    "confidence": "unknown",
                    "reason": "No eligible player in the observed window.",
                }
            )
            continue
        slot_score, fit, score, player = chosen
        margin = slot_score - eligible[1][0] if len(eligible) > 1 else slot_score
        assigned.add(player["player_id"])
        if margin >= 0.10 and player["start_rate"] >= 0.6 and fit >= 0.8:
            confidence = "high"
        elif margin >= 0.05 and player["start_rate"] >= 0.4 and fit >= 0.5:
            confidence = "medium"
        else:
            confidence = "low"
        picks.append(
            {
                **slot,
                "player_id": player["player_id"],
                "player_key": player.get("player_key"),
                "name": player["name"],
                "shirt_number": player.get("shirt_number"),
                "href": player.get("href"),
                "role_family": player.get("role_family") or slot.get("role_family"),
                "role_fit": round(fit, 3),
                "score": round(slot_score, 3),
                "confidence": confidence,
                "starts": player.get("starts"),
                "minutes": player.get("minutes"),
                "recency_start": player.get("recency_start"),
                "form": player.get("form"),
                "recent_rating": player.get("recent_rating"),
                "recent_rating_score": player.get("recent_rating_score"),
                "rating_count": player.get("rating_count"),
                "rating_coverage": player.get("rating_coverage"),
                "last_seen": player.get("last_seen"),
                "availability_status": player.get("availability_status", "unknown"),
                "availability_confidence": player.get("availability_confidence"),
                "availability_source": player.get("availability_source"),
                "availability_source_url": player.get("availability_source_url"),
                "availability_verified_at": player.get("availability_verified_at"),
                "availability_note": player.get("availability_note"),
                "availability_conflict": player.get("availability_conflict", False),
                "availability_downgrade": player.get("availability_downgrade", 0),
                "reason": (
                    f"{player.get('starts', 0)} starts, "
                    f"{player.get('minutes', 0)} minutes in the window; "
                    f"role fit {fit:.2f}; form {player.get('form', 0):.2f}; "
                    f"recent rating {player.get('recent_rating') or '—'}."
                ),
            }
        )
        alternatives = [item for item in eligible if item[3]["player_id"] not in assigned]
        for alternative in alternatives[:2]:
            alt_score, alt_fit, _, alt_player = alternative
            contenders_by_slot.append(
                {
                    "player_id": alt_player["player_id"],
                    "player_key": alt_player.get("player_key"),
                    "name": alt_player["name"],
                    "shirt_number": alt_player.get("shirt_number"),
                    "href": alt_player.get("href"),
                    "slot": slot["slot"],
                    "role_code": target,
                    "role_label": slot.get("role_label"),
                    "role_fit": round(alt_fit, 3),
                    "score": round(alt_score, 3),
                    "starts": alt_player.get("starts"),
                    "minutes": alt_player.get("minutes"),
                    "form": alt_player.get("form"),
                    "recent_rating": alt_player.get("recent_rating"),
                    "recent_rating_score": alt_player.get("recent_rating_score"),
                    "rating_count": alt_player.get("rating_count"),
                    "rating_coverage": alt_player.get("rating_coverage"),
                    "availability_status": alt_player.get("availability_status", "unknown"),
                    "availability_confidence": alt_player.get("availability_confidence"),
                    "availability_source": alt_player.get("availability_source"),
                    "availability_note": alt_player.get("availability_note"),
                    "availability_conflict": alt_player.get("availability_conflict", False),
                    "availability_downgrade": alt_player.get("availability_downgrade", 0),
                    "confidence": (
                        "medium" if alt_player["start_rate"] >= 0.4 and alt_fit >= 0.5 else "low"
                    ),
                    "reason": (
                        f"Alternative for {slot.get('role_label')}; "
                        f"{alt_player.get('starts', 0)} starts in the window."
                    ),
                }
            )

    deduped: list[dict[str, Any]] = []
    seen: set[int] = set()
    for item in sorted(contenders_by_slot, key=lambda value: (-value["score"], value["name"])):
        if item["player_id"] in assigned or item["player_id"] in seen:
            continue
        seen.add(item["player_id"])
        deduped.append(item)
        if len(deduped) >= contenders:
            break
    if len(deduped) < 4:
        extras = [
            player
            for player in available
            if player["player_id"] not in assigned and player["player_id"] not in seen
        ]
        extras.sort(
            key=lambda player: (-player["recency_start"], -player["start_rate"], player["name"])
        )
        for player in extras:
            if len(deduped) >= min(4, contenders):
                break
            deduped.append(
                {
                    "player_id": player["player_id"],
                    "player_key": player.get("player_key"),
                    "name": player["name"],
                    "shirt_number": player.get("shirt_number"),
                    "href": player.get("href"),
                    "slot": None,
                    "role_code": player.get("role_code"),
                    "role_label": None,
                    "role_fit": 0.0,
                    "score": round(_score(player, 0.0, policy), 3),
                    "starts": player.get("starts"),
                    "minutes": player.get("minutes"),
                    "form": player.get("form"),
                    "recent_rating": player.get("recent_rating"),
                    "recent_rating_score": player.get("recent_rating_score"),
                    "rating_count": player.get("rating_count"),
                    "rating_coverage": player.get("rating_coverage"),
                    "availability_status": player.get("availability_status", "unknown"),
                    "availability_confidence": player.get("availability_confidence"),
                    "availability_source": player.get("availability_source"),
                    "availability_note": player.get("availability_note"),
                    "availability_conflict": player.get("availability_conflict", False),
                    "availability_downgrade": player.get("availability_downgrade", 0),
                    "confidence": "low",
                    "reason": "Next-best observed player; no clear slot fit.",
                }
            )
            seen.add(player["player_id"])

    filled = sum(1 for pick in picks if pick.get("player_id") is not None)
    return {
        "status": "available" if filled == len(slots) else "partial",
        "formation": formation,
        "players": picks,
        "contenders": deduped,
        "filled": filled,
        "slots": slots,
        "slot_count": len(slots),
        "note": (
            "Greedy slot assignment. Goalkeeper is assigned first; outfield "
            "players are never placed in goal."
        ),
    }


def _downgrade(confidence: str, levels: int = 1) -> str:
    order = ["unknown", "low", "medium", "high"]
    index = max(0, order.index(confidence) - levels) if confidence in order else 0
    return order[index]


def predict_lineup(
    appearances: pl.DataFrame | Iterable[dict[str, Any]],
    shape_rows: pl.DataFrame | Iterable[dict[str, Any]],
    *,
    team_id: int | str,
    roles_config: dict[str, Any],
    policy: dict[str, Any],
    squad: pl.DataFrame | Iterable[dict[str, Any]] | None = None,
    fixtures_total: int | None = None,
    include_squad_only: bool = False,
    recent_fixtures: int = 6,
    contenders: int = 6,
    availability: dict[int, dict[str, Any]] | None = None,
    availability_state: str = "unavailable",
    availability_as_of: str | None = None,
    availability_source_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Predict an XI and 4-6 contenders from observed lineups."""
    scored = score_players(
        appearances,
        window=recent_fixtures,
        recency_weights=(policy.get("recency_weights") or None),
        squad=squad,
        include_squad_only=include_squad_only,
        availability=availability,
        availability_state=availability_state,
    )
    fixture_count = int(scored["fixture_count"])
    coverage = (
        round(fixture_count / fixtures_total, 3) if fixtures_total and fixtures_total > 0 else None
    )
    formation = select_formation(
        shape_rows,
        window=int(policy.get("formation_window", recent_fixtures)),
        recency_weights=(policy.get("recency_weights") or None),
    )
    unavailable = [
        {
            "player_id": player["player_id"],
            "name": player["name"],
            "reason": player.get("unavailable_reason") or "unavailable",
        }
        for player in scored["players"]
        if not player.get("available", True)
    ]
    availability_entries = list((availability or {}).values())
    status_counts = {
        status: sum(1 for entry in availability_entries if entry.get("status") == status)
        for status in ("out", "suspended", "doubtful", "returned", "available", "unknown")
    }
    availability_known = sum(
        status_counts[status]
        for status in ("out", "suspended", "doubtful", "returned", "available")
    )
    availability_conflicts = sum(1 for entry in availability_entries if entry.get("conflict"))
    availability_summary = {
        "state": availability_state,
        "known": availability_known,
        "unknown": status_counts["unknown"],
        "out": status_counts["out"],
        "suspended": status_counts["suspended"],
        "doubtful": status_counts["doubtful"],
        "returned": status_counts["returned"],
        "conflicts": availability_conflicts,
        "as_of": availability_as_of,
        "source_ids": availability_source_ids or [],
        "note": ("Curated team-news availability. A provider injury boolean is not team news."),
    }
    if include_squad_only is False:
        availability_note = "No provider team-news feed for the opponent; availability is unknown."
    elif availability_state == "partial":
        availability_note = (
            "Curated AFC team news"
            + (f" as of {availability_as_of}" if availability_as_of else "")
            + "; provider injuries unavailable/empty."
        )
    else:
        availability_note = (
            "No verified team-news entries; availability is unknown, not assumed fit."
        )
    rating_coverage = Counter(
        str(player.get("rating_coverage") or "unavailable") for player in scored["players"]
    )
    base = {
        "team_id": team_id,
        "formation": formation.get("formation"),
        "selection": {
            "weights": policy.get("scoring") or {},
            "rating_coverage": dict(rating_coverage),
            "note": (
                "Selection uses starts, recency, minutes, role fit, form and "
                "recent provider ratings. Ratings are a selection signal, not a "
                "fitba rating or an individual verdict."
            ),
        },
        "formation_confidence": formation.get("confidence"),
        "formation_detail": formation,
        "coverage": {
            "fixtures_with_lineups": fixture_count,
            "fixtures_total": fixtures_total,
            "lineup_coverage": coverage,
            "window": recent_fixtures,
        },
        "disclaimer": (
            "Predicted, not official team news. Based on recent starts, minutes, "
            "formation and position fit."
        ),
        "unavailable": unavailable,
        "availability": availability_summary,
        "unknowns": [availability_note],
    }
    if fixture_count < 3:
        return {
            **base,
            "status": "unavailable",
            "reason": "insufficient_lineups",
            "players": [],
            "contenders": [],
            "filled": 0,
            "team_confidence": "unknown",
            "note": (
                f"Only {fixture_count} matches with lineups in the window; "
                "at least 3 are needed for a prediction."
            ),
        }
    if not formation.get("formation"):
        return {
            **base,
            "status": "unavailable",
            "reason": "no_observed_formation",
            "players": [],
            "contenders": [],
            "filled": 0,
            "team_confidence": "unknown",
            "note": "No observed formation; a shape is not assumed.",
        }
    assigned = assign_lineup(
        scored["players"],
        formation=str(formation["formation"]),
        roles_config=roles_config,
        policy=policy,
        contenders=contenders,
    )
    if assigned.get("status") == "unavailable":
        return {
            **base,
            "status": "unavailable",
            "reason": assigned.get("reason"),
            "players": [],
            "contenders": [],
            "filled": 0,
            "team_confidence": "unknown",
            "note": assigned.get("note"),
        }
    downgrade = 0
    if coverage is not None and coverage < 0.6:
        downgrade = 1
    if coverage is not None and coverage < 0.3:
        downgrade = 3
    players = []
    selection_risks = []
    for player in assigned["players"]:
        confidence = player.get("confidence", "unknown")
        player_downgrade = int(player.get("availability_downgrade") or 0)
        if downgrade or player_downgrade:
            confidence = _downgrade(confidence, downgrade + player_downgrade)
        players.append({**player, "confidence": confidence})
        status = str(player.get("availability_status") or "unknown")
        if status in {"doubtful", "out", "suspended"} or player.get("availability_conflict"):
            selection_risks.append(
                {
                    "player_id": player.get("player_id"),
                    "name": player.get("name"),
                    "status": status,
                    "note": player.get("availability_note"),
                }
            )
    high = sum(1 for player in players if player.get("confidence") == "high")
    medium = sum(1 for player in players if player.get("confidence") == "medium")
    if formation.get("confidence") == "high" and high >= 9:
        team_confidence = "high"
    elif high + medium >= 7:
        team_confidence = "medium"
    else:
        team_confidence = "low"
    if coverage is not None and coverage < 0.3:
        team_confidence = "low"
    if availability_state == "partial":
        known_share = (
            availability_known / len(availability_entries) if availability_entries else 0.0
        )
        if known_share < 0.5:
            team_confidence = _downgrade(team_confidence, 1)
        if availability_conflicts:
            team_confidence = _downgrade(team_confidence, 1)
    slot_count = int(assigned.get("slot_count") or 0)
    if assigned.get("filled", 0) < slot_count:
        team_confidence = "unknown"
    status = "available"
    if coverage is not None and coverage < 0.6:
        status = "partial"
    if assigned.get("filled", 0) < slot_count:
        status = "partial"
    note = (
        f"Formation {formation['formation']} in "
        f"{formation.get('matches', 0)} of the last {formation.get('window', 0)} "
        f"lineups. {assigned.get('filled', 0)}/{slot_count} slots filled."
    )
    if coverage is not None:
        note += f" Lineup coverage {coverage * 100:.0f}%."
    return {
        **base,
        "status": status,
        "players": players,
        "contenders": assigned.get("contenders", []),
        "filled": assigned.get("filled", 0),
        "team_confidence": team_confidence,
        "selection_risks": selection_risks,
        "note": note,
        "assignment_note": assigned.get("note"),
    }


def _first_evidence(lean: dict[str, Any]) -> str:
    evidence = lean.get("evidence") or []
    return evidence[0] if evidence else "no usable shot sample"


def matchup_read(
    *,
    fixture: dict[str, Any],
    aberdeen: dict[str, Any],
    opponent: dict[str, Any],
) -> dict[str, Any]:
    """A deterministic, evidence-led read. It never predicts a result."""
    opponent_name = (
        fixture.get("opponent_name") or (opponent.get("team") or {}).get("name") or "The opponent"
    )
    aberdeen_venue = str(fixture.get("venue") or "").upper()
    opponent_venue = "A" if aberdeen_venue == "H" else "H" if aberdeen_venue == "A" else ""
    venue_label = (
        "at home" if opponent_venue == "H" else "away" if opponent_venue == "A" else "in this venue"
    )
    opponent_lean = (opponent.get("style") or {}).get("lean") or {}
    aberdeen_lean = (aberdeen.get("style") or {}).get("lean") or {}
    opponent_style = (opponent.get("style") or {}).get("venue") or {}
    aberdeen_style = (aberdeen.get("style") or {}).get("venue") or {}
    comparison = opponent.get("strength_comparison") or aberdeen.get("strength_comparison") or {}
    opponent_strength = opponent.get("strength") or {}
    aberdeen_strength = aberdeen.get("strength") or {}
    bullets = [
        {
            "text": (
                f"{opponent_name} profile as {opponent_lean.get('label', 'unknown').lower()} "
                f"{venue_label}: {_first_evidence(opponent_lean)}."
            ),
            "basis": "inferred",
        },
        {
            "text": (
                f"Venue effect: their approach index is "
                f"{opponent_lean.get('approach_index', 'unknown')} "
                f"(overall {opponent_lean.get('overall_index', 'unknown')}); "
                f"Aberdeen's is {aberdeen_lean.get('approach_index', 'unknown')}."
            ),
            "basis": "inferred",
        },
    ]
    if comparison.get("status") == "available":
        bullets.append(
            {
                "text": (
                    f"Strength: {opponent_name} are {opponent_strength.get('position')}th "
                    f"on {opponent_strength.get('ppg')} PPG; Aberdeen are "
                    f"{aberdeen_strength.get('position')}th on "
                    f"{aberdeen_strength.get('ppg')} PPG. "
                    f"The table gap is {comparison.get('descriptor')}."
                ),
                "basis": "measured",
            }
        )
    lineup = opponent.get("lineup") or {}
    if lineup.get("status") in {"available", "partial"}:
        high = sum(1 for player in lineup.get("players", []) if player.get("confidence") == "high")
        bullets.append(
            {
                "text": (
                    f"Lineup: {lineup.get('formation')} "
                    f"({lineup.get('formation_confidence')} formation confidence); "
                    f"{high}/11 high-confidence picks."
                ),
                "basis": "inferred",
            }
        )
    bullets.append(
        {
            "text": (
                "Unknowns: no injury, suspension or team-news feed. The opponent "
                "XI is a projection from recent lineups, not confirmed team news."
            ),
            "basis": "unknown",
        }
    )

    keys = []
    opp_shots = opponent_style.get("shots_for_pm")
    abd_shots_against = aberdeen_style.get("shots_against_pm")
    if opp_shots is not None and abd_shots_against is not None:
        keys.append(
            {
                "label": "Territory",
                "text": (
                    f"{opponent_name} average {opp_shots:.1f} shots per match "
                    f"{venue_label}; Aberdeen concede {abd_shots_against:.1f} "
                    "shots per match in the same venue split."
                ),
                "basis": "measured",
            }
        )
    abd_shots = aberdeen_style.get("shots_for_pm")
    opp_shots_against = opponent_style.get("shots_against_pm")
    if abd_shots is not None and opp_shots_against is not None:
        keys.append(
            {
                "label": "Aberdeen's route",
                "text": (
                    f"Aberdeen average {abd_shots:.1f} shots per match in this "
                    f"venue split; {opponent_name} concede "
                    f"{opp_shots_against:.1f}."
                ),
                "basis": "measured",
            }
        )
    opp_corners = opponent_style.get("corners_for_pm")
    abd_corners = aberdeen_style.get("corners_for_pm")
    if opp_corners is not None and abd_corners is not None:
        keys.append(
            {
                "label": "Set pieces",
                "text": (
                    f"Corners per match: {opponent_name} {opp_corners:.1f}, "
                    f"Aberdeen {abd_corners:.1f}. Delivery and second balls are "
                    "the measurable set-piece edge."
                ),
                "basis": "measured",
            }
        )
    if comparison.get("status") == "available":
        descriptor = str(comparison.get("descriptor") or "unknown")
        keys.append(
            {
                "label": "Table and form",
                "text": (
                    f"{descriptor.capitalize()} on PPG; "
                    f"edge: {comparison.get('edge')}. Form is the last five "
                    "league results, not a prediction."
                ),
                "basis": "measured",
            }
        )

    approach = opponent_lean.get("approach", "unknown")
    if approach == "attack":
        headline = (
            f"{opponent_name} are measured as a front-foot side {venue_label}; "
            "the question is whether Aberdeen can protect the space behind."
        )
    elif approach == "sit_deep_counter":
        headline = (
            f"{opponent_name} are measured as a deep, low-volume side "
            f"{venue_label}; Aberdeen's task is breaking a compact block without "
            "leaving the counter open."
        )
    else:
        headline = (
            f"{opponent_name} are measured as balanced {venue_label}; the matchup "
            "is less about one stylistic edge and more about who controls the "
            "shot volume."
        )
    return {
        "headline": headline,
        "bullets": bullets,
        "keys": keys,
        "basis": "measured_and_inferred",
        "note": (
            "The read describes measured form and shot profiles. It is not a "
            "result prediction and not betting advice."
        ),
    }


__all__ = [
    "assign_lineup",
    "form_block",
    "league_match_rows",
    "matchup_read",
    "percentile_rank",
    "predict_lineup",
    "record",
    "score_players",
    "select_formation",
    "split_record",
    "strength_block",
    "strength_comparison",
    "style_block",
    "style_lean",
]
