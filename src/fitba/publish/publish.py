"""Publish derived JSON for the web app.

Atomic: write a temp directory, validate the file sizes, then replace the live
directory. The manifest is written last. Raw/source-shaped feeds never enter
this directory.
"""

from __future__ import annotations

import calendar
import hashlib
import shutil
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import orjson
import polars as pl

from fitba.analytics.tables import build_tables
from fitba.analytics.valuation import (
    summarise_valuations,
    value_transfers,
)
from fitba.ingest.cups import league_cup_summary, scottish_cup_summary
from fitba.ingest.fixtures import load_club_fixtures
from fitba.ingest.history import load_all_history
from fitba.ingest.match_data import (
    load_player_appearances,
    load_player_match_stats,
    load_team_shapes,
)
from fitba.ingest.news import load_news
from fitba.ingest.runner import load_matches
from fitba.ingest.squad import load_squad_players
from fitba.ingest.transfer_audit import load_candidates, load_prior_squads
from fitba.ingest.transfers import published_transfers, withheld_transfers
from fitba.metrics.audit import (
    build_audit,
    build_registry_payload,
    build_validation_payload,
    load_corpus,
)
from fitba.metrics.registry import load_registry, registry_checksum
from fitba.normalize.teams import TeamRegistry
from fitba.normalize.transfer_audit import build_transfer_audit
from fitba.publish.availability import build_availability_payload
from fitba.publish.case import build_case_payload, fallback_case_payload
from fitba.publish.fixture import build_fixture_payloads
from fitba.publish.history import build_history_payloads
from fitba.publish.matchday import (
    build_matchday_payload,
    fallback_matchday_payload,
)
from fitba.publish.needs import build_needs_payload, fallback_needs_payload
from fitba.publish.player_page import build_player_page
from fitba.publish.provenance import build_provenance_payload
from fitba.publish.rumours import (
    forum_payload,
    load_rumour_rows,
    profile_payload,
    rumours_payload,
)
from fitba.publish.shapes import shape_payload
from fitba.publish.squad import PlayerLinkIndex, squad_payload
from fitba.publish.themes import build_themes_payload, fallback_themes_payload
from fitba.publish.xg import build_xg_payload, fallback_xg_payload
from fitba.settings import (
    WEB_DATA_DIR,
    ensure_dirs,
    history_markets,
    source_registry,
)
from fitba.settings import (
    aberdeen as aberdeen_config,
)
from fitba.settings import (
    competitions as competitions_config,
)
from fitba.settings import (
    cups as cups_config,
)
from fitba.settings import (
    european_competitions as european_config,
)
from fitba.settings import (
    sell_on_clauses as sell_on_config,
)
from fitba.settings import (
    source_ids as source_ids_config,
)
from fitba.settings import (
    transfer_gaps as transfer_gaps_config,
)
from fitba.settings import (
    transfer_policy as transfer_policy_config,
)
from fitba.util.dates import current_season, seasons_between, utc_now_iso
from fitba.validate.checks import validate_matches, validate_published, validate_tables

SCHEMA_VERSION = "1.0.0"
MAX_FILE_BYTES = 2_000_000


@dataclass(slots=True)
class PublishReport:
    out: str
    season: str
    files: int
    bytes: int
    dataset_version: str
    manifest: dict[str, Any] = field(default_factory=dict)


def _dumps(payload: Any) -> bytes:
    return orjson.dumps(payload, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS, default=str)


def _write(path: Path, payload: Any) -> dict[str, Any]:
    data = _dumps(payload)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"{path} is {len(data)} bytes, over the {MAX_FILE_BYTES} cap")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "path": str(path),
        "bytes": len(data),
        "checksum": "sha256:" + hashlib.sha256(data).hexdigest(),
    }


def _previous_fixture_payloads(target: Path) -> dict[str, Any] | None:
    index_path = target / "fixtures" / "index.json"
    if not index_path.exists():
        return None
    try:
        index = orjson.loads(index_path.read_bytes())
    except orjson.JSONDecodeError:
        return None
    documents: dict[int, dict[str, Any]] = {}
    for path in (target / "matches").glob("*.json"):
        if not path.stem.isdigit():
            continue
        try:
            documents[int(path.stem)] = orjson.loads(path.read_bytes())
        except orjson.JSONDecodeError:
            continue
    if not documents:
        return None
    return {
        "schema_version": index.get("schema_version", "1.0.0"),
        "generated_at": index.get("generated_at"),
        "count": len(index.get("fixtures") or []),
        "fixtures": index.get("fixtures") or [],
        "documents": documents,
        "state": "stale",
        "stale_reason": "fixture_build_returned_fewer_pages",
    }


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return "nogit"


def _competition_slug(competition_id: str) -> str:
    return competition_id.split(":", 1)[-1]


def _table_payload(table: pl.DataFrame, competition: dict[str, Any], season: str) -> dict[str, Any]:
    return {
        "competition_id": competition["id"],
        "competition_name": competition["name"],
        "short_name": competition["short_name"],
        "tier": competition["tier"],
        "season": season,
        "qualification_note": competition.get("qualification_note"),
        "cutoffs": competition.get("cutoffs", []),
        "rows": table.to_dicts(),
    }


def _stage_for(competition_id: str, match_date: Any) -> str | None:
    for cup in cups_config().get("cups", []):
        if cup["id"] != competition_id:
            continue
        for window in cup.get("stage_windows", []):
            if window["start"] <= match_date <= window["end"]:
                return str(window["stage"])
    return None


