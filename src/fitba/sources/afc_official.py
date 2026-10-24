"""Canonical Aberdeen FC men's-team roster adapter.

One server-rendered page is read per refresh. The parser uses semantic markers
(``h2`` sections and ``data-component="ProfileCard"``) rather than hashed CSS
class names. It records names, shirt numbers, generic positions and the
official profile link; it does not copy article text or images.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from fitba.ingest.cache import cache_path, fetch
from fitba.util.dates import utc_now_iso

OFFICIAL_URL = "https://www.afc.co.uk/en/teams/mens"
OFFICIAL_CACHE = cache_path("afc_official", "mens.html")
SECTIONS = {"Goalkeepers", "Defenders", "Midfielders", "Forwards", "On loan", "Staff"}


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def download(*, force: bool = False) -> Path:
    return fetch(
        OFFICIAL_URL,
        OFFICIAL_CACHE,
        ttl_hours=12,
        force=force,
        expected_marker="ProfileCard",
    )


def _class_text(node: Any) -> str:
    classes = node.get("class") if node is not None else None
    return " ".join(str(value) for value in (classes or []))


def _card_player(card: Any, section: str, *, official_order: int) -> dict[str, Any] | None:
    link = card.select_one("a[href^='/en/teams/mens/']")
    if link is None:
        return None
    href = str(link.get("href") or "").split("?", 1)[0].rstrip("/")
    if not href or href.endswith("/mens"):
        return None
    first = card.find("span", class_=lambda value: "firstName" in str(value or ""))
    surname = card.find("span", class_=lambda value: "surname" in str(value or ""))
    if first is not None or surname is not None:
        first_text = first.get_text() if first else ""
        surname_text = surname.get_text() if surname else ""
        name = _clean(f"{first_text} {surname_text}")
    else:
        name = _clean(link.get_text())
    if not name:
        return None
    position_node = card.find(
        "span",
        class_=lambda value: "position" in str(value or "")
        and "profileCard" in str(value or ""),
    )
    number_node = card.find("span", class_=lambda value: "squadNumber" in str(value or ""))
    number_text = _clean(number_node.get_text()) if number_node else ""
    try:
        number = int(number_text)
    except ValueError:
        number = None
    return {
        "name": name,
        "number": number,
        "position": _clean(position_node.get_text()) if position_node else None,
        "section": section,
        "official_order": official_order,
        "href": href,
        "url": f"https://www.afc.co.uk{href}",
    }


def parse_html(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    players: list[dict[str, Any]] = []
    seen: set[str] = set()
    current_section: str | None = None
    for element in soup.find_all(True):
        if element.name == "h2":
            text = _clean(element.get_text())
            if text in SECTIONS:
                current_section = text
            continue
        if element.get("data-component") != "ProfileCard":
            continue
        if current_section is None or current_section == "Staff":
            continue
        player = _card_player(
            element, current_section, official_order=len(players)
        )
        if player is None or player["href"] in seen:
            continue
        seen.add(player["href"])
        players.append(player)
    return players


def load_roster(*, force: bool = False) -> dict[str, Any]:
    """Return the parsed official roster and its cache metadata."""
    try:
        path = download(force=force)
        html = path.read_text(encoding="utf-8")
        players = parse_html(html)
        meta_path = path.with_suffix(path.suffix + ".meta.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        if not players:
            return {
                "status": "unavailable",
                "source_url": OFFICIAL_URL,
                "fetched_at": meta.get("fetched_at") or utc_now_iso(),
                "players": [],
                "note": "The official men's team page contained no player cards.",
            }
        return {
            "status": "available",
            "source_url": OFFICIAL_URL,
            "fetched_at": meta.get("fetched_at") or utc_now_iso(),
            "players": players,
        }
    except Exception as error:  # noqa: BLE001 - the caller falls back visibly
        return {
            "status": "unavailable",
            "source_url": OFFICIAL_URL,
            "fetched_at": utc_now_iso(),
            "players": [],
            "note": f"Official roster fetch failed: {type(error).__name__}",
        }


__all__ = ["OFFICIAL_URL", "download", "load_roster", "parse_html"]
