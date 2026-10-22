"""Aberdeen FC news listing adapter.

The official site is server-rendered. We ingest the listing metadata only:
headline, category, publish date and canonical link. Article bodies and images
are not copied; every card links back to afc.co.uk.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import ClassVar

import polars as pl
from bs4 import BeautifulSoup

from fitba.ingest.cache import cache_path, fetch
from fitba.sources.base import Capability, IngestResult, Lane
from fitba.util.dates import utc_now_iso

NEWS_URL = "https://www.afc.co.uk/en/news"
NEWS_COLUMNS = [
    "article_id",
    "title",
    "category",
    "category_slug",
    "published_date",
    "url",
    "source_id",
    "ingested_at",
]


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _parse_date(value: str) -> date | None:
    value = _clean(value)
    try:
        return datetime.strptime(value, "%d %b '%y").date()
    except ValueError:
        return None


def download(*, force: bool = False) -> Path:
    return fetch(
        NEWS_URL,
        cache_path("afc", "news.html"),
        ttl_hours=1,
        force=force,
        expected_marker="articleCard",
    )


def parse_html(html: str) -> pl.DataFrame:
    soup = BeautifulSoup(html, "html.parser")
    now = utc_now_iso()
    rows: list[dict[str, object]] = []
    seen: set[str] = set()

    for article in soup.select("article[class*='articleCard']"):
        title_node = article.select_one("[data-testid='heading']")
        date_node = article.select_one("[data-testid='publish-date']")
        category_node = article.select_one("[data-testid='category-link']")
        link_node = next(
            (
                node
                for node in article.select("a[href^='/en/news/']")
                if "/category/" not in str(node.get("href", ""))
                and "/listing/" not in str(node.get("href", ""))
            ),
            None,
        )
        if title_node is None or date_node is None or link_node is None:
            continue
        href = str(link_node.get("href", "")).split("?", 1)[0].rstrip("/")
        if not href:
            continue
        article_id = href.rsplit("/", 1)[-1]
        if not article_id or article_id in seen:
            continue
        seen.add(article_id)
        rows.append(
            {
                "article_id": article_id,
                "title": _clean(title_node.get_text()),
                "category": _clean(category_node.get_text()) if category_node else "News",
                "category_slug": (
                    str(category_node.get("href", "")).rstrip("/").rsplit("/", 1)[-1]
                    if category_node
                    else "news"
                ),
                "published_date": _parse_date(date_node.get_text()),
                "url": f"https://www.afc.co.uk{href}",
                "source_id": "afc_news",
                "ingested_at": now,
            }
        )

    if not rows:
        return pl.DataFrame({column: [] for column in NEWS_COLUMNS})
    return pl.DataFrame(
        rows,
        schema_overrides={
            "article_id": pl.String,
            "title": pl.String,
            "category": pl.String,
            "category_slug": pl.String,
            "published_date": pl.Date,
            "url": pl.String,
            "source_id": pl.String,
            "ingested_at": pl.String,
        },
    ).select(NEWS_COLUMNS)


def load(*, force: bool = False) -> pl.DataFrame:
    return parse_html(download(force=force).read_text(encoding="utf-8"))


def ingest(*, force: bool = False) -> IngestResult:
    try:
        frame = load(force=force)
        return IngestResult(
            source="afc_news",
            status="ok",
            rows=frame.height,
            details={"url": NEWS_URL},
        )
    except Exception as exc:  # noqa: BLE001 - reported by the runner
        return IngestResult(source="afc_news", status="error", errors=[str(exc)])


class AFCNews:
    name = "afc_news"
    capabilities: ClassVar[set[Capability]] = {Capability.NEWS}
    lane = Lane.DERIVED_DISPLAY
