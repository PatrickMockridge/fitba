"""Manager vacancy gate and next-manager market helpers.

The market is open only while the staff register has exactly one current
manager and that manager is interim. It closes automatically when a permanent
manager is recorded. The helpers are pure so the publish and guard paths can use
the same rule.
"""

from __future__ import annotations

import re
from typing import Any

FRACTIONAL_RE = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")


def _current_manager_stints(staff: dict[str, Any]) -> list[dict[str, Any]]:
    current: list[dict[str, Any]] = []
    for person in staff.get("people") or []:
        for stint in person.get("stints") or []:
            if stint.get("role_group") != "manager" or stint.get("end"):
                continue
            current.append({**stint, "name": person.get("name")})
    return current


def manager_vacancy(staff: dict[str, Any], *, checked_at: str | None = None) -> dict[str, Any]:
    current = _current_manager_stints(staff)
    if len(current) == 1 and current[0].get("interim"):
        interim = current[0]
        permanent_ends = [
            stint
            for person in staff.get("people") or []
            for stint in person.get("stints") or []
            if stint.get("role_group") == "manager"
            and not stint.get("interim")
            and stint.get("end")
        ]
        vacancy_started = max(
            (str(stint.get("end"))[:10] for stint in permanent_ends), default=None
        )
        return {
            "is_open": True,
            "state": "open",
            "permanent_manager": None,
            "interim_manager": interim.get("name"),
            "interim_since": str(interim.get("start") or "")[:10] or None,
            "vacancy_started": vacancy_started,
            "checked_at": checked_at,
        }
    if len(current) == 1 and not current[0].get("interim"):
        permanent = current[0]
        return {
            "is_open": False,
            "state": "closed",
            "permanent_manager": permanent.get("name"),
            "permanent_manager_start": str(permanent.get("start") or "")[:10] or None,
            "interim_manager": None,
            "interim_since": None,
            "vacancy_started": None,
            "checked_at": checked_at,
        }
    return {
        "is_open": False,
        "state": "unavailable",
        "permanent_manager": None,
        "interim_manager": None,
        "interim_since": None,
        "vacancy_started": None,
        "checked_at": checked_at,
        "reason": "staff register does not have exactly one current manager",
    }


def fractional_decimal(value: str | None) -> float | None:
    if not value:
        return None
    match = FRACTIONAL_RE.match(str(value))
    if match is None:
        return None
    denominator = int(match.group(2))
    if denominator == 0:
        return None
    return round(int(match.group(1)) / denominator + 1.0, 4)


def implied_probability(decimal: float | None) -> float | None:
    if decimal is None or decimal <= 0:
        return None
    return round(1.0 / decimal, 4)


def extract_manager_mentions(text: str, candidates: list[dict[str, Any]]) -> dict[str, int]:
    """Count full-name mentions only; no surname-only matching."""
    folded = text.casefold()
    counts: dict[str, int] = {}
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id") or candidate.get("id") or "")
        if not candidate_id:
            continue
        names = [str(candidate.get("name") or "")] + [
            str(alias) for alias in candidate.get("aliases") or []
        ]
        for name in names:
            if not name.strip():
                continue
            pattern = rf"(?<!\w){re.escape(name.casefold())}(?!\w)"
            found = len(re.findall(pattern, folded))
            if found:
                counts[candidate_id] = counts.get(candidate_id, 0) + found
                break
    return counts


__all__ = [
    "extract_manager_mentions",
    "fractional_decimal",
    "implied_probability",
    "manager_vacancy",
]
