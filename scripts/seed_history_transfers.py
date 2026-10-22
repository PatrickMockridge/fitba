#!/usr/bin/env python3
"""Seed the historical transfer register from reviewed candidates.

This is a curation helper, not an automatic publisher. It merges a reviewed
set of senior Cormack-era moves into reference/transfers.yaml, using the
historical API-Football candidate file for dates/clubs and the Wikipedia season
page as the public citation. Pre-2024-25 windows are curated partial, not
audited.

Run once, review the diff, then run `fitba transfers` and `fitba publish`.
"""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import date
from typing import Any

import yaml

from fitba.ingest.transfers import _transfer_season, _window_for
from fitba.settings import REFERENCE_DIR

WIKI = {
    "2019-20": "https://en.wikipedia.org/wiki/2019%E2%80%9320_Aberdeen_F.C._season",
    "2020-21": "https://en.wikipedia.org/wiki/2020%E2%80%9321_Aberdeen_F.C._season",
    "2021-22": "https://en.wikipedia.org/wiki/2021%E2%80%9322_Aberdeen_F.C._season",
    "2022-23": "https://en.wikipedia.org/wiki/2022%E2%80%9323_Aberdeen_F.C._season",
    "2023-24": "https://en.wikipedia.org/wiki/2023%E2%80%9324_Aberdeen_F.C._season",
}

