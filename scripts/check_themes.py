#!/usr/bin/env python3
"""Guard Data analysis (stored under themes/).

The page is a sequence of claims, not a fixed five-theme grid. This checker
proves the payload matches the claim register, every claim has a count, status,
evidence, data-upgrade line and withdrawal condition, the benchmark is present,
and the page/manifest/search artifacts agree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

from fitba.publish.case import CaseDocument, case_schema

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data" / "generated"
PAYLOAD = DATA / "themes" / "aberdeen.json"
SCHEMA = ROOT / "contracts" / "themes.schema.json"
CONFIG = ROOT / "config" / "themes.yaml"
MANIFEST = DATA / "manifest.json"
SEARCH = DATA / "search-index.json"

DOMAINS = {"matchday", "off_pitch", "chairman"}
STATUSES = {"supported", "mixed", "not_supported", "cant_test"}
BANNED = re.compile(
    r"\b(?:role famil(?:y|ies)|provider rating|basis|inferred|curated|p95|"
    r"25th percentile|AM/WM|FB/WB|CB|80/20|leaky boat|not a verdict)\b",
    re.IGNORECASE,
)
NUMBERS = re.compile(r"\d+(?:\.\d+)?")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _numbers(text: str) -> set[str]:
    return set(NUMBERS.findall(text))


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for child in value.values() for item in _strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in _strings(child)]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA)
    args = parser.parse_args()
    data = args.data.resolve()
    payload_path = data / "themes" / "aberdeen.json"
    manifest_path = data / "manifest.json"
    search_path = data / "search-index.json"
    errors: list[str] = []
    warnings: list[str] = []

    if not payload_path.exists():
        print(f"error: missing {payload_path}")
        return 1
    if not CONFIG.exists():
        print(f"error: missing {CONFIG}")
        return 1
    if not SCHEMA.exists():
        print(f"error: missing {SCHEMA}")
        return 1

    config = _load_yaml(CONFIG)
    raw = _load(payload_path)
    try:
        document = CaseDocument(**raw)
    except Exception as error:  # noqa: BLE001
        print(f"error: case document does not validate: {error}")
        return 1

    if json.loads(SCHEMA.read_text(encoding="utf-8")) != case_schema():
        errors.append("contracts/themes.schema.json is stale")

    config_claims = sorted(
        config.get("claims") or [], key=lambda item: int(item.get("order") or 99)
    )
    config_ids = [str(item.get("id")) for item in config_claims]
    payload_ids = [claim.id for claim in document.claims]
    if config_ids != payload_ids:
        errors.append(f"config/payload claim ids differ: config={config_ids} payload={payload_ids}")
    if len(payload_ids) != len(set(payload_ids)):
        errors.append("duplicate claim ids")
    if {claim.domain for claim in document.claims} != DOMAINS:
        errors.append("every domain must carry at least one claim")
    for claim in document.claims:
        if claim.status not in STATUSES:
            errors.append(f"{claim.id}: invalid status {claim.status!r}")
        if not claim.count.strip():
            errors.append(f"{claim.id}: count is empty")
        if not claim.evidence:
            errors.append(f"{claim.id}: evidence is empty")
        if not claim.better_data.strip():
            errors.append(f"{claim.id}: better_data is empty")
        if not claim.change_mind.strip():
            errors.append(f"{claim.id}: change_mind is empty")
        if "?" in claim.title:
            errors.append(f"{claim.id}: title must be declarative")
        claim_numbers = _numbers(claim.claim)
        evidence_numbers = _numbers(
            " ".join(f"{item.count} {item.sample} {item.period}" for item in claim.evidence)
        )
        missing = (
            claim_numbers - evidence_numbers - _numbers(claim.count) - _numbers(claim.status_reason)
        )
        if missing:
            errors.append(f"{claim.id}: claim numbers not in the evidence: {sorted(missing)}")
        count_missing = _numbers(claim.count) - evidence_numbers - _numbers(claim.status_reason)
        if count_missing:
            errors.append(f"{claim.id}: count numbers not in the evidence: {sorted(count_missing)}")
        for text in _strings(
            {
                "title": claim.title,
                "claim": claim.claim,
                "count": claim.count,
                "status_reason": claim.status_reason,
                "better_data": claim.better_data,
                "change_mind": claim.change_mind,
                "evidence": [item.model_dump() for item in claim.evidence],
            }
        ):
            match = BANNED.search(text)
            if match:
                errors.append(f"{claim.id}: banned jargon {match.group(0)!r} in {text!r}")

    for label, text in (
        ("owner view", document.owner_view.text),
        ("chairman frame", document.chairman_frame.text),
    ):
        match = BANNED.search(text)
        if match:
            errors.append(f"{label}: banned jargon {match.group(0)!r}")

    if not document.benchmark.rows:
        errors.append("benchmark has no rows")
    if "Aberdeen" not in {str(row.get("Club")) for row in document.benchmark.rows}:
        errors.append("benchmark does not include Aberdeen")
    if "transfer" not in document.benchmark.note.casefold():
        warnings.append("benchmark note does not mention the missing transfer/wage models")

    if manifest_path.exists():
        manifest = _load(manifest_path)
        files = {item["path"]: item for item in manifest.get("files") or []}
        relative = "themes/aberdeen.json"
        if relative not in files:
            errors.append(f"{relative} is not in manifest.files")
        else:
            actual = "sha256:" + hashlib.sha256(payload_path.read_bytes()).hexdigest()
            if files[relative]["checksum"] != actual:
                errors.append("case payload checksum does not match manifest.files")
        marts = {item["id"]: item for item in manifest.get("marts") or []}
        mart = marts.get("case.sco:aberdeen")
        if not mart:
            errors.append("manifest.marts is missing case.sco:aberdeen")
        else:
            if mart.get("rows") != len(document.claims):
                errors.append(f"case mart rows {mart.get('rows')} != {len(document.claims)}")
            if mart.get("checksum") != files.get(relative, {}).get("checksum"):
                errors.append("case mart checksum does not match manifest.files")
        coverage = (manifest.get("coverage") or {}).get("case") or {}
        if coverage.get("count") != len(document.claims):
            errors.append("manifest.coverage.case.count does not match the payload")
    else:
        warnings.append("manifest.json is missing; mart checks skipped")

    if search_path.exists():
        entries = _load(search_path)
        if not any(
            isinstance(entry, dict) and entry.get("href") == "/analysis/" for entry in entries
        ):
            errors.append("search-index.json has no /themes/ entry")
    else:
        warnings.append("search-index.json is missing")

    for warning in warnings:
        print(f"warning: {warning}")
    for error in errors:
        print(f"error: {error}")
    print(
        f"{'FAIL' if errors else 'PASS'} case check: "
        f"{len(document.claims)} claims, {len(document.benchmark.rows)} benchmark rows, "
        f"{len(errors)} error(s), {len(warnings)} warning(s)"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
