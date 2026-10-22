"""Player-page result document.

The page is a projection of one typed document, not a set of React branches
over the squad payload. The document has a fixed panel order and one home for
each fact. See docs/player-page-spec.md.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DataStatus = Literal["available", "partial", "unavailable", "not_applicable"]
WarningCode = Literal[
    "COVERAGE_PARTIAL",
    "SOURCE_MISSING",
    "NO_ROLE_EVIDENCE",
    "POSITION_UNKNOWN",
    "OTHER_RECORDS_ONLY",
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


class PositionPanel(PanelBase):
    id: Literal["position"] = "position"


class PlayingTimePanel(PanelBase):
    id: Literal["playing_time"] = "playing_time"


class PerformancePanel(PanelBase):
    id: Literal["performance"] = "performance"


class RecordsPanel(PanelBase):
    id: Literal["records"] = "records"


class PlayerPageDocument(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    player_id: int
    season: str
    generated_at: str
    identity: IdentityBlock
    panel_order: list[Literal["position", "playing_time", "performance", "records"]] = Field(
        default_factory=lambda: ["position", "playing_time", "performance", "records"]
    )
    panels: dict[str, PositionPanel | PlayingTimePanel | PerformancePanel | RecordsPanel]
    warnings: list[PageWarning] = Field(default_factory=list)


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


def build_player_page(
    player: dict[str, Any],
    *,
    season: str,
    generated_at: str,
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
        identity=identity,
        panels={
            "position": position_panel,
            "playing_time": playing_panel,
            "performance": performance_panel,
            "records": records_panel,
        },
        warnings=warnings,
    )
    return document.model_dump(mode="json")


def player_page_schema() -> dict[str, Any]:
    return PlayerPageDocument.model_json_schema()


__all__ = ["PlayerPageDocument", "build_player_page", "player_page_schema"]
