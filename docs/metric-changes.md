# Metric change log

**Status:** append-only record of metric-definition and parameter changes.
**Owner:** patrickmockridge. **Last reviewed:** 2026-10-22.

A semantic metric change is any change to an id, formula, input, denominator,
aggregation, rounding, basis, source layer, coverage tier, confidence rule,
parameter value or verification mode. Each change records owner approval, the
affected surfaces, the expected value impact and the audit impact.

## 1.0.0 — 2026-10-22

- Established the canonical registry in `config/metrics.yaml`.
- Registered the current published metric families and parameters.
- Established the generated audit, `/metrics/`, `/status/` summary and hard CI.
- This entry records the baseline. No published value was intentionally changed
  by the initial registry work; any change found during reconciliation is listed
  below when it lands.

### Value changes

None at baseline.

## 1.1.0 — 2026-10-22

Pipeline reconciliation of provenance source rows. No metric formula,
denominator, rounding mode or parameter value changed; the published payload
values that changed are the provenance source-row counts and the manifest
source summaries.

| Field | Before | After | Reason |
|---|---:|---:|---|
| `league_team_stats.football_data_uk.rows` | 0 | current-season matches with team stats | Placeholder replaced with the real row count. |
| `event_layer.api_football.rows` | 0 | appearance rows | Placeholder replaced with the reconstructed-event input count. |
| `transfers_candidate.api_football.rows` | 0 | candidate-feed rows | Placeholder replaced with the local candidate count; zero when the gitignored candidate file is absent. |
| `transfer_register.wikipedia.rows` | 0 | register rows with a Wikipedia source URL | Placeholder replaced with real corroboration rows. |
| `transfer_register.afc_news.rows` | 0 | register rows with an AFC source URL | Placeholder replaced with real corroboration rows. |
| `availability.afc_news.rows` | 0 | entries with an official AFC source | Computed; currently zero because every entry is `unknown`. |
| `rumours.afc_news.rows` | 0 | rumour rows with an AFC source | Computed; currently zero because the register is empty. |
| `history.wikipedia.rows` | 0 | history source references | Placeholder replaced with real source references. |
| `history.afc_news.rows` | — | history source references | AFC corroboration now counted. |
| `valuation.football_data_uk.rows` | 0 | — | Football-Data does not supply valuation anchors; the attribution was wrong. |
| `valuation.wikipedia.rows` | — | published anchor count | Public valuation anchors are AFC/Wikipedia only. |

Also in 1.1.0:

- Win/draw/loss, goals and points arithmetic moved to
  `fitba.analytics.records.record_totals`; matchday and history consume the same
  function.
- Valuation calibration and row estimates moved to a single
  `fitba.analytics.valuation.value_transfers` run. Transfers and history consume
  the same estimated rows and summary instead of recalculating.

`diff_published.py` reported zero changed numeric leaves for the consolidation
step. Affected surfaces: `/sources/`, `/methodology/`, `/status/`, `/metrics/`.
Audit impact: `provenance.layers` remains `provenance_only` and passes; the
audit is regenerated with the new dataset version. Owner approval: baseline
reconciliation approved with the metric-governance scope on 2026-10-22.

## 1.2.0 — 2026-10-22

Definition completeness for the `recompute` families. The registry now states
the arithmetic that the verification functions already implement for matchday
form, needs summary, transfer summary and windows, history baseline, squad
summary and rumours summary, and declares integer versus rate rounding. No
published value or calculation changed; `diff_published.py` is expected to
report zero changed numeric leaves after republishing.

## 2.0.0 — 2026-10-22

The themes section was rebuilt as **Data analysis**. The storage path stays
`themes/aberdeen.json` for pipeline stability; the reader-facing page is
`/analysis/`, with `/themes/` redirecting.

- The payload changed from five theme blocks to six claims with `claim`, `count`,
  `status`, `status_reason`, `evidence`, `better_data` and `change_mind`.
- The owner's view and the chairman's frame are published as attributed blocks.
- Added a peer benchmark: league performance of the other SPFL clubs, with the
  missing transfer/wage comparison labelled.
- Metric ids `themes.*` were replaced by `case.*`; the paths point to the same
  payload. The registry version is `2.0.0`.
- Added `param.case.thresholds` and `param.case.scope`.
- The 80/20 split, the fixed five-card count and the per-theme metric panels were
  retired.
