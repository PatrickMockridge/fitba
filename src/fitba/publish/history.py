"""Historical-record payload builders.

The index owns the canonical staff and honours registers. Season documents own
the narrative and the derived season aggregates; they reference staff stints,
honours and transfers by id rather than republishing them. The web joins the
club history row by season.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import polars as pl
from pydantic import BaseModel, ConfigDict

from fitba.analytics.history import (
    baseline_profile,
    club_match_rows,
    era_scorecard,
    flatten_stints,
    manager_splits_by_season,
    manager_stint_records,
    season_records,
)
from fitba.analytics.recruitment import era_recruitment_profile, recruitment_profile
from fitba.analytics.selection import selection_profile
from fitba.analytics.style import era_style_average, style_profile
from fitba.analytics.valuation import (
    calibration_factor,
    estimate_transfer,
    summarise_valuations,
)
from fitba.ingest.history import (
    history_coverage,
    load_all_history,
)
from fitba.ingest.runner import load_matches
from fitba.ingest.transfers import published_transfers
from fitba.settings import (
    aberdeen as aberdeen_config,
)
from fitba.settings import (
    competitions as competitions_config,
)
from fitba.settings import (
    history_era,
    history_honours,
    history_markets,
    history_policy,
    history_seasons,
    history_staff,
)
from fitba.settings import (
    source_ids as source_ids_config,
)
from fitba.util.dates import season_bounds, season_start_year

SCHEMA_VERSION = "1.0.0"
COMPETITION_NAMES = {
    "sco:premiership": "Premiership",
    "sco:championship": "Championship",
    "sco:league-one": "League One",
    "sco:league-two": "League Two",
    "sco:league-cup": "League Cup",
    "sco:scottish-cup": "Scottish Cup",
    "uefa:europa-league": "Europa League",
    "uefa:conference-league": "Conference League",
    "uefa:cup-winners-cup": "European Cup Winners' Cup",
    "uefa:super-cup": "European Super Cup",
}
CORMACK_START = date(2019, 12, 16)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HistoryIndexDocument(StrictModel):
    schema_version: str = SCHEMA_VERSION
    era: dict[str, Any]
    generated_at: str
    coverage: dict[str, Any]
    scorecard: dict[str, Any]
    baseline: dict[str, Any]
    staff: list[dict[str, Any]]
    honours: list[dict[str, Any]]
    seasons: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    notes: str


class HistorySeasonDocument(StrictModel):
    schema_version: str = SCHEMA_VERSION
    season: str
    status: str
    as_of: str | None
    reviewed_at: str
    headline: str
    expectations: dict[str, Any]
    managers: list[dict[str, Any]]
    cup_runs: list[dict[str, Any]]
    europe: list[dict[str, Any]]
    honour_ids: list[str]
    key_transfers: dict[str, Any]
    recruitment: dict[str, Any]
    style: dict[str, Any]
    selection: dict[str, Any]
    academy: dict[str, Any]
    tactical: dict[str, Any]
    staff_changes: list[dict[str, Any]]
    review: dict[str, Any] | None
    interim_read: str | None
    coverage: dict[str, Any]
    sources: list[dict[str, Any]]


def history_index_schema() -> dict[str, Any]:
    return HistoryIndexDocument.model_json_schema()


def history_season_schema() -> dict[str, Any]:
    return HistorySeasonDocument.model_json_schema()


def _source_list(urls: list[str], *, verified_at: str = "2026-10-21") -> list[dict[str, Any]]:
    seen = set()
    output = []
    for url in urls:
        if not url or url in seen:
            continue
        seen.add(url)
        if "wikipedia.org" in url:
            source_id = "wikipedia"
        elif "afc.co.uk" in url:
            source_id = "afc_news"
        else:
            source_id = "unknown"
        output.append({"id": source_id, "url": url, "verified_at": verified_at})
    return output


def _derived_era(honour: dict[str, Any]) -> str:
    value = honour.get("date")
    if value:
        try:
            parsed = date.fromisoformat(str(value)[:10])
        except ValueError:
            parsed = None
        if parsed is not None:
            return "cormack" if parsed >= CORMACK_START else "pre_cormack"
    season = str(honour.get("season") or "1900-01")
    return "cormack" if season_start_year(season) >= 2019 else "pre_cormack"


def _honours_payload() -> list[dict[str, Any]]:
    rows = []
    for honour in history_honours().get("honours", []) or []:
        item = dict(honour)
        item["era"] = _derived_era(honour)
        rows.append(item)
    rows.sort(key=lambda item: (str(item.get("season") or ""), str(item.get("date") or "")))
    return rows


def _staff_payload(manager_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_stint = {str(record.get("stint_id")): record for record in manager_records}
    people = []
    for person in history_staff().get("people", []) or []:
        stints = []
        for stint in person.get("stints", []) or []:
            item = dict(stint)
            item["record"] = by_stint.get(str(stint.get("stint_id")))
            stints.append(item)
        people.append(
            {
                "person_id": person.get("person_id"),
                "name": person.get("name"),
                "stints": stints,
            }
        )
    return people


def _birth_dates(history_data: dict[str, Any]) -> dict[str, str]:
    birth: dict[str, str] = {}
    for season_data in (history_data.get("seasons") or {}).values():
        rosters = season_data.get("rosters")
        if rosters is None or not rosters.height:
            continue
        for row in rosters.to_dicts():
            player_id = row.get("player_id")
            value = row.get("birth_date")
            if player_id is not None and value:
                birth.setdefault(f"api:player:{int(player_id)}", str(value))
    return birth


def _selection_profiles(
    history_data: dict[str, Any], seasons: list[str], club_api_id: int
) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    cumulative: set[int] = set()
    backfill_policy = history_policy().get("backfill") or {}
    min_lineup = float(backfill_policy.get("min_lineup_coverage") or 0.6)
    min_age = float(backfill_policy.get("min_age_coverage") or 0.5)
    for index, season in enumerate(seasons):
        season_data = (history_data.get("seasons") or {}).get(season) or {}
        appearances = season_data.get("appearances")
        fixtures = season_data.get("fixtures")
        rosters = season_data.get("rosters")
        if appearances is None or not appearances.height:
            output[season] = {
                "status": "unavailable",
                "reason": "no_lineups",
                "note": "Historical lineups have not been backfilled for this season.",
            }
            continue
        focus = appearances.filter(pl.col("team_id") == club_api_id)
        roster_map = (
            {int(row["player_id"]): row for row in rosters.to_dicts()}
            if rosters is not None and rosters.height
            else {}
        )
        total = (
            fixtures.filter(pl.col("status").is_in(["FT", "AET", "PEN"])).height
            if fixtures is not None and fixtures.height
            else focus["fixture_id"].n_unique()
        )
        profile = selection_profile(
            focus.to_dicts(),
            season=season,
            fixtures_total=total,
            rosters=roster_map,
            previous_player_ids=cumulative if index else None,
            min_lineup_coverage=min_lineup,
            min_age_coverage=min_age,
        )
        output[season] = profile
        cumulative.update(int(player_id) for player_id in focus["player_id"].unique().to_list())
    return output


def _key_transfers_payload(
    doc: dict[str, Any],
    season: str,
    resolver: Any,
) -> dict[str, Any]:
    existing = doc.get("key_transfers") or {}
    arrivals = existing.get("arrivals") or resolver(season, "arrivals")
    departures = existing.get("departures") or resolver(season, "departures")
    return {
        "arrivals": arrivals,
        "departures": departures,
        "note": existing.get("note")
        or "Curated key business; the full set is in the transfer register.",
    }


def _staff_changes(stints: list[dict[str, Any]], season: str) -> list[dict[str, Any]]:
    start_bound, end_bound = season_bounds(season)
    # A June appointment belongs to the season that starts in July; include the
    # month before the season without pulling in the previous campaign.
    start_bound = start_bound - timedelta(days=31)
    changes: list[dict[str, Any]] = []
    for stint in stints:
        start = stint.get("start")
        end = stint.get("end")
        if start:
            try:
                start_date = date.fromisoformat(str(start)[:10])
            except ValueError:
                start_date = None
            if start_date and start_bound <= start_date <= end_bound:
                changes.append(
                    {
                        "stint_id": stint.get("stint_id"),
                        "person_id": stint.get("person_id"),
                        "name": stint.get("name"),
                        "role": stint.get("role"),
                        "role_group": stint.get("role_group"),
                        "date": str(start),
                        "change": "in",
                        "interim": bool(stint.get("interim")),
                        "reason_out": stint.get("reason_out"),
                        "source_urls": stint.get("source_urls") or [],
                    }
                )
        if end:
            try:
                end_date = date.fromisoformat(str(end)[:10])
            except ValueError:
                end_date = None
            if end_date and start_bound <= end_date <= end_bound:
                changes.append(
                    {
                        "stint_id": stint.get("stint_id"),
                        "person_id": stint.get("person_id"),
                        "name": stint.get("name"),
                        "role": stint.get("role"),
                        "role_group": stint.get("role_group"),
                        "date": str(end),
                        "change": "out",
                        "interim": bool(stint.get("interim")),
                        "reason_out": stint.get("reason_out"),
                        "source_urls": stint.get("source_urls") or [],
                    }
                )
    changes.sort(key=lambda item: (str(item.get("date") or ""), str(item.get("name") or "")))
    return changes


def _selection_era(profiles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    usable = [
        profile
        for profile in profiles.values()
        if profile.get("status") in {"available", "partial"}
        and profile.get("u21_minutes_share") is not None
    ]
    if not usable:
        return {"seasons": 0, "u21_minutes_share": None}
    u21_values = [float(profile["u21_minutes_share"]) for profile in usable]
    age_values = [
        float(profile["average_starter_age"])
        for profile in usable
        if profile.get("average_starter_age") is not None
    ]
    return {
        "seasons": len(usable),
        "u21_minutes_share": round(sum(u21_values) / len(u21_values), 3),
        "average_starter_age": round(sum(age_values) / len(age_values), 2) if age_values else None,
    }


def build_history_payloads(*, generated_at: str, season: str) -> dict[str, Any]:
    """Build the index and every season document from local data only."""
    policy = history_policy() or {}
    era_doc = (history_era() or {}).get("era") or {}
    season_docs = sorted(
        (history_seasons() or {}).get("seasons", []),
        key=lambda item: str(item.get("season") or ""),
    )
    seasons = [str(item["season"]) for item in season_docs]
    matches = load_matches(None)
    competitions = competitions_config().get("competitions", [])
    club_id = str(aberdeen_config()["club_id"])
    club_api_id = int(source_ids_config()["teams"][club_id]["api_football"])
    records = season_records(matches, competitions, club_id=club_id, seasons=seasons)
    club_rows = club_match_rows(matches, club_id)
    stints = flatten_stints(history_staff().get("people", []) or [])
    manager_records = manager_stint_records(club_rows, stints)
    splits = manager_splits_by_season(club_rows, stints, seasons)
    completed = [str(doc.get("season")) for doc in season_docs if doc.get("status") == "completed"]
    style_profiles = {
        current: style_profile(
            club_rows,
            season=current,
            competition_id=(records.get(current) or {}).get("competition_id"),
        )
        for current in seasons
    }
    era_style = era_style_average([style_profiles[current] for current in completed])
    history_data = load_all_history()
    selection_profiles = _selection_profiles(history_data, seasons, club_api_id)
    transfers = published_transfers()
    markets = (history_markets() or {}).get("markets", [])
    valuation_policy = policy.get("valuation") or {}
    fx = valuation_policy.get("fx_to_gbp")
    birth_dates = _birth_dates(history_data)
    calibration, anchor_count = calibration_factor(
        transfers, birth_dates=birth_dates, markets=markets, fx=fx
    )
    for row in transfers:
        row["fee_estimate"] = estimate_transfer(
            row,
            birth_dates=birth_dates,
            markets=markets,
            calibration=calibration,
            fx=fx,
        )
    recruitment_profiles: dict[str, dict[str, Any]] = {}
    for current in seasons:
        profile = recruitment_profile(
            transfers,
            season=current,
            markets=markets,
            birth_dates=birth_dates,
            coverage="audited"
            if current >= str((policy.get("transfers") or {}).get("audited_from") or "2024-25")
            else "curated_partial",
        )
        profile["valuation"] = summarise_valuations(
            [row for row in transfers if row.get("season") == current]
        )
        profile["valuation"]["anchor_count"] = anchor_count
        profile["valuation"]["calibration_factor"] = round(calibration, 3)
        recruitment_profiles[current] = profile
    era_recruitment = era_recruitment_profile(
        [recruitment_profiles[current] for current in completed]
    )
    era_recruitment["valuation"] = summarise_valuations(
        [row for row in transfers if row.get("season") in completed]
    )
    honours = _honours_payload()
    cormack_honours = [honour for honour in honours if honour.get("era") == "cormack"]
    baseline_config = (policy.get("era") or {}).get("baseline") or {}
    baseline = baseline_profile(
        matches,
        competitions,
        club_id=club_id,
        first=str(baseline_config.get("from") or "2013-14"),
        last=str(baseline_config.get("to") or "2018-19"),
    )
    scorecard = era_scorecard(
        seasons=completed,
        season_records_by_season=records,
        manager_records=manager_records,
        honours=cormack_honours,
        recruitment=era_recruitment,
        selection=_selection_era({current: selection_profiles[current] for current in completed}),
        style=era_style,
    )
    staff = _staff_payload(manager_records)

    source_urls: list[str] = []
    source_urls.extend(era_doc.get("source_urls") or [])
    for person in staff:
        for stint in person.get("stints") or []:
            source_urls.extend(stint.get("source_urls") or [])
    for honour in honours:
        source_urls.extend(honour.get("source_urls") or [])
    for doc in season_docs:
        source_urls.extend(doc.get("source_urls") or [])
    sources = _source_list(source_urls)

    selected_backfill = {current: history_coverage(current) for current in seasons}
    index = HistoryIndexDocument(
        era={
            **era_doc,
            "chairman_name": next(
                (
                    person.get("name")
                    for person in (history_staff().get("people") or [])
                    if person.get("person_id") == era_doc.get("chairman_person_id")
                ),
                None,
            ),
        },
        generated_at=generated_at,
        coverage={
            "status": "available" if records else "partial",
            "seasons_curated": len(seasons),
            "completed_seasons": sum(1 for doc in season_docs if doc.get("status") == "completed"),
            "analytics": {
                "managers": "available" if manager_records else "unavailable",
                "style": "available"
                if all(
                    profile.get("coverage") == "available" for profile in style_profiles.values()
                )
                else "partial",
                "selection": "available"
                if all(
                    profile.get("status") in {"available", "partial"}
                    for profile in selection_profiles.values()
                )
                else "partial",
                "recruitment": "curated_partial",
            },
            "backfill": selected_backfill,
            "transfer_coverage": {
                "audited_from": str(
                    (policy.get("transfers") or {}).get("audited_from") or "2024-25"
                ),
                "historical_from": str(
                    (policy.get("transfers") or {}).get("expected_windows_from") or "2019-20"
                ),
            },
            "note": (
                "Manager records are league-only. Pre-2024-25 transfer windows are "
                "curated partial. Selection depends on the historical lineup backfill."
            ),
        },
        scorecard=scorecard,
        baseline=baseline,
        staff=staff,
        honours=honours,
        seasons=[
            {
                "season": doc.get("season"),
                "status": doc.get("status"),
                "href": f"/history/{doc.get('season')}/",
                "competition_name": (records.get(str(doc.get("season"))) or {}).get(
                    "competition_name"
                ),
                "headline": doc.get("headline"),
                "honour_ids": doc.get("honours") or [],
                "manager_person_ids": list(
                    dict.fromkeys(
                        record.get("person_id")
                        for record in splits.get(str(doc.get("season")), [])
                        if record.get("person_id")
                    )
                ),
                "review_status": "complete"
                if doc.get("status") == "completed" and doc.get("review")
                else "in_progress"
                if doc.get("status") == "in_progress"
                else "pending",
            }
            for doc in season_docs
        ],
        sources=sources,
        notes=(
            "The Cormack era begins on 16 December 2019. 2019-20 is a transition "
            "season. Staff and honours are curated; league records and style "
            "proxies are measured; selection is measured where the historical "
            "lineup backfill is available."
        ),
    ).model_dump()

    key_transfer_map = policy.get("key_transfers") or {}

    def key_transfers_for(current: str, direction: str) -> list[str]:
        names = (key_transfer_map.get(current) or {}).get(direction) or []
        wanted = "in" if direction == "arrivals" else "out"
        ids: list[str] = []
        for name in names:
            match = next(
                (
                    row
                    for row in transfers
                    if row.get("season") == current
                    and row.get("direction") == wanted
                    and row.get("player_name") == name
                ),
                None,
            )
            if match and match.get("transfer_id"):
                ids.append(str(match["transfer_id"]))
        return ids

    season_payloads: dict[str, Any] = {}
    for doc in season_docs:
        current = str(doc.get("season"))
        league = records.get(current) or {}
        selection = selection_profiles.get(current) or {
            "status": "unavailable",
            "reason": "no_lineups",
        }
        tactical = doc.get("tactical") or {}
        style = dict(style_profiles.get(current) or {})
        style["era_average"] = era_style
        style["tactical_note"] = tactical.get("style_note")
        selection = dict(selection)
        selection["tactical_note"] = tactical.get("selection_note")
        season_payloads[current] = HistorySeasonDocument(
            season=current,
            status=str(doc.get("status") or "completed"),
            as_of=doc.get("as_of"),
            reviewed_at=str(doc.get("reviewed_at") or ""),
            headline=str(doc.get("headline") or ""),
            expectations={
                **(doc.get("expectations") or {}),
                "label": "curated",
            },
            managers=[record for record in splits.get(current, []) if record.get("person_id")],
            cup_runs=[
                {
                    **run,
                    "competition_name": COMPETITION_NAMES.get(
                        str(run.get("competition_id")), str(run.get("competition_id"))
                    ),
                }
                for run in doc.get("cup_runs") or []
            ],
            europe=[
                {
                    **run,
                    "competition_name": COMPETITION_NAMES.get(
                        str(run.get("competition_id")), str(run.get("competition_id"))
                    ),
                }
                for run in doc.get("europe") or []
            ],
            honour_ids=list(doc.get("honours") or []),
            key_transfers=_key_transfers_payload(doc, current, key_transfers_for),
            recruitment=recruitment_profiles.get(current) or {},
            style=style,
            selection=selection,
            academy={
                "debuts": doc.get("academy_debuts") or [],
                "measured_new_players": selection.get("debutants") or [],
                "debut_basis": selection.get("debut_basis"),
                "note": (
                    "Curated debuts are explicit club/academy records. Measured "
                    "new players are first appearances in the covered history, not "
                    "career debuts."
                ),
            },
            tactical={
                "shape_note": tactical.get("shape_note"),
                "style_note": tactical.get("style_note"),
                "selection_note": tactical.get("selection_note"),
            },
            staff_changes=_staff_changes(stints, current),
            review=doc.get("review"),
            interim_read=doc.get("interim_read"),
            coverage={
                "league_record": "available" if league else "unavailable",
                "manager_scope": "league",
                "unattributed_matches": sum(
                    1 for record in splits.get(current, []) if not record.get("person_id")
                ),
                "history": history_coverage(current),
                "transfers": "audited"
                if current >= str((policy.get("transfers") or {}).get("audited_from") or "2024-25")
                else "curated_partial",
                "note": (
                    "League-only manager records. Cup/Europe runs are curated exit "
                    "rounds. Selection is measured where historical lineups exist."
                ),
            },
            sources=_source_list(
                list(doc.get("source_urls") or [])
                + [
                    url
                    for change in _staff_changes(stints, current)
                    for url in change.get("source_urls") or []
                ]
            ),
        ).model_dump()

    return {"index": index, "seasons": season_payloads}


__all__ = [
    "HistoryIndexDocument",
    "HistorySeasonDocument",
    "build_history_payloads",
    "history_index_schema",
    "history_season_schema",
]
