"""Publish the scouting hub, coverage and per-league pool documents."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import polars as pl

from fitba.analytics.scouting import (
    RATE_FIELDS,
    ROSE_LEAGUE,
    ROSE_LEAGUE_LABEL,
    CohortIndex,
    build_alignment,
    build_board,
    build_pool_rows,
    build_rose,
    build_squad_profile,
    build_squad_roses,
    history_player_totals,
    load_rose_history_indices,
    player_rates,
)
from fitba.analytics.scouting_value import fit_value_model, value_for_row
from fitba.analytics.valuation import age_at
from fitba.ingest.scouting import (
    PLAYER_ROLES_PATH,
    PLAYER_SEASON_PATH,
    POOL_META_PATH,
    ROLES_STATE_PATH,
)
from fitba.ingest.scouting_clubs import (
    load_current_clubs,
    load_current_clubs_meta,
)
from fitba.ingest.scouting_europe import (
    load_europe_appearances,
    load_europe_meta,
)
from fitba.ingest.scouting_standings import (
    load_standings,
    load_standings_meta,
)
from fitba.normalize.positions import position_group
from fitba.settings import (
    player_rose,
    scouting_archetypes,
    scouting_leagues,
    scouting_model,
    scouting_team_context,
    scouting_teams,
    scouting_value,
)
from fitba.settings import (
    roles as roles_config,
)
from fitba.settings import (
    teams as teams_config,
)
from fitba.util.dates import current_season

SCHEMA_VERSION = "1.0.0"
SEARCHABLE_MIN_RATED = 25


def _load_json(path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _load_parquet(path, columns: list[str] | None = None) -> pl.DataFrame:
    try:
        frame = pl.read_parquet(path)
    except (OSError, pl.exceptions.ComputeError):
        return pl.DataFrame()
    return frame.select(columns) if columns and frame.height else frame


def _team_resolver():
    canonical: dict[str, str] = {}
    for item in teams_config().get("teams") or []:
        name = str(item.get("name") or "")
        if not name:
            continue
        canonical[name.casefold()] = name
        for alias in item.get("aliases") or []:
            canonical[str(alias).casefold()] = name
    by_name: dict[str, str] = {}
    by_id: dict[int, str] = {}
    for item in scouting_teams().get("teams") or []:
        display = str(item.get("display_name") or "")
        if not display:
            continue
        if item.get("provider_name"):
            by_name[str(item["provider_name"]).casefold()] = display
        if item.get("api_football_id") is not None:
            by_id[int(item["api_football_id"])] = display

    def resolve(name: str | None, team_id: Any = None) -> str:
        text = str(name or "Unknown club")
        if team_id is not None:
            try:
                override = by_id.get(int(team_id))
            except (TypeError, ValueError):
                override = None
            if override:
                return override
        return by_name.get(text.casefold()) or canonical.get(text.casefold()) or text

    return resolve


def _family_labels() -> dict[str, str]:
    return {
        str(key): str(value.get("label") or key)
        for key, value in ((roles_config().get("families") or {}).items())
    }


def _archetype_definitions() -> tuple[list[dict[str, Any]], dict[str, str]]:
    definitions: list[dict[str, Any]] = []
    labels: dict[str, str] = {}
    for key, value in (scouting_archetypes().get("archetypes") or {}).items():
        label = str(value.get("label") or key)
        labels[key] = label
        definitions.append(
            {
                "id": key,
                "label": label,
                "description": value.get("description"),
                "families": value.get("families") or [],
                "features": value.get("features") or {},
            }
        )
    return definitions, labels


def _profile(
    row: dict[str, Any],
    labels: dict[str, str],
    *,
    score_key: str = "adjusted_score",
) -> dict[str, Any] | None:
    key_name = score_key
    scored = [
        (float(value[key_name]), key, value)
        for key, value in (row.get("archetypes") or {}).items()
        if value.get(key_name) is not None and float(value.get("coverage") or 0) >= 0.7
    ]
    if not scored and key_name != "score":
        scored = [
            (float(value["score"]), key, value)
            for key, value in (row.get("archetypes") or {}).items()
            if value.get("score") is not None and float(value.get("coverage") or 0) >= 0.7
        ]
    if not scored:
        return None
    score, key, value = max(scored)
    return {
        "id": key,
        "label": labels.get(key, key),
        "score": score,
        "raw_score": value.get("score"),
        "adjusted_score": value.get("adjusted_score"),
    }


def _former_aberdeen_block(
    player: dict[str, Any], clause: dict[str, Any] | None, *, stats_basis: str | None = None
) -> dict[str, Any]:
    departure = player.get("departure") or {}
    aberdeen = player.get("aberdeen") or {}
    post = player.get("post_career") or {}
    return {
        "player_key": player.get("player_key"),
        "name": player.get("name"),
        "href": player.get("href"),
        "transfer_href": player.get("transfer_href"),
        "departure": {
            key: departure.get(key)
            for key in (
                "transfer_id",
                "date",
                "season",
                "window",
                "kind",
                "fee_status",
                "fee_display",
                "to_club_name",
                "to_market",
                "to_country",
                "is_rival",
                "rival_name",
                "source_urls",
            )
        },
        "aberdeen": {
            key: aberdeen.get(key)
            for key in (
                "first_season",
                "last_season",
                "appearances",
                "starts",
                "sub_apps",
                "minutes",
                "goals",
                "assists",
                "rating",
                "tenure_coverage",
                "developed_here",
                "developed_basis",
                "final_season",
            )
        },
        "post_career": {
            key: post.get(key)
            for key in (
                "status",
                "totals",
                "current",
                "at_rival",
                "rival_current",
                "rival_spells",
                "top_flight_abroad",
            )
        },
        "sell_on": clause,
        "stats_basis": stats_basis,
    }


def _former_stats(
    player: dict[str, Any], detail: dict[str, Any]
) -> tuple[dict[str, Any] | None, str, str, str, str | None]:
    post_rows = list(detail.get("post_seasons") or [])
    post_rows = [row for row in post_rows if int(row.get("minutes") or 0) > 0]
    if post_rows:
        row = max(
            post_rows,
            key=lambda item: (str(item.get("season") or ""), int(item.get("minutes") or 0)),
        )
        return (
            row,
            "post_career_league",
            str(row.get("team_name") or ""),
            str(row.get("competition") or ""),
            row.get("country"),
        )
    aberdeen_rows = [
        row for row in detail.get("aberdeen_by_season") or [] if int(row.get("minutes") or 0) > 0
    ]
    if aberdeen_rows:
        row = max(aberdeen_rows, key=lambda item: str(item.get("season") or ""))
        return row, "aberdeen_last_season", "Aberdeen", "Aberdeen record", "Scotland"
    return None, "unavailable", "", "Former-player record", None


def _unavailable_rose(
    *, minutes: int, reason: str, label: str = "Former-player record"
) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "reason": reason,
        "league": ROSE_LEAGUE,
        "league_label": label,
        "minutes": minutes,
        "min_minutes": 180,
        "cohort_min_minutes": 450,
        "basis": "insufficient",
        "cohort_n": 0,
        "figures": [
            {"id": "overall", "label": "Overall profile", "status": "unavailable", "axes": []},
            {"id": "position", "label": "Position profile", "status": "unavailable", "axes": []},
        ],
        "season_used": None,
        "cohort_season": None,
        "fallback": False,
        "fallback_reason": reason,
        "fallback_note": (
            "No same-season Premiership cohort is available for this former-player "
            "record; the rose is unavailable rather than zero-filled."
        ),
    }


def _former_position_group(position: Any) -> str | None:
    value = str(position or "").casefold()
    if "goalkeeper" in value:
        return "GK"
    if "defender" in value or "back" in value:
        return "DEF"
    if "midfielder" in value:
        return "MID"
    if "attacker" in value or "forward" in value or "winger" in value:
        return "FWD"
    group = position_group(position)
    mapping = {
        "GK": "GK",
        "CB": "DEF",
        "FB": "DEF",
        "DM": "MID",
        "CM": "MID",
        "AM": "MID",
        "W": "FWD",
        "ST": "FWD",
    }
    return mapping.get(group or "")


def _former_rose(
    player: dict[str, Any],
    detail: dict[str, Any],
    *,
    rose_history: dict[str, CohortIndex],
    model: dict[str, Any],
    rose_config: dict[str, Any],
) -> dict[str, Any]:
    player_id = player.get("player_id")
    if player_id is None:
        return _unavailable_rose(minutes=0, reason="no_player_id")
    seasons = [
        str(row.get("season"))
        for row in reversed(detail.get("aberdeen_by_season") or [])
        if row.get("season")
    ]
    if not seasons:
        seasons = [str((player.get("aberdeen") or {}).get("last_season") or "")]
    player_min = int((model.get("squad") or {}).get("min_minutes") or 180)
    cohort_min = int((model.get("pool") or {}).get("min_minutes") or 450)
    for season in [value for value in seasons if value]:
        if season not in rose_history:
            continue
        totals = history_player_totals(int(player_id), season)
        minutes = int(totals.get("minutes") or 0)
        if minutes < player_min:
            continue
        rose = build_rose(
            player_rates(totals),
            minutes=minutes,
            league=ROSE_LEAGUE,
            league_label=ROSE_LEAGUE_LABEL,
            family=None,
            position_group=_former_position_group(player.get("position")),
            index=rose_history[season],
            model=model,
            config=rose_config,
            player_min_minutes=player_min,
            cohort_min_minutes=cohort_min,
        )
        rose.update(
            {
                "season_used": season,
                "cohort_season": season,
                "fallback": True,
                "fallback_reason": "former_player_last_aberdeen_season",
                "fallback_note": (
                    f"Former-player profile: {season} Aberdeen season against that "
                    "season's Premiership cohort. It is not a current-season ranking."
                ),
            }
        )
        return rose
    return _unavailable_rose(
        minutes=int((player.get("aberdeen") or {}).get("minutes") or 0),
        reason="no_prior_premiership_season",
    )


def _former_scouting_player(
    player: dict[str, Any],
    detail: dict[str, Any],
    clause: dict[str, Any] | None,
    *,
    today: date,
    rose_history: dict[str, CohortIndex],
    model: dict[str, Any],
    rose_config: dict[str, Any],
) -> dict[str, Any]:
    stats, stats_basis, stats_club, competition, _country = _former_stats(player, detail)
    post = player.get("post_career") or {}
    current = post.get("current") or {}
    minutes = int((stats or {}).get("minutes") or 0)
    appearances = (stats or {}).get("appearances")
    rating = (stats or {}).get("rating")
    birth_date = player.get("birth_date")
    club = current.get("club_name") or stats_club or "Unknown club"
    league_name = current.get("league") or competition or "Former-player record"
    role_label = player.get("position") or "Role unknown"
    return {
        "player_id": player.get("player_id"),
        "name": player.get("name"),
        "full_name": player.get("name"),
        "club": club,
        "stats_club": stats_club or "Unknown club",
        "current_club_status": "former_player",
        "current_club_source": current.get("source") or "former_register",
        "transferred_at": (player.get("departure") or {}).get("date"),
        "current_league_name": league_name,
        "age": age_at(birth_date, today.isoformat()) if birth_date else None,
        "nationality": player.get("nationality"),
        "position_group": position_group(player.get("position")) or "UNKNOWN",
        "role_family": None,
        "role_label": role_label,
        "role_status": "unknown",
        "role_family_share": None,
        "minutes": minutes,
        "appearances": appearances,
        "goals": (stats or {}).get("goals"),
        "assists": (stats or {}).get("assists"),
        "rating": rating,
        "rating_percentile": None,
        "adjusted_percentile": None,
        "adjustment_basis": "former_player_only",
        "value_index": None,
        "value_index_coverage": None,
        "value_index_drivers": [],
        "value_index_basis": None,
        "scouting_priority": None,
        "age_multiplier": None,
        "europe_multiplier": None,
        "european_league_phase_minutes": None,
        "european_league_phase_appearances": None,
        "european_league_phase_competitions": [],
        "european_status": "unknown",
        "value_low_gbp": None,
        "value_high_gbp": None,
        "value_confidence": "unknown",
        "value_method": "not_applicable",
        "cohort_basis": "former_player_only",
        "cohort_n": 0,
        "team_context_status": "unavailable",
        "team_rank": None,
        "team_points": None,
        "team_played": None,
        "team_ppg": None,
        "team_count": None,
        "team_points_percentile": None,
        "team_underperforming": None,
        "team_lift": None,
        "rose": _former_rose(
            player,
            detail,
            rose_history=rose_history,
            model=model,
            rose_config=rose_config,
        ),
        "flags": ["former_player"],
        "archetypes": {},
        "profile": None,
        **{field: None for field in RATE_FIELDS},
        "former_aberdeen": _former_aberdeen_block(player, clause, stats_basis=stats_basis),
    }


def _pool_player(
    row: dict[str, Any],
    *,
    family_labels: dict[str, str],
    archetype_labels: dict[str, str],
    resolve_team,
    value_model: dict[str, Any],
) -> dict[str, Any]:
    family = row.get("role_family")
    role_label = family_labels.get(str(family)) if family else None
    if not role_label:
        group = str(row.get("position_group") or "UNKNOWN")
        role_label = f"Provider group · {group}" if group != "UNKNOWN" else "Role unknown"
    return {
        "player_id": row.get("player_id"),
        "name": row.get("name"),
        "full_name": row.get("full_name"),
        "club": resolve_team(row.get("current_club"), row.get("current_club_id")),
        "stats_club": resolve_team(row.get("stats_club"), row.get("team_id")),
        "current_club_status": row.get("current_club_status"),
        "current_club_source": row.get("current_club_source"),
        "transferred_at": row.get("transferred_at"),
        "current_league_name": row.get("current_league_name"),
        "age": row.get("age"),
        "nationality": row.get("nationality"),
        "position_group": row.get("position_group"),
        "role_family": family,
        "role_label": role_label,
        "role_status": row.get("role_status"),
        "role_family_share": row.get("role_family_share"),
        "minutes": row.get("minutes"),
        "appearances": row.get("appearances"),
        "rating": row.get("rating"),
        "rating_percentile": row.get("rating_percentile"),
        "adjusted_percentile": row.get("adjusted_percentile"),
        "adjustment_basis": row.get("adjustment_basis"),
        "value_index": row.get("value_index"),
        "value_index_coverage": row.get("value_index_coverage"),
        "value_index_drivers": row.get("value_index_drivers") or [],
        "value_index_basis": row.get("value_index_basis"),
        "scouting_priority": row.get("scouting_priority"),
        "age_multiplier": row.get("age_multiplier"),
        "europe_multiplier": row.get("europe_multiplier"),
        "european_league_phase_minutes": row.get("european_league_phase_minutes"),
        "european_league_phase_appearances": row.get("european_league_phase_appearances"),
        "european_league_phase_competitions": row.get("european_league_phase_competitions") or [],
        "european_status": row.get("european_status"),
        **value_for_row(value_model, row),
        "cohort_basis": row.get("cohort_basis"),
        "cohort_n": row.get("cohort_n"),
        "team_context_status": row.get("team_context_status") or "unknown",
        "team_rank": row.get("team_rank"),
        "team_points": row.get("team_points"),
        "team_played": row.get("team_played"),
        "team_ppg": row.get("team_ppg"),
        "team_count": row.get("team_count"),
        "team_group": row.get("team_group"),
        "team_points_percentile": row.get("team_points_percentile"),
        "team_underperforming": row.get("team_underperforming"),
        "team_lift": row.get("team_lift"),
        "rose": row.get("rose"),
        "flags": row.get("flags") or [],
        **{field: (row.get("rates") or {}).get(field) for field in RATE_FIELDS},
        "archetypes": {
            key: {
                "score": value.get("score"),
                "adjusted_score": value.get("adjusted_score"),
                "coverage": value.get("coverage"),
            }
            for key, value in (row.get("archetypes") or {}).items()
        },
        "profile": _profile(row, archetype_labels),
    }


def _squad_row(
    row: dict[str, Any],
    *,
    archetype_labels: dict[str, str],
) -> dict[str, Any]:
    return {
        "player_id": row.get("player_id"),
        "name": row.get("name"),
        "role_family": row.get("role_family"),
        "role_label": row.get("role_label") or "Role unknown",
        "minutes": row.get("minutes"),
        "rating": row.get("rating"),
        "rating_percentile": row.get("rating_percentile"),
        "goals": row.get("goals"),
        "assists": row.get("assists"),
        "rose": row.get("rose"),
        **{field: (row.get("rates") or {}).get(field) for field in RATE_FIELDS},
        "archetypes": {
            key: {
                "score": value.get("score"),
                "coverage": value.get("coverage"),
            }
            for key, value in (row.get("archetypes") or {}).items()
        },
        "profile": _profile(row, archetype_labels, score_key="score"),
        "cohort": row.get("cohort"),
    }


def _board_row(family: dict[str, Any]) -> dict[str, Any]:
    return {
        "family": family.get("family"),
        "label": family.get("label"),
        "players": [
            {
                "player_id": player.get("player_id"),
                "name": player.get("name"),
                "role_label": player.get("role_label"),
                "minutes": player.get("minutes"),
                "rating": player.get("rating"),
                "availability": player.get("availability"),
                "prior": player.get("prior"),
                "first_choice": player.get("first_choice"),
            }
            for player in family.get("players") or []
        ],
        "player_count": family.get("player_count"),
        "minutes": family.get("minutes"),
        "average_rating": family.get("average_rating"),
        "rating_percentile": family.get("rating_percentile"),
        "cohort": family.get("cohort"),
        "status": family.get("status"),
        "reading": family.get("reading"),
        "absent_first_choice": family.get("absent_first_choice"),
        "drivers": family.get("drivers") or [],
    }


def _layer_zero(board: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[int] = set()
    order = {"out": 0, "doubtful": 1, "suspended": 2, "returned": 3, "available": 4}
    families_and_unassigned = [
        (family, player)
        for family in board.get("families") or []
        for player in family.get("layer0") or []
    ]
    for item in board.get("unassigned_layer0") or []:
        families_and_unassigned.append(({"family": None, "label": "Role not observed"}, item))
    for family, player in families_and_unassigned:
        player_id = int(player.get("player_id"))
        if player_id in seen:
            continue
        seen.add(player_id)
        availability = player.get("availability") or {}
        items.append(
            {
                "player_id": player_id,
                "name": player.get("name"),
                "family": family.get("family"),
                "family_label": family.get("label"),
                "role_label": player.get("role_label"),
                "minutes": player.get("minutes"),
                "rating": player.get("rating"),
                "status": availability.get("status"),
                "confidence": availability.get("confidence"),
                "source_id": availability.get("source_id"),
                "source_url": availability.get("source_url"),
                "verified_at": availability.get("verified_at"),
                "note": availability.get("note"),
                "prior": player.get("prior"),
                "first_choice": player.get("first_choice"),
            }
        )
    items.sort(
        key=lambda item: (
            order.get(str(item.get("status")), 9),
            str(item.get("name")),
        )
    )
    return items


def _profile_rank(row: dict[str, Any], archetype_id: str) -> float | None:
    """Profile score with the published scouting preference multipliers applied.

    The rank keeps the profile itself as the ordering signal: a player is
    ordered by how well they fit *this* profile, then adjusted by the U23 and
    European league-phase preferences. Ranking by the value-index priority
    alone made the assist and goal-scoring profiles collapse into the same
    order.
    """
    profile = (row.get("archetypes") or {}).get(archetype_id) or {}
    score = profile.get("adjusted_score")
    if score is None:
        return None
    age_multiplier = row.get("age_multiplier")
    europe_multiplier = row.get("europe_multiplier")
    return (
        float(score)
        * (float(age_multiplier) if age_multiplier is not None else 1.0)
        * (float(europe_multiplier) if europe_multiplier is not None else 1.0)
    )


def _profile_leaders(
    rows: list[dict[str, Any]],
    archetype_id: str,
    *,
    limit: int = 5,
    min_coverage: float = 0.7,
) -> list[dict[str, Any]]:
    candidates = []
    for row in rows:
        profile = (row.get("archetypes") or {}).get(archetype_id) or {}
        if profile.get("adjusted_score") is None:
            continue
        if (profile.get("coverage") or 0) < min_coverage:
            continue
        candidates.append(row)
    candidates.sort(
        key=lambda row: (
            -(_profile_rank(row, archetype_id) or 0.0),
            -float(row["archetypes"][archetype_id]["adjusted_score"]),
            -int(row.get("minutes") or 0),
        )
    )
    return candidates[:limit]


def _leader(row: dict[str, Any], *, resolve_team, archetype_id: str) -> dict[str, Any]:
    archetype = (row.get("archetypes") or {}).get(archetype_id, {})
    return {
        "player_id": row.get("player_id"),
        "name": row.get("name"),
        "club": resolve_team(
            row.get("current_club") or row.get("team_name"),
            row.get("current_club_id") or row.get("team_id"),
        ),
        "league_id": row.get("competition_id"),
        "league_slug": row.get("league_slug"),
        "league_name": row.get("competition"),
        "stats_club": resolve_team(row.get("stats_club"), row.get("team_id")),
        "current_club_status": row.get("current_club_status"),
        "age": row.get("age"),
        "minutes": row.get("minutes"),
        "rating": row.get("rating"),
        "rating_percentile": row.get("rating_percentile"),
        "adjusted_percentile": row.get("adjusted_percentile"),
        "raw_score": archetype.get("score"),
        "adjusted_score": archetype.get("adjusted_score"),
        "coverage": archetype.get("coverage"),
        "value_index": row.get("value_index"),
        "value_index_coverage": row.get("value_index_coverage"),
        "team_context_status": row.get("team_context_status") or "unknown",
        "team_rank": row.get("team_rank"),
        "team_points": row.get("team_points"),
        "team_played": row.get("team_played"),
        "team_ppg": row.get("team_ppg"),
        "team_count": row.get("team_count"),
        "team_group": row.get("team_group"),
        "team_points_percentile": row.get("team_points_percentile"),
        "team_underperforming": row.get("team_underperforming"),
        "team_lift": row.get("team_lift"),
        "scouting_priority": row.get("scouting_priority"),
        "age_multiplier": row.get("age_multiplier"),
        "europe_multiplier": row.get("europe_multiplier"),
        "european_league_phase_minutes": row.get("european_league_phase_minutes"),
        "european_league_phase_competitions": row.get("european_league_phase_competitions") or [],
        "european_status": row.get("european_status"),
    }


def _goal_scorer(row: dict[str, Any], resolve_team) -> dict[str, Any]:
    rates = row.get("rates") or {}
    return {
        "player_id": row.get("player_id"),
        "name": row.get("name"),
        "club": resolve_team(row.get("current_club"), row.get("current_club_id")),
        "stats_club": resolve_team(row.get("stats_club"), row.get("team_id")),
        "league_id": row.get("competition_id"),
        "league_slug": row.get("league_slug"),
        "league_name": row.get("competition"),
        "age": row.get("age"),
        "minutes": row.get("minutes"),
        "goals": row.get("goals"),
        "assists": row.get("assists"),
        "goals_p90": rates.get("goals_p90"),
        "assists_p90": rates.get("assists_p90"),
        "goals_assists_p90": rates.get("goals_assists_p90"),
        "shots_p90": rates.get("shots_p90"),
        "conversion_pct": rates.get("conversion_pct"),
        "scouting_priority": row.get("scouting_priority"),
        "value_index": row.get("value_index"),
        "european_status": row.get("european_status"),
        "european_league_phase_minutes": row.get("european_league_phase_minutes"),
        "current_club_status": row.get("current_club_status"),
    }


def _attackers(
    rows: list[dict[str, Any]],
    *,
    resolve_team,
    archetype_labels: dict[str, str],
) -> dict[str, Any]:
    attack_families = {"centre_forward", "wide_forward", "attacking_midfield"}

    def bias(row: dict[str, Any]) -> float | None:
        assist = (row.get("archetypes") or {}).get("assist_creator", {})
        goal = (row.get("archetypes") or {}).get("goal_scorer", {})
        assist_score = assist.get("adjusted_score")
        goal_score = goal.get("adjusted_score")
        if assist_score is None or goal_score is None:
            return None
        return float(assist_score) - float(goal_score)

    assist_rows: list[tuple[float, dict[str, Any]]] = []
    goal_rows: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        if row.get("role_family") not in attack_families:
            continue
        value = bias(row)
        if value is None:
            continue
        if value > 0:
            assist_rows.append((value, row))
        elif value < 0:
            goal_rows.append((value, row))
    assist_rows.sort(
        key=lambda item: (
            -(_profile_rank(item[1], "assist_creator") or 0.0),
            -float(item[0]),
            -float(item[1].get("scouting_priority") or 0),
        )
    )
    goal_rows.sort(
        key=lambda item: (
            -(_profile_rank(item[1], "goal_scorer") or 0.0),
            float(item[0]),
            -float(item[1].get("scouting_priority") or 0),
        )
    )

    def attacker_leader(row: dict[str, Any], archetype_id: str, value: float) -> dict[str, Any]:
        leader = _leader(row, resolve_team=resolve_team, archetype_id=archetype_id)
        leader["bias"] = round(float(value), 1)
        leader["assist_score"] = (
            (row.get("archetypes") or {}).get("assist_creator", {}).get("adjusted_score")
        )
        leader["goal_score"] = (
            (row.get("archetypes") or {}).get("goal_scorer", {}).get("adjusted_score")
        )
        return leader

    scoring_rows = [
        row
        for row in rows
        if row.get("role_family") in attack_families
        and (row.get("rates") or {}).get("goals_p90") is not None
    ]
    scoring_rows.sort(
        key=lambda row: (
            -float(row["rates"]["goals_p90"]),
            -float(row["rates"].get("goals_assists_p90") or 0),
            -int(row.get("minutes") or 0),
        )
    )
    return {
        "assist_bias": {
            "profile_id": "assist_creator",
            "label": archetype_labels.get("assist_creator", "Assist-biased contributor"),
            "leaders": [
                attacker_leader(row, "assist_creator", value) for value, row in assist_rows[:8]
            ],
        },
        "goal_bias": {
            "profile_id": "goal_scorer",
            "label": archetype_labels.get("goal_scorer", "Goal-scoring forward"),
            "leaders": [attacker_leader(row, "goal_scorer", value) for value, row in goal_rows[:8]],
        },
        "goal_scoring": [_goal_scorer(row, resolve_team) for row in scoring_rows[:12]],
        "note": (
            "Assist bias and goal bias are separate profile scores. The "
            "goal-scoring list is ordered by goals per 90 at the pool minutes "
            "threshold, not by the composite profile."
        ),
    }


def _team_lens(
    rows: list[dict[str, Any]],
    *,
    resolve_team,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    threshold = float(config.get("underperforming_ppg_percentile_max") or 40)
    min_lift = float(config.get("min_lift") or 0)
    limit = int(config.get("lens_limit") or 12)
    candidates = [
        row
        for row in rows
        if row.get("team_context_status") == "available"
        and row.get("team_lift") is not None
        and float(row["team_lift"]) > min_lift
        and row.get("team_points_percentile") is not None
        and float(row["team_points_percentile"]) <= threshold
    ]
    candidates.sort(
        key=lambda row: (
            -float(row["team_lift"]),
            -float(row.get("scouting_priority") or 0),
            -int(row.get("minutes") or 0),
        )
    )
    return [
        _leader(row, resolve_team=resolve_team, archetype_id=row.get("profile_id") or "")
        for row in candidates[:limit]
    ]


def _league_summary(
    *,
    league: dict[str, Any],
    meta: dict[str, Any] | None,
    pool_rows: pl.DataFrame,
    role_rows: pl.DataFrame,
    state: dict[str, Any] | None,
    min_rated: int,
) -> dict[str, Any]:
    provider_id = int((league.get("provider") or {}).get("api_football_id") or 0)
    league_id = str(league["id"])
    players = (
        pool_rows.filter(pl.col("competition_id") == league_id)
        if pool_rows.height
        else pl.DataFrame()
    )
    rated = players.filter(pl.col("rating").is_not_null()).height if players.height else 0
    with_minutes = players.filter(pl.col("minutes") >= 450).height if players.height else 0
    # Role rows can include players the provider has no season-stat row for; the
    # coverage numerator is role-known players *in the published pool* so the
    # ratio cannot exceed one pool player.
    pool_ids = set(players["player_id"].to_list()) if players.height else set()
    roles = (
        role_rows.filter(
            (pl.col("league_id") == league_id)
            & pl.col("player_id").is_in(sorted(pool_ids))
        ).height
        if role_rows.height and pool_ids
        else 0
    )
    status = (meta or {}).get("status") or ("no_player_stats" if provider_id else "unknown")
    if status == "ok" and rated < min_rated:
        status = "partial"
    searchable = status == "ok"
    role_state = next(
        (item for item in ((state or {}).get("leagues") or []) if item.get("id") == league_id),
        None,
    )
    return {
        "id": league_id,
        "slug": str(league.get("slug")),
        "name": str(league.get("name")),
        "country": str(league.get("country") or ""),
        "tier": league.get("tier"),
        "provider_league_id": provider_id,
        "status": status,
        "searchable": searchable,
        "players": players.height if players.height else 0,
        "rated": rated,
        "with_minutes_450": with_minutes,
        "role_players": roles,
        "role_coverage": round(roles / (players.height or 1), 3) if players.height else 0.0,
        "lineups_fetched": int((role_state or {}).get("lineups_fetched") or 0),
        "fixtures_played": int((role_state or {}).get("played") or 0),
        "error": (meta or {}).get("error") or (role_state or {}).get("error"),
        "href": f"/scouting/{league.get('slug')}/",
    }


def _pool_document(
    *,
    league: dict[str, Any],
    summary: dict[str, Any],
    players: list[dict[str, Any]],
    season: str,
    generated_at: str,
) -> dict[str, Any]:
    state = "no_player_stats" if summary["status"] == "no_player_stats" else "full"
    if summary["status"] in {"error", "stale"}:
        state = "stale"
    return {
        "schema_version": SCHEMA_VERSION,
        "season": season,
        "generated_at": generated_at,
        "league": {
            "id": league["id"],
            "slug": league["slug"],
            "name": league["name"],
            "country": league.get("country"),
            "tier": league.get("tier"),
            "provider_league_id": summary["provider_league_id"],
        },
        "state": state,
        "min_minutes": 450,
        "rose_meta": {
            "catalogue": (player_rose() or {}).get("catalogue") or {},
            "min_petals": (player_rose() or {}).get("min_petals") or 4,
            "method_note": (
                "Two Nightingale rose figures: an all-round overall set and a "
                "role-specific position set, both against the same league and "
                "role-family cohort. Percentiles are directional; missing "
                "values are not zero."
            ),
        },
        "players": players,
        "coverage": {
            "players": summary["players"],
            "rated": summary["rated"],
            "with_minutes_450": summary["with_minutes_450"],
            "role_players": summary["role_players"],
            "role_coverage": summary["role_coverage"],
            "lineups_fetched": summary["lineups_fetched"],
            "fixtures_played": summary["fixtures_played"],
            "note": (
                "The provider returns no player season statistics for this league."
                if state == "no_player_stats"
                else (
                    "Provider season statistics; ratings and percentiles are "
                    "within this league and role."
                )
            ),
        },
        "limitations": [
            "Provider ratings are opaque and not comparable across leagues.",
            "Percentiles are within this league and role cohort; no cross-league ranking.",
            "No contracts, wages, fees or release clauses are claimed.",
            "No xG/xA, progressive passes, carries, pressures, aerial wins or "
            "crosses are in the feed.",
            "Role families come from starting-XI grids; leagues without grids use "
            "the provider group.",
        ],
        "sources": [
            {
                "id": "api_football",
                "name": "API-Football",
                "url": "https://www.api-football.com",
            }
        ],
    }


def _search_sort_key(row: dict[str, Any]) -> tuple[str, float, int, str]:
    percentile = row.get("p")
    pct = float(percentile) if isinstance(percentile, (int, float)) else -1.0
    return (str(row.get("l") or ""), -pct, -int(row.get("m") or 0), str(row.get("n") or ""))


def _compact_search_row(row: dict[str, Any]) -> dict[str, Any]:
    """Drop nulls and empty collections; unknown stays absent, never zero."""
    compact: dict[str, Any] = {}
    for key, value in row.items():
        if value is None:
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        if key == "em" and value == 0:
            continue
        compact[key] = value
    return compact


def build_scouting_bundle(
    *,
    season: str | None = None,
    squad_data: dict[str, Any],
    availability: dict[str, Any] | None,
    generated_at: str,
    former_players: dict[str, Any] | None = None,
    former_seasons: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the hub, coverage and every per-league pool document."""
    season_label = season or current_season()
    model = scouting_model()
    archetypes = scouting_archetypes()
    rose_config = player_rose()
    roles = roles_config()
    pool = _load_parquet(PLAYER_SEASON_PATH)
    role_rows = _load_parquet(PLAYER_ROLES_PATH)
    europe_rows = load_europe_appearances()
    europe_meta = load_europe_meta()
    standings = load_standings()
    standings_meta = load_standings_meta()
    team_context_config = scouting_team_context()
    current_clubs = load_current_clubs()
    current_clubs_meta = load_current_clubs_meta()
    value_config = scouting_value()
    priority_config = value_config.get("priority") or {}
    index_config = value_config.get("index") or {}
    meta = _load_json(POOL_META_PATH) or {}
    state = _load_json(ROLES_STATE_PATH) or {}
    meta_by_id = {str(item.get("id")): item for item in meta.get("leagues") or []}
    resolve_team = _team_resolver()
    family_labels = _family_labels()
    archetype_defs, archetype_labels = _archetype_definitions()
    min_rated = int((model.get("coverage") or {}).get("min_rated_players") or 25)

    pools = build_pool_rows(
        pool,
        role_rows,
        config=roles,
        archetypes=archetypes,
        model=model,
        value_config=scouting_value(),
        rose_config=rose_config,
        europe_rows=europe_rows,
        europe_meta=europe_meta,
        current_clubs=current_clubs,
        team_standings=standings,
        team_context_config=team_context_config,
    )
    all_rows = [row for rows in pools.values() for row in rows]
    premiership_rows = pools.get("sco:premiership", [])
    adjustment = build_alignment(all_rows, model)
    adjustment.pop("reference_values", None)
    # Aberdeen is compared with the league, not with itself. The pool source
    # already excludes team 252; this is the invariant guard, not a filter that
    # changes today's published values.
    squad_players = [
        *(squad_data.get("players") or []),
        *(squad_data.get("excluded_players") or []),
    ]
    squad_ids = {
        int(player["player_id"])
        for player in squad_players
        if player.get("player_id") is not None
    }
    index = CohortIndex(all_rows, model, exclude_player_ids=squad_ids)
    board = build_board(
        squad_data=squad_data,
        pool_rows=premiership_rows,
        index=index,
        season=season_label,
        roles=roles,
        model=model,
        availability_entries=(availability or {}).get("entries") or [],
    )
    squad_roses = build_squad_roses(
        squad_data=squad_data,
        index=index,
        model=model,
        config=rose_config,
        season=season_label,
    )
    squad_profile = build_squad_profile(
        squad_data=squad_data,
        index=index,
        roles=roles,
        archetypes=archetypes,
        model=model,
        roses=squad_roses,
    )
    value_model = fit_value_model()
    layer_zero = _layer_zero(board)
    attackers = _attackers(
        all_rows,
        resolve_team=resolve_team,
        archetype_labels=archetype_labels,
    )
    leaders = {
        definition["id"]: [
            _leader(row, resolve_team=resolve_team, archetype_id=definition["id"])
            for row in _profile_leaders(
                all_rows,
                definition["id"],
                limit=5,
            )
        ]
        for definition in archetype_defs
    }

    team_lens = _team_lens(
        all_rows,
        resolve_team=resolve_team,
        config=team_context_config,
    )

    league_list = []
    for league in scouting_leagues().get("pool") or []:
        if not league.get("enabled"):
            continue
        league_list.append(
            _league_summary(
                league=league,
                meta=meta_by_id.get(str(league["id"])),
                pool_rows=pool,
                role_rows=role_rows,
                state=state,
                min_rated=min_rated,
            )
        )
    by_slug = {str(league["slug"]): league for league in league_list}
    pool_documents: dict[str, dict[str, Any]] = {}
    for league in scouting_leagues().get("pool") or []:
        if not league.get("enabled"):
            continue
        summary = by_slug[str(league["slug"])]
        players = [
            _pool_player(
                row,
                family_labels=family_labels,
                archetype_labels=archetype_labels,
                resolve_team=resolve_team,
                value_model=value_model,
            )
            for row in pools.get(str(league["id"]), [])
        ]
        pool_documents[str(league["slug"])] = _pool_document(
            league=league,
            summary=summary,
            players=players,
            season=season_label,
            generated_at=generated_at,
        )

    former_document = former_players or {}
    former_detail = (former_seasons or {}).get("seasons") or {}
    former_list = former_document.get("players") or []
    former_by_id = {
        int(player["player_id"]): player
        for player in former_list
        if player.get("player_id") is not None
    }
    former_clauses = {
        str(clause.get("player_key")): clause
        for clause in (former_document.get("sell_on_watch") or {}).get("clauses") or []
        if clause.get("player_key")
    }
    existing_ids = {
        int(player["player_id"])
        for document in pool_documents.values()
        for player in document.get("players") or []
        if player.get("player_id") is not None
    }
    rose_history = load_rose_history_indices(model) if former_by_id else {}
    if former_by_id:
        for document in pool_documents.values():
            for player in document.get("players") or []:
                player_id = player.get("player_id")
                if player_id is None or int(player_id) not in former_by_id:
                    continue
                source = former_by_id[int(player_id)]
                player["former_aberdeen"] = _former_aberdeen_block(
                    source,
                    former_clauses.get(str(source.get("player_key"))),
                    stats_basis="scouting_current_season",
                )
                if (player.get("rose") or {}).get("status") != "available":
                    detail = former_detail.get(str(source.get("player_key"))) or {}
                    player["rose"] = _former_rose(
                        source,
                        detail,
                        rose_history=rose_history,
                        model=model,
                        rose_config=rose_config,
                    )
        today = date.today()
        fallback_players = [
            _former_scouting_player(
                player,
                former_detail.get(str(player.get("player_key"))) or {},
                former_clauses.get(str(player.get("player_key"))),
                today=today,
                rose_history=rose_history,
                model=model,
                rose_config=rose_config,
            )
            for player in former_list
            if player.get("player_id") is not None and int(player["player_id"]) not in existing_ids
        ]
        if fallback_players:
            fallback_players.sort(key=lambda row: str(row.get("name") or ""))
            former_league = {
                "id": "sco:former-players",
                "slug": "former",
                "name": "Former-player record",
                "country": "Scotland",
                "tier": None,
            }
            former_summary = {
                "status": "full",
                "provider_league_id": 0,
                "players": len(fallback_players),
                "rated": sum(1 for row in fallback_players if row.get("rating") is not None),
                "with_minutes_450": sum(
                    1 for row in fallback_players if int(row.get("minutes") or 0) >= 450
                ),
                "role_players": 0,
                "role_coverage": 0,
                "lineups_fetched": 0,
                "fixtures_played": 0,
            }
            pool_documents["former"] = _pool_document(
                league=former_league,
                summary=former_summary,
                players=fallback_players,
                season=season_label,
                generated_at=generated_at,
            )

    totals = {
        "leagues": len(league_list),
        "searchable": sum(1 for league in league_list if league["searchable"]),
        "no_player_stats": sum(
            1 for league in league_list if league["status"] == "no_player_stats"
        ),
        "players": sum(league["players"] for league in league_list),
        "rated": sum(league["rated"] for league in league_list),
        "with_minutes_450": sum(league["with_minutes_450"] for league in league_list),
        "role_players": sum(league["role_players"] for league in league_list),
    }
    known_gaps = [
        f"{totals['no_player_stats']} enabled leagues return no player season statistics "
        "(Scottish Championship/League One/League Two and four other leagues); their pages "
        "say so instead of zero-filling.",
        "Contracts, wages, fees, release clauses and agent fees are not in the fed data.",
        "No event coordinates, xG/xA, progressive passes, carries, pressures, aerial wins "
        "or crosses.",
        "Role families need starting-XI grids; leagues without them use the provider group.",
        "Provider ratings are opaque and league-relative; no cross-league ranking is published.",
        "The availability ledger has only the verified official AFC entries; every other "
        "injury state is unknown.",
        "This is a profile search, not a target list or a recommendation.",
    ]
    coverage = {
        "schema_version": SCHEMA_VERSION,
        "season": season_label,
        "generated_at": generated_at,
        "provider": "api_football",
        "cohort_minutes": 450,
        "leagues": league_list,
        "totals": totals,
        "adjustment": adjustment,
        "europe": europe_meta,
        "current_clubs": current_clubs_meta,
        "team_context": {
            "standings": standings_meta,
            "underperforming_ppg_percentile_max": team_context_config.get(
                "underperforming_ppg_percentile_max"
            ),
            "min_lift": team_context_config.get("min_lift"),
        },
        "known_gaps": known_gaps,
        "sources": [
            {
                "id": "api_football",
                "name": "API-Football",
                "url": "https://www.api-football.com",
                "coverage": "season player statistics and starting-XI lineups",
            },
            {
                "id": "afc_news",
                "name": "Aberdeen FC official",
                "url": "https://www.afc.co.uk",
                "coverage": "verified availability ledger entries",
            },
        ],
    }
    hub = {
        "schema_version": SCHEMA_VERSION,
        "season": season_label,
        "generated_at": generated_at,
        "state": "full" if board["families"] and all_rows else "empty",
        "club_id": "sco:aberdeen",
        "board": board,
        "layer_zero": layer_zero,
        "squad": [_squad_row(row, archetype_labels=archetype_labels) for row in squad_profile],
        "archetypes": [
            {**definition, "leaders": leaders.get(definition["id"], [])}
            for definition in archetype_defs
        ],
        "attackers": attackers,
        "team_lens": {
            "label": "Outperforming struggling teams",
            "definition": (
                "Team points-per-game percentile at or below the threshold; player "
                "lift is the role-adjusted percentile minus the team points percentile."
            ),
            "threshold": team_context_config.get("underperforming_ppg_percentile_max"),
            "leaders": team_lens,
            "coverage": (standings_meta or {}).get("totals") or {},
        },
        "value_model": value_model,
        "priority": priority_config,
        "europe_coverage": europe_meta,
        "leagues": league_list,
        "coverage": {
            "totals": totals,
            "known_gaps": known_gaps,
            "sources": coverage["sources"],
            "team_context": (standings_meta or {}).get("totals") or {},
        },
        "limitations": [
            "Provider ratings are relative to a league and role cohort; they are not a verdict.",
            "The model cannot separate selection, availability and quality.",
            "Assist bias and goal bias are profile descriptions, not causal claims.",
            "No contracts, wages, fees or release clauses are claimed.",
            "No target list and no Aberdeen FC recommendation.",
        ],
    }
    search_players: list[dict[str, Any]] = []
    flag_codes = {"low_minutes": "l", "role_unknown": "r", "no_rating": "n"}
    goal_counts = {
        (int(row["player_id"]), str(row.get("league_slug"))): (
            row.get("goals"),
            row.get("assists"),
        )
        for row in all_rows
        if row.get("player_id") is not None
    }
    if "former" in pool_documents:
        for player in pool_documents["former"].get("players") or []:
            player_id = player.get("player_id")
            if player_id is not None:
                goal_counts[(int(player_id), "former")] = (
                    player.get("goals"),
                    player.get("assists"),
                )
    profile_order_list = list(archetype_labels)
    profile_order = {key: index for index, key in enumerate(profile_order_list)}
    for document in pool_documents.values():
        league = document["league"]
        for player in document["players"]:
            profile = player.get("profile") or {}
            player_id = player.get("player_id")
            goals, assists = (
                goal_counts.get((int(player_id), str(league.get("slug"))), (None, None))
                if player_id is not None
                else (None, None)
            )
            search_players.append(
                _compact_search_row(
                    {
                        "i": player.get("player_id"),
                        "n": player.get("name"),
                        "c": player.get("club"),
                        "sc": player.get("stats_club"),
                        "l": league.get("slug"),
                        "na": player.get("nationality"),
                        "rf": player.get("role_family"),
                        "a": player.get("age"),
                        "m": player.get("minutes"),
                        "rt": player.get("rating"),
                        "p": player.get("rating_percentile"),
                        "cn": player.get("cohort_n"),
                        "cb": player.get("cohort_basis"),
                        "ap": player.get("adjusted_percentile"),
                        "vi": player.get("value_index"),
                        "vc": player.get("value_index_coverage"),
                        "cs": player.get("current_club_status"),
                        "gl": goals,
                        "ast": assists,
                        "g90": player.get("goals_p90"),
                        "sh90": player.get("shots_p90"),
                        "cv": player.get("conversion_pct"),
                        "em": player.get("european_league_phase_minutes"),
                        "es": player.get("european_status"),
                        "eu": [
                            {
                                "UEFA Champions League": "ucl",
                                "UEFA Europa League": "uel",
                                "UEFA Conference League": "uecl",
                            }.get(str(name), str(name))
                            for name in (player.get("european_league_phase_competitions") or [])
                        ],
                        "ga": player.get("goals_assists_p90"),
                        "dr": player.get("dribbles_success_p90"),
                        "ps": player.get("passes_completed_p90"),
                        "pa": player.get("pass_completion_pct"),
                        "kp": player.get("key_passes_p90"),
                        "tk": player.get("tackles_p90"),
                        "it": player.get("interceptions_p90"),
                        "dw": player.get("duel_win_pct"),
                        "tr": player.get("team_rank"),
                        "tpts": player.get("team_points"),
                        "tpc": player.get("team_points_percentile"),
                        "tl": player.get("team_lift"),
                        "tc": player.get("team_count"),
                        "tg": player.get("team_group"),
                        "tu": player.get("team_underperforming"),
                        "pr": profile.get("id"),
                        "psc": profile.get("score"),
                        "arp": [
                            [
                                profile_order[key],
                                value.get("adjusted_score"),
                                value.get("score"),
                                value.get("coverage"),
                            ]
                            for key, value in (player.get("archetypes") or {}).items()
                            if key in profile_order
                        ],
                        "f": [
                            flag_codes[flag]
                            for flag in player.get("flags") or []
                            if flag in flag_codes
                        ],
                    }
                )
            )
    search_players.sort(key=_search_sort_key)
    search_document = {
        "schema_version": SCHEMA_VERSION,
        "season": season_label,
        "generated_at": generated_at,
        "state": "full" if search_players else "empty",
        "min_minutes": 450,
        "min_cohort": int((model.get("pool") or {}).get("min_cohort") or 15),
        "min_cohort_by_family": (model.get("pool") or {}).get("min_cohort_by_family") or {},
        "count": len(search_players),
        "leagues": [
            {
                "id": league["id"],
                "slug": league["slug"],
                "name": league["name"],
                "country": league["country"],
                "players": league["players"],
                "searchable": league["searchable"],
                "href": league["href"],
            }
            for league in league_list
        ],
        "role_labels": family_labels,
        "profile_labels": archetype_labels,
        "profile_order": profile_order_list,
        "priority": priority_config,
        "archetype_min_coverage": float(
            (model.get("archetypes") or {}).get("min_weight_coverage") or 0.7
        ),
        "value_model": {
            "weights": index_config.get("weights") or {},
            "min_weight_coverage": index_config.get("min_weight_coverage"),
            "minutes_full": index_config.get("minutes_full"),
            "age_curve": index_config.get("age_curve") or [],
        },
        "team_context": {
            "underperforming_ppg_percentile_max": team_context_config.get(
                "underperforming_ppg_percentile_max"
            ),
            "min_lift": team_context_config.get("min_lift"),
        },
        "europe_coverage": europe_meta,
        "players": search_players,
        "limitations": [
            "Adjusted percentiles are an empirical alignment to the Premiership cohort, "
            "not a measured equivalence; raw within-league percentiles are shown beside them.",
            "Provider ratings are opaque and league-relative.",
            "The value index is a scouting ordering, not a transfer value or fee.",
            "No contracts, wages, fees or release clauses are claimed.",
            "No xG/xA, progressive passes, carries, pressures, aerial wins or crosses.",
        ],
    }
    if "former" in pool_documents:
        search_document["leagues"].append(
            {
                "id": "sco:former-players",
                "slug": "former",
                "name": "Former-player record",
                "country": "Scotland",
                "players": len(pool_documents["former"].get("players") or []),
                "searchable": True,
                "href": "/former-players/",
            }
        )
        coverage["former_profiles"] = {
            "players": len(pool_documents["former"].get("players") or []),
            "note": (
                "Former Aberdeen players use the standard scouting profile. Their "
                "statistical profile is their latest league season, falling back to "
                "their last Aberdeen season and labelled. Cup/European provider rows "
                "and cross-league percentiles are not published."
            ),
        }

    return {
        "hub": hub,
        "coverage": coverage,
        "pools": pool_documents,
        "search": search_document,
        "squad_roses": squad_roses,
    }