- Data corrections: the centre-back "thin" headline, the young-minutes wording,
  the CB 5-vs-4, fixture 15-vs-20, shape 2-vs-5 and AM/WM 8-vs-7 counts, the
  "record" run wording and the 0.05 rating-gap claim.
- Overlapping measured values (league record, shape split, goals, recruitment
  counts) are unchanged by design.
- Affected surfaces: `/analysis/`, `/matchday/`, `/recruitment/`, `/status/`,
  `/sources/` and `/metrics/`.
- Audit impact: `case.*` families are `provenance_only` in this version with
  explicit limitations; the guard checks claim counts, statuses, evidence,
  benchmark and headline/table agreement.

## 2.1.0 — 2026-10-22

The API-Football match record, fxG and the confidence ledger.

- Added `matches.document`, `fixtures.index`, `xg.document` and
  `confidence.document` metric families. Each covers a published document family
  with wildcard payload paths; all are `provenance_only` with explicit
  limitations in this version. No existing metric or published value was
  changed.
- Added `param.xg`, `param.confidence` and `param.fixtures`. The values are the
  live `config/xg.yaml`, `config/confidence.yaml` and `config/fixtures.yaml`
  nodes.
- The registry version moves to `2.1.0`. The audit grows from 53 to 57 metrics
  and from 14 to 17 parameters. Numeric coverage now includes 370 fixture
  documents plus the fixture index, xG and confidence payloads.
- New surfaces: `/matches/` and `/analysis/xg/`; new markers on `/analysis/` and
  `/matchday/`. Existing surfaces and contracts are unchanged.
- fxG gate: fit before 2026-27, validate on 2026-27 provider xG. At this publish
  the gate fails, so fxG is descriptive and is not used in a confidence verdict.
- Confidence ledger: team form and up to 12 current-squad players, with 80%
  intervals and mechanical verdicts. 2019-20 has no historical provider player
  stats; later seasons are partial.
- Affected surfaces: `/matches/`, `/analysis/`, `/analysis/xg/`, `/matchday/`,
  `/methodology/`, `/metrics/`, `/status/`.
- Audit impact: the four new families are present and sourced; they do not add
  an independent recomputation of the fxG model or the confidence intervals in
  this version.
- Change-control comparison now normalises the previous registry through the
  same metric/parameter models, so default-valued fields are not reported as
  semantic changes. A real formula, parameter or path change still fails.

### Value changes in 2.1.0

The current-season football-data.co.uk re-ingest added one Championship result
before the 2026-10-22 18:17 publish. The table formula did not change.

| Field | Before | After | Reason |
|---|---:|---:|---|
| Dunfermline Athletic played / points / position | 9 / 14 / 6 | 10 / 15 / 5 | New 2026-27 Championship result in the source CSV. |
| Partick Thistle played / points / position | 10 / 21 / 3 | 11 / 22 / 2 | Same result. |
| Livingston position | 5 | 6 | Same result. |
| Raith Rovers position | 2 | 3 | Same result. |

Affected surfaces: `/`, `/competitions/`, `/status/`, `/metrics/`. The other
three 2026-27 league tables are unchanged. The audit is regenerated with the new
dataset version and passes.

The same release completed the historical match-stat backfill. Coverage counts
in `history` and the availability of lineup/event/player-stat fields increased
where the provider returned data; no history formula or denominator changed.

## 2.2.0 — 2026-10-22

Removed the confidence ledger. It repeated obvious statements and factoids
without adding evidence to the argument. This is an owner-directed removal, not
a formula repair.

- Removed the `confidence.document` metric family, the `param.confidence`
  parameter, the `confidence/aberdeen.json` payload and mart, the
  `ConfidenceTable` component, the confidence types and getter, and the
  `/analysis/` and `/matchday/` confidence blocks.
- Removed the `confidence.ledger` and `matchday.confidence` contract markers and
  their pinned tests. No other surface contract changed.
- Removed `docs/confidence.md` and the confidence method sections from
  `docs/analysis.md`, `docs/matchday.md` and `docs/methodology.md`.
- Retained from 2.1.0: `matches.document`, `fixtures.index`, `xg.document`,
  `param.xg` and `param.fixtures`.
- Registry version `2.2.0`; 56 metrics and 16 parameters.
- fxG remains, descriptive only while the provider gate fails. It is no longer
  described as entering a confidence verdict.
