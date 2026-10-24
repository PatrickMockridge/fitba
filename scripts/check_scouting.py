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
COHORT_BASES = {"role_family", "provider_group", "insufficient", "former_player_only"}
EUROPE_STATUSES = {"qualified", "below_threshold", "none", "unknown"}
CLUB_STATUSES = {
    "stats",
    "transferred",
    "loan",
    "free_agent",
    "retired",
    "unknown",
    "former_player",
}
CLUB_SOURCES = {
    "transfer_feed",
    "stats_snapshot",
    "former_register",
    "current_season_stats",
    "transfer_history",
    "latest_season",
    "register_destination",
    "curated_override",
}
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
    for archetype in hub.get("archetypes") or []:
        leaders = archetype.get("leaders") or []
        if len(leaders) > 5:
            errors.append(f"{archetype.get('id')}: {len(leaders)} leaders, expected at most 5")
    attackers = hub.get("attackers") or {}
    for key in ("assist_bias", "goal_bias"):
        leaders = (attackers.get(key) or {}).get("leaders") or []
        if len(leaders) > 8:
            errors.append(f"attackers.{key}: {len(leaders)} leaders, expected at most 8")
    if len(attackers.get("goal_scoring") or []) > 12:
        errors.append("attackers.goal_scoring: more than 12 rows")
    if len((hub.get("team_lens") or {}).get("leaders") or []) > 12:
        errors.append("team_lens: more than 12 leaders")

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
    if {path.stem for path in pool_files} - {"former"} != expected_slugs:
        errors.append("pool files do not match the enabled league slugs")
    for path in pool_files:
        document = _load(path)
        if document.get("state") not in {"full", "no_player_stats", "stale"}:
            errors.append(f"{path.name}: invalid state")
        rose_meta = document.get("rose_meta") or {}
        if not rose_meta.get("catalogue"):
            errors.append(f"{path.name}: missing rose catalogue")
        _check_number(errors, rose_meta.get("min_petals"), 1, 20, f"{path.name} min petals")
        for player in document.get("players") or []:
            label = f"{path.name}:{player.get('player_id')}"
            if path.stem != "former" and (player.get("minutes") or 0) < 450:
                errors.append(f"{label}: below the ranked minutes threshold")
            _check_number(errors, player.get("rating"), 0, 10, f"{label} rating")
            _check_number(errors, player.get("rating_percentile"), 0, 100, f"{label} percentile")
            _check_number(errors, player.get("role_family_share"), 0, 1, f"{label} role share")
            _check_number(errors, player.get("scouting_priority"), 0, 130, f"{label} priority")
            _check_number(errors, player.get("age_multiplier"), 0, 2, f"{label} age multiplier")
            _check_number(
                errors, player.get("europe_multiplier"), 0, 2, f"{label} Europe multiplier"
            )
            _check_number(
                errors,
                player.get("european_league_phase_minutes"),
                0,
                100_000,
                f"{label} Europe minutes",
            )
            _check_number(
                errors,
                player.get("european_league_phase_appearances"),
                0,
                1_000,
                f"{label} Europe appearances",
            )
            if player.get("european_status") not in EUROPE_STATUSES:
                errors.append(f"{label}: invalid European status")
            if player.get("current_club_status") not in CLUB_STATUSES:
                errors.append(f"{label}: invalid current-club status")
            if player.get("current_club_source") not in CLUB_SOURCES:
                errors.append(f"{label}: invalid current-club source")
            if not player.get("club") or not player.get("stats_club"):
                errors.append(f"{label}: missing current or stats club")
            if player.get("cohort_basis") not in COHORT_BASES:
                errors.append(f"{label}: invalid cohort basis")
            for feature, value in (player.get("archetypes") or {}).items():
                _check_number(errors, value.get("score"), 0, 100, f"{label} {feature} score")
                _check_number(errors, value.get("coverage"), 0, 1, f"{label} {feature} coverage")
            _check_number(errors, player.get("team_rank"), 1, 1000, f"{label} team rank")
            _check_number(errors, player.get("team_points"), 0, 1000, f"{label} team points")
            _check_number(errors, player.get("team_played"), 0, 1000, f"{label} team played")
            _check_number(errors, player.get("team_ppg"), 0, 10, f"{label} team ppg")
            _check_number(errors, player.get("team_count"), 1, 1000, f"{label} team count")
            _check_number(
                errors,
                player.get("team_points_percentile"),
                0,
                100,
                f"{label} team points percentile",
            )
            _check_number(errors, player.get("team_lift"), -100, 100, f"{label} team lift")
            if player.get("team_context_status") not in {"available", "unknown", "unavailable"}:
                errors.append(f"{label}: invalid team context status")
            rose = player.get("rose") or {}
            if not rose:
                if path.stem != "former":
                    errors.append(f"{label}: missing rose profile")
                continue
            if rose.get("status") not in {"available", "partial", "unavailable"}:
                errors.append(f"{label}: invalid rose status")
            if rose.get("basis") not in COHORT_BASES:
                errors.append(f"{label}: invalid rose basis")
            figures = rose.get("figures") or []
            if [figure.get("id") for figure in figures] != ["overall", "position"]:
                errors.append(f"{label}: rose figures are not overall, position")
            for figure in figures:
                for axis in figure.get("axes") or []:
                    _check_number(
                        errors,
                        axis.get("percentile"),
                        0,
                        100,
                        f"{label} {figure.get('id')} {axis.get('metric')} percentile",
                    )
                    _check_number(
                        errors,
                        axis.get("cohort_n"),
                        0,
                        100_000,
                        f"{label} {figure.get('id')} {axis.get('metric')} cohort n",
                    )
                    if axis.get("value") is not None and not isinstance(
                        axis.get("value"), (int, float)
                    ):
                        errors.append(f"{label}: rose axis value is not a number")

    search = _load(SEARCH) if SEARCH.exists() else {}
    if not search:
        errors.append("missing scouting search-index.json")
    else:
        search_players = search.get("players") or []
        profile_order = search.get("profile_order") or []
        if int(search.get("count") or 0) != len(search_players):
            errors.append("search count does not match its player rows")
        expected_rows = sum(len(_load(path).get("players") or []) for path in pool_files)
        if len(search_players) != expected_rows:
            errors.append(f"search has {len(search_players)} rows, pool files have {expected_rows}")
        for player in search_players:
            label = f"search:{player.get('i')}:{player.get('l')}"
            if player.get("l") not in expected_slugs | {"former"}:
                errors.append(f"{label}: unknown league slug")
            _check_number(errors, player.get("rt"), 0, 10, f"{label} rating")
            _check_number(errors, player.get("p"), 0, 100, f"{label} percentile")
            if player.get("l") == "former":
                _check_number(errors, player.get("m"), 0, 100_000, f"{label} minutes")
            else:
                _check_number(errors, player.get("m"), 450, 100_000, f"{label} minutes")
            _check_number(errors, player.get("em"), 0, 100_000, f"{label} Europe minutes")
            _check_number(errors, player.get("ea"), 0, 1_000, f"{label} Europe apps")
            if player.get("es") not in EUROPE_STATUSES:
                errors.append(f"{label}: invalid European status")
            if not player.get("c") or not player.get("sc"):
                errors.append(f"{label}: missing current or stats club")
            if player.get("eu") is not None and not isinstance(player.get("eu"), list):
                errors.append(f"{label}: Europe competitions is not a list")
            _check_number(errors, player.get("gl"), 0, 10_000, f"{label} goals")
            _check_number(errors, player.get("ast"), 0, 10_000, f"{label} assists")
            _check_number(errors, player.get("g90"), 0, 100, f"{label} goals per 90")
            _check_number(errors, player.get("sh90"), 0, 1_000, f"{label} shots per 90")
            _check_number(errors, player.get("cv"), 0, 1_000, f"{label} conversion")
            if player.get("cs") is not None and player.get("cs") not in CLUB_STATUSES:
                errors.append(f"{label}: invalid current-club status")
            arp = player.get("arp")
            if arp is not None:
                if not isinstance(arp, list):
                    errors.append(f"{label}: profile scores are not a list")
                else:
                    for entry in arp:
                        if not isinstance(entry, list) or len(entry) != 4:
                            errors.append(f"{label}: malformed profile score entry")
                            continue
                        index, adjusted, raw, profile_coverage = entry
                        if not isinstance(index, int) or not 0 <= index < len(profile_order):
                            errors.append(f"{label}: invalid profile index")
                        _check_number(errors, adjusted, 0, 100, f"{label} adjusted profile")
                        _check_number(errors, raw, 0, 100, f"{label} raw profile")
                        _check_number(
                            errors,
                            profile_coverage,
                            0,
                            1,
                            f"{label} profile coverage",
                        )
        profile_order = search.get("profile_order") or []
        if sorted(profile_order) != sorted((search.get("profile_labels") or {}).keys()):
            errors.append("search profile order does not match the profile labels")
        _check_number(
            errors,
            search.get("archetype_min_coverage"),
            0,
            1,
            "search archetype min coverage",
        )
        value_model = search.get("value_model") or {}
        for key in ("performance", "age", "minutes", "profile"):
            _check_number(
                errors,
                (value_model.get("weights") or {}).get(key),
                0,
                1,
                f"search value weight {key}",
            )
        _check_number(
            errors,
            value_model.get("min_weight_coverage"),
            0,
            1,
            "search value min coverage",
        )
        _check_number(errors, value_model.get("minutes_full"), 1, 10_000, "search minutes full")
        age_curve = value_model.get("age_curve") or []
        if not age_curve:
            errors.append("search value age curve is empty")
        for band in age_curve:
            _check_number(errors, band.get("max_age"), 1, 200, "search age band max")
            _check_number(errors, band.get("factor"), 0, 1, "search age band factor")
        team_context = search.get("team_context") or {}
        _check_number(
            errors,
            team_context.get("underperforming_ppg_percentile_max"),
            0,
            100,
            "search team threshold",
        )
        _check_number(errors, team_context.get("min_lift"), 0, 100, "search team min lift")
        priority = hub.get("priority") or {}
        _check_number(errors, priority.get("u23_max_age"), 0, 60, "priority u23 max age")
        _check_number(errors, priority.get("u23_multiplier"), 0, 3, "priority u23 multiplier")
        _check_number(
            errors,
            priority.get("europe_minutes_threshold"),
            0,
            100_000,
            "priority Europe threshold",
        )
        _check_number(errors, priority.get("europe_multiplier"), 0, 3, "priority Europe multiplier")
        current_clubs = coverage.get("current_clubs") or {}
        if current_clubs:
            _check_number(errors, current_clubs.get("players"), 0, 100_000, "current-club players")
            _check_number(
                errors, current_clubs.get("teams_fetched"), 0, 10_000, "current-club teams"
            )
        europe = coverage.get("europe") or {}
        if europe:
            if europe.get("coverage_complete") not in {True, False}:
                errors.append("Europe coverage completeness is not a boolean")
            for item in europe.get("competitions") or []:
                _check_number(errors, item.get("played"), 0, 10_000, "Europe played")
                _check_number(errors, item.get("fetched"), 0, 10_000, "Europe fetched")
                if int(item.get("fetched") or 0) > int(item.get("played") or 0):
                    errors.append(f"{item.get('competition')}: fetched more than played")
        for document in [hub, coverage, search]:
            for location, key, _ in _walk(document):
                if key in FORBIDDEN_KEYS:
                    errors.append(f"{location}: forbidden contract/fee field")
    return errors


