"""Player-page result document.

The page is a projection of one typed document, not a set of React branches
over the squad payload. The document has a fixed panel order and one home for
each fact. See docs/player-page-spec.md.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from fitba.analytics.player_facts import (
    club_totals,
    league_totals,
    missing_output_competitions,
)
from fitba.normalize.teams import TeamRegistry

DataStatus = Literal["available", "partial", "unavailable", "not_applicable"]
WarningCode = Literal[
    "COVERAGE_PARTIAL",
    "SOURCE_MISSING",
    "NO_ROLE_EVIDENCE",
    "POSITION_UNKNOWN",
    "OTHER_RECORDS_ONLY",
    "EXCLUDED_FROM_SQUAD",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PageWarning(StrictModel):
    code: WarningCode
    message: str
    field: str | None = None


class SourceRef(StrictModel):
    id: str
    url: str | None = None
    verified_at: str | None = None


class KnownValue(StrictModel):
    status: Literal["known", "unknown", "conflict"]
    value: str | None = None
    reason: str | None = None
    source: SourceRef | None = None


class IdentityBlock(StrictModel):
    player_id: int
    name: str
    full_name: str
    href: str
    season: str
    role: str | None
    age: int | None
    nationality: str | None
    number: int | None
    status: str
    injured: bool
    loan: dict[str, Any] | None
    side: str | None
    preferred_foot: KnownValue


class PanelBase(StrictModel):
    eyebrow: str
    title: str
    status: DataStatus
    badge: str | None = None
    data: dict[str, Any] | list[dict[str, Any]] | None
    note: str | None = None
    warnings: list[PageWarning] = Field(default_factory=list)


class RoseAxis(StrictModel):
    metric: str
    value: float | None
    percentile: float | None
    cohort_n: int


class RoseFigure(StrictModel):
    id: Literal["overall", "position"]
    label: str
    status: Literal["available", "partial", "unavailable"]
    axes: list[RoseAxis]


class RoseBlock(StrictModel):
    status: Literal["available", "partial", "unavailable"]
    reason: str | None
    league: str
    league_label: str
    minutes: int
    min_minutes: int
    cohort_min_minutes: int
    basis: Literal["role_family", "provider_group", "insufficient"]
    cohort_n: int
    figures: list[RoseFigure]
    season_used: str | None = None
    cohort_season: str | None = None
    fallback: bool = False
    fallback_reason: str | None = None
    fallback_note: str | None = None


class ProfileSummary(StrictModel):
    season: str
    league: str
    league_label: str
    role_label: str | None
    scope: str = "all_competitions"
    output_coverage: str = "unavailable"
    output_missing_competitions: list[str] = []
    minutes: int
    minutes_season: str
    appearances: int | None
    rating: float | None
    league_minutes: int | None = None
    league_appearances: int | None = None
    league_rating: float | None = None
    rating_percentile: float | None
    league_rating_percentile: float | None = None
    cohort_basis: str | None
    cohort_n: int | None
    rose_season: str | None
    rose_fallback: bool


class AvailabilityBlock(StrictModel):
    status: str
    reason: str | None
    reason_category: str | None
    expected_return: str | None
    confidence: str
    source_id: str | None
    source_title: str | None
    source_url: str | None
    verified_at: str | None
    note: str | None
    in_squad: bool | None


class RecentMatch(StrictModel):
    fixture_id: int | str
    date: str
    competition: str
    opponent: str
    venue: Literal["H", "A"] | None
    score_for: int | None
    score_against: int | None
    result: Literal["W", "D", "L"] | None
    minutes: int | None
    rating: float | None
    goals: int | None
    assists: int | None


class ProfilePanel(PanelBase):
    id: Literal["profile"] = "profile"
    data: dict[str, Any] | None


class AvailabilityPanel(PanelBase):
    id: Literal["availability"] = "availability"


class RecentMatchesPanel(PanelBase):
    id: Literal["recent_matches"] = "recent_matches"


class PositionPanel(PanelBase):
    id: Literal["position"] = "position"


class PlayingTimePanel(PanelBase):
    id: Literal["playing_time"] = "playing_time"


class PerformancePanel(PanelBase):
    id: Literal["performance"] = "performance"


class RecordsPanel(PanelBase):
    id: Literal["records"] = "records"


PanelId = Literal[
    "profile",
    "position",
    "playing_time",
    "performance",
    "availability",
    "recent_matches",
    "records",
]

PANEL_ORDER: list[PanelId] = [
    "profile",
    "position",
    "playing_time",
    "performance",
    "availability",
    "recent_matches",
    "records",
]


class PlayerPageDocument(StrictModel):
    schema_version: Literal["1.2.0"] = "1.2.0"
    player_id: int
    season: str
    generated_at: str
    out_of_squad: bool = False
    out_of_squad_reason: str | None = None
    identity: IdentityBlock
    panel_order: list[PanelId] = Field(default_factory=lambda: list(PANEL_ORDER))
    panels: dict[
        str,
        ProfilePanel
        | AvailabilityPanel
        | PositionPanel
        | PlayingTimePanel
        | PerformancePanel
        | RecentMatchesPanel
        | RecordsPanel,
    ]
    warnings: list[PageWarning] = Field(default_factory=list)


def build_recent_matches(
    appearance_rows: list[dict[str, Any]],
    stat_rows: list[dict[str, Any]],
    match_rows: list[dict[str, Any]],
    *,
    player_id: int,
    team_id: int = 252,
    season: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Latest competitive current-season rows for one Aberdeen player."""
    season_start = season.split("-")[0]
    team_names = TeamRegistry()
    stats = {
        str(row.get("fixture_id")): row
        for row in stat_rows
        if str(row.get("player_id")) == str(player_id) and str(row.get("team_id")) == str(team_id)
    }
    matches: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in match_rows:
        if str(row.get("season")) != season or row.get("home_goals") is None:
            continue
        date = str(row.get("date") or "")[:10]
        home = str(row.get("home_team_name") or "").casefold()
        away = str(row.get("away_team_name") or "").casefold()
        if home and away:
            matches[(date, home, away)] = row
    rows: list[dict[str, Any]] = []
    for row in appearance_rows:
        if str(row.get("player_id")) != str(player_id):
            continue
        if str(row.get("team_id")) != str(team_id):
            continue
        if str(row.get("season")) != season_start:
            continue
        if int(row.get("minutes") or 0) <= 0:
            continue
        competition = str(row.get("competition") or "")
        if "friendly" in competition.lower():
            continue
        rows.append(row)
    rows.sort(key=lambda item: str(item.get("date") or ""), reverse=True)
    out: list[dict[str, Any]] = []
    for row in rows[:limit]:
        fixture_key = str(row.get("fixture_id"))
        stat = stats.get(fixture_key) or {}
        date = str(row.get("date") or "")[:10]
        competition = str(row.get("competition") or "")
        opponent = team_names.display_name(str(row.get("opponent") or "Unknown"))
        fixture = matches.get((date, "aberdeen", opponent.casefold())) or matches.get(
            (date, opponent.casefold(), "aberdeen")
        )
        venue: Literal["H", "A"] | None = None
        score_for = score_against = None
        result: Literal["W", "D", "L"] | None = None
        if fixture is not None:
            home = str(fixture.get("home_team_name") or "").casefold() == "aberdeen"
            home_goals = fixture.get("home_goals")
            away_goals = fixture.get("away_goals")
            if home_goals is not None and away_goals is not None:
                venue = "H" if home else "A"
                score_for = int(home_goals) if home else int(away_goals)
                score_against = int(away_goals) if home else int(home_goals)
                if score_for > score_against:
                    result = "W"
                elif score_for < score_against:
                    result = "L"
                else:
                    result = "D"
        out.append(
            {
                "fixture_id": fixture_key,
                "date": date,
                "competition": competition,
                "opponent": opponent,
                "venue": venue,
                "score_for": score_for,
                "score_against": score_against,
                "result": result,
                "minutes": row.get("minutes"),
                "rating": stat.get("rating"),
                "goals": stat.get("goals"),
                "assists": stat.get("assists"),
            }
        )
    return out