def fallback_scouting_bundle(
    previous: dict[str, Any] | None,
    *,
    reason: str,
    season: str | None = None,
    generated_at: str,
) -> dict[str, Any]:
    """Keep the last good documents, labelled stale, rather than fail publish."""
    season_label = season or current_season()
    if previous and previous.get("hub"):
        hub = dict(previous["hub"])
        hub["state"] = "stale"
        hub["stale_reason"] = reason
        hub["generated_at"] = generated_at
        coverage = dict(previous.get("coverage") or {})
        coverage["state"] = "stale"
        coverage["stale_reason"] = reason
        coverage["generated_at"] = generated_at
        pools = previous.get("pools") or {}
        for document in pools.values():
            document["state"] = "stale"
            document["stale_reason"] = reason
        return {
            "hub": hub,
            "coverage": coverage,
            "pools": pools,
            "search": previous.get("search")
            or {
                "schema_version": SCHEMA_VERSION,
                "season": season_label,
                "generated_at": generated_at,
                "state": "stale",
                "min_minutes": 450,
                "count": 0,
                "leagues": [],
                "players": [],
                "limitations": ["No scouting search data is available in this build."],
            },
            "squad_roses": {},
        }
    empty = {
        "schema_version": SCHEMA_VERSION,
        "season": season_label,
        "generated_at": generated_at,
        "state": "empty",
        "stale_reason": reason,
        "club_id": "sco:aberdeen",
        "board": {"league_id": "sco:premiership", "families": [], "summary": {}},
        "layer_zero": [],
        "squad": [],
        "archetypes": [],
        "pivot": None,
        "leagues": [],
        "coverage": {"totals": {}, "known_gaps": [], "sources": []},
        "limitations": ["No scouting data is available in this build."],
    }
    return {
        "hub": empty,
        "search": {
            "schema_version": SCHEMA_VERSION,
            "season": season_label,
            "generated_at": generated_at,
            "state": "empty",
            "min_minutes": 450,
            "count": 0,
            "leagues": [],
            "players": [],
            "limitations": ["No scouting search data is available in this build."],
        },
        "coverage": {
            "schema_version": SCHEMA_VERSION,
            "season": season_label,
            "generated_at": generated_at,
            "state": "empty",
            "stale_reason": reason,
            "provider": "api_football",
            "cohort_minutes": 450,
            "leagues": [],
            "totals": {},
            "known_gaps": [],
            "sources": [],
        },
        "pools": {},
        "squad_roses": {},
    }


__all__ = ["build_scouting_bundle", "fallback_scouting_bundle"]
