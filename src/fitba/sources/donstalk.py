"""DonsTalk — Aberdeen Football Club forum adapter.

Reference use only. The public robots.txt allows standard forum and topic URLs
and sets no crawl delay. This adapter samples the AFC board index and the
**latest page** of the public Next manager thread. It does not use search,
member pages or pagination beyond the latest page, and it never publishes raw
post bodies, usernames or quotes.

The Next manager topic is long-lived: page 1 is from 2022. Sampling page 1 would
publish obsolete names, so the adapter discovers the page count and fetches the
latest page. If page discovery fails it raises rather than falling back.
"""

from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path
from typing import ClassVar

from bs4 import BeautifulSoup

from fitba.ingest.cache import cache_path, fetch
from fitba.sources.base import Capability, Lane

BOARD_URL = "https://www.donstalk.co.uk/forum/7-aberdeen-football-club/"
NEXT_MANAGER_URL = "https://www.donstalk.co.uk/topic/9479-next-manager/"
TOPIC_RE = re.compile(r"/topic/(\d+)-")
PAGE_RE = re.compile(r"/page/(\d+)/?$")


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def download_board(*, force: bool = False) -> Path:
    return fetch(
        BOARD_URL,
        cache_path("donstalk", "board.html"),
        ttl_hours=3,
        force=force,
        expected_marker='data-ips-hook="topicRow"',
    )


def _topic_url(topic_url: str, page: int) -> str:
    base = topic_url.rstrip("/")
    if page <= 1:
        return f"{base}/"
    return f"{base}/page/{page}/"


def download_topic_page(
    topic_id: str,
    page: int,
    *,
    topic_url: str = NEXT_MANAGER_URL,
    force: bool = False,
) -> Path:
    return fetch(
        _topic_url(topic_url, page),
        cache_path("donstalk", "topics", f"{topic_id}-page-{page}.html"),
        ttl_hours=6,
        force=force,
        expected_marker='data-role="commentContent"',
    )


def parse_board(html: str) -> list[dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    topics: list[dict[str, object]] = []
    for row in soup.select('li[data-ips-hook="topicRow"]'):
        link = row.select_one("h4 a") or row.select_one('a[data-ips-hook="topicLink"]')
        if link is None:
            continue
        url = str(link.get("href") or "").strip()
        topic_id = TOPIC_RE.search(url)
        if topic_id is None:
            continue
        time_node = row.select_one("time[datetime]")
        topics.append(
            {
                "topic_id": topic_id.group(1),
                "title": _clean(link.get_text(" ", strip=True)),
                "url": url,
                "latest_post": str(time_node.get("datetime") or "") if time_node else None,
            }
        )
    return topics


def parse_page_count(html: str) -> int | None:
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one("[data-ipsPagination-pages], [data-pages]")
    if node is None:
        return None
    value = node.get("data-ipsPagination-pages") or node.get("data-pages")
    try:
        return int(str(value)) if value is not None else None
    except (TypeError, ValueError):
        return None


def _post_text(article: object) -> str:
    node = article.select_one('div[data-role="commentContent"]')  # type: ignore[attr-defined]
    if node is None:
        return ""
    for quoted in node.select("blockquote, .ipsQuote, script, style, figure, img"):
        quoted.decompose()
    return _clean(node.get_text(" ", strip=True))


def parse_topic(html: str) -> list[dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    posts: list[dict[str, object]] = []
    for article in soup.select("article.ipsEntry--post"):
        # The topic header repeats the opening 2022 post on every page.
        if "ipsEntry--first-simple" in (article.get("class") or []):
            continue
        time_node = article.select_one("time[datetime]")
        if time_node is None:
            continue
        comment_id = str(article.get("id") or "").removeprefix("elComment_")
        if not comment_id:
            content = article.select_one("[data-commentid]")
            comment_id = str(content.get("data-commentid")) if content else ""
        if not comment_id:
            continue
        posts.append(
            {
                "comment_id": comment_id,
                "posted_at": str(time_node.get("datetime") or ""),
                "text": _post_text(article),
            }
        )
    return posts


def sample(
    *,
    force: bool = False,
    topic_id: str = "9479",
    topic_url: str = NEXT_MANAGER_URL,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Return (topics, posts) from the AFC board and latest thread page."""
    board_path = download_board(force=force)
    board_topics = parse_board(board_path.read_text(encoding="utf-8", errors="ignore"))

    first_path = download_topic_page(topic_id, 1, topic_url=topic_url, force=force)
    time.sleep(0.75)
    first_html = first_path.read_text(encoding="utf-8", errors="ignore")
    page_count = parse_page_count(first_html)
    if page_count is None:
        raise RuntimeError("DonsTalk pagination could not be determined; refusing page 1")

    latest_page = max(1, page_count)
    latest_path = download_topic_page(topic_id, latest_page, topic_url=topic_url, force=force)
    latest_html = latest_path.read_text(encoding="utf-8", errors="ignore")
    posts = parse_topic(latest_html)
    for post in posts:
        post["topic_id"] = topic_id
    latest_time = max((str(post.get("posted_at") or "") for post in posts), default=None)
    topic = {
        "topic_id": topic_id,
        "title": "Next manager",
        "url": topic_url,
        "published_at": latest_time,
        "latest_post": latest_time,
        "sampled_posts": len(posts),
        "thread_page": latest_page,
        "thread_page_count": page_count,
        "latest_page_only": True,
        "single_page_only": True,
    }
    # Expose the board index as topic metadata; only the Next manager thread is
    # read for post text.
    selected = [topic]
    for row in board_topics:
        if str(row.get("topic_id")) == topic_id:
            continue
        selected.append({**row, "sampled_posts": 0, "thread_page": None})
    return selected, posts


def post_key(topic_id: str, comment_id: str) -> str:
    digest = hashlib.sha256(f"{topic_id}:{comment_id}".encode()).hexdigest()[:16]
    return f"donstalk:{digest}"


class DonsTalk:
    name = "donstalk"
    capabilities: ClassVar[set[Capability]] = {Capability.FAN_SIGNAL, Capability.SENTIMENT}
    lane = Lane.DERIVED_DISPLAY


__all__ = [
    "BOARD_URL",
    "NEXT_MANAGER_URL",
    "DonsTalk",
    "download_board",
    "download_topic_page",
    "parse_board",
    "parse_page_count",
    "parse_topic",
    "post_key",
    "sample",
]
