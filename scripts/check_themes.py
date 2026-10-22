#!/usr/bin/env python3
"""CI guard for the medium and long-term themes document.

The guard checks the typed document, the evidence arithmetic and the editorial
policy: no player-level ratings, no blame or club-intent claims, no invented
availability, and no unmeasured channel claims.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from fitba.publish.themes import ThemesDocument, themes_schema

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "web" / "data" / "generated"
DOCUMENT = GENERATED / "themes" / "aberdeen.json"
SCHEMA = ROOT / "contracts" / "themes.schema.json"
MANIFEST = GENERATED / "manifest.json"
CLUB = GENERATED / "clubs" / "aberdeen.json"
SEARCH = GENERATED / "search-index.json"
MAX_FILE_BYTES = 2_000_000

FAMILIES = {"GK", "CB", "FB/WB", "MID", "AM/WM", "W", "ST"}
CATEGORIES = {"starter", "rotation", "fringe", "injured", "unavailable"}
HORIZONS = {"season", "mission"}
STATUSES = {"available", "partial", "unavailable"}
CONFIDENCE = {"high", "medium", "low", "unknown"}
BASES = {"measured", "inferred", "curated", "mixed", "unknown"}
FORBIDDEN_HOSTS = ("transfermarkt.", "fotmob.", "sofascore.", "fbref.", "bbc.")
CERTAINTY = ("confirmed xi", "will start", "guaranteed", "definitely")
BLAME = (
    "to blame",
    "at fault",
    "liability",
    "must sign",
    "should sign",
    "doesn't trust",
    "does not trust",
    "manager wants",
    "board wants",
    "not good enough",
)
AVAILABILITY = (
    "ruled out",
    "out for",
    "fit to play",
    "doubtful",
    "injury crisis",
    "returns from injury",
)
TACTICAL = ("doubling up", "overload", "half-space", "channel", "crosses")


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


def _narrative_strings(document: dict[str, Any]) -> list[str]:
    output: list[str] = []
    for theme in document.get("themes") or []:
        for key in ("title", "fan_question", "headline", "read", "method"):
            value = theme.get(key)
            if isinstance(value, str):
                output.append(value)
        for evidence in theme.get("evidence") or []:
            for key in ("label", "note"):
                if isinstance(evidence.get(key), str):
                    output.append(evidence[key])
        output.extend(str(item) for item in theme.get("caveats") or [])
    return output


def _check_family(theme: dict[str, Any], errors: list[str]) -> None:
    metrics = theme.get("metrics") or {}
    groups = metrics.get("groups") or []
    seen = {group.get("family") for group in groups}
    if theme.get("status") == "available" and not seen >= FAMILIES:
        errors.append(f"family_balance: missing groups {sorted(FAMILIES - seen)}")
    for group in groups:
        rating = group.get("provider_rating")
        if rating is not None and not 0 < float(rating) <= 10:
            errors.append(f"family_balance: {group.get('family')} rating {rating} out of range")
        for key in ("starts", "starter_minutes", "players", "matches"):
            if int(group.get(key) or 0) < 0:
                errors.append(f"family_balance: {group.get('family')} {key} is negative")
        sample = group.get("rating_sample") or {}
        if int(sample.get("minutes") or 0) < 0:
            errors.append(f"family_balance: {group.get('family')} sample minutes negative")


def _check_shape(theme: dict[str, Any], errors: list[str]) -> None:
    metrics = theme.get("metrics") or {}
    groups = {row.get("group"): row for row in metrics.get("groups") or []}
    coverage = metrics.get("coverage") or {}
    total = int(coverage.get("fixtures_total") or 0)
    counts = sum(int(row.get("matches") or 0) for row in groups.values())
    if total and counts != total:
        errors.append(f"wing_back_tax: shape group matches {counts} != fixtures {total}")
    if "unknown" not in groups and coverage.get("unknown_shapes"):
        errors.append("wing_back_tax: unknown shapes are not reported as a group")
    for group, row in groups.items():
        for key in ("wb_starts_pm", "wf_starts_pm", "named_bench_wf_pm"):
            value = row.get(key)
            if value is not None and float(value) < 0:
                errors.append(f"wing_back_tax: {group} {key} is negative")


def _check_cover(theme: dict[str, Any], errors: list[str]) -> None:
    metrics = theme.get("metrics") or {}
    groups = metrics.get("groups") or []
    if not groups:
        errors.append("cover_question: no depth groups")
    for group in groups:
        top_share = group.get("top_share")
        if top_share is not None and not 0 <= float(top_share) <= 1:
            errors.append(f"cover_question: {group.get('group')} top_share out of range")
        for item in group.get("items") or []:
            if item.get("category") not in CATEGORIES:
                errors.append(
                    f"cover_question: {item.get('name')} has invalid category "
                    f"{item.get('category')!r}"
                )
            if item.get("category") == "loan_out":
                errors.append(f"cover_question: loan-out player {item.get('name')} is in depth")


def _check_balance(theme: dict[str, Any], club: dict[str, Any], errors: list[str]) -> None:
    metrics = theme.get("metrics") or {}
    season = metrics.get("season") or {}
    summary = club.get("summary") or {}
    for key in ("gf", "ga"):
        if season.get(key) != summary.get(key):
            errors.append(f"leaky_boat: season {key} {season.get(key)} != club {summary.get(key)}")
    mix = metrics.get("goals_by_family") or {}
    total = int(mix.get("total") or 0)
    parts = sum(int(mix.get(key) or 0) for key in ("attack", "midfield", "defence"))
    if total != parts:
        errors.append(f"leaky_boat: goal mix parts {parts} != total {total}")
    share = mix.get("attack_share")
    if share is not None and not 0 <= float(share) <= 1:
        errors.append(f"leaky_boat: attack share {share} out of range")


def _check_mission(theme: dict[str, Any], errors: list[str]) -> None:
    metrics = theme.get("metrics") or {}
    if theme.get("status") == "available":
        pillars = metrics.get("pillars") or []
        if len(pillars) != 5:
            errors.append(f"mission_check: expected 5 pillars, found {len(pillars)}")
        coverage = metrics.get("coverage") or {}
        if coverage.get("ratings_used") is not False:
            errors.append("mission_check: ratings_used must be false")
        if not any(link.get("href") == "/history/" for link in theme.get("links") or []):
            errors.append("mission_check: missing /history/ link")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    if not DOCUMENT.exists():
        print(f"missing {DOCUMENT}; run `uv run fitba publish`")
        return 1
    document = _load(DOCUMENT)
    try:
        ThemesDocument(**document)
    except ValidationError as error:
        errors.append(f"document does not validate: {error}")
    if SCHEMA.exists():
        if _load(SCHEMA) != themes_schema():
            errors.append(f"{SCHEMA} is stale; regenerate it from the Pydantic model")
    else:
        errors.append(f"missing {SCHEMA}")

    if document.get("club_id") != "sco:aberdeen":
        errors.append("club_id must be sco:aberdeen")
    if document.get("state") not in {"fresh", "partial", "unavailable", "stale"}:
        errors.append(f"invalid state {document.get('state')!r}")
    scope = document.get("scope") or {}
    if scope.get("season_weight") != 80 or scope.get("mission_weight") != 20:
        errors.append("scope weights must be 80/20")
    themes = document.get("themes") or []
    if len(themes) != 5:
        errors.append(f"expected 5 themes, found {len(themes)}")
    if sum(1 for theme in themes if theme.get("horizon") == "season") != 4:
        errors.append("expected 4 season themes")
    if sum(1 for theme in themes if theme.get("horizon") == "mission") != 1:
        errors.append("expected 1 mission theme")
    ids = [theme.get("theme_id") for theme in themes]
    if len(ids) != len(set(ids)):
        errors.append("duplicate theme ids")
    if sorted(theme.get("order") for theme in themes) != [1, 2, 3, 4, 5]:
        errors.append("theme order must be 1-5")
    statuses = []
    for theme in themes:
        theme_id = theme.get("theme_id")
        status = theme.get("status")
        statuses.append(status)
        if theme.get("horizon") not in HORIZONS:
            errors.append(f"{theme_id}: invalid horizon")
        if status not in STATUSES:
            errors.append(f"{theme_id}: invalid status")
        if theme.get("basis") not in BASES:
            errors.append(f"{theme_id}: invalid basis")
        if theme.get("read_basis") not in {"inferred", "curated", "unknown"}:
            errors.append(f"{theme_id}: invalid read basis")
        if theme.get("confidence") not in CONFIDENCE:
            errors.append(f"{theme_id}: invalid confidence")
        if status == "available":
            for key in ("headline", "read", "fan_question", "title"):
                if not theme.get(key):
                    errors.append(f"{theme_id}: missing {key}")
            if not theme.get("evidence"):
                errors.append(f"{theme_id}: no evidence")
        for evidence in theme.get("evidence") or []:
            if evidence.get("basis") not in BASES:
                errors.append(f"{theme_id}: invalid evidence basis")
        for player in theme.get("players") or []:
            if "rating" in player:
                errors.append(f"{theme_id}: player-level rating is not allowed")
        if theme_id == "family_balance":
            _check_family(theme, errors)
        elif theme_id == "wing_back_tax":
            _check_shape(theme, errors)
        elif theme_id == "cover_question":
            _check_cover(theme, errors)
        elif theme_id == "leaky_boat":
            _check_balance(theme, _load(CLUB) if CLUB.exists() else {}, errors)
        elif theme_id == "mission_check":
            _check_mission(theme, errors)
    if statuses and all(status == "available" for status in statuses):
        if document.get("state") != "fresh":
            errors.append("all themes available but state is not fresh")
    elif (
        statuses
        and any(status == "available" for status in statuses)
        and document.get("state") not in {"partial", "stale"}
    ):
        errors.append("some themes available but state is not partial/stale")

    for text in _strings(document):
        lowered = text.casefold()
        for host in FORBIDDEN_HOSTS:
            if host in lowered:
                errors.append(f"forbidden source host {host}")
    for text in _narrative_strings(document):
        lowered = text.casefold()
        for phrase in CERTAINTY:
            if phrase in lowered:
                errors.append(f"certainty language {phrase!r}")
        for phrase in BLAME:
            if phrase in lowered:
                errors.append(f"blame or club-intent language {phrase!r}")
        for phrase in AVAILABILITY:
            if phrase in lowered and "curated" not in lowered:
                errors.append(f"availability claim {phrase!r}")
        for phrase in TACTICAL:
            if phrase in lowered and not any(
                allowed in lowered for allowed in ("no channel", "cannot be measured", "unknown")
            ):
                errors.append(f"unmeasured tactical claim {phrase!r}")
        if "fitba rating" in lowered and "not a fitba rating" not in lowered:
            errors.append("fitba-rating claim")

    coverage = document.get("coverage") or {}
    if coverage.get("provider_ratings") not in {
        "Premiership starters",
        "Premiership only",
        "unavailable",
    }:
        errors.append(f"unexpected provider rating scope {coverage.get('provider_ratings')!r}")
    if not isinstance(coverage.get("availability_feed"), dict):
        errors.append("availability_feed must be a coverage object")
    if coverage.get("channel_data") is not False:
        errors.append("channel_data must be false")
    if coverage.get("historical_ratings") is not False:
        errors.append("historical_ratings must be false")

    if DOCUMENT.stat().st_size > MAX_FILE_BYTES:
        errors.append(f"{DOCUMENT} exceeds the {MAX_FILE_BYTES} byte cap")
    if MANIFEST.exists():
        manifest = _load(MANIFEST)
        files = {row.get("path"): row for row in manifest.get("files") or []}
        info = files.get("themes/aberdeen.json")
        if info is None:
            errors.append("manifest missing themes/aberdeen.json")
        else:
            digest = "sha256:" + hashlib.sha256(DOCUMENT.read_bytes()).hexdigest()
            if info.get("checksum") != digest:
                errors.append("manifest checksum does not match themes/aberdeen.json")
        marts = {mart.get("id") for mart in manifest.get("marts") or []}
        if "themes.sco:aberdeen" not in marts:
            errors.append("manifest missing themes.sco:aberdeen mart")
        if "themes" not in (manifest.get("coverage") or {}):
            errors.append("manifest coverage missing themes")
    if SEARCH.exists():
        search = _load(SEARCH)
        if not any(entry.get("href") == "/themes/" for entry in search):
            errors.append("search index missing /themes/")
        if not any(entry.get("type") == "theme" for entry in search):
            errors.append("search index missing theme entries")

    for error in errors:
        print(f"  - {error}")
    for warning in warnings:
        print(f"  ! {warning}")
    if errors:
        print(f"Themes check failed ({len(errors)} error(s))")
        return 1
    season_count = sum(1 for theme in themes if theme.get("horizon") == "season")
    mission_count = sum(1 for theme in themes if theme.get("horizon") == "mission")
    print(
        "Themes check passed "
        f"({len(themes)} themes, {season_count} season, {mission_count} mission)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
