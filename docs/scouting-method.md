# Scouting method

**Status:** live. Last reviewed 2026-10-24.

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
3. **Layer 2 — profiles.** Seven archetypes show the types of player that add
   options. The attacker section splits assist-biased contribution from
   goal-scoring contribution; a separate goal-scoring lens orders forwards by
   goals per 90. The team-context lens compares the player's role-adjusted
   percentile with the team's points-per-game percentile. These are profiles,
   not recommendations.

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

`config/scouting/archetypes.yaml` defines seven profiles:

| Profile | Families | Inputs |
|---|---|---|
| Ball-winning pivot | DM, CM | tackles/90, interceptions/90, duels won %, pass completion |
| Deep-lying playmaker | DM, CM | completed passes/90, pass completion, key passes/90, assists/90 |
| Build-up defender | CB, FB, WB | completed passes/90, pass completion, key passes/90, successful dribbles/90 |
| Wide dribbler | WM, WF, AM | successful dribbles/90, dribble success %, key passes/90, G+A/90 |
| Assist-biased contributor | ST, WF, AM, WM | completed passes/90 (0.25), key passes/90 (0.30), pass completion (0.05), assists/90 (0.25), successful dribbles/90 (0.15) |
| Goal-scoring forward | ST, WF, AM | goals/90 (0.50), shots/90 (0.20), conversion (0.20), G+A/90 (0.10); pass and dribble volume excluded |
| Goalkeeper shot-stopper | GK | save %, goals conceded/90 |

Each score is a weighted composite of winsorised robust z-scores within the
league and role cohort, shrunk by `minutes / (minutes + 450)` and mapped to
0–100 with the normal CDF. Missing features are dropped and the remaining
absolute weights renormalised. If less than 70% of the absolute weight is
present, the score is null, not zero.

Layer 2 uses the top league-adjusted profiles across every league, not the
Premiership only. Each leader shows the league and club, the raw score and the
adjusted score. Leaders are ordered by `adjusted profile score × U23 multiplier
× European league-phase multiplier`; the U23 and shop-window preferences still
apply, but the profile itself sets the order. Ordering by the value-index
priority alone reproduced the same names in every attacking profile. The
attacker card splits assist bias from goal bias, and the goal-scoring table
orders forwards and attacking midfielders by goals per 90. The feed carries no
crosses, so key passes are the closest available creation signal. These answer
"what profile is missing?", not "would this signing reduce goals?".

## Published default lists

The published hub lists are capped at:

- five leaders for each of the seven archetype profiles;
- eight leaders for each of the assist-bias and goal-bias attacker lists;
- twelve rows in the goal-scoring table;
- twelve leaders in the team-context lens.

The caps are part of the published shape, not a display accident. The reader
scenario uses the same limits: a lens or a reader weight can change which
players qualify and their order, but it cannot widen a list beyond the published
length. The defaults are the audited publisher output.

## Full pool payload

`/scouting/pool.json` is a static route that publishes the full ranked pool
(the same data as the search index) for the reader scenarios. The hub does not
embed that payload in the initial page. It is fetched only when a lens becomes
active, with a loading state, an explicit error state and a retry. If the fetch
fails, the published lists remain visible and unchanged; the page does not
pretend the lens was applied.

The reader scenario is computed in the browser from this published payload. It
does not write to the payload, the registry or the audit.

## Player roses

Every dedicated player profile carries two Nightingale rose figures:

- **Overall profile** — the shared all-round outfield set (or the goalkeeper
  set): goals, assists, shots, key passes, successful dribbles, completed
  passes, pass completion, tackles, interceptions and duels won.
- **Position profile** — the role-specific set from
  `config/player-rose.yaml`: for example scoring and creation for a centre
  forward, passing and retention for a centre back, shot-stopping and
  distribution for a goalkeeper.

Both figures use the same cohort: the player's league and role family at the
450-minute pool threshold, falling back to the provider position group when the
role cohort is below its minimum (15; 8 for goalkeepers). Aberdeen uses
Premiership-only statistics so the comparison is like-for-like; the scouting
pool uses the row's league statistics. There is no cross-league percentile.

Each axis is a midrank percentile from 0 to 100. Higher is better:
`conceded_p90` is ranked on negated values. Sector radius is
`sqrt(percentile / 100)`, so sector area is proportional to the percentile.
A missing value or an insufficient cohort is null and appears as a dash in the
companion table; it is never zero. The companion table carries the raw value,
percentile and per-axis cohort n, and is the accessible alternative to the
chart.

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

