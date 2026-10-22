#!/usr/bin/env python3
"""Probe the data sources before building on them.

This is deliberately read-only and polite: one request per host where possible,
no credentials required for the free probes, and no bypass of bot protection.
Results are written to reports/source-probes/{date}.json.

Usage:
    uv run python scripts/probe_source.py
    uv run python scripts/probe_source.py --deep   # read pannadata schema too
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "source-probes"
USER_AGENT = "fitba/0.1 (+https://github.com/PatrickMockridge/footballstats; research)"
TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def season_code(d: date | None = None) -> str:
    d = d or date.today()
    start = d.year if d.month >= 7 else d.year - 1
    return f"{start % 100:02d}{(start + 1) % 100:02d}"


def record(source: str, status: str, **details: object) -> dict[str, object]:
    return {
        "source": source,
        "status": status,
        "checked_at": datetime.now(UTC).isoformat(),
        **details,
    }


def probe_football_data(client: httpx.Client) -> list[dict[str, object]]:
    out = []
    code = season_code()
    for div in ("SC0", "SC1", "SC2", "SC3"):
        url = f"https://www.football-data.co.uk/mmz4281/{code}/{div}.csv"
        try:
            r = client.get(url, follow_redirects=True)
            lines = r.text.splitlines()
            header = lines[0].lstrip("﻿").split(",") if lines else []
            out.append(
                record(
                    "football_data_uk",
                    "ok" if r.status_code == 200 and len(lines) > 1 else "empty",
                    url=url,
                    http=r.status_code,
                    rows=max(0, len(lines) - 1),
                    fields=header[:16],
                )
            )
        except Exception as exc:  # noqa: BLE001 - probe reports, never crashes
            out.append(record("football_data_uk", "error", url=url, error=str(exc)))
    return out


def probe_pannadata(client: httpx.Client, deep: bool = False) -> dict[str, object]:
    # `releases/latest` points at the predictions release, not the Opta data
    # bundle. Search all releases for the `opta-latest` tag.
    url = "https://api.github.com/repos/peteowen1/pannadata/releases?per_page=100"
    try:
        r = client.get(url)
        if r.status_code != 200:
            return record("pannadata", "error", url=url, http=r.status_code)
        releases = r.json()
        payload = next(
            (release for release in releases if release.get("tag_name") == "opta-latest"),
            next(
                (
                    release
                    for release in releases
                    if any(
                        "Scottish_Premiership" in a.get("name", "")
                        for a in release.get("assets", [])
                    )
                ),
                None,
            ),
        )
        if payload is None:
            return record(
                "pannadata",
                "missing_scottish",
                url=url,
                releases=[release.get("tag_name") for release in releases],
            )
        assets = payload.get("assets", [])
        scottish = [a for a in assets if "Scottish_Premiership" in a.get("name", "")]
        detail: dict[str, object] = {
            "url": url,
            "tag": payload.get("tag_name"),
            "published_at": payload.get("published_at"),
            "asset_count": len(assets),
            "scottish_assets": [
                {"name": a["name"], "bytes": a.get("size"), "url": a.get("browser_download_url")}
                for a in scottish
            ],
        }
        events = next((a for a in scottish if a["name"].startswith("events_")), None)
        if deep and events:
            import io

            import polars as pl

            dl = client.get(events["browser_download_url"], follow_redirects=True)
            df = pl.read_parquet(io.BytesIO(dl.content))
            detail["events_schema"] = [str(c) for c in df.columns][:60]
            detail["events_rows"] = df.height
        return record("pannadata", "ok" if scottish else "missing_scottish", **detail)
    except Exception as exc:  # noqa: BLE001
        return record("pannadata", "error", url=url, error=str(exc))


def probe_fbref(client: httpx.Client) -> dict[str, object]:
    url = "https://fbref.com/en/comps/40/Scottish-Premiership-Stats"
    try:
        r = client.get(url)
        return record(
            "fbref",
            "ok" if r.status_code == 200 else "blocked",
            url=url,
            http=r.status_code,
            notes="Terms prohibit automated collection/redistribution; ingest disabled.",
        )
    except Exception as exc:  # noqa: BLE001
        return record("fbref", "error", url=url, error=str(exc))


def probe_datafc() -> dict[str, object]:
    try:
        version = importlib.metadata.version("datafc")
        return record(
            "sofascore_datafc",
            "installed",
            version=version,
            notes="Not executed; Sofascore terms prohibit automated access. Derived only.",
        )
    except importlib.metadata.PackageNotFoundError:
        return record("sofascore_datafc", "not_installed")


def probe_afc_news(client: httpx.Client) -> dict[str, object]:
    url = "https://www.afc.co.uk/en/news"
    try:
        r = client.get(url)
        ok = r.status_code == 200 and "articleCard" in r.text
        return record(
            "afc_news",
            "ok" if ok else "blocked",
            url=url,
            http=r.status_code,
            notes="Listing metadata only; article bodies and images are not copied.",
        )
    except Exception as exc:  # noqa: BLE001
        return record("afc_news", "error", url=url, error=str(exc))


def probe_spfl(client: httpx.Client) -> dict[str, object]:
    url = "https://spfl.co.uk/clubs/aberdeen/fixtures"
    try:
        r = client.get(url)
        ok = r.status_code == 200 and "fixtures-list__group" in r.text
        return record(
            "spfl",
            "ok" if ok else "blocked",
            url=url,
            http=r.status_code,
            notes="Official SPFL club feed; league and Premier Sports Cup fixtures/results.",
        )
    except Exception as exc:  # noqa: BLE001
        return record("spfl", "error", url=url, error=str(exc))


def probe_statsbomb(client: httpx.Client) -> dict[str, object]:
    url = "https://raw.githubusercontent.com/hudl/open-data/master/data/competitions.json"
    try:
        r = client.get(url)
        comps = r.json() if r.status_code == 200 else []
        scottish = [
            c
            for c in comps
            if "scot" in json.dumps(c).lower() or "aberdeen" in json.dumps(c).lower()
        ]
        return record(
            "statsbomb_open",
            "ok",
            url=url,
            http=r.status_code,
            competitions=len(comps),
            scottish_competitions=scottish,
        )
    except Exception as exc:  # noqa: BLE001
        return record("statsbomb_open", "error", url=url, error=str(exc))


def probe_clubelo(client: httpx.Client) -> dict[str, object]:
    url = f"https://api.clubelo.com/{date.today().isoformat()}"
    try:
        r = client.get(url)
        return record(
            "clubelo",
            "ok" if r.status_code == 200 and ";" in r.text[:2000] else "unexpected",
            url=url,
            http=r.status_code,
            bytes=len(r.content),
        )
    except Exception as exc:  # noqa: BLE001
        return record("clubelo", "error", url=url, error=str(exc))


def probe_optional_keys() -> list[dict[str, object]]:
    out = []
    for source, env in (
        ("sportmonks", "SPORTMONKS_API_KEY"),
        ("pitchapi", "PITCHAPI_KEY"),
        ("api_football", "API_FOOTBALL_KEY"),
    ):
        out.append(
            record(
                source,
                "key_present" if os.environ.get(env) else "no_key",
                env=env,
                notes="Enable and probe the endpoint once a key is configured.",
            )
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deep", action="store_true", help="Read the pannadata event schema")
    args = parser.parse_args()

    results: list[dict[str, object]] = []
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT) as client:
        results.extend(probe_football_data(client))
        results.append(probe_pannadata(client, deep=args.deep))
        results.append(probe_fbref(client))
        results.append(probe_datafc())
        results.append(probe_afc_news(client))
        results.append(probe_spfl(client))
        results.append(probe_statsbomb(client))
        results.append(probe_clubelo(client))
    results.extend(probe_optional_keys())

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{date.today().isoformat()}.json"
    out.write_text(json.dumps({"results": results}, indent=2) + "\n", encoding="utf-8")

    ok = sum(1 for r in results if r["status"] in {"ok", "installed", "key_present"})
    print(f"Wrote {out} ({ok}/{len(results)} healthy)")
    for r in results:
        print(f"  {r['source']:<20} {r['status']}")
    # A failed required source is a hard failure.
    required_ok = any(r["source"] == "football_data_uk" and r["status"] == "ok" for r in results)
    return 0 if required_ok else 1


if __name__ == "__main__":
    sys.exit(main())