# Reviewed senior moves. `player` matches the candidate name; `from`/`to` are
# only needed when the candidate is missing or ambiguous. Fees stay undisclosed
# unless an exact official amount is stated; reported figures live in fee_raw.
# fmt: off
MOVES: list[dict[str, Any]] = [
    # 2019-20 (Summer 2019 was before Cormack; Winter 2020 was his first window)
    {"player": "R. Hedges", "season": "2019-20", "direction": "in", "kind": "free", "date": "2019-07-01", "position": "Attacker"},
    {"player": "A. Taylor", "season": "2019-20", "direction": "in", "kind": "free", "date": "2019-07-01", "position": "Defender"},
    {"player": "C. Main", "season": "2019-20", "direction": "in", "kind": "free", "date": "2019-07-01", "position": "Attacker"},
    {"player": "C. Bryson", "season": "2019-20", "direction": "in", "kind": "free", "date": "2019-07-01", "position": "Midfielder"},
    {"player": "F. Ojo", "season": "2019-20", "direction": "in", "kind": "permanent", "date": "2019-07-14", "fee_status": "undisclosed", "fee_raw": "Reported £125,000", "position": "Midfielder"},
    {"player": "G. Leigh", "season": "2019-20", "direction": "in", "kind": "loan", "date": "2019-06-25", "position": "Defender"},
    {"player": "J. Gallagher", "season": "2019-20", "direction": "in", "kind": "loan", "date": "2019-07-01", "position": "Attacker"},
    {"player": "D. McGeouch", "season": "2019-20", "direction": "in", "kind": "permanent", "date": "2020-01-07", "position": "Midfielder"},
    {"player": "M. Kennedy", "season": "2019-20", "direction": "in", "kind": "permanent", "date": "2020-01-24", "fee_status": "undisclosed", "fee_raw": "Reported £70,000", "position": "Attacker"},
    {"player": "R. Hernández", "season": "2019-20", "direction": "in", "kind": "permanent", "date": "2020-01-31", "position": "Defender"},
    {"player": "G. Shinnie", "season": "2019-20", "direction": "out", "kind": "free", "date": "2019-07-01", "position": "Midfielder"},
    {"player": "M. Reynolds", "season": "2019-20", "direction": "out", "kind": "free", "date": "2019-07-01", "position": "Defender"},
    {"player": "G. Mackay-Steven", "season": "2019-20", "direction": "out", "kind": "free", "date": "2019-06-24", "position": "Attacker"},
    {"player": "S. May", "season": "2019-20", "direction": "out", "kind": "permanent", "date": "2019-08-29", "position": "Attacker"},
    {"player": "J. Wilson", "season": "2019-20", "direction": "out", "kind": "free", "date": "2020-02-01", "position": "Attacker"},
    {"player": "S. Gleeson", "season": "2019-20", "direction": "out", "kind": "free", "date": "2020-01-31", "position": "Midfielder"},

    # 2020-21
    {"player": "J. Hayes", "season": "2020-21", "direction": "in", "kind": "free", "date": "2020-07-01", "position": "Attacker"},
    {"player": "T. Hoban", "season": "2020-21", "direction": "in", "kind": "free", "date": "2020-07-31", "from": "Free agent", "position": "Defender"},
    {"player": "R. McCrorie", "season": "2020-21", "direction": "in", "kind": "permanent", "date": "2020-08-18", "position": "Midfielder", "notes": "Initial loan with an obligation to buy; made permanent in February 2021."},
    {"player": "M. Watkins", "season": "2020-21", "direction": "in", "kind": "loan", "date": "2020-08-01", "position": "Attacker"},
    {"player": "R. Edmondson", "season": "2020-21", "direction": "in", "kind": "loan", "date": "2020-07-31", "position": "Attacker"},
    {"player": "G. Leigh", "season": "2020-21", "direction": "in", "kind": "free", "date": "2020-10-05", "position": "Defender"},
    {"player": "G. Woods", "season": "2020-21", "direction": "in", "kind": "loan", "date": "2020-10-01", "position": "Goalkeeper"},
    {"player": "F. Hornby", "season": "2020-21", "direction": "in", "kind": "loan", "date": "2021-02-01", "position": "Attacker"},
    {"player": "C. Hendry", "season": "2020-21", "direction": "in", "kind": "loan", "date": "2021-02-01", "position": "Attacker"},
    {"player": "F. Kamberi", "season": "2020-21", "direction": "in", "kind": "loan", "date": "2021-02-01", "position": "Attacker"},
    {"player": "S. McKenna", "season": "2020-21", "direction": "out", "kind": "permanent", "date": "2020-09-23", "fee_status": "undisclosed", "fee_raw": "Club-record fee (reported £3m)", "position": "Defender"},
    {"player": "S. Cosgrove", "season": "2020-21", "direction": "out", "kind": "permanent", "date": "2021-01-31", "fee_status": "undisclosed", "fee_raw": "Reported £2m", "position": "Attacker"},
    {"player": "S. Wright", "season": "2020-21", "direction": "out", "kind": "permanent", "date": "2021-02-01", "position": "Attacker"},
    {"player": "C. Main", "season": "2020-21", "direction": "out", "kind": "free", "date": "2021-02-01", "position": "Attacker"},
    {"player": "C. Bryson", "season": "2020-21", "direction": "out", "kind": "free", "date": "2020-09-18", "position": "Midfielder"},
    {"player": "D. Rogers", "season": "2020-21", "direction": "out", "kind": "free", "date": "2020-07-28", "position": "Goalkeeper"},

    # 2021-22
    {"player": "S. Brown", "season": "2021-22", "direction": "in", "kind": "free", "date": "2021-07-01", "position": "Midfielder"},
    {"player": "D. Gallagher", "season": "2021-22", "direction": "in", "kind": "free", "date": "2021-07-01", "position": "Defender"},
    {"player": "J. Emmanuel-Thomas", "season": "2021-22", "direction": "in", "kind": "free", "date": "2021-07-01", "position": "Attacker"},
    {"player": "C. Ramirez", "season": "2021-22", "direction": "in", "kind": "permanent", "date": "2021-07-01", "position": "Attacker"},
    {"player": "J. Gurr", "season": "2021-22", "direction": "in", "kind": "free", "date": "2021-07-01", "position": "Defender"},
    {"player": "G. Woods", "season": "2021-22", "direction": "in", "kind": "free", "date": "2021-07-01", "position": "Goalkeeper"},
    {"player": "T. Jenks", "season": "2021-22", "direction": "in", "kind": "loan", "date": "2021-07-01", "position": "Midfielder"},
    {"player": "M. Longstaff", "season": "2021-22", "direction": "in", "kind": "loan", "date": "2021-08-01", "position": "Midfielder"},
    {"player": "A. Samuels", "season": "2021-22", "direction": "in", "kind": "loan", "date": "2021-08-01", "position": "Attacker"},
    {"player": "D. Polvara", "season": "2021-22", "direction": "in", "kind": "free", "date": "2022-01-08", "from": "Charleston Battery", "position": "Midfielder"},
    {"player": "V. Besuijen", "season": "2021-22", "direction": "in", "kind": "permanent", "date": "2022-01-24", "position": "Attacker"},
    {"player": "A. Montgomery", "season": "2021-22", "direction": "in", "kind": "loan", "date": "2022-01-01", "position": "Defender"},
    {"player": "R. Hedges", "season": "2021-22", "direction": "out", "kind": "permanent", "date": "2022-01-30", "position": "Attacker"},
    {"player": "N. McGinn", "season": "2021-22", "direction": "out", "kind": "free", "date": "2022-01-24", "position": "Attacker"},
    {"player": "R. Hernández", "season": "2021-22", "direction": "out", "kind": "permanent", "date": "2022-01-17", "position": "Defender"},
    {"player": "S. Brown", "season": "2021-22", "direction": "out", "kind": "free", "date": "2022-03-01", "position": "Midfielder"},
    {"player": "D. McGeouch", "season": "2021-22", "direction": "out", "kind": "free", "date": "2022-05-31", "position": "Midfielder"},

    # 2022-23
    {"player": "B. Miovski", "season": "2022-23", "direction": "in", "kind": "permanent", "date": "2022-07-01", "fee_status": "undisclosed", "fee_raw": "Reported £535,000", "position": "Attacker"},
    {"player": "Y. Ramadani", "season": "2022-23", "direction": "in", "kind": "permanent", "date": "2022-07-01", "fee_status": "undisclosed", "fee_raw": "Reported £100,000", "position": "Midfielder"},
    {"player": "J. Richardson", "season": "2022-23", "direction": "in", "kind": "permanent", "date": "2022-06-20", "position": "Defender"},
    {"player": "A. Stewart", "season": "2022-23", "direction": "in", "kind": "free", "date": "2022-07-01", "position": "Defender"},
    {"player": "K. Roos", "season": "2022-23", "direction": "in", "kind": "free", "date": "2022-07-01", "position": "Goalkeeper"},
    {"player": "Duk", "season": "2022-23", "direction": "in", "kind": "permanent", "date": "2022-07-15", "position": "Attacker"},
    {"player": "C. Roberts", "season": "2022-23", "direction": "in", "kind": "permanent", "date": "2022-07-25", "position": "Attacker"},
    {"player": "S. Morris", "season": "2022-23", "direction": "in", "kind": "permanent", "date": "2022-08-04", "position": "Attacker"},
    {"player": "L. Scales", "season": "2022-23", "direction": "in", "kind": "loan", "date": "2022-06-01", "position": "Defender"},
    {"player": "L. Clarkson", "season": "2022-23", "direction": "in", "kind": "loan", "date": "2022-08-06", "position": "Midfielder"},
    {"player": "G. Shinnie", "season": "2022-23", "direction": "in", "kind": "loan", "date": "2023-01-05", "position": "Midfielder"},
    {"player": "P. Myslovič", "season": "2022-23", "direction": "in", "kind": "loan", "date": "2023-01-05", "position": "Midfielder"},
    {"player": "M. Pollock", "season": "2022-23", "direction": "in", "kind": "loan", "date": "2023-01-29", "position": "Defender"},
    {"player": "J. Gorter", "season": "2022-23", "direction": "in", "kind": "loan", "date": "2023-01-31", "position": "Goalkeeper"},
    {"player": "A. MacDonald", "season": "2022-23", "direction": "in", "kind": "free", "date": "2023-01-31", "position": "Defender"},
    {"player": "D. Markanday", "season": "2022-23", "direction": "in", "kind": "loan", "date": "2023-01-31", "position": "Attacker"},
    {"player": "C. Ramsay", "season": "2022-23", "direction": "out", "kind": "permanent", "date": "2022-06-19", "fee_status": "disclosed", "fee_amount": 4200000, "fee_currency": "GBP", "fee_raw": "Initial £4.2m plus up to £2.5m in add-ons", "position": "Defender"},
    {"player": "L. Ferguson", "season": "2022-23", "direction": "out", "kind": "permanent", "date": "2022-07-12", "fee_status": "undisclosed", "fee_raw": "Reported £3m", "position": "Midfielder"},
    {"player": "A. Considine", "season": "2022-23", "direction": "out", "kind": "free", "date": "2022-07-01", "position": "Defender"},
    {"player": "F. Ojo", "season": "2022-23", "direction": "out", "kind": "free", "date": "2022-07-01", "position": "Midfielder"},
    {"player": "M. Ruth", "season": "2022-23", "direction": "out", "kind": "free", "date": "2022-07-01", "position": "Attacker"},
    {"player": "D. Gallagher", "season": "2022-23", "direction": "out", "kind": "free", "date": "2022-07-01", "position": "Defender"},
    {"player": "D. Bates", "season": "2022-23", "direction": "out", "kind": "permanent", "date": "2022-09-01", "position": "Defender"},
    {"player": "M. Devlin", "season": "2022-23", "direction": "out", "kind": "free", "date": "2022-08-26", "position": "Defender"},
    {"player": "J. Emmanuel-Thomas", "season": "2022-23", "direction": "out", "kind": "free", "date": "2022-08-12", "position": "Attacker"},
    {"player": "D. McGeouch", "season": "2022-23", "direction": "out", "kind": "free", "date": "2022-11-21", "position": "Midfielder"},
    {"player": "A. Stewart", "season": "2022-23", "direction": "out", "kind": "loan", "date": "2023-01-31", "position": "Defender"},
    {"player": "V. Besuijen", "season": "2022-23", "direction": "out", "kind": "loan", "date": "2023-01-31", "position": "Attacker"},

    # 2023-24
    {"player": "N. Devlin", "season": "2023-24", "direction": "in", "kind": "free", "date": "2023-05-22", "position": "Defender"},
    {"player": "L. Clarkson", "season": "2023-24", "direction": "in", "kind": "permanent", "date": "2023-06-15", "position": "Midfielder"},
    {"player": "E. Sokler", "season": "2023-24", "direction": "in", "kind": "permanent", "date": "2023-06-16", "position": "Attacker"},
    {"player": "G. Shinnie", "season": "2023-24", "direction": "in", "kind": "free", "date": "2023-06-16", "position": "Midfielder"},
    {"player": "R. Jensen", "season": "2023-24", "direction": "in", "kind": "permanent", "date": "2023-08-23", "position": "Defender"},
    {"player": "J. McGrath", "season": "2023-24", "direction": "in", "kind": "free", "date": "2023-08-22", "position": "Midfielder"},
    {"player": "J. McGarry", "season": "2023-24", "direction": "in", "kind": "permanent", "date": "2023-08-11", "position": "Defender"},
    {"player": "P. Guèye", "season": "2023-24", "direction": "in", "kind": "permanent", "date": "2023-08-29", "position": "Attacker"},
    {"player": "S. Rubežić", "season": "2023-24", "direction": "in", "kind": "permanent", "date": "2023-07-31", "position": "Defender"},
    {"player": "R. Doohan", "season": "2023-24", "direction": "in", "kind": "free", "date": "2023-07-06", "position": "Goalkeeper"},
    {"player": "K. Phillips", "season": "2023-24", "direction": "in", "kind": "loan", "date": "2024-01-01", "position": "Midfielder"},
    {"player": "J. Hoilett", "season": "2023-24", "direction": "in", "kind": "free", "date": "2024-02-16", "position": "Attacker"},
    {"player": "R. McCrorie", "season": "2023-24", "direction": "out", "kind": "permanent", "date": "2023-06-14", "position": "Defender"},
    {"player": "Y. Ramadani", "season": "2023-24", "direction": "out", "kind": "permanent", "date": "2023-08-04", "fee_status": "undisclosed", "fee_raw": "Reported £1.1m", "position": "Midfielder"},
    {"player": "M. Watkins", "season": "2023-24", "direction": "out", "kind": "free", "date": "2023-07-21", "position": "Attacker"},
    {"player": "C. McLennan", "season": "2023-24", "direction": "out", "kind": "free", "date": "2023-07-25", "position": "Attacker"},
    {"player": "D. Campbell", "season": "2023-24", "direction": "out", "kind": "free", "date": "2023-07-01", "position": "Midfielder"},
    {"player": "M. Kennedy", "season": "2023-24", "direction": "out", "kind": "free", "date": "2023-06-21", "position": "Attacker"},
    {"player": "J. Lewis", "season": "2023-24", "direction": "out", "kind": "free", "date": "2023-07-01", "position": "Goalkeeper"},
]
# fmt: on


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "unknown"