def _known_foot(player: dict[str, Any]) -> KnownValue:
    attribute = (player.get("attributes") or {}).get("preferred_foot") or {}
    status = str(attribute.get("status") or "unknown")
    if status == "known" and attribute.get("value"):
        source = attribute.get("source") or {}
        return KnownValue(
            status="known",
            value=str(attribute["value"]),
            source=SourceRef(
                id=str(source.get("id") or "unknown"),
                url=source.get("url"),
                verified_at=source.get("verified_at"),
            ),
        )
    return KnownValue(
        status="conflict" if status == "conflict" else "unknown",
        value=None,
        reason=attribute.get("unknown_reason"),
    )


def _group(player: dict[str, Any]) -> str:
    family = (player.get("display_role") or {}).get("family")
    if family == "goalkeeper":
        return "goalkeeper"
    if family in {"centre_back", "full_back", "wing_back", "defensive_midfield"}:
        return "defensive"
    if family in {"central_midfield", "attacking_midfield"}:
        return "midfield"
    if family in {"wide_midfield", "wide_forward"}:
        return "wide"
    if family == "centre_forward":
        return "forward"
    return "unknown"


def _tiles(player: dict[str, Any], group: str) -> list[dict[str, Any]]:
    totals = player.get("totals") or {}
    position = player.get("position_totals") or {}
    if group == "goalkeeper":
        return [
            {
                "key": "conceded",
                "label": "Conceded",
                "value": position.get("conceded_on_pitch"),
                "note": "on pitch",
            },
            {
                "key": "clean_sheets",
                "label": "Clean sheets",
                "value": position.get("clean_sheets"),
                "note": "60+ mins",
            },
            {"key": "saves", "label": "Saves", "value": totals.get("saves"), "note": "provider"},
            {
                "key": "own_goals",
                "label": "Own goals",
                "value": position.get("own_goals"),
                "note": "event",
            },
        ]
    if group == "defensive":
        return [
            {
                "key": "conceded",
                "label": "Conceded",
                "value": position.get("conceded_on_pitch"),
                "note": "on pitch",
            },
            {
                "key": "clean_sheets",
                "label": "Clean sheets",
                "value": position.get("clean_sheets"),
                "note": "60+ mins",
            },
            {
                "key": "tackles",
                "label": "Tackles",
                "value": totals.get("tackles"),
                "note": "provider",
            },
            {
                "key": "own_goals",
                "label": "Own goals",
                "value": position.get("own_goals"),
                "note": "event",
            },
        ]
    if group == "midfield":
        return [
            {"key": "goals", "label": "Goals", "value": totals.get("goals"), "note": "provider"},
            {
                "key": "assists",
                "label": "Assists",
                "value": totals.get("assists"),
                "note": "provider",
            },
            {
                "key": "passes_key",
                "label": "Key passes",
                "value": totals.get("passes_key"),
                "note": "provider",
            },
            {
                "key": "tackles",
                "label": "Tackles",
                "value": totals.get("tackles"),
                "note": "provider",
            },
        ]
    if group == "wide":
        return [
            {"key": "goals", "label": "Goals", "value": totals.get("goals"), "note": "provider"},
            {
                "key": "assists",
                "label": "Assists",
                "value": totals.get("assists"),
                "note": "provider",
            },
            {
                "key": "shots_total",
                "label": "Shots",
                "value": totals.get("shots_total"),
                "note": "provider",
            },
            {
                "key": "dribbles_success",
                "label": "Dribbles won",
                "value": totals.get("dribbles_success"),
                "note": "provider",
            },
        ]
    if group == "forward":
        return [
            {"key": "goals", "label": "Goals", "value": totals.get("goals"), "note": "provider"},
            {
                "key": "assists",
                "label": "Assists",
                "value": totals.get("assists"),
                "note": "provider",
            },
            {
                "key": "shots_total",
                "label": "Shots",
                "value": totals.get("shots_total"),
                "note": "provider",
            },
            {
                "key": "shots_on",
                "label": "On target",
                "value": totals.get("shots_on"),
                "note": "provider",
            },
        ]
    return []


