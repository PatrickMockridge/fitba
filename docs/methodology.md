# Methodology

**Status:** reference. Last reviewed 2026-10-24.

This page defines how numbers are produced and how uncertainty is shown. It is
the technical companion to the [product strategy](product-strategy.md).

## What we know, what we infer, what we do not know

- **Measured:** a value taken directly from a licensed feed (a result, a minute,
  a goal, a line-up).
- **Inferred:** a model output (a percentile, a league-adjusted score, a fit
  score, an estimated value band).
- **Curated:** a public fact we maintain by hand with a citation (contract dates,
  fee bands, coaching context).
- **Unknown:** a value we do not have. It is shown as unknown, never filled with
  a convenient number.

Every panel should make its category visible.

## Coverage tiers

Each league and player carries a coverage label:

| Tier | Meaning |
|---|---|
| `event` | Event or detailed player data is available. |
| `match` | Results and basic match/player stats are available. |
| `curated` | A human-maintained match log or public record. |
| `value-only` | Only a value/valuation is available, not performance data. |

A `value-only` player is never ranked against `event` players without a warning.
League One/Two player data is the main gap and is labelled accordingly.

## League tables

- Points: **3 for a win, 1 for a draw, 0 for a loss**.
- Tie-breaks: points, goal difference, goals scored, then a head-to-head
  mini-league, then name. The SPFL split and play-offs are handled separately.
- **Points deductions** are stored in `reference/disciplinary.yaml` with a
  source, season, competition and reason. The raw points and the deduction are
  both retained; ranking uses the adjusted points.
- **Split:** the Premiership splits after 33 matches; top six and bottom six
  cannot cross. Play-off matches are excluded from league tables.
- **Curtailed seasons** (2019/20, 2020/21 lower tiers) are validated as partial
  seasons rather than failing the full-match-count check.
- Tables are validated against official final tables each season; arithmetic and
  goal-balance checks run on every build.

## Cup group tables (League Cup)

The licensed source does not provide League Cup standings, so the app computes
them from the group fixtures using the official rules:

- columns: **W, PW, PL, L, GF, GA, GD, Pts**;
- 3 points for a win; 1 point for a draw plus 1 bonus point to the shoot-out
  winner;
- tie-breaks: goal difference, goals scored, away goals, matches won, away
  matches won, head-to-head, drawing of lots;
- the **best three runners-up** are selected using the same comparison;
- the 8 group winners and 3 best runners-up join the 5 European byes in the
  second round.

The computed table is a model of the official rules, not a scraped table. It is
validated against the official results and published with a "computed" label.

## Knockout rounds

- Rounds are stored in config with an explicit order, not inferred from dates.
- A tie stores the 90/120-minute score, an extra-time flag, separate penalty
  scores, status and winner.
- Byes are advancement events, not fake fixtures.
- An unpublished draw is shown as **awaiting draw**, never as an invented tie.
- Scottish Cup ties are single-leg with extra time and penalties; there are no
  replays for drawn matches.

## Player metrics and percentiles

The scouting engine is described in [scouting-method.md](scouting-method.md). In
summary:

- per-90 rates from provider season totals;
- rating percentiles within `(league, season, role family)` at 450+ minutes,
  with a minimum cohort of 15 (8 for goalkeepers);
- role families from starting-XI grids, with a labelled provider-group fallback
  where the feed has no grid;
- an empirical Premiership-equivalent percentile built from the observed
  league/role median and spread, shown beside the raw within-league percentile
  and labelled as a model;
- archetype scores from winsorised robust z-scores, with minutes shrinkage and a
  70% weight-coverage floor;
- a separate scouting priority: U23 (≤23) ×1.30 and European league-phase
  (≥90 minutes in the Champions League, Europa League or Conference League)
  ×0.60, applied to the value index;
- no composite when the applicable weight coverage is below the floor.

The scouting priority is an Aberdeen recruitment preference, not measured
quality. Unknown European status is never discounted. The league-phase flag is
built from the three competitions' league-phase fixtures and the per-fixture
player endpoint; qualifiers and play-offs are excluded.

