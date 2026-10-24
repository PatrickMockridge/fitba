# fxG: fitba expected goals

**Status:** experimental model card and reader guide. **Last reviewed:** 2026-10-24.
**Route:** `/analysis/xg/`. **Config:** `config/xg.yaml`.

## What xG is

Expected goals (xG) is a pre-shot estimate of the probability that a shot
becomes a goal. A provider assigns each shot a value between 0 and 1 from the
circumstances at the moment of the shot — location, distance and angle, body
part, shot type, the pattern of play, the assist, defensive pressure, the
goalkeeper and other players. A team's xG is the sum of its shots' values.

It is **not** a result prediction. A team with 2.0 xG will not score exactly two
goals; the same chances can produce none, one, three or more. One match is a
small sample. xG describes the quality of the chances, not the quality of the
finish, the goalkeeper, the tactics or the result.

Provider models are not identical. Opta, StatsBomb and other providers train
different models on different event data and legitimately disagree about the
same shot. Do not compare decimals across providers as if they were one scale.

## What xGOT is, and why it is not here

Post-shot xG (xGOT) asks a different question: given that a shot was on target
and where it crossed the goal line, how likely was it to score? It combines the
pre-shot chance with the execution — placement, trajectory and the goalkeeper's
position. It is used to describe finishing and shot-stopping.

fitba does not publish xGOT. The record has no goalmouth coordinates, no ball
trajectory and no shot-level freeze-frame. A post-shot number cannot be
reconstructed from team totals, and inventing one would be worse than leaving it
unavailable.

## What fitba publishes

Two separate measures:

1. **Provider xG** where the feed supplies it: football-data.co.uk 2026-27 SC0
   `HxG`/`AxG`, and API-Football `expected_goals` where returned. It is carried
   with its source. It is never averaged with fxG.
2. **fxG**, fitba's own **team-match estimate**. It is not provider xG, not a
   shot-level model and not a replacement for the provider. It exists because
   most historical pages have no provider xG, and because a transparent local
   estimate can carry its own uncertainty and coverage.

No missing value is shown as zero. Provider xG, shots, penalties and the ranges
are each `unavailable` when the record cannot support them.

**Scope and source.** The aggregate table, era and last-10 rows are Scottish
Premiership only. Cup and European fxG appears on the individual match pages
and is never added to the league aggregates. Current-season league shots and
shot zones come from API-Football, the same source as the fixture page;
historical league shots use football-data. The source is published on the match
row. `provider_xg_source` is separate from the shot-feature source and is
published per side. `goals − fxG` is a descriptive finishing comparison, not a
verdict, and own goals are not part of the shot model.

## The model

The record has team-match counts and events, not shot coordinates. The model is
therefore a **team-match aggregate estimate**, not a shot-level xG model. It
uses the best available licensed inputs:

- shots inside and outside the penalty box;
- shots on target, off target and blocked;
- non-shootout penalty attempts;
- the provider-xG target for the 2026-27 Premiership.

The selected specification is **zone volume plus on-target** (`D`):

```text
open_play_insidebox  = max(0, shots_insidebox − penalty_attempts)
open_play_outsidebox = max(0, shots_outsidebox)
open_play_sot        = max(0, shots_on_target − penalty_sot_subtracted)

fxG_open = 0.092658 × open_play_insidebox
         + 0.000000 × open_play_outsidebox
         + 0.100354 × open_play_sot

fxG = max(0, fxG_open) + 0.76 × penalty_attempts
```

The coefficients are fitted by ordinary least squares through the origin to
2026-27 Premiership team rows where football-data provider xG exists: 54
matches, 107 complete team rows after one shot-reconciliation failure. The
outside-box coefficient is zero at this fit; the model does not claim that
outside-box shots are worthless, only that this sample's provider xG is better
explained by the inside-box and on-target counts. The candidate table, including
the simpler open-play volume and zone-volume models, is published on the model
page.

Penalties are priced at a **fixed 0.76 xG** each, inside the commonly cited
0.76–0.79 range. Every non-shootout penalty attempt is removed from the
open-play counts and added back at that value. The feed does not always say
whether a missed penalty was saved or off target; the model treats a penalty as
on target when removing it from open-play counts and records the assumption.
This is a policy parameter, not a fitted coefficient.

If the zone features are missing, the model falls back to open-play volume
(shots on target and off target). If shots on target are missing, it falls back
to the competition-season conversion rate and labels the basis. A zero-shot
match is zero, not an intercept.

## Evaluation

The in-season gate is leave-one-match-out by match, leaving out both team rows
of a match:

| Test | Result |
|---|---|
| Matches / complete team rows | 54 / 107 |
| Bias | −0.013 |
| MAE | 0.383 |
| Calibration slope | 0.969 |
| R² | 0.649 |
| 80% model-range coverage | 0.813 |
| 80% goals-range coverage | 0.953 |

The gate thresholds are bias within ±0.15, MAE at most 0.55 and calibration
slope between 0.70 and 1.30. The gate passes, but this is an **in-season
calibration**, not an out-of-season holdout. The model remains descriptive.

A separate **transfer check** applies the 2026-27 model unchanged to 2025-26
Aberdeen Premiership rows with API-Football provider xG: 26 matches / 52 team
rows, bias −0.183, MAE 0.342, slope 1.138, model-range coverage 0.808. It
crosses both season and provider, covers 26 of 38 league matches, and is never
used for tuning. It is evidence about transfer, not a clean holdout.

The goals-range coverage is above the nominal 80% because goals are discrete and
the binomial approximation is conservative. A discrete central range can cover
more than its label; the coverage is published rather than hidden.

## The two ranges

