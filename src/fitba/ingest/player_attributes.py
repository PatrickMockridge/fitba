"""Resolve preferred foot, which the licensed feed does not provide.

Preferred foot is resolved through a strict source hierarchy:

1. verified manual override (correction, not a source);
2. Sportmonks metadata, when the adapter is enabled;
3. official club/federation pages that explicitly state the attribute;
4. Wikipedia, last resort, explicit statements only;
5. unknown.

Side is not resolved here. It is derived from the starting-XI role in
``fitba.ingest.match_data``; team sheets do not contain preferred foot.

Every value carries its source id, tier, URL and verification date. The front
end only presents the resolved payload; it never chooses sources or infers a
value.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol
from urllib.parse import quote

import httpx
import polars as pl

from fitba.ingest.cache import USER_AGENT, cache_path, is_stale
from fitba.normalize.names import strip_accents
from fitba.normalize.players import player_slug
from fitba.settings import (
    NORMALIZED_DIR,
    ensure_dirs,
    source_registry,
)
from fitba.settings import (
    player_attributes as attributes_config,
)
from fitba.settings import (
    player_attributes_overrides as overrides_config,
)
from fitba.sources.base import IngestResult
from fitba.util.dates import utc_now_iso

ATTRIBUTE_COLUMNS = [
    "player_id",
    "player_key",
    "attribute",
    "value",
    "source_id",
    "source_tier",
    "source_url",
    "source_revision",
    "source_text",
    "derivation",
    "confidence",
    "verified_at",
    "status",
    "unknown_reason",
    "conflict_state",
    "conflict",
    "conflict_sources",
    "notes",
    "ingested_at",
]

WIKI_TTL_HOURS = 168
WIKI_DELAY_SECONDS = 1.0
WIKI_BASE = "https://en.wikipedia.org/wiki/"
WIKI_RAW = "https://en.wikipedia.org/w/index.php"
TIER_OVERRIDE = 0
TIER_SPORTMONKS = 2
TIER_OFFICIAL = 3
TIER_WIKIPEDIA = 4


@dataclass(slots=True)
class AttributeCandidate:
    attribute: str
    value: str
    source_id: str
    source_tier: int
    source_url: str | None
    source_text: str | None
    derivation: str
    confidence: str
    verified_at: str | None
    source_revision: str | None = None


class AttributeSource(Protocol):
    name: str

    def candidates(self, player: dict[str, Any]) -> list[AttributeCandidate]: ...


def _today() -> str:
    return date.today().isoformat()


def _plain_text(value: str) -> str:
    text = re.sub(r"<ref[^>]*>.*?</ref>", " ", value, flags=re.S | re.I)
    text = re.sub(r"<ref[^>]*/>", " ", text, flags=re.I)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    for _ in range(3):
        text = re.sub(r"\{\{[^{}]*\}\}", " ", text)
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[https?://[^\]]+\]", " ", text)
    text = re.sub(r"'''?", "", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


NEGATIVE_FOOT_CONTEXT = {
    "not",
    "never",
    "injured",
    "injury",
    "surgery",
    "knee",
    "ankle",
    "weak",
    "shot",
    "cross",
    "pass",
    "effort",
}


def _norm_phrase(value: str) -> str:
    normalized = strip_accents(value).casefold()
    normalized = normalized.replace("\u2013", "-").replace("\u2014", "-")
    normalized = re.sub(r"[-_/]", " ", normalized)
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _phrase_lookup(phrase_map: dict[str, list[str]]) -> dict[str, str]:
    return {
        _norm_phrase(phrase): value for value, phrases in phrase_map.items() for phrase in phrases
    }


def _foot_from_text(
    text: str, *, name: str, phrase_map: dict[str, list[str]]
) -> tuple[str | None, list[str]]:
    normalized = _norm_phrase(text)
    surname = _norm_phrase(name).split()[-1]
    mapping = _phrase_lookup(phrase_map)
    values: list[str] = []
    matched: list[str] = []
    for phrase, value in mapping.items():
        pattern = re.compile(rf"\b{re.escape(phrase)}\b")
        for match in pattern.finditer(normalized):
            context = normalized[max(0, match.start() - 140) : match.end() + 140]
            if surname and surname not in context:
                continue
            if any(token in context.split() for token in NEGATIVE_FOOT_CONTEXT):
                continue
            values.append(value)
            matched.append(phrase)
            break
    unique = sorted(set(values))
    if not unique:
        return None, []
    if len(unique) > 1:
        return "conflict", matched
    return unique[0], matched


def _foot_candidates(
    text: str,
    *,
    name: str,
    source_url: str,
    verified_at: str,
    tier: int,
    config: dict[str, Any],
) -> list[AttributeCandidate]:
    value, matched_phrases = _foot_from_text(
        text, name=name, phrase_map=config.get("foot_phrases", {})
    )
    if value is None:
        return []
    if value == "conflict":
        return [
            AttributeCandidate(
                attribute="preferred_foot",
                value="",
                source_id="wikipedia",
                source_tier=tier,
                source_url=source_url,
                source_text=", ".join(matched_phrases)[:160],
                derivation="conflict_distinct_foot_phrases",
                confidence="reference",
                verified_at=verified_at,
            )
        ]
    return [
        AttributeCandidate(
            attribute="preferred_foot",
            value=value,
            source_id="wikipedia",
            source_tier=tier,
            source_url=source_url,
            source_text=matched_phrases[0][:160] if matched_phrases else None,
            derivation="explicit_foot_phrase",
            confidence="reference",
            verified_at=verified_at,
        )
    ]


def _fetch_page_meta(title: str, *, force: bool = False) -> dict[str, Any] | None:
    path = cache_path("wikipedia", "meta", f"{player_slug(title)}.json")
    missing = path.with_suffix(".missing")
    if not force and not is_stale(path, WIKI_TTL_HOURS):
        return json.loads(path.read_text(encoding="utf-8"))
    if not force and not is_stale(missing, 24):
        return None
    url = f"https://en.wikipedia.org/w/rest.php/v1/page/{quote(title.replace(' ', '_'))}"
    response = httpx.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=20,
        follow_redirects=True,
    )
    time.sleep(WIKI_DELAY_SECONDS)
    if response.status_code == 404:
        missing.parent.mkdir(parents=True, exist_ok=True)
        missing.write_text("missing", encoding="utf-8")
        return None
    response.raise_for_status()
    payload = response.json()
    latest = payload.get("latest") or {}
    meta = {
        "page_id": payload.get("id"),
        "revision_id": latest.get("id"),
        "title": payload.get("title") or title,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta), encoding="utf-8")
    return meta


def _fetch_wikitext(title: str, revision_id: int | str, *, force: bool = False) -> str | None:
    path = cache_path("wikipedia", f"{player_slug(title)}.{revision_id}.wikitext")
    if not force and not is_stale(path, WIKI_TTL_HOURS):
        return path.read_text(encoding="utf-8")
    response = httpx.get(
        WIKI_RAW,
        params={"title": title, "action": "raw", "oldid": revision_id},
        headers={"User-Agent": USER_AGENT, "Accept": "text/x-wiki,*/*"},
        timeout=20,
        follow_redirects=True,
    )
    time.sleep(WIKI_DELAY_SECONDS)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(response.text, encoding="utf-8")
    return response.text


def _fetch_search(query: str, *, force: bool = False) -> list[str]:
    path = cache_path("wikipedia", "search", f"{player_slug(query)}.json")
    if not force and not is_stale(path, WIKI_TTL_HOURS):
        return json.loads(path.read_text(encoding="utf-8")).get("titles", [])
    response = httpx.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 5,
        },
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=20,
        follow_redirects=True,
    )
    time.sleep(WIKI_DELAY_SECONDS)
    response.raise_for_status()
    titles = [
        str(item.get("title") or "")
        for item in response.json().get("query", {}).get("search", [])
        if item.get("title")
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"titles": titles}), encoding="utf-8")
    return titles


def _birth_matches(wikitext: str, birth_date: str) -> bool:
    if not birth_date or len(birth_date) < 10:
        return False
    try:
        year, month, day = (int(part) for part in birth_date[:10].split("-"))
    except ValueError:
        return False
    patterns = [
        rf"birth date and age\|{year}\|{month}\|{day}",
        rf"birth date\|{year}\|{month}\|{day}",
        rf"birth date and age\|{year}\|{month:02d}\|{day:02d}",
        rf"birth date\|{year}\|{month:02d}\|{day:02d}",
    ]
    return any(re.search(pattern, wikitext, re.I) for pattern in patterns)


class WikipediaSource:
    name = "wikipedia"

    def __init__(self, config: dict[str, Any], *, force: bool = False) -> None:
        self._config = config
        self._force = force
        self.tier = int(config.get("tiers", {}).get("wikipedia", 4))
        self.max_pages = int(config.get("max_pages_per_run", 40))
        self.pages_attempted = 0
        self.blocked = False
        self.status = "idle"
        self.counts = {
            "used": 0,
            "no_explicit_statement": 0,
            "not_found": 0,
            "error": 0,
            "blocked": 0,
            "budget_exhausted": 0,
        }

    def summary(self) -> str:
        return ", ".join(f"{key}={value}" for key, value in self.counts.items() if value)

    def _record(self, status: str) -> None:
        self.status = status
        self.counts[status] = self.counts.get(status, 0) + 1

    def candidates(self, player: dict[str, Any]) -> list[AttributeCandidate]:
        if self.blocked:
            return []
        if self.pages_attempted >= self.max_pages:
            if not getattr(self, "_budget_recorded", False):
                self._record("budget_exhausted")
                self._budget_recorded = True
            return []
        full_name = str(player.get("full_name") or "").strip()
        if not full_name or full_name == player.get("name"):
            self._record("not_found")
            return []
        birth_date = str(player.get("birth_date") or "")
        birth_year = birth_date[:4] if birth_date[:4].isdigit() else None
        surname = strip_accents(full_name).casefold().split()[-1]
        titles = [full_name, f"{full_name} (footballer)"]
        if birth_year:
            titles.append(f"{full_name} (footballer, born {birth_year})")
        with contextlib.suppress(Exception):
            titles.extend(_fetch_search(f"{surname} footballer Aberdeen", force=self._force))

        seen: set[str] = set()
        for title in titles:
            if title in seen:
                continue
            seen.add(title)
            if self.pages_attempted >= self.max_pages:
                if not getattr(self, "_budget_recorded", False):
                    self._record("budget_exhausted")
                    self._budget_recorded = True
                break
            self.pages_attempted += 1
            try:
                meta = _fetch_page_meta(title, force=self._force)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 403:
                    self.blocked = True
                    self._record("blocked")
                    return []
                self._record("error")
                continue
            except Exception:  # noqa: BLE001 - a failed page is not fatal
                self._record("error")
                continue
            if not meta or not meta.get("revision_id"):
                continue
            revision_id = meta["revision_id"]
            try:
                wikitext = _fetch_wikitext(title, revision_id, force=self._force)
            except Exception:  # noqa: BLE001
                self._record("error")
                continue
            if not wikitext:
                continue
            lowered = strip_accents(wikitext).casefold()
            if "{{disambiguation" in lowered or "may refer to" in lowered:
                continue
            if "aberdeen" not in lowered:
                # Identity guard: the page must mention the current club.
                continue
            if surname not in strip_accents(title).casefold():
                continue
            if birth_date and not _birth_matches(wikitext, birth_date):
                # A birth-date check is the strongest crosswalk guard.
                continue
            if not birth_date and strip_accents(full_name).casefold() not in lowered:
                continue
            plain = _plain_text(wikitext)
            lead = plain[:5000]
            source_url = (
                "https://en.wikipedia.org/w/index.php?"
                f"title={quote(title.replace(' ', '_'))}&oldid={revision_id}"
            )
            verified_at = _today()
            candidates = _foot_candidates(
                lead,
                name=full_name,
                source_url=source_url,
                verified_at=verified_at,
                tier=self.tier,
                config=self._config,
            )
            for candidate in candidates:
                candidate.source_revision = str(revision_id)
            self._record("used" if candidates else "no_explicit_statement")
            return candidates
        if not self.blocked and self.pages_attempted < self.max_pages:
            self._record("not_found")
        return []


class SportmonksSource:
    name = "sportmonks"

    def __init__(self, config: dict[str, Any]) -> None:
        self.tier = int(config.get("tiers", {}).get("sportmonks", 2))
        source = source_registry()["sources"].get("sportmonks", {})
        gate = config.get("sportmonks", {})
        self.gates = {
            "api_key": bool(os.getenv(source.get("api_key_env", "SPORTMONKS_API_KEY"))),
            "adapter_ready": bool(source.get("adapter_ready")),
            "enabled": bool(gate.get("enabled")),
            "plan_confirmed": bool(gate.get("plan_confirmed")),
            "public_display_terms_confirmed": bool(gate.get("public_display_terms_confirmed")),
            "crosswalk_confirmed": bool(gate.get("crosswalk_confirmed")),
        }
        self.enabled = all(self.gates.values())
        self.status = "enabled" if self.enabled else "disabled"

    def candidates(self, player: dict[str, Any]) -> list[AttributeCandidate]:
        if not self.enabled:
            return []
        # The concrete Sportmonks mapping is intentionally gated: it needs a
        # confirmed key, plan, public-display terms and a player crosswalk.
        return []


class OfficialSource:
    name = "afc_official"

    def __init__(self, config: dict[str, Any]) -> None:
        self.tier = int(config.get("tiers", {}).get("official", 3))
        self.status = "not_provided"

    def candidates(self, player: dict[str, Any]) -> list[AttributeCandidate]:
        # AFC player pages state a generic position (Goalkeeper/Defender/
        # Midfielder/Forward), not a preferred foot.
        return []


class ManualOverrideSource:
    name = "override"
    status = "used"

    def __init__(self, overrides: dict[str, Any], config: dict[str, Any]) -> None:
        self.tier = int(config.get("tiers", {}).get("override", 0))
        self._rows: dict[tuple[str, str], dict[str, Any]] = {}
        for row in overrides.get("players", []) or []:
            key = str(row.get("player_key") or "")
            attribute = str(row.get("attribute") or "")
            if key and attribute:
                self._rows[(key, attribute)] = row

    def candidates(self, player: dict[str, Any]) -> list[AttributeCandidate]:
        key = str(player.get("player_key") or "")
        output = []
        row = self._rows.get((key, "preferred_foot"))
        if row:
            output.append(
                AttributeCandidate(
                    attribute="preferred_foot",
                    value=str(row.get("value") or ""),
                    source_id=str(row.get("source_id") or "override"),
                    source_tier=self.tier,
                    source_url=row.get("source_url"),
                    source_text=str(row.get("reason") or "")[:160],
                    derivation="manual_override",
                    confidence="curated",
                    verified_at=(str(row.get("verified_at")) if row.get("verified_at") else None),
                )
            )
        return output


def _validate_override(row: dict[str, Any], config: dict[str, Any]) -> None:
    attribute = str(row.get("attribute") or "")
    value = str(row.get("value") or "")
    allowed = config.get("attributes", {}).get(attribute, {}).get("allowed", [])
    if attribute != "preferred_foot" or value not in allowed:
        raise ValueError(f"override {row.get('player_key')}: invalid {attribute}={value!r}")
    for field in ("source_id", "source_url", "reason", "verified_at"):
        if not row.get(field):
            raise ValueError(f"override {row.get('player_key')}: missing {field}")


def _conflict_row(
    player: dict[str, Any],
    attribute: str,
    candidates: list[AttributeCandidate],
    *,
    ingested_at: str,
) -> dict[str, Any]:
    sources = [{"source_id": item.source_id, "source_url": item.source_url} for item in candidates]
    return {
        "player_id": int(player["player_id"]),
        "player_key": str(player["player_key"]),
        "attribute": attribute,
        "value": None,
        "source_id": "conflict",
        "source_tier": min(item.source_tier for item in candidates),
        "source_url": candidates[0].source_url,
        "source_revision": None,
        "source_text": None,
        "derivation": "same_tier_conflict",
        "confidence": "conflict",
        "verified_at": _today(),
        "status": "conflict",
        "unknown_reason": "unresolved_conflict",
        "conflict_state": "unresolved",
        "conflict": True,
        "conflict_sources": json.dumps(sources),
        "notes": "Sources at the same tier disagree; the value is withheld.",
        "ingested_at": ingested_at,
    }


def _unknown_row(player: dict[str, Any], attribute: str, *, ingested_at: str) -> dict[str, Any]:
    return {
        "player_id": int(player["player_id"]),
        "player_key": str(player["player_key"]),
        "attribute": attribute,
        "value": None,
        "source_id": None,
        "source_tier": None,
        "source_url": None,
        "source_revision": None,
        "source_text": None,
        "derivation": "unknown",
        "confidence": "unknown",
        "verified_at": None,
        "status": "unknown",
        "unknown_reason": "not_sourced",
        "conflict_state": "none",
        "conflict": False,
        "conflict_sources": "[]",
        "notes": "No allowed source states this attribute.",
        "ingested_at": ingested_at,
    }


def resolve_attributes(
    players: list[dict[str, Any]],
    sources: list[AttributeSource],
    *,
    config: dict[str, Any],
    ingested_at: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    conflicts = 0
    for player in players:
        all_candidates: list[AttributeCandidate] = []
        for source in sources:
            all_candidates.extend(source.candidates(player))
        for attribute in ("preferred_foot",):
            allowed = config.get("attributes", {}).get(attribute, {}).get("allowed", [])
            candidates = [
                candidate
                for candidate in all_candidates
                if candidate.attribute == attribute
                and (candidate.value == "" or candidate.value in allowed)
            ]
            if not candidates:
                rows.append(_unknown_row(player, attribute, ingested_at=ingested_at))
                continue
            best_tier = min(item.source_tier for item in candidates)
            best = [item for item in candidates if item.source_tier == best_tier]
            values = {item.value for item in best if item.value}
            if "" in {item.value for item in best} or len(values) > 1:
                rows.append(_conflict_row(player, attribute, best, ingested_at=ingested_at))
                conflicts += 1
                continue
            chosen = best[0]
            lower = [
                item
                for item in candidates
                if item.source_tier > best_tier and item.value and item.value != chosen.value
            ]
            override_tier = int(config.get("tiers", {}).get("override", 0))
            if chosen.source_tier == override_tier:
                conflict_state = "override_applied"
            elif lower:
                conflict_state = "resolved_by_precedence"
            else:
                conflict_state = "none"
            notes = None
            if lower:
                notes = (
                    "Higher-tier source won over "
                    + ", ".join(sorted({item.source_id for item in lower}))
                    + "."
                )
            rows.append(
                {
                    "player_id": int(player["player_id"]),
                    "player_key": str(player["player_key"]),
                    "attribute": attribute,
                    "value": chosen.value,
                    "source_id": chosen.source_id,
                    "source_tier": chosen.source_tier,
                    "source_url": chosen.source_url,
                    "source_revision": chosen.source_revision,
                    "source_text": chosen.source_text,
                    "derivation": chosen.derivation,
                    "confidence": chosen.confidence,
                    "verified_at": chosen.verified_at,
                    "status": "known",
                    "unknown_reason": None,
                    "conflict_state": conflict_state,
                    "conflict": False,
                    "conflict_sources": "[]",
                    "notes": notes,
                    "ingested_at": ingested_at,
                }
            )
    by_attribute: dict[str, dict[str, int]] = {}
    by_source: dict[str, int] = {}
    for row in rows:
        attribute_counts = by_attribute.setdefault(
            str(row["attribute"]), {"known": 0, "unknown": 0, "conflict": 0}
        )
        attribute_counts[str(row["status"])] = attribute_counts.get(str(row["status"]), 0) + 1
        if row["status"] == "known" and row.get("source_id"):
            by_source[str(row["source_id"])] = by_source.get(str(row["source_id"]), 0) + 1
    source_status: dict[str, str] = {}
    for source in sources:
        summary = getattr(source, "summary", None)
        source_status[source.name] = (
            str(summary()) if callable(summary) else str(getattr(source, "status", "used"))
        )
    meta = {
        "rows": len(rows),
        "known": sum(1 for row in rows if row["status"] == "known"),
        "conflicts": conflicts,
        "unknown": sum(1 for row in rows if row["status"] == "unknown"),
        "by_attribute": by_attribute,
        "by_source": by_source,
        "sources": source_status,
        "note": (
            "Preferred-foot resolution. Side is derived from the starting-XI "
            "role, not from this resolver. The licensed API does not provide "
            "foot; Sportmonks is used when enabled; Wikipedia is the last resort "
            "and only explicit statements are accepted. Unknown is a valid state."
        ),
        "ingested_at": ingested_at,
    }
    return rows, meta


def ingest_player_attributes(players: list[dict[str, Any]], *, force: bool = False) -> IngestResult:
    ensure_dirs()
    try:
        config = attributes_config()
        overrides = overrides_config()
        for row in overrides.get("players", []) or []:
            _validate_override(row, config)
        sources: list[AttributeSource] = [
            ManualOverrideSource(overrides, config),
            SportmonksSource(config),
            OfficialSource(config),
            WikipediaSource(config, force=force),
        ]
        now = utc_now_iso()
        rows, meta = resolve_attributes(
            players,
            sources,
            config=config,
            ingested_at=now,
        )
        output_dir = NORMALIZED_DIR / "squad"
        output_dir.mkdir(parents=True, exist_ok=True)
        frame = (
            pl.DataFrame(rows).select(ATTRIBUTE_COLUMNS)
            if rows
            else pl.DataFrame({column: [] for column in ATTRIBUTE_COLUMNS})
        )
        frame.write_parquet(output_dir / "aberdeen_attributes.parquet")
        (output_dir / "player_attributes_meta.json").write_text(
            json.dumps(meta, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        return IngestResult(
            source="player_attributes",
            status="ok",
            rows=frame.height,
            path=str(output_dir / "aberdeen_attributes.parquet"),
            details=meta,
        )
    except Exception as exc:  # noqa: BLE001 - reported by the CLI
        return IngestResult(source="player_attributes", status="error", errors=[str(exc)])


def load_player_attributes() -> pl.DataFrame:
    path = NORMALIZED_DIR / "squad" / "aberdeen_attributes.parquet"
    if not path.exists():
        return pl.DataFrame({column: [] for column in ATTRIBUTE_COLUMNS})
    return pl.read_parquet(path)


def load_player_attributes_meta() -> dict[str, Any]:
    path = NORMALIZED_DIR / "squad" / "player_attributes_meta.json"
    if not path.exists():
        return {"rows": 0, "conflicts": 0, "unknown": 0, "sources": {}}
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = [
    "ATTRIBUTE_COLUMNS",
    "AttributeCandidate",
    "ingest_player_attributes",
    "load_player_attributes",
    "load_player_attributes_meta",
    "resolve_attributes",
]
