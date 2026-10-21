"""Polite HTTP downloads with a content-addressed cache.

No WAF bypass, no proxy rotation, no headless browsers. A source that blocks
us is a source we do not use.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from fitba.settings import CACHE_DIR

USER_AGENT = "fitba/0.1 (+https://github.com/PatrickMockridge/footballstats; research)"
TIMEOUT = httpx.Timeout(45.0, connect=15.0)
RETRY_STATUS = {429, 500, 502, 503, 504}


class SourceBlockedError(RuntimeError):
    """The source returned a page that is not the expected data."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _fresh(path: Path, ttl_hours: float | None) -> bool:
    if not path.exists():
        return False
    if ttl_hours is None:
        return True
    age = datetime.now(UTC).timestamp() - path.stat().st_mtime
    return age < ttl_hours * 3600


@retry(
    retry=retry_if_exception_type((httpx.HTTPError, SourceBlockedError)),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    reraise=True,
)
def fetch(
    url: str,
    dest: Path,
    *,
    ttl_hours: float | None = 6,
    force: bool = False,
    expected_marker: str | None = None,
    timeout: httpx.Timeout | None = None,
) -> Path:
    """Download ``url`` to ``dest`` unless a fresh copy exists.

    Writes a sidecar ``.meta.json`` with URL, timestamp, bytes and checksum.
    """
    if not force and _fresh(dest, ttl_hours):
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    with httpx.Client(headers=headers, timeout=timeout or TIMEOUT, follow_redirects=True) as client:
        response = client.get(url)
        if response.status_code in RETRY_STATUS:
            raise httpx.HTTPStatusError(
                f"retryable status {response.status_code}",
                request=response.request,
                response=response,
            )
        response.raise_for_status()
        payload = response.content
        if expected_marker is not None:
            head = payload[:4096].decode("utf-8", errors="ignore").lstrip("﻿")
            if expected_marker not in head:
                raise SourceBlockedError(
                    f"{url} did not contain expected marker {expected_marker!r}; "
                    "the source may be blocking automated access"
                )
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        tmp.write_bytes(payload)
        os.replace(tmp, dest)

    meta = {
        "url": url,
        "fetched_at": utc_now(),
        "bytes": len(payload),
        "sha256": sha256_bytes(payload),
    }
    dest.with_suffix(dest.suffix + ".meta.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    return dest


def cache_path(*parts: str) -> Path:
    return CACHE_DIR.joinpath(*parts)


def is_stale(path: Path, hours: float) -> bool:
    if not path.exists():
        return True
    return datetime.now(UTC) - datetime.fromtimestamp(path.stat().st_mtime, UTC) > timedelta(
        hours=hours
    )
