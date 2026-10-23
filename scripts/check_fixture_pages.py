#!/usr/bin/env python3
"""Check every played-fixture document and every built match page.

The dynamic match route is guarded here rather than in the literal-path web
contract checker. Every played fixture must have a document, a page, the required
visible markers, a score that matches the feed, a summary whose numbers appear in
the payload, and no banned verdict language.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

from fitba.publish.fixture import FixtureDocument, fixture_page_schema

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data" / "generated"
OUT = ROOT / "web" / "out"
INDEX = DATA / "fixtures" / "index.json"
MATCHES = DATA / "matches"
SCHEMA = ROOT / "contracts" / "fixture-page.schema.json"
SUMMARY_BANNED = re.compile(
    r"\b(?:deserved|dominated|lucky|should have won|bottled|collapse|disgrace|hero|villain)\b",
    re.IGNORECASE,
)
NUMBER = re.compile(r"\d+(?:\.\d+)?")
REQUIRED_MARKERS = {
    "match.header": 1,
    "match.scoreboard": 1,
    "match.scoreboard.side": 2,
    "match.team-key": 1,
    "match.summary": 1,
    "match.stats": 1,
    "match.xg": 1,
    "match.timeline": 1,
    "match.lineup": 2,
    "match.player-stats": 1,
    "match.coverage": 1,
    "match.links": 1,
}


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment)).strip()


def _h1(page: str) -> str:
    match = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.DOTALL | re.IGNORECASE)
    return _text(match.group(1)) if match else ""


def _marker_count(page: str, marker: str) -> int:
    return len(re.findall(rf'data-contract="{re.escape(marker)}"', page))


def _goal_key(item: dict) -> tuple:
    return (
        item.get("side"),
        item.get("minute"),
        item.get("extra_minute"),
        item.get("player_name"),
        bool(item.get("is_penalty")),
        bool(item.get("is_own_goal")),
    )


def _card_key(item: dict) -> tuple:
    return (
        item.get("side"),
        item.get("minute"),
        item.get("extra_minute"),
        item.get("player_name"),
        item.get("card_type"),
    )


def _expected_depth(coverage: dict) -> str:
    events = bool(coverage.get("events"))
    lineups = bool(coverage.get("lineups"))
    team_stats = bool(coverage.get("team_stats"))
    player_stats = bool(coverage.get("player_stats"))
    if events and lineups and team_stats and player_stats:
        return "full"
    if events and lineups:
        return "result"
    if events or lineups or team_stats or player_stats:
        return "partial"
    return "score"


def _validate_scoreboard(document: dict, fixture_id: int, errors: list[str]) -> None:
    fixture = document.get("fixture") or {}
    board = document.get("scoreboard") or {}
    timeline = document.get("timeline") or []
    home = board.get("home") or {}
    away = board.get("away") or {}
    if home.get("side") != "home" or away.get("side") != "away":
        errors.append(f"{fixture_id}: scoreboard sides are not home/away")
    if home.get("team_id") != fixture.get("home_team_id"):
        errors.append(f"{fixture_id}: scoreboard home team id mismatch")
    if away.get("team_id") != fixture.get("away_team_id"):
        errors.append(f"{fixture_id}: scoreboard away team id mismatch")
    aberdeen_sides = [side.get("side") for side in (home, away) if bool(side.get("is_aberdeen"))]
    if aberdeen_sides != ["home"] and aberdeen_sides != ["away"]:
        errors.append(f"{fixture_id}: scoreboard must mark exactly one Aberdeen side")

    for side_name, side in (("home", home), ("away", away)):
        for goal in side.get("goals") or []:
            if goal.get("side") != side_name:
                errors.append(f"{fixture_id}: {side_name} goal has the wrong side")
            if goal.get("team_name") != side.get("team_name"):
                errors.append(f"{fixture_id}: {side_name} goal has the wrong team name")
        for card in side.get("red_cards") or []:
            if card.get("side") != side_name:
                errors.append(f"{fixture_id}: {side_name} red card has the wrong side")
            if card.get("card_type") not in {"straight_red", "second_yellow"}:
                errors.append(f"{fixture_id}: invalid red-card type {card.get('card_type')!r}")

    events_available = bool(board.get("events_available"))
    if not events_available and (
        home.get("goals") or away.get("goals") or home.get("red_cards") or away.get("red_cards")
    ):
        errors.append(f"{fixture_id}: unavailable event feed has scoreboard events")
    goals_complete = bool(board.get("goals_complete"))
    home_goals = fixture.get("home_goals")
    away_goals = fixture.get("away_goals")
    if goals_complete:
        if len(home.get("goals") or []) != home_goals:
            errors.append(f"{fixture_id}: complete home goal count does not match score")
        if len(away.get("goals") or []) != away_goals:
            errors.append(f"{fixture_id}: complete away goal count does not match score")
        reconciliation = (document.get("summary") or {}).get("reconciliation") or {}
        if not reconciliation.get("matched"):
            errors.append(f"{fixture_id}: complete scoreboard has an unreconciled summary")

    expected_shootout = None
    if fixture.get("home_penalties") is not None and fixture.get("away_penalties") is not None:
        expected_shootout = {
            "home": fixture["home_penalties"],
            "away": fixture["away_penalties"],
        }
    if board.get("shootout") != expected_shootout:
        errors.append(f"{fixture_id}: scoreboard shootout does not match the fixture")

    timeline_goals = [
        row
        for row in timeline
        if row.get("is_goal") and not row.get("is_shootout") and row.get("beneficiary_side")
    ]
    scoreboard_goals = [
        goal for side in (home, away) for goal in (side.get("goals") or []) if goal.get("side")
    ]
    if sorted(_goal_key(item) for item in timeline_goals) != sorted(
        _goal_key(item) for item in scoreboard_goals
    ):
        errors.append(f"{fixture_id}: scoreboard goals do not match the timeline")

    timeline_cards = [
        row
        for row in timeline
        if row.get("is_red_card") and row.get("side") and row.get("card_type")
    ]
    scoreboard_cards = [card for side in (home, away) for card in (side.get("red_cards") or [])]
    if sorted(_card_key(item) for item in timeline_cards) != sorted(
        _card_key(item) for item in scoreboard_cards
    ):
        errors.append(f"{fixture_id}: scoreboard red cards do not match the timeline")

    home_score = 0
    away_score = 0
    for row in timeline:
        if row.get("is_second_yellow") and not row.get("is_red_card"):
            errors.append(f"{fixture_id}: second yellow is not marked red")
        if row.get("card_type") == "second_yellow" and not row.get("is_second_yellow"):
            errors.append(f"{fixture_id}: second-yellow card type disagrees with flags")
        if row.get("card_type") == "straight_red" and row.get("is_second_yellow"):
            errors.append(f"{fixture_id}: straight red marked second yellow")
        if row.get("beneficiary_side") is not None and not (
            row.get("is_goal") and not row.get("is_shootout")
        ):
            errors.append(f"{fixture_id}: non-goal has a beneficiary side")
        score = row.get("score_after") or {}
        current_home = int(score.get("home") or 0)
        current_away = int(score.get("away") or 0)
        if current_home < home_score or current_away < away_score:
            errors.append(f"{fixture_id}: timeline score decreases")
        home_score, away_score = current_home, current_away
    if goals_complete and (home_score, away_score) != (home_goals, away_goals):
        errors.append(f"{fixture_id}: complete timeline does not end at the final score")

    summary = document.get("summary") or {}
    summary_text = " ".join(
        [str(summary.get("headline") or "")]
        + [str(item.get("text") or "") for item in summary.get("bullets") or []]
    )
    if not summary.get("events_available") and "records 0 goals" in summary_text:
        errors.append(f"{fixture_id}: unavailable event feed is described as 0 goals")
    if (
        fixture.get("home_penalties") is not None
        and fixture.get("away_penalties") is not None
        and "penalties" not in str(summary.get("headline") or "").casefold()
    ):
        errors.append(f"{fixture_id}: shootout headline does not name the penalty result")
    if (
        home_goals is not None
        and away_goals is not None
        and abs(int(home_goals) - int(away_goals)) > 1
        and "win it late" in summary_text.casefold()
    ):
        errors.append(f"{fixture_id}: multi-goal margin described as a late win")
    for row in (document.get("stats") or {}).get("rows") or []:
        if row.get("key") == "goals_prevented" and row.get("basis") == "measured":
            errors.append(f"{fixture_id}: goals prevented is labelled measured")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-path", default="", help="Base path used for links")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    errors: list[str] = []
    warnings: list[str] = []

    if not INDEX.exists():
        print(f"error: missing {INDEX}")
        return 1
    if (
        not SCHEMA.exists()
        or json.loads(SCHEMA.read_text(encoding="utf-8")) != fixture_page_schema()
    ):
        errors.append("contracts/fixture-page.schema.json is stale")
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    rows = index.get("fixtures") or []
    alias_rows = index.get("aliases") or []
    if index.get("count") != len(rows):
        errors.append("fixtures/index.json count does not match its rows")
    scheduled = index.get("scheduled") or []
    if int(index.get("scheduled_count") or 0) != len(scheduled):
        errors.append("fixtures/index.json scheduled_count does not match its rows")
    played_ids = {str(row.get("fixture_id")) for row in rows}
    scheduled_ids = {str(row.get("fixture_id")) for row in scheduled}
    if played_ids & scheduled_ids:
        errors.append("fixtures/index.json schedules a played fixture")
    for row in scheduled:
        if row.get("href"):
            errors.append("scheduled fixture must not have a page link")
        if not row.get("date") or not row.get("competition_id"):
            errors.append("scheduled fixture is missing date or competition")
        if row.get("status") not in {
            "scheduled",
            "conflict_review",
            "postponed",
            "cancelled",
            "abandoned",
            "unknown",
        }:
            errors.append("scheduled fixture has an invalid status")
    if not rows:
        errors.append("fixtures/index.json has no played fixtures")

    document_ids = {int(path.stem) for path in MATCHES.glob("*.json") if path.stem.isdigit()}
    index_ids = {int(row["fixture_id"]) for row in rows if row.get("fixture_id") is not None}
    alias_ids = {int(row["fixture_id"]) for row in alias_rows if row.get("fixture_id") is not None}
    missing_docs = (index_ids | alias_ids) - document_ids
    extra_docs = document_ids - (index_ids | alias_ids)
    if missing_docs:
        errors.append(f"missing fixture documents: {sorted(missing_docs)[:5]}")
    if extra_docs:
        warnings.append(f"documents without index rows: {sorted(extra_docs)[:5]}")
    seen_signatures: dict[tuple, int] = {}
    for row in rows:
        signature = (
            row.get("date"),
            row.get("competition_id"),
            tuple(sorted([str(row.get("home_team_name")), str(row.get("away_team_name"))])),
        )
        if signature in seen_signatures:
            errors.append(
                f"{row.get('fixture_id')}: duplicate fixture signature of "
                f"{seen_signatures[signature]}"
            )
        seen_signatures[signature] = int(row["fixture_id"])

    for alias in alias_rows:
        alias_id = int(alias["fixture_id"])
        document_path = MATCHES / f"{alias_id}.json"
        if not document_path.exists():
            errors.append(f"{alias_id}: missing alias document")
            continue
        document = json.loads(document_path.read_text(encoding="utf-8"))
        document_fixture = document.get("fixture") or {}
        if document_fixture.get("duplicate_of") != alias.get("canonical_href"):
            errors.append(f"{alias_id}: alias does not point to its canonical page")
        alias_page = args.out / "matches" / str(alias_id) / "index.html"
        if not alias_page.exists():
            errors.append(f"{alias_id}: missing alias page")
        elif 'data-contract="match.duplicate"' not in alias_page.read_text(encoding="utf-8"):
            errors.append(f"{alias_id}: alias page has no duplicate notice")

    out_matches = args.out / "matches"
    index_page = out_matches / "index.html"
    if not index_page.exists():
        errors.append(f"missing built match index {index_page}")
        index_html = ""
    else:
        index_html = index_page.read_text(encoding="utf-8")

    base = args.base_path.rstrip("/")
    dash = chr(8211)
    checked = 0

    # The match index renders one season at a time, defaulting to the current
    # season. Its default HTML therefore links only that season's fixture
    # pages; the earlier seasons are selected client-side. Require the selector
    # to name every season, and keep the link assertion for the default season.
    # The per-page checks below still cover every fixture in every season.
    seasons = sorted({row.get("season") for row in rows if row.get("season")})
    default_season = seasons[-1] if seasons else ""
    if index_html:
        for season in seasons:
            if season not in index_html:
                errors.append(f"match index season selector does not list {season}")
    for row in rows:
        fixture_id = int(row["fixture_id"])
        document_path = MATCHES / f"{fixture_id}.json"
        if not document_path.exists():
            continue
        document = json.loads(document_path.read_text(encoding="utf-8"))
        try:
            FixtureDocument.model_validate(document)
        except Exception as error:  # noqa: BLE001 - report the schema failure
            errors.append(f"{fixture_id}: document schema: {error}")
            continue
        _validate_scoreboard(document, fixture_id, errors)
        coverage = document.get("coverage") or {}
        expected_depth = _expected_depth(coverage)
        if document.get("depth") != expected_depth:
            errors.append(f"{fixture_id}: depth {document.get('depth')!r} != {expected_depth!r}")
        fixture = document.get("fixture") or {}
        if fixture.get("fixture_id") != fixture_id:
            errors.append(f"{fixture_id}: document fixture_id mismatch")
        if (
            fixture.get("competition_id") == "sco:scottish-cup"
            and "scottish cup" not in str(fixture.get("competition_name") or "").casefold()
        ):
            errors.append(f"{fixture_id}: Scottish Cup has a non-canonical label")
        expected_href = f"{base}/matches/{fixture_id}/"
        if row.get("href") != f"/matches/{fixture_id}/":
            errors.append(f"{fixture_id}: index href is not canonical")
        if index_html and row.get("season") == default_season and expected_href not in index_html:
            errors.append(f"{fixture_id}: match index does not link the default-season page")

        page_path = out_matches / str(fixture_id) / "index.html"
        if not page_path.exists():
            errors.append(f"{fixture_id}: missing built page {page_path}")
            continue
        page = page_path.read_text(encoding="utf-8")
        for marker, minimum in REQUIRED_MARKERS.items():
            count = _marker_count(page, marker)
            if count < minimum:
                errors.append(f"{fixture_id}: {marker} count {count} < {minimum}")
        if page.count('data-team-split="aberdeen-opponent"') < 6:
            errors.append(f"{fixture_id}: fewer than six Aberdeen/opposition splits")
        if 'data-team="aberdeen"' not in page:
            errors.append(f"{fixture_id}: no Aberdeen data-team marker")
        if 'data-team="opponent"' not in page:
            errors.append(f"{fixture_id}: no opponent data-team marker")
        xg = document.get("xg") or {}
        if (
            xg.get("available")
            and xg.get("gate_passed") is False
            and _marker_count(page, "match.xg.gate") < 1
        ):
            errors.append(f"{fixture_id}: fxG gate failure is not shown on the page")

        title = _h1(page)
        if "?" in title:
            errors.append(f"{fixture_id}: H1 is a question")
        home_goals = fixture.get("home_goals")
        away_goals = fixture.get("away_goals")
        if (
            home_goals is not None
            and away_goals is not None
            and f"{home_goals}{dash}{away_goals}" not in title
            and f"{home_goals}-{away_goals}" not in title
        ):
            errors.append(f"{fixture_id}: H1 does not carry the scoreline: {title!r}")

        summary = document.get("summary") or {}
        summary_text = " ".join(
            [str(summary.get("headline") or "")]
            + [str(item.get("text") or "") for item in summary.get("bullets") or []]
        )
        if SUMMARY_BANNED.search(summary_text):
            errors.append(f"{fixture_id}: banned summary phrase")
        payload_text = json.dumps(document, ensure_ascii=False)
        for token in NUMBER.findall(summary_text):
            if token not in payload_text:
                errors.append(f"{fixture_id}: summary number {token!r} is not in the payload")

        coverage = document.get("coverage") or {}
        if coverage.get("depth") != document.get("depth"):
            errors.append(f"{fixture_id}: coverage depth does not match document depth")
        if not document.get("summary"):
            errors.append(f"{fixture_id}: summary is empty")
        checked += 1

    for warning in warnings:
        print(f"warning: {warning}")
    for error in errors:
        print(f"error: {error}")
    print(
        f"{'FAIL' if errors else 'PASS'} fixture-page check: "
        f"{checked} pages, {len(errors)} error(s), {len(warnings)} warning(s)"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