- Affected surfaces: `/analysis/`, `/matchday/`, `/methodology/`, `/metrics/`,
  `/status/`.

## 2.2.1 — 2026-10-22

Match scoreboard and event attribution corrections.

- Added `scoreboard`, timeline `side`/`beneficiary_side`/`card_type`/
  `is_missed_penalty`, and player-stat `team_name`/`is_aberdeen` to the fixture
  document. `matches.document` moves to version 2; registry version 2.2.1.
- Corrected own-goal attribution. API-Football's own-goal event team is the
  benefiting team; the old timeline flipped it. Examples:
  - `1174068` Aberdeen 3–1 Kilmarnock now ends 3–1 (was 2–2 in the timeline);
  - `569617` Aberdeen 0–2 Livingston now ends 0–2 (was 1–1);
  - `1382671` Hearts 2–0 Aberdeen now ends 2–0 (was 1–1).
- Corrected team alias matching (`Dundee Utd`, `Heart OF Midlothian`, etc.) via
  the team registry, with an exact-name fallback.
- Reclassified unflagged penalty-shootout events for PEN fixtures when excluding
  them reconciles to the final score. `693837` is 2–2 with 5–3 penalties; its
  timeline no longer runs to 7–5.
- Summaries now consume the corrected timeline, so the read reconciles with the
  final score.
- Nine fixtures have no event feed and one (`288887`) is partial; the scoreboard
  labels them unavailable/incomplete rather than inventing goals.
- Affected surfaces: `/matches/`, `/matches/<fixture_id>/`, `/analysis/`,
  `/metrics/`, `/status/`.
- Audit impact: the existing `matches.document` wildcard covers the new numeric
  leaves; the audit passes and the fixture checker verifies scoreboard/timeline
  reconciliation.

## 2.3.0 — 2026-10-22

Six-lens review remediation. Owner approval recorded in the reviewed plan.
Registry version 2.3.0.

### Definitions and parameters

- Replaced 48 placeholder formulas with explicit definitions or document-envelope
  definitions. A registry lint now rejects the placeholder phrases.
- Metrics whose definitions changed in this entry (versions bumped): table.cutoffs, competition.index, cup.league, cup.scottish, matchday.strength, matchday.style, matchday.lineup, matchday.coverage, matchday.head-to-head, matchday.next-fixtures, needs.family, needs.roster-space, needs.coverage, transfers.row, transfers.valuation, transfers.sell-on, transfers.loans, transfers.plausibility, transfers.audit, transfers.coverage, history.scorecard, history.season, history.staff, history.coverage, history.season-document, squad.players, squad.meta, player.page, rumours.profile, forum.signal, provenance.layers, coverage.surfaces, clubs.aberdeen, availability.ledger, case.document, case.claims, case.evidence, case.benchmark, case.coverage, case.claim.team-now, case.claim.defence, case.claim.attack, case.claim.managers, case.claim.squad, case.claim.chairman-record, matches.document, fixtures.index, xg.document, history.defeats.
- `param.fixtures.pages` now describes `team_stats` (not `league_stats`), adds
  `partial_classes`, and adds the `partial` depth label.
- `matches.document` summary now carries `events_available`, `goals_complete` and
  nullable reconciliation fields.
- `xg.document` evaluation now reports distinct `matches` and `team_rows`.

### Value changes

| Field | Before | After | Reason |
|---|---:|---:|---|
| Canonical played fixtures | 370 | 367 | Three duplicate provider records became labelled aliases. |
| Friendlies | 19 | 16 | Same dedup; `870984`/`871150`, `870479`/`891298`/`922189`. |
| Depth `score` pages | 39 | 6 | 30 pages with events/stats are now `partial`; the label no longer understates the page. |
| Depth `partial` pages | 0 | 30 | New honest state. |
| Scottish Cup competition labels | 23 × `FA Cup` | 23 × `Scottish Gas Men's Scottish Cup` | Provider label passthrough removed. |
| Second-yellow dismissals | 0 labelled | 30 labelled | A red after two yellows is inferred as a second yellow. |
| No-event summaries | “records 0 goals” on 9 pages | “event feed is unavailable” | Unknown is not zero. |
| Late-win headlines | 5 heavy defeats | “beat …” / “Ten-man …” | The phrase now requires a one-goal decisive late goal. |
| Shootout final `1372545` | “draw 1-1”, FA Cup | “beat Celtic 4-3 on penalties…” | Shootout checked before draw; canonical label. |
| Nisbet 2026-27 starts/minutes | 17 / 1,313 | 15 / 1,221 | Competitive-only scope; friendlies excluded from player and season totals. |
| Needs availability risk | 0.0 when all unknown | null | Denominator over known projected players; score renormalised. |
| Forum per-player sentiment | published | removed | Topic-level sentiment only; sample size shown. |