def check_pages() -> list[str]:
    errors: list[str] = []
    if not OUT.exists():
        return [f"missing static export {OUT}"]
    hub_page = OUT / "scouting" / "index.html"
    if not hub_page.exists():
        errors.append("missing /scouting/ page")
    else:
        html = hub_page.read_text(encoding="utf-8")
        for marker in ("scouting.filters", "scouting.lenses"):
            if f'data-contract="{marker}"' not in html:
                errors.append(f"scouting hub: missing {marker} marker")
        if "Published defaults" not in html:
            errors.append("scouting hub: missing the published-defaults label")
    search_page = OUT / "scouting" / "search" / "index.html"
    if not search_page.exists():
        errors.append("missing /scouting/search/ page")
    else:
        html = search_page.read_text(encoding="utf-8")
        if len(re.findall(r"<h1[ >]", html)) != 1:
            errors.append("scouting search: expected exactly one H1")
        if 'data-contract="scouting.advanced-filters"' not in html:
            errors.append("scouting search: missing the advanced-filters marker")
        if "Published defaults" not in html:
            errors.append("scouting search: missing the published-defaults label")
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
            "Priority",
            "Europe",
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
        "Team",
        "Lift",
        "Role",
        "Mins",
        "Rating",
        "Pct",
        "Adj Pct",
        "Value index",
        "Priority",
        "Europe",
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
        if 'data-contract="scouting.lenses"' not in html:
            errors.append(f"{slug}: missing the scouting lens selector")
        if not re.search(r"<caption", html):
            errors.append(f"{slug}: missing table caption")
        for header in required:
            if header not in html:
                errors.append(f"{slug}: missing column {header!r}")

    search = _load(SEARCH) if SEARCH.exists() else {}
    player_ids = sorted({int(row["i"]) for row in search.get("players") or []})
    for player_id in player_ids:
        page = OUT / "scouting" / "player" / str(player_id) / "index.html"
        if not page.exists():
            errors.append(f"missing scouting profile page for {player_id}")
            continue
        html = page.read_text(encoding="utf-8")
        if len(re.findall(r"<h1[ >]", html)) != 1:
            errors.append(f"player {player_id}: expected exactly one H1")
        for marker in (
            "player-profile.header",
            "player-profile.rose",
            "player-profile.summary",
            "player-profile.output",
            "player-profile.context",
            "player-profile.coverage",
        ):
            if f'data-contract="{marker}"' not in html:
                errors.append(f"player {player_id}: missing {marker} marker")
        if html.count('data-rose-figure="overall"') != 1:
            errors.append(f"player {player_id}: missing the overall rose figure")
        if html.count('data-rose-figure="position"') != 1:
            errors.append(f"player {player_id}: missing the position rose figure")
        for phrase in (
            "Overall profile",
            "Position profile",
            "Scouting priority",
            "League-phase shop window",
            "Current club",
            "Raw and adjusted archetype scores",
            "not a target",
        ):
            if phrase not in html:
                errors.append(f"player {player_id}: missing {phrase!r}")
        if not re.search(r'href="[^"]*scouting/"', html):
            errors.append(f"player {player_id}: missing link back to the scouting board")
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
