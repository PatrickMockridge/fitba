#!/usr/bin/env python3
"""Validate the per-fixture broadcast document and its curated source."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from fitba.publish.broadcast import BroadcastDocument, broadcast_schema

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data" / "generated"
DOCUMENT = DATA / "broadcast.json"
FIXTURES = DATA / "fixtures" / "index.json"
POLICY = ROOT / "config" / "broadcast.yaml"
REFERENCE = ROOT / "reference" / "broadcast.yaml"
SCHEMA = ROOT / "contracts" / "broadcast.schema.json"
FORBIDDEN = re.compile(
    r"£|\bprice\b|\bpricing\b|\bsubscribe\b|\bsubscription\b|\bfree(?:-to-air)?\b|"
    r"watch here|click here|sign up|\.m3u8|stream_url",
    re.IGNORECASE,
)
REGION_STATUSES = {"confirmed", "blackout_window", "not_announced", "unknown"}
INTERNATIONAL_STATUSES = {"confirmed", "not_announced", "unknown"}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy(value: Any) -> str:
    return " ".join(str(value or "").split())


def _is_blackout(row: dict[str, Any]) -> bool:
    value = str(row.get("date") or "")
    kickoff = str(row.get("kickoff") or "")
    if not value or not kickoff:
        return False
    try:
        return date.fromisoformat(value).weekday() == 5 and kickoff == "15:00"
    except ValueError:
        return False


def _numeric_leaves(node: Any) -> list[str]:
    if isinstance(node, bool):
        return []
    if isinstance(node, (int, float)):
        return ["numeric"]
    if isinstance(node, dict):
        return [item for value in node.values() for item in _numeric_leaves(value)]
    if isinstance(node, list):
        return [item for value in node for item in _numeric_leaves(value)]
    return []


def check() -> list[str]:
    errors: list[str] = []
    if not DOCUMENT.exists():
        return ["missing broadcast.json"]
    if not SCHEMA.exists():
        errors.append("missing contracts/broadcast.schema.json")
    elif _load(SCHEMA) != broadcast_schema():
        errors.append("contracts/broadcast.schema.json is stale")
    document = _load(DOCUMENT)
    try:
        BroadcastDocument.model_validate(document)
    except Exception as error:  # noqa: BLE001
        return [f"broadcast document invalid: {error}"]

    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8")) or {}
    reference = yaml.safe_load(REFERENCE.read_text(encoding="utf-8")) or {}
    fixtures = _load(FIXTURES)
    scheduled = {
        str(row.get("fixture_id") or ""): row
        for row in fixtures.get("scheduled") or []
    }
    played = {str(row.get("fixture_id") or "") for row in fixtures.get("fixtures") or []}
    fixture_rows = document.get("fixtures") or []
    rows = {str(row.get("fixture_id")): row for row in fixture_rows}
    if len(rows) != len(fixture_rows):
        errors.append("duplicate fixture rows in broadcast.json")
    if set(rows) != set(scheduled):
        missing = sorted(set(scheduled) - set(rows))[:5]
        extra = sorted(set(rows) - set(scheduled))[:5]
        errors.append(
            "broadcast rows do not match scheduled fixtures; "
            f"missing={missing} extra={extra}"
        )

    copy_values = {_copy(value) for value in (policy.get("copy") or {}).values()}
    allowed_sources = set(policy.get("allowed_source_ids") or [])
    source_hosts = policy.get("source_hosts") or {}
    max_title = int(policy.get("source_max_title_chars") or 160)
    warn_days = int(policy.get("source_warn_after_days") or 30)
    today = date.today()
    for fixture_id, row in rows.items():
        fixture = scheduled.get(fixture_id)
        if fixture is None:
            continue
        for field in (
            "date",
            "kickoff",
            "competition_id",
            "home_team_name",
            "away_team_name",
            "season",
        ):
            if str(row.get(field) or "") != str(fixture.get(field) or ""):
                errors.append(f"{fixture_id}: {field} does not match the scheduled fixture")
        for region_name in ("domestic", "international"):
            region = row.get(region_name) or {}
            status = str(region.get("status") or "")
            allowed = REGION_STATUSES if region_name == "domestic" else INTERNATIONAL_STATUSES
            if status not in allowed:
                errors.append(f"{fixture_id}: invalid {region_name} status {status!r}")
            if _copy(region.get("note")) not in copy_values:
                errors.append(f"{fixture_id}: {region_name} note is not policy copy")
            if region.get("basis") != "official_source" and region.get("outlets"):
                errors.append(f"{fixture_id}: {region_name} outlets on a non-source row")
            if status != "confirmed" and region.get("outlets"):
                errors.append(f"{fixture_id}: {region_name} outlets without confirmed status")
        domestic = row.get("domestic") or {}
        international = row.get("international") or {}
        if domestic.get("status") == "blackout_window":
            if international.get("status") == "blackout_window":
                errors.append(f"{fixture_id}: international cannot be a blackout window")
            if not _is_blackout(fixture):
                errors.append(f"{fixture_id}: blackout window outside Saturday 15:00")
            if domestic.get("outlets"):
                errors.append(f"{fixture_id}: blackout with an outlet")
        if row.get("state") in {"fixture_conflict", "source_conflict"} and (
            domestic.get("status") != "unknown"
            or international.get("status") != "unknown"
        ):
            errors.append(f"{fixture_id}: conflict state must withhold both regions")
        sources = row.get("sources") or []
        if domestic.get("status") == "confirmed" and (
            not sources
            or not any(
                source.get("source_id") in (domestic.get("source_ids") or [])
                and source.get("confidence") == "confirmed"
                for source in sources
            )
        ):
            errors.append(f"{fixture_id}: domestic confirmed without a confirmed source")
        for source in sources:
            url = str(source.get("url") or "")
            host = urlparse(url).hostname or ""
            source_id = str(source.get("source_id") or "")
            if not url.startswith("https://"):
                errors.append(f"{fixture_id}: source URL is not HTTPS")
            if source_id not in allowed_sources:
                errors.append(f"{fixture_id}: unknown source id {source_id}")
            if host not in set(source_hosts.get(source_id) or []):
                errors.append(f"{fixture_id}: host {host} not allowed for {source_id}")
            if len(str(source.get("title") or "")) > max_title:
                errors.append(f"{fixture_id}: source title too long")
            try:
                verified = date.fromisoformat(str(source.get("verified_at") or ""))
                if (today - verified).days > warn_days:
                    print(f"warning: {fixture_id}: source older than {warn_days} days")
            except ValueError:
                errors.append(f"{fixture_id}: invalid verified_at")
    if _numeric_leaves(document):
        errors.append("broadcast.json contains numeric leaves")
    if _copy(document.get("notes")) != _copy((policy.get("copy") or {}).get("document_note")):
        errors.append("document note is not policy copy")
    for text in _strings(document):
        if FORBIDDEN.search(text):
            errors.append(f"forbidden broadcast token in {text!r}")

    curated = reference.get("fixtures") or []
    curated_ids = {str(row.get("fixture_id")) for row in curated}
    for fixture_id in curated_ids - set(scheduled):
        if fixture_id in played:
            print(f"warning: curated broadcast row {fixture_id} is now a played fixture")
        else:
            errors.append(f"curated broadcast row {fixture_id} is not in the scheduled set")
    return errors


def _strings(node: Any) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [item for value in node.values() for item in _strings(value)]
    if isinstance(node, list):
        return [item for value in node for item in _strings(value)]
    return []


def main() -> int:
    errors = check()
    for error in errors:
        print(f"error: {error}")
    print(f"{'PASS' if not errors else 'FAIL'} broadcast check: {len(errors)} error(s)")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