def _aberdeen_payload(
    matches: pl.DataFrame,
    tables_by_season: dict[str, dict[str, pl.DataFrame]],
    season: str,
    player_index: PlayerLinkIndex,
) -> dict[str, Any]:
    club_id = str(aberdeen_config()["club_id"])
    club_matches = matches.filter(
        (pl.col("home_team_id") == club_id) | (pl.col("away_team_id") == club_id)
    ).sort("date", descending=True)

    def result_row(row: dict[str, Any]) -> dict[str, Any]:
        is_home = row["home_team_id"] == club_id
        goals_for = row["home_goals"] if is_home else row["away_goals"]
        goals_against = row["away_goals"] if is_home else row["home_goals"]
        return {
            "match_id": row["match_id"],
            "date": row["date"],
            "competition_id": row["competition_id"],
            "opponent_id": row["away_team_id"] if is_home else row["home_team_id"],
            "opponent_name": row["away_team_name"] if is_home else row["home_team_name"],
            "venue": "H" if is_home else "A",
            "goals_for": goals_for,
            "goals_against": goals_against,
            "result": "W"
            if goals_for > goals_against
            else "D"
            if goals_for == goals_against
            else "L",
        }

    results = [result_row(row) for row in club_matches.to_dicts()]

    club_slug = club_id.split(":", 1)[-1]
    fixture_frame = load_club_fixtures(club_slug)
    fixture_rows = fixture_frame.to_dicts() if fixture_frame.height else []

    def fixture_row(row: dict[str, Any]) -> dict[str, Any]:
        is_home = row["home_team_id"] == club_id
        item = {
            "match_id": row["match_id"],
            "competition_id": row["competition_id"],
            "competition_name": row["competition_name"],
            "stage": _stage_for(row["competition_id"], row["date"]),
            "date": row["date"],
            "kickoff": row["kickoff"],
            "opponent_id": row["away_team_id"] if is_home else row["home_team_id"],
            "opponent_name": row["away_team_name"] if is_home else row["home_team_name"],
            "venue": "H" if is_home else "A",
            "status": row["status"],
        }
        if row["status"] == "played":
            goals_for = row["home_goals"] if is_home else row["away_goals"]
            goals_against = row["away_goals"] if is_home else row["home_goals"]
            item["goals_for"] = goals_for
            item["goals_against"] = goals_against
            item["result"] = (
                "W" if goals_for > goals_against else "D" if goals_for == goals_against else "L"
            )
        return item

    fixtures = sorted(
        [fixture_row(row) for row in fixture_rows if row["status"] == "scheduled"],
        key=lambda item: (str(item["date"]), item.get("kickoff") or ""),
    )
    recent_results = sorted(
        [fixture_row(row) for row in fixture_rows if row["status"] == "played"],
        key=lambda item: str(item["date"]),
        reverse=True,
    )

    news = [
        {
            "article_id": row["article_id"],
            "title": row["title"],
            "category": row["category"],
            "category_slug": row["category_slug"],
            "published_date": row["published_date"],
            "url": row["url"],
            "source": "Aberdeen FC",
            "player_mentions": player_index.mentions(row["title"]),
        }
        for row in load_news(limit=24).to_dicts()
    ]

    spfl_meta = source_registry()["sources"].get("spfl", {})
    league_id = None
    table_row = None
    for competition_id, table in (tables_by_season.get(season) or {}).items():
        if table is None or not table.height:
            continue
        rows = table.filter(pl.col("team_id") == club_id)
        if rows.height:
            league_id = competition_id
            table_row = rows.to_dicts()[0]
            break
    league_meta = next(
        (
            competition
            for competition in competitions_config()["competitions"]
            if competition["id"] == league_id
        ),
        None,
    )
    competitions: list[dict[str, Any]] = []
    if league_meta:
        competitions.append(
            {
                "id": league_meta["id"],
                "name": league_meta["name"],
                "short_name": league_meta["short_name"],
                "status": "Active",
                "stage": None,
                "next_fixture": next(
                    (item for item in fixtures if item["competition_id"] == league_meta["id"]),
                    None,
                ),
                "source": spfl_meta.get("url"),
                "verified_at": spfl_meta.get("last_verified"),
            }
        )
    for cup in cups_config().get("cups", []):
        next_fixture = next(
            (item for item in fixtures if item["competition_id"] == cup["id"]), None
        )
        competitions.append(
            {
                "id": cup["id"],
                "name": cup["name"],
                "short_name": cup["short_name"],
                "status": cup.get("status", "Active"),
                "stage": next_fixture["stage"] if next_fixture else None,
                "entry_round": cup.get("entry_round"),
                "entry_date": cup.get("entry_date"),
                "note": cup.get("note"),
                "next_fixture": next_fixture,
                "source": cup.get("source"),
                "verified_at": cup.get("verified_at"),
            }
        )

    europe = (european_config() or {}).get("aberdeen") or {}
    if europe.get("in_europe"):
        for competition in europe.get("competitions", []) or []:
            competitions.append(
                {
                    "id": competition.get("id"),
                    "name": competition.get("name"),
                    "short_name": competition.get("short_name"),
                    "status": "Active",
                    "stage": competition.get("stage"),
                    "next_fixture": competition.get("next_fixture"),
                    "source": competition.get("source"),
                    "verified_at": competition.get("verified_at"),
                }
            )

    history = []
    for history_season in sorted(tables_by_season, reverse=True):
        for table in (tables_by_season[history_season] or {}).values():
            if table is None or not table.height:
                continue
            rows = table.filter(pl.col("team_id") == club_id)
            if not rows.height:
                continue
            row = rows.to_dicts()[0]
            history.append(
                {
                    "season": history_season,
                    "position": row["position"],
                    "played": row["played"],
                    "points": row["points"],
                    "gd": row["gd"],
                    "form": row["form"],
                }
            )
            break

    summary = None
    if table_row:
        summary = {
            key: table_row[key]
            for key in (
                "position",
                "played",
                "won",
                "drawn",
                "lost",
                "gf",
                "ga",
                "gd",
                "points",
                "form",
                "competition_id",
                "competition_name",
            )
        }

    club_team_id = int(source_ids_config()["teams"][club_id]["api_football"])
    return {
        "club_id": club_id,
        "name": aberdeen_config()["name"],
        "profile": {
            key: aberdeen_config().get(key)
            for key in ("nickname", "stadium", "city", "founded", "colours")
        },
        "budget": aberdeen_config().get("budget"),
        "squad_needs": aberdeen_config().get("squad_needs"),
        "style_intent": aberdeen_config().get("style_intent"),
        "season": season,
        "summary": summary,
        "results": results,
        "fixtures": fixtures,
        "recent_results": recent_results,
        "competitions": competitions,
        "news": news,
        "history": history,
        "shapes": shape_payload(team_id=club_team_id, season_year=int(season[:4])),
        "coverage": "match",
        "notes": (
            "League results from football-data.co.uk; league and League Cup "
            "fixtures from the SPFL club feed; Scottish Cup calendar from the SFA. "
            "Player/event layers pending."
        ),
    }


FIXTURE_FIELDS = [
    "match_id",
    "round",
    "round_order",
    "group",
    "date",
    "kickoff",
    "home_team_id",
    "home_team_name",
    "away_team_id",
    "away_team_name",
    "home_goals",
    "away_goals",
    "home_penalties",
    "away_penalties",
    "status",
    "winner_team_id",
    "extra_time",
    "venue",
]


def _fixture_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row.get(field) for field in FIXTURE_FIELDS}


