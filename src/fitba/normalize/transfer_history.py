"""Shared parsing for provider transfer histories.

The transfer register has its own curation rules; this module only normalizes
the provider's free-text move type and sequences moves. Provider fee-like text
is never treated as a fee fact here.
"""

from __future__ import annotations

from datetime import date
from typing import Any

TRANSFER_KINDS = {
    "permanent",
    "free",
    "loan",
    "loan_return",
    "free_agent",
    "retired",
    "noise",
    "unknown",
}

NOISE_TYPES = {"raise", "swap", "end of career", "none"}
LOAN_RETURN_TYPES = {"return from loan", "back from loan", "loan end"}
FREE_TYPES = {"free", "free agent", "free transfer", "without club"}
LOAN_TYPES = {"loan"}
RETIRED_TYPES = {"retired", "end of career"}


def parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def parse_transfer_type(raw: Any) -> str:
    """Map a provider ``type`` string to a normalized kind.

    A fee-like string such as ``€ 1M`` is a permanent move; the amount is not
    returned and must never be published as a fee.
    """
    value = str(raw or "").strip()
    lower = value.casefold()
    if lower in RETIRED_TYPES:
        return "retired"
    if lower in NOISE_TYPES:
        return "noise"
    if lower in LOAN_RETURN_TYPES:
        return "loan_return"
    if lower in LOAN_TYPES:
        return "loan"
    if lower in FREE_TYPES:
        return "free"
    # Most provider rows are permanent moves; only explicit loan/free/retired
    # types are special. An empty type is a transfer, not "unknown".
    return "permanent"


def transfer_date(transfer: dict[str, Any]) -> date | None:
    return parse_date(transfer.get("date"))


def latest_transfer(
    transfers: list[dict[str, Any]], *, today: date | None = None
) -> dict[str, Any] | None:
    """Return the latest move on or before ``today``."""
    cutoff = today or date.today()
    dated = [
        (moved, index, transfer)
        for index, transfer in enumerate(transfers)
        if (moved := transfer_date(transfer)) is not None and moved <= cutoff
    ]
    if not dated:
        return None
    return max(dated, key=lambda item: (item[0], item[1]))[2]


def sorted_transfers(transfers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        transfers,
        key=lambda transfer: (
            transfer_date(transfer) or date.min,
            str(transfer.get("type") or ""),
            str((transfer.get("teams") or {}).get("in", {}).get("id") or ""),
        ),
    )


def subsequent_permanent_transfer(
    transfers: list[dict[str, Any]],
    *,
    after: date | None,
    from_club_name: str | None = None,
) -> dict[str, Any] | None:
    """First permanent/free move after ``after`` (optionally from a club).

    Loans and loan returns are skipped. A move to a free-agent pseudo-club is
    returned as a free move; the caller classifies it as no sale.
    """
    for transfer in sorted_transfers(transfers):
        moved = transfer_date(transfer)
        if moved is None or (after is not None and moved <= after):
            continue
        kind = parse_transfer_type(transfer.get("type"))
        if kind not in {"permanent", "free"}:
            continue
        teams = transfer.get("teams") or {}
        outgoing = teams.get("out") or {}
        if from_club_name:
            source = str(outgoing.get("name") or "").casefold()
            if source != from_club_name.casefold():
                continue
        return transfer
    return None


__all__ = [
    "TRANSFER_KINDS",
    "latest_transfer",
    "parse_date",
    "parse_transfer_type",
    "sorted_transfers",
    "subsequent_permanent_transfer",
    "transfer_date",
]
