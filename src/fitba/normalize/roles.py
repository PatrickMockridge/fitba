"""Role taxonomy and formation-grid mapping.

Role is derived from the starting-XI grid in the licensed lineup feed: the
formation shape gives the row lengths, and the grid slot gives the row/column.
Nothing here reads preferred foot, a generic squad position, a shirt number or
a substitute's entry. Those are separate data.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

SHAPE_RE = re.compile(r"^\d+(?:-\d+)+$")
SIDE_VALUES = {None, "left", "right", "central"}
DEFENSIVE_FAMILIES = {
    "goalkeeper",
    "centre_back",
    "full_back",
    "wing_back",
    "defensive_midfield",
}


def shape_from_formation(formation: str | None) -> tuple[int, ...] | None:
    """Return the grid row counts for a formation string such as 4-2-3-1."""
    if not formation:
        return None
    value = str(formation).strip()
    if not SHAPE_RE.fullmatch(value):
        return None
    parts = [int(part) for part in value.split("-")]
    return (1, *parts) if sum(parts) == 10 else None


def shape_from_grid(grids: Iterable[str | None]) -> tuple[int, ...] | None:
    """Return row counts from starting-XI grid slots such as ``2:4``.

    Every starter must have a valid grid, the first row must contain the
    goalkeeper, and the rows must be contiguous. Anything else is unknown.
    """
    rows: dict[int, int] = {}
    count = 0
    for grid in grids:
        if not grid:
            return None
        try:
            row_text, col_text = str(grid).split(":", 1)
            row, col = int(row_text), int(col_text)
        except (TypeError, ValueError):
            return None
        if row < 1 or col < 1:
            return None
        rows[row] = rows.get(row, 0) + 1
        count += 1
    if count != 11 or sorted(rows) != list(range(1, len(rows) + 1)):
        return None
    if rows.get(1) != 1:
        return None
    return tuple(rows[index] for index in sorted(rows))


def shape_key(shape: tuple[int, ...] | str | None) -> str | None:
    """Return the outfield formation key, e.g. ``4-2-3-1``."""
    if shape is None:
        return None
    if isinstance(shape, str):
        value = shape.strip()
        return value if SHAPE_RE.fullmatch(value) else None
    if len(shape) < 2:
        return None
    return "-".join(str(part) for part in shape[1:])


def formation_family(shape: tuple[int, ...] | str | None) -> str | None:
    """Return the back-line family for the shape, e.g. ``back_four``."""
    key = shape_key(shape)
    if not key:
        return None
    first = int(key.split("-", 1)[0])
    return {3: "back_three", 4: "back_four", 5: "back_five"}.get(first)


def role_for_grid(
    config: dict[str, Any],
    shape: tuple[int, ...] | str | None,
    grid: str | None,
) -> str | None:
    """Map a grid slot to a role code for a known formation shape."""
    key = shape_key(shape)
    if not key or not grid:
        return None
    rows = (config.get("formations") or {}).get(key)
    if not rows:
        return None
    try:
        row_text, col_text = str(grid).split(":", 1)
        row, col = int(row_text), int(col_text)
    except (TypeError, ValueError):
        return None
    if row < 1 or row > len(rows):
        return None
    slots = rows[row - 1]
    if col < 1 or col > len(slots):
        return None
    code = slots[col - 1]
    return str(code) if code else None


def shape_counts(config: dict[str, Any], shape: tuple[int, ...] | str | None) -> dict[str, int]:
    """Count the roles in a formation shape, for shape/balance analysis."""
    key = shape_key(shape)
    rows = (config.get("formations") or {}).get(key) if key else None
    roles = config.get("roles") or {}
    codes = [str(code) for row in (rows or []) for code in row]
    families = [str((roles.get(code) or {}).get("family") or "") for code in codes]
    return {
        "cb_count": families.count("centre_back"),
        "wing_back_count": families.count("wing_back"),
        "dm_count": families.count("defensive_midfield"),
        "forward_count": families.count("centre_forward"),
        "wide_forward_count": families.count("wide_forward"),
        "wide_midfield_count": families.count("wide_midfield"),
    }


def validate_config(config: dict[str, Any]) -> None:
    """Validate the role taxonomy and every formation map.

    Raises ``ValueError`` with a specific message. The CI guard calls this so a
    new role or formation cannot silently produce an unknown slot.
    """
    roles = config.get("roles")
    families = config.get("families")
    formations = config.get("formations")
    if not isinstance(roles, dict) or not roles:
        raise ValueError("roles must be a non-empty mapping")
    if not isinstance(families, dict) or not families:
        raise ValueError("families must be a non-empty mapping")
    if not isinstance(formations, dict) or not formations:
        raise ValueError("formations must be a non-empty mapping")

    for name, family in families.items():
        if not isinstance(family, dict) or not family.get("label"):
            raise ValueError(f"family {name!r} has no label")
        if not isinstance(family.get("order"), int):
            raise ValueError(f"family {name!r} has no integer order")

    orders: set[int] = set()
    for code, role in roles.items():
        if not isinstance(role, dict):
            raise ValueError(f"role {code!r} must be a mapping")
        if not role.get("label"):
            raise ValueError(f"role {code!r} has no label")
        if role.get("family") not in families:
            raise ValueError(f"role {code!r} uses unknown family {role.get('family')!r}")
        if role.get("side") not in SIDE_VALUES:
            raise ValueError(f"role {code!r} has invalid side {role.get('side')!r}")
        if not isinstance(role.get("order"), int):
            raise ValueError(f"role {code!r} has no integer order")
        if role["order"] in orders:
            raise ValueError(f"role {code!r} reuses order {role['order']}")
        orders.add(role["order"])

    for key, rows in formations.items():
        if not SHAPE_RE.fullmatch(str(key)):
            raise ValueError(f"formation key {key!r} is not a shape")
        parts = [int(part) for part in str(key).split("-")]
        if sum(parts) != 10:
            raise ValueError(f"formation {key!r} does not have ten outfield slots")
        if not isinstance(rows, list) or len(rows) != len(parts) + 1:
            raise ValueError(f"formation {key!r} has the wrong number of rows")
        if rows[0] != ["GK"]:
            raise ValueError(f"formation {key!r} must start with the goalkeeper")
        for index, (part, row) in enumerate(zip(parts, rows[1:], strict=True), start=2):
            if not isinstance(row, list) or len(row) != part:
                raise ValueError(f"formation {key!r} row {index} has the wrong length")
            for code in row:
                if code not in roles:
                    raise ValueError(f"formation {key!r} uses unknown role {code!r}")

    validate_career_config(config)


def validate_career_config(config: dict[str, Any]) -> None:
    """Validate the career-role policy and its family groups."""
    career = config.get("career")
    if not isinstance(career, dict):
        raise ValueError("career policy is missing")
    if not isinstance(career.get("seasons"), int) or career["seasons"] < 1:
        raise ValueError("career.seasons must be a positive integer")
    if (
        not isinstance(career.get("max_fixtures_per_player_season"), int)
        or career["max_fixtures_per_player_season"] < 1
    ):
        raise ValueError("career.max_fixtures_per_player_season must be positive")
    if not isinstance(career.get("target_starts"), int) or career["target_starts"] < 1:
        raise ValueError("career.target_starts must be positive")
    weights = career.get("season_weights")
    if not isinstance(weights, list) or len(weights) != career["seasons"]:
        raise ValueError("career.season_weights must match career.seasons")
    if any(not isinstance(weight, (int, float)) or weight <= 0 for weight in weights):
        raise ValueError("career.season_weights must be positive numbers")

    dominant = career.get("dominant")
    if not isinstance(dominant, dict):
        raise ValueError("career.dominant is missing")
    for field in ("min_family_starts", "max_secondary_roles"):
        if not isinstance(dominant.get(field), int) or dominant[field] < 0:
            raise ValueError(f"career.dominant.{field} must be a non-negative integer")
    for field in ("min_family_share", "min_margin", "min_secondary_share"):
        value = dominant.get(field)
        if not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError(f"career.dominant.{field} must be between 0 and 1")

    override = career.get("override")
    if not isinstance(override, dict):
        raise ValueError("career.override is missing")
    for field in ("min_aberdeen_starts", "min_career_starts", "min_career_seasons"):
        if not isinstance(override.get(field), int) or override[field] < 0:
            raise ValueError(f"career.override.{field} must be a non-negative integer")
    for field in ("min_aberdeen_share", "max_career_share_of_current_family"):
        value = override.get(field)
        if not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError(f"career.override.{field} must be between 0 and 1")

    groups = career.get("family_groups")
    families = set((config.get("families") or {}).keys())
    if not isinstance(groups, dict) or not groups:
        raise ValueError("career.family_groups is missing")
    assigned: list[str] = []
    for name, members in groups.items():
        if not isinstance(members, list) or not members:
            raise ValueError(f"career.family_groups.{name} must be a non-empty list")
        for member in members:
            if member not in families:
                raise ValueError(f"career.family_groups.{name} uses unknown family {member!r}")
            assigned.append(str(member))
    if sorted(assigned) != sorted(families):
        raise ValueError("career.family_groups must cover every family exactly once")

    slots = career.get("slots")
    if not isinstance(slots, dict) or not slots:
        raise ValueError("career.slots is missing")
    assigned_roles: list[str] = []
    for name, slot in slots.items():
        if not isinstance(slot, dict):
            raise ValueError(f"career.slots.{name} must be a mapping")
        for field in ("label", "fm"):
            if not slot.get(field):
                raise ValueError(f"career.slots.{name} has no {field}")
        if slot.get("side") not in {None, "left", "centre", "right"}:
            raise ValueError(f"career.slots.{name} has invalid side")
        groups = slot.get("groups")
        if not isinstance(groups, list) or not groups:
            raise ValueError(f"career.slots.{name} has no groups")
        if any(
            group not in {"goalkeeper", "defender", "midfielder", "attacker"} for group in groups
        ):
            raise ValueError(f"career.slots.{name} has an invalid group")
        if not isinstance(slot.get("roles"), list) or not slot["roles"]:
            raise ValueError(f"career.slots.{name} has no roles")
        for code in slot["roles"]:
            if code not in (config.get("roles") or {}):
                raise ValueError(f"career.slots.{name} uses unknown role {code!r}")
            assigned_roles.append(str(code))
        if not isinstance(slot.get("order"), int):
            raise ValueError(f"career.slots.{name} has no integer order")
    if sorted(assigned_roles) != sorted((config.get("roles") or {}).keys()):
        raise ValueError("career.slots must cover every role exactly once")
    eligibility = career.get("eligibility")
    if not isinstance(eligibility, dict):
        raise ValueError("career.eligibility is missing")
    for field in ("secondary_min_share",):
        value = eligibility.get(field)
        if not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError(f"career.eligibility.{field} must be between 0 and 1")
    for field in ("secondary_min_starts", "stretch_min_starts"):
        value = eligibility.get(field)
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"career.eligibility.{field} must be a non-negative integer")

    backfill = career.get("backfill")
    if not isinstance(backfill, dict):
        raise ValueError("career.backfill is missing")
    if (
        not isinstance(backfill.get("max_requests_per_run"), int)
        or backfill["max_requests_per_run"] < 1
    ):
        raise ValueError("career.backfill.max_requests_per_run must be positive")
    if (
        not isinstance(backfill.get("request_interval_seconds"), (int, float))
        or backfill["request_interval_seconds"] < 0
    ):
        raise ValueError("career.backfill.request_interval_seconds must be non-negative")


def is_defensive_family(family: str | None) -> bool:
    return str(family) in DEFENSIVE_FAMILIES


def role_label(config: dict[str, Any], code: str | None) -> str | None:
    if not code:
        return None
    return str(((config.get("roles") or {}).get(code) or {}).get("label") or code)


def role_family(config: dict[str, Any], code: str | None) -> str | None:
    if not code:
        return None
    return (config.get("roles") or {}).get(code, {}).get("family")


def role_side(config: dict[str, Any], code: str | None) -> str | None:
    if not code:
        return None
    return (config.get("roles") or {}).get(code, {}).get("side")


def family_label(config: dict[str, Any], family: str | None) -> str | None:
    if not family:
        return None
    return str(((config.get("families") or {}).get(family) or {}).get("label") or family)


def _role_order(config: dict[str, Any], code: str) -> int:
    return int(((config.get("roles") or {}).get(code) or {}).get("order") or 999)


def _family_order(config: dict[str, Any], family: str) -> int:
    return int(((config.get("families") or {}).get(family) or {}).get("order") or 999)


def sorted_role_rows(
    rows: Iterable[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            -int(row.get("starts") or 0),
            -int(row.get("minutes") or 0),
            _role_order(config, str(row.get("code") or "")),
        ),
    )


def primary_role(
    rows: Iterable[dict[str, Any]], config: dict[str, Any]
) -> tuple[str | None, str | None]:
    """Choose the primary role family and role by starts, minutes, config order."""
    items = [row for row in rows if row.get("code")]
    if not items:
        return None, None
    families: dict[str, dict[str, int]] = {}
    for row in items:
        code = str(row["code"])
        family = role_family(config, code)
        if not family:
            continue
        bucket = families.setdefault(family, {"starts": 0, "minutes": 0})
        bucket["starts"] += int(row.get("starts") or 0)
        bucket["minutes"] += int(row.get("minutes") or 0)
    if not families:
        return None, None
    family = max(
        families,
        key=lambda name: (
            families[name]["starts"],
            families[name]["minutes"],
            -_family_order(config, name),
        ),
    )
    family_rows = [row for row in items if role_family(config, str(row["code"])) == family]
    winner = max(
        family_rows,
        key=lambda row: (
            int(row.get("starts") or 0),
            int(row.get("minutes") or 0),
            -_role_order(config, str(row["code"])),
        ),
    )
    return str(winner["code"]), family


__all__ = [
    "DEFENSIVE_FAMILIES",
    "family_label",
    "formation_family",
    "is_defensive_family",
    "primary_role",
    "role_family",
    "role_for_grid",
    "role_label",
    "role_side",
    "shape_counts",
    "shape_from_formation",
    "shape_from_grid",
    "shape_key",
    "sorted_role_rows",
    "validate_career_config",
    "validate_config",
]
