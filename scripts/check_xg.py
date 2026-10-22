#!/usr/bin/env python3
"""Check the fxG model card, evaluation gate and payload consistency.

A failed provider-xG gate does not fail the build: it changes the publication
label and removes fxG from confidence verdicts. A missing evaluation, an
unsupported claimed pass, or a payload that cannot be rebuilt does fail.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fitba.publish.xg import build_xg_payload

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--published",
        action="store_true",
        help="Check the published payload instead of rebuilding from local data",
    )
    args = parser.parse_args()
    if args.published:
        path = ROOT / "web" / "data" / "generated" / "xg" / "aberdeen.json"
        if not path.exists():
            print(f"error: missing {path}")
            return 1
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = build_xg_payload()
    model = payload.get("model") or {}
    evaluation = payload.get("evaluation") or {}
    coverage = payload.get("coverage") or {}
    errors: list[str] = []

    if not model.get("model_id"):
        errors.append("missing model id")
    if not evaluation:
        errors.append("missing evaluation")
    if evaluation.get("status") == "pass" and not evaluation.get("passed"):
        errors.append("evaluation says pass but passed is false")
    if evaluation.get("status") == "fail" and evaluation.get("passed"):
        errors.append("evaluation says fail but passed is true")
    if coverage.get("matches", 0) <= 0:
        errors.append("no played fixtures in the fxG payload")
    if coverage.get("with_fxg", 0) <= 0:
        errors.append("no fixture has fxG")

    for error in errors:
        print(f"error: {error}")
    status = evaluation.get("status") or "unavailable"
    print(
        f"{'FAIL' if errors else 'PASS'} fxG check: model={model.get('model_id')} "
        f"gate={status} matches={coverage.get('matches')} "
        f"with_fxg={coverage.get('with_fxg')} errors={len(errors)}"
    )
    if status != "pass":
        print(
            "note: the gate has not passed; fxG is published as a descriptive "
            "shot expectation and is not used for a confidence verdict."
        )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