## Uncertainty

- **Sample size:** effective minutes, starts and a small-sample flag.
- **Coverage:** the tier and source for every player/league.
- **League strength:** measured Elo where available, documented prior otherwise;
  the confidence is shown.
- **Budget:** value bands, confidence and unknown states; no invented wages.
- **Cups:** computed group tables are labelled; an unpublished draw is a state.
- **fxG:** a team-match expected-goals estimate from open-play shot zones,
  shots on target, blocked shots and penalties, with an 80% model range and a
  separate 80% goals range. Provider-xG calibration, a transfer check and a
  published gate are visible. See [xg.md](xg.md).

## Transfers and loans

The transfer register uses API-Football as a candidate feed; official AFC
announcements and Wikipedia season records are the cross-checks. Only
confirmed/curated completed business is published; feed-only, reported and
rejected rows are excluded. Fees are curated only: undisclosed is never zero;
permanent moves carry an inferred range, and loan fees are excluded from the
net. Loan end/recall/obligation terms are unknown unless confirmed. See
[transfers.md](transfers.md).

Completeness is judged by seniority: an established senior move should be in
the register; a youth/development gap is recorded and tolerated. A person may
read a third-party page as a finding aid, but it is never scraped, cited or
published; the move is added only when AFC, API-Football or Wikipedia
independently confirms it. `fitba transfers --audit` produces a report-only
review queue and `reference/transfer_gaps.yaml` records accepted gaps. No gap
blocks a publish.

The register counts **moves, not players**: a loan out and a return are two
rows. The payload derives the period, distinct-player, season and window counts
from the rows, and the guard checks that those aggregates, the per-window
arrival/departure totals and the audited window counts all agree. The
membership cards read those values from the payload rather than a hard-coded
season label.

## Historical record

- **League tables:** a completed 12-team Premiership season is ranked inside its
  post-split top-six and bottom-six groups, using each team's first 33 matches to
  decide membership. A bottom-six team cannot be placed above a top-six team on
  total points. This is why the 2021-22 and 2023-24 final positions differ from a
  naive all-38-match sort.
- **Manager records:** league-only. Matches are assigned by the curated stint
  dates; a match in a gap is unattributed, and a boundary day is assigned once.
  Month/year precision is preserved and marked boundary-ambiguous.
- **Style:** opponent-unadjusted team proxies from football-data.co.uk — shots,
  shots on target, accuracy, corners, fouls and cards. Not xG and not a tactical
  model. Possession is shown only from the provider team-statistics backfill.
- **Selection:** formation mix, players used, average starter age, U21 minutes
  and debutants from the historical lineup backfill. Missing lineups or ages are
  partial/unavailable; they are never inferred. Debutants mean first appearance
  in the covered record, not career debut.
- **Recruitment:** counts, disclosed fees, source-market mix and age at arrival.
  Undisclosed is never zero. Pre-2024-25 windows are curated partial.
- **"The read":** a labelled editorial assessment, separate from the measured and
  curated panels. It is not the club's internal view.

See [history.md](history.md).

## Matchday projections

The matchday dashboard is described in [matchday.md](matchday.md). In summary:

- **Form** is league-only: the last five results for the strip, every league
  match for home/away splits. Cup and league form are never merged silently.
- **Style** uses measured shot volume, shot share, shots on target, goals,
  conversion and corners. Possession is unknown and is not an input.
- **The three-way lean** is a weighted percentile index with venue adjustment
  when the fixture-venue sample has at least three matches. `attack`,
  `balanced` and `sit_deep_counter` are inference labels, not a tactical model.
- **Relative strength** percentiles are within the same league. A cross-tier cup
  opponent is labelled and compared on raw values only.
- **Predicted XIs** are a deterministic projection from observed formations,
  starts, minutes, role adjacency, player form and recent provider ratings.
  Form and recent rating carry 35% of the selection score; team form is context,
  not a selection input. A missing formation or a sample below three matches is
  `unavailable`; it is never guessed. Missing ratings are renormalised and the
  rating coverage is shown, not zero-filled.
