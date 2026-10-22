#!/usr/bin/env python3
"""Seed reference/transfers.yaml from the reviewed API-Football candidates.

This is a curation helper, not an automatic publisher. It marks rows as
confirmed only where an official AFC announcement is linked; everything else is
curated against the Wikipedia season table. Review the output before publishing.
"""

from __future__ import annotations

import yaml

from fitba.ingest.transfers import _is_pseudo_team
from fitba.settings import REFERENCE_DIR

WIKI = {
    "2024-25": "https://en.wikipedia.org/wiki/2024%E2%80%9325_Aberdeen_F.C._season",
    "2025-26": "https://en.wikipedia.org/wiki/2025%E2%80%9326_Aberdeen_F.C._season",
    "2026-27": "https://en.wikipedia.org/wiki/2026%E2%80%9327_Aberdeen_F.C._season",
}
OFFICIAL = {
    (
        "M. Müller",
        "2026-27",
        "in",
        "permanent",
    ): "https://www.afc.co.uk/en/news/marius-mueller-joins-the-dons",
    (
        "L. Mayo",
        "2026-27",
        "in",
        "free",
    ): "https://www.afc.co.uk/en/news/dons-land-defender-as-mayo-agrees-aberdeen-move",
    (
        "N. Suman",
        "2026-27",
        "out",
        "loan",
    ): "https://www.afc.co.uk/en/news/suman-joins-ross-county-on-loan",
}


def main() -> int:
    candidates = yaml.safe_load(
        (REFERENCE_DIR / "transfers.candidates.yaml").read_text(encoding="utf-8")
    )["transfers"]
    rows = []
    for candidate in candidates:
        if candidate["season"] not in WIKI:
            continue
        if candidate["transfer_kind"] == "loan_return":
            continue
        if candidate["window"] not in {"summer", "winter"}:
            continue
        from_name = candidate["from_club_name"]
        to_name = candidate["to_club_name"]
        from_id = candidate["from_club_id"]
        to_id = candidate["to_club_id"]
        if candidate["direction"] == "out" and _is_pseudo_team(to_name, candidate["player_name"]):
            to_name, to_id = "Free agent", "sco:free-agent"
        if candidate["direction"] == "in" and _is_pseudo_team(from_name, candidate["player_name"]):
            from_name, from_id = "Free agent", "sco:free-agent"
        official = OFFICIAL.get(
            (
                candidate["player_name"],
                candidate["season"],
                candidate["direction"],
                candidate["transfer_kind"],
            )
        )
        status = "confirmed" if official else "curated"
        fee_status = (
            candidate["fee_status"]
            if candidate["fee_status"] in {"free", "loan"}
            else "undisclosed"
        )
        rows.append(
            {
                "transfer_id": candidate["transfer_id"],
                "player_key": candidate["player_key"],
                "player_name": candidate["player_name"],
                "transfer_kind": candidate["transfer_kind"],
                "direction": candidate["direction"],
                "from_club_id": from_id,
                "from_club_name": from_name,
                "to_club_id": to_id,
                "to_club_name": to_name,
                "date_effective": candidate["date_effective"],
                "date_announced": candidate["date_announced"],
                "season": candidate["season"],
                "window": candidate["window"],
                "fee_status": fee_status,
                "fee_amount": None,
                "fee_currency": None,
                "fee_raw": candidate.get("fee_raw"),
                "loan_end_date": None,
                "recall_clause": None,
                "obligation_to_buy": None,
                "option_to_buy": None,
                "verification_status": status,
                "source_urls": ([official] if official else []) + [WIKI[candidate["season"]]],
                "verified_at": "2026-10-21",
                "notes": (
                    "Official AFC announcement linked; feed candidate corroborated."
                    if status == "confirmed"
                    else (
                        "Curated from the API-Football candidate feed and the "
                        "Wikipedia season table; official club announcement not "
                        "found for this row."
                    )
                ),
            }
        )
    rows.sort(key=lambda row: (row["season"], row["window"], row["date_effective"]))
    path = REFERENCE_DIR / "transfers.yaml"
    path.write_text(
        yaml.safe_dump({"transfers": rows}, sort_keys=False, allow_unicode=True, width=120),
        encoding="utf-8",
    )
    print(f"Wrote {path} ({len(rows)} transfers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