### Affected surfaces

- `/matches/`, `/matches/<fixture_id>/`, `/history/`, `/history/<season>/`,
  `/analysis/`, `/analysis/xg/`, `/matchday/`, `/recruitment/`, `/squad/`,
  `/players/<id>/`, `/metrics/`, `/status/`, `/corrections/`.
- The fixture checker now asserts depth/coverage agreement, dedup signatures,
  shootout headlines, no-event wording, late-win margin, fxG gate visibility and
  goals-prevented basis.
- The web contract adds `/corrections/`; the metrics registry and audit are
  regenerated. Audit status passes.

## 2.4.0 — 2026-10-23

fxG/provider-xG breakdown on Data analysis. Owner approval recorded in the
reviewed plan. Registry version 2.4.0.

- `xg.document` gains `provider_estimate` and `manager_splits`. The estimate is
  an OLS calibration `max(0, intercept + slope * fxg)` fitted on 2026-27 league
  team rows where provider xG exists; manager splits sum league match rows by
  date-attributed manager stint. Actual provider values and estimates are never
  summed. `xg.document` moves to version 3.
- `param.xg` gains the `provider_estimate` config node and moves to version 2.
- Existing numeric values are unchanged; the new leaves are additive. The
  estimate is `provenance_only` and is not a reconstruction of provider xG.
- Affected surfaces: `/analysis/`, `/analysis/xg/`, `/metrics/`, `/status/`.
- Audit impact: the `xg.document` wildcard covers the new numeric leaves; the
  audit is regenerated and the xG checker validates the estimate and split
  coverage.

## 2.5.0 — 2026-10-23

Scouting board, player pool and role-family cohorts. Owner approval recorded in
the reviewed plan. Registry version 2.5.0.

- New `scouting.pool` metric: provider season statistics, per-90 and percentage
  formulas, within-league role percentiles and archetype scores. Provider
  ratings are opaque and league-relative; no cross-league ranking is published.
- New `scouting.board` metric: Aberdeen role-family averages against the other
  Scottish Premiership players in the same role family, with verified
  availability and first-choice evidence. The reading is evidence, not a
  verdict.
- New `scouting.archetypes` metric: six signed weighted composites using only
  fields the licensed feed supplies, with winsorisation, robust z-scores,
  minutes shrinkage, weight renormalisation and a 70% coverage floor.
- New `scouting.squad` metric: Aberdeen registered-squad position-specific per-90
  output, competitive matches only, at 180+ minutes.
- New `scouting.coverage` metric: per-league player, rating, minutes and role
  counts; seven enabled leagues return no player statistics and are labelled.
- New `param.scouting` parameter backed by `config/scouting/model.yaml`.
- New provenance layer `scouting_pool` (API-Football player season statistics
  and starting-XI lineups).
- `scouting.pool` also covers `scouting/search-index.json`, the compact
  cross-league search index. The index carries the league with every row; it
  does not publish a cross-league percentile rank.
- Existing values are unchanged; the new leaves are additive. The new metrics
  are provenance-only or derived; `scripts/check_scouting.py` validates the
  document structure, percentile bounds, cohort bases, layer-0 statuses and
  coverage reconciliation.
- Affected surfaces: `/scouting/`, `/scouting/search/`, `/scouting/<league>/`, `/sources/`,
  `/methodology/`, `/metrics/`, `/status/`, `/sitemap.xml`.
- Audit impact: the new wildcard payload paths cover the numeric leaves; the
  audit is regenerated. Contracts and prices are not in the feed and are not
  claimed.

## 2.6.0 — 2026-10-23

Cross-league Layer 2 and the anchor-gated scouting value model. Owner approval
recorded in the reviewed plan. Registry version 2.6.0.

