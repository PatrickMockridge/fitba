#!/usr/bin/env python3
"""CI guard for the scouting documents and the static league pages.

The data checks are structural and numerical: every enabled league has a
document, percentiles are bounded, cohort bases are declared, layer-0 entries
come from the verified availability ledger, and no contract or fee field leaks
into the record. The page checks (``--pages``) need the static export and are
run with the web contract check.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "web" / "data" / "generated"
SCOUTING = GENERATED / "scouting"
HUB = SCOUTING / "aberdeen.json"
COVERAGE = SCOUTING / "coverage.json"
POOL_DIR = SCOUTING / "pool"
SEARCH = SCOUTING / "search-index.json"
AVAILABILITY = GENERATED / "availability" / "aberdeen.json"
LEAGUES = ROOT / "config" / "scouting" / "leagues.yaml"
OUT = ROOT / "web" / "out"

STATUSES = {"ok", "partial", "no_player_stats", "error", "stale", "unknown"}
FAMILY_STATUS = {"below", "at", "above", "insufficient"}
READINGS = {"structural", "cover", "hold", "none", "insufficient"}
COHORT_BASES = {"role_family", "provider_group", "insufficient"}
AVAILABILITY_STATUSES = {"out", "doubtful", "suspended", "returned", "available", "unknown"}
FORBIDDEN_KEYS = {
    "contract",
    "contract_end",
    "contract_expiry",
    "wage",
    "wages",
    "fee",
    "release_clause",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk(value: Any, path: str = "") -> list[tuple[str, str, Any]]:
    found: list[tuple[str, str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.extend(_walk(child, f"{path}.{key}" if path else str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_walk(child, f"{path}[{index}]"))
    else:
        found.append((path, path.rsplit(".", 1)[-1], value))
    return found


def _check_number(errors: list[str], value: Any, low: float, high: float, label: str) -> None:
    if value is None:
        return
    if not isinstance(value, (int, float)):
        errors.append(f"{label}: not a number: {value!r}")
        return
    if value < low or value > high:
        errors.append(f"{label}: {value} outside [{low}, {high}]")


def check_data() -> list[str]:
    errors: list[str] = []
    config = yaml.safe_load(LEAGUES.read_text(encoding="utf-8")) or {}
    leagues = [item for item in config.get("pool") or [] if item.get("enabled")]
    ids = [str(item.get("id")) for item in leagues]
    slugs = [str(item.get("slug")) for item in leagues]
    provider_ids = [
        int((item.get("provider") or {}).get("api_football_id"))
        for item in leagues
        if (item.get("provider") or {}).get("api_football_id") is not None
    ]
    if len(set(ids)) != len(ids):
        errors.append("duplicate canonical league ids")
    if len(set(slugs)) != len(slugs):
        errors.append("duplicate league slugs")
    if len(set(provider_ids)) != len(provider_ids):
        errors.append("duplicate provider league ids")
    if len(provider_ids) != len(leagues):
        errors.append("an enabled league is missing a provider id")

    if not HUB.exists() or not COVERAGE.exists():
        return ["missing scouting hub or coverage document"]
    hub = _load(HUB)
    coverage = _load(COVERAGE)
    if hub.get("season") != coverage.get("season"):
        errors.append("hub and coverage season disagree")
    if hub.get("state") not in {"full", "stale", "empty"}:
        errors.append(f"invalid hub state {hub.get('state')!r}")

    availability = _load(AVAILABILITY) if AVAILABILITY.exists() else {}
    ledger_status = {
        int(entry["player_id"]): entry.get("status")
        for entry in availability.get("entries") or []
        if entry.get("player_id") is not None
    }
    for item in hub.get("layer_zero") or []:
        player_id = item.get("player_id")
        status = item.get("status")
        if status not in AVAILABILITY_STATUSES:
            errors.append(f"layer0 {player_id}: invalid status {status!r}")
        if player_id is not None and ledger_status.get(int(player_id)) != status:
            errors.append(f"layer0 {player_id}: status does not match the availability ledger")
        if status != "unknown" and not item.get("source_url"):
            errors.append(f"layer0 {player_id}: non-unknown status without a source URL")
        if status != "unknown" and not item.get("verified_at"):
            errors.append(f"layer0 {player_id}: non-unknown status without verified_at")

    board = hub.get("board") or {}
    families = board.get("families") or []
    if hub.get("state") == "full" and len(families) != 10:
        errors.append(f"board has {len(families)} families, expected 10")
    for family in families:
        if family.get("status") not in FAMILY_STATUS:
            errors.append(f"{family.get('family')}: invalid status")
        if family.get("reading") not in READINGS:
            errors.append(f"{family.get('family')}: invalid reading")
        cohort = family.get("cohort") or {}
        _check_number(
            errors, family.get("rating_percentile"), 0, 100, f"{family.get('family')} percentile"
        )
        _check_number(errors, cohort.get("n"), 0, 1_000_000, f"{family.get('family')} cohort n")
        _check_number(
            errors, family.get("average_rating"), 0, 10, f"{family.get('family')} average"
        )
        if cohort.get("basis") not in COHORT_BASES:
            errors.append(f"{family.get('family')}: invalid cohort basis")
        if family.get("status") != "insufficient" and (cohort.get("n") or 0) < 1:
            errors.append(f"{family.get('family')}: ranked without a cohort")

    league_rows = coverage.get("leagues") or []
    if len(league_rows) != len(leagues):
        errors.append(f"coverage has {len(league_rows)} leagues, config has {len(leagues)}")
    expected_slugs = set(slugs)
    actual_slugs = {str(item.get("slug")) for item in league_rows}
    if expected_slugs - actual_slugs:
        errors.append(f"coverage missing leagues: {sorted(expected_slugs - actual_slugs)}")
    for item in league_rows:
        if item.get("status") not in STATUSES:
            errors.append(f"{item.get('slug')}: invalid coverage status")
        _check_number(errors, item.get("role_coverage"), 0, 1, f"{item.get('slug')} role coverage")
        _check_number(errors, item.get("players"), 0, 1_000_000, f"{item.get('slug')} players")
        if item.get("searchable") and (item.get("rated") or 0) < 25:
            errors.append(f"{item.get('slug')}: searchable with fewer than 25 rated players")

    pool_files = sorted(POOL_DIR.glob("*.json")) if POOL_DIR.exists() else []
    if {path.stem for path in pool_files} != expected_slugs:
        errors.append("pool files do not match the enabled league slugs")
    for path in pool_files:
        document = _load(path)
        if document.get("state") not in {"full", "no_player_stats", "stale"}:
            errors.append(f"{path.name}: invalid state")
        for player in document.get("players") or []:
            label = f"{path.name}:{player.get('player_id')}"
            if (player.get("minutes") or 0) < 450:
                errors.append(f"{label}: below the ranked minutes threshold")
            _check_number(errors, player.get("rating"), 0, 10, f"{label} rating")
            _check_number(errors, player.get("rating_percentile"), 0, 100, f"{label} percentile")
            _check_number(errors, player.get("role_family_share"), 0, 1, f"{label} role share")
            if player.get("cohort_basis") not in COHORT_BASES:
                errors.append(f"{label}: invalid cohort basis")
            for feature, value in (player.get("archetypes") or {}).items():
                _check_number(errors, value.get("score"), 0, 100, f"{label} {feature} score")
                _check_number(errors, value.get("coverage"), 0, 1, f"{label} {feature} coverage")

    search = _load(SEARCH) if SEARCH.exists() else {}
    if not search:
        errors.append("missing scouting search-index.json")
    else:
        search_players = search.get("players") or []
        if int(search.get("count") or 0) != len(search_players):
            errors.append("search count does not match its player rows")
        expected_rows = sum(len(_load(path).get("players") or []) for path in pool_files)
        if len(search_players) != expected_rows:
            errors.append(f"search has {len(search_players)} rows, pool files have {expected_rows}")
        for player in search_players:
            label = f"search:{player.get('i')}:{player.get('l')}"
            if player.get("l") not in expected_slugs:
                errors.append(f"{label}: unknown league slug")
            _check_number(errors, player.get("rt"), 0, 10, f"{label} rating")
            _check_number(errors, player.get("p"), 0, 100, f"{label} percentile")
            _check_number(errors, player.get("m"), 450, 100_000, f"{label} minutes")
        for document in [hub, coverage, search]:
            for location, key, _ in _walk(document):
                if key in FORBIDDEN_KEYS:
                    errors.append(f"{location}: forbidden contract/fee field")
    return errors


def check_pages() -> list[str]:
    errors: list[str] = []
    if not OUT.exists():
        return [f"missing static export {OUT}"]
    search_page = OUT / "scouting" / "search" / "index.html"
    if not search_page.exists():
        errors.append("missing /scouting/search/ page")
    else:
        html = search_page.read_text(encoding="utf-8")
        if len(re.findall(r"<h1[ >]", html)) != 1:
            errors.append("scouting search: expected exactly one H1")
        if not re.search(r"<caption", html):
            errors.append("scouting search: missing table caption")
        for header in (
            "Player",
            "Club",
            "League",
            "Nationality",
            "Role",
            "Pct",
            "Adj Pct",
            "Value index",
            "Profile",
        ):
            if header not in html:
                errors.append(f"scouting search: missing column {header!r}")
        if not re.search(r'href="[^"]*scouting/"', html):
            errors.append("scouting search: missing link back to the scouting board")
    coverage = _load(COVERAGE) if COVERAGE.exists() else {}
    required = [
        "Player",
        "Club",
        "Role",
        "Mins",
        "Rating",
        "Pct",
        "Adj Pct",
        "Value index",
        "G+A/90",
        "Duels won %",
    ]
    for league in coverage.get("leagues") or []:
        slug = str(league.get("slug"))
        page = OUT / "scouting" / slug / "index.html"
        if not page.exists():
            errors.append(f"missing page for {slug}")
            continue
        html = page.read_text(encoding="utf-8")
        if len(re.findall(r"<h1[ >]", html)) != 1:
            errors.append(f"{slug}: expected exactly one H1")
        if league.get("name") and league["name"] not in html:
            errors.append(f"{slug}: league name is not visible")
        if not re.search(r'href="[^"]*scouting/"', html):
            errors.append(f"{slug}: missing link back to the scouting board")
        pool_path = POOL_DIR / f"{slug}.json"
        pool_document = _load(pool_path) if pool_path.exists() else {}
        if not pool_document.get("players"):
            if 'data-contract="scouting.league-empty"' not in html:
                errors.append(f"{slug}: missing the explicit empty state")
            if "No player statistics" not in html and "No ranked player" not in html:
                errors.append(f"{slug}: missing the empty-state explanation")
            continue
        if not re.search(r"<caption", html):
            errors.append(f"{slug}: missing table caption")
        for header in required:
            if header not in html:
                errors.append(f"{slug}: missing column {header!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", action="store_true", help="Also check the static league pages")
    args = parser.parse_args()
    errors = check_data()
    if args.pages:
        errors.extend(check_pages())
    if errors:
        print("Scouting check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Scouting check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
