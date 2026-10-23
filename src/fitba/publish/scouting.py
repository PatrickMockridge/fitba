"""Publish the scouting hub, coverage and per-league pool documents."""

from __future__ import annotations

import json
from typing import Any

import polars as pl

from fitba.analytics.scouting import (
    RATE_FIELDS,
    CohortIndex,
    build_alignment,
    build_board,
    build_pool_rows,
    build_squad_profile,
    top_profiles,
)
from fitba.analytics.scouting_value import fit_value_model, value_for_row
from fitba.ingest.scouting import (
    PLAYER_ROLES_PATH,
    PLAYER_SEASON_PATH,
    POOL_META_PATH,
    ROLES_STATE_PATH,
)
from fitba.settings import (
    roles as roles_config,
)
from fitba.settings import (
    scouting_archetypes,
    scouting_leagues,
    scouting_model,
    scouting_teams,
    scouting_value,
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
        "club": resolve_team(row.get("team_name"), row.get("team_id")),
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
        **value_for_row(value_model, row),
        "cohort_basis": row.get("cohort_basis"),
        "cohort_n": row.get("cohort_n"),
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


def _leader(row: dict[str, Any], *, resolve_team, archetype_id: str) -> dict[str, Any]:
    archetype = (row.get("archetypes") or {}).get(archetype_id, {})
    return {
        "player_id": row.get("player_id"),
        "name": row.get("name"),
        "club": resolve_team(row.get("team_name"), row.get("team_id")),
        "league_id": row.get("competition_id"),
        "league_slug": row.get("league_slug"),
        "league_name": row.get("competition"),
        "minutes": row.get("minutes"),
        "rating": row.get("rating"),
        "rating_percentile": row.get("rating_percentile"),
        "adjusted_percentile": row.get("adjusted_percentile"),
        "raw_score": archetype.get("score"),
        "adjusted_score": archetype.get("adjusted_score"),
        "coverage": archetype.get("coverage"),
        "value_index": row.get("value_index"),
        "value_index_coverage": row.get("value_index_coverage"),
    }


def _pivot(
    *,
    squad_profile: list[dict[str, Any]],
    pool_rows: list[dict[str, Any]],
    resolve_team,
    archetype_labels: dict[str, str],
) -> dict[str, Any]:
    current: dict[str, Any] = {}
    for archetype_id in ("ball_winning_pivot", "deep_lying_playmaker"):
        candidates = [
            row
            for row in squad_profile
            if (row.get("archetypes") or {}).get(archetype_id, {}).get("score") is not None
        ]
        best = (
            max(
                candidates,
                key=lambda row: (
                    float(row["archetypes"][archetype_id]["score"]),
                    int(row.get("minutes") or 0),
                ),
            )
            if candidates
            else None
        )
        current[archetype_id] = (
            {
                "player_id": best.get("player_id"),
                "name": best.get("name"),
                "role_label": best.get("role_label"),
                "minutes": best.get("minutes"),
                "score": best["archetypes"][archetype_id]["score"],
                "coverage": best["archetypes"][archetype_id].get("coverage"),
            }
            if best
            else None
        )
    pool = {
        archetype_id: [
            _leader(row, resolve_team=resolve_team, archetype_id=archetype_id)
            for row in top_profiles(pool_rows, archetype_id, limit=5, score_key="adjusted_score")
        ]
        for archetype_id in ("ball_winning_pivot", "deep_lying_playmaker")
    }
    return {
        "label": "The double pivot",
        "current": current,
        "pool": pool,
        "archetype_labels": {
            key: archetype_labels.get(key, key)
            for key in ("ball_winning_pivot", "deep_lying_playmaker")
        },
        "hypothesis": (
            "A ball-winning pivot plus a deep-lying playmaker is a testable way to "
            "shield a centre-back line and still offer a short forward pass. This "
            "page measures the profile gap; it cannot show that a signing would "
            "reduce goals conceded. It is a hypothesis, not a recommendation."
        ),
    }


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
    roles = role_rows.filter(pl.col("league_id") == league_id).height if role_rows.height else 0
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


def build_scouting_bundle(
    *,
    season: str | None = None,
    squad_data: dict[str, Any],
    availability: dict[str, Any] | None,
    generated_at: str,
) -> dict[str, Any]:
    """Build the hub, coverage and every per-league pool document."""
    season_label = season or current_season()
    model = scouting_model()
    archetypes = scouting_archetypes()
    roles = roles_config()
    pool = _load_parquet(PLAYER_SEASON_PATH)
    role_rows = _load_parquet(PLAYER_ROLES_PATH)
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
    )
    all_rows = [row for rows in pools.values() for row in rows]
    premiership_rows = pools.get("sco:premiership", [])
    adjustment = build_alignment(all_rows, model)
    adjustment.pop("reference_values", None)
    index = CohortIndex(all_rows, model)
    board = build_board(
        squad_data=squad_data,
        pool_rows=premiership_rows,
        index=index,
        season=season_label,
        roles=roles,
        model=model,
        availability_entries=(availability or {}).get("entries") or [],
    )
    squad_profile = build_squad_profile(
        squad_data=squad_data,
        index=index,
        roles=roles,
        archetypes=archetypes,
        model=model,
    )
    value_model = fit_value_model()
    layer_zero = _layer_zero(board)
    pivot = _pivot(
        squad_profile=squad_profile,
        pool_rows=all_rows,
        resolve_team=resolve_team,
        archetype_labels=archetype_labels,
    )
    leaders = {
        definition["id"]: [
            _leader(row, resolve_team=resolve_team, archetype_id=definition["id"])
            for row in top_profiles(all_rows, definition["id"], limit=5, score_key="adjusted_score")
        ]
        for definition in archetype_defs
    }

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
        "pivot": pivot,
        "value_model": value_model,
        "leagues": league_list,
        "coverage": {
            "totals": totals,
            "known_gaps": known_gaps,
            "sources": coverage["sources"],
        },
        "limitations": [
            "Provider ratings are relative to a league and role cohort; they are not a verdict.",
            "The model cannot separate selection, availability and quality.",
            "The pivot card is a hypothesis, not a causal claim.",
            "No contracts, wages, fees or release clauses are claimed.",
            "No target list and no Aberdeen FC recommendation.",
        ],
    }
    search_players: list[dict[str, Any]] = []
    flag_codes = {"low_minutes": "l", "role_unknown": "r", "no_rating": "n"}
    for document in pool_documents.values():
        league = document["league"]
        for player in document["players"]:
            profile = player.get("profile") or {}
            search_players.append(
                {
                    "i": player.get("player_id"),
                    "n": player.get("name"),
                    "c": player.get("club"),
                    "l": league.get("slug"),
                    "na": player.get("nationality"),
                    "rf": player.get("role_family"),
                    "a": player.get("age"),
                    "m": player.get("minutes"),
                    "rt": player.get("rating"),
                    "p": player.get("rating_percentile"),
                    "ap": player.get("adjusted_percentile"),
                    "vi": player.get("value_index"),
                    "vc": player.get("value_index_coverage"),
                    "ab": player.get("adjustment_basis"),
                    "vl": player.get("value_low_gbp"),
                    "vh": player.get("value_high_gbp"),
                    "vconf": player.get("value_confidence"),
                    "vm": player.get("value_method"),
                    "ga": player.get("goals_assists_p90"),
                    "dr": player.get("dribbles_success_p90"),
                    "ps": player.get("passes_completed_p90"),
                    "pa": player.get("pass_completion_pct"),
                    "kp": player.get("key_passes_p90"),
                    "tk": player.get("tackles_p90"),
                    "it": player.get("interceptions_p90"),
                    "dw": player.get("duel_win_pct"),
                    "pr": profile.get("id"),
                    "psc": profile.get("score"),
                    "ar": {
                        key: [value.get("score"), value.get("adjusted_score")]
                        for key, value in (player.get("archetypes") or {}).items()
                    },
                    "f": [
                        flag_codes[flag] for flag in player.get("flags") or [] if flag in flag_codes
                    ],
                }
            )
    search_players.sort(key=_search_sort_key)
    search_document = {
        "schema_version": SCHEMA_VERSION,
        "season": season_label,
        "generated_at": generated_at,
        "state": "full" if search_players else "empty",
        "min_minutes": 450,
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
    return {
        "hub": hub,
        "coverage": coverage,
        "pools": pool_documents,
        "search": search_document,
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
    }


__all__ = ["build_scouting_bundle", "fallback_scouting_bundle"]
