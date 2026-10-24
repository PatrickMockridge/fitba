"""Ingest the Aberdeen squad and current-season player statistics.

The squad is the current API-Football squad plus current loanees out from the
confirmed transfer register. Stats are per competition for the current season.
Missing data is labelled: a youth player with no statistics entries is
``unavailable``, not a set of zeroes, and a loanee's parent-club rows are never
presented as loan-club output.
"""

from __future__ import annotations

import json
import re
from typing import Any

import polars as pl
from rapidfuzz.fuzz import token_set_ratio

from fitba.ingest.match_data import ingest_match_data
from fitba.ingest.player_attributes import ingest_player_attributes
from fitba.ingest.transfers import published_transfers
from fitba.normalize.names import strip_accents
from fitba.normalize.player_stats import (
    STAT_COLUMNS,
    parse_stat_entry,
)
from fitba.normalize.player_stats import (
    to_int as _int,
)
from fitba.normalize.players import PlayerRegistry, normalize_player_name
from fitba.normalize.positions import squad_group
from fitba.settings import (
    NORMALIZED_DIR,
    ensure_dirs,
)
from fitba.settings import (
    aberdeen as aberdeen_config,
)
from fitba.settings import (
    source_ids as source_ids_config,
)
from fitba.sources import api_football
from fitba.sources.afc_official import load_roster
from fitba.sources.base import IngestResult
from fitba.util.dates import current_season, utc_now_iso

PLAYER_COLUMNS = [
    "player_id",
    "player_key",
    "name",
    "full_name",
    "firstname",
    "lastname",
    "birth_date",
    "age",
    "number",
    "position",
    "position_group",
    "nationality",
    "injured",
    "status",
    "loan_club",
    "loan_since",
    "loan_end_date",
    "stats_coverage",
    "stats_note",
    "roster_status",
    "squad_member",
    "exclusion_reason",
    "official_order",
    "official_section",
    "official_href",
    "official_position",
    "official_number",
    "official_only",
    "roster_conflict",
    "identity_source",
    "ingested_at",
]

STATUS_ORDER = {"squad": 0, "loan_in": 1, "loan_out": 2}
POSITION_ORDER = {"GK": 0, "DEF": 1, "MID": 2, "FWD": 3}
PUNCT_RE = re.compile(r"[^\w\s]")
SPACE_RE = re.compile(r"\s+")


def _club_key(value: str) -> str:
    normalized = strip_accents(value).casefold()
    normalized = PUNCT_RE.sub(" ", normalized)
    return SPACE_RE.sub(" ", normalized).strip()


def _club_matches(api_name: str, loan_club: str) -> bool:
    left = _club_key(api_name)
    right = _club_key(loan_club)
    if not left or not right:
        return False
    if left == right or left in right or right in left:
        return True
    return token_set_ratio(left, right) >= 85


def _season_year(season: str) -> int:
    try:
        return int(season[:4])
    except ValueError:
        return api_football.CURRENT_SEASON