- **Availability** comes from a curated official AFC team-news ledger; the
  provider `/injuries` snapshot is optional and currently not populated for
  Scottish 2026. Unknown stays unknown. The opponent has no availability feed
  unless a curated record exists. The page says "predicted, not team news" and
  never claims a confirmed XI.
- **Refresh** is daily, bounded to the next opponent and cache-first. A failed
  refresh carries the previous snapshot as stale, or degrades to league-only
  context with the opponent XI unavailable.

## Season overview

`/analysis/` is described in [analysis.md](analysis.md) and the review record in
[analysis-review.md](analysis-review.md). It projects the current table row,
the next three fixtures, official AFC team news, derived selection signals,
measured season aims and factual squad-decision lenses. The active availability
universe is the current squad plus ledger-only players; loan-outs are separate.
Derived absence is not a medical diagnosis, and suspension rules are
watch/review-only until a current sourced protocol is verified. Squad decisions
use age, minutes, role and cohort percentile; no value, fee, wage or contract
expiry is inferred. The old thematic case analytics remain in the warehouse for
the matchday strip and needs model, but are not rendered on `/analysis/`.

## fxG

fxG is a **team-match expected-goals estimate**, not a shot-level model and not
provider xG. The record has team counts and events, but no shot coordinates,
distance, angle, body part, pressure, goalkeeper position or goalmouth
trajectory.

The selected model uses open-play inside-box shots, outside-box shots and shots
on target, plus a fixed 0.76 xG for every non-shootout penalty attempt.
Penalties are removed from the open-play counts before the fit and added back
after it. If zones are missing, the model falls back to open-play volume; if
shots on target are missing, it falls back to the competition-season conversion
rate and labels the basis. The coefficients are fitted by OLS to the 2026-27
Premiership team rows where football-data provider xG exists. Leave-one-match-out
validation leaves out both team rows of a match.

Two ranges are published:

- The **80% model range** is the uncertainty in the fxG estimate: a
  match-clustered bootstrap plus the leave-one-match-out residual pool.
  Aggregates sum per-draw predictions and residuals; per-match intervals are
  never added together.
- The **80% goals range** is the spread of goals from the same chances: a
  beta-binomial open-play distribution convolved with a binomial penalty
  distribution. Aggregate distributions are convolved, so variance sums and
  width grows roughly with the square root of matches.

`Goals − fxG` is descriptive and is not a verdict on finishing. One match or one
season is noisy; style, shot selection, game state, own goals, deflections and
provider differences can move the difference. Provider xG is carried separately
where available and is never blended into fxG. There is no xGOT, player xG or
shot-level location model in this record. The model card, calibration gate,
transfer check and limitations are in [xg.md](xg.md).


## Provenance and squad needs

- **Provenance** is a layer truth table: [provenance.md](provenance.md). A source
  is primary only for the layer it supplies; API-Football is primary for cups,
  lineups, player stats and the squad, while Football-Data remains primary for
  league results and team stats until the strict migration gate passes.
- **Availability** is a curated special case of team news:
  [availability.md](availability.md). Out/suspended players are excluded from the
  predicted XI; doubtful players are selectable with a confidence downgrade;
  unknown stays unknown.
- **Squad needs** turn analyses, availability and depth into role profiles:
  [needs.md](needs.md). Cover (loan/free), replace (active outgoing evidence
  only) and strengthen (measured weakness) are role classifications, not named
  targets.

## Inferred fees, sell-ons and plausibility

- **Fee basis:** disclosed and reported fees are anchors with a public source;
  free transfers have a zero fee; loan fees are unknown and excluded from the
  net; undisclosed permanent moves get a modelled range.
- **Model:** market/position base × age curve, calibrated to the
  reported/disclosed anchors. Each row shows a low–high range, a confidence
  label and the method. The aggregate uses modelled midpoints with a 20%
  portfolio band on modelled gross flows. It is never presented as an audited
  balance.
