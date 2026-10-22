# Scouting method

**Status:** method reference. Last reviewed 2026-10-21.

The scouting engine is deliberately explainable. It does not produce a single
"good player" verdict; it shows the components, the coverage and the uncertainty.

## Universe and positions

- Scottish pyramid: all four tiers.
- European pool: comparable markets plus fringe leagues Aberdeen have recruited
  from, including Slovenia, Albania, Hungary, Eastern Europe and Switzerland.
- Position groups are role families from the starting-XI team sheet:
  `GK`, `CB`, `FB`, `WB`, `DM`, `CM`, `AM`, `WM`, `WF`, `ST`. See
  [roles.md](roles.md).
- A player is compared within their role family, not across a generic “DEF” or
  “MID” pool. A left back is compared with left backs, a centre back with centre
  backs, a winger with wingers.
- Multi-position players get separate percentiles per role family; they are
  never averaged across families. A player without a starting-XI role is
  excluded from a role cohort and labelled, not silently grouped into the
  nearest bucket.

## Features

The feature registry is in `config/scouting/features.yaml`; the group weights are
in `config/scouting/weights.yaml`. Each feature records its required capability
(`match` or `event`) and direction.

If a feature is unavailable it is removed and the remaining weights are
renormalised. If more than **40% of the absolute weight** is missing, no composite
is produced; the player is marked "insufficient data".

## Shrinkage

Small samples are shrunk toward the positional mean:

- binomial rates: `(s + alpha) / (n + alpha + beta)` with an empirical prior;
- count rates: `(c + mu*k) / (exposure + k)`, with `k` around 450 minutes;
- goals over xG: shrunk over 900 minutes.

This prevents a few good matches from producing an extreme percentile.

## Normalisation

Within each `(league, season, position group)` cell:

1. require at least 25 players with at least 450 minutes, or fall back to a
   broader cell;
2. winsorise at the 1st/99th percentile;
3. compute a robust z-score using median and MAD, with defined fallbacks for zero
   MAD;
4. shrink the z-score toward the positional mean by effective minutes;
5. composite `Q = 100 * Phi(z_composite)`.

Raw league percentile and league-adjusted percentile are both shown.

## League strength

Measured Elo is preferred; otherwise a documented prior from
`config/scouting/leagues.yaml` is used. The adjustment is a z-score offset by
feature family, not a blanket multiplier. The confidence flag is `high` when Elo
is available and `low` for a prior. A sensitivity check at ±50% of the prior is
shown rather than hiding the assumption.

## Aberdeen style and fit

The team style vector covers possession, directness, pressing, line height,
width, tempo, crossing, build-up and transition. The recruitment target is:

```text
target_style = 0.6 * current_style + 0.4 * config_intent
```

`config_intent` is set by the analyst in `config/clubs/aberdeen.yaml`, not
inferred. Player style similarity is `50 + 50 * cosine(player_z, target_z)`,
damped by the style confidence.

The fit score is a weighted, explainable composite:

```text
0.32 quality + 0.18 style + 0.16 squad need + 0.12 budget
+ 0.10 age + 0.07 reliability + 0.05 availability
- explicit penalties
```

Hard filters (known fee above ceiling, age outside band, work-permit
ineligibility) are separate from the score. Unknowns never hard-exclude; they
lower confidence and are flagged.

## Budget

- `config/clubs/aberdeen.yaml` holds the fee ceiling, wage ceiling and age band.
- Default mode is fee-only; individual Scottish wages are not public.
- Market values are curated and cited in `reference/market_values.yaml`; the app
  publishes value bands and the fit score, not a raw market-value feed.
- Loan/agent fees and sell-ons are flagged unknown.

## Reliability and output

- Headline shortlist: at least 900 effective minutes and fit confidence ≥ 0.5.
- 450–900 minutes: visibly flagged watchlist.
- Below 450: no percentile, only raw stats and "insufficient data".
- Every card shows coverage tier, minutes, league, value band, confidence and a
  component-by-component contribution breakdown.
- The output is never presented as an Aberdeen FC recommendation.

## Rumour signal overlay

The scouting board carries a labelled **advisory overlay** derived from the
curated rumour register (see [rumours.md](rumours.md)). It shows the weighted
position, age, league and value mix of active links, with an explicit sample size
and a low-confidence flag below five rows.

The overlay is not part of the fit score and never re-ranks a player. It answers a
different question: "what profile are the public links pointing at?" The
data-driven fit remains primary, and an opinion card that argues for a different
profile must cite the rumour ids and the measured comparison it relies on.

## What the method does not know

- The club's internal rankings, wage structure and sell-on terms.
- Individual wages and agent fees.
- Event coordinates, xG or tracking unless a licensed event source is added.
- Lower-tier player detail where no licensed source exists.

Those gaps are labelled, not filled.
