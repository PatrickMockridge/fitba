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
SCOUTING_POOL = GENERATED / "scouting" / "pool"
TRANSFERS = GENERATED / "transfers" / "aberdeen.json"
FORMER = GENERATED / "former-players" / "aberdeen.json"
SQUAD = GENERATED / "squad" / "aberdeen.json"

VALID_STATUS = {"active", "denied", "confirmed", "stale"}
VALID_CONFIDENCE = {"low", "medium", "high"}
VALID_SOURCE_TYPES = {"press", "journalist", "forum", "club"}
VALID_AFFILIATIONS = {
    "current_squad",
    "loan_out",
    "current_non_official",
    "former_player",
    "external_target",
    "unknown",
}
VALID_LOOKUPS = {
    "local",
    "former_player",
    "scouted_player",
    "api_match",
    "api_not_found",
    "ambiguous",
}
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
    former = json.loads(FORMER.read_text(encoding="utf-8")) if FORMER.exists() else {}
    squad = json.loads(SQUAD.read_text(encoding="utf-8"))
    scouted_keys: set[str] = set()
    if SCOUTING_POOL.exists():
        for path in SCOUTING_POOL.glob("*.json"):
            document = json.loads(path.read_text(encoding="utf-8"))
            for row in document.get("players", []):
                if row.get("player_id") is not None:
                    scouted_keys.add(f"api:player:{row['player_id']}")
    transfer_ids = {row.get("transfer_id") for row in transfers.get("transfers", [])}
    former_keys = {str(row.get("player_key")) for row in former.get("players", [])}
    former_hrefs = {str(row.get("href")) for row in former.get("players", []) if row.get("href")}
    squad_keys = {
        str(row.get("player_key")) for row in squad.get("players", []) if row.get("player_key")
    }
    non_official_keys = {
        str(row.get("player_key"))
        for row in squad.get("excluded_players", [])
        if row.get("player_key")
    }

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
        affiliation = row.get("affiliation") or "unknown"
        if affiliation not in VALID_AFFILIATIONS:
            errors.append(f"{rid}: invalid affiliation {affiliation!r}")
        key = str(row.get("player_key") or "")
        if affiliation == "former_player" and key not in former_keys:
            errors.append(f"{rid}: former_player does not resolve in the former register")
        if affiliation in {"current_squad", "loan_out"} and key not in squad_keys:
            errors.append(f"{rid}: {affiliation} does not resolve in the current squad")
        if affiliation == "current_non_official" and key not in non_official_keys:
            errors.append(f"{rid}: current_non_official does not resolve in excluded_players")
        if affiliation == "external_target" and key in (
            squad_keys | non_official_keys | former_keys
        ):
            errors.append(f"{rid}: external_target resolves to an Aberdeen player")
        if row.get("former_href") and row["former_href"] not in former_hrefs:
            errors.append(f"{rid}: unknown former_href")
        if row.get("status") == "confirmed":
            if row.get("linked_transfer_id") not in transfer_ids:
                errors.append(f"{rid}: confirmed row links no transfer")
        elif row.get("linked_transfer_id"):
            errors.append(f"{rid}: non-confirmed row has a transfer link")

    if rumours.get("summary", {}).get("total") != len(rows):
        errors.append("rumour summary total does not match rows")
    by_affiliation = (rumours.get("summary") or {}).get("by_affiliation") or {}
    if sum(int(value) for value in by_affiliation.values()) != len(rows):
        errors.append("rumour summary by_affiliation does not sum to rows")

    opinion_ids = {row.get("rumour_id") for row in rows}
    for opinion in rumours.get("opinions", []):
        if not opinion.get("evidence"):
            errors.append(f"{opinion.get('opinion_id')}: opinion has no evidence")
        for item in opinion.get("evidence", []):
            if item not in opinion_ids:
                errors.append(f"{opinion.get('opinion_id')}: unknown evidence {item}")

    target_ids = {
        row.get("rumour_id")
        for row in rows
        if row.get("status") == "active"
        and row.get("direction") == "in"
        and (row.get("affiliation") or "unknown") == "external_target"
    }
    if profile.get("sample_size") != len(target_ids):
        errors.append("rumour profile sample_size != active incoming external targets")
    for signal in profile.get("signals", []):
        if signal.get("rumour_id") not in target_ids:
            errors.append(f"profile contains a non-target row {signal.get('rumour_id')}")
    if profile.get("sample_size", 0) < 5 and not profile.get("low_confidence"):
        errors.append("small rumour cohort is not flagged low_confidence")
    if profile.get("low_confidence") and profile.get("sample_size", 0) >= 5:
        errors.append("large rumour cohort is wrongly flagged low_confidence")

    forum_signals = forum.get("signals", [])
    for signal in forum_signals:
        affiliation = signal.get("affiliation") or "unknown"
        if affiliation not in VALID_AFFILIATIONS:
            errors.append(
                f"forum signal {signal.get('player_name')}: invalid affiliation {affiliation!r}"
            )
        lookup = signal.get("lookup_status")
        if lookup not in VALID_LOOKUPS:
            errors.append(
                f"forum signal {signal.get('player_name')}: invalid lookup status {lookup!r}"
            )
        key = str(signal.get("player_key") or "")
        if lookup == "former_player" and key not in former_keys:
            errors.append(
                f"forum signal {signal.get('player_name')}: former lookup does not resolve"
            )
        if lookup == "scouted_player" and key not in scouted_keys:
            errors.append(
                f"forum signal {signal.get('player_name')}: scouted lookup does not resolve"
            )
        if signal.get("former_href") and signal["former_href"] not in former_hrefs:
            errors.append(f"forum signal {signal.get('player_name')}: unknown former_href")
    affiliation_mix = (forum.get("profile") or {}).get("affiliation_mix") or {}
    if sum(int(value) for value in affiliation_mix.values()) != len(forum_signals):
        errors.append("forum affiliation_mix does not sum to signals")
    external_count = sum(
        1
        for signal in forum_signals
        if (signal.get("affiliation") or "unknown") == "external_target"
    )
    if (forum.get("profile") or {}).get("external_sample_size") != external_count:
        errors.append("forum external_sample_size != external-target signals")
    former_count = sum(
        1 for signal in forum_signals if (signal.get("affiliation") or "unknown") == "former_player"
    )
    if ((forum.get("profile") or {}).get("former_player_profile") or {}).get(
        "sample_size"
    ) != former_count:
        errors.append("forum former_player_profile sample_size != former signals")

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
