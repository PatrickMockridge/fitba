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
    if index.get("count") != len(rows):
        errors.append("fixtures/index.json count does not match its rows")
    if not rows:
        errors.append("fixtures/index.json has no played fixtures")

    document_ids = {int(path.stem) for path in MATCHES.glob("*.json") if path.stem.isdigit()}
    index_ids = {int(row["fixture_id"]) for row in rows if row.get("fixture_id") is not None}
    missing_docs = index_ids - document_ids
    extra_docs = document_ids - index_ids
    if missing_docs:
        errors.append(f"missing fixture documents: {sorted(missing_docs)[:5]}")
    if extra_docs:
        warnings.append(f"documents without index rows: {sorted(extra_docs)[:5]}")

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
        fixture = document.get("fixture") or {}
        if fixture.get("fixture_id") != fixture_id:
            errors.append(f"{fixture_id}: document fixture_id mismatch")
        expected_href = f"{base}/matches/{fixture_id}/"
        if row.get("href") != f"/matches/{fixture_id}/":
            errors.append(f"{fixture_id}: index href is not canonical")
        if index_html and expected_href not in index_html:
            errors.append(f"{fixture_id}: match index does not link the page")

        page_path = out_matches / str(fixture_id) / "index.html"
        if not page_path.exists():
            errors.append(f"{fixture_id}: missing built page {page_path}")
            continue
        page = page_path.read_text(encoding="utf-8")
        for marker, minimum in REQUIRED_MARKERS.items():
            count = _marker_count(page, marker)
            if count < minimum:
                errors.append(f"{fixture_id}: {marker} count {count} < {minimum}")

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