- **Sell-ons:** a clause is `confirmed` only with an allowed public URL, or
  `reported` with a finding-aid label and no restricted URL. A missing
  percentage is never inferred.
- **Plausibility:** a curated row with three or more high-confidence flags
  (unknown club, no profile, no position, Wikipedia-only, merged name) is
  withheld until accepted in `reference/transfer_plausibility.yaml`.
- **Manual calibration:** a restricted page may be read privately as a sanity
  check, but no restricted value, URL or table is published.

See [transfers.md](transfers.md).

## Squad and player statistics

- The squad is the current licensed squad plus current-season loanees out from
  the confirmed register.
- Stats are current-season, per competition. A provider row with 0 appearances
  is a measured zero; a missing row is `unavailable`; a row missing a key field
  is `partial`. Missing values are never filled with zero.
- Stats are scoped `club` (Aberdeen), `loan` (the registered loan club) or
  `other` (national team, previous club, stale parent-club row). Parent-club rows
  are never presented as loan-club output.
- The provider rating is labelled as such and aggregated by appearances. It is
  not a fitba rating and is not used to rank players.
- Starts, substitute appearances and on-pitch minutes are reconstructed from
  fixture lineups and substitution events, so a start and a substitute
  appearance are separate numbers rather than one “apps” total.
- Goals conceded while on the pitch, clean sheets (60+ minutes, zero conceded
  while on the pitch) and own goals are reconstructed from fixture lineups and
  events. A fixture missing either is excluded and the coverage is labelled.
- Provider player stats and event-reconstructed position stats can cover
  different competitions; they are shown separately and not merged.
- Player pages are current-season only and publish no photographs. The shared
  player-profile standard adds two Nightingale rose figures, league-only role
  percentiles, and an explicit unavailable state; see
  `docs/player-profile-standard.md`.

See [squad.md](squad.md) and [roles.md](roles.md).

## Roles and shape

Role is derived from the starting-XI formation grid, not from a generic position
label. The formation gives the row lengths; the grid slot gives the row and
column; `config/roles.yaml` maps that slot to a role code. A starter without a
grid, an unmapped formation or an invalid slot is unknown. A substitute has no
grid slot and therefore no role. The primary role is chosen by family starts,
then family minutes, then role starts/minutes and config order; the full role
history is published. Kick-off shape, centre-back count and holding-midfielder
count are recorded for the shape/balance view. Mid-game formation changes are
not in the feed and are never inferred from substitutions; sourced switches are
kept in `reference/shape_notes.yaml`. See [roles.md](roles.md). The 2026-27
rebuild and shape-instability context is in
[the context diary](context/aberdeen-2026-27.md).

The career layer treats a player as a set of positions, not one label. Starting
appearances across the last three seasons are aggregated into FM-style slots
(`D/WB L`, `DM/M C`, `AM R`, ...). A slot is primary, secondary or stretch based
on starts and share; a full-back/wing-back counts as both a defender and a
midfielder for the broad filter, a DM is a midfielder, and a winger is an
attacker. Starts are equal-weighted; the current Aberdeen role only overrides
the display label when it is clearly different, and the current role is itself
a multi-slot summary. This is a general football model for fluid formations and
utility/inverted roles; curated `reference/role_notes.yaml` context covers
interpretations the kick-off grid cannot see. See
[career-roles.md](career-roles.md).

## Scouting

The scouting universe is `config/scouting/leagues.yaml`. Player season
statistics and starting-XI lineups come from API-Football. At the 2026-10-23
sync, 25 of 33 enabled leagues returned searchable player statistics; seven are
labelled as having none and one is partial. Role families come from the same starting-XI
grid as the Aberdeen roles; a league without a grid uses the provider position
group and says so.

