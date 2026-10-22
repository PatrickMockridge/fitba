#!/usr/bin/env python3
"""Report the Sportmonks player-attribute gate.

The adapter is deliberately disabled until the key, plan, public-display terms
and crosswalk are confirmed. This script makes no HTTP request until every gate
passes. It never prints the API token or a raw payload.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
CROSSWALK = ROOT / "reference" / "player_crosswalk.yaml"


def main() -> int:
    sources = yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8")).get(
        "sources", {}
    )
    policy = yaml.safe_load(
        (ROOT / "config" / "player_attributes.yaml").read_text(encoding="utf-8")
    )
    source = sources.get("sportmonks", {})
    gate = policy.get("sportmonks", {})
    gates = {
        "api_key": bool(os.getenv(source.get("api_key_env", "SPORTMONKS_API_KEY"))),
        "adapter_ready": bool(source.get("adapter_ready")),
        "enabled": bool(gate.get("enabled")),
        "plan_confirmed": bool(gate.get("plan_confirmed")),
        "public_display_terms_confirmed": bool(gate.get("public_display_terms_confirmed")),
        "crosswalk_confirmed": bool(gate.get("crosswalk_confirmed")),
    }
    print("Sportmonks player-attribute gate:")
    for name, passed in gates.items():
        print(f"  {'ok' if passed else 'blocked'}  {name}")

    crosswalk = (
        yaml.safe_load(CROSSWALK.read_text(encoding="utf-8")).get("players", [])
        if CROSSWALK.exists()
        else []
    )
    print(f"  crosswalk rows: {len(crosswalk)}")
    if not all(gates.values()) or not crosswalk:
        print("Adapter disabled. No request made.")
        return 0

    row = crosswalk[0]
    player_id = row.get("sportmonks_player_id")
    if not player_id:
        print("First crosswalk row has no sportmonks_player_id.")
        return 1
    token = os.getenv(source.get("api_key_env", "SPORTMONKS_API_KEY"))
    response = httpx.get(
        f"https://api.sportmonks.com/v3/football/players/{player_id}",
        params={
            "api_token": token,
            "include": "metadata;detailedPosition",
        },
        timeout=30,
    )
    print(f"HTTP {response.status_code}")
    if response.status_code != 200:
        return 1
    payload = response.json().get("data") or {}
    metadata = payload.get("metadata") or []
    detailed = payload.get("detailedposition") or payload.get("detailedPosition") or {}
    print(
        json.dumps(
            {
                "player_id": payload.get("id"),
                "metadata_count": len(metadata),
                "metadata_types": sorted(
                    {str(item.get("type_id")) for item in metadata if isinstance(item, dict)}
                ),
                "detailed_position": detailed.get("name") if isinstance(detailed, dict) else None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
