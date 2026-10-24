"""Canonical player affiliation for rumours, forum signals and needs.

Affiliation answers "who is this player to Aberdeen?" It is not a credibility
or probability label. It is derived from the current squad payload and the
former-player register, never from a guess about a transfer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fitba.normalize.players import normalize_player_name

AFFILIATIONS = (
    "current_squad",
    "loan_out",
    "current_non_official",
    "former_player",
    "external_target",
    "unknown",
)

AFFILIATION_LABELS = {
    "current_squad": "Current squad",
    "loan_out": "On loan out",
    "current_non_official": "At Aberdeen (not official)",
    "former_player": "Former player",
    "external_target": "External target",
    "unknown": "Unknown",
}


def _name(value: Any) -> str:
    return " ".join(normalize_player_name(str(value or "")).split())


@dataclass
class AffiliationIndex:
    current_squad: set[str] = field(default_factory=set)
    loan_out: set[str] = field(default_factory=set)
    current_non_official: set[str] = field(default_factory=set)
    former_player: set[str] = field(default_factory=set)
    _name_to_key: dict[str, str] = field(default_factory=dict)
    _ambiguous_names: set[str] = field(default_factory=set)

    @classmethod
    def from_payloads(
        cls,
        *,
        squad: dict[str, Any] | None,
        former_keys: set[str] | None = None,
    ) -> AffiliationIndex:
        index = cls()
        squad = squad or {}
        for player in squad.get("players") or []:
            key = str(player.get("player_key") or "")
            if not key:
                continue
            status = str(player.get("status") or "")
            if status == "loan_out":
                index.loan_out.add(key)
            else:
                index.current_squad.add(key)
            index._add_name(player.get("name"), key)
            index._add_name(player.get("full_name"), key)
        former = set(former_keys or set())
        for key in former:
            index.former_player.add(key)
        for player in squad.get("excluded_players") or []:
            key = str(player.get("player_key") or "")
            if not key:
                continue
            if key in former:
                continue
            index.current_non_official.add(key)
            index._add_name(player.get("name"), key)
            index._add_name(player.get("full_name"), key)
        return index

    def add_former_names(self, names: dict[str, str]) -> None:
        """Add normalized full-name -> key entries for former players.

        ``names`` maps player key to display name. Ambiguous names are dropped.
        """
        for key, name in names.items():
            self._add_name(name, key)

    def _add_name(self, value: Any, key: str) -> None:
        normalized = _name(value)
        if not normalized:
            return
        existing = self._name_to_key.get(normalized)
        if existing is not None and existing != key:
            self._ambiguous_names.add(normalized)
            return
        self._name_to_key[normalized] = key

    def affiliation_for(
        self, player_key: Any, player_name: Any = None
    ) -> tuple[str, str]:
        """Return ``(affiliation, source)``.

        Source is ``key``, ``name_match`` or ``none``.
        """
        key = str(player_key or "")
        if key:
            if key in self.loan_out:
                return "loan_out", "key"
            if key in self.current_squad:
                return "current_squad", "key"
            if key in self.former_player:
                return "former_player", "key"
            if key in self.current_non_official:
                return "current_non_official", "key"
            return "external_target", "key"
        normalized = _name(player_name)
        if normalized and normalized not in self._ambiguous_names:
            matched = self._name_to_key.get(normalized)
            if matched:
                if matched in self.loan_out:
                    return "loan_out", "name_match"
                if matched in self.current_squad:
                    return "current_squad", "name_match"
                if matched in self.former_player:
                    return "former_player", "name_match"
                if matched in self.current_non_official:
                    return "current_non_official", "name_match"
        return "unknown", "none"

    def counts(self) -> dict[str, int]:
        return {
            "current_squad": len(self.current_squad),
            "loan_out": len(self.loan_out),
            "current_non_official": len(self.current_non_official),
            "former_player": len(self.former_player),
        }


def is_target(affiliation: str, direction: str | None) -> bool:
    return affiliation == "external_target" and str(direction or "") == "in"


def is_return_link(affiliation: str, direction: str | None) -> bool:
    return affiliation == "former_player" and str(direction or "") == "in"


__all__ = [
    "AFFILIATIONS",
    "AFFILIATION_LABELS",
    "AffiliationIndex",
    "is_return_link",
    "is_target",
]
