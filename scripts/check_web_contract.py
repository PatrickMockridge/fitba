#!/usr/bin/env python3
"""Post-build identity and data-surface guard for the Fitba web app.

The guard reads the static export under web/out and the contract manifest at
web/contracts/surfaces.json. It never reads generated JSON and never counts
words: the contract protects evidence, not prose length.

A contracted surface must be present in the default rendered state. The guard
fails when a required table, metric, column, source, anchor or identity string
is missing, hidden behind a closed <details>, hidden with attributes or CSS, or
replaced by a question heading.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from bs4 import BeautifulSoup, Tag
except ImportError:  # pragma: no cover - exercised only in a broken environment
    BeautifulSoup = None  # type: ignore[assignment]
    Tag = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "web" / "out"
DEFAULT_MANIFEST = ROOT / "web" / "contracts" / "surfaces.json"

MARKER_RE = re.compile(r"^[a-z0-9]+(?:\.[a-z0-9-]+)+$")
QUESTION_RE = re.compile(
    r"^(?:what|who|why|how|when|where|which|can|should|do|does|is|are|will|would|could|has|have|did)\b.*\?\s*$",
    re.IGNORECASE,
)
BUDGET_KEYS = {
    "max_words",
    "min_words",
    "word_budget",
    "visible_words",
    "prose_budget",
    "word_limit",
    "word_count",
}
INDICATORS = {
    "basis",
    "confidence",
    "availability",
    "unknown",
    "freshness",
    "source",
}
ALLOWED_TOP = {"version", "identity", "site", "surfaces"}
ALLOWED_IDENTITY = {"line", "lede", "banned_phrases", "banned_headings"}
ALLOWED_SITE = {"markers", "copy", "links"}
ALLOWED_SURFACE = {"id", "path", "owners", "ci_states", "states"}
ALLOWED_STATE = {
    "markers",
    "columns",
    "indicators",
    "links",
    "anchors",
    "anchor_patterns",
    "headings",
    "copy",
    "metadata",
}
ALLOWED_MARKER = {"id", "min", "same_as"}
ALLOWED_HEADINGS = {"forbid_question", "h1", "forbid_text"}
ALLOWED_METADATA = {"title_contains", "description_contains"}


class ManifestError(Exception):
    """The manifest itself is invalid or tries to weaken the contract."""


@dataclass(frozen=True)
class Issue:
    route: str
    owners: tuple[str, ...]
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "route": self.route,
            "owners": list(self.owners),
            "message": self.message,
        }


def norm(text: str) -> str:
    """Normalise visible text for comparison."""
    value = " ".join(text.split()).strip().casefold()
    return (
        value.replace(chr(0x2019), "'")
        .replace(chr(0x2018), "'")
        .replace(chr(0x2014), "-")
        .replace(chr(0x2013), "-")
    )


def text_of(element: Any) -> str:
    return norm(element.get_text(" ", strip=True))


def hidden_reason(element: Any) -> str | None:
    """Return why an element is not in the default visible state, if it is not."""
    for parent in [element, *element.parents]:
        if parent is None or not isinstance(parent, Tag):
            continue
        if parent.name == "details" and not parent.has_attr("open"):
            return "closed <details>"
        if parent.has_attr("hidden"):
            return "hidden attribute"
        if str(parent.get("aria-hidden", "")).lower() == "true":
            return "aria-hidden"
        if parent.name in {"script", "style", "template", "noscript"}:
            return f"inside <{parent.name}>"
        classes = {str(value) for value in (parent.get("class") or [])}
        for marker in ("sr-only", "visually-hidden", "hidden"):
            if marker in classes:
                return f".{marker}"
        style = str(parent.get("style") or "")
        if re.search(r"display\s*:\s*none|visibility\s*:\s*hidden", style, re.IGNORECASE):
            return "inline hidden style"
    return None


def hidden_contracted_details(element: Any) -> Any | None:
    """Find a closed disclosure inside a contracted marker that contains data.

    Method and caveat disclosures are allowed to stay closed. A disclosure that
    contains a table, another contract marker or a provenance indicator is data,
    not method, and must be open by default.
    """
    for details in element.find_all("details"):
        if details.has_attr("open"):
            continue
        if details.find("table") is not None:
            return details
        if details.select_one("[data-contract], [data-contract-indicator]") is not None:
            return details
    return None


def markers_by_id(scope: Any) -> dict[str, list[Any]]:
    found: dict[str, list[Any]] = {}
    for element in scope.select("[data-contract]"):
        marker = str(element.get("data-contract") or "").strip()
        if marker:
            found.setdefault(marker, []).append(element)
    return found


def internal_path(href: str, base_path: str) -> str | None:
    if not href or href.startswith(("#", "mailto:", "tel:", "http://", "https://")):
        return None
    path = href.split("?", 1)[0].split("#", 1)[0]
    if not path:
        return None
    if base_path and (path == base_path or path.startswith(base_path + "/")):
        path = path[len(base_path) :]
    if not path.startswith("/"):
        path = "/" + path
    return path.rstrip("/") + "/" if path != "/" else "/"


def resolve_page(out: Path, route: str) -> Path:
    relative = route.strip("/")
    return out / relative / "index.html" if relative else out / "index.html"


def detect_base_path_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "link"]):
        value = str(tag.get("src") or tag.get("href") or "")
        match = re.search(r"(?P<base>/[^\"']*)?/_next/", value)
        if match:
            return (match.group("base") or "").rstrip("/")
    return ""


def detect_base_path(out: Path) -> str:
    candidates = [out / "index.html", *sorted(out.glob("*/index.html"))]
    for candidate in candidates:
        if not candidate.exists():
            continue
        detected = detect_base_path_from_html(candidate.read_text(encoding="utf-8"))
        if detected:
            return detected
    return ""


def _check_keys(mapping: dict[str, Any], allowed: set[str], where: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise ManifestError(f"{where}: unknown key(s) {', '.join(unknown)}")


def _reject_word_budgets(value: Any, where: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in BUDGET_KEYS or (
                "word" in lowered
                and any(part in lowered for part in ("max", "min", "budget", "limit", "count"))
            ):
                raise ManifestError(
                    f"{where}.{key}: word-count budgets are prohibited; "
                    "they incentivise deleting data"
                )
            _reject_word_budgets(item, f"{where}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_word_budgets(item, f"{where}[{index}]")


def validate_manifest(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise ManifestError("manifest must be a JSON object")
    _check_keys(document, ALLOWED_TOP, "manifest")
    _reject_word_budgets(document, "manifest")
    if document.get("version") != 1:
        raise ManifestError("manifest.version must be 1")

    identity = document.get("identity")
    if not isinstance(identity, dict):
        raise ManifestError("manifest.identity must be an object")
    _check_keys(identity, ALLOWED_IDENTITY, "manifest.identity")
    for key in ("line", "lede"):
        if not isinstance(identity.get(key), str) or not identity[key].strip():
            raise ManifestError(f"manifest.identity.{key} must be a non-empty string")
    for key in ("banned_phrases", "banned_headings"):
        if not isinstance(identity.get(key, []), list):
            raise ManifestError(f"manifest.identity.{key} must be a list")

    site = document.get("site")
    if not isinstance(site, dict):
        raise ManifestError("manifest.site must be an object")
    _check_keys(site, ALLOWED_SITE, "manifest.site")
    site_markers = site.get("markers")
    if not isinstance(site_markers, list) or not site_markers:
        raise ManifestError("manifest.site.markers must be a non-empty list")
    for marker in site_markers:
        if not isinstance(marker, str) or not MARKER_RE.match(marker):
            raise ManifestError(f"invalid site marker {marker!r}")

    surfaces = document.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        raise ManifestError("manifest.surfaces must be a non-empty list")

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for index, surface in enumerate(surfaces):
        where = f"manifest.surfaces[{index}]"
        if not isinstance(surface, dict):
            raise ManifestError(f"{where} must be an object")
        _check_keys(surface, ALLOWED_SURFACE, where)
        surface_id = surface.get("id")
        if not isinstance(surface_id, str) or not surface_id:
            raise ManifestError(f"{where}.id must be a non-empty string")
        if surface_id in seen_ids:
            raise ManifestError(f"{where}.id duplicates {surface_id!r}")
        seen_ids.add(surface_id)
        path = surface.get("path")
        if not isinstance(path, str) or not path.startswith("/") or not path.endswith("/"):
            raise ManifestError(f"{where}.path must start and end with '/'")
        if path in seen_paths:
            raise ManifestError(f"{where}.path duplicates {path!r}")
        seen_paths.add(path)
        owners = surface.get("owners")
        if not isinstance(owners, list) or not owners:
            raise ManifestError(f"{where}.owners must be a non-empty list")
        ci_states = surface.get("ci_states", [])
        if not isinstance(ci_states, list):
            raise ManifestError(f"{where}.ci_states must be a list")
        states = surface.get("states")
        if not isinstance(states, dict) or not states:
            raise ManifestError(f"{where}.states must be a non-empty object")
        for state_name, state in states.items():
            state_where = f"{where}.states.{state_name}"
            if not isinstance(state, dict):
                raise ManifestError(f"{state_where} must be an object")
            _check_keys(state, ALLOWED_STATE, state_where)
            marker_specs = state.get("markers", [])
            if not isinstance(marker_specs, list):
                raise ManifestError(f"{state_where}.markers must be a list")
            marker_ids: set[str] = set()
            for marker_index, spec in enumerate(marker_specs):
                spec_where = f"{state_where}.markers[{marker_index}]"
                if not isinstance(spec, dict):
                    raise ManifestError(f"{spec_where} must be an object")
                _check_keys(spec, ALLOWED_MARKER, spec_where)
                marker = spec.get("id")
                if not isinstance(marker, str) or not MARKER_RE.match(marker):
                    raise ManifestError(f"{spec_where}.id is malformed")
                if marker in marker_ids:
                    raise ManifestError(f"{spec_where}.id duplicates {marker!r}")
                marker_ids.add(marker)
                minimum = spec.get("min", 1)
                if not isinstance(minimum, int) or minimum < 1:
                    raise ManifestError(f"{spec_where}.min must be a positive integer")
                reference = spec.get("same_as")
                if reference is not None and (
                    not isinstance(reference, str) or not MARKER_RE.match(reference)
                ):
                    raise ManifestError(f"{spec_where}.same_as is malformed")
            for marker, reference in (
                (spec["id"], spec.get("same_as")) for spec in marker_specs if isinstance(spec, dict)
            ):
                if reference and reference not in marker_ids:
                    raise ManifestError(
                        f"{state_where}: marker {marker!r} references unknown same_as {reference!r}"
                    )
            columns = state.get("columns", {})
            if not isinstance(columns, dict):
                raise ManifestError(f"{state_where}.columns must be an object")
            for marker, headers in columns.items():
                if marker not in marker_ids:
                    raise ManifestError(
                        f"{state_where}.columns references unknown marker {marker!r}"
                    )
                if not isinstance(headers, list) or not headers:
                    raise ManifestError(f"{state_where}.columns.{marker} must be a non-empty list")
            indicators = state.get("indicators", {})
            if not isinstance(indicators, dict):
                raise ManifestError(f"{state_where}.indicators must be an object")
            for name, minimum in indicators.items():
                if name not in INDICATORS:
                    raise ManifestError(f"{state_where}.indicators: unknown indicator {name!r}")
                if not isinstance(minimum, int) or minimum < 0:
                    raise ManifestError(
                        f"{state_where}.indicators.{name} must be a non-negative integer"
                    )
            headings = state.get("headings", {})
            if not isinstance(headings, dict):
                raise ManifestError(f"{state_where}.headings must be an object")
            _check_keys(headings, ALLOWED_HEADINGS, f"{state_where}.headings")
            metadata = state.get("metadata", {})
            if not isinstance(metadata, dict):
                raise ManifestError(f"{state_where}.metadata must be an object")
            _check_keys(metadata, ALLOWED_METADATA, f"{state_where}.metadata")
            copy = state.get("copy", {})
            if not isinstance(copy, dict):
                raise ManifestError(f"{state_where}.copy must be an object")
            for marker, phrases in copy.items():
                if marker not in marker_ids:
                    raise ManifestError(f"{state_where}.copy references unknown marker {marker!r}")
                if not isinstance(phrases, list) or not phrases:
                    raise ManifestError(f"{state_where}.copy.{marker} must be a non-empty list")
            for key in ("links", "anchors", "anchor_patterns"):
                value = state.get(key, [] if key != "anchor_patterns" else {})
                if key == "anchor_patterns" and not isinstance(value, dict):
                    raise ManifestError(f"{state_where}.anchor_patterns must be an object")
                if key != "anchor_patterns" and not isinstance(value, list):
                    raise ManifestError(f"{state_where}.{key} must be a list")
        if any(state_name not in states for state_name in ci_states):
            raise ManifestError(f"{where}.ci_states references an unknown state")
    return document


def _table_headers(table: Any) -> list[str]:
    return [norm(header.get_text(" ", strip=True)) for header in table.find_all("th")]


def _headers_match(found: list[str], required: list[str]) -> bool:
    required_norm = [norm(value) for value in required]
    index = 0
    for header in found:
        if index < len(required_norm) and header == required_norm[index]:
            index += 1
    return index == len(required_norm)


def _required_indices(found: list[str], required: list[str]) -> list[int] | None:
    required_norm = [norm(value) for value in required]
    indices: list[int] = []
    cursor = 0
    for wanted in required_norm:
        while cursor < len(found) and found[cursor] != wanted:
            cursor += 1
        if cursor >= len(found):
            return None
        indices.append(cursor)
        cursor += 1
    return indices


def _table_has_values(table: Any, required: list[str]) -> bool:
    """Require at least one non-placeholder value in every contracted column."""
    headers = _table_headers(table)
    indices = _required_indices(headers, required)
    if indices is None:
        return False
    rows = [row for row in table.find_all("tr") if row.find("td") is not None]
    if not rows:
        return False
    placeholders = {"", "-", "n/a", "na"}
    for index in indices:
        values = []
        for row in rows:
            cells = row.find_all("td")
            if index < len(cells):
                values.append(norm(cells[index].get_text(" ", strip=True)))
        if not any(value not in placeholders for value in values):
            return False
    return True


def _tables_for(marker_element: Any) -> list[Any]:
    tables = list(marker_element.find_all("table"))
    if marker_element.name == "table":
        tables.insert(0, marker_element)
    return tables


def _check_meta_description(soup: Any) -> str:
    tag = soup.find("meta", attrs={"name": "description"})
    return str(tag.get("content") or "") if tag is not None else ""


def check_document(
    html: str,
    surface: dict[str, Any],
    identity: dict[str, Any],
    site: dict[str, Any],
    base_path: str,
    ci: bool,
) -> list[Issue]:
    soup = BeautifulSoup(html, "html.parser")
    route = surface["path"]
    owners = tuple(str(value) for value in surface["owners"])
    issues: list[Issue] = []

    def add(message: str) -> None:
        issues.append(Issue(route, owners, message))

    pages = soup.select("[data-contract-page]")
    if len(pages) != 1:
        add(f"expected exactly one [data-contract-page], found {len(pages)}")
        return issues
    page = pages[0]
    page_id = str(page.get("data-contract-page") or "")
    if page_id != surface["id"]:
        add(f"page marker is {page_id!r}, expected {surface['id']!r}")

    state_name = str(page.get("data-contract-state") or "full")
    states = surface["states"]
    if state_name not in states:
        add(f"unknown page state {state_name!r}")
        return issues
    if ci and state_name not in surface.get("ci_states", []):
        add(f"state {state_name!r} is not allowed in CI")
    state = states[state_name]

    markers = markers_by_id(page)

    for spec in state.get("markers", []):
        marker = spec["id"]
        found = markers.get(marker, [])
        minimum = int(spec.get("min", 1))
        reference = spec.get("same_as")
        if reference:
            expected = len(markers.get(reference, []))
            if expected == 0:
                add(f"marker {marker!r} references missing marker {reference!r}")
                continue
            if len(found) != expected:
                add(
                    f"marker {marker!r}: expected {expected} (one per {reference!r}), "
                    f"found {len(found)}"
                )
        elif len(found) < minimum:
            add(
                f"missing required marker {marker!r} "
                f"(expected at least {minimum}, found {len(found)})"
            )
        for element in found:
            if element.get("data-contract-optional") is not None:
                add(f"required marker {marker!r} is marked data-contract-optional")
            reason = hidden_reason(element)
            if reason:
                add(f"contracted data hidden: marker {marker!r} is in {reason}")
            hidden_details = hidden_contracted_details(element)
            if hidden_details is not None:
                add(
                    f"contracted data hidden: marker {marker!r} contains a closed "
                    "<details> with data"
                )
            expected_count = element.get("data-contract-count")
            count_of = element.get("data-contract-count-of")
            if expected_count is not None and count_of:
                try:
                    expected = int(str(expected_count))
                except ValueError:
                    add(f"marker {marker!r}: invalid data-contract-count {expected_count!r}")
                else:
                    actual = len(element.select(f'[data-contract="{count_of}"]'))
                    if actual != expected:
                        add(
                            f"marker {marker!r}: page declares {expected} {count_of!r} "
                            f"items but rendered {actual}"
                        )

    for marker, required_headers in state.get("columns", {}).items():
        found_tables = []
        for element in markers.get(marker, []):
            found_tables.extend(_tables_for(element))
        if not found_tables:
            add(f"marker {marker!r}: no table found for required columns")
            continue
        matches = sum(
            1
            for table in found_tables
            if _headers_match(_table_headers(table), required_headers)
            and _table_has_values(table, required_headers)
        )
        if matches == 0:
            available = "; ".join(
                ", ".join(_table_headers(table)) or "(no headers)" for table in found_tables[:3]
            )
            headers_present = any(
                _headers_match(_table_headers(table), required_headers) for table in found_tables
            )
            if headers_present:
                add(
                    f"marker {marker!r}: required columns {required_headers} "
                    "are present but contain no values"
                )
            else:
                add(
                    f"marker {marker!r}: missing required columns {required_headers}; "
                    f"found {available}"
                )

    for name, minimum in state.get("indicators", {}).items():
        selector = f'[data-contract-indicator="{name}"]'
        scope = soup if name == "freshness" else page
        count = sum(1 for element in scope.select(selector) if hidden_reason(element) is None)
        if count < minimum:
            add(f"indicator {name!r}: expected at least {minimum}, found {count}")

    for anchor in state.get("anchors", []):
        element = page.find(id=anchor)
        if element is None or hidden_reason(element):
            add(f"missing visible anchor #{anchor}")
    for pattern, minimum in state.get("anchor_patterns", {}).items():
        regex = re.compile(pattern)
        count = sum(
            1
            for element in page.select("[id]")
            if regex.search(str(element.get("id") or "")) and hidden_reason(element) is None
        )
        if count < minimum:
            add(f"anchor pattern {pattern!r}: expected at least {minimum}, found {count}")

    present_links = {
        path
        for element in page.select("a[href]")
        if (path := internal_path(str(element.get("href") or ""), base_path)) is not None
        and hidden_reason(element) is None
    }
    for link in state.get("links", []):
        if link not in present_links:
            add(f"missing required link {link!r}")

    for marker, phrases in state.get("copy", {}).items():
        nodes = markers.get(marker, [])
        if not nodes:
            continue
        visible = " ".join(text_of(node) for node in nodes)
        for phrase in phrases:
            if norm(phrase) not in visible:
                add(f"marker {marker!r}: missing required copy {phrase!r}")

    headings_config = state.get("headings", {})
    h1_nodes = [element for element in page.select("h1") if hidden_reason(element) is None]
    if len(h1_nodes) != 1:
        add(f"expected exactly one visible <h1>, found {len(h1_nodes)}")
    if h1_nodes:
        actual_h1 = text_of(h1_nodes[0])
        expected_h1 = headings_config.get("h1")
        if expected_h1 and actual_h1 != norm(str(expected_h1)):
            add(f"<h1> is {actual_h1!r}, expected {norm(str(expected_h1))!r}")
    forbidden_tags = {str(value).lower() for value in headings_config.get("forbid_question", [])}
    forbidden_headings = {norm(str(value)) for value in headings_config.get("forbid_text", [])}
    visible_headings = [
        heading for heading in page.select("h1, h2, h3, h4, h5, h6") if not hidden_reason(heading)
    ]
    levels = [int(heading.name[1]) for heading in visible_headings]
    if levels:
        if levels[0] != 1:
            add("first visible heading is not an h1")
        for previous, current in itertools.pairwise(levels):
            if current > previous + 1:
                add(f"heading level jumps from h{previous} to h{current}")
    banned_headings = [norm(str(value)) for value in identity.get("banned_headings", [])]
    for heading in page.select("h1, h2, h3"):
        if hidden_reason(heading):
            continue
        text = text_of(heading)
        if heading.name in forbidden_tags and (text.endswith("?") or QUESTION_RE.match(text)):
            add(f"interrogative heading not allowed: <{heading.name}>{text}</{heading.name}>")
        if text in forbidden_headings:
            add(f"forbidden heading text: {text!r}")
        if any(
            text == banned or text.startswith(banned + " ") or text.startswith(banned + ":")
            for banned in banned_headings
        ):
            add(f"banned fan-first heading: {text!r}")

    title = text_of(soup.title) if soup.title is not None else ""
    description = norm(_check_meta_description(soup))
    for key, target in (("title_contains", title), ("description_contains", description)):
        expected = state.get("metadata", {}).get(key)
        if expected and norm(str(expected)) not in target:
            add(f"metadata {key} missing {expected!r}")

    site_nodes: dict[str, list[Any]] = {}
    for marker in site.get("markers", []):
        nodes = soup.select(f'[data-contract="{marker}"]')
        site_nodes[marker] = nodes
        if not nodes:
            add(f"missing site marker {marker!r}")
        for node in nodes:
            reason = hidden_reason(node)
            if reason:
                add(f"site marker {marker!r} is in {reason}")
    for marker, phrases in site.get("copy", {}).items():
        nodes = site_nodes.get(marker, [])
        if not nodes:
            continue
        visible = " ".join(text_of(node) for node in nodes)
        for phrase in phrases:
            if norm(phrase) not in visible:
                add(f"site marker {marker!r}: missing required copy {phrase!r}")
    site_links = {
        path
        for element in soup.select("a[href]")
        if (path := internal_path(str(element.get("href") or ""), base_path)) is not None
        and hidden_reason(element) is None
    }
    for link in site.get("links", []):
        if link not in site_links:
            add(f"missing site link {link!r}")

    haystack_parts = [text_of(page), title, description]
    for selector in ("header", "footer"):
        node = soup.select_one(selector)
        if node is not None:
            haystack_parts.append(text_of(node))
    haystack = " ".join(haystack_parts)
    for phrase in identity.get("banned_phrases", []):
        escaped = re.escape(norm(str(phrase)))
        if re.search(rf"(?<!\w){escaped}(?!\w)", haystack):
            add(f"banned identity phrase {phrase!r}")

    return issues


def run(args: argparse.Namespace) -> int:
    if BeautifulSoup is None:
        print("beautifulsoup4 is required; run `uv sync --frozen`", file=sys.stderr)
        return 2
    manifest_path = Path(args.manifest)
    out = Path(args.out)
    if not manifest_path.exists():
        print(f"contract manifest not found: {manifest_path}", file=sys.stderr)
        return 2
    if not out.exists():
        print(f"rendered output not found: {out}; run `npm run build` first", file=sys.stderr)
        return 2
    try:
        document = validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
    except (ManifestError, json.JSONDecodeError) as error:
        print(f"invalid contract manifest: {error}", file=sys.stderr)
        return 2

    base_path = detect_base_path(out) if args.base_path == "auto" else args.base_path.rstrip("/")
    selected = [
        surface
        for surface in document["surfaces"]
        if not args.route or surface["path"] in args.route
    ]
    if args.route and len(selected) != len(args.route):
        missing = sorted(set(args.route) - {surface["path"] for surface in selected})
        print(f"unknown route(s): {', '.join(missing)}", file=sys.stderr)
        return 2

    issues: list[Issue] = []
    checked_markers = 0
    for surface in selected:
        page_path = resolve_page(out, surface["path"])
        if not page_path.exists():
            issues.append(
                Issue(
                    surface["path"],
                    tuple(surface["owners"]),
                    f"missing built page {page_path.relative_to(ROOT)}; run `npm run build`",
                )
            )
            continue
        page_issues = check_document(
            page_path.read_text(encoding="utf-8"),
            surface,
            document["identity"],
            document["site"],
            base_path,
            args.ci,
        )
        issues.extend(page_issues)
        checked_markers += sum(
            len(surface["states"][state]["markers"])
            for state in surface["states"]
            if state == "full"
        )

    if args.json:
        print(json.dumps([issue.as_dict() for issue in issues], indent=2))
    elif issues:
        print(f"Web contract check failed ({len(issues)} error{'s' if len(issues) != 1 else ''})")
        by_route: dict[str, list[Issue]] = {}
        for issue in issues:
            by_route.setdefault(issue.route, []).append(issue)
        for route, route_issues in by_route.items():
            owners = ", ".join(route_issues[0].owners)
            print(f"  {route} [{owners}]:")
            for issue in route_issues:
                print(f"    - {issue.message}")
        print()
        print("Hint: restore the contracted element, or propose a contract diff in")
        print("docs/page-contracts.md and web/contracts/surfaces.json. Do not edit the")
        print("checker to pass a deletion.")
    else:
        print(
            f"Web contract check passed ({len(selected)} surfaces, "
            f"{checked_markers} contracted markers)"
        )
    return 1 if issues else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--base-path",
        default="auto",
        help="URL base path used by the build; 'auto' detects it from _next assets",
    )
    parser.add_argument("--route", action="append", help="check only this route (repeatable)")
    parser.add_argument("--ci", action="store_true", help="enforce the manifest's ci_states")
    parser.add_argument("--json", action="store_true", help="emit machine-readable issues")
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
