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

    estimate = payload.get("provider_estimate") or {}
    if not estimate:
        errors.append("missing provider_estimate")
    elif estimate.get("status") == "available":
        coefficients = estimate.get("coefficients") or {}
        if coefficients.get("intercept") is None or coefficients.get("slope") is None:
            errors.append("provider estimate has no coefficients")
        if not estimate.get("sample", {}).get("team_rows"):
            errors.append("provider estimate has no calibration sample")
        if estimate.get("in_sample_mae") is None or estimate.get("loocv_mae") is None:
            errors.append("provider estimate has no error diagnostics")
    elif estimate.get("status") == "unavailable":
        print("warning: provider-style estimate is unavailable")
    else:
        errors.append(f"unknown provider estimate status {estimate.get('status')!r}")

    splits = payload.get("manager_splits") or []
    if not splits:
        errors.append("missing manager splits")
    else:
        allowed = {"actual", "estimate", "actual_partial", "unavailable"}
        for row in splits:
            if row.get("provider_basis") not in allowed:
                errors.append(
                    f"manager split has invalid provider basis {row.get('provider_basis')!r}"
                )
            if row.get("provider_basis") == "actual" and row.get(
                "provider_actual_matches"
            ) != row.get("matches"):
                errors.append(
                    f"{row.get('manager')} {row.get('season')}: actual basis with partial rows"
                )
            if row.get("provider_basis") == "estimate" and row.get(
                "provider_estimate_matches"
            ) != row.get("matches"):
                errors.append(
                    f"{row.get('manager')} {row.get('season')}: estimate basis with partial rows"
                )
        for season in ("2025-26", "2026-27"):
            managers = [
                row
                for row in splits
                if row.get("season") == season and row.get("scope") == "manager_stint"
            ]
            if not managers:
                errors.append(f"no manager split for {season}")
            context = [
                row
                for row in splits
                if row.get("season") == season and row.get("scope") == "season_context"
            ]
            if season == "2025-26" and not context:
                errors.append("no full-season context row for 2025-26")
        robinson = [row for row in splits if row.get("person_id") == "stephen-robinson"]
        if not robinson:
            errors.append("no Robinson manager split")

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