def _rounds_payload(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rounds: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for row in fixtures:
        key = (int(row["round_order"]), str(row["round"]))
        rounds.setdefault(key, []).append(_fixture_payload(row))
    return [
        {
            "name": name,
            "order": order,
            "fixtures": sorted(items, key=lambda item: (str(item["date"]), item["kickoff"] or "")),
        }
        for (order, name), items in sorted(rounds.items())
    ]


def _league_cup_payload(summary: dict[str, Any], season: str) -> dict[str, Any]:
    cup = summary["cup"]
    fixtures = summary["fixtures"]
    rounds = _rounds_payload(fixtures)
    present_orders = {round_["order"] for round_ in rounds}
    official_rounds = cup.get("official_rounds", [])
    final = next((item for item in official_rounds if item["name"] == "Final"), None)
    if final and final["order"] not in present_orders:
        rounds.append(
            {
                "name": "Final",
                "order": final["order"],
                "fixtures": [],
                "note": "Final: 13 December 2026, Hampden Park — participants TBC.",
            }
        )
    scheduled = summary["scheduled"]
    qualifiers = [
        *summary["group_winners"],
        *summary["best_runners_up"],
        *summary["byes"],
    ]
    return {
        "competition_id": cup["id"],
        "name": cup["name"],
        "short_name": cup["short_name"],
        "kind": "cup",
        "season": season,
        "format": {
            "groups": cup.get("groups"),
            "teams_per_group": cup.get("teams_per_group"),
            "group_points": cup.get("group_points"),
            "qualifiers": cup.get("qualifiers"),
            "bye_rule": cup.get("bye_rule"),
            "official_rounds": official_rounds,
        },
        "status": {
            "phase": scheduled[0]["round"] if scheduled else "Complete",
            "next_fixtures": [_fixture_payload(item) for item in scheduled],
            "coverage_note": cup.get("coverage_note"),
        },
        "groups": summary["groups"],
        "group_winners": summary["group_winners"],
        "best_runners_up": summary["best_runners_up"],
        "byes": summary["byes"],
        "qualifiers": {
            "count": len(qualifiers),
            "group_winners": summary["group_winners"],
            "best_runners_up": summary["best_runners_up"],
            "byes": summary["byes"],
        },
        "rounds": rounds,
        "fixtures": [_fixture_payload(item) for item in fixtures],
        "validation": summary.get("validation"),
        "source": {
            "id": "api_football",
            "name": "API-Football",
            "url": "https://www.api-football.com",
            "verified_at": cup.get("verified_at"),
        },
    }


def _scottish_cup_payload(summary: dict[str, Any], season: str) -> dict[str, Any]:
    cup = summary["cup"]
    fixtures = summary["fixtures"]
    covered_rounds = {item["name"]: item for item in _rounds_payload(fixtures)}
    official_rounds = cup.get("official_rounds", [])
    rounds = []
    for official in official_rounds:
        covered = covered_rounds.get(official["name"])
        rounds.append(
            {
                "name": official["name"],
                "order": official["order"],
                "official_ties": official.get("ties"),
                "official_date": official.get("date"),
                "covered": covered is not None,
                "fixtures": covered["fixtures"] if covered else [],
            }
        )
    licensed_ties = len(fixtures)
    official_ties = int(cup.get("total_ties") or 136)
    present_names = [item["name"] for item in summary["rounds_present"]]
    missing_names = [item["name"] for item in summary["missing_rounds"]]
    coverage_note = (
        f"The licensed feed covers {licensed_ties} of {official_ties} ties "
        f"({', '.join(present_names) if present_names else 'no rounds'}). "
        f"Rounds not provided: {', '.join(missing_names) if missing_names else 'none'}. "
        "The page labels the gap rather than inventing ties."
    )
    return {
        "competition_id": cup["id"],
        "name": cup["name"],
        "short_name": cup["short_name"],
        "kind": "cup",
        "season": season,
        "format": {
            "total_clubs": cup.get("total_clubs"),
            "total_ties": official_ties,
            "entry_round": cup.get("entry_round"),
            "entry_date": cup.get("entry_date"),
            "official_rounds": official_rounds,
        },
        "coverage": {
            "official_ties": official_ties,
            "licensed_ties": licensed_ties,
            "rounds_present": present_names,
            "rounds_missing": missing_names,
            "note": coverage_note,
            "status": "partial" if licensed_ties < official_ties else "full",
        },
        "status": {
            "phase": summary["scheduled"][0]["round"] if summary["scheduled"] else "In progress",
            "next_fixtures": [_fixture_payload(item) for item in summary["scheduled"]],
        },
        "rounds": rounds,
        "fixtures": [_fixture_payload(item) for item in fixtures],
        "aberdeen": {
            "entry_round": cup.get("entry_round"),
            "entry_date": cup.get("entry_date"),
            "status": "Awaiting draw",
            "note": cup.get("note"),
        },
        "source": {
            "id": "api_football",
            "name": "API-Football",
            "url": "https://www.api-football.com",
            "verified_at": cup.get("verified_at"),
        },
    }


def _short_date(value: Any) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%d %b %Y").lstrip("0")
    return str(value)


def _competitions_index(
    tables: dict[str, pl.DataFrame],
    league_cup: dict[str, Any],
    scottish_cup: dict[str, Any],
    season: str,
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    aberdeen_league_id = next(
        (
            competition_id
            for competition_id, table in tables.items()
            if table is not None
            and table.height
            and table.filter(pl.col("team_id") == "sco:aberdeen").height
        ),
        None,
    )
    for competition in competitions_config()["competitions"]:
        table = tables.get(competition["id"])
        leader = table.to_dicts()[0] if table is not None and table.height else None
        slug = _competition_slug(competition["id"])
        entries.append(
            {
                "id": competition["id"],
                "name": competition["name"],
                "short_name": competition["short_name"],
                "kind": "league",
                "tier": competition["tier"],
                "season": season,
                "status": "Active",
                "leader": leader,
                "link": f"/scotland/{slug}/",
                "coverage": "match",
                "aberdeen_involved": competition["id"] == aberdeen_league_id,
            }
        )
    for cup in (league_cup, scottish_cup):
        next_fixtures = cup.get("status", {}).get("next_fixtures", [])
        next_fixture = next_fixtures[0] if next_fixtures else None
        aberdeen_note = None
        if cup["competition_id"] == "sco:scottish-cup":
            aberdeen = cup.get("aberdeen", {})
            aberdeen_note = (
                f"Aberdeen enter the {aberdeen.get('entry_round')} · "
                f"{_short_date(aberdeen.get('entry_date'))} · {aberdeen.get('status')}"
            )
        elif next_fixture and "Aberdeen" in (
            next_fixture.get("home_team_name"),
            next_fixture.get("away_team_name"),
        ):
            aberdeen_note = (
                f"{next_fixture['home_team_name']} v {next_fixture['away_team_name']} · "
                f"{_short_date(next_fixture['date'])}"
            )
        entries.append(
            {
                "id": cup["competition_id"],
                "name": cup["name"],
                "short_name": cup["short_name"],
                "kind": "cup",
                "season": cup["season"],
                "status": cup.get("coverage", {}).get("status", "active"),
                "stage": cup.get("status", {}).get("phase"),
                "next_fixture": next_fixture,
                "aberdeen_note": aberdeen_note,
                "link": f"/competitions/{_competition_slug(cup['competition_id'])}/",
                "coverage": cup.get("coverage", {}).get(
                    "status",
                    "match" if cup["competition_id"] == "sco:league-cup" else "partial",
                ),
                "aberdeen_involved": True,
            }
        )
    europe = european_config() or {}
    europe_aberdeen = europe.get("aberdeen") or {}
    europe_competitions = [
        {
            "id": competition.get("id"),
            "name": competition.get("name"),
            "short_name": competition.get("short_name"),
            "stage": competition.get("stage"),
            "next_fixture": competition.get("next_fixture"),
            "source": competition.get("source"),
            "verified_at": competition.get("verified_at"),
            "link": competition.get("link"),
        }
        for competition in europe_aberdeen.get("competitions", []) or []
    ]
    return {
        "season": season,
        "competitions": [
            entry
            for entry in entries
            if entry.get("aberdeen_involved") and entry.get("season") == season
        ],
        "europe": {
            "season": europe.get("season") or season,
            "in_europe": bool(europe_aberdeen.get("in_europe")),
            "note": europe_aberdeen.get("note"),
            "competitions": europe_competitions,
        },
    }


def _fee_display(row: dict[str, Any]) -> str:
    status = row.get("fee_status")
    if status == "free":
        return "Free"
    if status == "loan":
        return "Loan"
    if status == "disclosed" and row.get("fee_amount") is not None:
        currency = row.get("fee_currency") or "GBP"
        symbol = {"GBP": "£", "EUR": "€", "USD": "$"}.get(currency, "")
        return f"{symbol}{float(row['fee_amount']):,.0f}"
    return "Undisclosed"


def _transfer_payload(
    row: dict[str, Any],
    player_index: PlayerLinkIndex | None = None,
    registry: TeamRegistry | None = None,
) -> dict[str, Any]:
    fields = [
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
        "loan_end_date",
        "recall_clause",
        "obligation_to_buy",
        "option_to_buy",
        "verification_status",
        "source_urls",
        "verified_at",
        "notes",
    ]
    payload = {field: row.get(field) for field in fields}
    if registry is not None:
        payload["from_club_name"] = registry.display_name_for_id(
            row.get("from_club_id"), row.get("from_club_name")
        )
        payload["to_club_name"] = registry.display_name_for_id(
            row.get("to_club_id"), row.get("to_club_name")
        )
    payload["fee_display"] = _fee_display(row)
    payload["fee_estimate"] = row.get("fee_estimate")
    payload["player_href"] = (
        player_index.href(row.get("player_key")) if player_index is not None else None
    )
    return payload


def _window_label(season: str, window: str) -> str:
    start = int(season[:4])
    if window == "summer":
        return f"Summer {start}"
    if window == "winter":
        return f"Winter {start + 1}"
    return f"Out of window {start + 1}"


def _window_bounds(season: str, window: str) -> tuple[date, date] | None:
    start = int(season[:4])
    if window == "summer":
        return date(start, 5, 1), date(start, 9, 30)
    if window == "winter":
        end_month = 2
        end_day = calendar.monthrange(start + 1, end_month)[1]
        return date(start, 12, 1), date(start + 1, end_month, end_day)
    return None


def _window_state(season: str, window: str) -> str:
    bounds = _window_bounds(season, window)
    if bounds is None:
        return "closed"
    today = date.today()
    start, end = bounds
    if today < start:
        return "upcoming"
    if today <= end:
        return "open"
    return "closed"


def _window_coverage(season: str, policy: dict[str, Any]) -> str:
    audited_from = str((policy.get("transfers") or {}).get("audited_from") or "2024-25")
    return "audited" if season >= audited_from else "curated_partial"


def _window_era_context(season: str, window: str) -> str:
    bounds = _window_bounds(season, window)
    if bounds is None:
        return "era"
    return "pre_era" if bounds[1] < date(2019, 12, 16) else "era"


def _valuation_birth_dates() -> dict[str, str]:
    """Birth dates from historical rosters and the current squad, keyed by player."""
    dates: dict[str, str] = {}
    for season_data in (load_all_history().get("seasons") or {}).values():
        rosters = season_data.get("rosters")
        if rosters is None or not rosters.height:
            continue
        for row in rosters.to_dicts():
            player_id = row.get("player_id")
            birth = row.get("birth_date")
            if player_id is not None and birth:
                dates.setdefault(f"api:player:{int(player_id)}", str(birth))
    squad = load_squad_players()
    if squad.height:
        for row in squad.to_dicts():
            player_id = row.get("player_id")
            birth = row.get("birth_date")
            if player_id is not None and birth:
                dates.setdefault(f"api:player:{int(player_id)}", str(birth))
    return dates


def _window_summary(
    rows: list[dict[str, Any]],
    season: str,
    window: str,
    *,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bucket = [row for row in rows if row.get("season") == season and row.get("window") == window]
    arrivals = [row for row in bucket if row["direction"] == "in"]
    departures = [row for row in bucket if row["direction"] == "out"]
    disclosed_in = [
        row
        for row in arrivals
        if row.get("fee_status") == "disclosed" and row.get("fee_amount") is not None
    ]
    disclosed_out = [
        row
        for row in departures
        if row.get("fee_status") == "disclosed" and row.get("fee_amount") is not None
    ]
    spend = sum(float(row["fee_amount"]) for row in disclosed_in)
    income = sum(float(row["fee_amount"]) for row in disclosed_out)
    unknown = sum(
        1
        for row in bucket
        if row.get("transfer_kind") in {"permanent"} and row.get("fee_status") != "disclosed"
    )
    valuation = summarise_valuations(bucket)
    return {
        "key": f"{season}-{window}",
        "season": season,
        "window": window,
        "label": _window_label(season, window),
        "coverage": _window_coverage(season, policy or {}),
        "state": _window_state(season, window),
        "era_context": _window_era_context(season, window),
        "arrivals": len(arrivals),
        "departures": len(departures),
        "permanent_in": sum(1 for row in arrivals if row["transfer_kind"] == "permanent"),
        "permanent_out": sum(1 for row in departures if row["transfer_kind"] == "permanent"),
        "loans_in": sum(1 for row in arrivals if row["transfer_kind"] == "loan"),
        "loans_out": sum(1 for row in departures if row["transfer_kind"] == "loan"),
        "free_in": sum(1 for row in arrivals if row["transfer_kind"] == "free"),
        "free_out": sum(1 for row in departures if row["transfer_kind"] == "free"),
        "disclosed_spend": spend,
        "disclosed_income": income,
        "net_spend": spend - income,
        "disclosed_count": len(disclosed_in) + len(disclosed_out),
        "undisclosed_count": unknown,
        "inferred_net_low_gbp": valuation.get("fee_low_gbp"),
        "inferred_net_high_gbp": valuation.get("fee_high_gbp"),
        "valuation_confidence": valuation.get("confidence"),
        "valuation_counts": valuation.get("counts"),
    }


def _transfers_payload(
    rows: list[dict[str, Any]],
    season: str,
    player_index: PlayerLinkIndex,
    *,
    valuation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    seasons = sorted({row["season"] for row in rows}, reverse=True)
    season_dash = chr(0x2013)

    def window_date_key(item: tuple[str, str]) -> tuple[int, int]:
        season, window = item
        start = int(season[:4])
        if window == "summer":
            return (start, 7)
        if window == "winter":
            return (start + 1, 1)
        return (start, 3)

    policy = transfer_policy_config() or {}
    markets = (history_markets() or {}).get("markets", [])
    if valuation is None:
        valuation = value_transfers(
            rows,
            birth_dates=_valuation_birth_dates(),
            markets=markets,
            fx=(policy.get("valuation") or {}).get("fx_to_gbp"),
        )
    valuation_summary = dict(valuation)
    valuation_summary["method"] = (
        "Market/position base x age curve, calibrated to reported/disclosed fees"
    )
    expected_from = str((policy.get("transfers") or {}).get("expected_windows_from") or "2019-20")
    expected = {
        (expected_season, window)
        for expected_season in seasons_between(expected_from, season)
        for window in ("summer", "winter")
    }
    window_keys = sorted(
        expected | {(row["season"], row["window"]) for row in rows},
        key=window_date_key,
        reverse=True,
    )
    windows = [
        _window_summary(rows, current, window, policy=policy) for current, window in window_keys
    ]
    recent_count = int((policy.get("audit") or {}).get("recent_windows") or 4)
    regular = [
        window
        for window in windows
        if window["window"] in {"summer", "winter"} and window["state"] != "upcoming"
    ]
    upcoming = [
        window
        for window in windows
        if window["window"] in {"summer", "winter"} and window["state"] == "upcoming"
    ]
    out_of_window = [window for window in windows if window["window"] == "other"]
    window_groups = {
        "recent": [window["key"] for window in regular[:recent_count]],
        "further": [window["key"] for window in regular[recent_count:]],
        "out_of_window": [window["key"] for window in out_of_window],
        "upcoming": [window["key"] for window in upcoming],
    }
    transfers = sorted(rows, key=lambda row: row.get("date_effective") or "", reverse=True)
    registry = TeamRegistry()
    by_transfer = {str(row.get("transfer_id")): row for row in rows}
    sell_on = []
    for clause in sell_on_config().get("clauses", []) or []:
        item = dict(clause)
        row = by_transfer.get(str(clause.get("transfer_id")))
        item["fee_display"] = _fee_display(row) if row else None
        item["fee_estimate"] = row.get("fee_estimate") if row else None
        sell_on.append(item)
    sell_on.sort(key=lambda item: str(item.get("sale_date") or ""), reverse=True)
    withheld = withheld_transfers()
    plausibility = {
        "withheld": len(withheld),
        "note": (
            "Rows that fail the provider/plausibility screen are withheld until "
            "a reviewer accepts them in reference/transfer_plausibility.yaml. "
            "The public count is a coverage warning, not a list of names."
        ),
    }
    sell_on_summary = {
        "total": len(sell_on),
        "confirmed": sum(1 for item in sell_on if item.get("confidence") == "confirmed"),
        "reported": sum(1 for item in sell_on if item.get("confidence") == "reported"),
        "percentage_known": sum(1 for item in sell_on if item.get("sell_on_pct") is not None),
        "percentage_unknown": sum(1 for item in sell_on if item.get("sell_on_pct") is None),
        "note": (
            "Only publicly sourced or reported clauses are tracked. A blank "
            "percentage means the clause is reported but the percentage is "
            "undisclosed; it is never inferred."
        ),
    }
    sources = sorted({url for row in rows for url in (row.get("source_urls") or []) if url})
    confirmed = sum(1 for row in rows if row.get("verification_status") == "confirmed")
    curated = sum(1 for row in rows if row.get("verification_status") == "curated")
    return {
        "club_id": "sco:aberdeen",
        "name": "Aberdeen",
        "season": season,
        "seasons": seasons,
        "windows": windows,
        "window_groups": window_groups,
        "transfers": [_transfer_payload(row, player_index, registry) for row in transfers],
        "loans_out": [
            _transfer_payload(row, player_index, registry)
            for row in transfers
            if row["direction"] == "out" and row["transfer_kind"] == "loan"
        ],
        "loans_in": [
            _transfer_payload(row, player_index, registry)
            for row in transfers
            if row["direction"] == "in" and row["transfer_kind"] == "loan"
        ],
        "summary": {
            "total": len(rows),
            "confirmed": confirmed,
            "curated": curated,
            "players": len({row["player_key"] for row in rows}),
            "seasons_covered": len(seasons),
            "windows_covered": len({(row["season"], row["window"]) for row in rows}),
            "period": (
                f"{seasons[-1].replace('-', '/')}{season_dash}{seasons[0].replace('-', '/')}"
                if seasons
                else None
            ),
        },
        "coverage": {
            "status": "curated",
            "audited_from": str((policy.get("transfers") or {}).get("audited_from") or "2024-25"),
            "historical_from": str(
                (policy.get("transfers") or {}).get("expected_windows_from") or "2019-20"
            ),
            "note": (
                "Confirmed business only. The recent four windows are audited "
                "against a seniority review; earlier windows are curated partial. "
                "Rows are curated from the licensed API-Football candidate feed and "
                "Wikipedia season tables; an official AFC announcement is linked "
                "where found. Fees are not in the feed. Disclosed/reported fees are "
                "kept as anchors; undisclosed permanent moves carry an inferred "
                "range, not a claimed amount. Free transfers count as zero fee; "
                "loan fees are excluded. Loan end, recall and obligation terms are "
                "unknown unless confirmed."
            ),
        },
        "valuation": valuation_summary,
        "plausibility": plausibility,
        "sell_on_clauses": sell_on,
        "sell_on_summary": sell_on_summary,
        "sources": sources,
        "notes": "No rumours or unconfirmed links are published in this register.",
    }


def publish(
    *,
    season: str | None = None,
    out: Path | None = None,
    profile: str = "public",
    require_validation: bool = False,
) -> PublishReport:
    ensure_dirs()
    target = out or WEB_DATA_DIR
    all_matches = load_matches(None)
    seasons = sorted(all_matches["season"].unique().to_list())
    target_season = season or current_season()
    if target_season not in seasons:
        target_season = seasons[-1]
    matches = all_matches.filter(pl.col("season") == target_season)

    tables_by_season: dict[str, dict[str, pl.DataFrame]] = {
        current: build_tables(all_matches, season=current, config=competitions_config())
        for current in seasons
    }
    tables = tables_by_season[target_season]
    generated_at = utc_now_iso()
    dataset_version = f"{generated_at}-{_git_sha()}"

    previous_matchday = None
    previous_matchday_path = target / "matchday" / "upcoming.json"
    if previous_matchday_path.exists():
        try:
            previous_matchday = orjson.loads(previous_matchday_path.read_bytes())
        except orjson.JSONDecodeError:
            previous_matchday = None

    previous_case = None
    previous_case_path = target / "themes" / "aberdeen.json"
    if previous_case_path.exists():
        try:
            previous_case = orjson.loads(previous_case_path.read_bytes())
        except orjson.JSONDecodeError:
            previous_case = None

    previous_xg = None
    previous_xg_path = target / "xg" / "aberdeen.json"
    if previous_xg_path.exists():
        try:
            previous_xg = orjson.loads(previous_xg_path.read_bytes())
        except orjson.JSONDecodeError:
            previous_xg = None

    previous_needs = None
    previous_needs_path = target / "needs" / "aberdeen.json"
    if previous_needs_path.exists():
        try:
            previous_needs = orjson.loads(previous_needs_path.read_bytes())
        except orjson.JSONDecodeError:
            previous_needs = None

    temp = target.with_name(target.name + ".tmp")
    if temp.exists():
        shutil.rmtree(temp)
    temp.mkdir(parents=True, exist_ok=True)

    written: list[dict[str, Any]] = []
    marts: list[dict[str, Any]] = []
    for competition in competitions_config()["competitions"]:
        competition_id = competition["id"]
        table = tables.get(competition_id)
        if table is None or not table.height:
            continue
        slug = _competition_slug(competition_id)
        path = temp / "tables" / f"{slug}-{target_season}.json"
        info = _write(path, _table_payload(table, competition, target_season))
        written.append(info)
        marts.append(
            {
                "id": f"league_table.{competition_id}",
                "path": str(path.relative_to(temp)),
                "rows": table.height,
                "checksum": info["checksum"],
                "season": target_season,
            }
        )

    squad_data = squad_payload(target_season, generated_at=generated_at)
    player_index = PlayerLinkIndex.from_payload(squad_data)
    squad_info = _write(temp / "squad" / "aberdeen.json", squad_data)
    written.append(squad_info)
    for player in squad_data["players"]:
        page = build_player_page(
            player,
            season=target_season,
            generated_at=generated_at,
        )
        page_info = _write(temp / "players" / f"{player['player_id']}.json", page)
        written.append(page_info)
    marts.append(
        {
            "id": "squad.sco:aberdeen",
            "path": "squad/aberdeen.json",
            "rows": len(squad_data["players"]),
            "checksum": squad_info["checksum"],
            "season": target_season,
        }
    )

    club_payload = _aberdeen_payload(
        matches, tables_by_season, target_season, player_index=player_index
    )
    club_info = _write(temp / "clubs" / "aberdeen.json", club_payload)
    written.append(club_info)
    marts.append(
        {
            "id": "club.sco:aberdeen",
            "path": "clubs/aberdeen.json",
            "rows": len(club_payload["results"]),
            "checksum": club_info["checksum"],
            "season": target_season,
        }
    )

    availability_payload = build_availability_payload(
        squad_data=squad_data,
        generated_at=generated_at,
        season=target_season,
    )
    availability_info = _write(temp / "availability" / "aberdeen.json", availability_payload)
    written.append(availability_info)
    marts.append(
        {
            "id": "availability.sco:aberdeen",
            "path": "availability/aberdeen.json",
            "rows": len(availability_payload.get("entries", [])),
            "checksum": availability_info["checksum"],
            "season": target_season,
        }
    )

    try:
        matchday_payload = build_matchday_payload(
            season=target_season,
            generated_at=generated_at,
            matches=matches,
            all_matches=all_matches,
            tables=tables,
            squad_data=squad_data,
            availability=availability_payload,
        )
    except Exception as error:  # noqa: BLE001 - matchday must not fail the publish
        matchday_payload = fallback_matchday_payload(
            previous_matchday,
            generated_at=generated_at,
            season=target_season,
            reason=f"matchday_build_failed:{type(error).__name__}",
        )
    matchday_info = _write(temp / "matchday" / "upcoming.json", matchday_payload)
    written.append(matchday_info)
    marts.append(
        {
            "id": "matchday.upcoming",
            "path": "matchday/upcoming.json",
            "rows": 1,
            "checksum": matchday_info["checksum"],
            "season": target_season,
        }
    )

    transfer_rows = published_transfers()
    transfer_valuation = value_transfers(
        transfer_rows,
        birth_dates=_valuation_birth_dates(),
        markets=(history_markets() or {}).get("markets", []),
        fx=((transfer_policy_config() or {}).get("valuation") or {}).get("fx_to_gbp"),
    )
    transfers_payload = _transfers_payload(
        transfer_rows,
        target_season,
        player_index,
        valuation=transfer_valuation,
    )
    transfer_info = _write(temp / "transfers" / "aberdeen.json", transfers_payload)
    written.append(transfer_info)
    marts.append(
        {
            "id": "transfers.sco:aberdeen",
            "path": "transfers/aberdeen.json",
            "rows": len(transfer_rows),
            "checksum": transfer_info["checksum"],
            "season": target_season,
        }
    )

    policy = transfer_policy_config() or {}
    gaps = (transfer_gaps_config() or {}).get("gaps", []) or []
    audit = build_transfer_audit(
        players=list(squad_data.get("players", [])),
        prior_seasons=load_prior_squads(),
        transfers=transfer_rows,
        candidates=load_candidates(),
        gaps=list(gaps),
        config=policy,
        generated_at=generated_at,
    )
    audit_info = _write(temp / "transfers" / "aberdeen.audit.json", audit)
    written.append(audit_info)
    marts.append(
        {
            "id": "transfers-audit.sco:aberdeen",
            "path": "transfers/aberdeen.audit.json",
            "rows": len(audit.get("current_squad_arrivals", []))
            + len(audit.get("prior_departures", [])),
            "checksum": audit_info["checksum"],
            "season": target_season,
        }
    )

    history_payloads = build_history_payloads(
        generated_at=generated_at,
        season=target_season,
        transfers=transfer_rows,
        valuation=transfer_valuation,
    )
    history_info = _write(temp / "history" / "aberdeen.json", history_payloads["index"])
    written.append(history_info)
    marts.append(
        {
            "id": "history.sco:aberdeen",
            "path": "history/aberdeen.json",
            "rows": len(history_payloads["index"].get("seasons", [])),
            "checksum": history_info["checksum"],
            "season": target_season,
        }
    )
    for history_season, history_doc in sorted(history_payloads["seasons"].items()):
        season_info = _write(temp / "history" / "seasons" / f"{history_season}.json", history_doc)
        written.append(season_info)
        marts.append(
            {
                "id": f"history.season.{history_season}",
                "path": f"history/seasons/{history_season}.json",
                "rows": len(history_doc.get("managers", [])),
                "checksum": season_info["checksum"],
                "season": history_season,
            }
        )

    try:
        themes_payload = build_themes_payload(
            season=target_season,
            generated_at=generated_at,
            matches=matches,
            squad_data=squad_data,
            transfers_data=transfers_payload,
            history_index=history_payloads["index"],
            history_season=history_payloads["seasons"].get(target_season),
            availability=availability_payload,
        )
    except Exception as error:  # noqa: BLE001 - internal evidence must not fail the publish
        themes_payload = fallback_themes_payload(
            None,
            generated_at=generated_at,
            season=target_season,
            reason=f"themes_build_failed:{type(error).__name__}",
        )
    rumour_rows = load_rumour_rows()
    try:
        needs_payload = build_needs_payload(
            season=target_season,
            generated_at=generated_at,
            themes=themes_payload,
            availability=availability_payload,
            squad_data=squad_data,
            transfers_data=transfers_payload,
            rumours=rumour_rows,
            team_shapes=load_team_shapes(),
        )
    except Exception as error:  # noqa: BLE001 - needs must not fail the publish
        needs_payload = fallback_needs_payload(
            previous_needs,
            generated_at=generated_at,
            season=target_season,
            reason=f"needs_build_failed:{type(error).__name__}",
        )
    try:
        case_payload = build_case_payload(
            season=target_season,
            generated_at=generated_at,
            matches=matches,
            all_matches=all_matches,
            squad_data=squad_data,
            transfers_data=transfers_payload,
            history_index=history_payloads["index"],
            history_season=history_payloads["seasons"].get(target_season),
            history_seasons=history_payloads["seasons"],
            availability=availability_payload,
        )
    except Exception as error:  # noqa: BLE001 - the case must not fail the publish
        case_payload = fallback_case_payload(
            previous_case,
            generated_at=generated_at,
            season=target_season,
            reason=f"case_build_failed:{type(error).__name__}",
        )
    case_info = _write(temp / "themes" / "aberdeen.json", case_payload)
    written.append(case_info)
    marts.append(
        {
            "id": "case.sco:aberdeen",
            "path": "themes/aberdeen.json",
            "rows": len(case_payload.get("claims", [])),
            "checksum": case_info["checksum"],
            "season": target_season,
        }
    )
    needs_info = _write(temp / "needs" / "aberdeen.json", needs_payload)
    written.append(needs_info)
    marts.append(
        {
            "id": "needs.sco:aberdeen",
            "path": "needs/aberdeen.json",
            "rows": len(needs_payload.get("families", [])),
            "checksum": needs_info["checksum"],
            "season": target_season,
        }
    )

    try:
        xg_payload = build_xg_payload(season=target_season, generated_at=generated_at)
    except Exception as error:  # noqa: BLE001 - fxG must not fail the publish
        xg_payload = fallback_xg_payload(
            previous_xg,
            reason=f"xg_build_failed:{type(error).__name__}",
        )
    if (xg_payload.get("coverage") or {}).get("matches", 0) == 0 and previous_xg:
        xg_payload = fallback_xg_payload(previous_xg, reason="xg_build_returned_no_matches")
    xg_info = _write(temp / "xg" / "aberdeen.json", xg_payload)
    written.append(xg_info)
    marts.append(
        {
            "id": "xg.sco:aberdeen",
            "path": "xg/aberdeen.json",
            "rows": len(xg_payload.get("matches", [])),
            "checksum": xg_info["checksum"],
            "season": target_season,
        }
    )

    try:
        fixture_payloads = build_fixture_payloads(
            generated_at=generated_at,
            xg_payload=xg_payload,
            player_index=player_index,
        )
    except Exception as error:  # noqa: BLE001 - a broken fixture build is visible, not hidden
        fixture_payloads = {
            "schema_version": "1.0.0",
            "generated_at": generated_at,
            "count": 0,
            "fixtures": [],
            "documents": {},
            "state": "unavailable",
            "stale_reason": f"fixture_build_failed:{type(error).__name__}",
        }
    previous_fixtures = _previous_fixture_payloads(target)
    new_page_count = fixture_payloads.get("count", 0) + len(fixture_payloads.get("aliases", []))
    if previous_fixtures and new_page_count < previous_fixtures["count"]:
        previous_fixtures["stale_reason"] = (
            f"new fixture build returned {fixture_payloads.get('count', 0)} pages; "
            f"kept {previous_fixtures['count']}"
        )
        fixture_payloads = previous_fixtures
    fixture_index = {
        "schema_version": fixture_payloads.get("schema_version"),
        "generated_at": fixture_payloads.get("generated_at"),
        "count": fixture_payloads.get("count", 0),
        "fixtures": fixture_payloads.get("fixtures", []),
        "aliases": fixture_payloads.get("aliases", []),
    }
    if fixture_payloads.get("state"):
        fixture_index["state"] = fixture_payloads["state"]
        fixture_index["stale_reason"] = fixture_payloads.get("stale_reason")
    fixtures_info = _write(temp / "fixtures" / "index.json", fixture_index)
    written.append(fixtures_info)
    marts.append(
        {
            "id": "fixtures.sco:aberdeen",
            "path": "fixtures/index.json",
            "rows": fixture_index["count"],
            "checksum": fixtures_info["checksum"],
            "season": target_season,
        }
    )
    for fixture_id, document in sorted(fixture_payloads.get("documents", {}).items()):
        document_info = _write(temp / "matches" / f"{fixture_id}.json", document)
        written.append(document_info)
    marts.append(
        {
            "id": "matches.sco:aberdeen",
            "path": "matches/",
            "rows": fixture_payloads.get("count", 0),
            "checksum": None,
            "season": target_season,
            "row_basis": "one canonical file per played fixture; duplicate aliases separate",
        }
    )

    rumours_data = rumours_payload(
        rumour_rows, target_season, player_index, generated_at=generated_at
    )
    profile_data = profile_payload(rumour_rows, player_index, generated_at=generated_at)
    forum_data = forum_payload(player_index, generated_at=generated_at)
    for relative, payload, mart_id, rows in (
        ("rumours/aberdeen.json", rumours_data, "rumours.sco:aberdeen", len(rumour_rows)),
        ("rumours/profile.json", profile_data, "rumours.profile", profile_data["sample_size"]),
        (
            "forum/afc_chat.json",
            forum_data,
            "forum.afc_chat",
            forum_data["coverage"]["posts_sampled"],
        ),
    ):
        info = _write(temp / relative, payload)
        written.append(info)
        marts.append(
            {
                "id": mart_id,
                "path": relative,
                "rows": rows,
                "checksum": info["checksum"],
                "season": target_season,
            }
        )

    league_cup_summary_data = league_cup_summary()
    scottish_cup_summary_data = scottish_cup_summary()
    league_cup_payload = _league_cup_payload(league_cup_summary_data, target_season)
    scottish_cup_payload = _scottish_cup_payload(scottish_cup_summary_data, target_season)
    competitions_payload = _competitions_index(
        tables, league_cup_payload, scottish_cup_payload, target_season
    )
    for name, payload, rows in (
        ("index", competitions_payload, len(competitions_payload["competitions"])),
        ("league-cup", league_cup_payload, len(league_cup_payload["fixtures"])),
        ("scottish-cup", scottish_cup_payload, len(scottish_cup_payload["fixtures"])),
    ):
        info = _write(temp / "competitions" / f"{name}.json", payload)
        written.append(info)
        marts.append(
            {
                "id": f"competitions.{name}",
                "path": f"competitions/{name}.json",
                "rows": rows,
                "checksum": info["checksum"],
                "season": target_season,
            }
        )

    appearances = load_player_appearances()
    player_match_stats = load_player_match_stats()

    # Provenance contributions are real row counts, never placeholders. A
    # corroborating source is only listed when it contributed rows.
    transfer_source_counts: Counter[str] = Counter()
    for row in transfer_rows:
        urls = " ".join(str(url) for url in row.get("source_urls") or [])
        if "wikipedia.org" in urls:
            transfer_source_counts["wikipedia"] += 1
        if "afc.co.uk" in urls:
            transfer_source_counts["afc_news"] += 1
    history_source_counts = Counter(
        str(source.get("id"))
        for source in (history_payloads["index"].get("sources") or [])
        if source.get("id")
    )
    availability_official = sum(
        1
        for entry in availability_payload.get("entries") or []
        if entry.get("source_id") == "afc_news"
    )
    rumour_official = sum(
        1
        for row in rumour_rows
        if "afc_news" in (row.get("source_types") or [])
        or any("afc.co.uk" in str(url) for url in row.get("source_urls") or [])
    )
    valuation_anchors = int((transfers_payload.get("valuation") or {}).get("anchor_count") or 0)
    team_stats_rows = matches.filter(pl.col("home_shots").is_not_null()).height

    provenance_payload = build_provenance_payload(
        season=target_season,
        generated_at=generated_at,
        contributions={
            "league_results_current": {"football_data_uk": matches.height},
            "league_results_history": {
                "football_data_uk": max(0, all_matches.height - matches.height)
            },
            "league_team_stats": {"football_data_uk": team_stats_rows},
            "cup_fixtures": {
                "api_football": len(league_cup_payload["fixtures"])
                + len(scottish_cup_payload["fixtures"])
            },
            "club_fixtures": {
                "spfl": len(club_payload.get("fixtures", []))
                + len(club_payload.get("recent_results", []))
            },
            "lineups_roles": {"api_football": appearances.height},
            "player_match_stats": {"api_football": player_match_stats.height},
            "event_layer": {"api_football": appearances.height},
            "squad_identity": {"api_football": len(squad_data["players"])},
            "preferred_foot": {
                "wikipedia": int(squad_data["summary"].get("attributes_foot_known") or 0)
            },
            "transfers_candidate": {"api_football": len(load_candidates())},
            "transfer_register": {
                "afc_news": transfer_source_counts["afc_news"],
                "wikipedia": transfer_source_counts["wikipedia"],
            },
            "news": {"afc_news": len(club_payload.get("news", []))},
            "availability": {"afc_news": availability_official},
            "rumours": {"afc_news": rumour_official},
            "forum_signal": {"afc_chat": int(forum_data["coverage"]["posts_sampled"])},
            "history": {
                "afc_news": history_source_counts["afc_news"],
                "wikipedia": history_source_counts["wikipedia"],
            },
            "valuation": {"wikipedia": valuation_anchors},
            "needs": {},
        },
        availability={
            "status": availability_payload["coverage"]["status"],
            "provider_snapshot": (
                availability_payload["coverage"].get("provider_snapshot") or {}
            ).get("status", "unavailable"),
            "reason": (availability_payload["coverage"].get("provider_snapshot") or {}).get(
                "reason"
            ),
        },
    )
    provenance_info = _write(temp / "provenance.json", provenance_payload)
    written.append(provenance_info)
    marts.append(
        {
            "id": "provenance",
            "path": "provenance.json",
            "rows": len(provenance_payload.get("layers", [])),
            "checksum": provenance_info["checksum"],
            "season": target_season,
        }
    )

    team_ids = sorted(
        set(matches["home_team_id"].drop_nulls().to_list())
        | set(matches["away_team_id"].drop_nulls().to_list())
    )
    team_names = {
        row["team_id"]: row["team_name"]
        for row in matches.select(
            pl.col("home_team_id").alias("team_id"),
            pl.col("home_team_name").alias("team_name"),
        )
        .unique()
        .to_dicts()
    }
    team_names.update(
        {
            row["team_id"]: row["team_name"]
            for row in matches.select(
                pl.col("away_team_id").alias("team_id"),
                pl.col("away_team_name").alias("team_name"),
            )
            .unique()
            .to_dicts()
        }
    )
    search = [
        {
            "type": "club",
            "id": team_id,
            "name": team_names.get(team_id, team_id),
            "slug": team_id.split(":", 1)[-1],
        }
        for team_id in team_ids
        if not team_id.startswith("sco:provisional")
    ]
    search.extend(
        {
            "type": "player",
            "id": player["player_key"],
            "name": player["name"],
            "slug": str(player["player_id"]),
            "href": player["href"],
        }
        for player in squad_data["players"]
    )
    search.extend(
        {
            "type": "history-season",
            "id": item["season"],
            "name": f"Aberdeen {item['season']}",
            "slug": item["season"],
            "href": item["href"],
        }
        for item in history_payloads["index"].get("seasons", [])
    )
    search.extend(
        {
            "type": "staff",
            "id": person["person_id"],
            "name": person["name"],
            "slug": person["person_id"],
            "href": "/history/",
        }
        for person in history_payloads["index"].get("staff", [])
        if person.get("person_id")
    )
    matchday_fixture = matchday_payload.get("fixture")
    if matchday_fixture:
        search.append(
            {
                "type": "match",
                "id": matchday_fixture.get("match_id"),
                "name": (
                    f"{matchday_fixture.get('home_team_name')} v "
                    f"{matchday_fixture.get('away_team_name')}"
                ),
                "slug": str(matchday_fixture.get("match_id") or "next"),
                "href": "/matchday/",
            }
        )
    search.append(
        {
            "type": "page",
            "id": "matches",
            "name": "Match record",
            "slug": "matches",
            "href": "/matches/",
        }
    )
    search.extend(
        {
            "type": "match",
            "id": f"fixture:{item['fixture_id']}",
            "name": (
                f"{item.get('home_team_name')} {item.get('home_goals')}-"
                f"{item.get('away_goals')} {item.get('away_team_name')}"
            ),
            "slug": str(item["fixture_id"]),
            "href": item.get("href") or f"/matches/{item['fixture_id']}/",
        }
        for item in fixture_index.get("fixtures", [])
        if item.get("fixture_id") is not None
    )
    if xg_payload.get("matches"):
        search.append(
            {
                "type": "page",
                "id": "analysis-xg",
                "name": "fxG model and aggregates",
                "slug": "analysis-xg",
                "href": "/analysis/xg/",
            }
        )
    search.append(
        {
            "type": "page",
            "id": "sources",
            "name": "Data sources and provenance",
            "slug": "sources",
            "href": "/sources/",
        }
    )
    search.append(
        {
            "type": "page",
            "id": "metrics",
            "name": "Metrics and audit",
            "slug": "metrics",
            "href": "/metrics/",
        }
    )
    if case_payload.get("claims"):
        search.append(
            {
                "type": "page",
                "id": "data-analysis",
                "name": "Data analysis",
                "slug": "analysis",
                "href": "/analysis/",
            }
        )
        search.extend(
            {
                "type": "analysis",
                "id": claim.get("id"),
                "name": claim.get("title") or claim.get("id"),
                "slug": str(claim.get("id") or "claim").replace("_", "-"),
                "href": "/analysis/#claim-" + str(claim.get("id") or "claim").replace("_", "-"),
            }
            for claim in case_payload.get("claims", [])
        )
    if needs_payload.get("families"):
        search.extend(
            [
                {
                    "type": "page",
                    "id": "squad-needs",
                    "name": "Squad needs",
                    "slug": "squad-needs",
                    "href": "/recruitment/#squad-needs",
                },
                {
                    "type": "page",
                    "id": "priority-profiles",
                    "name": "Priority scouting profiles",
                    "slug": "priority-profiles",
                    "href": "/scouting/#priority-profiles",
                },
            ]
        )
    search_info = _write(temp / "search-index.json", search)
    written.append(search_info)
    marts.append(
        {
            "id": "search.index",
            "path": "search-index.json",
            "rows": len(search),
            "checksum": search_info["checksum"],
            "season": target_season,
            "row_basis": "one row per indexed page, theme or player",
        }
    )

    coverage = {
        "season": target_season,
        "competitions": [
            {
                "id": competition["id"],
                "name": competition["name"],
                "matches": int(
                    matches.filter(
                        (pl.col("competition_id") == competition["id"])
                        & (pl.col("season") == target_season)
                        & pl.col("home_goals").is_not_null()
                    ).height
                ),
                "expected_matches": competition["matches_per_season"],
                "coverage": "match",
                "results_source": (
                    matches.filter(pl.col("competition_id") == competition["id"])
                    .get_column("source_id")
                    .unique()
                    .to_list()
                    or [None]
                )[0],
                "team_stats_source": (
                    matches.filter(
                        (pl.col("competition_id") == competition["id"])
                        & pl.col("home_shots").is_not_null()
                    )
                    .get_column("source_id")
                    .unique()
                    .to_list()
                    or [None]
                )[0],
                "events": int(
                    appearances.filter(
                        (pl.col("season") == int(target_season[:4]))
                        & (pl.col("competition") == competition.get("short_name"))
                    )["fixture_id"].n_unique()
                ),
                "player_stats": int(
                    player_match_stats.filter(
                        (pl.col("season") == int(target_season[:4]))
                        & (pl.col("competition") == competition.get("short_name"))
                    ).height
                ),
            }
            for competition in competitions_config()["competitions"]
        ],
        "cups": [
            {
                "id": league_cup_payload["competition_id"],
                "name": league_cup_payload["name"],
                "matches": len(league_cup_payload["fixtures"]),
                "groups": len(league_cup_payload["groups"]),
                "coverage": "match",
                "note": league_cup_payload["status"]["coverage_note"],
            },
            {
                "id": scottish_cup_payload["competition_id"],
                "name": scottish_cup_payload["name"],
                "ties": scottish_cup_payload["coverage"]["licensed_ties"],
                "official_ties": scottish_cup_payload["coverage"]["official_ties"],
                "coverage": scottish_cup_payload["coverage"]["status"],
                "note": scottish_cup_payload["coverage"]["note"],
            },
        ],
        "transfers": {
            "club": "sco:aberdeen",
            "count": len(transfer_rows),
            "confirmed": transfers_payload["summary"]["confirmed"],
            "curated": transfers_payload["summary"]["curated"],
            "note": transfers_payload["coverage"]["note"],
        },
        "squad": {
            "club": "sco:aberdeen",
            "count": len(squad_data["players"]),
            "squad": squad_data["summary"]["squad_size"],
            "loans_out": squad_data["summary"]["loans_out"],
            "stats_unavailable": squad_data["summary"]["stats_unavailable"],
            "note": squad_data["coverage"]["note"],
        },
        "rumours": {
            "club": "sco:aberdeen",
            "count": len(rumour_rows),
            "active": rumours_data["summary"]["by_status"].get("active", 0),
            "note": rumours_data["coverage"]["note"],
        },
        "forum": {
            "source": "afc_chat",
            "topics": forum_data["coverage"]["topics_sampled"],
            "posts": forum_data["coverage"]["posts_sampled"],
            "first_page_only": True,
            "raw_posts_published": False,
            "note": forum_data["coverage"]["note"],
        },
        "history": {
            "club": "sco:aberdeen",
            "seasons": history_payloads["index"]["coverage"].get("seasons_curated"),
            "completed": history_payloads["index"]["coverage"].get("completed_seasons"),
            "staff": len(history_payloads["index"].get("staff", [])),
            "honours": len(history_payloads["index"].get("honours", [])),
            "analytics": history_payloads["index"]["coverage"].get("analytics"),
            "note": history_payloads["index"]["coverage"].get("note"),
        },
        "matchday": {
            "club": "sco:aberdeen",
            "fixture": (matchday_payload.get("fixture") or {}).get("match_id"),
            "opponent": (matchday_payload.get("fixture") or {}).get("opponent_name"),
            "date": (matchday_payload.get("fixture") or {}).get("date"),
            "state": matchday_payload.get("state"),
            "snapshot_at": (matchday_payload.get("coverage") or {})
            .get("snapshot", {})
            .get("generated_at"),
            "lineups": (matchday_payload.get("coverage") or {}).get("lineups"),
            "note": (matchday_payload.get("coverage") or {}).get("note"),
        },
        "case": {
            "club": "sco:aberdeen",
            "season": target_season,
            "state": case_payload.get("state"),
            "count": len(case_payload.get("claims", [])),
            "domains": len({claim.get("domain") for claim in case_payload.get("claims", [])}),
            "benchmark_rows": len((case_payload.get("benchmark") or {}).get("rows") or []),
            "note": (case_payload.get("coverage") or {}).get("note"),
        },
        "xg": {
            "model": (xg_payload.get("model") or {}).get("model_id"),
            "state": xg_payload.get("state", "available"),
            "matches": (xg_payload.get("coverage") or {}).get("matches"),
            "with_fxg": (xg_payload.get("coverage") or {}).get("with_fxg"),
            "with_provider_xg": (xg_payload.get("coverage") or {}).get("with_provider_xg"),
            "evaluation": (xg_payload.get("evaluation") or {}).get("status"),
            "note": (xg_payload.get("coverage") or {}).get("note"),
        },
        "fixtures": {
            "count": fixture_index.get("count", 0),
            "full": sum(
                1 for item in fixture_index.get("fixtures", []) if item.get("depth") == "full"
            ),
            "result": sum(
                1 for item in fixture_index.get("fixtures", []) if item.get("depth") == "result"
            ),
            "score": sum(
                1 for item in fixture_index.get("fixtures", []) if item.get("depth") == "score"
            ),
            "note": (
                "One page per played Cormack-era fixture; depth is the data actually available."
            ),
        },
        "provenance": {
            "layers": len(provenance_payload.get("layers", [])),
            "migration": provenance_payload.get("migration"),
            "availability": provenance_payload.get("availability"),
            "note": provenance_payload.get("notes"),
        },
        "availability": {
            "club": "sco:aberdeen",
            "state": availability_payload.get("state"),
            "coverage": availability_payload.get("coverage"),
            "note": availability_payload.get("notes"),
        },
        "needs": {
            "club": "sco:aberdeen",
            "state": needs_payload.get("state"),
            "summary": needs_payload.get("summary"),
            "coverage": needs_payload.get("coverage"),
            "note": needs_payload.get("notes"),
        },
    }
    coverage_info = _write(temp / "coverage.json", coverage)
    written.append(coverage_info)
    marts.append(
        {
            "id": "coverage",
            "path": "coverage.json",
            "rows": 1,
            "checksum": coverage_info["checksum"],
            "season": target_season,
            "row_basis": "one coverage document",
        }
    )
    seasons_payload = {"seasons": seasons, "current": target_season}
    seasons_info = _write(temp / "seasons.json", seasons_payload)
    written.append(seasons_info)
    marts.append(
        {
            "id": "seasons",
            "path": "seasons.json",
            "rows": len(seasons_payload["seasons"]),
            "checksum": seasons_info["checksum"],
            "season": target_season,
            "row_basis": "one row per published season",
        }
    )

    # Validation and audit run against the complete public corpus, before the
    # manifest. A failed audit blocks the atomic replace below.
    validation_checks = [
        asdict(check)
        for check in (
            validate_matches(matches, season=target_season)
            + validate_tables(tables, season=target_season)
            + validate_published(temp)
        )
    ]
    validation_payload = build_validation_payload(
        checks=validation_checks,
        season=target_season,
        generated_at=generated_at,
        strict=require_validation,
    )
    validation_info = _write(temp / "audit" / "validation.json", validation_payload)
    written.append(validation_info)

    registry = load_registry()
    registry_payload = build_registry_payload(registry)
    registry_info = _write(temp / "metrics" / "registry.json", registry_payload)
    written.append(registry_info)

    corpus = load_corpus(temp)
    audit_payload = build_audit(
        corpus=corpus,
        registry=registry,
        dataset_version=dataset_version,
        generated_at=generated_at,
        season=target_season,
    )
    audit_info = _write(temp / "audit" / "metrics.json", audit_payload)
    written.append(audit_info)
    marts.extend(
        [
            {
                "id": "metrics.registry",
                "path": "metrics/registry.json",
                "rows": len(registry.metrics),
                "checksum": registry_info["checksum"],
                "season": target_season,
                "row_basis": "one row per registered metric",
            },
            {
                "id": "audit.metrics",
                "path": "audit/metrics.json",
                "rows": len(audit_payload["metrics"]),
                "checksum": audit_info["checksum"],
                "season": target_season,
                "row_basis": "one row per audited metric",
            },
            {
                "id": "audit.validation",
                "path": "audit/validation.json",
                "rows": len(validation_payload["checks"]),
                "checksum": validation_info["checksum"],
                "season": target_season,
                "row_basis": "one row per validation check",
            },
            {
                "id": "players.sco:aberdeen",
                "path": "players/",
                "rows": len(squad_data["players"]),
                "checksum": None,
                "season": target_season,
                "row_basis": "one file per squad player",
            },
        ]
    )

    if audit_payload["status"] != "pass":
        errors = "; ".join(audit_payload["errors"][:3])
        raise RuntimeError(f"metric audit failed: {errors}")
    if require_validation and validation_payload["status"] != "pass":
        raise RuntimeError(
            "validation failed: "
            f"{validation_payload['errors']} error(s), "
            f"{validation_payload['warnings']} warning(s)"
        )

    sources = [
        {
            "id": source["id"],
            "name": source["name"],
            "lane": source.get("lane"),
            "status": "ok",
            "rows": source.get("rows", 0),
            "last_verified": source.get("last_verified"),
            "attribution": source.get("attribution"),
            "layers": source.get("primary_layers", []),
            "rows_basis": source.get("rows_basis", "primary contributions only"),
        }
        for source in provenance_payload.get("sources", [])
    ]

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset_version": dataset_version,
        "generated_at": generated_at,
        "season": target_season,
        "profile": profile,
        "sources": sources,
        "provenance": {
            "path": "provenance.json",
            "checksum": provenance_info["checksum"],
            "layers": len(provenance_payload.get("layers", [])),
            "migration": provenance_payload.get("migration"),
            "availability": provenance_payload.get("availability"),
        },
        "marts": marts,
        "validation": {
            "status": validation_payload["status"],
            "report": "audit/validation.json",
            "checksum": validation_info["checksum"],
            "generated_at": validation_payload["generated_at"],
            "season": validation_payload["season"],
            "strict": validation_payload["strict"],
            "errors": validation_payload["errors"],
            "warnings": validation_payload["warnings"],
            "checks": len(validation_payload["checks"]),
        },
        "metrics": {
            "registry_path": "metrics/registry.json",
            "registry_checksum": registry_checksum(registry),
            "registry_version": registry.registry_version,
            "registry_reviewed": registry.reviewed.isoformat(),
            "audit_path": "audit/metrics.json",
            "audit_checksum": audit_info["checksum"],
            "status": audit_payload["status"],
            "metrics_total": audit_payload["summary"]["metrics_total"],
            "metrics_passed": audit_payload["summary"]["metrics_passed"],
            "metrics_failed": audit_payload["summary"]["metrics_failed"],
            "parameters_total": audit_payload["summary"]["parameters_total"],
            "parameters_passed": audit_payload["summary"]["parameters_passed"],
            "parameters_failed": audit_payload["summary"]["parameters_failed"],
            "verification_modes": audit_payload["summary"]["verification_modes"],
            "provenance_only": audit_payload["summary"]["provenance_only"],
            "audited_at": audit_payload["audited_at"],
            "allowlist": audit_payload["allowlist"],
        },
        "coverage": coverage,
        "files": [
            {
                "path": str(Path(info["path"]).relative_to(temp)),
                "bytes": info["bytes"],
                "checksum": info["checksum"],
            }
            for info in written
        ],
    }
    manifest_info = _write(temp / "manifest.json", manifest)
    written.append(manifest_info)

    # Atomic replace. Restore the previous directory if the rename fails.
    old = target.with_name(target.name + ".old")
    if old.exists():
        shutil.rmtree(old)
    if target.exists():
        target.rename(old)
    try:
        temp.rename(target)
    except Exception:
        if old.exists() and not target.exists():
            old.rename(target)
        raise
    if old.exists():
        shutil.rmtree(old)

    total_bytes = sum(int(info["bytes"]) for info in written)
    return PublishReport(
        out=str(target),
        season=target_season,
        files=len(written),
        bytes=total_bytes,
        dataset_version=dataset_version,
        manifest=manifest,
    )
