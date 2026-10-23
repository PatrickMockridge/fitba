# Scouting method

**Status:** live. Last reviewed 2026-10-23.

The scouting section is deliberately explainable. It does not produce a single
"good player" verdict or a target list. It shows the components, the cohort, the
coverage and the uncertainty. Every number is registered in
`config/metrics.yaml` and checked by `scripts/check_scouting.py`.

## Layer model

1. **Layer 0 — internal first.** The verified availability ledger is read before
   the market. A player with first-choice evidence in the most recent season
   with at least 450 minutes (10 starts or 900 minutes) is an internal future
   option. One verified first-choice absentee in a below-cohort family is read as
   **cover**; two or more is **hold**. A player absent from the provider squad
   snapshot but present in the official ledger keeps a role only from prior
   starting-XI evidence, never from a generic position.
2. **Layer 1 — measured gaps.** Aberdeen's competitive provider rating by role
   family is compared with the other Scottish Premiership players in the same
   role family. Aberdeen are excluded from their own cohort.
3. **Layer 2 — profiles.** Six archetypes show the types of player that add
   options. The double-pivot card is a labelled hypothesis, not a causal claim.

## Universe

`config/scouting/leagues.yaml` is the universe. It includes the Scottish
pyramid, England's Championship, League One and the explicitly added **League
Two**, and the configured European markets. Provider ids and coverage flags are
recorded per league.

At the 2026-10-23 sync, 33 leagues are enabled. Twenty-five return searchable
player statistics; seven return none and are shown as honest empty pages; one
(Albania) returns a single unrated row and is labelled partial:

- Scottish Championship, League One and League Two;
- Bulgarian First Professional League, Icelandic Besta deild, Slovenian
  PrvaLiga and NIFL Premiership.

That is a provider fact, not a zero. The coverage table on `/scouting/` reports
it league by league.

## Roles and cohorts

A player's role family comes from the starting-XI grid in `/fixtures/lineups`:
the shape is derived from the grid with `shape_from_grid()`, then the slot maps
through `config/roles.yaml`. A formation string is a fallback when the grid is
incomplete. A team sheet with neither a formation nor a grid is marked
`role_unavailable` and falls back to the provider position group (GK/DEF/MID/
FWD); the page says so. Nothing is inferred from a generic position, a shirt
number or the bench. The goalkeeper `pos=G` fallback is the only exception.

A player's primary family is the family with the most starts, then minutes, then
config order. `role_family_share` is the share of role starts in that family; a
share below 0.6 is labelled `mixed`.

Percentiles are within `(league, season, role family)`, at 450+ minutes, with a
minimum cohort of 15 (8 for goalkeepers). When the role cohort is too small, the
page may use the provider position group and labels `cohort_basis:
provider_group`. It never pools cohorts across leagues.

Provider ratings are opaque and league-relative, so the page also publishes an
**empirical Premiership-equivalent percentile**. It maps a player's rating into
the actual Premiership cohort distribution using the observed league/role
spread; the raw rating's level carries the league's level, and the Premiership
is the identity. A profile score is a within-league percentile, so the profile
alignment also adds the observed league/role location. This is a model, not a
measured equivalence; the raw and adjusted values are shown side by side and the
per-league median, scale, offset, cohort size and basis are published in the
coverage document.

`/scouting/search/` is the full search across every league in the pool. It
shows the league, club and nationality beside every row and filters by league,
so the comparison boundary is explicit. The default sort is a league mix, not a
cross-league quality rank; the adjusted percentile is available as a sort and
is labelled as a model.

## Per-90 and position-specific output

- per-90: `stat × 90 / minutes`;
- completed passes: `passes.total × passes.accuracy / 100`;
- duel and dribble percentages divide by the provider attempts;
- conversion: `goals / shots.total`;
- save percentage: `saves / (saves + conceded)`.

The feed does **not** carry forward or progressive passes, carries, pressures,
aerial wins, crosses, xG or xA. Those are shown as unavailable, not inferred.
For defenders, the passing and retention measures are the available proxy for
build-up and press resistance; they are not a complete answer.

## Archetypes

`config/scouting/archetypes.yaml` defines six profiles:

| Profile | Families | Inputs |
|---|---|---|
| Ball-winning pivot | DM, CM | tackles/90, interceptions/90, duels won %, pass completion |
| Deep-lying playmaker | DM, CM | completed passes/90, pass completion, key passes/90, assists/90 |
| Build-up defender | CB, FB, WB | completed passes/90, pass completion, key passes/90, successful dribbles/90 |
| Wide dribbler | WM, WF, AM | successful dribbles/90, dribble success %, key passes/90, G+A/90 |
| Goal contributor | ST, WF, AM | G+A/90, shots/90, conversion % |
| Goalkeeper shot-stopper | GK | save %, goals conceded/90 |

Each score is a weighted composite of winsorised robust z-scores within the
league and role cohort, shrunk by `minutes / (minutes + 450)` and mapped to
0–100 with the normal CDF. Missing features are dropped and the remaining
absolute weights renormalised. If less than 70% of the absolute weight is
present, the score is null, not zero.

Layer 2 and the pivot card use the top league-adjusted profiles across every
league, not the Premiership only. Each leader shows the league and club, the raw
score and the adjusted score. The pivot card shows the current squad's best
ball-winner and deep playmaker and the all-league profiles. It answers "what
profile is missing?", not "would this signing reduce goals?".

## Value

The **value index** is a 0–100 scouting ordering, not a transfer value:

```text
value_index = 100 × (
  0.55 × adjusted_percentile/100
+ 0.15 × age_curve
+ 0.15 × minutes_reliability
+ 0.15 × profile_fit
)
```

The weights are renormalised over available components; below 70% coverage the
index is null. The age curve peaks at 24–27; minutes reliability is
`min(1, minutes / 1800)`; profile fit is the best adjusted profile / 100. It is
labelled **"Scouting value index — not a transfer value"** everywhere and never
uses a currency symbol.

A GBP band is fitted only from the public-source anchor register in
`reference/scouting_values.yaml`:

```text
log(value_gbp) = b0 + b1×adjusted_percentile/100 + b2×age + b3×age²
               + b4×log(minutes) + role-group dummies
```

Each anchor needs a contemporaneous performance snapshot, an allowed source URL
and a verified date. The gate requires 60 usable anchors, at least 5 per broad
role group, at least 3 league tiers, at least 3 age bands and at least 20% in
the top two tiers. If the gate is not met, the state is `awaiting_anchors`, the
GBP band is null and no currency value is published.

The GBP band is deferred for now. The value index is live; the anchor register
and fit gate are scaffolded (four diagnostic Aberdeen-market anchors) and will be
revisited with a proper public-source curation pass. No GBP value is published
until then.

## Availability

The curated ledger in `reference/availability.yaml` is primary. An entry needs
an official AFC source URL and a `verified_at` date; stale entries become
unknown for selection but keep their ledger status visible. The provider injury
boolean is not team news, and minutes are never fitness evidence.

At this review, two entries are verified: Kristers Tobers (out, official club
press conference 2026-10-08) and Mats Knoester (available, official club
interview 2026-10-16, confidence `reported`). Every other player is unknown.

## Contracts

The licensed feed has no contract expiry field. The curated
`reference/contracts.yaml` is empty and every entry would need a public source.
No contract column, filter or ranking input is published. Wages, fees, sell-on
terms and release clauses are not claimed.

## Commands

```bash
uv run fitba scouting pool  --season current
uv run fitba scouting roles --season current --budget 6500
uv run fitba scouting status
uv run fitba scouting values --status
uv run fitba scouting values --validate
uv run fitba scouting values --fit
uv run fitba publish --season current --profile public --require-validation
uv run python scripts/check_scouting.py
```

The pool sync caches every provider response. The role backfill is resumable and
stops cleanly at the request budget; a full run is about 2,750 played fixtures
and fits inside the Pro daily allowance. Raw responses stay in `.cache` and are
never published.

## What the method does not know

- The club's internal rankings, wage structure, sell-on terms or contract
  details.
- Individual wages, agent fees or release clauses.
- Event coordinates, xG/xA, progressive passes, carries, pressures or aerial
  data.
- Lower-tier player detail where the provider returns no statistics.
- Whether a profile would change results. The data can show a gap, not a cause.
- A calibrated transfer value. The public-source anchor register is the missing
  input; until it passes the gate, only the value index is published.
