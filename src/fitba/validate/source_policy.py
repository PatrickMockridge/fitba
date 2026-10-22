"""Shared publication-source policy.

`no_publication` sources may be read manually as a finding aid, but a published
payload must never cite their ids or hosts. This module is deliberately small so
the transfer and history guards use the same rule.
"""

from __future__ import annotations

from fitba.settings import source_registry


def no_publication_tokens() -> tuple[set[str], set[str]]:
    ids: set[str] = set()
    hosts: set[str] = {"bbc.co.uk", "bbc.com"}
    for source_id, source in (source_registry().get("sources") or {}).items():
        if source.get("lane") != "no_publication":
            continue
        ids.add(source_id)
        for field in ("url", "base_url"):
            url = str(source.get(field) or "")
            if "://" in url:
                hosts.add(url.split("://", 1)[1].split("/", 1)[0].removeprefix("www."))
    return ids, hosts


def is_blocked_url(url: str, hosts: set[str]) -> bool:
    lower = str(url).lower()
    return any(host in lower for host in hosts)


__all__ = ["is_blocked_url", "no_publication_tokens"]
