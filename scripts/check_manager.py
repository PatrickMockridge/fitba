#!/usr/bin/env python3
"""CI guard for the dedicated manager surface.

Payload mode proves the published manager state is unambiguous and reconciles
the history register, the current season document, the aims and the gated
next-manager market. Page mode proves the built `/manager/` page keeps the
contracted sections, columns, labels and links visible, and that it does not
duplicate the odds table or publish a pressure verdict.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "web" / "data" / "generated"
OUT = ROOT / "web" / "out"
HISTORY = GENERATED / "history" / "aberdeen.json"
SEASON_DIR = GENERATED / "history" / "seasons"
ANALYSIS = GENERATED / "analysis" / "summary.json"
MARKET = GENERATED / "rumours" / "manager-market.json"
XG = GENERATED / "xg" / "aberdeen.json"
CLUB = GENERATED / "clubs" / "aberdeen.json"
DONSTALK = GENERATED / "forum" / "donstalk.json"

MARKERS = [
    "manager.hero",
    "manager.situation",
    "manager.expectations",
    "manager.aims",
    "manager.record",
    "manager.season-record",
    "manager.xg",
    "manager.churn",
    "manager.news",
    "manager.rumours",
    "manager.coverage",
]
COLUMNS = {
    "manager.aims": ["Aim", "Target", "Current", "Status", "Gap"],
    "manager.record": ["Manager", "Dates", "Pld", "W-D-L", "GF", "GA", "Pts", "PPG"],
    "manager.season-record": [
        "Manager",
        "Dates",
        "Pld",
        "W-D-L",
        "GF",
        "GA",
        "Pts",
        "PPG",
    ],
    "manager.churn": [
        "Manager",
        "Dates",
        "Reason",
        "Pld",
        "W-D-L",
        "GF",
        "GA",
        "Pts",
        "PPG",
    ],
}
REQUIRED_LINKS = [
    "/history/",
    "/analysis/",
    "/analysis/xg/",
    "/rumours/",
    "/news/",
    "/claims/",
    "/methodology/",
    "/sources/",
]
REQUIRED_COPY = [
    "The manager record",
    "Analyst-set, not a published club target",
    "League only",
    "Measured context, not a manager rating",
    "zero sample, not a zero-performance verdict",
    "Not betting advice",
]
FORBIDDEN_COPY = [
    "under pressure",
    "must go",
    "should be sacked",
    "has to go",
    "lost the dressing room",
    "out of his depth",
    "dead man walking",
]


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _norm(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def _manager_stints(history: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {**stint, "name": person.get("name")}
        for person in history.get("staff") or []
        for stint in person.get("stints") or []
        if stint.get("role_group") == "manager"
    ]


def _payload_errors() -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    state: dict[str, Any] = {}
    for path in (HISTORY, ANALYSIS):
        if not path.exists():
            return [f"missing {path}; run `uv run fitba publish`"], state
    history = _load(HISTORY)
    analysis = _load(ANALYSIS)
    season = str(analysis.get("season") or "")
    season_path = SEASON_DIR / f"{season}.json"
    if not season_path.exists():
        return [f"missing {season_path}; run `uv run fitba publish`"], state
    season_doc = _load(season_path)

    stints = _manager_stints(history)
    current = [stint for stint in stints if not stint.get("end")]
    permanent = [stint for stint in current if not stint.get("interim")]
    interim = [stint for stint in current if stint.get("interim")]
    state.update(
        season=season,
        season_doc=season_doc,
        stints=stints,
        current=current,
        permanent=permanent,
        interim=interim,
    )
    if len(permanent) > 1:
        errors.append("more than one current permanent manager")
    if len(interim) > 1:
        errors.append("more than one current interim manager")
    if not permanent and not interim:
        errors.append("no permanent manager and no interim manager are recorded")

    register = {
        (person.get("person_id"), stint.get("stint_id"))
        for person in history.get("staff") or []
        for stint in person.get("stints") or []
        if stint.get("role_group") == "manager"
    }
    managers = season_doc.get("managers") or []
    if not managers:
        errors.append(f"{season} has no manager segment")
    for row in managers:
        if (row.get("person_id"), row.get("stint_id")) not in register:
            errors.append(
                f"{season} manager {row.get('name')!r} does not resolve to the staff register"
            )
        played = int(row.get("played") or 0)
        won = int(row.get("won") or 0)
        drawn = int(row.get("drawn") or 0)
        lost = int(row.get("lost") or 0)
        points = int(row.get("points") or 0)
        if played != won + drawn + lost:
            errors.append(
                f"{season} manager {row.get('name')!r} played {played} != W+D+L "
                f"{won + drawn + lost}"
            )
        if points != 3 * won + drawn:
            errors.append(
                f"{season} manager {row.get('name')!r} points {points} != 3W+D {3 * won + drawn}"
            )
        if played == 0 and row.get("ppg") is not None:
            errors.append(f"{season} manager {row.get('name')!r} has a PPG on a zero-match sample")

    aims = analysis.get("aims") or []
    league_aim = next((aim for aim in aims if str(aim.get("id")) == "league"), None)
    if league_aim is None:
        errors.append("analysis.summary has no league aim")
    else:
        note = _norm(league_aim.get("note"))
        baseline = _norm((season_doc.get("expectations") or {}).get("baseline"))
        if "analyst-set" not in note:
            errors.append("league aim is not labelled analyst-set")
        if baseline and baseline not in note:
            errors.append("league aim does not carry the season expectations baseline")

    if MARKET.exists():
        market_doc = _load(MARKET)
        market = market_doc.get("market") or {}
        gate = market.get("gate") or {}
        expected_open = len(current) == 1 and bool(current[0].get("interim"))
        if bool(gate.get("is_open")) != expected_open:
            errors.append("manager market gate does not match the published staff register")
        if expected_open:
            if gate.get("interim_manager") != current[0].get("name"):
                errors.append("manager market interim manager does not match the staff register")
            if str(gate.get("interim_since") or "")[:10] != str(current[0].get("start") or "")[:10]:
                errors.append("manager market interim start does not match the staff register")
        elif permanent and gate.get("permanent_manager") != permanent[0].get("name"):
            errors.append("manager market permanent manager does not match the staff register")

    corpus_text = " ".join(
        [
            str((history.get("era") or {}).get("read") or ""),
            *[
                str(pillar.get("statement") or "")
                for pillar in (history.get("era") or {}).get("pillars") or []
            ],
            str(season_doc.get("headline") or ""),
            str(season_doc.get("interim_read") or ""),
            *[
                str(value)
                for value in (season_doc.get("expectations") or {}).values()
                if isinstance(value, str)
            ],
            *[str(aim.get("note") or "") for aim in aims],
        ]
    ).casefold()
    for phrase in FORBIDDEN_COPY:
        if phrase in corpus_text:
            errors.append(f"manager-specific published copy contains {phrase!r}")

    return errors, state


def _normalised_href(href: str, base_path: str) -> str:
    if not href or href.startswith(("http://", "https://", "#", "mailto:", "tel:")):
        return ""
    path = href.split("?", 1)[0].split("#", 1)[0]
    if base_path and path.startswith(base_path):
        path = path[len(base_path) :]
    return path


def _page_errors(out: Path, base_path: str) -> tuple[list[str], int]:
    errors: list[str] = []
    page = out / "manager" / "index.html"
    if not page.exists():
        return [f"missing built page {page}"], 0
    html = page.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    payload_errors, state = _payload_errors()
    errors.extend(payload_errors)

    if soup.select_one('[data-contract-page="manager"]') is None:
        errors.append('missing data-contract-page="manager"')
    if soup.select_one('[data-contract-state="full"]') is None:
        errors.append("manager page is not in the full state")
    for marker in MARKERS:
        if soup.select_one(f'[data-contract="{marker}"]') is None:
            errors.append(f"missing marker {marker}")

    for marker, headers in COLUMNS.items():
        element = soup.select_one(f'[data-contract="{marker}"]')
        if element is None:
            continue
        table = element.find("table")
        if table is None:
            errors.append(f"{marker}: no table")
            continue
        actual = [cell.get_text(" ", strip=True) for cell in table.find_all("th")]
        for header in headers:
            if header not in actual:
                errors.append(f"{marker}: missing column {header!r}")

    text = soup.get_text(" ", strip=True)
    normalised = _norm(text)
    for phrase in REQUIRED_COPY:
        if _norm(phrase) not in normalised:
            errors.append(f"missing required copy {phrase!r}")
    for phrase in FORBIDDEN_COPY:
        if phrase in normalised:
            errors.append(f"forbidden manager copy {phrase!r}")

    links = {
        _normalised_href(str(anchor.get("href") or ""), base_path) for anchor in soup.find_all("a")
    }
    for link in REQUIRED_LINKS:
        if link not in links:
            errors.append(f"missing required link {link}")

    if soup.select_one('[data-contract="rumours.manager-market"]') is not None:
        errors.append("manager page duplicates the gated market panel")
    if any(
        cell.get_text(" ", strip=True).casefold() == "fractional" for cell in soup.find_all("th")
    ):
        errors.append("manager page duplicates the odds table")

    if XG.exists():
        xg = _load(XG)
        season = state.get("season")
        rows = [row for row in xg.get("manager_splits") or [] if str(row.get("season")) == season]
        if rows and soup.select_one('[data-contract="xg.managers"]') is None:
            errors.append("xG manager rows exist but the xG manager table is missing")

    season_doc = state.get("season_doc") or {}
    expectations = season_doc.get("expectations") or {}
    club_urls = [
        url
        for url in expectations.get("source_urls") or []
        if isinstance(url, str) and "afc.co.uk" in url
    ]
    if club_urls and club_urls[0] not in html:
        errors.append("club statement URL is not linked")

    if DONSTALK.exists():
        donstalk = _load(DONSTALK)
        thread = next(
            (
                topic
                for topic in donstalk.get("topics") or []
                if _norm(topic.get("title")) == "next manager"
            ),
            None,
        )
        if thread and str(thread.get("url") or "") not in html:
            errors.append("DonsTalk Next manager thread is not linked")

    title = soup.title.get_text(" ", strip=True) if soup.title is not None else ""
    if "manager" not in title.casefold():
        errors.append("page title does not contain 'manager'")
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = str(description_tag.get("content") or "") if description_tag else ""
    if "aberdeen" not in description.casefold():
        errors.append("meta description does not contain 'Aberdeen'")

    return errors, 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", action="store_true", help="check the built static export")
    parser.add_argument("--out", type=Path, default=OUT, help="built export directory")
    parser.add_argument("--base-path", default="", help="static-export base path, e.g. /fitba")
    args = parser.parse_args()
    base_path = args.base_path.rstrip("/")

    if args.pages:
        errors, checked = _page_errors(args.out, base_path)
        label = f"Manager page check ({checked} page)"
    else:
        errors, state = _payload_errors()
        label = (
            "Manager payload check "
            f"({state.get('season')}, "
            f"{len(state.get('current') or [])} current manager stint(s))"
        )
    for error in errors:
        print(f"  - {error}")
    if errors:
        print(f"{label} failed ({len(errors)} error(s))")
        return 1
    print(f"{label} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
