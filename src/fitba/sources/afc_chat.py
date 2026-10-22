"""AFC Chat — The Rumour Mill adapter.

Reference use only. The forum advertises ``search=yes, ai-train=no,
use=reference`` in robots.txt. This adapter samples the first page of recent
Rumour Mill topics to derive name mentions, cross-reference labels and
rule-based sentiment. It does not train a model on the text, does not follow
every page, and never publishes raw post bodies, usernames or quotes.

The feed is the topic index; post text is sampled from first pages only.
"""

from __future__ import annotations

import hashlib
import re
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import ClassVar

from bs4 import BeautifulSoup

from fitba.ingest.cache import cache_path, fetch
from fitba.sources.base import Capability, Lane

FEED_URL = "https://afc-chat.co.uk/forums/index.php?/forum/20-the-rumour-mill.xml/"
FORUM_URL = "https://afc-chat.co.uk/forums/index.php?/forum/20-the-rumour-mill/"
TOPIC_RE = re.compile(r"/topic/(\d+)-")


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _parse_rfc822(value: str) -> datetime | None:
    from email.utils import parsedate_to_datetime

    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _topic_id(url: str) -> str | None:
    match = TOPIC_RE.search(url)
    return match.group(1) if match else None


def download_feed(*, force: bool = False) -> Path:
    return fetch(
        FEED_URL,
        cache_path("afc_chat", "rumour-mill.xml"),
        ttl_hours=3,
        force=force,
        expected_marker="<rss",
        timeout=None,
    )


def download_topic(topic_id: str, url: str, *, force: bool = False) -> Path:
    return fetch(
        url,
        cache_path("afc_chat", "topics", f"{topic_id}.html"),
        ttl_hours=24,
        force=force,
        expected_marker="cPost",
    )


def parse_feed(payload: bytes) -> list[dict[str, object]]:
    """Parse the forum RSS into topic rows, newest first."""
    root = ET.fromstring(payload)
    topics: list[dict[str, object]] = []
    for item in root.iter("item"):
        url = (item.findtext("link") or "").strip()
        topic_id = _topic_id(url)
        if not url or topic_id is None:
            continue
        published = _parse_rfc822(item.findtext("pubDate") or "")
        topics.append(
            {
                "topic_id": topic_id,
                "title": _clean(item.findtext("title") or ""),
                "url": url,
                "published_at": published.isoformat() if published else None,
            }
        )
    topics.sort(key=lambda row: str(row.get("published_at") or ""), reverse=True)
    return topics


def _post_text(article: object) -> str:
    node = article.select_one('div[data-role="commentContent"]')  # type: ignore[attr-defined]
    if node is None:
        return ""
    # Quoted posts repeat someone else's words; remove them so sentiment and
    # name counts are not double-counted.
    for quoted in node.select("blockquote, .ipsQuote, script, style, figure, img"):
        quoted.decompose()
    return _clean(node.get_text(" ", strip=True))


def parse_topic(html: str) -> list[dict[str, object]]:
    """Parse the first page of a topic into post rows (text is internal only)."""
    soup = BeautifulSoup(html, "html.parser")
    posts: list[dict[str, object]] = []
    for article in soup.select("article.cPost"):
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


def sample_topics(
    *,
    limit: int = 8,
    days: int = 365,
    force: bool = False,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Return (topics, posts) from sampled first pages.

    Posts carry ``topic_id`` but no username. Sampling is capped and rate
    limited; it is not a crawler.
    """
    topics = parse_feed(download_feed(force=force).read_bytes())
    cutoff = datetime.now(UTC) - timedelta(days=days)
    selected = []
    for topic in topics:
        published = topic.get("published_at")
        if published:
            try:
                if datetime.fromisoformat(str(published)) < cutoff:
                    continue
            except ValueError:
                pass
        selected.append(topic)
        if len(selected) >= limit:
            break

    posts: list[dict[str, object]] = []
    for index, topic in enumerate(selected):
        if index:
            time.sleep(0.75)
        try:
            path = download_topic(str(topic["topic_id"]), str(topic["url"]), force=force)
        except Exception as exc:  # noqa: BLE001 - a failed topic is not fatal
            topic["error"] = str(exc)
            continue
        parsed = parse_topic(path.read_text(encoding="utf-8", errors="ignore"))
        for post in parsed:
            post["topic_id"] = topic["topic_id"]
        topic["sampled_posts"] = len(parsed)
        topic["latest_post"] = max((str(p["posted_at"]) for p in parsed), default=None)
        posts.extend(parsed)
    return selected, posts


def post_key(topic_id: str, comment_id: str) -> str:
    digest = hashlib.sha256(f"{topic_id}:{comment_id}".encode()).hexdigest()[:16]
    return f"afcchat:{digest}"


class AFCChat:
    name = "afc_chat"
    capabilities: ClassVar[set[Capability]] = {Capability.FAN_SIGNAL, Capability.SENTIMENT}
    lane = Lane.DERIVED_DISPLAY


__all__ = [
    "FEED_URL",
    "FORUM_URL",
    "AFCChat",
    "download_feed",
    "download_topic",
    "parse_feed",
    "parse_topic",
    "post_key",
    "sample_topics",
]