Raw ratings and profile scores are compared only within a league and role
family. A separate empirical alignment maps a player's within-league percentile
into the actual Premiership cohort distribution; it is a model built from the
observed league and role spread, not a measured equivalence, and the raw and
adjusted values are shown side by side. Per-90 values use the provider season
totals; completed passes are `passes.total × accuracy / 100`. Forward and
progressive passes, carries, pressures, aerial wins and crosses are not in the
feed. Contracts, wages, fees and release clauses are not claimed. The
availability layer uses only verified official AFC team news.

`/scouting/search/` searches every ranked player across the pool and shows the
league beside every row. The adjusted percentile is the empirical
Premiership-equivalent alignment, not a measured equivalence. The value index
is a scouting ordering, not a transfer value; it combines the adjusted
percentile, the age curve, minutes reliability and profile fit. Aberdeen's U23
and European shop-window preferences are applied after the index as a separate
priority, and the team-context lens compares the player's role-adjusted
percentile with the team's points-per-game percentile. The hub exposes simple
reader lenses; the full search adds reader weights, thresholds and eligibility
filters as labelled scenarios. A GBP band is published only after the
public-source anchor register passes its gate.

See [scouting-method.md](scouting-method.md).

## Preferred foot

Preferred foot is resolved through a source hierarchy: verified override,
Sportmonks (preferred licensed source), official pages, Wikipedia (last resort),
then unknown. A value is accepted only from an explicit foot statement.
Same-tier disagreement is a conflict with no published value. Every value
carries its source, URL, revision where applicable, verification date and
derivation. Side is not resolved here; it is derived from the role. The front
end never infers. See [player-data.md](player-data.md).

## Rumours, fan signal and sentiment

- A rumour is an unconfirmed link with public sources, a lifecycle status and an
  editorial confidence. It is separate from confirmed business; a confirmed
  rumour links to a transfer row and never becomes a second source of truth.
- Fan signal is a sample: the first page of recent AFC Chat Rumour Mill topics,
  not the whole forum. Name mentions use a rule-based gazetteer; ambiguous
  surnames are rejected rather than guessed.
- Cross-reference labels record where else a name appears (press rumour, club
  output, recent confirmed transfer, current squad). They are coverage labels,
  not probabilities.
- Sentiment is rule-based VADER on sampled posts, press claims and club titles.
  It is descriptive and noisy, and it is never presented as a poll or a measure
  of credibility.
- The recruitment profile is advisory: confidence- and recency-weighted active
  links, with a low-confidence flag below five rows. It never overrides the
  scouting fit.

See [rumours.md](rumours.md) for the full method.

## Event-reconstructed visuals vs tracking

The 2D viewer planned for later is **event-reconstructed**, not tracking:

- only the ball and the players involved in an event are placed from source
  coordinates;
- other players are inferred from formation and average position;
- every sequence carries an "event-reconstructed — not tracking data" badge;
- no offside lines, pressing traps or player-speed claims.

Full tracking is an enterprise data product and is not part of the public
pipeline in this phase.

## Publication and provenance

- Raw payloads stay in gitignored caches; only derived tables, aggregates and
  short excerpts are committed.
- Every published file has a manifest entry with a checksum.
- Publishing is atomic: temp directory, validation, rename, manifest last.
- The manifest records source, coverage, last success and freshness.
- A failed source keeps its last-good data and is marked stale.

## Cross-surface consistency

Every shared fact has one production derivation. The squad, player, scouting,
analysis, matchday, fixture and transfer publishers call the shared analytics
helpers rather than re-filtering the same input. A page may show a different
scope (league vs all competitions, official list vs register, current vs
all-time), but it must name that scope beside the number.

`scripts/check_consistency.py` reconciles the published payloads: squad counts,
loan scopes, player totals and playing time, xG aggregates and fixture rows,
shootout labels, scheduled counts, availability universes and coverage counts.
The same checks run inside `fitba publish` and block the atomic swap on a
failure. See [data-consistency.md](data-consistency.md) for the scope
vocabulary and the full check list.

## Corrections

If a source, format or calculation changes, update the config, this document and
the in-app page in the same change. The last-reviewed date and sources are part
of the page. Do not leave a stale claim in one place and fix it in another.
