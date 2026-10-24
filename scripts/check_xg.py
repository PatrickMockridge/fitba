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

    if not model.get("specification"):
        errors.append("missing model specification")
    if not model.get("coefficients"):
        errors.append("missing model coefficients")
    if model.get("penalty_xg") is None:
        errors.append("missing penalty_xg")
    if not model.get("selection"):
        errors.append("missing candidate selection")
    transfer = model.get("transfer_check") or payload.get("transfer_evaluation") or {}
    if transfer.get("tuned_on_holdout") is not False:
        errors.append("transfer check is missing or was tuned on the holdout")
    if evaluation.get("model_interval_coverage") is None:
        errors.append("missing model-range coverage")
    if evaluation.get("goals_range_coverage") is None:
        errors.append("missing goals-range coverage")

    for row in payload.get("aggregates") or []:
        label = f"{row.get('scope')} {row.get('season')}"
        fxg = row.get("fxg")
        low = row.get("low")
        high = row.get("high")
        goals_low = row.get("goals_low")
        goals_high = row.get("goals_high")
        if fxg is None or low is None or high is None:
            errors.append(f"{label}: missing fxG/model range")
            continue
        if not low <= fxg <= high:
            errors.append(f"{label}: model range does not contain fxG")
        if high - low > 0.5 * fxg + 5:
            errors.append(f"{label}: model range looks like summed intervals")
        if goals_low is None or goals_high is None or goals_low > goals_high:
            errors.append(f"{label}: invalid goals range")
        if row.get("goals_minus_low") is not None and abs(
            float(row["goals_minus_low"]) - (float(goals_low) - float(fxg))
        ) > 0.01:
            errors.append(f"{label}: goals-minus lower bound does not equal goals_low - fxG")
        if row.get("goals_minus_high") is not None and abs(
            float(row["goals_minus_high"]) - (float(goals_high) - float(fxg))
        ) > 0.01:
            errors.append(f"{label}: goals-minus upper bound does not equal goals_high - fxG")
        if (
            row.get("shots")
            and row.get("xg_per_shot") is not None
            and abs(float(row["xg_per_shot"]) - float(fxg) / float(row["shots"])) > 0.002
        ):
            errors.append(f"{label}: xG per shot does not match fxG / shots")

    for row in payload.get("matches") or []:
        for side in ("for", "against"):
            fxg = row.get(f"fxg_{side}")
            low = row.get(f"fxg_{side}_low")
            high = row.get(f"fxg_{side}_high")
            goals_low = row.get(f"goals_{side}_low")
            goals_high = row.get(f"goals_{side}_high")
            if fxg is None:
                continue
            if low is None or high is None or not low <= fxg <= high:
                errors.append(f"{row.get('fixture_id')} {side}: invalid model range")
            if goals_low is None or goals_high is None or goals_low > goals_high:
                errors.append(f"{row.get('fixture_id')} {side}: invalid goals range")
            minus = row.get(f"goals_minus_fxg_{side}")
            goals = row.get("goals_for" if side == "for" else "goals_against")
            if (
                minus is not None
                and goals is not None
                and abs(float(minus) - (float(goals) - float(fxg))) > 0.01
            ):
                errors.append(f"{row.get('fixture_id')} {side}: goals minus fxG mismatch")

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