The page publishes two 80% ranges. They answer different questions.

### Model range

How uncertain is the fxG estimate? The range is the 10th–90th percentile of
match-clustered bootstrap predictions plus a draw from the leave-one-match-out
residual pool. The bootstrap resamples whole matches, so both team rows stay
together. Aggregates sum the per-draw predictions and residuals before taking
quantiles; per-match ranges are **never** added together.

The old `fxg-2` aggregate interval was a sum of per-match intervals. It produced
an era interval of 142.98–503.00 around 332.29 fxG. The corrected model range is
305.36–334.22. The width now grows with the number of matches, not with the
number of intervals.

### Goals range

How many goals would the same chances produce? Open-play goals use a binomial
distribution, widened to a beta-binomial when the observed dispersion is above
one. Penalties are a separate binomial at 0.76. The two distributions are
convolved exactly. The range is the 10th–90th percentile. At aggregate level the
per-match distributions are convolved, so the variance is the sum of the
per-match variances and the width grows roughly with the square root of the
number of matches.

The goals range is not a prediction of the score and not a confidence interval
for team quality. It is the spread of goals from the same chances.

## Over- and underperformance

`Goals − fxG` is descriptive. A positive value means the team scored more than
the model's estimate; a negative value means fewer. The page also says whether
the observed goals are below, within or above the 80% goals range.

A single match is one sample. One season is still a small sample. Finishing
overperformance has a small repeatable skill component in the research, but most
large overperformances regress, and a single season is not enough to identify a
finisher. Style, shot selection, game state, opponent, own goals, deflections
and provider-model differences can all move the difference. The page therefore
does not call a team lucky, clinical, wasteful or deserving.

Penalties are counted separately. Own goals and shootouts are outside the shot
model. A team that scores from an own goal has goals that no xG model assigned
to a shot.

## Style

xG does not adjust for style. Style changes the chance profile:

- A low block can concede volume while limiting the quality of each chance.
- A high press can force low-quality shots, or create high-quality turnovers.
- A possession side can take many low-quality shots; a selective side can take
  fewer better ones.
- A team with elite finishers can outperform xG for longer than a team without
  them, but the model does not assume that.

Read **xG per shot with shot volume**. A low xG per shot and a high xG per shot
are different profiles, not a ranking. The model has no pressure, goalkeeper
position, body-part or game-state inputs, so it cannot price those differences.
That is a limitation, not a reason to adjust the number after the fact.

## Limitations and non-uses

- No shot coordinates, distance, angle, body part, pressure, goalkeeper
  position or post-shot placement.
- Team-match aggregate, not a shot-level xG model. It cannot price an individual
  chance.
- No xGOT, player xG, xA or PSxG.
- The coefficients are calibrated to 2026-27 football-data provider xG. The
  transfer check crosses providers and is informational.
- Applied to other competitions and seasons as a descriptive estimate. Zones are
  used where the record has them; older or incomplete matches fall back to
  volume or conversion and say so.
- Not a result prediction, not a betting model, not a player ranking and not a
  verdict on finishing, management or merit.
- Provider xG is a different model and is never blended into fxG.

## Reproduce

```bash
uv run fitba xg-enrich --season 2026-27 --max-requests 120
uv run fitba xg --fit --evaluate
uv run fitba publish --season current --profile public --require-validation
uv run python scripts/check_xg.py --published
uv run python scripts/check_metrics.py --strict
```

The published payload is `web/data/generated/xg/aberdeen.json`; the fixture
payload carries the same values under `xg`. The model card on `/analysis/xg/`
is the public companion to this document.

## References

These sources informed the method and its interpretation. No external event
data, coordinates, code or proprietary model output is ingested, copied or
redistributed. Provider xG is used only as the licensed calibration target and
benchmark.

- Opta Analyst, “What Are Expected Goals on Target (xGOT)?”:
  https://theanalyst.com/articles/what-are-expected-goals-on-target-xgot
- Stats Perform, “Introducing Expected Goals on Target (xGOT)”:
  https://www.statsperform.com/insights/introducing-expected-goals-on-target-xgot/
- StatsBomb, “Arsenal Aren’t This Good. Nor Are Dortmund. Here’s Why”:
  https://blogarchive.statsbomb.com/articles/soccer/arsenal-arent-this-good-nor-are-dortmund-heres-why/
- StatsBomb, “Are Manchester United and Burnley Just Regressing to the Mean?”:
  https://blogarchive.statsbomb.com/articles/soccer/are-manchester-united-and-burnley-just-regressing-to-the-mean/
- Robberechts, “How data availability affects the ability to learn good xG
  models” (KU Leuven):
  https://people.cs.kuleuven.be/~pieter.robberechts/repo/robberechts-mlsa20-xg.pdf
- Mead, O’Hare and McMenemy (2023), “Expected goals in football: Improving
  model performance and demonstrating value”, PLoS ONE:
  https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0282295
- “Shot-Level xG for Exact Outcome Prediction in Soccer: A Poisson Binomial
  Approach” (KU Leuven MLSA26):
  https://dtai.cs.kuleuven.be/events/MLSA26/papers/MLSA26_paper_385.pdf
- Heiniger (ETH), “Computing the Poisson Binomial Distribution for Soccer Match
  Outcomes”:
  https://www.research-collection.ethz.ch/bitstream/handle/20.500.11850/668637/Computing_the_Poisson_Binomial_Distribution_for_Soccer_Match_Outcomes_Aaron_Heiniger.pdf
- Stats Perform, “Shots, Pressure, Clarity and the Premier League”:
  https://www.statsperform.com/insights/shots-pressure-clarity-and-the-premier-league/
