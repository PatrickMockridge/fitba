"""Ingest Aberdeen transfers/loans from API-Football and merge curated rows.

The feed is a candidate source: it has dates, deal type and clubs, but no fees,
loan terms or youth/Highland loans. Feed rows are written to
``reference/transfers.candidates.yaml`` for review; only rows curated in
``reference/transfers.yaml`` are published.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import polars as pl
import yaml
from rapidfuzz.fuzz import token_set_ratio

from fitba.ingest.history import load_all_history
from fitba.normalize.players import PlayerRegistry, normalize_player_name
from fitba.normalize.teams import TeamRegistry
from fitba.normalize.transfer_plausibility import screen_transfers
from fitba.settings import (
    NORMALIZED_DIR,
    REFERENCE_DIR,
    WEB_DATA_DIR,
    ensure_dirs,
    history_markets,
)
from fitba.settings import (
    aberdeen as aberdeen_config,
)
from fitba.settings import (
    source_ids as source_ids_config,
)
from fitba.settings import (
    transfer_plausibility as transfer_plausibility_config,
)
from fitba.settings import (
    transfer_policy as transfer_policy_config,
)
from fitba.settings import (
    transfer_positions as transfer_positions_config,
)
from fitba.sources import api_football
from fitba.sources.base import IngestResult
from fitba.util.dates import utc_now_iso

POSITION_SOURCES = {"curated", "squad", "api_player_stats", "career_role", "unknown"}
POSITION_UNKNOWN_REASONS = {
    "no_allowed_source",
    "player_not_found",
    "youth_no_profile",
    "conflicting_sources",
    "budget",
    "historical_scope",
}
PROFILE_CALL_CAP = 120

TRANSFER_COLUMNS = [
    "transfer_id",
    "player_key",
    "player_name",
    "position",
    "position_source",
    "position_source_season",
    "position_unknown_reason",
    "nationality",
    "direction",
    "transfer_kind",
    "from_club_id",
    "from_club_name",
    "to_club_id",
    "to_club_name",
    "date_effective",
    "date_announced",
    "season",
    "window",
    "fee_status",
    "fee_amount",
    "fee_currency",
    "fee_raw",
    "loan_end_date",
    "recall_clause",
    "obligation_to_buy",
    "option_to_buy",
    "verification_status",
    "source_urls",
    "verified_at",
    "notes",
]

FEE_RE = re.compile(r"([€£$])?\s*([\d.,]+)\s*([KkMm])?")
CURRENCY = {"€": "EUR", "£": "GBP", "$": "USD", None: None}
NOISE_TYPES = {"raise", "swap", "end of career", "none"}
LOAN_RETURN_TYPES = {"return from loan", "back from loan"}
FREE_TYPES = {"free", "free agent", "free transfer"}
LOAN_TYPES = {"loan"}


def _parse_type(raw: str) -> tuple[str, str, float | None, str | None, str | None]:
    value = (raw or "").strip()
    lower = value.casefold()
    if lower in NOISE_TYPES:
        return "noise", "unknown", None, None, value
    if lower in LOAN_RETURN_TYPES:
        return "loan_return", "loan", None, None, value
    if lower in LOAN_TYPES:
        return "loan", "loan", None, None, value
    if lower in FREE_TYPES:
        return "free", "free", None, None, value
    fee = FEE_RE.search(value)
    if fee and fee.group(2):
        currency = CURRENCY[fee.group(1)]
        amount = float(fee.group(2).replace(",", ""))
        suffix = (fee.group(3) or "").casefold()
        if suffix == "k":
            amount *= 1_000
        elif suffix == "m":
            amount *= 1_000_000
        return "permanent", "feed_hint", amount, currency, value
    if lower in {"transfer", "n/a", "-", ""}:
        return "permanent", "unknown", None, None, value
    return "permanent", "unknown", None, None, value


def _window_for(value: date) -> str:
    if 5 <= value.month <= 9:
        return "summer"
    if value.month in {12, 1, 2}:
        return "winter"
    return "other"


def _transfer_season(value: date) -> str:
    """A summer deal in May/June belongs to the season starting that year."""
    if 5 <= value.month <= 9:
        start = value.year
    elif value.month in {12, 1, 2}:
        start = value.year if value.month == 12 else value.year - 1
    else:
        start = value.year if value.month >= 7 else value.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def _is_youth_or_reserve(name: str) -> bool:
    lowered = name.casefold()
    return any(token in lowered for token in (" u19", " u20", " u21", " ii", " b team", "academy"))


def _is_pseudo_team(name: str, player_name: str) -> bool:
    left = normalize_player_name(name)
    right = normalize_player_name(player_name)
    if left == right:
        return True
    # API-Football sometimes writes an out-of-contract player as a pseudo-club
    # using their surname/first name in either order.
    left_tokens = left.split()
    right_tokens = right.split()
    if right_tokens and right_tokens[-1] in left_tokens and len(left_tokens) <= 3:
        return True
    return token_set_ratio(left, right) >= 85


def _team_id(registry: TeamRegistry, name: str, raw_id: int | None = None) -> str:
    if raw_id is not None:
        source_map = source_ids_config().get("teams", {})
        for club_id, ids in source_map.items():
            if ids.get("api_football") == raw_id:
                return club_id
    resolved = registry.resolve(name)
    return resolved or registry.provisional(name)


def _candidate(
    *,
    player_record: dict[str, Any],
    transfer: dict[str, Any],
    club_api_id: int,
    club_id: str,
    registry: TeamRegistry,
    player_registry: PlayerRegistry,
    squads: dict[int, dict[str, Any]],
    now: str,
) -> dict[str, Any] | None:
    teams = transfer.get("teams") or {}
    out_team = teams.get("out") or {}
    in_team = teams.get("in") or {}
    if out_team.get("id") == club_api_id:
        direction = "out"
        counterparty = in_team
    elif in_team.get("id") == club_api_id:
        direction = "in"
        counterparty = out_team
    else:
        return None

    player_name = str(player_record.get("name") or "Unknown player").strip()
    kind, fee_status, fee_amount, fee_currency, fee_raw = _parse_type(
        str(transfer.get("type") or "")
    )
    if kind == "noise":
        return None

    counterparty_name = str(counterparty.get("name") or "Unknown").strip()
    counterparty_id = counterparty.get("id")
    if _is_youth_or_reserve(counterparty_name):
        return None
    if _is_pseudo_team(counterparty_name, player_name):
        counterparty_id = None
        counterparty_name = "Free agent"
        if kind == "permanent":
            kind = "free"
            fee_status = "free"

    resolved_player = player_registry.resolve(
        api_football_id=player_record.get("id"), name=player_name
    )
    squad = squads.get(int(resolved_player.api_football_id or 0), {})
    date_text = str(transfer.get("date") or "")
    try:
        effective = datetime.strptime(date_text, "%Y-%m-%d").date()
    except ValueError:
        return None
    season = _transfer_season(effective)
    window = _window_for(effective)
    other_id = (
        _team_id(registry, counterparty_name, counterparty_id)
        if counterparty_name != "Free agent"
        else "sco:free-agent"
    )
    display_name = registry.display_name_for_id(other_id, counterparty_name)
    from_id, from_name = (other_id, display_name) if direction == "in" else (club_id, "Aberdeen")
    to_id, to_name = (club_id, "Aberdeen") if direction == "in" else (other_id, display_name)
    key = hashlib.sha1(
        f"{resolved_player.player_key}|{direction}|{other_id}|{kind}|{season}|{window}".encode()
    ).hexdigest()[:16]
    return {
        "transfer_id": f"afc:{key}",
        "player_key": resolved_player.player_key,
        "player_name": resolved_player.name,
        "position": squad.get("position"),
        "position_source": "squad" if squad.get("position") else None,
        "position_source_season": None,
        "position_unknown_reason": None,
        "nationality": resolved_player.nationality,
        "direction": direction,
        "transfer_kind": kind,
        "from_club_id": from_id,
        "from_club_name": from_name,
        "to_club_id": to_id,
        "to_club_name": to_name,
        "date_effective": effective.isoformat(),
        "date_announced": effective.isoformat(),
        "season": season,
        "window": window,
        "fee_status": fee_status,
        "fee_amount": fee_amount,
        "fee_currency": fee_currency,
        "fee_raw": fee_raw,
        "loan_end_date": None,
        "recall_clause": None,
        "obligation_to_buy": None,
        "option_to_buy": None,
        "verification_status": "feed_only",
        "source_urls": [],
        "verified_at": now,
        "notes": "API-Football candidate; needs official/Wikipedia verification.",
    }


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            row["player_key"],
            row["direction"],
            row["transfer_kind"],
            row["season"],
        )
        grouped.setdefault(key, []).append(row)
    out: list[dict[str, Any]] = []
    for group in grouped.values():
        # Prefer a real club over a free-agent pseudo row, then the latest date.
        group.sort(
            key=lambda row: (
                row["to_club_id"] == "sco:free-agent" or row["from_club_id"] == "sco:free-agent",
                row["date_effective"],
            )
        )
        chosen = group[0]
        chosen["date_announced"] = min(row["date_effective"] for row in group)
        chosen["date_effective"] = max(row["date_effective"] for row in group)
        out.append(chosen)
    return sorted(out, key=lambda row: row["date_effective"], reverse=True)


def _squads(team_id: int) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for item in api_football.players_squads(team_id):
        for player in item.get("players", []):
            result[int(player["id"])] = player
    return result


def _player_id(row: dict[str, Any]) -> int | None:
    key = str(row.get("player_key") or "")
    if not key.startswith("api:player:"):
        return None
    tail = key.rsplit(":", 1)[-1]
    return int(tail) if tail.isdigit() else None


def _season_from_year(year: int) -> str:
    return f"{year}-{(year + 1) % 100:02d}"


def _position_from_family(family: str | None) -> str | None:
    if family == "goalkeeper":
        return "Goalkeeper"
    if family in {"centre_back", "full_back", "wing_back"}:
        return "Defender"
    if family in {
        "defensive_midfield",
        "central_midfield",
        "attacking_midfield",
        "wide_midfield",
    }:
        return "Midfielder"
    if family in {"wide_forward", "centre_forward"}:
        return "Attacker"
    return None


def _load_curated_positions() -> dict[str, dict[str, Any]]:
    payload = transfer_positions_config() or {}
    result: dict[str, dict[str, Any]] = {}
    for row in payload.get("players", []) or []:
        key = str(row.get("player_key") or "")
        position = row.get("position")
        if key and position:
            result[key] = {
                "position": position,
                "source_urls": list(row.get("source_urls") or []),
                "verified_at": row.get("verified_at"),
            }
    return result


def _load_career_positions() -> dict[str, str]:
    path = WEB_DATA_DIR / "squad" / "aberdeen.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    for player in payload.get("players", []) or []:
        key = str(player.get("player_key") or "")
        career = player.get("career_role") or {}
        display = player.get("display_role") or {}
        family = (
            (career.get("primary_slot") or {}).get("family")
            or display.get("family")
            or (player.get("role") or {}).get("family")
        )
        position = _position_from_family(family)
        if key and position:
            result[key] = position
    return result


def _profiles(
    needs: set[tuple[int, int]], max_calls: int = PROFILE_CALL_CAP
) -> tuple[dict[tuple[int, int], dict[str, Any]], bool]:
    """Fill missing positions from the player's season profile.

    Each requested ``(player_id, season)`` tries that season and up to two
    earlier ones. The call cap keeps the enrichment bounded; a truncated run
    marks the remaining rows unknown with reason ``budget``.
    """
    result: dict[tuple[int, int], dict[str, Any]] = {}
    calls = 0
    exhausted = False
    for player_id, season in sorted(needs):
        if calls >= max_calls:
            exhausted = True
            break
        for year in (season, season - 1, season - 2):
            if calls >= max_calls:
                exhausted = True
                break
            try:
                response = api_football.player(player_id, season=year, ttl_hours=168)
            except Exception:  # noqa: BLE001 - a missing profile is not fatal
                continue
            calls += 1
            if not response:
                continue
            item = response[0]
            player = item.get("player") or {}
            position = None
            for statistics in item.get("statistics", []):
                position = (statistics.get("games") or {}).get("position") or position
                if position:
                    break
            if position:
                result[(player_id, season)] = {
                    "position": position,
                    "nationality": player.get("nationality"),
                    "season": _season_from_year(year),
                }
                break
    return result, exhausted


def resolve_positions(rows: list[dict[str, Any]]) -> None:
    """Apply the documented position precedence in place.

    curated > current squad > season-specific API profile > career role >
    unknown. The resolver runs after the candidate/curated merge, so a curated
    correction always wins.
    """
    curated = _load_curated_positions()
    career = _load_career_positions()
    squad = {
        str(row.get("player_key")): row["position"]
        for row in rows
        if row.get("position") and str(row.get("position_source") or "") == "squad"
    }

    needs: set[tuple[int, int]] = set()
    for row in rows:
        key = str(row.get("player_key") or "")
        if row.get("position_source") == "curated" and row.get("position"):
            continue
        if key in curated or key in squad or key in career:
            continue
        if row.get("position_unknown_reason") == "historical_scope":
            continue
        player_id = _player_id(row)
        season = row.get("season")
        if player_id is not None and season:
            needs.add((player_id, int(str(season)[:4])))

    profiles, exhausted = _profiles(needs)
    for row in rows:
        key = str(row.get("player_key") or "")
        if row.get("position_source") == "curated" and row.get("position"):
            continue
        player_id = _player_id(row)
        season_year = int(str(row.get("season"))[:4]) if row.get("season") else None
        profile = profiles.get((player_id, season_year)) if player_id and season_year else None
        if key in curated:
            row["position"] = curated[key]["position"]
            row["position_source"] = "curated"
            row["position_source_season"] = None
            row["position_unknown_reason"] = None
        elif key in squad:
            row["position"] = squad[key]
            row["position_source"] = "squad"
            row["position_source_season"] = None
            row["position_unknown_reason"] = None
        elif profile and profile.get("position"):
            row["position"] = profile["position"]
            row["position_source"] = "api_player_stats"
            row["position_source_season"] = profile.get("season")
            row["position_unknown_reason"] = None
            row["nationality"] = row.get("nationality") or profile.get("nationality")
        elif key in career:
            row["position"] = career[key]
            row["position_source"] = "career_role"
            row["position_source_season"] = None
            row["position_unknown_reason"] = None
        elif row.get("position_unknown_reason") == "historical_scope":
            row["position"] = None
            row["position_source"] = "unknown"
            row["position_source_season"] = None
            row["position_unknown_reason"] = "historical_scope"
        else:
            row["position"] = None
            row["position_source"] = "unknown"
            row["position_source_season"] = None
            row["position_unknown_reason"] = "budget" if exhausted else "no_allowed_source"


def write_candidates(rows: list[dict[str, Any]], *, path: Path | None = None) -> str:
    target = path or REFERENCE_DIR / "transfers.candidates.yaml"
    target.write_text(
        yaml.safe_dump(
            {"transfers": rows},
            sort_keys=False,
            allow_unicode=True,
            width=120,
        ),
        encoding="utf-8",
    )
    return str(target)


def _excluded_candidate_ids() -> set[str]:
    policy = transfer_policy_config() or {}
    return {
        str(row.get("transfer_id"))
        for row in policy.get("candidate_exclusions") or []
        if row.get("transfer_id")
    }


def _load_curated() -> list[dict[str, Any]]:
    path = REFERENCE_DIR / "transfers.yaml"
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(payload.get("transfers", []))


def ingest_transfers(*, force: bool = False) -> IngestResult:
    ensure_dirs()
    club_id = str(aberdeen_config()["club_id"])
    club_api_id = int(source_ids_config()["teams"][club_id]["api_football"])
    registry = TeamRegistry()
    player_registry = PlayerRegistry()
    try:
        records = api_football.transfers(team_id=club_api_id, force=force)
        squads = _squads(club_api_id)
        excluded = _excluded_candidate_ids()
        now = utc_now_iso()
        rows: list[dict[str, Any]] = []
        for record in records:
            player_record = record.get("player") or {}
            for transfer in record.get("transfers", []):
                row = _candidate(
                    player_record=player_record,
                    transfer=transfer,
                    club_api_id=club_api_id,
                    club_id=club_id,
                    registry=registry,
                    player_registry=player_registry,
                    squads=squads,
                    now=now,
                )
                if row is None:
                    continue
                if row["transfer_id"] in excluded:
                    continue
                if row["date_effective"] < "2024-05-01":
                    continue
                rows.append(row)

        candidates = _dedupe(rows)
        resolve_positions(candidates)
        write_candidates(candidates)

        curated = _load_curated()
        by_id = {row["transfer_id"]: row for row in candidates}
        published: list[dict[str, Any]] = []
        for row in curated:
            transfer_id = row.get("transfer_id")
            candidate = by_id.get(transfer_id) if transfer_id else None
            merged = {**(candidate or {}), **row}
            if merged.get("verification_status") not in {"confirmed", "curated"}:
                continue
            if not merged.get("source_urls"):
                continue
            merged["from_club_name"] = registry.display_name_for_id(
                merged.get("from_club_id"), merged.get("from_club_name")
            )
            merged["to_club_name"] = registry.display_name_for_id(
                merged.get("to_club_id"), merged.get("to_club_name")
            )
            published.append(merged)
        resolve_positions(published)

        path = NORMALIZED_DIR / "transfers" / "aberdeen.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        complete = [
            {column: row.get(column) for column in TRANSFER_COLUMNS}
            for row in candidates + published
        ]
        frame = (
            pl.DataFrame(complete, infer_schema_length=200)
            if complete
            else pl.DataFrame({column: [] for column in TRANSFER_COLUMNS})
        )
        frame = (
            frame.select(TRANSFER_COLUMNS)
            .unique(subset=["transfer_id"], keep="last")
            .sort("date_effective", descending=True)
        )
        frame.write_parquet(path)
        return IngestResult(
            source="api_football",
            status="ok",
            rows=frame.height,
            path=str(path),
            details={
                "players": len(records),
                "candidates": len(candidates),
                "positions_enriched": sum(
                    1
                    for row in candidates + published
                    if row.get("position_source") in {"api_player_stats", "career_role"}
                ),
                "positions_unknown": sum(
                    1 for row in candidates + published if not row.get("position")
                ),
                "curated_published": len(published),
                "candidate_file": str(REFERENCE_DIR / "transfers.candidates.yaml"),
            },
        )
    except Exception as exc:  # noqa: BLE001 - reported to the CLI
        return IngestResult(source="api_football", status="error", errors=[str(exc)])


def _apply_historical_positions(rows: list[dict[str, Any]]) -> None:
    """Apply curated positions, then mark the rest historical_scope.

    Historical seasons are deliberately not profile-enriched by default: a
    current-season profile is not evidence for a 2019 move. A curated position
    or a squad position already attached to the row is kept.
    """
    curated = _load_curated_positions()
    for row in rows:
        key = str(row.get("player_key") or "")
        if key in curated:
            row["position"] = curated[key]["position"]
            row["position_source"] = "curated"
            row["position_source_season"] = None
            row["position_unknown_reason"] = None
        elif not row.get("position"):
            row["position"] = None
            row["position_source"] = "unknown"
            row["position_source_season"] = None
            row["position_unknown_reason"] = "historical_scope"


def ingest_transfer_history(
    *,
    from_date: str = "2019-07-01",
    max_profile_calls: int = 0,
    force: bool = False,
) -> IngestResult:
    """Build a review file of historical transfer candidates.

    This is separate from the daily ingest so the daily candidate file stays
    small. Curated rows in reference/transfers.yaml are merged by the normal
    ingest; this command only produces the historical review queue.
    """
    ensure_dirs()
    club_id = str(aberdeen_config()["club_id"])
    club_api_id = int(source_ids_config()["teams"][club_id]["api_football"])
    registry = TeamRegistry()
    player_registry = PlayerRegistry()
    try:
        records = api_football.transfers(team_id=club_api_id, force=force)
        squads = _squads(club_api_id)
        excluded = _excluded_candidate_ids()
        now = utc_now_iso()
        rows: list[dict[str, Any]] = []
        for record in records:
            player_record = record.get("player") or {}
            for transfer in record.get("transfers", []):
                row = _candidate(
                    player_record=player_record,
                    transfer=transfer,
                    club_api_id=club_api_id,
                    club_id=club_id,
                    registry=registry,
                    player_registry=player_registry,
                    squads=squads,
                    now=now,
                )
                if (
                    row is None
                    or row["transfer_id"] in excluded
                    or row["date_effective"] < from_date
                ):
                    continue
                rows.append(row)
        candidates = _dedupe(rows)
        if max_profile_calls:
            resolve_positions(candidates)
        _apply_historical_positions(candidates)
        path = write_candidates(
            candidates,
            path=REFERENCE_DIR / "transfers.candidates.history.yaml",
        )
        dates = sorted(row["date_effective"] for row in candidates)
        return IngestResult(
            source="api_football",
            status="ok",
            rows=len(candidates),
            path=path,
            details={
                "players": len(records),
                "candidates": len(candidates),
                "from_date": from_date,
                "earliest": dates[0] if dates else None,
                "latest": dates[-1] if dates else None,
                "positions_known": sum(1 for row in candidates if row.get("position")),
                "positions_unknown": sum(1 for row in candidates if not row.get("position")),
                "candidate_file": path,
            },
        )
    except Exception as exc:  # noqa: BLE001 - reported to the CLI
        return IngestResult(source="api_football", status="error", errors=[str(exc)])


def load_transfers() -> pl.DataFrame:
    path = NORMALIZED_DIR / "transfers" / "aberdeen.parquet"
    if not path.exists():
        return pl.DataFrame({column: [] for column in TRANSFER_COLUMNS})
    return pl.read_parquet(path)


@lru_cache(maxsize=1)
def _plausibility_context() -> tuple[dict[str, str], list[dict[str, Any]], set[str]]:
    birth_dates: dict[str, str] = {}
    for season_data in (load_all_history().get("seasons") or {}).values():
        rosters = season_data.get("rosters")
        if rosters is None or not rosters.height:
            continue
        for row in rosters.to_dicts():
            player_id = row.get("player_id")
            birth = row.get("birth_date")
            if player_id is not None and birth:
                birth_dates.setdefault(f"api:player:{int(player_id)}", str(birth))
    squad_path = NORMALIZED_DIR / "squad" / "aberdeen_players.parquet"
    if squad_path.exists():
        squad = pl.read_parquet(squad_path)
        for row in squad.to_dicts():
            player_id = row.get("player_id")
            birth = row.get("birth_date")
            if player_id is not None and birth:
                birth_dates.setdefault(f"api:player:{int(player_id)}", str(birth))
    markets = (history_markets() or {}).get("markets", [])
    accepted = {
        str(row.get("transfer_id"))
        for row in (transfer_plausibility_config() or {}).get("accepted", [])
        if row.get("transfer_id")
    }
    return birth_dates, markets, accepted


def published_transfers() -> list[dict[str, Any]]:
    frame = load_transfers()
    if frame.height == 0:
        return []
    rows = [
        row
        for row in frame.to_dicts()
        if row.get("verification_status") in {"confirmed", "curated"}
        and row.get("source_urls")
        and row.get("window") in {"summer", "winter", "other"}
    ]
    birth_dates, markets, accepted = _plausibility_context()
    published, _withheld = screen_transfers(
        rows,
        birth_dates=birth_dates,
        markets=markets,
        accepted=accepted,
    )
    return published


def withheld_transfers() -> list[dict[str, Any]]:
    """Rows withheld by the plausibility screen, for local review only."""
    frame = load_transfers()
    if frame.height == 0:
        return []
    rows = [
        row
        for row in frame.to_dicts()
        if row.get("verification_status") in {"confirmed", "curated"}
        and row.get("source_urls")
        and row.get("window") in {"summer", "winter", "other"}
    ]
    birth_dates, markets, accepted = _plausibility_context()
    _published, withheld = screen_transfers(
        rows,
        birth_dates=birth_dates,
        markets=markets,
        accepted=accepted,
    )
    return withheld