def _hash_id(player_key: str, date_effective: str, direction: str, club: str) -> str:
    raw = f"{player_key}|{date_effective}|{direction}|{club}".encode()
    return "afc:" + hashlib.sha256(raw).hexdigest()[:16]


def _candidate_index(
    candidates: list[dict[str, Any]],
) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    index: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        index[
            (str(row.get("player_name")), str(row.get("season")), str(row.get("direction")))
        ].append(row)
    return index


def main() -> int:
    register_path = REFERENCE_DIR / "transfers.yaml"
    register = yaml.safe_load(register_path.read_text(encoding="utf-8")) or {}
    existing = list(register.get("transfers", []))
    candidates = yaml.safe_load(
        (REFERENCE_DIR / "transfers.candidates.history.yaml").read_text(encoding="utf-8")
    )["transfers"]
    index = _candidate_index(candidates)
    existing_keys = {
        (row.get("player_key"), row.get("date_effective"), row.get("direction")) for row in existing
    }
    added = 0
    for move in MOVES:
        season = move["season"]
        direction = move["direction"]
        player = move["player"]
        options = index.get((player, season, direction), [])
        candidate = None
        for option in options:
            if move.get("from") and str(option.get("from_club_name")) != move["from"]:
                continue
            if move.get("to") and str(option.get("to_club_name")) != move["to"]:
                continue
            if move.get("kind") and str(option.get("transfer_kind")) == move["kind"]:
                candidate = option
                break
            candidate = option
        if candidate is None and options:
            candidate = options[0]
        player_key = candidate.get("player_key") if candidate else f"curated:player:{_slug(player)}"
        date_effective = move["date"]
        if (player_key, date_effective, direction) in existing_keys:
            continue
        from_name = move.get("from") or (candidate or {}).get("from_club_name") or "Unknown"
        to_name = move.get("to") or (candidate or {}).get("to_club_name") or "Unknown"
        from_id = (candidate or {}).get("from_club_id") or f"sco:provisional-{_slug(from_name)}"
        to_id = (candidate or {}).get("to_club_id") or f"sco:provisional-{_slug(to_name)}"
        if direction == "in" and to_name != "Aberdeen":
            to_name, to_id = "Aberdeen", "sco:aberdeen"
        if direction == "out" and from_name != "Aberdeen":
            from_name, from_id = "Aberdeen", "sco:aberdeen"
        kind = move.get("kind") or (candidate or {}).get("transfer_kind") or "permanent"
        fee_status = move.get("fee_status") or (
            "free" if kind == "free" else "loan" if kind == "loan" else "undisclosed"
        )
        position = move.get("position")
        parsed_date = date.fromisoformat(date_effective)
        row = {
            "transfer_id": (candidate or {}).get("transfer_id")
            or _hash_id(
                player_key, date_effective, direction, to_name if direction == "in" else from_name
            ),
            "player_key": player_key,
            "player_name": player,
            "position": position,
            "position_source": "curated" if position else "unknown",
            "position_source_season": None,
            "position_unknown_reason": None if position else "historical_scope",
            "direction": direction,
            "transfer_kind": kind,
            "from_club_id": from_id,
            "from_club_name": from_name,
            "to_club_id": to_id,
            "to_club_name": to_name,
            "date_effective": date_effective,
            "date_announced": date_effective,
            "season": _transfer_season(parsed_date),
            "window": _window_for(parsed_date),
            "fee_status": fee_status,
            "fee_amount": move.get("fee_amount"),
            "fee_currency": move.get("fee_currency"),
            "fee_raw": move.get("fee_raw")
            or ("Free" if fee_status == "free" else "Loan" if fee_status == "loan" else ""),
            "loan_end_date": None,
            "recall_clause": None,
            "obligation_to_buy": None,
            "option_to_buy": None,
            "verification_status": "curated",
            "source_urls": [WIKI[season]],
            "verified_at": "2026-10-21",
            "notes": move.get(
                "notes",
                "Curated from the historical API-Football candidate feed and the Wikipedia season table; pre-2024-25 coverage is curated partial, not audited.",
            ),
        }
        row["nationality"] = (candidate or {}).get("nationality")
        existing.append(row)
        existing_keys.add((player_key, date_effective, direction))
        added += 1

    existing.sort(
        key=lambda row: (
            str(row.get("season") or ""),
            str(row.get("date_effective") or ""),
            str(row.get("direction") or ""),
        )
    )
    register_path.write_text(
        yaml.safe_dump(
            {"transfers": existing},
            sort_keys=False,
            allow_unicode=True,
            width=120,
        ),
        encoding="utf-8",
    )
    print(f"Added {added} historical rows; register now {len(existing)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