def _detail_columns(group: str) -> list[dict[str, Any]]:
    columns = {
        # Tiles already carry the headline metric; detail columns add the
        # remaining role-relevant fields only.
        "goalkeeper": [
            ("penalty_saved", "Pen. saved"),
            ("pass_accuracy", "Pass acc."),
        ],
        "defensive": [
            ("blocks", "Blocks"),
            ("interceptions", "Interceptions"),
            ("duels_won", "Duels won"),
            ("fouls_committed", "Fouls"),
            ("pass_accuracy", "Pass acc."),
        ],
        "midfield": [
            ("interceptions", "Interceptions"),
            ("duels_won", "Duels won"),
            ("fouls_committed", "Fouls"),
            ("pass_accuracy", "Pass acc."),
        ],
        "wide": [
            ("passes_key", "Key passes"),
            ("penalty_scored", "Penalties"),
        ],
        "forward": [
            ("passes_key", "Key passes"),
            ("penalty_scored", "Penalties"),
        ],
        "unknown": [],
    }
    return [
        {
            "key": key,
            "label": label,
            **({"format": "percent"} if key == "pass_accuracy" else {}),
        }
        for key, label in columns[group]
    ]


def _status(value: str | None, *, not_applicable: bool = False) -> DataStatus:
    if not_applicable:
        return "not_applicable"
    if value == "available":
        return "available"
    if value == "partial":
        return "partial"
    return "unavailable"


