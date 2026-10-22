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


_SMALL_WORDS = {
    "of",
    "the",
    "and",
    "de",
    "van",
    "der",
    "den",
    "di",
    "da",
    "do",
    "dos",
    "das",
    "el",
    "la",
    "le",
}


def _title_token(token: str, *, first: bool, last: bool) -> str:
    if not token:
        return token
    if token in {"ST", "ST.", "St", "St."}:
        return "St." if token.endswith(".") else "St"
    folded = token.casefold()
    if folded in {"fc", "afc", "fk", "sk", "if", "ifk", "bk", "ac", "sv", "cf", "sc"}:
        return folded.upper()
    if folded in _SMALL_WORDS and not first and not last:
        return folded
    if folded == "the" and first:
        return "The"
    if token.isupper():
        # Preserve short club acronyms (FC, HJK, IBV, IFK, SK, AC, ...).
        if len(token) <= 3:
            return token
        return token[:1].upper() + token[1:].lower()
    if token.islower():
        return token[:1].upper() + token[1:]
    return token


_CLUB_NAME_OVERRIDES = {
    "ado den haag": "ADO Den Haag",
    "free agent": "Free agent",
}


def titlecase_club_name(value: str) -> str:
    """Fix capitalisation for a club display name without inventing an identity.

    This is a presentation helper for unresolved provisional clubs. Resolved
    clubs should use the canonical name from reference/teams.yaml instead.
    """
    text = _SPACE.sub(" ", str(value or "").strip())
    if not text:
        return text
    if text.casefold() in _CLUB_NAME_OVERRIDES:
        return _CLUB_NAME_OVERRIDES[text.casefold()]
    tokens = text.split(" ")
    output = []
    for index, token in enumerate(tokens):
        if "-" in token:
            parts = token.split("-")
            token = "-".join(
                _title_token(
                    part,
                    first=index == 0 and part_index == 0,
                    last=index == len(tokens) - 1 and part_index == len(parts) - 1,
                )
                for part_index, part in enumerate(parts)
            )
        else:
            token = _title_token(
                token,
                first=index == 0,
                last=index == len(tokens) - 1,
            )
        output.append(token)
    return " ".join(output)


def slugify(value: str) -> str:
    return normalize_name(value).replace(" ", "-")


def team_slug(team_id: str) -> str:
    """sco:aberdeen -> aberdeen; keeps ids readable in match keys."""
    return team_id.split(":", 1)[-1]
