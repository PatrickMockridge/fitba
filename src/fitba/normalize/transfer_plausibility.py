"""Plausibility screen for curated transfer rows.

The provider occasionally returns a merged or invented identity. A row is not
published just because it has a citation: it must also look like a real football
transfer. This screen is deliberately conservative and only targets the
high-confidence nonsense case: an unknown player moving permanently from an
unknown/lower-level club with no profile, no position and a Wikipedia-only
citation.

Rows that trigger enough flags are withheld until a reviewer accepts them in
reference/transfer_plausibility.yaml with a written reason and a public source.
"""

from __future__ import annotations

from typing import Any

from fitba.analytics.recruitment import market_for


def _market_maps(markets: list[dict[str, Any]]) -> tuple[dict[str, str], dict[str, str]]:
    by_id: dict[str, str] = {}
    by_name: dict[str, str] = {}
    for entry in markets:
        market = str(entry.get("market") or "unknown")
        if entry.get("club_id"):
            by_id[str(entry["club_id"])] = market
        if entry.get("club_name"):
            by_name[str(entry["club_name"]).casefold()] = market
    return by_id, by_name


def transfer_flags(
    row: dict[str, Any],
    *,
    birth_dates: dict[str, str],
    markets: list[dict[str, Any]],
) -> list[str]:
    flags: list[str] = []
    if row.get("direction") != "in" or row.get("transfer_kind") != "permanent":
        return flags
    player_key = str(row.get("player_key") or "")
    player_name = str(row.get("player_name") or "")
    position = row.get("position")
    source_urls = [str(url) for url in row.get("source_urls") or []]
    by_id, by_name = _market_maps(markets)
    market = market_for(
        row.get("from_club_id"),
        row.get("from_club_name"),
        by_id=by_id,
        by_name=by_name,
    )
    if str(row.get("from_club_id") or "").startswith("sco:provisional-") and market == "unknown":
        flags.append("unknown_source_club")
    if market in {"england", "other", "unknown"}:
        if not birth_dates.get(player_key):
            flags.append("no_player_profile")
        if not position:
            flags.append("no_position")
        if source_urls and all("wikipedia.org" in url for url in source_urls):
            flags.append("wikipedia_only")
    if "-" in player_name and not birth_dates.get(player_key):
        flags.append("merged_name")
    return flags


def is_suspect(flags: list[str]) -> bool:
    return len(flags) >= 3


def screen_transfers(
    rows: list[dict[str, Any]],
    *,
    birth_dates: dict[str, str],
    markets: list[dict[str, Any]],
    accepted: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split rows into publishable and withheld by the plausibility screen."""
    published: list[dict[str, Any]] = []
    withheld: list[dict[str, Any]] = []
    for row in rows:
        flags = transfer_flags(row, birth_dates=birth_dates, markets=markets)
        if is_suspect(flags) and str(row.get("transfer_id")) not in accepted:
            withheld.append({**row, "plausibility_flags": flags})
        else:
            published.append(row)
    return published, withheld


__all__ = ["is_suspect", "screen_transfers", "transfer_flags"]
