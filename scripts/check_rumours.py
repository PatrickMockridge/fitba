#!/usr/bin/env python3
"""CI guard for the rumour mill and fan-signal publication.

Checks that:
- the rumour register and the confirmed transfer register stay separate;
- a confirmed rumour links a real transfer and nothing else does;
- every rumour is sourced and engagement stays null; and
- no raw forum text, username or engagement count reaches the web payload.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "web" / "data" / "generated"
RUMOURS = GENERATED / "rumours" / "aberdeen.json"
PROFILE = GENERATED / "rumours" / "profile.json"
FORUM = GENERATED / "forum" / "afc_chat.json"
TRANSFERS = GENERATED / "transfers" / "aberdeen.json"

VALID_STATUS = {"active", "denied", "confirmed", "stale"}
VALID_CONFIDENCE = {"low", "medium", "high"}
VALID_SOURCE_TYPES = {"press", "journalist", "forum", "club"}
FORBIDDEN_KEYS = {
    "text",
    "post_text",
    "body_text",
    "raw_text",
    "username",
    "user_name",
    "author",
    "display_name",
    "quote",
    "quotes",
}
FORBIDDEN_ENGAGEMENT = {"votes", "vote_count", "likes", "comments", "poll", "polls"}


def _walk(payload: Any, path: str = "") -> list[tuple[str, Any]]:
    items = [(path, payload)]
    if isinstance(payload, dict):
        for key, value in payload.items():
            items.extend(_walk(value, f"{path}.{key}" if path else key))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            items.extend(_walk(value, f"{path}[{index}]"))
    return items


def main() -> int:
    for path in (RUMOURS, PROFILE, FORUM):
        if not path.exists():
            print(f"missing {path}")
            return 1

    rumours = json.loads(RUMOURS.read_text(encoding="utf-8"))
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    forum = json.loads(FORUM.read_text(encoding="utf-8"))
    transfers = json.loads(TRANSFERS.read_text(encoding="utf-8"))
    transfer_ids = {row.get("transfer_id") for row in transfers.get("transfers", [])}

    errors: list[str] = []
    rows = rumours.get("rumours", [])
    ids = [row.get("rumour_id") for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("duplicate rumour ids")

    for row in rows:
        rid = row.get("rumour_id")
        if row.get("status") not in VALID_STATUS:
            errors.append(f"{rid}: invalid status {row.get('status')!r}")
        if row.get("confidence") not in VALID_CONFIDENCE:
            errors.append(f"{rid}: invalid confidence {row.get('confidence')!r}")
        sources = set(row.get("source_types") or [])
        if not sources or not sources <= VALID_SOURCE_TYPES:
            errors.append(f"{rid}: invalid source types {sorted(sources)}")
        if not row.get("source_urls"):
            errors.append(f"{rid}: no source URLs")
        if row.get("engagement") is not None:
            errors.append(f"{rid}: engagement must stay null in this phase")
        if row.get("status") == "confirmed":
            if row.get("linked_transfer_id") not in transfer_ids:
                errors.append(f"{rid}: confirmed row links no transfer")
        elif row.get("linked_transfer_id"):
            errors.append(f"{rid}: non-confirmed row has a transfer link")

    if rumours.get("summary", {}).get("total") != len(rows):
        errors.append("rumour summary total does not match rows")

    opinion_ids = {row.get("rumour_id") for row in rows}
    for opinion in rumours.get("opinions", []):
        if not opinion.get("evidence"):
            errors.append(f"{opinion.get('opinion_id')}: opinion has no evidence")
        for item in opinion.get("evidence", []):
            if item not in opinion_ids:
                errors.append(f"{opinion.get('opinion_id')}: unknown evidence {item}")

    if profile.get("sample_size", 0) < 5 and not profile.get("low_confidence"):
        errors.append("small rumour cohort is not flagged low_confidence")
    if profile.get("low_confidence") and profile.get("sample_size", 0) >= 5:
        errors.append("large rumour cohort is wrongly flagged low_confidence")

    coverage = forum.get("coverage", {})
    if coverage.get("raw_posts_published") is not False:
        errors.append("forum payload must state that raw posts are not published")
    if coverage.get("first_page_only") is not True:
        errors.append("forum payload must state first-page-only sampling")

    for path, value in _walk(forum):
        key = path.split(".")[-1].split("[")[0]
        if key in FORBIDDEN_KEYS and value not in (None, "", []):
            errors.append(f"forum payload contains forbidden key {path}")
        if key in FORBIDDEN_ENGAGEMENT:
            errors.append(f"forum payload contains engagement field {path}")

    if errors:
        print("Rumour publication check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        "Rumour publication check passed "
        f"({len(rows)} rumours, {len(forum.get('signals', []))} fan signals, "
        f"{coverage.get('posts_sampled', 0)} sampled posts)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
