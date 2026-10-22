"""Build the squad payload and the current-player link index.

The squad payload is the shared destination for every structured player mention
on the site. Hrefs are precomputed here so client components never need to read
files, and news/rumour free text can carry a separate mention link.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from fitba.ingest.availability import (
    load_availability_frame,
    load_availability_meta,
)
from fitba.ingest.career_roles import load_career_meta, load_career_roles, load_evidence
from fitba.ingest.forum import STOP_SURNAMES
from fitba.ingest.match_data import (
    load_match_meta,
    load_player_roles,
    load_playing_time,
    playing_time_for,
    role_block_for,
)
from fitba.ingest.player_attributes import (
    load_player_attributes,
    load_player_attributes_meta,
)
from fitba.ingest.position_stats import load_position_stats, load_position_stats_meta
from fitba.ingest.squad import load_squad_players, load_squad_stats
from fitba.normalize.career import (
    career_role_summary,
    choose_display_role,
    current_role_slots,
)
from fitba.normalize.names import strip_accents
from fitba.settings import (
    aberdeen as aberdeen_config,
)
from fitba.settings import (
    role_notes as role_notes_config,
)
from fitba.settings import (
    roles as roles_config,
)
from fitba.settings import (
    source_ids as source_ids_config,
)
from fitba.util.dates import utc_now_iso

STAT_FIELDS = [
    "scope",
    "competition",
    "team_name",
    "season",
    "appearances",
    "starts",
    "minutes",
    "goals",
    "assists",
    "yellow_cards",
    "red_cards",
    "rating",
    "shots_total",
    "shots_on",
    "passes_total",
    "passes_key",
    "pass_accuracy",
    "saves",
    "conceded",
    "tackles",
    "blocks",
    "interceptions",
    "duels_total",
    "duels_won",
    "dribbles_attempts",
    "dribbles_success",
    "fouls_drawn",
    "fouls_committed",
    "penalty_won",
    "penalty_committed",
    "penalty_scored",
    "penalty_missed",
    "penalty_saved",
]
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
STATUS_ORDER = {"squad": 0, "loan_in": 1, "loan_out": 2}
POSITION_ORDER = {"GK": 0, "DEF": 1, "MID": 2, "FWD": 3}


def _stat_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row.get(field) for field in STAT_FIELDS}


def _totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    totals: dict[str, Any] = {
        field: sum(int(row.get(field) or 0) for row in rows) for field in TOTAL_FIELDS
    }
    rated = [
        (float(row["rating"]), int(row.get("appearances") or 0))
        for row in rows
        if row.get("rating") is not None and int(row.get("appearances") or 0) > 0
    ]
    if rated:
        weight = sum(appearances for _, appearances in rated)
        weighted = sum(rating * appearances for rating, appearances in rated)
        totals["rating"] = round(weighted / weight, 2)
    else:
        totals["rating"] = None
    return totals


def _summary(players: list[dict[str, Any]]) -> dict[str, Any]:
    squad = [player for player in players if player["status"] != "loan_out"]
    ages = [player["age"] for player in squad if player.get("age") is not None]
    positions: dict[str, int] = {}
    statuses: dict[str, int] = {}
    role_families: dict[str, int] = {}
    role_families_squad: dict[str, int] = {}
    primary_groups: dict[str, int] = {}
    primary_sides: dict[str, int] = {}
    for player in players:
        position = player.get("position_group") or "Unknown"
        positions[position] = positions.get(position, 0) + 1
        statuses[str(player["status"])] = statuses.get(str(player["status"]), 0) + 1
        family = (player.get("role") or {}).get("family") or "unknown"
        role_families[str(family)] = role_families.get(str(family), 0) + 1
        if player["status"] != "loan_out":
            role_families_squad[str(family)] = role_families_squad.get(str(family), 0) + 1
        primary = (player.get("career_role") or {}).get("primary_slot") or {}
        group = (primary.get("groups") or ["unknown"])[0]
        primary_groups[str(group)] = primary_groups.get(str(group), 0) + 1
        side = primary.get("side") or "unknown"
        primary_sides[str(side)] = primary_sides.get(str(side), 0) + 1
    return {
        "total_players": len(players),
        "squad_size": len(squad),
        "loans_out": statuses.get("loan_out", 0),
        "loans_in": statuses.get("loan_in", 0),
        "average_age": round(sum(ages) / len(ages), 1) if ages else None,
        "stats_unavailable": sum(
            1 for player in players if player["stats_coverage"] == "unavailable"
        ),
        "stats_partial": sum(1 for player in players if player["stats_coverage"] == "partial"),
        "by_position": dict(sorted(positions.items())),
        "by_role_family": dict(sorted(role_families.items())),
        "by_role_family_squad": dict(sorted(role_families_squad.items())),
        "by_primary_group": dict(sorted(primary_groups.items())),
        "by_primary_side": dict(sorted(primary_sides.items())),
        "by_status": dict(sorted(statuses.items())),
    }


def _position_totals(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return {
        "matches": sum(int(row.get("matches") or 0) for row in rows),
        "minutes_on_pitch": sum(int(row.get("minutes_on_pitch") or 0) for row in rows),
        "conceded_on_pitch": sum(int(row.get("conceded_on_pitch") or 0) for row in rows),
        "clean_sheets": sum(int(row.get("clean_sheets") or 0) for row in rows),
        "own_goals": sum(int(row.get("own_goals") or 0) for row in rows),
    }


def _attribute_block(row: dict[str, Any] | None) -> dict[str, Any]:
    if row is None:
        return {
            "value": None,
            "status": "unknown",
            "unknown_reason": "not_sourced",
            "source": None,
            "conflict_state": "none",
            "conflict_sources": [],
        }
    source = None
    if row.get("status") == "known":
        source = {
            "id": row.get("source_id"),
            "tier": row.get("source_tier"),
            "url": row.get("source_url"),
            "revision": row.get("source_revision"),
            "verified_at": row.get("verified_at"),
            "confidence": row.get("confidence"),
            "derivation": row.get("derivation"),
        }
    conflict_sources = []
    if row.get("status") == "conflict":
        conflict_sources = json.loads(row.get("conflict_sources") or "[]")
    return {
        "value": row.get("value"),
        "status": row.get("status"),
        "unknown_reason": row.get("unknown_reason"),
        "source": source,
        "conflict_state": row.get("conflict_state"),
        "conflict_sources": conflict_sources,
    }


def squad_payload(season: str, generated_at: str | None = None) -> dict[str, Any]:
    players_frame = load_squad_players()
    stats_frame = load_squad_stats()
    position_frame = load_position_stats()
    position_meta = load_position_stats_meta()
    attribute_frame = load_player_attributes()
    attribute_meta = load_player_attributes_meta()
    match_meta = load_match_meta()
    role_frame = load_player_roles()
    playing_frame = load_playing_time()
    role_rows = role_frame.to_dicts() if role_frame.height else []
    playing_rows = playing_frame.to_dicts() if playing_frame.height else []
    career_frame = load_career_roles()
    evidence_frame = load_evidence()
    career_rows = career_frame.to_dicts() if career_frame.height else []
    evidence_rows = evidence_frame.to_dicts() if evidence_frame.height else []
    career_meta = load_career_meta()
    availability_frame = load_availability_frame()
    availability_meta = load_availability_meta()
    availability_by_player = {
        int(row["player_id"]): row
        for row in (availability_frame.to_dicts() if availability_frame.height else [])
        if row.get("player_id") is not None
    }
    tactical_notes: dict[str, list[dict[str, Any]]] = {}
    for note in role_notes_config().get("players", []) or []:
        tactical_notes.setdefault(str(note.get("player_key") or ""), []).append(
            {
                "note_type": note.get("note_type"),
                "note": note.get("note"),
                "source": note.get("source"),
                "verified_at": note.get("verified_at"),
            }
        )
    career_by_player: dict[int, list[dict[str, Any]]] = {}
    for row in career_rows:
        career_by_player.setdefault(int(row["player_id"]), []).append(row)
    evidence_by_player: dict[int, list[dict[str, Any]]] = {}
    for row in evidence_rows:
        evidence_by_player.setdefault(int(row["player_id"]), []).append(row)
    role_config = roles_config()
    club_id = str(aberdeen_config()["club_id"])
    parent_team_id = int(source_ids_config()["teams"][club_id]["api_football"])
    season_year = int(str(season)[:4])

    attributes_by_player: dict[str, dict[str, dict[str, Any]]] = {}
    for row in attribute_frame.to_dicts() if attribute_frame.height else []:
        attributes_by_player.setdefault(str(row["player_key"]), {})[str(row["attribute"])] = row

    stats_by_player: dict[int, list[dict[str, Any]]] = {}
    for row in stats_frame.to_dicts() if stats_frame.height else []:
        stats_by_player.setdefault(int(row["player_id"]), []).append(row)

    position_by_player: dict[int, list[dict[str, Any]]] = {}
    for row in position_frame.to_dicts() if position_frame.height else []:
        position_by_player.setdefault(int(row["player_id"]), []).append(row)

    players: list[dict[str, Any]] = []
    for row in players_frame.to_dicts() if players_frame.height else []:
        player_id = int(row["player_id"])
        rows = stats_by_player.get(player_id, [])
        relevant = [item for item in rows if item["scope"] in {"club", "loan"}]
        other = [item for item in rows if item["scope"] == "other"]
        status = str(row["status"])
        player_attributes = attributes_by_player.get(str(row["player_key"]), {})
        foot = _attribute_block(player_attributes.get("preferred_foot"))
        attribute_coverage = (
            "conflict"
            if foot["status"] == "conflict"
            else "known"
            if foot["status"] == "known"
            else "unknown"
        )
        playing = playing_time_for(
            playing_rows,
            player_id=player_id,
            team_id=parent_team_id,
            season_year=season_year,
        )
        if playing["coverage"] == "no_matches":
            playing["coverage"] = "not_applicable" if status == "loan_out" else "unavailable"
            playing["note"] = (
                "On loan; Aberdeen playing time is not applicable."
                if status == "loan_out"
                else "No 2026-27 Aberdeen lineup appearances were found."
            )
        else:
            playing["coverage"] = (
                "available"
                if match_meta.get("fixtures_with_lineups") == match_meta.get("fixtures_total")
                else "partial"
            )
            playing["note"] = (
                "Starts, substitute appearances and on-pitch minutes are "
                "reconstructed from fixture lineups and substitution events."
            )
            if status == "loan_out":
                playing["note"] += (
                    " These are Aberdeen appearances only; loan-club lineups are not ingested."
                )
        role = role_block_for(
            role_rows,
            player_id=player_id,
            team_id=parent_team_id,
            season_year=season_year,
            starts_total=int(playing.get("starts") or 0),
            config=role_config,
        )
        if role["status"] == "unknown" and status == "loan_out":
            role["unknown_reason"] = "loan_out_no_aberdeen_starts"
        elif role["status"] == "unknown" and int(playing.get("starts") or 0) > 0:
            role["unknown_reason"] = "no_role_evidence"
        if role.get("source"):
            role["source"]["fixtures_covered"] = int(match_meta.get("fixtures_with_grid") or 0)
            role["source"]["starts_with_role"] = int(role.get("starts_with_role") or 0)
        role.update(current_role_slots(role, config=role_config))
        player_evidence = evidence_by_player.get(player_id, [])
        career = career_role_summary(
            career_by_player.get(player_id, []),
            starts_total=len(player_evidence),
            starts_with_role=sum(1 for item in player_evidence if item.get("role_code")),
            config=role_config,
            current_season=season,
        )
        if not player_evidence and not career_meta.get("generated_at"):
            career["status"] = "unavailable"
            career["unknown_reason"] = "career_backfill_not_run"
        display = choose_display_role(role, career, config=role_config)
        position_rows = position_by_player.get(player_id, [])
        position_stats = [
            {key: value for key, value in item.items() if key != "ingested_at"}
            for item in position_rows
        ]
        full_name = str(row.get("full_name") or row["name"])
        players.append(
            {
                "player_id": player_id,
                "player_key": row["player_key"],
                "href": f"/players/{player_id}/",
                "name": row["name"],
                "full_name": full_name,
                "firstname": row.get("firstname"),
                "lastname": row.get("lastname"),
                "age": row.get("age"),
                "number": row.get("number"),
                "position": row.get("position"),
                "position_group": row.get("position_group"),
                "nationality": row.get("nationality"),
                "injured": bool(row.get("injured")),
                "provider_flag": bool(row.get("injured")),
                "availability": (
                    {
                        "status": availability_by_player[player_id].get("status"),
                        "confidence": availability_by_player[player_id].get("confidence"),
                        "source_id": availability_by_player[player_id].get("source_id"),
                        "source_url": availability_by_player[player_id].get("source_url"),
                        "verified_at": availability_by_player[player_id].get("verified_at"),
                        "note": availability_by_player[player_id].get("note"),
                        "stale": bool(availability_by_player[player_id].get("stale")),
                        "conflict": bool(availability_by_player[player_id].get("conflict")),
                    }
                    if player_id in availability_by_player
                    else {"status": "unknown", "confidence": "unknown"}
                ),
                "status": status,
                "loan": (
                    {
                        "club": row.get("loan_club"),
                        "since": row.get("loan_since"),
                        "end_date": row.get("loan_end_date"),
                    }
                    if status in {"loan_out", "loan_in"}
                    else None
                ),
                "stats_coverage": row["stats_coverage"],
                "stats_note": row["stats_note"],
                "attributes": {
                    "preferred_foot": foot,
                    "coverage": attribute_coverage,
                },
                "role": role,
                "career_role": career,
                "display_role": display,
                "tactical_notes": tactical_notes.get(str(row["player_key"]), []),
                "playing_time": playing,
                "stats": [_stat_payload(item) for item in relevant],
                "totals": _totals(relevant) if relevant else None,
                "position_stats": position_stats,
                "position_totals": _position_totals(position_rows),
                "position_stats_coverage": (
                    "no_matches"
                    if not position_rows
                    else str(position_meta.get("coverage", "unavailable"))
                ),
                "position_stats_note": (
                    str(position_meta.get("note", ""))
                    if position_rows
                    else (
                        "No 2026-27 fixture appearances with lineups and events "
                        "were found for this player."
                    )
                ),
                "other_stats": [_stat_payload(item) for item in other],
            }
        )

    players.sort(
        key=lambda player: (
            STATUS_ORDER.get(str(player["status"]), 9),
            POSITION_ORDER.get(str(player["position_group"]), 9),
            str(player["name"]),
        )
    )

    return {
        "club_id": str(aberdeen_config()["club_id"]),
        "name": "Aberdeen",
        "season": season,
        "generated_at": generated_at or utc_now_iso(),
        "players": players,
        "summary": {
            **_summary(players),
            "position_stats_coverage": position_meta.get("coverage", "unavailable"),
            "fixtures_covered": position_meta.get("fixtures_covered", 0),
            "fixtures_total": position_meta.get("fixtures_total", 0),
            "own_goals_total": sum(
                int(player["position_totals"]["own_goals"])
                for player in players
                if player.get("position_totals")
            ),
            "attributes_foot_known": sum(
                1
                for player in players
                if player["attributes"]["preferred_foot"]["status"] == "known"
            ),
            "attributes_unknown": sum(
                1 for player in players if player["attributes"]["coverage"] == "unknown"
            ),
            "attributes_conflicts": sum(
                1 for player in players if player["attributes"]["coverage"] == "conflict"
            ),
            "roles_observed": sum(
                1 for player in players if player["role"]["status"] == "observed"
            ),
            "roles_partial": sum(1 for player in players if player["role"]["status"] == "partial"),
            "roles_unknown": sum(1 for player in players if player["role"]["status"] == "unknown"),
            "role_coverage": match_meta.get("role_coverage", "unavailable"),
            "formations_seen": match_meta.get("formations_seen", {}),
            "formations_unmapped": match_meta.get("unmapped_formations", []),
            "playing_time_available": sum(
                1 for player in players if player["playing_time"].get("coverage") == "available"
            ),
            "playing_time_unavailable": sum(
                1
                for player in players
                if player["playing_time"].get("coverage") in {"unavailable", "not_applicable"}
            ),
            "career_roles_observed": sum(
                1 for player in players if player["career_role"].get("status") == "observed"
            ),
            "career_roles_low_evidence": sum(
                1 for player in players if player["career_role"].get("status") == "low_evidence"
            ),
            "career_roles_mixed": sum(
                1 for player in players if player["career_role"].get("status") == "mixed"
            ),
            "career_roles_unknown": sum(
                1 for player in players if player["career_role"].get("status") == "unknown"
            ),
            "career_roles_unavailable": sum(
                1 for player in players if player["career_role"].get("status") == "unavailable"
            ),
            "display_overrides": sum(
                1
                for player in players
                if player["display_role"].get("source") == "aberdeen_override"
            ),
        },
        "position_stats_meta": position_meta,
        "attributes_meta": attribute_meta,
        "role_meta": match_meta,
        "career_meta": career_meta,
        "availability_meta": availability_meta,
        "coverage": {
            "status": "match" if players else "empty",
            "note": (
                "Current-season squad and per-competition statistics from "
                "API-Football. Roles come from the starting-XI formation grid; "
                "starts, substitute appearances and on-pitch minutes are "
                "reconstructed from lineups and substitution events. Loan tags "
                "come from the confirmed transfer register. Missing data is "
                "labelled unavailable or partial and is never filled with "
                "zeroes. Player photographs are not published."
            ),
        },
    }


def _alias_key(value: str) -> str:
    return re.sub(r"\s+", " ", strip_accents(value).casefold()).strip()


def _unique_surnames(players: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for player in players:
        surname = player.get("lastname") or (
            str(player["name"]).split()[-1] if " " in str(player["name"]) else ""
        )
        key = _alias_key(str(surname))
        if key:
            buckets.setdefault(key, []).append(player)
    return {
        key: rows[0]
        for key, rows in buckets.items()
        if len(rows) == 1 and len(key) >= 4 and key not in STOP_SURNAMES
    }


@dataclass(slots=True)
class PlayerLinkIndex:
    by_key: dict[str, str]
    players: list[dict[str, Any]]
    full_names: dict[str, dict[str, Any]]
    surnames: dict[str, dict[str, Any]]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> PlayerLinkIndex:
        players = payload.get("players", [])
        by_key = {
            str(player["player_key"]): str(player["href"])
            for player in players
            if player.get("player_key")
        }
        full_names: dict[str, dict[str, Any]] = {}
        for player in players:
            aliases = [str(player.get("name") or "")]
            first = str(player.get("firstname") or "").strip()
            last = str(player.get("lastname") or "").strip()
            if first and last:
                aliases.append(f"{first} {last}")
            for alias in aliases:
                key = _alias_key(alias)
                if len(key) >= 5:
                    full_names.setdefault(key, player)
        return cls(
            by_key=by_key,
            players=players,
            full_names=full_names,
            surnames=_unique_surnames(players),
        )

    def href(self, player_key: Any) -> str | None:
        if not player_key:
            return None
        return self.by_key.get(str(player_key))

    def mentions(self, text: Any, *, limit: int = 5) -> list[dict[str, str]]:
        """Find current players named in free text.

        Full names and display names match anywhere. A surname-only mention is
        accepted only when it is unique in the current squad and not a common
        word-like surname. Matches are deduped by player and returned in text
        order.
        """
        value = str(text or "")
        if not value:
            return []
        hits: list[tuple[int, dict[str, Any]]] = []
        used: set[int] = set()

        def scan(mapping: dict[str, dict[str, Any]], *, surname: bool) -> None:
            for key, player in mapping.items():
                player_id = int(player["player_id"])
                if surname and player_id in used:
                    continue
                pattern = re.compile(rf"\b{re.escape(key)}\b", re.IGNORECASE)
                for match in pattern.finditer(_alias_text(value)):
                    if player_id in used and not surname:
                        continue
                    hits.append((match.start(), player))
                    if not surname:
                        used.add(player_id)
                    break

        scan(self.full_names, surname=False)
        scan(self.surnames, surname=True)
        hits.sort(key=lambda item: item[0])
        output: list[dict[str, str]] = []
        seen: set[int] = set()
        for _, player in hits:
            player_id = int(player["player_id"])
            if player_id in seen:
                continue
            seen.add(player_id)
            output.append(
                {
                    "name": str(player.get("full_name") or player["name"]),
                    "href": str(player["href"]),
                }
            )
            if len(output) >= limit:
                break
        return output


def _alias_text(value: str) -> str:
    """Match against the accent-stripped text, as aliases are accent-stripped."""
    return strip_accents(value)


__all__ = ["PlayerLinkIndex", "squad_payload"]