## Prior-season rose cohorts

`data/normalized/scouting/rose_history.parquet` holds full-season Premiership
pools for 2024-25 and 2025-26, used only by the player-page rose fallback. It is
a separate file and never replaces the current-season pool. The cohort builder
excludes Aberdeen from the comparison values but keeps the Aberdeen row so a
player's own season totals are available. A season the provider does not return
is omitted and reported; the fallback never uses the current-season cohort for
a prior-season rate.

## Commands

```bash
uv run fitba scouting pool  --season current
uv run fitba scouting roles --season current --budget 6500
uv run fitba scouting rose-history --seasons 2024,2025
uv run fitba scouting standings --season current
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
- Whether the U23 or European shop-window preference is correct for Aberdeen;
  they are published as preferences, not as measured effects.
- A calibrated transfer value. The public-source anchor register is the missing
  input; until it passes the gate, only the value index is published.

## Team context: outperforming struggling teams

The team-context lens uses the licensed league tables. One current table is
fetched per enabled league; the group with the most played rounds is used. A
team's points-per-game percentile is its rank among the teams in that table.

```text
team_lift = player role-adjusted percentile − team points-per-game percentile
```

A team is treated as underperforming at or below the configured percentile
(default 40), with a minimum lift of 0 and a lens limit of 12 rows; the
parameters live in `config/scouting/team-context.yaml`. The lens keeps players
with a positive lift at those teams, ordered by lift and then scouting priority.
The contrast is descriptive, not a valuation, prediction or recommendation. A
league or team without a current table is `unknown`, never zero-strength;
coverage is published in the hub and the player profile.

The recent Aberdeen examples fit the team side of the lens: Kilmarnock finished
11th of 12 in the 2025-26 Premiership, and Northampton finished 24th of 24 in
2025-26 League One. The lens is not a claim that either player was signed for
that reason.

## Simple lenses on the hub

The `/scouting/` hub, the global search and the per-league searches share one
lens selector. Each selected lens is visible as an active layer:

- **Priority rank** — rank by the value-index priority.
- **U23** — apply the ×1.30 preference, optionally restrict to U23 only.
- **Europe shop window** — apply the ×0.60 preference, optionally exclude
  players with 90+ league-phase minutes.
- **Struggling team** — restrict to teams at or below the team PPG percentile.
- **Profile** — restrict to an archetype and its coverage floor.
- **Role** — restrict to a role family.
- **League** — restrict to one league.

Eligibility lenses intersect; preference lenses multiply the priority score.
The selector states whether one lens or a layered set is active.

On the hub, no active lens renders the published default lists exactly. Any
active lens recomputes the seven profile lists, the assist/goal lists, the
goal-scoring table and the team-context lens from the published full-pool
payload at `/scouting/pool.json`. The result is labelled **Reader scenario** and
is reset to the published defaults with one control. The hub exposes no numeric
weights and no separate player table; the full table stays on
`/scouting/search/`.

## Advanced filters on the full search

`/scouting/search/` keeps the simple lens bar and adds an always-visible
**Advanced filters** panel. The reader can set:

- the U23 cutoff and multiplier and the European league-phase minutes threshold
  and multiplier;
- the four value-index weights (performance, age, minutes, profile fit), with
  the normalised share shown;
- the underperforming PPG percentile and the minimum team lift;
- eligibility filters: text, nationality, minimum minutes, maximum age,
  European status, role-known only and minimum value-index coverage.

The reader U23 cutoff and European minutes threshold are applied to the
player's age and league-phase minutes, so lowering the European threshold can
treat a below-threshold player as qualified and raising it can remove the
discount from a qualified player. The published status remains visible in the
Europe column; the reader discount and the shop-window badge use the active
threshold.

The reader value index uses the registered formula with the reader weights:

```text
performance = adjusted percentile / 100
age         = the published age-curve band factor for the player's age
minutes     = min(1, minutes / 1800)
profile     = best adjusted profile score / 100
coverage    = sum(weights of present components) / sum(all weights)
if coverage < 0.70: null
reader_value_index = 100 × Σ(weight × component) / Σ(weights of present)
reader_priority    = reader value index × U23 factor × Europe factor
```

The default weights reproduce the published value index and priority. Any
change is labelled **Reader scenario** and a single reset restores the published
defaults. Reader scenarios are computed in the browser from the published
search index; they never change a published value, the registry or the audit.
The published value index, priority and audit remain the source of truth.