def _unavailable_rose(season: str, reason: str = "not_built") -> dict[str, Any]:
    return {
        "status": "unavailable",
        "reason": reason,
        "league": "sco:premiership",
        "league_label": "Scottish Premiership",
        "minutes": 0,
        "min_minutes": 180,
        "cohort_min_minutes": 450,
        "basis": "insufficient",
        "cohort_n": 0,
        "season_used": season,
        "cohort_season": season,
        "fallback": False,
        "fallback_reason": None,
        "fallback_note": None,
        "figures": [
            {"id": "overall", "label": "Overall profile", "status": "unavailable", "axes": []},
            {"id": "position", "label": "Position profile", "status": "unavailable", "axes": []},
        ],
    }


def _summary_values(player: dict[str, Any], rose: dict[str, Any] | None) -> dict[str, Any]:
    club = club_totals(player) or {}
    league = league_totals(player) or {}
    playing = player.get("playing_time") or {}
    display = player.get("display_role") or {}
    role = player.get("role") or {}
    minutes = int(playing.get("minutes") or club.get("minutes") or 0)
    missing = missing_output_competitions(player)
    return {
        "season": str(player.get("season") or ""),
        "league": "sco:premiership",
        "league_label": "Scottish Premiership",
        "role_label": display.get("label") or role.get("label"),
        "scope": "all_competitions",
        "output_coverage": "partial" if missing else "available" if club else "unavailable",
        "output_missing_competitions": missing,
        "minutes": minutes,
        "minutes_season": str(player.get("season") or ""),
        "appearances": club.get("appearances"),
        "rating": club.get("rating"),
        "league_minutes": league.get("minutes"),
        "league_appearances": league.get("appearances"),
        "league_rating": league.get("rating"),
        "rating_percentile": None,
        "league_rating_percentile": None,
        "cohort_basis": None,
        "cohort_n": None,
        "rose_season": (rose or {}).get("season_used"),
        "rose_fallback": bool((rose or {}).get("fallback")),
    }