- `scouting.pool` now carries an empirical Premiership-equivalent percentile,
  adjusted profile scores, a 0–100 value index and value-model fields. The
  adjustment uses the observed league/role median and spread from the pool; the
  Premiership is the identity. It is a model, not a measured equivalence.
- Layer 2 archetype leaders and the pivot card now use all ranked leagues, not
  the Premiership only.
- New `scouting.value-model` metric: the value index and the GBP band, which is
  published only after the public-source anchor gate passes. With no anchors,
  the state is `awaiting_anchors` and every GBP band is null.
- New `param.scouting.value` backed by `config/scouting/value.yaml`.
- New `reference/scouting_values.yaml` anchor register, scaffolded with four
  diagnostic Aberdeen-market rows. The gate requires 60 usable anchors with
  role, tier and age coverage. The GBP band is deferred; no GBP value is
  published before the gate.
- Affected surfaces: `/scouting/`, `/scouting/search/`, `/scouting/<league>/`,
  `/metrics/`, `/status/`, `/methodology/`, `/sources/`.
- Audit impact: the new wildcard payload paths cover the value-model and
  adjusted leaves; the audit is regenerated.

## 2.7.0 — 2026-10-23

U23 and European shop-window scouting priority, and per-player scouting profile
pages. Owner approval recorded in the reviewed plan. Registry version 2.7.0.

- New `scouting.priority` metric: `scouting_priority = value_index ×
  age_multiplier × europe_multiplier`, with U23 ≤23 ×1.30 and European
  league-phase ≥90 minutes ×0.60. The priority is an Aberdeen scouting
  preference, not a measured quality term or a transfer value. Unknown European
  status is never discounted.
- `scouting.pool` gains `scouting_priority`, `age_multiplier`,
  `europe_multiplier`, `european_league_phase_minutes`,
  `european_league_phase_appearances` and `european_status`; version 2.
- `scouting.coverage` gains the European league-phase coverage block; version 2.
- `param.scouting.value` gains the `priority` block (U23 cutoff, U23 multiplier,
  European threshold, European multiplier) and moves to version 2.
- New provenance layer `scouting_europe`: the 2026-27 league phases of the
  Champions League, Europa League and Conference League, built from league-phase
  fixtures and the per-fixture player endpoint. Qualifiers and play-offs are
  excluded. 147 requests covered 54/54 UCL, 54/54 UEL and 36/36 UECL played
  league-phase fixtures at the first run; 2,130 players, 494 in the domestic
  pool.
- Layer 2 archetype leaders and the pivot card rank by scouting priority after
  the profile filter. The global and per-league searches default to priority and
  expose U23/Europe filters and columns.
- New `/scouting/player/<playerId>/` scouting profile page for every unique
  ranked player (4,105 pages), linked from the search, league tables and Layer 2.
- Affected surfaces: `/scouting/`, `/scouting/search/`, `/scouting/<league>/`,
  `/scouting/player/<id>/`, `/methodology/`, `/sources/`, `/metrics/`,
  `/status/`, `/sitemap.xml`.
- Audit impact: the new payload paths cover the priority and European leaves;
  the audit is regenerated. Existing values are unchanged except the additive
  priority fields.

## 2.8.0 — 2026-10-23

Current-club resolution and split attacker lenses. Owner approval recorded in
the reviewed request. Registry version 2.8.0.

- The scouting pool now publishes the **current club** from the provider
  transfer feed for every team in the pool, with the season-statistics club kept
  as `stats_club`. `scouting.pool` gains `current_club_status`,
  `stats_club`, `current_club_source` and `transferred_at`; version 3.
  `scouting.coverage` gains the current-club coverage block; version 3.
- Robbie Ure’s 2026-27 Allsvenskan statistics remain Sirius; his latest transfer
  is to Sevilla on 2026-08-10, so the club shown is Sevilla with “stats at
  Sirius”. A player with no later transfer keeps the stats club and is labelled
  `source: stats_snapshot`.
- The combined “goal contributor” archetype is replaced by **assist-biased
  contributor** and **goal-scoring forward** profiles. `scouting.archetypes`
  gains the attacker payload path and moves to version 2; the hub gains the
  attacker leader sections and a dedicated goal-scoring table ordered by goals
  per 90.
- New provenance layer `scouting_current_clubs` (API-Football team transfer
  feed). The current-club source, snapshot date, team coverage and the
  subsequent-move limitation are published.
