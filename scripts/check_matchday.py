#!/usr/bin/env python3
"""CI guard for the upcoming-matchday document.

The document must be internally consistent, use the mapped formations and
never claim team news. Missing lineups are a coverage state, not a failure.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from fitba.normalize.roles import role_for_grid
from fitba.publish.matchday import MatchdayDocument, matchday_schema
from fitba.settings import roles

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "web" / "data" / "generated"
DOCUMENT = GENERATED / "matchday" / "upcoming.json"
SCHEMA = ROOT / "contracts" / "matchday.schema.json"
MANIFEST = GENERATED / "manifest.json"
SQUAD = GENERATED / "squad" / "aberdeen.json"
TABLES = GENERATED / "tables"
MAX_FILE_BYTES = 2_000_000

CONFIDENCE = {"high", "medium", "low", "unknown"}
APPROACHES = {"attack", "balanced", "sit_deep_counter", "unknown"}
STATES = {"fresh", "stale", "no_fixture", "unavailable"}
FORBIDDEN_HOSTS = (
    "transfermarkt.",
    "fotmob.",
    "sofascore.",
    "fbref.",
    "bbc.",
)
CERTAINTY = ("confirmed xi", "will start", "guaranteed")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        output: list[str] = []
        for key, item in value.items():
            output.append(str(key))
            output.extend(_strings(item))
        return output
    if isinstance(value, list):
        output = []
        for item in value:
            output.extend(_strings(item))
        return output
    return []


def _check_lineup(
    team: str,
    block: dict[str, Any] | None,
    *,
    squad: dict[int, dict[str, Any]],
    roles_config: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> None:
    if not block:
        warnings.append(f"{team}: no predicted-lineup block")
        return
    status = block.get("status")
    players = block.get("players") or []
    contenders = block.get("contenders") or []
    filled = [player for player in players if player.get("player_id") is not None]
    ids = [player.get("player_id") for player in filled]
    if len(ids) != len(set(ids)):
        errors.append(f"{team}: duplicate player ids in the XI")
    if status == "available" and len(filled) != 11:
        errors.append(f"{team}: available XI has {len(filled)} players, not 11")
    if status == "unavailable" and filled:
        errors.append(f"{team}: unavailable XI contains players")
    formation = block.get("formation")
    if status in {"available", "partial"}:
        if not formation:
            errors.append(f"{team}: lineup has no formation")
        elif formation not in (roles_config.get("formations") or {}):
            errors.append(f"{team}: formation {formation} is not mapped")
        else:
            for player in filled:
                grid = player.get("grid")
                role_code = player.get("role_code")
                expected = role_for_grid(roles_config, formation, grid)
                if expected and role_code and expected != role_code:
                    errors.append(
                        f"{team}: {player.get('name')} is {role_code} at {grid}, "
                        f"expected {expected}"
                    )
        goalkeepers = [player for player in filled if player.get("role_code") == "GK"]
        if len(goalkeepers) != 1:
            errors.append(f"{team}: expected one goalkeeper, found {len(goalkeepers)}")
    for player in players + contenders:
        confidence = player.get("confidence")
        if confidence not in CONFIDENCE:
            errors.append(f"{team}: invalid confidence {confidence!r}")
    if status == "available":
        if not 4 <= len(contenders) <= 6:
            errors.append(f"{team}: expected 4-6 contenders, found {len(contenders)}")
        if set(ids) & {player.get("player_id") for player in contenders}:
            errors.append(f"{team}: a contender is also in the XI")
    if status in {"available", "partial"}:
        if block.get("formation_confidence") not in CONFIDENCE:
            errors.append(f"{team}: invalid formation confidence")
        if block.get("team_confidence") not in CONFIDENCE:
            errors.append(f"{team}: invalid team confidence")
    selection = block.get("selection") or {}
    weights = selection.get("weights") or {}
    if weights:
        total = sum(float(value) for value in weights.values())
        if abs(total - 1.0) > 0.01:
            errors.append(f"{team}: selection weights sum to {total:.2f}, not 1.0")
        form_rating = float(weights.get("form", 0)) + float(weights.get("recent_rating", 0))
        if form_rating < 0.30:
            errors.append(f"{team}: form + recent rating weight {form_rating:.2f} is below 0.30")
    for player in players + contenders:
        rating = player.get("recent_rating")
        if rating is not None and not 0 <= float(rating) <= 10:
            errors.append(f"{team}: recent rating {rating} is outside 0-10")
        coverage_value = player.get("rating_coverage")
        if coverage_value is not None and coverage_value not in {
            "available",
            "partial",
            "unavailable",
        }:
            errors.append(f"{team}: invalid rating coverage {coverage_value!r}")
    coverage = block.get("coverage") or {}
    value = coverage.get("lineup_coverage")
    if value is not None and not 0 <= float(value) <= 1:
        errors.append(f"{team}: lineup coverage {value} is outside 0-1")
    if team == "aberdeen":
        for player in filled:
            player_id = player.get("player_id")
            squad_player = squad.get(int(player_id)) if player_id is not None else None
            if squad_player is None:
                errors.append(f"aberdeen: player {player_id} is not in the current squad")
                continue
            if squad_player.get("status") == "loan_out":
                errors.append(f"aberdeen: loan-out player {player_id} is in the XI")
            if squad_player.get("injured"):
                errors.append(f"aberdeen: provider-injured player {player_id} is in the XI")
        if len(filled) == 11 and not block.get("disclaimer"):
            errors.append("aberdeen: missing predicted-XI disclaimer")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    if not DOCUMENT.exists():
        print(f"missing {DOCUMENT}; run `uv run fitba publish`")
        return 1
    document = _load(DOCUMENT)
    try:
        MatchdayDocument(**document)
    except ValidationError as error:
        errors.append(f"document does not validate: {error}")
    if SCHEMA.exists():
        if _load(SCHEMA) != matchday_schema():
            errors.append(f"{SCHEMA} is stale; regenerate it from the Pydantic model")
    else:
        errors.append(f"missing {SCHEMA}")

    state = document.get("state")
    if state not in STATES:
        errors.append(f"invalid state {state!r}")
    fixture = document.get("fixture")
    if state == "no_fixture":
        if fixture is not None:
            errors.append("no_fixture state has a fixture")
    elif fixture is None:
        errors.append(f"{state} state has no fixture")
    if state == "stale" and not document.get("stale_reason"):
        errors.append("stale state has no stale_reason")
    if fixture:
        fixture_date = str(fixture.get("date") or "")[:10]
        if fixture_date and fixture_date < date.today().isoformat():
            warnings.append(
                f"fixture {fixture_date} has passed; the next publish should replace it"
            )
        if fixture.get("venue") not in {"H", "A", "N"}:
            errors.append("fixture venue must be H or A")
        next_fixtures = document.get("next_fixtures") or []
        if len(next_fixtures) > 5:
            errors.append("next_fixtures must contain at most five rows")
        fixture_date = str((document.get("fixture") or {}).get("date") or "")
        dates = [str(row.get("date") or "") for row in next_fixtures]
        if dates != sorted(dates):
            errors.append("next_fixtures must be date-sorted")
        if len(set(dates)) != len(dates):
            errors.append("next_fixtures must not repeat a date")
        if any(date <= fixture_date for date in dates):
            errors.append("next_fixtures must be after the featured fixture")
        for row in next_fixtures:
            if row.get("venue") not in {"H", "A", "N"}:
                errors.append("next_fixtures has an invalid venue")
            if row.get("competition_id") == "sco:other:friendlies-clubs":
                errors.append("next_fixtures must exclude friendlies")

    for team, form in (document.get("form_guide") or {}).items():
        matches = form.get("matches") or []
        if len(matches) > 5:
            errors.append(f"{team}: form guide has {len(matches)} matches")
        if len(form.get("form") or "") != len(matches):
            errors.append(f"{team}: form string does not match the match count")
        if any(match.get("result") not in {"W", "D", "L"} for match in matches):
            errors.append(f"{team}: invalid result in the form guide")
        if any(int(match.get("points") or 0) not in {0, 1, 3} for match in matches):
            errors.append(f"{team}: invalid points in the form guide")

    for team, pair in (document.get("styles") or {}).items():
        lean = pair.get("lean") or {}
        if lean.get("approach") not in APPROACHES:
            errors.append(f"{team}: invalid approach {lean.get('approach')!r}")
        if lean.get("confidence") not in CONFIDENCE:
            errors.append(f"{team}: invalid style confidence")
        index = lean.get("approach_index")
        if index is not None and not 0 <= float(index) <= 100:
            errors.append(f"{team}: approach index {index} is outside 0-100")
        if lean.get("approach") != "unknown" and not lean.get("evidence"):
            errors.append(f"{team}: non-unknown lean has no evidence")
        for profile_name in ("overall", "venue"):
            profile = pair.get(profile_name) or {}
            if profile.get("possession_for_pm") is not None:
                errors.append(f"{team}: possession is presented as known")
            if not profile.get("possession_unknown_reason"):
                errors.append(f"{team}: missing possession-unknown reason")

    squad_doc = _load(SQUAD) if SQUAD.exists() else {}
    squad = {
        int(player["player_id"]): player
        for player in squad_doc.get("players", [])
        if player.get("player_id") is not None
    }
    predicted = document.get("predicted_lineups") or {}
    for team in ("aberdeen", "opponent"):
        _check_lineup(
            team,
            predicted.get(team),
            squad=squad,
            roles_config=roles(),
            errors=errors,
            warnings=warnings,
        )

    season = document.get("season")
    for team, row in (document.get("strength") or {}).items():
        if row.get("status") != "available":
            continue
        competition_id = row.get("competition_id")
        if not competition_id:
            errors.append(f"{team}: available strength row has no competition")
            continue
        slug = competition_id.split(":", 1)[-1]
        table_path = TABLES / f"{slug}-{season}.json"
        if not table_path.exists():
            errors.append(f"{team}: table {table_path.name} is missing")
            continue
        table = _load(table_path)
        table_row = next(
            (item for item in table.get("rows") or [] if item.get("team_id") == row.get("team_id")),
            None,
        )
        if table_row is None:
            errors.append(f"{team}: strength row is not in {table_path.name}")
            continue
        for key in ("position", "played", "points", "gf", "ga", "gd"):
            if row.get(key) != table_row.get(key):
                errors.append(
                    f"{team}: strength {key} {row.get(key)} != table {table_row.get(key)}"
                )
        if "rows" in row:
            errors.append(f"{team}: strength embeds a full table")

    for text in _strings(document):
        lowered = text.casefold()
        for host in FORBIDDEN_HOSTS:
            if host in lowered:
                errors.append(f"forbidden source host {host} in the document")
        for phrase in CERTAINTY:
            if phrase in lowered:
                errors.append(f"certainty language {phrase!r} in the document")
        if "official team news" in lowered and "not official team news" not in lowered:
            errors.append("official-team-news claim in the document")

    if DOCUMENT.stat().st_size > MAX_FILE_BYTES:
        errors.append(f"{DOCUMENT} exceeds the {MAX_FILE_BYTES} byte cap")
    if MANIFEST.exists():
        manifest = _load(MANIFEST)
        files = {row.get("path"): row for row in manifest.get("files") or []}
        info = files.get("matchday/upcoming.json")
        if info is None:
            errors.append("manifest missing matchday/upcoming.json")
        else:
            digest = "sha256:" + hashlib.sha256(DOCUMENT.read_bytes()).hexdigest()
            if info.get("checksum") != digest:
                errors.append("manifest checksum does not match matchday/upcoming.json")
        marts = {mart.get("id") for mart in manifest.get("marts") or []}
        if "matchday.upcoming" not in marts:
            errors.append("manifest missing the matchday.upcoming mart")
        if "matchday" not in (manifest.get("coverage") or {}):
            errors.append("manifest coverage missing the matchday block")

    for error in errors:
        print(f"  - {error}")
    for warning in warnings:
        print(f"  ! {warning}")
    if errors:
        print(f"Matchday check failed ({len(errors)} error(s))")
        return 1
    fixture = document.get("fixture") or {}
    print(
        "Matchday check passed "
        f"({document.get('state')}, {fixture.get('opponent_name') or 'no fixture'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