def build_player_page(
    player: dict[str, Any],
    *,
    season: str,
    generated_at: str,
    rose: dict[str, Any] | None = None,
    rose_catalogue: dict[str, Any] | None = None,
    availability: dict[str, Any] | None = None,
    recent_matches: list[dict[str, Any]] | None = None,
    rating_percentile: float | None = None,
    cohort_basis: str | None = None,
    cohort_n: int | None = None,
    current_squad: bool | None = None,
    out_of_squad: bool = False,
    out_of_squad_reason: str | None = None,
) -> dict[str, Any]:
    """Project one squad player into the player-page result document."""
    role = player.get("role") or {}
    career = player.get("career_role") or {}
    display = player.get("display_role") or {}
    playing = player.get("playing_time") or {}
    group = _group(player)
    warnings: list[PageWarning] = []

    position_status: DataStatus
    if role.get("status") in {"observed", "partial"}:
        position_status = "available"
    elif career.get("status") in {"observed", "low_evidence", "mixed"}:
        position_status = "partial"
    else:
        position_status = "unavailable"
        warnings.append(
            PageWarning(
                code="POSITION_UNKNOWN",
                message="No starting-XI role evidence was found.",
                field="position",
            )
        )

    if playing.get("coverage") == "partial":
        warnings.append(
            PageWarning(
                code="COVERAGE_PARTIAL",
                message="Some appearances have no lineup or event coverage.",
                field="playing_time",
            )
        )
    if player.get("stats_coverage") == "partial":
        warnings.append(
            PageWarning(
                code="COVERAGE_PARTIAL",
                message="Some provider stat fields are missing.",
                field="performance",
            )
        )
    if out_of_squad:
        warnings.append(
            PageWarning(
                code="EXCLUDED_FROM_SQUAD",
                message=(
                    "Not on the official AFC men's team list; retained so existing "
                    "links resolve and excluded from squad counts."
                ),
                field="profile",
            )
        )
    if (player.get("attributes") or {}).get("preferred_foot", {}).get("status") == "known":
        source = player["attributes"]["preferred_foot"].get("source") or {}
        if not source.get("url"):
            warnings.append(
                PageWarning(
                    code="SOURCE_MISSING",
                    message="Preferred-foot value has no source URL.",
                    field="identity.preferred_foot",
                )
            )

    club_history = []
    seen_history: set[tuple[Any, ...]] = set()
    for row in (player.get("stats") or []) + (player.get("other_stats") or []):
        key = (
            row.get("season"),
            row.get("team_name"),
            row.get("competition"),
            row.get("appearances"),
            row.get("starts"),
            row.get("minutes"),
        )
        if key in seen_history:
            continue
        if not any(row.get(field) for field in ("appearances", "starts", "minutes")):
            continue
        seen_history.add(key)
        club_history.append(
            {
                "season": row.get("season"),
                "team_name": row.get("team_name"),
                "competition": row.get("competition"),
                "appearances": row.get("appearances"),
                "starts": row.get("starts"),
                "minutes": row.get("minutes"),
            }
        )

    if position_status == "unavailable" and club_history:
        position_status = "partial"

    current = bool(player.get("status") == "squad") if current_squad is None else current_squad
    rose_block = RoseBlock.model_validate(rose or _unavailable_rose(season))
    summary_values = _summary_values(player, rose_block.model_dump())
    summary_values.update(
        {
            "season": season,
            "minutes_season": season,
            "rating_percentile": None,
            "league_rating_percentile": rating_percentile,
            "cohort_basis": cohort_basis,
            "cohort_n": cohort_n,
        }
    )
    summary = ProfileSummary.model_validate(summary_values)
    availability_block = (
        AvailabilityBlock(
            status=str(availability.get("status") or "unknown"),
            reason=availability.get("reason"),
            reason_category=availability.get("reason_category"),
            expected_return=availability.get("expected_return"),
            confidence=str(availability.get("confidence") or "unknown"),
            source_id=availability.get("source_id"),
            source_title=availability.get("source_title"),
            source_url=availability.get("source_url"),
            verified_at=availability.get("verified_at"),
            note=availability.get("note"),
            in_squad=availability.get("in_squad"),
        )
        if availability is not None
        else None
    )
    match_rows = [RecentMatch.model_validate(row) for row in (recent_matches or [])]

    identity = IdentityBlock(
        player_id=int(player["player_id"]),
        name=str(player.get("name") or ""),
        full_name=str(player.get("full_name") or player.get("name") or ""),
        href=str(player.get("href") or f"/players/{player['player_id']}/"),
        season=season,
        role=display.get("label") or role.get("primary") or player.get("position"),
        age=player.get("age"),
        nationality=player.get("nationality"),
        number=player.get("number"),
        status=str(player.get("status") or "squad"),
        injured=bool(player.get("injured")),
        loan=player.get("loan"),
        side=display.get("side"),
        preferred_foot=_known_foot(player),
    )

    profile_panel = ProfilePanel(
        eyebrow="Profile",
        title="Overall and position profile",
        status=rose_block.status,
        badge=rose_block.basis if rose_block.status != "unavailable" else rose_block.reason,
        data={
            "tier": "extended",
            "current_squad": current,
            "summary": summary.model_dump(),
            "rose": rose_block.model_dump(),
            "rose_catalogue": rose_catalogue or {},
        },
        note=(
            f"League-only rates; cohort {rose_block.basis.replace('_', ' ')} "
            f"n={rose_block.cohort_n}; percentiles 0-100, higher is better."
            + (f" {rose_block.fallback_note}" if rose_block.fallback_note else "")
        ),
        warnings=[],
    )

    availability_status: DataStatus = (
        "available"
        if availability_block is not None and availability_block.status != "unknown"
        else "partial"
        if availability_block is not None
        else "not_applicable"
    )
    availability_panel = AvailabilityPanel(
        eyebrow="Availability",
        title="Availability and team news",
        status=availability_status,
        badge=availability_block.status if availability_block is not None else None,
        data=(
            {"availability": availability_block.model_dump()}
            if availability_block is not None
            else None
        ),
        note=(
            availability_block.note
            if availability_block is not None
            else "Current-squad team news is not applicable to this loan profile."
        ),
        warnings=[],
    )

    recent_status: DataStatus = (
        "available" if match_rows else "unavailable" if current else "not_applicable"
    )
    recent_panel = RecentMatchesPanel(
        eyebrow="Recent matches",
        title="Recent match log",
        status=recent_status,
        badge=f"{len(match_rows)} rows" if match_rows else None,
        data=[row.model_dump() for row in match_rows],
        note=(
            "Current season, competitive matches only; latest 10. Missing "
            "provider values are shown as a dash, not zero."
            if current
            else "Recent Aberdeen matches are not applicable to this loan profile."
        ),
        warnings=[],
    )

    position_panel = PositionPanel(
        eyebrow="Position",
        title="How this position was inferred",
        status=position_status,
        badge=None,
        data={
            "display_role": display,
            "role": role,
            "career_role": career,
            "history_status": (
                "observed"
                if career.get("status") == "observed"
                else "partial"
                if career.get("history")
                else "no_role_evidence"
            ),
            "club_history": club_history,
            "tactical_notes": player.get("tactical_notes") or [],
        },
        note=(
            "No starting-XI role history is available for this player."
            if position_status == "unavailable"
            else None
        ),
        warnings=[warning for warning in warnings if warning.field == "position"],
    )

    playing_status = _status(
        playing.get("coverage"),
        not_applicable=playing.get("coverage") == "not_applicable",
    )
    playing_panel = PlayingTimePanel(
        eyebrow="Playing time",
        title="Playing time",
        status=playing_status,
        badge=playing.get("coverage"),
        data={"playing_time": playing},
        note=playing.get("note"),
        warnings=[warning for warning in warnings if warning.field == "playing_time"],
    )

    performance_status = _status(player.get("stats_coverage"))
    performance_panel = PerformancePanel(
        eyebrow="Performance",
        title="Performance",
        status=performance_status,
        badge=player.get("stats_coverage"),
        data={
            "tiles": _tiles(player, group),
            "provider_columns": [
                {"key": "competition", "label": "Competition"},
                {"key": "team_name", "label": "Team"},
                {"key": "goals", "label": "G"},
                {"key": "assists", "label": "A"},
                {"key": "yellow_cards", "label": "YC"},
                {"key": "red_cards", "label": "RC"},
                {"key": "rating", "label": "Rating", "format": "decimal"},
            ],
            "detail_columns": _detail_columns(group),
            "stats": player.get("stats") or [],
            "position_stats": player.get("position_stats") or [],
            "stats_coverage": player.get("stats_coverage"),
            "stats_note": player.get("stats_note"),
            "position_stats_coverage": player.get("position_stats_coverage"),
            "position_stats_note": player.get("position_stats_note"),
        },
        note=player.get("stats_note"),
        warnings=[warning for warning in warnings if warning.field == "performance"],
    )

    records = player.get("other_stats") or []
    records_panel = RecordsPanel(
        eyebrow="Records",
        title="Records outside the main scope",
        status="available" if records else "not_applicable",
        badge="Not loan-club output" if records else None,
        data=records,
        note=None,
        warnings=(
            [
                PageWarning(
                    code="OTHER_RECORDS_ONLY",
                    message="These rows are outside the main club or loan scope.",
                    field="records",
                )
            ]
            if records
            else []
        ),
    )

    document = PlayerPageDocument(
        player_id=int(player["player_id"]),
        season=season,
        generated_at=generated_at,
        out_of_squad=out_of_squad,
        out_of_squad_reason=out_of_squad_reason,
        identity=identity,
        panels={
            "profile": profile_panel,
            "availability": availability_panel,
            "position": position_panel,
            "playing_time": playing_panel,
            "performance": performance_panel,
            "recent_matches": recent_panel,
            "records": records_panel,
        },
        warnings=warnings,
    )
    return document.model_dump(mode="json")


def player_page_schema() -> dict[str, Any]:
    return PlayerPageDocument.model_json_schema()


__all__ = [
    "PlayerPageDocument",
    "build_player_page",
    "build_recent_matches",
    "player_page_schema",
]