- New `/scouting/player/<playerId>/` profile pages show current club, stats
  club, transfer date/source, priority and the seven archetype scores.
- Affected surfaces: `/scouting/`, `/scouting/search/`, `/scouting/<league>/`,
  `/scouting/player/<id>/`, `/sources/`, `/methodology/`, `/metrics/`,
  `/status/`, `/sitemap.xml`.
- Audit impact: the new payload paths cover the current-club and attacker
  leaves; the audit is regenerated.

## 2.9.0 — 2026-10-23

Separate the assist and goal-scoring attacker rankings. Owner approval recorded
in the reviewed request: the two lists were displaying the same players.
Registry version 2.9.0.

- `config/scouting/archetypes.yaml`: the assist-biased profile now weights
  completed passes 0.25, key passes 0.30, pass completion 0.05, assists 0.25
  and successful dribbles 0.15. The goal-scoring profile weights goals 0.50,
  shots 0.20, conversion 0.20 and goal contribution 0.10, and deliberately
  excludes pass and dribble volume. The feed has no cross data.
- Layer 2 profile leaders and the attacker assist/goal lists are now ordered by
  the profile's adjusted score multiplied by the published U23 and European
  league-phase multipliers, not by the value-index priority. Ranking by value
  index alone produced the same names in the same order for every attacking
  profile.
- Layer 2 leaders now show the current club and keep the stats club where it
  differs; previously the leader list used the stats club.
- `scouting.archetypes` description, fields, limitations and payload paths
  updated; the stale `/pivot/**` path is removed. Version 3.
- The dead double-pivot builder and its limitation sentence are removed.
- Affected surfaces: `/scouting/`. Audit impact: payload paths unchanged except
  the removed pivot path; the audit is regenerated. Published archetype scores
  change for the assist profile because its weights changed; no other metric
  changes.

Also included in this publish, carried from the uncommitted 2.7.0/2.8.0 work:
`scouting.pool` v3 current-club/stats-club fields, `scouting.coverage` v3
current-club and European coverage blocks, the new `scouting.priority`
metric, and the `param.scouting.value` v2 priority block. These identifiers
are listed here because this is the first registry version validated against
`origin/main`; their definitions are recorded in the 2.7.0 and 2.8.0 entries
above.

## 3.0.0 — 2026-10-23

Nightingale player roses and the unified player-profile standard. Owner
approval recorded in the reviewed request. Registry version 3.0.0.

- New `config/player-rose.yaml` defines the 16-metric catalogue, the shared
  10-axis overall outfield set, the goalkeeper overall/position sets, the ten
  role-family position sets and the four provider-group fallback sets. The
  thresholds are not duplicated: `config/scouting/model.yaml` supplies the
  450-minute pool cohort, 180-minute squad gate and cohort minima.
- `saves_p90` is added to the shared rate fields so goalkeepers have a
  five-axis overall and four-axis position profile. It is derived as
  `saves * 90 / minutes`.
- Both roses compare with the same role-family cohort (provider position group
  when the role cohort is below its minimum). Percentiles are midrank ranks
  from 0 to 100; `conceded_p90` is ranked on negated values. Missing values and
  insufficient cohorts are null, never zero.
- `scouting.pool` gains `saves_p90`, `rose`, `rose_meta` and the rose
  percentile fields; version 4. `scouting.squad` gains `saves_p90` and `rose`;
  version 2. `player.page` gains the profile, availability and recent-match
  projections and their limitations; version 3.
- New `param.player.rose` records `min_petals` and points at
  `config/player-rose.yaml`; the catalogue and axis sets are declared in the
  metric inputs and the contract file.
- The `/players/<id>/` result document moves to schema 1.1.0 with Profile,
  Availability, Position, Playing time, Performance, Recent matches and
  Records panels. Current Aberdeen squad members get availability and a latest
  10 competitive-match log; loan-out profiles mark those panels not applicable.
- The `/scouting/player/<id>/` page adopts the shared header, rose, key facts,
  output and profile-score order; priority and Europe move to Scouting context.
- `docs/player-profile-standard.md` is the new normative standard. Affected
  surfaces: `/players/<id>/`, `/scouting/player/<id>/`, `/scouting/`,
  `/methodology/`, `/sources/`, `/metrics/`, `/status/`.
