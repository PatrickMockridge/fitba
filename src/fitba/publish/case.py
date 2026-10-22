"""Data analysis: the published bridge between matchday, recruitment and the record.

The storage path stays ``themes/aberdeen.json`` for URL and pipeline stability,
but the reader-facing page is Data analysis. Six claims carry the argument. Each
claim has a count, a status, an evidence table, a data-upgrade line and a
withdrawal condition.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Literal

import polars as pl
from pydantic import BaseModel, ConfigDict, model_validator

from fitba.analytics.history import club_match_rows, manager_stint_records
from fitba.analytics.tables import build_tables
from fitba.analytics.themes import build_theme_document
from fitba.ingest.match_data import (
    load_player_appearances,
    load_player_match_stats,
    load_team_shapes,
)
from fitba.settings import aberdeen as aberdeen_config
from fitba.settings import competitions as competitions_config
from fitba.settings import source_registry
from fitba.settings import themes as themes_config

SCHEMA_VERSION = "3.0.0"
State = Literal["fresh", "partial", "unavailable", "stale"]
ClaimStatus = Literal["supported", "mixed", "not_supported", "cant_test"]
Domain = Literal["matchday", "off_pitch", "chairman"]
Basis = Literal["measured", "inferred", "curated", "mixed", "unknown"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaseSource(StrictModel):
    id: str
    name: str
    url: str | None = None
    verified_at: str | None = None


class OwnerView(StrictModel):
    label: str
    text: str
    attribution: str


class ChairmanFrame(StrictModel):
    label: str
    text: str
    source: str
    note: str


class ClaimEvidence(StrictModel):
    metric: str
    count: str
    sample: str
    period: str
    status: ClaimStatus
    source: str
    note: str | None = None


class ClaimLink(StrictModel):
    label: str
    href: str


class Claim(StrictModel):
    id: str
    domain: Domain
    order: int
    title: str
    claim: str
    count: str
    status: ClaimStatus
    status_reason: str
    evidence: list[ClaimEvidence]
    better_data: str
    change_mind: str
    links: list[ClaimLink] = []

    @model_validator(mode="after")
    def _validate_claim(self) -> Claim:
        if "?" in self.title:
            raise ValueError(f"{self.id}: title must be declarative")
        if not self.evidence:
            raise ValueError(f"{self.id}: evidence is required")
        if not self.better_data:
            raise ValueError(f"{self.id}: better_data is required")
        if not self.change_mind:
            raise ValueError(f"{self.id}: change_mind is required")
        return self


class Benchmark(StrictModel):
    title: str
    note: str
    columns: list[str]
    rows: list[dict[str, Any]]


class CaseCoverage(StrictModel):
    status: State
    season: str
    availability_feed: str
    historical_appearances: str
    missing: list[str]
    note: str


class CaseDocument(StrictModel):
    schema_version: str = SCHEMA_VERSION
    generated_at: str
    season: str
    club_id: str
    state: State
    stale_reason: str | None = None
    served_generated_at: str | None = None
    title: str = "Data analysis"
    owner_view: OwnerView
    chairman_frame: ChairmanFrame
    thesis: str
    claims: list[Claim]
    benchmark: Benchmark
    coverage: CaseCoverage
    sources: list[CaseSource] = []
    notes: str

    @model_validator(mode="after")
    def _validate_document(self) -> CaseDocument:
        ids = [claim.id for claim in self.claims]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate claim ids")
        domains = {claim.domain for claim in self.claims}
        if not domains:
            raise ValueError("at least one claim is required")
        return self


def case_schema() -> dict[str, Any]:
    return CaseDocument.model_json_schema()


def _source_name(source_id: str) -> str:
    registry = (source_registry() or {}).get("sources") or {}
    return str((registry.get(source_id) or {}).get("name") or source_id)


def _source_ids() -> list[dict[str, Any]]:
    registry = (source_registry() or {}).get("sources") or {}
    refs = []
    for source_id in ("football_data_uk", "api_football", "afc_news", "wikipedia"):
        item = registry.get(source_id) or {}
        if not item:
            continue
        refs.append(
            {
                "id": source_id,
                "name": item.get("name") or source_id,
                "url": item.get("url") or item.get("base_url"),
                "verified_at": str(item.get("last_verified") or ""),
            }
        )
    return refs


def _theme(themes: list[dict[str, Any]], theme_id: str) -> dict[str, Any]:
    return next((theme for theme in themes if theme.get("theme_id") == theme_id), {})


def _group(theme: dict[str, Any], group: str) -> dict[str, Any]:
    for row in (theme.get("metrics") or {}).get("groups") or []:
        if row.get("group") == group:
            return row
    return {}


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _longest_runs(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: str(row.get("date") or ""))
    patterns = {
        "winning": lambda result: result == "W",
        "unbeaten": lambda result: result in {"W", "D"},
        "winless": lambda result: result in {"D", "L"},
        "losing": lambda result: result == "L",
    }
    output: dict[str, dict[str, Any]] = {}
    for name, predicate in patterns.items():
        best: list[dict[str, Any]] = []
        current: list[dict[str, Any]] = []
        for row in ordered:
            if predicate(str(row.get("result") or "")):
                current.append(row)
                if len(current) > len(best):
                    best = list(current)
            else:
                current = []
        output[name] = {
            "count": len(best),
            "start": str(best[0].get("date"))[:10] if best else None,
            "end": str(best[-1].get("date"))[:10] if best else None,
        }
    return output


def _manager_evidence(
    all_matches: pl.DataFrame,
    history_index: dict[str, Any],
    season: str,
) -> tuple[list[ClaimEvidence], str]:
    club_id = str(aberdeen_config()["club_id"])
    club_rows = club_match_rows(all_matches, club_id)
    people = history_index.get("staff") or []
    stints = []
    for person in people:
        for stint in person.get("stints") or []:
            if stint.get("role_group") != "manager":
                continue
            stints.append(
                {
                    **stint,
                    "person_id": person.get("person_id"),
                    "name": person.get("name"),
                }
            )
    records = manager_stint_records(club_rows, stints)
    by_name = {str(record.get("name") or ""): record for record in records}
    thelin = by_name.get("Jimmy Thelin") or {}
    leven = by_name.get("Peter Leven") or {}
    robinson = by_name.get("Stephen Robinson") or {}
    thelin_rows = []
    if thelin:
        start = str(thelin.get("first_match") or "")
        end = str(thelin.get("last_match") or "")
        thelin_rows = [
            row for row in club_rows.to_dicts() if start <= str(row.get("date") or "") <= end
        ]
    runs = _longest_runs(thelin_rows)
    evidence = [
        ClaimEvidence(
            metric="Thelin league record",
            count=f"{thelin.get('played', 0)} matches, {_fmt(thelin.get('ppg'))} points per game",
            sample="League only",
            period="2024-25 to January 2026",
            status="mixed",
            source=_source_name("football_data_uk"),
            note="The aggregate record; the cup is separate.",
        ),
        ClaimEvidence(
            metric="Thelin winning run",
            count=f"{runs['winning']['count']} straight league wins",
            sample="League only",
            period=f"{runs['winning']['start']} to {runs['winning']['end']}",
            status="mixed",
            source=_source_name("football_data_uk"),
            note="Not called a record; the covered league record has an 8-match run in 2014-15.",
        ),
        ClaimEvidence(
            metric="Thelin winless run",
            count=f"{runs['winless']['count']} league games without a win",
            sample="League only",
            period=f"{runs['winless']['start']} to {runs['winless']['end']}",
            status="mixed",
            source=_source_name("football_data_uk"),
        ),
        ClaimEvidence(
            metric="Leven interim",
            count=f"{leven.get('played', 0)} matches, {_fmt(leven.get('ppg'))} points per game",
            sample="League only",
            period="January to March 2026",
            status="mixed",
            source=_source_name("football_data_uk"),
            note="A caretaker spell inherited mid-season.",
        ),
        ClaimEvidence(
            metric="Robinson league record",
            count=(
                f"{robinson.get('played', 0)} matches, {_fmt(robinson.get('ppg'))} points per game"
            ),
            sample="League only",
            period="March 2026 to date",
            status="mixed",
            source=_source_name("football_data_uk"),
            note=(
                "Two nine-match spells of three wins, two draws and four defeats; "
                "the sample is small."
            ),
        ),
    ]
    count = (
        f"{thelin.get('played', 0)} + {leven.get('played', 0)} + "
        f"{robinson.get('played', 0)} league matches"
    )
    return evidence, count


def _benchmark(all_matches: pl.DataFrame, season: str) -> Benchmark:
    config = competitions_config()
    seasons = sorted(str(value) for value in all_matches["season"].unique().to_list())
    era_seasons = [value for value in seasons if value >= "2019-20"]
    positions: dict[str, list[int]] = defaultdict(list)
    points: dict[str, list[int]] = defaultdict(list)
    current: dict[str, int] = {}
    for current_season in era_seasons:
        tables = build_tables(all_matches, season=current_season, config=config)
        table = tables.get("sco:premiership")
        if table is None or not table.height:
            continue
        for row in table.to_dicts():
            name = str(row.get("team_name"))
            positions[name].append(int(row["position"]))
            points[name].append(int(row["points"]))
            if current_season == season:
                current[name] = int(row["position"])
    rows = []
    for name, values in positions.items():
        if len(values) < 3:
            continue
        ordered = sorted(points[name])
        median = ordered[len(ordered) // 2]
        rows.append(
            {
                "Club": name,
                "Seasons": len(values),
                "Best finish": min(positions[name]),
                "Worst finish": max(positions[name]),
                "Median points": median,
                "Current position": current.get(name, "—"),
            }
        )
    rows.sort(key=lambda row: (-int(row["Median points"]), str(row["Club"])))
    peers = [row for row in rows if row["Club"] != "Aberdeen"][:7]
    aberdeen = next((row for row in rows if row["Club"] == "Aberdeen"), None)
    if aberdeen:
        peers.append(aberdeen)
    return Benchmark(
        title="How the record compares",
        note=(
            "League performance only. Other clubs' transfer and wage models are "
            "not in the public record held here; they are not invented."
        ),
        columns=[
            "Club",
            "Seasons",
            "Best finish",
            "Worst finish",
            "Median points",
            "Current position",
        ],
        rows=peers,
    )


def _team_now_claim(
    shape: dict[str, Any], balance: dict[str, Any], team_shapes: pl.DataFrame
) -> dict[str, Any]:
    season = (balance.get("metrics") or {}).get("season") or {}
    last_five = (balance.get("metrics") or {}).get("last_five") or {}
    coverage = (shape.get("metrics") or {}).get("coverage") or {}
    formations = []
    if not team_shapes.is_empty():
        formations = (
            team_shapes.filter(
                (pl.col("team_id") == int(aberdeen_config()["api_football_id"]))
                & pl.col("formation").is_not_null()
            )
            .get_column("formation")
            .unique()
            .to_list()
        )
    evidence = [
        ClaimEvidence(
            metric="League record",
            count=(
                f"{season.get('won')} wins, {season.get('drawn')} draws and "
                f"{season.get('lost')} defeats; {season.get('points')} points; "
                f"{season.get('gf')} goals for and {season.get('ga')} against"
            ),
            sample=f"{season.get('played')} league matches",
            period="2026-27",
            status="supported",
            source=_source_name("football_data_uk"),
        ),
        ClaimEvidence(
            metric="Last five league matches",
            count=(
                f"{last_five.get('points')} points; {last_five.get('gf')} goals for and "
                f"{last_five.get('ga')} against; "
                f"{_fmt(float(last_five.get('shot_share') or 0) * 100, 1)}% share of shots"
            ),
            sample="5 league matches",
            period="2026-27",
            status="supported",
            source=_source_name("football_data_uk"),
        ),
        ClaimEvidence(
            metric="Kick-off shapes",
            count=(
                f"{coverage.get('fixtures_total', 0)} competitive fixtures with a recorded shape; "
                f"{coverage.get('unknown_shapes', 0)} unknown; {len(formations)} formations"
            ),
            sample="All competitive fixtures with a recorded shape",
            period="2026-27",
            status="supported",
            source=_source_name("api_football"),
            note="Shape is the kick-off formation only; mid-game switches are not recorded.",
        ),
    ]
    return {
        "count": (
            f"{season.get('played')} league matches; {coverage.get('fixtures_total', 0)} "
            f"competitive fixtures with a recorded shape"
        ),
        "status": "supported",
        "status_reason": (
            "The record and the shape churn are counted. What they mean is a separate question."
        ),
        "evidence": evidence,
    }


def _defence_claim(
    shape: dict[str, Any], cover: dict[str, Any], availability_entries: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    three = _group(shape, "three_cb")
    two = _group(shape, "two_cb")
    cb = _group(cover, "CB")
    coverage = (cover.get("metrics") or {}).get("coverage") or {}
    availability = coverage.get("availability") or {}
    defensive_known = sum(
        int(value) for status, value in availability.items() if status != "unknown"
    )
    defensive_unknown = sum(
        int(value) for status, value in availability.items() if status == "unknown"
    )
    squad_known = sum(
        1 for entry in availability_entries.values() if str(entry.get("status")) != "unknown"
    )
    squad_unknown = len(availability_entries) - squad_known
    items = {
        int(item.get("player_id")): item
        for item in cb.get("items") or []
        if item.get("player_id") is not None
    }
    knoester = items.get(37253) or {}
    tobors_note = ""
    for note in (cover.get("metrics") or {}).get("curated_notes") or []:
        if "Tobers" in str(note.get("name") or ""):
            tobors_note = str(note.get("note") or "")
    evidence = [
        ClaimEvidence(
            metric="Three centre-backs",
            count=(
                f"{three.get('matches', 0)} matches, "
                f"{_fmt(three.get('points_pg'))} points per game, "
                f"{_fmt(three.get('ga_pm'))} goals against per game"
            ),
            sample=f"{three.get('matches', 0)} competitive fixtures",
            period="2026-27",
            status="mixed",
            source=_source_name("football_data_uk"),
        ),
        ClaimEvidence(
            metric="Two centre-backs",
            count=(
                f"{two.get('matches', 0)} matches, "
                f"{_fmt(two.get('points_pg'))} points per game, "
                f"{_fmt(two.get('ga_pm'))} goals against per game"
            ),
            sample=f"{two.get('matches', 0)} competitive fixtures",
            period="2026-27",
            status="mixed",
            source=_source_name("football_data_uk"),
        ),
        ClaimEvidence(
            metric="Wide roles by shape",
            count=(
                f"{_fmt(three.get('wb_starts_pm'))} wing-back starts per match "
                "in the three-centre-back set; "
                f"{_fmt(three.get('wf_starts_pm'))} wide-forward starts. "
                f"In the two-centre-back set: {_fmt(two.get('wb_starts_pm'))} and "
                f"{_fmt(two.get('wf_starts_pm'))}."
            ),
            sample="Starts per match",
            period="2026-27",
            status="supported",
            source=_source_name("api_football"),
            note="The selection cost is visible; the performance effect is not established.",
        ),
        ClaimEvidence(
            metric="Defensive availability",
            count=(
                f"{squad_known} known / {squad_unknown} unknown squad entries; "
                f"{defensive_known} known / {defensive_unknown} unknown defensive players; "
                "Knoester "
                f"{knoester.get('starts', 0)} starts / {knoester.get('minutes', 0)} minutes; "
                "Tobers is not in the current squad"
            ),
            sample="Official team-news entries",
            period="2026-27",
            status="cant_test",
            source=_source_name("afc_news"),
            note=(
                "Absence is not injury; the ledger has no verified entry for either player. "
                + (tobors_note[:180] if tobors_note else "")
            ).strip(),
        ),
    ]
    return {
        "count": (
            f"{three.get('matches', 0)} three-centre-back fixtures vs "
            f"{two.get('matches', 0)} two-centre-back; "
            f"{squad_known} known / {squad_unknown} unknown availability"
        ),
        "status": "mixed",
        "status_reason": (
            "The selection cost is supported: the wide forwards do not start in "
            "the three-centre-back set. Whether the shape itself helps or hurts "
            "is not established: four matches, the manager chooses the shape, "
            "and the opponents and competitions differ. Availability cannot be tested."
        ),
        "evidence": evidence,
    }


def _attack_claim(balance: dict[str, Any]) -> dict[str, Any]:
    metrics = balance.get("metrics") or {}
    season = metrics.get("season") or {}
    last_five = metrics.get("last_five") or {}
    goals = metrics.get("goals_by_family") or {}
    evidence = [
        ClaimEvidence(
            metric="League goals",
            count=f"{season.get('gf')} for and {season.get('ga')} against",
            sample=f"{season.get('played')} league matches",
            period="2026-27",
            status="supported",
            source=_source_name("football_data_uk"),
        ),
        ClaimEvidence(
            metric="Share of goals from wide forwards and strikers",
            count=f"{_fmt(float(goals.get('attack_share') or 0) * 100, 0)}%",
            sample=f"{goals.get('total', 0)} league goals",
            period="2026-27",
            status="supported",
            source=_source_name("api_football"),
        ),
        ClaimEvidence(
            metric="Share of shots",
            count=f"{_fmt(float(season.get('shot_share') or 0) * 100, 1)}%",
            sample=f"{season.get('played')} league matches",
            period="2026-27",
            status="supported",
            source=_source_name("football_data_uk"),
        ),
        ClaimEvidence(
            metric="Last five league matches",
            count=(
                f"{last_five.get('points')} points; {last_five.get('gf')} goals for and "
                f"{last_five.get('ga')} against; "
                f"{_fmt(float(last_five.get('shot_share') or 0) * 100, 1)}% share of shots"
            ),
            sample="5 league matches",
            period="2026-27",
            status="supported",
            source=_source_name("football_data_uk"),
        ),
        ClaimEvidence(
            metric="Set plays and errors",
            count="Not measured",
            sample="No event feed for set-piece goals, errors or penalties",
            period="2026-27",
            status="cant_test",
            source=_source_name("api_football"),
            note="Corners and fouls are available; they are not a proxy for the claim.",
        ),
    ]
    return {
        "count": (
            f"{season.get('gf')} goals for and {season.get('ga')} against "
            f"in {season.get('played')} league matches"
        ),
        "status": "mixed",
        "status_reason": (
            "The goals are measured. The set-play and error claims cannot be tested "
            "with the current feed."
        ),
        "evidence": evidence,
    }


def _squad_claim(mission: dict[str, Any], transfers: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = mission.get("metrics") or {}
    recruitment = metrics.get("recruitment") or {}
    scorecard = metrics.get("scorecard") or {}
    selection = scorecard.get("selection") or {}
    morris = next(
        (
            row
            for row in transfers
            if str(row.get("player_name") or "").casefold() == "s. morris"
            and row.get("direction") == "out"
        ),
        None,
    )
    morris_date = str((morris or {}).get("date_effective") or "")[:10]
    morris_fee = (morris or {}).get("fee_estimate") or {}
    fee_text = "undisclosed"
    if morris_fee.get("fee_low_gbp") is not None:
        fee_text = (
            f"undisclosed; modelled £{int(morris_fee['fee_low_gbp']):,} to "
            f"£{int(morris_fee['fee_high_gbp']):,}"
        )
    evidence = [
        ClaimEvidence(
            metric="Arrivals and departures",
            count=(
                f"{recruitment.get('arrivals', 0)} in and {recruitment.get('departures', 0)} out; "
                f"{recruitment.get('permanent_in', 0)} permanent in, "
                f"{recruitment.get('permanent_out', 0)} permanent out, "
                f"{recruitment.get('loans_out', 0)} loans out"
            ),
            sample="Confirmed transfer register",
            period="2026-27",
            status="supported",
            source=_source_name("afc_news"),
        ),
        ClaimEvidence(
            metric="Arrival age",
            count=f"median {recruitment.get('median_age', '—')}",
            sample="Arrivals with a known birth date",
            period="2026-27",
            status="supported",
            source=_source_name("api_football"),
        ),
        ClaimEvidence(
            metric="Under-21 minutes",
            count=f"{_fmt(float(selection.get('u21_minutes_share') or 0) * 100, 0)}%",
            sample="League minutes",
            period="Cormack era",
            status="supported",
            source=_source_name("api_football"),
        ),
        ClaimEvidence(
            metric="Morris sale",
            count=f"{morris_date or '—'}; fee {fee_text}",
            sample="Confirmed transfer register",
            period="2025-26",
            status="mixed",
            source=_source_name("afc_news"),
            note="Fees are mostly undisclosed; the fee range is modelled, not audited.",
        ),
    ]
    return {
        "count": (
            f"{recruitment.get('arrivals', 0)} arrivals and {recruitment.get('departures', 0)} "
            "departures in 2026-27"
        ),
        "status": "mixed",
        "status_reason": (
            "The turnover is measured. The squad is not young: median arrival age "
            f"{recruitment.get('median_age', '—')} and Under-21 minutes "
            f"{_fmt(float(selection.get('u21_minutes_share') or 0) * 100, 0)}%. "
            "The goal-threat replacement effect cannot be tested with the current output data."
        ),
        "evidence": evidence,
    }


def _chairman_claim(
    mission: dict[str, Any],
    history_index: dict[str, Any],
    history_seasons: dict[str, dict[str, Any]] | None,
    benchmark: Benchmark,
) -> dict[str, Any]:
    metrics = mission.get("metrics") or {}
    scorecard = metrics.get("scorecard") or {}
    era_recruitment = scorecard.get("recruitment") or {}
    europe = sum(
        1
        for document in (history_seasons or {}).values()
        for entry in document.get("europe") or []
        if str(entry.get("stage_reached") or "") in {"Group stage", "League phase"}
    )
    honours = history_index.get("honours") or []
    cup = any(str(item.get("honour_id")) == "scottish-cup-2024-25" for item in honours)
    evidence = [
        ClaimEvidence(
            metric="Completed seasons",
            count=f"{scorecard.get('seasons', 0)} seasons",
            sample="Cormack era",
            period="2019-20 to date",
            status="supported",
            source=_source_name("wikipedia"),
        ),
        ClaimEvidence(
            metric="League range",
            count=(
                f"{scorecard.get('best_position')} to {scorecard.get('worst_position')}; "
                f"average {scorecard.get('average_position')}"
            ),
            sample="Completed league seasons",
            period="Cormack era",
            status="supported",
            source=_source_name("football_data_uk"),
        ),
        ClaimEvidence(
            metric="Major honours",
            count="1 Scottish Cup" if cup else f"{scorecard.get('honours_total', 0)}",
            sample="Cormack era",
            period="2019-20 to date",
            status="supported",
            source=_source_name("wikipedia"),
            note="The 2023-24 League Cup runners-up is a cup run, not an honour.",
        ),
        ClaimEvidence(
            metric="Manager spells",
            count=f"{scorecard.get('manager_count', 0)} people in charge",
            sample="Cormack era",
            period="2019-20 to date",
            status="supported",
            source=_source_name("wikipedia"),
        ),
        ClaimEvidence(
            metric="Arrivals and departures",
            count=(
                f"{era_recruitment.get('arrivals', 0)} in and "
                f"{era_recruitment.get('departures', 0)} out"
            ),
            sample="Confirmed transfer register",
            period="Cormack era",
            status="supported",
            source=_source_name("afc_news"),
        ),
        ClaimEvidence(
            metric="European campaigns",
            count=f"{europe}",
            sample="Season documents",
            period="Cormack era",
            status="supported",
            source=_source_name("wikipedia"),
        ),
    ]
    return {
        "count": (
            f"{scorecard.get('seasons', 0)} seasons; "
            f"{scorecard.get('best_position')}rd to "
            f"{scorecard.get('worst_position')}th; 1 major honour"
        ),
        "status": "supported",
        "status_reason": (
            "The record is measured. It cannot prove cause and effect, boardroom "
            "intent or that the trading model has made money."
        ),
        "evidence": evidence,
    }


def build_case_payload(
    *,
    season: str,
    generated_at: str,
    matches: pl.DataFrame,
    all_matches: pl.DataFrame,
    squad_data: dict[str, Any],
    transfers_data: dict[str, Any] | None,
    history_index: dict[str, Any] | None,
    history_season: dict[str, Any] | None,
    history_seasons: dict[str, dict[str, Any]] | None = None,
    availability: dict[str, Any] | None = None,
    appearances: pl.DataFrame | None = None,
    match_stats: pl.DataFrame | None = None,
    team_shapes: pl.DataFrame | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = config or themes_config()
    appearances = appearances if appearances is not None else load_player_appearances()
    match_stats = match_stats if match_stats is not None else load_player_match_stats()
    team_shapes = team_shapes if team_shapes is not None else load_team_shapes()
    transfers = (transfers_data or {}).get("transfers") or []
    history_index = history_index or {}
    availability_entries = {
        int(entry["player_id"]): entry
        for entry in (availability or {}).get("entries", [])
        if entry.get("player_id") is not None and entry.get("in_squad", True)
    }
    document = build_theme_document(
        appearances=appearances,
        match_stats=match_stats,
        team_shapes=team_shapes,
        matches=matches,
        squad_data=squad_data,
        transfers=transfers,
        history_index=history_index,
        history_season=history_season,
        season=season,
        generated_at=generated_at,
        config=policy,
        curated_notes=_curated_notes(),
        availability=availability_entries,
    )
    themes = {theme["theme_id"]: theme for theme in document.get("themes") or []}
    shape = themes.get("wing_back_tax") or {}
    cover = themes.get("cover_question") or {}
    balance = themes.get("leaky_boat") or {}
    mission = themes.get("mission_check") or {}
    benchmark = _benchmark(all_matches, season)
    builders = {
        "team_now": lambda: _team_now_claim(shape, balance, team_shapes),
        "defence": lambda: _defence_claim(shape, cover, availability_entries),
        "attack": lambda: _attack_claim(balance),
        "managers": lambda: {
            **_manager_claim(all_matches, history_index),
        },
        "squad": lambda: _squad_claim(mission, transfers),
        "chairman_record": lambda: _chairman_claim(
            mission, history_index, history_seasons, benchmark
        ),
    }
    claim_defs = sorted(policy.get("claims") or [], key=lambda item: int(item.get("order") or 99))
    claims = []
    for definition in claim_defs:
        claim_id = str(definition.get("id"))
        builder = builders.get(claim_id)
        if builder is None:
            claims.append(
                {
                    "id": claim_id,
                    "domain": str(definition.get("domain") or "matchday"),
                    "order": int(definition.get("order") or 99),
                    "title": str(definition.get("title") or claim_id),
                    "claim": str(definition.get("claim") or ""),
                    "count": "Unavailable",
                    "status": "cant_test",
                    "status_reason": "No builder is registered for this claim.",
                    "evidence": [
                        {
                            "metric": "Evidence",
                            "count": "Unavailable",
                            "sample": "—",
                            "period": season,
                            "status": "cant_test",
                            "source": "—",
                        }
                    ],
                    "better_data": str(definition.get("better_data") or ""),
                    "change_mind": str(definition.get("change_mind") or ""),
                    "links": definition.get("links") or [],
                }
            )
            continue
        payload = builder()
        claims.append(
            {
                "id": claim_id,
                "domain": str(definition.get("domain") or "matchday"),
                "order": int(definition.get("order") or 99),
                "title": str(definition.get("title") or claim_id),
                "claim": str(definition.get("claim") or ""),
                "count": payload["count"],
                "status": payload["status"],
                "status_reason": payload["status_reason"],
                "evidence": [
                    item.model_dump() if hasattr(item, "model_dump") else item
                    for item in payload["evidence"]
                ],
                "better_data": str(definition.get("better_data") or ""),
                "change_mind": str(definition.get("change_mind") or ""),
                "links": definition.get("links") or [],
            }
        )
    statuses = [claim["status"] for claim in claims]
    state = "unavailable" if not claims else "partial" if "cant_test" in statuses else "fresh"
    known = sum(
        1 for entry in availability_entries.values() if str(entry.get("status")) != "unknown"
    )
    unknown = len(availability_entries) - known
    missing = [
        "Official team news and injury return dates",
        "Set-piece goals, errors and per-match penalties",
        "Pressing, possession and transition events",
        "Mid-game shape",
        "Through balls and second balls",
        "Other clubs' transfer and wage models",
    ]
    coverage = CaseCoverage(
        status=state,
        season=season,
        availability_feed=f"{known} known / {unknown} unknown",
        historical_appearances="Local season files",
        missing=missing,
        note=(
            "The record is derived from local match, squad, history and transfer data. "
            "Missing layers are labelled; they are never zero."
        ),
    )
    case_config = policy.get("case") or {}
    owner_view = OwnerView(
        label=str(case_config.get("owner_label") or "The owner's view"),
        text=str(case_config.get("owner_view") or ""),
        attribution=str(case_config.get("owner_attribution") or "Patrick Mockridge"),
    )
    chairman_frame = ChairmanFrame(
        label=str(case_config.get("chairman_label") or "The chairman's frame"),
        text=str(case_config.get("chairman_frame") or ""),
        source=str(case_config.get("chairman_source") or ""),
        note=str(case_config.get("chairman_note") or ""),
    )
    return CaseDocument(
        generated_at=generated_at,
        season=season,
        club_id=str(aberdeen_config()["club_id"]),
        state=state,
        stale_reason=None,
        served_generated_at=generated_at,
        title="Data analysis",
        owner_view=owner_view,
        chairman_frame=chairman_frame,
        thesis=str(
            case_config.get("thesis")
            or "The team on the pitch is the visible edge of a seven-year trading model."
        ),
        claims=[Claim(**item) for item in claims],
        benchmark=benchmark,
        coverage=coverage,
        sources=[CaseSource(**item) for item in _source_ids()],
        notes=(
            "The owner's view is attributed opinion. Statuses are the record's "
            "answer: supported, mixed, not supported or can't test yet."
        ),
    ).model_dump()


def _curated_notes() -> list[dict[str, Any]]:
    from fitba.settings import transfer_gaps

    gaps = (transfer_gaps() or {}).get("gaps", []) or []
    notes = []
    for gap in gaps:
        if str(gap.get("player_key") or "") != "api:player:68534":
            continue
        reason = str(gap.get("reason") or "").strip()
        if reason:
            notes.append(
                {
                    "player_id": 68534,
                    "name": gap.get("player_name") or "K. Tobers",
                    "note": reason,
                    "basis": "curated",
                    "source": "reference/transfer_gaps.yaml",
                }
            )
    return notes


def _manager_claim(all_matches: pl.DataFrame, history_index: dict[str, Any]) -> dict[str, Any]:
    evidence, count = _manager_evidence(all_matches, history_index, "")
    return {
        "count": count,
        "status": "mixed",
        "status_reason": (
            "The manager records are measured. 'Steadying' and 'lower variance' "
            "are readings: 18 matches, two squads and no agreed measure of consistency."
        ),
        "evidence": evidence,
    }


__all__ = ["CaseDocument", "build_case_payload", "case_schema"]


def fallback_case_payload(
    previous: dict[str, Any] | None,
    *,
    generated_at: str,
    season: str,
    reason: str,
) -> dict[str, Any]:
    """Carry the last good case forward, or publish an explicit unavailable case."""

    if previous:
        carried = {
            **previous,
            "generated_at": generated_at,
            "season": season,
            "state": "stale",
            "stale_reason": reason,
            "served_generated_at": previous.get("generated_at"),
        }
        try:
            return CaseDocument(**carried).model_dump()
        except Exception:  # noqa: BLE001 - fall through to the minimal document
            pass

    config = themes_config()
    claim_defs = sorted(config.get("claims") or [], key=lambda item: int(item.get("order") or 99))
    claims = [
        {
            "id": str(item.get("id")),
            "domain": str(item.get("domain") or "matchday"),
            "order": int(item.get("order") or 99),
            "title": str(item.get("title") or item.get("id")),
            "claim": str(item.get("claim") or ""),
            "count": "Unavailable",
            "status": "cant_test",
            "status_reason": reason,
            "evidence": [
                {
                    "metric": "Evidence",
                    "count": "Unavailable",
                    "sample": "—",
                    "period": season,
                    "status": "cant_test",
                    "source": "—",
                }
            ],
            "better_data": str(item.get("better_data") or ""),
            "change_mind": str(item.get("change_mind") or ""),
            "links": item.get("links") or [],
        }
        for item in claim_defs
    ]
    case_config = config.get("case") or {}
    return CaseDocument(
        generated_at=generated_at,
        season=season,
        club_id=str(aberdeen_config()["club_id"]),
        state="unavailable",
        stale_reason=reason,
        served_generated_at=generated_at,
        title="Data analysis",
        owner_view=OwnerView(
            label=str(case_config.get("owner_label") or "The owner's view"),
            text=str(case_config.get("owner_view") or ""),
            attribution=str(case_config.get("owner_attribution") or "Patrick Mockridge"),
        ),
        chairman_frame=ChairmanFrame(
            label=str(case_config.get("chairman_label") or "The chairman's frame"),
            text=str(case_config.get("chairman_frame") or ""),
            source=str(case_config.get("chairman_source") or ""),
            note=str(case_config.get("chairman_note") or ""),
        ),
        thesis=str(case_config.get("thesis") or ""),
        claims=[Claim(**item) for item in claims],
        benchmark=Benchmark(
            title="How the record compares",
            note="Unavailable for this publish.",
            columns=[
                "Club",
                "Seasons",
                "Best finish",
                "Worst finish",
                "Median points",
                "Current position",
            ],
            rows=[],
        ),
        coverage=CaseCoverage(
            status="unavailable",
            season=season,
            availability_feed="unavailable",
            historical_appearances="unavailable",
            missing=["all claim data"],
            note=reason,
        ),
        sources=[CaseSource(**item) for item in _source_ids()],
        notes="Data analysis is unavailable for this publish.",
    ).model_dump()
