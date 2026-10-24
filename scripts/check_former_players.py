#!/usr/bin/env python3
"""CI guard for the former-player index and season-detail documents."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fitba.publish.former_players import (
    FormerPlayersDocument,
    FormerSeasonsDocument,
    former_players_schema,
    former_seasons_schema,
)

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "web" / "data" / "generated"
FORMER = GENERATED / "former-players" / "aberdeen.json"
SEASONS = GENERATED / "former-players" / "seasons.json"
TRANSFERS = GENERATED / "transfers" / "aberdeen.json"
SQUAD = GENERATED / "squad" / "aberdeen.json"
SCHEMA = ROOT / "contracts" / "former-players.schema.json"
SEASONS_SCHEMA = ROOT / "contracts" / "former-seasons.schema.json"

VERDICT_PHRASES = (
    "good price",
    "bad price",
    "bargain",
    "flop",
    "success rate",
    "should have kept",
)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _strings(node: Any):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from _strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _strings(value)


def main() -> int:
    for path in (FORMER, SEASONS):
        if not path.exists():
            print(f"missing {path}")
            return 1
    if not SCHEMA.exists() or not SEASONS_SCHEMA.exists():
        print("missing former-player schema")
        return 1
    index = _load(FORMER)
    seasons = _load(SEASONS)
    transfers = _load(TRANSFERS)
    squad = _load(SQUAD)
    errors: list[str] = []
    try:
        FormerPlayersDocument.model_validate(index)
        FormerSeasonsDocument.model_validate(seasons)
    except Exception as error:  # noqa: BLE001 - a schema failure is the result
        errors.append(f"document schema: {type(error).__name__}: {error}")
    if former_players_schema() != _load(SCHEMA):
        errors.append("contracts/former-players.schema.json is stale")
    if former_seasons_schema() != _load(SEASONS_SCHEMA):
        errors.append("contracts/former-seasons.schema.json is stale")

    players = index.get("players") or []
    summary = index.get("summary") or {}
    transfer_rows = {str(row.get("transfer_id")): row for row in transfers.get("transfers") or []}
    official = {
        str(row.get("player_key")) for row in squad.get("players") or [] if row.get("player_key")
    }
    keys: set[str] = set()
    if summary.get("total") != len(players):
        errors.append("former summary total != player rows")
    for row in players:
        key = str(row.get("player_key") or "")
        if not key or key in keys:
            errors.append(f"former player key missing or duplicated: {key!r}")
            continue
        keys.add(key)
        if key in official:
            errors.append(f"former player {key} is in the official squad")
        if not str(row.get("href") or "").startswith("/former-players/#former-"):
            errors.append(f"former player {key} has no board anchor")
        departure = row.get("departure") or {}
        transfer = transfer_rows.get(str(departure.get("transfer_id")))
        if not transfer:
            errors.append(f"former player {key} has no published departure")
        elif transfer.get("direction") != "out" or transfer.get("transfer_kind") not in {
            "permanent",
            "free",
        }:
            errors.append(f"former player {key} departure is not permanent/free")
        if (row.get("post_career") or {}).get("current", {}).get("coverage") not in {
            "current",
            "historical",
            "unknown",
        }:
            errors.append(f"former player {key} has invalid current coverage")

    detail = seasons.get("seasons") or {}
    if set(detail) != keys:
        errors.append("former season keys do not match the player index")
    for key, block in detail.items():
        rows = block.get("post_seasons") or []
        player = next((row for row in players if row.get("player_key") == key), {})
        totals = (player.get("post_career") or {}).get("totals") or {}
        for field_name in ("appearances", "starts", "minutes", "goals", "assists"):
            expected = totals.get(field_name)
            if expected is None:
                continue
            actual = sum(int(row.get(field_name) or 0) for row in rows)
            if actual != int(expected):
                errors.append(f"former {key} post {field_name} {actual} != {expected}")
        coverage = block.get("coverage") or {}
        present = {str(row.get("season")) for row in rows}
        if set(coverage.get("present_seasons") or []) != present:
            errors.append(f"former {key} present seasons do not match rows")

    watch = index.get("sell_on_watch") or {}
    transfer_clauses = {
        str(row.get("clause_id")) for row in transfers.get("sell_on_clauses") or []
    }
    clauses = watch.get("clauses") or []
    if {str(row.get("clause_id")) for row in clauses} != transfer_clauses:
        errors.append("sell-on clauses do not match the transfer register")
    computed = 0
    for clause in clauses:
        receipt = clause.get("receipt") or {}
        if receipt.get("status") == "computed":
            computed += 1
            if receipt.get("receipt_gbp") is None:
                errors.append(f"sell-on {clause.get('clause_id')} computed without a receipt")
        elif receipt.get("receipt_gbp") is not None:
            errors.append(f"sell-on {clause.get('clause_id')} has a receipt without status")
        if receipt.get("status") == "missing_inputs" and not receipt.get("missing_inputs"):
            errors.append(f"sell-on {clause.get('clause_id')} missing inputs but no reason")
    if (watch.get("summary") or {}).get("computed") != computed:
        errors.append("sell-on summary computed != clauses")

    coverage = index.get("coverage") or {}
    counts = coverage.get("counts") or {}
    if counts.get("players") != len(players):
        errors.append("former coverage players != player rows")
    if int(counts.get("with_api_id") or 0) + int(counts.get("without_api_id") or 0) != len(players):
        errors.append("former coverage API ids do not sum to players")

    for text in _strings({"notes": index.get("notes"), "coverage": coverage.get("note")}):
        lowered = text.casefold()
        for phrase in VERDICT_PHRASES:
            if phrase in lowered:
                errors.append(f"verdict language {phrase!r} in former-player payload")

    if errors:
        print("Former-player publication check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(
        "Former-player publication check passed "
        f"({len(players)} players, {len(detail)} season documents, "
        f"{len(clauses)} sell-on clauses)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
