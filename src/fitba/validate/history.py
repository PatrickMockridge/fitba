"""Validation rules for the curated and published historical record.

Pure functions: the CLI guard loads YAML/JSON, calls these, and exits non-zero
on structural errors. Missing backfill or partial historical transfers are
warnings, not failures.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fitba.util.dates import season_bounds, seasons_between, validate_season
from fitba.validate.source_policy import is_blocked_url, no_publication_tokens

ROLE_GROUPS = {
    "manager",
    "assistant_manager",
    "first_team_coach",
    "goalkeeper_coach",
    "sporting_director",
    "head_of_recruitment",
    "academy_director",
    "chief_executive",
    "chair",
    "board_member",
}
REASON_OUT = {
    "end_of_contract",
    "dismissed",
    "resigned",
    "moved_club",
    "interim_end",
    "role_change",
    "retired",
    "unknown",
}
DATE_PRECISIONS = {"day", "month", "season", "year"}
HONOUR_COMPETITIONS = {
    "League",
    "Scottish Cup",
    "League Cup",
    "European Cup Winners' Cup",
    "European Super Cup",
}
SEASON_STATUSES = {"completed", "in_progress"}
CUP_COMPETITIONS = {
    "sco:premiership",
    "sco:championship",
    "sco:league-one",
    "sco:league-two",
    "sco:league-cup",
    "sco:scottish-cup",
    "uefa:europa-league",
    "uefa:conference-league",
    "uefa:cup-winners-cup",
    "uefa:super-cup",
}


def _date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _boundary(value: Any, precision: str, *, end: bool) -> date | None:
    parsed = _date(value)
    if parsed is not None:
        return parsed
    text = str(value or "")
    try:
        if precision == "month" and len(text) >= 7:
            year, month = int(text[:4]), int(text[5:7])
            from calendar import monthrange

            day = monthrange(year, month)[1] if end else 1
            return date(year, month, day)
        if precision == "year" and len(text) >= 4:
            return date(int(text[:4]), 12, 31) if end else date(int(text[:4]), 1, 1)
        if precision == "season" and len(text) >= 4:
            return date(int(text[:4]) + 1, 6, 30) if end else date(int(text[:4]), 7, 1)
    except (ValueError, TypeError):
        return None
    return None


def _staff_rows(staff: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for person in staff.get("people") or []:
        for stint in person.get("stints") or []:
            rows.append(
                {
                    **stint,
                    "person_id": person.get("person_id"),
                    "name": person.get("name"),
                }
            )
    return rows


def _covers_season(row: dict[str, Any], season: str) -> bool:
    start = _boundary(row.get("start"), str(row.get("start_precision") or "day"), end=False)
    if start is None:
        return False
    end = (
        _boundary(row.get("end"), str(row.get("end_precision") or "day"), end=True)
        if row.get("end")
        else None
    )
    lower, upper = season_bounds(season)
    return start <= upper and (end is None or end >= lower)


def _manager_overlap(rows: list[dict[str, Any]]) -> list[str]:
    managers = [row for row in rows if row.get("role_group") == "manager"]
    errors = []
    for index, first in enumerate(managers):
        first_start = _boundary(
            first.get("start"), str(first.get("start_precision") or "day"), end=False
        )
        first_end = _boundary(first.get("end"), str(first.get("end_precision") or "day"), end=True)
        if first_start is None:
            continue
        for second in managers[index + 1 :]:
            second_start = _boundary(
                second.get("start"),
                str(second.get("start_precision") or "day"),
                end=False,
            )
            second_end = _boundary(
                second.get("end"), str(second.get("end_precision") or "day"), end=True
            )
            if second_start is None:
                continue
            if first_end is not None and second_start >= first_end:
                continue
            if second_end is not None and first_start >= second_end:
                continue
            errors.append(
                f"manager stints overlap: {first.get('stint_id')} and {second.get('stint_id')}"
            )
    return errors


def validate_reference(
    *,
    policy: dict[str, Any],
    era: dict[str, Any],
    staff: dict[str, Any],
    honours: dict[str, Any],
    seasons: dict[str, Any],
    transfer_rows: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    blocked_ids, blocked_hosts = no_publication_tokens()

    era_doc = era.get("era") or {}
    for field in ("id", "label", "start", "chairman_person_id", "first_season"):
        if not era_doc.get(field):
            errors.append(f"era: missing {field}")
    if not era_doc.get("pillars"):
        errors.append("era: no strategic pillars")
    for pillar in era_doc.get("pillars") or []:
        if not pillar.get("id") or not pillar.get("title"):
            errors.append("era: pillar missing id/title")

    people = staff.get("people") or []
    person_ids = [str(person.get("person_id")) for person in people]
    if len(person_ids) != len(set(person_ids)):
        errors.append("staff: duplicate person_id")
    rows = _staff_rows(staff)
    stint_ids = [str(row.get("stint_id")) for row in rows]
    if len(stint_ids) != len(set(stint_ids)):
        errors.append("staff: duplicate stint_id")
    manager_rows = [row for row in rows if row.get("role_group") == "manager"]
    current_managers = [row for row in manager_rows if not row.get("end")]
    current_chairs = [
        row for row in rows if row.get("role_group") == "chair" and not row.get("end")
    ]
    current_ceos = [
        row for row in rows if row.get("role_group") == "chief_executive" and not row.get("end")
    ]
    if len(current_managers) != 1:
        errors.append(f"staff: expected one current manager, found {len(current_managers)}")
    if len(current_chairs) != 1:
        errors.append(f"staff: expected one current chair, found {len(current_chairs)}")
    if len(current_ceos) > 1:
        errors.append(f"staff: expected at most one current CEO, found {len(current_ceos)}")
    for row in rows:
        stint_id = row.get("stint_id")
        if row.get("role_group") not in ROLE_GROUPS:
            errors.append(f"staff {stint_id}: invalid role_group {row.get('role_group')!r}")
        if row.get("start_precision") not in DATE_PRECISIONS:
            errors.append(f"staff {stint_id}: invalid start_precision")
        if row.get("end") and row.get("end_precision") not in DATE_PRECISIONS:
            errors.append(f"staff {stint_id}: invalid end_precision")
        if not row.get("source_urls"):
            errors.append(f"staff {stint_id}: no source URLs")
        for url in row.get("source_urls") or []:
            if is_blocked_url(str(url), blocked_hosts):
                errors.append(f"staff {stint_id}: blocked source {url!r}")
        for source_id in row.get("source_ids") or []:
            if source_id in blocked_ids:
                errors.append(f"staff {stint_id}: blocked source id {source_id!r}")
        if row.get("reason_out") and row.get("reason_out") not in REASON_OUT:
            errors.append(f"staff {stint_id}: invalid reason_out {row.get('reason_out')!r}")
        start = _boundary(row.get("start"), str(row.get("start_precision") or "day"), end=False)
        end = _boundary(row.get("end"), str(row.get("end_precision") or "day"), end=True)
        if start is None:
            errors.append(f"staff {stint_id}: unparseable start {row.get('start')!r}")
        if row.get("end") and end is None:
            errors.append(f"staff {stint_id}: unparseable end {row.get('end')!r}")
        if start and end and end < start:
            errors.append(f"staff {stint_id}: end precedes start")
    errors.extend(_manager_overlap(rows))

    expected = (policy.get("honours") or {}).get("expected_totals") or {}
    honour_rows = honours.get("honours") or []
    honour_ids = [str(row.get("honour_id")) for row in honour_rows]
    if len(honour_ids) != len(set(honour_ids)):
        errors.append("honours: duplicate honour_id")
    counts: dict[str, int] = {}
    for honour in honour_rows:
        competition = honour.get("competition")
        counts[competition] = counts.get(competition, 0) + 1
        if competition not in HONOUR_COMPETITIONS:
            errors.append(f"honours {honour.get('honour_id')}: invalid competition")
        try:
            validate_season(str(honour.get("season")))
        except ValueError as exc:
            errors.append(f"honours {honour.get('honour_id')}: {exc}")
        if honour.get("date") and _date(honour.get("date")) is None:
            errors.append(f"honours {honour.get('honour_id')}: unparseable date")
        if competition in {"Scottish Cup", "League Cup"} and (
            not honour.get("opponent") or not honour.get("score") or not honour.get("venue")
        ):
            errors.append(
                f"honours {honour.get('honour_id')}: cup win needs opponent, score and venue"
            )
        manager_person = honour.get("manager_person_id")
        if manager_person:
            honour_date = _date(honour.get("date"))
            covered = False
            for row in manager_rows:
                if row.get("person_id") != manager_person:
                    continue
                start = _boundary(
                    row.get("start"), str(row.get("start_precision") or "day"), end=False
                )
                end = _boundary(row.get("end"), str(row.get("end_precision") or "day"), end=True)
                if (
                    honour_date
                    and start
                    and (not end or honour_date <= end)
                    and honour_date >= start
                ):
                    covered = True
            if not covered:
                errors.append(
                    f"honours {honour.get('honour_id')}: manager stint does not cover the date"
                )
    for competition, total in expected.items():
        if counts.get(competition, 0) != int(total):
            errors.append(f"honours: {competition} count {counts.get(competition, 0)} != {total}")
    for required in (policy.get("honours") or {}).get("required_ids") or []:
        if required not in honour_ids:
            errors.append(f"honours: required id {required!r} is missing")
    if "league-cup-2023-24" in honour_ids:
        errors.append("honours: 2023-24 League Cup was runners-up, not a major honour")

    season_docs = seasons.get("seasons") or []
    season_names = [str(doc.get("season")) for doc in season_docs]
    if len(season_names) != len(set(season_names)):
        errors.append("seasons: duplicate season")
    if season_docs:
        first = str(season_docs[0].get("season"))
        last = str(season_docs[-1].get("season"))
        expected_seasons = seasons_between(first, last)
        if season_names != expected_seasons:
            errors.append("seasons: season files are not contiguous")
    transfer_ids = {str(row.get("transfer_id")) for row in transfer_rows if row.get("transfer_id")}
    for doc in season_docs:
        season = doc.get("season")
        status = doc.get("status")
        if status not in SEASON_STATUSES:
            errors.append(f"season {season}: invalid status {status!r}")
        if not doc.get("manager_stint_ids"):
            errors.append(f"season {season}: no manager_stint_ids")
        for stint_id in doc.get("manager_stint_ids") or []:
            if stint_id not in stint_ids:
                errors.append(f"season {season}: unknown stint {stint_id!r}")
        for honour_id in doc.get("honours") or []:
            if honour_id not in honour_ids:
                errors.append(f"season {season}: unknown honour {honour_id!r}")
        for run in list(doc.get("cup_runs") or []) + list(doc.get("europe") or []):
            if run.get("competition_id") not in CUP_COMPETITIONS:
                errors.append(f"season {season}: unknown competition {run.get('competition_id')!r}")
        if not doc.get("source_urls"):
            errors.append(f"season {season}: no source URLs")
        for url in doc.get("source_urls") or []:
            if is_blocked_url(str(url), blocked_hosts):
                errors.append(f"season {season}: blocked source {url!r}")
        if status == "completed":
            review = doc.get("review") or {}
            for field in ("what_worked", "what_did_not", "trade_off", "read", "look_ahead"):
                if not review.get(field):
                    errors.append(f"season {season}: review missing {field}")
            if not doc.get("reviewed_at"):
                errors.append(f"season {season}: completed review has no reviewed_at")
        if status == "in_progress":
            if doc.get("review"):
                errors.append(f"season {season}: in-progress season has a final review")
            if not doc.get("as_of"):
                errors.append(f"season {season}: in-progress season has no as_of")
        for transfer_id in (doc.get("key_transfers") or {}).get("arrivals", []) + (
            doc.get("key_transfers") or {}
        ).get("departures", []):
            if transfer_id not in transfer_ids:
                errors.append(f"season {season}: unknown transfer {transfer_id!r}")

    for doc in season_docs:
        season = str(doc.get("season"))
        if not any(_covers_season(row, season) for row in manager_rows):
            errors.append(f"season {season}: no manager stint covers the season")

    if not rows:
        warnings.append("staff register is empty")
    return errors, warnings


def validate_published(
    *,
    index: dict[str, Any],
    season_docs: dict[str, dict[str, Any]],
    club_history: list[dict[str, Any]],
    transfer_payload: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    blocked_ids, blocked_hosts = no_publication_tokens()
    if index.get("schema_version") != "1.0.0":
        errors.append("history index schema_version is not 1.0.0")
    season_refs = index.get("seasons") or []
    ref_seasons = [str(item.get("season")) for item in season_refs]
    if set(ref_seasons) != set(season_docs):
        errors.append("history index seasons do not match season files")
    for item in season_refs:
        if item.get("href") != f"/history/{item.get('season')}/":
            errors.append(f"history index href mismatch for {item.get('season')}")
        for forbidden in ("position", "points", "played", "gf", "ga", "gd"):
            if forbidden in item:
                errors.append(f"history index season row duplicates league fact {forbidden!r}")
    honour_ids = {str(row.get("honour_id")) for row in index.get("honours") or []}
    transfer_ids = {str(row.get("transfer_id")) for row in transfer_payload.get("transfers") or []}
    history_by_season = {str(row.get("season")): row for row in club_history}
    for season, doc in season_docs.items():
        if doc.get("schema_version") != "1.0.0":
            errors.append(f"season {season}: schema_version is not 1.0.0")
        if doc.get("season") != season:
            errors.append(f"season {season}: file season mismatch")
        ref = next(
            (item for item in season_refs if str(item.get("season")) == season),
            None,
        )
        if ref and ref.get("status") != doc.get("status"):
            errors.append(f"season {season}: index status mismatch")
        if doc.get("status") == "completed" and not doc.get("review"):
            errors.append(f"season {season}: completed season has no review")
        if doc.get("status") == "in_progress" and doc.get("review"):
            errors.append(f"season {season}: in-progress season has a final review")
        for honour_id in doc.get("honour_ids") or []:
            if honour_id not in honour_ids:
                errors.append(f"season {season}: unknown published honour {honour_id!r}")
        for transfer_id in (doc.get("key_transfers") or {}).get("arrivals", []) + (
            doc.get("key_transfers") or {}
        ).get("departures", []):
            if transfer_id not in transfer_ids:
                errors.append(f"season {season}: unknown published transfer {transfer_id!r}")
        managers = doc.get("managers") or []
        for manager in managers:
            if int(manager.get("won", 0)) + int(manager.get("drawn", 0)) + int(
                manager.get("lost", 0)
            ) != int(manager.get("played", 0)):
                errors.append(
                    f"season {season}: manager {manager.get('name')} W-D-L does not match played"
                )
            if int(manager.get("won", 0)) * 3 + int(manager.get("drawn", 0)) != int(
                manager.get("points", 0)
            ):
                errors.append(f"season {season}: manager {manager.get('name')} points mismatch")
        league = history_by_season.get(season)
        if league:
            played = sum(int(manager.get("played", 0)) for manager in managers)
            points = sum(int(manager.get("points", 0)) for manager in managers)
            gd = sum(int(manager.get("gf", 0)) - int(manager.get("ga", 0)) for manager in managers)
            unattributed = int((doc.get("coverage") or {}).get("unattributed_matches") or 0)
            if played != int(league.get("played", 0)) and not unattributed:
                errors.append(f"season {season}: manager played does not match league row")
            if points != int(league.get("points", 0)) and not unattributed:
                errors.append(f"season {season}: manager points do not match league row")
            if gd != int(league.get("gd", 0)) and not unattributed:
                errors.append(f"season {season}: manager goal difference does not match league row")
        for source in doc.get("sources") or []:
            if is_blocked_url(str(source.get("url") or ""), blocked_hosts):
                errors.append(f"season {season}: blocked source {source.get('url')!r}")
        selection = doc.get("selection") or {}
        if selection.get("status") == "unavailable":
            for key in ("players_used", "average_starter_age", "u21_minutes_share"):
                if selection.get(key) is not None:
                    errors.append(f"season {season}: unavailable selection has {key} populated")
        if (
            doc.get("status") == "completed"
            and (doc.get("coverage") or {}).get("league_record") == "unavailable"
        ):
            warnings.append(f"season {season}: league record unavailable")
    for source in index.get("sources") or []:
        if is_blocked_url(str(source.get("url") or ""), blocked_hosts):
            errors.append(f"history index: blocked source {source.get('url')!r}")
    for transfer in transfer_payload.get("transfers") or []:
        for source_id in transfer.get("source_ids") or []:
            if source_id in blocked_ids:
                errors.append(f"transfers: blocked source id {source_id!r}")
    for window in transfer_payload.get("windows") or []:
        if window.get("coverage") not in {"audited", "curated_partial"}:
            errors.append(f"window {window.get('key')}: invalid coverage")
    transfer_rows = transfer_payload.get("transfers") or []
    for move in (policy.get("transfers") or {}).get("required_moves") or []:
        matches = [
            row
            for row in transfer_rows
            if row.get("player_name") == move.get("player")
            and row.get("direction") == move.get("direction")
            and row.get("season") == move.get("season")
        ]
        if len(matches) != 1:
            errors.append(
                f"required historical move {move.get('player')} "
                f"{move.get('direction')} {move.get('season')} has {len(matches)} rows"
            )
    if not (policy.get("era") or {}).get("first_season"):
        warnings.append("history policy has no first_season")
    return errors, warnings


__all__ = ["validate_published", "validate_reference"]
