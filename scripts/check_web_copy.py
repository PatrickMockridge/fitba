#!/usr/bin/env python3
"""Check the fan-facing copy budget and table accessibility after a web build.

Visible words are counted inside <main>, excluding navigation, scripts, closed
<details> and .sr-only content. This is deliberately a presentation guard: it
does not inspect the generated JSON.
"""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "out"

BUDGETS = {
    "": {"words": 350, "badges": 0, "fine": 0, "label": "home"},
    "matchday": {"words": 750, "badges": 4, "fine": 1, "label": "matchday"},
    "themes": {"words": 800, "badges": 5, "fine": 1, "label": "themes"},
    "recruitment": {"words": 600, "badges": 4, "fine": 1, "label": "recruitment"},
    "transfers": {"words": 1100, "badges": 6, "fine": 2, "label": "transfers"},
    "loans": {"words": 600, "badges": 4, "fine": 1, "label": "loans"},
}

BANNED = (
    "door one",
    "door two",
    "the bridge",
    "run `uv run",
    "nationality unknown",
    "loan fee unknown",
    "status is a lifecycle label",
)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.main_depth = 0
        self.skip_stack: list[str] = []
        self.details: list[bool] = []
        self.visible: list[str] = []
        self.all_main: list[str] = []
        self.badges = 0
        self.fine = 0
        self.h1 = 0
        self.tables = 0
        self.table_captions = 0
        self.table_th_without_scope = 0
        self.regions = 0
        self.unnamed_regions = 0

    @property
    def in_main(self) -> bool:
        return self.main_depth > 0

    @property
    def closed(self) -> bool:
        return any(not opened for opened in self.details)

    @property
    def skipping(self) -> bool:
        return bool(self.skip_stack) or self.closed

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = (values.get("class") or "").split()
        if tag == "main":
            self.main_depth += 1
            return
        if tag in {"script", "style", "noscript"} or "sr-only" in classes:
            if tag == "caption" and self.in_main:
                self.table_captions += 1
            self.skip_stack.append(tag)
            return
        if tag == "details":
            self.details.append("open" in values)
            return
        if not self.in_main or self.skipping:
            return
        if tag == "h1":
            self.h1 += 1
        if "badge" in classes:
            self.badges += 1
        if "fine-print" in classes:
            self.fine += 1
        if tag == "table":
            self.tables += 1
        if tag == "caption":
            self.table_captions += 1
        if tag == "th" and not values.get("scope"):
            self.table_th_without_scope += 1
        if tag == "div" and "table-wrap" in classes:
            self.regions += 1
            if values.get("role") != "region" or not values.get("aria-label"):
                self.unnamed_regions += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "main" and self.main_depth:
            self.main_depth -= 1
        elif self.skip_stack and tag == self.skip_stack[-1]:
            self.skip_stack.pop()
        elif tag == "details" and self.details:
            self.details.pop()

    def handle_data(self, data: str) -> None:
        if not self.in_main or self.skip_stack:
            return
        text = " ".join(data.split())
        if not text:
            return
        self.all_main.append(text)
        if not self.closed:
            self.visible.append(text)


def check(route: str, budget: dict[str, object]) -> list[str]:
    path = OUT / route / "index.html" if route else OUT / "index.html"
    if not path.exists():
        return [f"{path} is missing; run npm run build"]
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    words = len(" ".join(parser.visible).split())
    errors: list[str] = []
    if words > int(budget["words"]):
        errors.append(
            f"/{route}/ has {words} visible words (budget {budget['words']})"
        )
    if parser.badges > int(budget["badges"]):
        errors.append(
            f"/{route}/ has {parser.badges} visible badges (budget {budget['badges']})"
        )
    if parser.fine > int(budget["fine"]):
        errors.append(
            f"/{route}/ has {parser.fine} visible fine-print blocks (budget {budget['fine']})"
        )
    if parser.h1 != 1:
        errors.append(f"/{route}/ has {parser.h1} visible h1 elements, expected 1")
    if parser.table_captions < parser.tables:
        errors.append(
            f"/{route}/ has {parser.tables} tables and {parser.table_captions} captions"
        )
    if parser.table_th_without_scope:
        errors.append(
            f"/{route}/ has {parser.table_th_without_scope} th elements without scope"
        )
    if parser.unnamed_regions:
        errors.append(
            f"/{route}/ has {parser.unnamed_regions} table regions without role/name"
        )
    full = " ".join(parser.all_main).casefold()
    for phrase in BANNED:
        if phrase in full:
            errors.append(f"/{route}/ contains banned phrase {phrase!r}")
    print(
        f"/{route or ''}/: {words} words, {parser.badges} badges, "
        f"{parser.fine} fine-print, {parser.h1} h1"
    )
    return errors


def main() -> int:
    errors: list[str] = []
    for route, budget in BUDGETS.items():
        errors.extend(check(route, budget))
    if errors:
        print("\nWeb copy check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Web copy check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