- Audit impact: `player.page` already covers every numeric leaf under
  `players/*.json`; `scouting.pool` covers the pool documents. The audit is
  regenerated. Existing values other than the archetype weight change in 2.9.0
  are unchanged; the new values are additive.

Also included in this publish, carried from the uncommitted 2.7.0/2.8.0 work:
`scouting.archetypes` v3 (attacker split, profile ordering and stale pivot path
removal), `scouting.coverage` v3 current-club/European blocks, the new
`scouting.priority` metric, and the `param.scouting.value` v2 priority block.
These identifiers are listed here because this is the first registry version
validated against `origin/main`; their definitions are recorded in the 2.7.0
and 2.8.0 entries above.

## 3.1.0 — 2026-10-23

Season overview and the full fixture calendar. Owner approval recorded in the
reviewed request and the six-agent review record. Registry version 3.1.0.

- New `analysis.summary` metric covers `analysis/summary.json`: current table
  row and form, the next three fixtures, official and derived availability,
  measured season aims, factual squad-decision lenses and the bridge block.
- `fixtures.index` gains `scheduled`, `scheduled_count` and the schedule
  coverage fields; version 3. The played `fixtures`/`count` contract is
  unchanged, and scheduled rows have no page or sitemap entry.
- `matchday.next-fixtures` becomes current plus the next five (six-game
  lookahead), excludes friendlies/conflicts, and records local kickoff; version
  3.
- `xg.document` no longer lists `/analysis/` as a displayed surface and moves
  to version 4; `/analysis/xg/` remains the deep page.
- New `param.analysis` registers the next-up count, lookahead count, selection
  watch, squad-decision thresholds and absence-inference window.
- New `config/suspensions.yaml` registers sourced rules with `verified` flags.
  Unverified rules publish watch/review-required states, not player bans.
- New `data/normalized/matches/player_squads.parquet` records all starters and
  named substitutes, including unused substitutes, with per-side
  `bench_complete`.
- The `/analysis/` page is now the season overview; old claim cards, owner view,
  chairman frame, benchmark and xG tables are no longer rendered there. The
  case payload and `matchday.themes` strip remain contracted and unchanged.
- Affected surfaces: `/analysis/`, `/matches/`, `/matchday/`, `/themes/`,
  `/methodology/`, `/sources/`, `/metrics/`, `/status/`, `/sitemap.xml`.
- Audit impact: the new payload paths cover the analysis, scheduled fixture and
  lookahead leaves; the audit is regenerated. Existing published values are
  unchanged; the new values are additive.

Also included in this publish, carried from the uncommitted 3.0.0 rose work:
`player.page` v3, `scouting.archetypes` v3, `scouting.coverage` v3,
`scouting.pool` v4, `scouting.priority`, `scouting.squad` v2,
`param.player.rose` and the `param.scouting.value` priority block. These
identifiers are listed here because this is the first registry version
validated against `origin/main`; their definitions are in the 3.0.0 entry above.

## 3.2.0 — 2026-10-23

Team-context scouting lens. Owner approval recorded in the reviewed request.
Registry version 3.2.0.

- New `scouting.team-lens` metric covers league team standings, team points
  percentile and `team_lift` (player role-adjusted percentile minus team points
  percentile). A team is underperforming at or below the configured points-per-game
  percentile; a league without a table is unknown.
- The pool and search payloads gain `team_rank`, `team_points`, `team_played`,
  `team_ppg`, `team_count`, `team_points_percentile`, `team_underperforming` and
  `team_lift`; `scouting.pool` moves to version 5.
- `scouting.coverage` gains the standings coverage block; version 4.
- New `param.scouting.team-context` registers the threshold, minimum lift, lens
  limit and note.
- New provenance layer: provider league tables for every enabled scouting
  league, one request per league; groups choose the table with the most played
  rounds. Missing tables are `unknown`, not zero-strength.
- A new `/scouting/` section, search filter/sort and player-profile team-context
  card consume the lens. The lens is a contrast, not a valuation or
  recommendation.
- Affected surfaces: `/scouting/`, `/scouting/search/`, `/scouting/<league>/`,
  `/scouting/player/<id>/`, `/sources/`, `/methodology/`, `/metrics/`.
- Audit impact: the new payload paths cover the team-context leaves; the audit
  is regenerated. Existing scouting values other than additive fields are
  unchanged.

