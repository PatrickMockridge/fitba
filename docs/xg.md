# fxG: fitba expected goals

**Status:** experimental model card. **Last reviewed:** 2026-10-22.
**Route:** `/analysis/xg/`. **Config:** `config/xg.yaml`.

## What fxG is

fxG is fitba's own expected-goals estimate from shots on target. It is not
provider xG, not Opta, not StatsBomb and not a result prediction.

The record has no shot coordinates. The model therefore estimates a
competition-season on-target conversion rate and multiplies it by the match's
shots on target:

```
p_on  = empirical-Bayes posterior mean of goals / shots on target
fxG   = shots_on_target × p_on
```

The prior is a Beta distribution with strength `prior_strength_sot`. Exact
competition-season rates are used when the season has enough shots on target;
otherwise the model falls back to the competition rate and then the global rate.

## Interval

The published 80% interval carries two things:

1. uncertainty in the conversion rate (Beta posterior quantiles);
2. match-to-match overdispersion, estimated from the model residuals and capped.

A single-match interval is wider than a naive binomial interval. An aggregate
interval is wider than a naive standard error because it sums the match-level
variance. The interval is a model interval, not a guarantee about a result.

## Provider xG

Provider xG is carried separately where available:

- football-data.co.uk 2026-27 SC0 `HxG`/`AxG` (54 matches at the 2026-10-22
  publish);
- API-Football `/fixtures/statistics` `expected_goals` where returned.

Provider xG is a benchmark. It is never averaged with fxG.

## Evaluation gate

The model is fit before 2026-27 and validated on 2026-27 provider xG. The gate
requires:

- mean bias within ±0.15 fxG per match;
- MAE at most 0.55;
- calibration slope between 0.70 and 1.30.

At the 2026-10-22 publish the gate fails (MAE and calibration slope outside the
thresholds). The payload therefore labels the model descriptive and the
fxG is not used as a performance verdict. This is a finding, not a
reason to loosen the gate.

The evaluation reports `matches` as distinct match keys and `team_rows` as the
two side-level observations per match. Every fixture page carries the gate status
and a link to the model page, so a failed gate is visible where the number is
used, not only on `/analysis/xg/`.

## Coverage

- League shots and shots on target: football-data.co.uk for every league match.
- Cup and European shots: API-Football where the provider returns statistics.
- Missing team statistics are `unavailable`; fxG is not zero.
- 2019-20 has no per-player provider stats; that does not stop league fxG.

## What fxG does not do

- It does not see shot location, goalkeeper position or game state.
- It does not adjust for opponent, home advantage or game state.
- It does not rank players.
- It does not predict results or justify a "deserved" verdict.
- It does not replace provider xG.

## Reproduce

```bash
uv run fitba xg --fit
uv run fitba xg --evaluate
uv run python scripts/check_xg.py
uv run python scripts/check_metrics.py --strict
```

The published payload is `web/data/generated/xg/aberdeen.json`. The registry
records the model family and the configuration parameters; the audit checks
presence and source.
