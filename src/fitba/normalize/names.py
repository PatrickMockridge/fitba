"""Name normalisation for entity resolution."""

from __future__ import annotations

import re
import unicodedata

_PUNCT = re.compile(r"[^\w\s]")
_SPACE = re.compile(r"\s+")

# Common football-name abbreviations. Keep only unambiguous expansions; do not
# strip City/County/Rovers because those distinguish clubs.
ABBREVIATIONS = {
    "utd": "united",
    "rvs": "rovers",
    "sth": "south",
    "ct": "caledonian thistle",
    "fc": "",
    "afc": "",
    "the": "",
}


def strip_accents(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", value) if not unicodedata.combining(char)
    )


def normalize_name(value: str) -> str:
    """Normalise a club/player name for alias matching.

    Example: "St. Mirren" -> "st mirren"; "Airdrie Utd" -> "airdrie united".
    """
    value = strip_accents(value).casefold().strip()
    value = value.replace("&", " and ")
    value = value.replace("'", "").replace("’", "")  # noqa: RUF001
    value = _PUNCT.sub(" ", value)
    tokens = [ABBREVIATIONS.get(token, token) for token in value.split()]
    return _SPACE.sub(" ", " ".join(tokens)).strip()


def slugify(value: str) -> str:
    return normalize_name(value).replace(" ", "-")


def team_slug(team_id: str) -> str:
    """sco:aberdeen -> aberdeen; keeps ids readable in match keys."""
    return team_id.split(":", 1)[-1]