def _loan_maps(season: str) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Latest current-season move per player; only a latest loan is a live loan.

    A player who went out on loan and then returned, or then left permanently,
    is not tagged as a current loanee.
    """
    latest: dict[str, dict[str, Any]] = {}
    for row in published_transfers():
        if row.get("season") != season:
            continue
        key = str(row.get("player_key") or "")
        if not key:
            continue
        current = latest.get(key)
        if current is None or (
            str(row.get("date_effective") or ""),
            str(row.get("transfer_id") or ""),
        ) > (
            str(current.get("date_effective") or ""),
            str(current.get("transfer_id") or ""),
        ):
            latest[key] = row

    outs = {
        key: row
        for key, row in latest.items()
        if row.get("transfer_kind") == "loan" and row.get("direction") == "out"
    }
    ins = {
        key: row
        for key, row in latest.items()
        if row.get("transfer_kind") == "loan" and row.get("direction") == "in"
    }
    return outs, ins


def _scope_for(
    entry: dict[str, Any],
    *,
    status: str,
    loan_club: str | None,
    parent_team_id: int,
) -> str:
    team = entry.get("team") or {}
    team_id = _int(team.get("id"))
    team_name = str(team.get("name") or "")
    if status in {"squad", "loan_in"} and team_id == parent_team_id:
        return "club"
    if status == "loan_out" and loan_club and _club_matches(team_name, loan_club):
        return "loan"
    return "other"


def _coverage(
    *,
    status: str,
    stats: list[dict[str, Any]],
    loan_club: str | None,
) -> tuple[str, str]:
    scope = "loan" if status == "loan_out" else "club"
    relevant = [row for row in stats if row["scope"] == scope]
    other_teams = sorted({row["team_name"] for row in stats if row["scope"] == "other"})

    if not relevant:
        if status == "loan_out" and loan_club:
            note = f"No 2026-27 statistics for {loan_club} in the licensed feed."
        else:
            note = "No 2026-27 player statistics in the licensed feed."
        if other_teams:
            note += f" The feed lists records for {', '.join(other_teams)}."
        return "unavailable", note

    partial = any(
        (row.get("appearances") or 0) > 0 and row.get("minutes") is None for row in relevant
    )
    if status == "loan_out" and loan_club:
        note = f"Loan-club statistics from {loan_club}."
    else:
        note = "Current-season statistics from the licensed feed."
    if partial:
        note += " Some minutes are missing from the source."
        return "partial", note
    return "available", note


def _player_row(
    *,
    player_id: int,
    player_key: str,
    fallback_name: str,
    fallback_position: str | None,
    fallback_age: int | None,
    number: int | None,
    status: str,
    loan: dict[str, Any] | None,
    details: list[dict[str, Any]],
    season_year: int,
    parent_team_id: int,
    ingested_at: str,
    player_registry: PlayerRegistry,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    profile = (details[0].get("player") if details else {}) or {}
    entries = (details[0].get("statistics") if details else []) or []
    source_name = str(profile.get("name") or fallback_name)
    resolved = player_registry.resolve(api_football_id=player_id, name=source_name)
    if resolved.status == "resolved":
        name = resolved.name
        parts = name.split(" ", 1)
        firstname = parts[0] or None
        lastname = parts[1] if len(parts) > 1 else None
        full_name = name
    else:
        name = source_name
        firstname = str(profile.get("firstname") or "").strip() or None
        lastname = str(profile.get("lastname") or "").strip() or None
        full_name = f"{firstname} {lastname}".strip() if firstname and lastname else name
    birth = profile.get("birth") or {}
    birth_date = str(birth.get("date") or "") or None
    loan_club = str(loan.get("to_club_name") or loan.get("from_club_name") or "") if loan else None
    if status == "loan_out" and loan:
        loan_club = str(loan.get("to_club_name") or "")
    if status == "loan_in" and loan:
        loan_club = str(loan.get("from_club_name") or "")

    stats: list[dict[str, Any]] = []
    position = resolved.position or fallback_position
    number = number if number is not None else resolved.shirt_number
    for entry in entries:
        scope = _scope_for(
            entry,
            status=status,
            loan_club=loan_club,
            parent_team_id=parent_team_id,
        )
        row = parse_stat_entry(
            player_id=player_id,
            player_key=player_key,
            entry=entry,
            scope=scope,
            season_year=season_year,
            ingested_at=ingested_at,
        )
        if row is not None:
            stats.append(row)
        games_position = (entry.get("games") or {}).get("position")
        if position is None and games_position:
            position = str(games_position)

    coverage, note = _coverage(status=status, stats=stats, loan_club=loan_club)
    age = _int(profile.get("age")) or fallback_age
    row = {
        "player_id": player_id,
        "player_key": player_key,
        "name": name,
        "full_name": full_name,
        "firstname": firstname,
        "lastname": lastname,
        "birth_date": birth_date,
        "age": age,
        "number": number,
        "position": position,
        "position_group": squad_group(position),
        "nationality": profile.get("nationality") or resolved.nationality,
        "injured": bool(profile.get("injured")) if profile else False,
        "status": status,
        "loan_club": loan_club,
        "loan_since": str(loan.get("date_effective")) if loan else None,
        "loan_end_date": loan.get("loan_end_date") if loan else None,
        "stats_coverage": coverage,
        "stats_note": note,
        "roster_status": "excluded_api",
        "squad_member": False,
        "exclusion_reason": "not_on_official_list",
        "official_order": None,
        "official_section": None,
        "official_href": None,
        "official_position": None,
        "official_number": None,
        "official_only": False,
        "roster_conflict": False,
        "identity_source": "api_football",
        "ingested_at": ingested_at,
    }
    return row, stats


def _roster_name(row: dict[str, Any]) -> str:
    return normalize_player_name(str(row.get("full_name") or row.get("name") or ""))


def _match_official_player(
    official: dict[str, Any], players: list[dict[str, Any]]
) -> dict[str, Any] | None:
    target = normalize_player_name(str(official.get("name") or ""))
    if not target:
        return None
    exact = [row for row in players if _roster_name(row) == target]
    if len(exact) == 1:
        return exact[0]
    target_tokens = target.split()
    target_surname = target_tokens[-1]
    target_initial = target_tokens[0][:1] if target_tokens else ""
    compatible: list[dict[str, Any]] = []
    for row in players:
        tokens = _roster_name(row).split()
        if not tokens:
            continue
        if tokens[-1] == target_surname:
            compatible.append(row)
            continue
        if (
            official.get("number") is not None
            and _int(row.get("number")) == _int(official.get("number"))
            and target_initial
            and tokens[0][:1] == target_initial
        ):
            compatible.append(row)
    if len(compatible) == 1:
        return compatible[0]
    return None


def _search_official_player(
    official: dict[str, Any],
    *,
    parent_team_id: int,
    season_year: int,
    force: bool,
) -> tuple[int, list[dict[str, Any]]] | None:
    tokens = normalize_player_name(str(official.get("name") or "")).split()
    if not tokens:
        return None
    surname = tokens[-1]
    candidates: list[int] = []
    for result in api_football.players_search(
        surname, team_id=parent_team_id, force=force
    ):
        player = result.get("player") or {}
        player_id = _int(player.get("id"))
        if player_id is None:
            continue
        statistics = result.get("statistics") or []
        if statistics:
            teams = {
                _int((entry.get("team") or {}).get("id"))
                for entry in statistics
            }
            if parent_team_id not in teams:
                continue
        if player_id not in candidates:
            candidates.append(player_id)
    if len(candidates) != 1:
        return None
    player_id = candidates[0]
    try:
        details = api_football.player(player_id, season=season_year, force=force)
    except Exception:  # noqa: BLE001 - identity is still usable
        details = []
    return player_id, details


def _apply_official(
    row: dict[str, Any],
    official: dict[str, Any],
    *,
    loan: dict[str, Any] | None,
    official_only: bool,
) -> None:
    section = str(official.get("section") or "")
    on_loan = section == "On loan"
    row["roster_status"] = "official_loan" if on_loan else "official"
    row["squad_member"] = True
    row["exclusion_reason"] = None
    row["official_order"] = official.get("official_order")
    row["official_section"] = official.get("section")
    row["official_href"] = official.get("href")
    row["official_position"] = official.get("position")
    row["official_number"] = official.get("number")
    row["official_only"] = official_only
    row["identity_source"] = (
        "afc_official" if official_only else "afc_official+api_football"
    )
    if official.get("number") is not None:
        row["number"] = official.get("number")
    if on_loan:
        row["status"] = "loan_out"
        if loan:
            row["loan_club"] = loan.get("to_club_name") or row.get("loan_club")
            row["loan_since"] = loan.get("date_effective") or row.get("loan_since")
            row["loan_end_date"] = loan.get("loan_end_date") or row.get("loan_end_date")
        else:
            row["loan_club"] = None
            row["loan_since"] = None
            row["loan_end_date"] = None
            if "loan club" not in str(row.get("stats_note") or "").casefold():
                row["stats_note"] = (
                    f"{row.get('stats_note') or ''} Official page lists this player on loan; "
                    "the loan club is not confirmed in the transfer register."
                ).strip()
    elif row.get("status") == "loan_out":
        row["status"] = "squad"
        row["roster_conflict"] = True


def ingest_squad(*, force: bool = False) -> IngestResult:
    ensure_dirs()
    try:
        club_id = str(aberdeen_config()["club_id"])
        parent_team_id = int(source_ids_config()["teams"][club_id]["api_football"])
        season = current_season()
        season_year = _season_year(season)
        loan_outs, loan_ins = _loan_maps(season)
        player_registry = PlayerRegistry()
        now = utc_now_iso()

        squad_records: list[dict[str, Any]] = []
        for item in api_football.players_squads(parent_team_id, force=force):
            squad_records.extend(item.get("players", []))

        players: list[dict[str, Any]] = []
        stats: list[dict[str, Any]] = []
        seen: set[str] = set()

        for record in squad_records:
            player_id = _int(record.get("id"))
            if player_id is None:
                continue
            player_key = f"api:player:{player_id}"
            seen.add(player_key)
            loan = loan_ins.get(player_key)
            status = "loan_in" if loan else "squad"
            try:
                details = api_football.player(player_id, season=season_year, force=force)
            except Exception:  # noqa: BLE001 - one player is not fatal
                details = []
            row, player_stats = _player_row(
                player_id=player_id,
                player_key=player_key,
                fallback_name=str(record.get("name") or f"Player {player_id}"),
                fallback_position=record.get("position"),
                fallback_age=_int(record.get("age")),
                number=_int(record.get("number")),
                status=status,
                loan=loan,
                details=details,
                season_year=season_year,
                parent_team_id=parent_team_id,
                ingested_at=now,
                player_registry=player_registry,
            )
            players.append(row)
            stats.extend(player_stats)

        for player_key, loan in loan_outs.items():
            if player_key in seen:
                continue
            player_id = _int(player_key.split(":")[-1])
            if player_id is None:
                continue
            try:
                details = api_football.player(player_id, season=season_year, force=force)
            except Exception:  # noqa: BLE001
                details = []
            row, player_stats = _player_row(
                player_id=player_id,
                player_key=player_key,
                fallback_name=str(loan.get("player_name") or f"Player {player_id}"),
                fallback_position=loan.get("position"),
                fallback_age=None,
                number=None,
                status="loan_out",
                loan=loan,
                details=details,
                season_year=season_year,
                parent_team_id=parent_team_id,
                ingested_at=now,
                player_registry=player_registry,
            )
            players.append(row)
            stats.extend(player_stats)

        official = load_roster(force=force)
        roster_only: list[dict[str, Any]] = []
        matched_official: set[str] = set()
        if official.get("status") == "available":
            for entry in official.get("players") or []:
                row = _match_official_player(entry, players)
                if row is not None:
                    matched_official.add(str(row["player_key"]))
                    _apply_official(
                        row,
                        entry,
                        loan=loan_outs.get(str(row["player_key"])),
                        official_only=False,
                    )
                    continue
                resolved = _search_official_player(
                    entry,
                    parent_team_id=parent_team_id,
                    season_year=season_year,
                    force=force,
                )
                if resolved is None:
                    roster_only.append(
                        {
                            "name": entry.get("name"),
                            "number": entry.get("number"),
                            "position": entry.get("position"),
                            "section": entry.get("section"),
                            "official_href": entry.get("href"),
                            "reason": "no_unique_api_player_id",
                        }
                    )
                    continue
                player_id, details = resolved
                player_key = f"api:player:{player_id}"
                if any(str(row["player_key"]) == player_key for row in players):
                    existing = next(
                        row for row in players if str(row["player_key"]) == player_key
                    )
                    _apply_official(
                        existing,
                        entry,
                        loan=loan_outs.get(player_key),
                        official_only=True,
                    )
                    matched_official.add(player_key)
                    continue
                loan = loan_outs.get(player_key)
                status = "loan_out" if entry.get("section") == "On loan" else "squad"
                new_row, new_stats = _player_row(
                    player_id=player_id,
                    player_key=player_key,
                    fallback_name=str(entry.get("name") or f"Player {player_id}"),
                    fallback_position=entry.get("position"),
                    fallback_age=None,
                    number=_int(entry.get("number")),
                    status=status,
                    loan=loan,
                    details=details,
                    season_year=season_year,
                    parent_team_id=parent_team_id,
                    ingested_at=now,
                    player_registry=player_registry,
                )
                _apply_official(
                    new_row,
                    entry,
                    loan=loan,
                    official_only=True,
                )
                players.append(new_row)
                stats.extend(new_stats)
                matched_official.add(player_key)
        if official.get("status") == "available":
            for row in players:
                if row.get("roster_status") not in {"official", "official_loan"}:
                    row["squad_member"] = False
                    row["roster_status"] = "excluded_api"
                    row["exclusion_reason"] = "not_on_official_list"
                    row["official_order"] = None
                    row["official_section"] = None
        else:
            for row in players:
                row["squad_member"] = True
                row["roster_status"] = "provider_fallback"
                row["exclusion_reason"] = None
                row["official_order"] = None
                row["official_section"] = None

        roster_meta = {
            "status": official.get("status") or "unavailable",
            "source_url": official.get("source_url"),
            "fetched_at": official.get("fetched_at"),
            "official_players": len(official.get("players") or []),
            "matched": len(matched_official),
            "official_only": sum(1 for row in players if row.get("official_only")),
            "excluded_api": sum(1 for row in players if not row.get("squad_member")),
            "ambiguous": len(roster_only),
            "staff_excluded": None,
            "loan_section": sum(
                1
                for entry in official.get("players") or []
                if entry.get("section") == "On loan"
            ),
            "roster_only": roster_only,
            "note": official.get("note"),
        }

        players.sort(
            key=lambda row: (
                0 if row.get("squad_member") else 1,
                STATUS_ORDER.get(str(row["status"]), 9),
                int(row["official_order"])
                if row.get("official_order") is not None
                else 10**6,
                POSITION_ORDER.get(str(row["position_group"]), 9),
                str(row["name"]),
            )
        )

        output_dir = NORMALIZED_DIR / "squad"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "roster_meta.json").write_text(
            json.dumps(roster_meta, indent=2) + "\n", encoding="utf-8"
        )
        player_frame = (
            pl.DataFrame(players).select(PLAYER_COLUMNS)
            if players
            else pl.DataFrame({column: [] for column in PLAYER_COLUMNS})
        )
        stat_frame = (
            pl.DataFrame(stats).select(STAT_COLUMNS)
            if stats
            else pl.DataFrame({column: [] for column in STAT_COLUMNS})
        )
        player_frame.write_parquet(output_dir / "aberdeen_players.parquet")
        stat_frame.write_parquet(output_dir / "aberdeen_stats.parquet")

        match_result = ingest_match_data(
            team_id=parent_team_id,
            squad_ids={int(row["player_id"]) for row in players},
            season_year=season_year,
            force=force,
        )
        attribute_result = ingest_player_attributes(players, force=force)

        return IngestResult(
            source="api_football",
            status="ok",
            rows=player_frame.height,
            path=str(output_dir / "aberdeen_players.parquet"),
            details={
                "season": season,
                "squad": sum(1 for row in players if row["status"] == "squad"),
                "loans_out": sum(1 for row in players if row["status"] == "loan_out"),
                "loans_in": sum(1 for row in players if row["status"] == "loan_in"),
                "roster_status": roster_meta["status"],
                "official_players": roster_meta["official_players"],
                "official_matched": roster_meta["matched"],
                "official_only": roster_meta["official_only"],
                "excluded_api": roster_meta["excluded_api"],
                "roster_only": roster_meta["ambiguous"],
                "stats_rows": stat_frame.height,
                "stats_unavailable": sum(
                    1 for row in players if row["stats_coverage"] == "unavailable"
                ),
                "match_data": match_result.details,
                "match_data_errors": match_result.errors,
                "player_attributes": attribute_result.details,
                "player_attributes_errors": attribute_result.errors,
            },
        )
    except Exception as exc:  # noqa: BLE001 - reported by the CLI
        return IngestResult(source="api_football", status="error", errors=[str(exc)])


def load_squad_players() -> pl.DataFrame:
    path = NORMALIZED_DIR / "squad" / "aberdeen_players.parquet"
    if not path.exists():
        return pl.DataFrame({column: [] for column in PLAYER_COLUMNS})
    return pl.read_parquet(path)


def load_squad_stats() -> pl.DataFrame:
    path = NORMALIZED_DIR / "squad" / "aberdeen_stats.parquet"
    if not path.exists():
        return pl.DataFrame({column: [] for column in STAT_COLUMNS})
    return pl.read_parquet(path)


__all__ = [
    "PLAYER_COLUMNS",
    "STAT_COLUMNS",
    "ingest_squad",
    "load_squad_players",
    "load_squad_stats",
]
