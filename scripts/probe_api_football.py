#!/usr/bin/env python3
"""Key-test for the planned API-Football source.

Run with API_FOOTBALL_KEY set. This is the hard gate before buying a
subscription or building the cup layer. It makes a handful of read-only calls,
prints the Scottish competition IDs/coverage, and writes a JSON audit.

    API_FOOTBALL_KEY=... uv run python scripts/probe_api_football.py
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
# The key-test is run locally; .env is gitignored.
load_dotenv(ROOT / ".env")
OUT_DIR = ROOT / "reports"
BASE = "https://v3.football.api-sports.io"
TIMEOUT = httpx.Timeout(30.0, connect=15.0)


def _get(client: httpx.Client, path: str, **params: object) -> dict:
    response = client.get(path, params=params)
    payload = response.json()
    errors = payload.get("errors") or {}
    return {
        "http": response.status_code,
        "errors": errors,
        "results": payload.get("results"),
        "response": payload.get("response", []),
    }


def _count_rounds(fixtures: list[dict]) -> Counter:
    return Counter((item.get("league") or {}).get("round") or "unknown" for item in fixtures)


def main() -> int:
    key = os.environ.get("API_FOOTBALL_KEY")
    if not key:
        print("API_FOOTBALL_KEY is not set; no requests made.")
        print("Set it in the shell or a local .env, then rerun.")
        return 2

    audit: dict[str, object] = {
        "checked_at": datetime.now(UTC).isoformat(),
        "season": 2026,
        "checks": {},
    }
    with httpx.Client(
        base_url=BASE,
        headers={"x-apisports-key": key},
        timeout=TIMEOUT,
    ) as client:
        status = _get(client, "/status")
        leagues = _get(client, "/leagues", country="Scotland")
        audit["checks"]["status"] = {"http": status["http"], "errors": status["errors"]}
        audit["checks"]["leagues"] = {
            "http": leagues["http"],
            "errors": leagues["errors"],
            "count": len(leagues["response"]),
            "competitions": [
                {
                    "id": (item.get("league") or {}).get("id"),
                    "name": (item.get("league") or {}).get("name"),
                    "type": (item.get("league") or {}).get("type"),
                    "seasons": [
                        season.get("year")
                        for season in (item.get("seasons") or [])
                        if season.get("current")
                    ],
                }
                for item in leagues["response"]
            ],
        }

        scottish = audit["checks"]["leagues"]["competitions"]
        print("Scottish competitions returned:")
        for competition in scottish:
            print(
                f"  {competition['id']:>6}  {competition['name']}  "
                f"({competition['type']}, current seasons {competition['seasons']})"
            )

        def find(*needles: str) -> list[dict]:
            return [
                item
                for item in scottish
                if any(needle.lower() in (item["name"] or "").lower() for needle in needles)
            ]

        cups = {
            "league_cup": find("league cup"),
            "scottish_cup": find("scottish cup", "fa cup"),
        }
        for key_name, matches in cups.items():
            for competition in matches:
                league_id = competition["id"]
                fixtures = _get(
                    client,
                    "/fixtures",
                    league=league_id,
                    season=2026,
                )
                rounds = _get(
                    client,
                    "/fixtures/rounds",
                    league=league_id,
                    season=2026,
                )
                standings = _get(
                    client,
                    "/standings",
                    league=league_id,
                    season=2026,
                )
                rounds_count = _count_rounds(fixtures["response"])
                sample = [
                    {
                        "round": (item.get("league") or {}).get("round"),
                        "date": (item.get("fixture") or {}).get("date"),
                        "home": ((item.get("teams") or {}).get("home") or {}).get("name"),
                        "away": ((item.get("teams") or {}).get("away") or {}).get("name"),
                        "goals": item.get("goals"),
                        "score": item.get("score"),
                        "status": ((item.get("fixture") or {}).get("status") or {}).get("short"),
                    }
                    for item in fixtures["response"][:5]
                ]
                audit["checks"][f"{key_name}_{league_id}"] = {
                    "name": competition["name"],
                    "fixtures_http": fixtures["http"],
                    "fixtures_errors": fixtures["errors"],
                    "fixture_count": len(fixtures["response"]),
                    "rounds": dict(rounds_count),
                    "rounds_http": rounds["http"],
                    "rounds_errors": rounds["errors"],
                    "standings_http": standings["http"],
                    "standings_errors": standings["errors"],
                    "standings_count": len(standings["response"]),
                    "sample": sample,
                }
                print(
                    f"\n{competition['name']} (id {league_id}): "
                    f"{len(fixtures['response'])} fixtures; "
                    f"standings response {len(standings['response'])}; "
                    f"rounds {dict(rounds_count)}"
                )

        # A lower-tier fixture/player check: lineups and player stats.
        lower = find("championship", "league one")
        if lower:
            league_id = lower[0]["id"]
            fixtures = _get(client, "/fixtures", league=league_id, season=2026)
            completed = [
                item
                for item in fixtures["response"]
                if ((item.get("fixture") or {}).get("status") or {}).get("short")
                in {"FT", "AET", "PEN"}
            ]
            if completed:
                fixture_id = completed[-1]["fixture"]["id"]
                players = _get(client, "/fixtures/players", fixture=fixture_id)
                lineups = _get(client, "/fixtures/lineups", fixture=fixture_id)
                audit["checks"]["lower_tier_players"] = {
                    "league": lower[0]["name"],
                    "fixture": fixture_id,
                    "players_http": players["http"],
                    "players_count": len(players["response"]),
                    "lineups_http": lineups["http"],
                    "lineups_count": len(lineups["response"]),
                }
                print(
                    f"\nLower-tier sample {lower[0]['name']} fixture {fixture_id}: "
                    f"{len(players['response'])} player blocks, "
                    f"{len(lineups['response'])} lineups"
                )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"api-football-key-test-{date.today().isoformat()}.json"
    out.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
