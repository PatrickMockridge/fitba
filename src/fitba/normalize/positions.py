"""Position grouping shared by the squad and fan-signal layers."""

from __future__ import annotations


def squad_group(position: str | None) -> str | None:
    """Generic squad grouping for source labels that are not role-specific.

    API-Football often returns ``Defender`` / ``Midfielder`` / ``Attacker``
    without a side or role. The squad page groups at that level rather than
    inventing CB/FB or DM/AM.
    """
    if not position:
        return None
    value = position.casefold()
    if "goalkeeper" in value:
        return "GK"
    if "defender" in value or "back" in value:
        return "DEF"
    if "midfielder" in value:
        return "MID"
    if "attacker" in value or "forward" in value or "winger" in value or "striker" in value:
        return "FWD"
    return None


def position_group(position: str | None) -> str | None:
    """Map a source position label to the project's position groups."""
    if not position:
        return None
    value = position.casefold()
    if "goalkeeper" in value:
        return "GK"
    if "defender" in value or "back" in value:
        return "CB" if "centre" in value else "FB"
    if "midfielder" in value:
        return "DM" if "defensive" in value else "AM" if "attacking" in value else "CM"
    if "winger" in value:
        return "W"
    if "forward" in value or "striker" in value or "attack" in value:
        return "ST"
    return None


__all__ = ["position_group", "squad_group"]
