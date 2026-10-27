# Page contracts

**Status:** normative for the contracted routes. Last reviewed 2026-10-24.
**Machine-readable source:** `web/contracts/surfaces.json`.
**Guard:** `scripts/check_web_contract.py`, run after `npm run build` in CI and
before the Pages artifact is uploaded.

A contract is a floor, not a ceiling. It lists the evidence that must be visible
in the default rendered state, not the only evidence a page may show. Method
notes, caveats and definitions may sit behind disclosure; contracted data may
not.

## Marker convention

| Attribute | Purpose |
|---|---|
| `data-contract-page="<surface>"` | Identifies the contracted route |
| `data-contract-state="full\|empty\|no-fixture"` | Declares the rendered state |
| `data-contract="<surface>.<section>"` | Required data surface |
| `data-contract-indicator="basis\|confidence\|availability\|unknown\|freshness\|source"` | Visible provenance or uncertainty cue |

- IDs are lowercase kebab-case and namespaced by surface.
- Markers sit on stable section or panel roots, not individual numbers.
- Shared components take an optional `contract` prop and put the attribute on
  their root. This keeps the marker attached when a page is refactored.
- `data-contract-optional` does not suppress a required marker; it is an error
  on one. There is no `data-contract-hidden` escape.
- Required data inside a closed `<details>` fails. A closed disclosure that
  contains a table, another contract marker or an indicator also fails.

## Contracted routes

### `/` — home

Must remain visible:

- Identity hero: the line and lede.
- Matchday door: position, points, form, next fixtures.
- Off-the-pitch door: registered moves, active rumours, fan signals, latest
  confirmed moves, links to transfers, loans, scouting and rumours.
- Squad: size, loans out, average age, stats unavailable, current-season leaders.
- News and rumours: official news, the curated rumour register, forum signal.
- Competitions and the full current standings table with cutoffs and
  qualification note.
- Unknown and freshness indicators.

May be disclosed: the explanatory paragraphs inside the door cards, method
notes.

Forbidden: "Door one", "Door two", the old pyramid/pittodrie line, a three-row
standings slice in place of the table.

### `/matchday/` — matchday

Must remain visible:

- Fixture identity, competition, date, venue, state and snapshot freshness.
- The matchup read: headline, bullets and keys with measured/inferred/unknown
  basis.
- Both predicted XIs: formation and confidence, selection weights, availability
  known/unknown, the pitch, contenders, and the not-considered list.
- Form guide: last five, overall/home/away split, P/W-D-L/Pts/PPG/GF/GA/Shots.
- Style: lean, evidence, venue split, shot metrics, possession-unknown note.
- Strength: percentile comparison, table gap, confidence and cross-tier flag.
- The **How to watch** panel: UK & Ireland and International states, outlet
  and access where an official source confirms them, the source link and
  checked date, and a visible unknown/not-announced state. It never shows a
  price, stream URL or copied article text.
- Themes strip, a Next six table (current fixture plus the next five
  competitive matches; Date/Competition/Opponent/Venue/Kickoff/Watch, where
  Watch is the domestic status only), the head-to-head table with
  Date/Match/Score/Aberdeen, and the coverage/limits card with snapshot counts
  and source/method links.

May be disclosed: long method notes. The XIs, selection weights, form, style and
not-considered data are visible.

Forbidden: "Who imposes what?", "Who starts?", bare form rows without GF/GA/
shots, strength bars without percentiles, a predicted XI without confidence.

### `/analysis/` — Season overview

Must remain visible:

- The hero: position, played, points, goal difference and last-five form, with
  one freshness/source line. No opinion thesis and no duplicate fixture row.
- Next up: the next three competitive, non-conflict fixtures with Date,
  Competition, Opponent, Venue, Kickoff and Status, plus links to the six-game
  matchday lookahead and the full `/matches/` schedule.
- Availability and selection: counts (known unavailable, reported available,
  no verified news, loans out); official AFC team news with source and
  verification date; competition-scoped derived suspension watch; inferred
  absence rows with basis and the exact two fixture dates; a capped selection
  watch. Full roster stays on `/squad/`.
- Season aims: at most three aims with Aim, Target, Current and Status, and the
  visible label “Analyst-set baseline, not a published club target”.
- Squad decisions: measured age, minutes, role and percentile lenses with the
  denominator and sample count; loan-out count and role/needs context; one
  block-level note that contract, fee and wage data is unavailable.
- Bridges to matchday, matches, squad, scouting, fxG, methodology and sources.
- Coverage: known/unknown availability, card and bench coverage, fixture
  conflicts and limitations.

The active availability universe is the current squad plus ledger-only players;
loan-outs are separate. Counts must sum to that universe. “Available” means a
verified ledger entry, not fit; inferred absence is “not in the last two
matchday squads — reason not published”, never injury.

Forbidden: owner view, chairman frame, thesis, claim cards, benchmark, xG
tables (they stay on `/analysis/xg/`), a medical diagnosis from selection
patterns, a ban from an unverified rule, a global suspension state, a value or
transfer recommendation, a fee/wage/contract-expiry claim, “will leave”,
“sell-high”, a question heading, or hiding unknown/coverage states.

### `/analysis/xg/` — fxG model

Must remain visible:

- The model id, label, experimental status and fit size (matches and team rows).
- The provider-xG calibration: method, status, validation season, matches, team
  rows, bias, MAE and calibration slope.
- The aggregate table with columns Scope, Matches, fxG, 80% model range, xG per
  shot, Goals, 80% goals range, Goals − fxG.
- The uncertainty card: the model range, the goals range, bootstrap and
  dispersion, and why per-match intervals are never summed.
- The overperformance and style cards: Goals − fxG and its position, xG per
  shot, shot volume, penalties and the no-style-adjustment caveat.
- The provider card: provider xG sources, separation from fxG, and the absence
  of xGOT and shot coordinates.
- Coverage: played fixtures, with fxG, with provider xG, missing team stats.
- The model card: what it does, what it does not do, the selected specification,
  coefficients, candidate table, calibration result and transfer check.
- Links to Season overview, methodology and the results and fixtures page.

Forbidden: calling fxG provider xG, hiding the calibration status, a point
estimate without its model and goals ranges, summing per-match intervals,
calling either range a confidence interval for team quality, or a result
prediction.

### `/matches/` — results and fixtures

Must remain visible:

- Every played fixture grouped by season, with Date, Competition, Home, Score,
  Away, Result and Depth.
- The remaining scheduled fixtures for the selected season in an Upcoming table
  with Date, Competition, Home, Away, Venue, Kickoff, Status and Watch. Watch is
  the domestic (UK & Ireland) state only; a missing listing is not a claim that
  the match is not televised. Scheduled rows have no fixture page and are never
  in the sitemap.
- A season selector bar that defaults to the current season and shows one
  season at a time; every earlier season remains reachable from the bar.
- The current-season remaining count is a minimum, shown as “N+ to play”:
  cup progression and the post-split league fixtures can add to the known
  schedule.
- Links to each played fixture page.
- The depth labels and the note that missing classes are unavailable.
- Links to Season overview, fxG, matchday and the Cormack era.

Forbidden: a fixed "featured match" that hides the rest, a result without a
depth label, or a match page link that does not resolve.

### `/matches/<fixture_id>/` — fixture page

Must remain visible:

- Score, competition, round, date, venue, referee, half-time and penalties where
  present. A shootout outcome is named in the H1 and the result badge.
- The scoreboard: final score, goals with scorer, minute, assist and penalty
  marker; red cards with explicit "Straight red" and "Second yellow" labels;
  shootout score; the team key; and the event-feed completeness note.
- Aberdeen in red and the opposition neutral across the scoreboard, stats, fxG,
  timeline, lineups, player stats and performance. Team names and a visible team
  key remain; colour is never the only cue.
- The deterministic read with measured/inferred/unknown basis.
- Match stats table with source and basis per row.
- fxG, its 80% model range, its 80% goals range and provider xG separately, or
  an explicit unavailable state. Goals, Goals − fxG and the below/within/above
  position, xG per shot, the shot profile, penalties and the model basis are
  visible. The calibration status and a link to the model page are visible
  beside the number.
- Timeline with goals, cards, substitutions and VAR where available.
- Both lineups and the substitutes.
- Player match stats where available.
- The performance block: standout measured output for both teams (top provider
  ratings with goals, assists, shots on target, passes, tackles and duels) and
  the measured team strengths, labelled provider/measured and not a verdict.
- Coverage and the depth state.
- Previous/next match, season and match-record links.
- A duplicate record carries a visible notice and a link to the canonical match;
  it is excluded from counts and navigation.

Forbidden: a missing data class shown as zero, an invented attendance or
injury, a question H1, "deserved"/"dominated" verdict language, a fixture page
omitted because the feed is incomplete, colour-only team identity, a shootout
kick counted as a match goal, or a second yellow rendered as a straight red.

### `/themes/` — legacy redirect

The old route must show a visible link to `/analysis/` and redirect without
losing a legacy anchor. It carries no data.

### `/recruitment/` — recruitment and squad needs

Must remain visible:

- Hero and the seven-family needs board.
- Per family: priority, urgency, category, confidence, expected slots,
  available/ready/trusted counts, top share, availability risk, drivers, market
  route (fee, budget, wages), roster space, curated prior, and the player table
  with Player/Category/Starts/Minutes/Sub apps/Availability.
- Transfer register summary, rumour register summary, recruitment profile with
  sample size and low-confidence flag, forum signals.

May be disclosed: caveats and method notes.

Forbidden: a six-column needs table that drops expected slots, ready/trusted,
market route, roster, curated prior or availability; player tables hidden by
default; confidence badges removed.

### `/rumours/` — rumour mill and fan signal

Must remain visible:

- The hero, affiliation counts (external targets, former players, current
  squad), curated register, target profile, former-player lane, forum signals
  and coverage.
- The statement that former players are not transfer targets and that a return
  link is separate.
- The target-profile sample size, basis and excluded counts.
- The fan-signal table with affiliation and cross-reference labels.

May be disclosed: method notes, sentiment caveats and sampled-topic prose.

Forbidden: current or former players inside the target profile; a former player
shown as an ordinary target; raw forum posts, usernames or quotes; a mention
treated as a transfer link.

### `/transfers/` — transfers and loans

Must remain visible:

- Confirmation, curation, total and withheld badges; audited/historical coverage.
- Board filters and the estimated-net range with confidence and known/modelled/
  loan decomposition.
- The register cards: verification, position and nationality, fee or inferred
  range, loan terms (or an explicit "not confirmed" for a loan), source links.
- Sell-on clauses table: Player/Buyer/Sale/Clause/Confidence/Source.
- Register completeness: seniority review, position coverage, open/accepted/
  resolved gaps, last audit date.
- Coverage and source links.

May be disclosed: the "how to read" definitions and long fee method notes.

Forbidden: cards without position, nationality, fee basis, loan terms or
sources; a register that hides completeness; "undisclosed" counted as zero.

### `/loans/` — loan register

Must remain visible:

- Out and in counts and sections.
- Every loan card with direction, player, clubs, season/window, fee status and
  loan terms (or an explicit "not confirmed by a public source").
- Coverage: which tiers can be tracked, and that duration/recall/obligation are
  unknown unless confirmed.
- Source links where they exist.

May be disclosed: the coverage prose and long method notes.

Forbidden: loan cards without terms, a single "terms often unknown" badge with
no per-card unknown state, removal of the in/out split.

### `/former-players/` — former-player register

Must remain visible:

- The register size, sell-on clause count, rival-spell count and the visible
  `2019-20 onward` coverage line.
- Summary counts: permanent/free exits, current coverage, known top-flight
  abroad, rival spells, young exits and early-career proxy.
- The register table: Player, Left, To, Type, Fee, Age, Aberdeen apps, Aberdeen
  starts, Post seasons, Post mins, Current club, Rival, Status.
- A row link to the player's standard `/scouting/player/<id>/` profile, which
  carries the shared scouting sections plus a former-Aberdeen section. Former
  players without an API player id stay plain text with an explicit reason.
- The sell-on watch, development scorecard and former-player rumour lane.
- The development scorecard with its definitions and by-exit-season table.
- The sell-on watch with the missing-input reason where no receipt is computable.
- The sale-chain section and, on each profile, the ordered chain from departure
  through post-Aberdeen seasons and any clause, trigger and receipt. Every
  missing input keeps its published reason.
- The former-player rumour lane and the coverage/limits card.

May be disclosed: long method notes and source prose.

Forbidden: presenting a former player as a transfer target; hiding a last-known
club behind a current label; a good/bad-price or should-have-kept verdict;
zero-filling a missing post-career season or a sell-on receipt.

### `/squad/` — current squad

Must remain visible:

- The squad summary: size, loans out, role evidence, stats unavailable.
- The roster table: Player, No., Role, Age, Status, Starts, Sub, Mins, Conc, CS,
  G, A, OG, Rating, Stats, with loan status and availability labels.
- The role-family depth chart: every official squad player once across the ten
  role families, Family, Player, Role, Mins (all), Availability, Status;
  measured minutes order, unknown availability labelled, loan-outs included
  with a visible loan badge, and no quality score.
- The role-mix card: squad profile tiles (average age, registered players,
  role evidence, starts with a role) and absolute-count bars for primary
  position group and primary role family.
- The "what is measured and what is missing" card as a compact data-class
  table: Current-season output, Position and role, Minutes, Loan status, and
  Context and links.
- The coverage note and the source/method link.
- The canonical official roster source link and fetched-at note; API-only rows
  outside the official list are retained profiles, not squad rows, and official
  loanees with an unknown club say so.

May be disclosed: the role-inference dialog and its career heat map, and long
method notes. The roster table stays visible.

Forbidden: removing the stats-unavailable or coverage labels; zero-filling
missing stats; presenting provider ratings as verdicts; hiding per-player data
behind a default-closed disclosure.

### `/players/<playerId>/` — Aberdeen player profile

The extended tier of the player-profile standard. Must remain visible:

- The shared profile header: name, role, age, nationality, squad number,
  status/loan badges and the role-inference link.
- The statistical profile: **Overall profile** and **Position profile**
  Nightingale roses, each with labelled axes and an accessible title/description
  carrying the exact values and cohort n. The cohort basis, cohort n, league,
  minutes threshold and the higher-is-better rule are visible; an unavailable or
  partial figure says why and does not draw zero petals. There is no duplicate
  rose table.
- Key facts: Premiership minutes, appearances, provider rating and cohort
  percentile with the cohort basis and n. Key facts remain current-season when
  the rose uses a prior-season fallback.
- The rose's season label and visible fallback note when a prior season is used;
  the note must not imply that the prior season is current form.
- The Position panel: role inference, career evidence and club history.
- Playing time: starts, sub apps, minutes started, minutes as sub and the
  per-competition table.
- Performance: role-relevant tiles, provider table, detail table and defensive
  context where applicable.
- Availability and team news for the current squad: status, reason, expected
  return, confidence, source and verification date, with an explicit unknown
  state and no inferred injury.
- Recent matches for the current squad: date, competition, opponent, venue,
  score, result, minutes, rating, goals and assists; latest 10 competitive
  current-season rows, with a dash for missing values.
- Records outside the main scope when present.
- Coverage and limits, the source, and the squad/matchday/recruitment back
  links.

The profile is a projection of `players/<playerId>.json`; React does not
derive or merge new facts. Loan-out players keep their role and loan record but
show Availability and Recent matches as not applicable.

Forbidden: zero-filling a missing petal, hiding a missing cohort, presenting a
provider rating as a verdict, presenting a prior-season fallback as current-season
form, an injury claim without the verified ledger, a contract/wage/fee claim, or
removing a panel to fit a layout.

### `/scouting/` — scouting board

Must remain visible:

- The hero, season and the league/search counts.
- Layer 0: every verified availability entry with player, role, status, current
  minutes, prior rating and minutes, source link and verification date; an
  explicit unknown state when the ledger has no verified entry.
- Layer 1: one row per role family with players, minutes, Aberdeen rating,
  cohort median and n, percentile, availability summary and the reading
  (structural, cover, hold, none, insufficient).
- Layer 2: the seven archetype definitions with their feature weights and
  all-league profile leaders (league, club, raw score, adjusted score, value
  index, priority, U23/Europe badges). Leaders are ordered by the adjusted
  profile score multiplied by the U23 and European league-phase multipliers, so
  each profile ranks its own fit rather than the shared value-index order.
- The simple lens bar: priority rank, U23 (with only-U23), Europe shop window
  (with exclude-90+), struggling team, profile, role and league. The bar is
  always visible. With no lens active the published defaults are shown; any
  active lens selects from the full pool and is labelled **Reader scenario**
  with a visible reset. The reader scenario never replaces or relabels the
  published default order and never changes a published value or the audit.
- The published list shape: five leaders per archetype, eight per attacker
  list, twelve goal-scoring rows and twelve team-context rows. Reader
  scenarios use the same limits.
- The full-pool payload at `/scouting/pool.json` is fetched only when a lens is
  active, with a visible loading state, an explicit error and retry, and the
  published lists kept unchanged on failure. The payload is not embedded in the
  initial hub page.
- The attacker sections: assist-biased leaders, goal-biased leaders and the
  goal-scoring table with Player, Club, League, Age, Mins, Goals, Assists,
  Goals/90, G+A/90, Shots/90, Conversion, Priority. The table is ordered by
  goals per 90; it is not a recommendation.
- The team-context lens: **Outperforming struggling teams**. Teams at or below
  the configured points-per-game percentile, ranked by team lift (player
  role-adjusted percentile minus the team points percentile). Columns: Player,
  Club, League, Team, Team PPG %, Adj %, Lift, Priority. It is a contrast, not a
  valuation, forecast or recommendation; a league without a table is unknown.
- The scouting-weights card: U23 cutoff and multiplier, European league-phase
  threshold and multiplier, the priority formula, the preference caveat and the
  European coverage. The card is the published reference; numeric weight
  controls live only on the full search.
- The value index is a scouting ordering, not a transfer value; a GBP band is
  deferred until a public-source anchor register is available.
- The league index: every enabled league with players, rated, 450+, role
  coverage, status and a link to its search page. No-player-statistics leagues
  are labelled.
- The squad profile table: Player, Role, Mins, Rating, Pct, G+A/90, Shots/90,
  Dribbles/90, Passes/90, Pass %, Key passes/90, Tackles/90, Interceptions/90,
  Duels won %.
- Coverage: totals, known gaps, sources and links to method and sources.

May be disclosed: long method notes and the archetype feature definitions.

Forbidden: a provider rating presented as a verdict; a cross-league ranking; a
contract, wage or fee claim; a first-choice or injury claim without a verified
official source; a pivot pairing presented as a causal fix; zero-filling a
league with no player statistics.

### `/scouting/<league>/` — league player search

One static page per enabled league. Must remain visible:

- The league name, country, season and source.
- The lens selector and the search filters, with a single or layered lens summary.
- The ranked table at 450+ minutes: Player, Club, Team, Lift, Role, Age, Mins,
  Rating, Pct, Adj Pct, Value index, Priority, Europe, G+A/90, Dribbles/90,
  Passes/90, Pass %, Key passes/90, Tackles/90, Interceptions/90, Duels won %,
  Profile.
- A caption stating that percentiles are within the league and role, and a
  visible link back to `/scouting/`.
- Coverage: played fixtures, players with a role, the 450+ pool, rated players
  and the limits. A league with no player statistics shows an explicit empty
  state, not zero rows.

Forbidden: a table without a caption; a percentile presented across leagues; a
missing role shown as a guessed role; hiding the no-player-statistics state.

### `/scouting/search/` — full scouting search

Must remain visible:

- The hero counts: ranked players, leagues with players and the season.
- The basic lens selector (priority rank, U23, Europe, struggling team, profile,
  role, league) in single or layered mode, plus sort.
- The always-visible **Advanced filters** panel: reader-set U23 cutoff and
  multiplier, European minutes threshold and multiplier; reader-set value-index
  weights (performance, age, minutes, profile) with the normalised share; reader
  team-context thresholds (underperforming PPG percentile and minimum lift);
  and eligibility filters (text, nationality, minimum minutes, maximum age,
  European status, role-known only, minimum value-index coverage). The panel
  carries a visible **Published defaults** / **Reader scenario** label and a
  reset. Reader weights recompute the displayed value index and priority only;
  they do not change the published values, registry or audit.
- The full table: Player, Club, Team, Lift, League, Nationality, Role, Age, Mins,
  Rating, Pct, Adj Pct, Value index, Priority, Europe, G+A/90, Dribbles/90,
  Passes/90, Pass %, Key passes/90, Tackles/90, Interceptions/90, Duels won %, Profile.
  Club is the current club from the provider transfer feed; League is where the
  2026-27 statistics were produced. When the two clubs differ, the stats club is
  visible beside the current club.
- The league column and a visible statement that percentiles are within each
  league and role, never a cross-league ranking.
- The guarded comparison panel: two players selectable from the published
  scouting rows and the reviewed current-squad crosswalk; same league and role
  only; minutes, percentile, cohort basis and cohort n visible; a not-comparable
  reason; no winner, delta, ranking or recommendation.
- Coverage: ranked players, leagues with players, leagues without stats and the
  cross-league limitation.
- Links back to `/scouting/`, `/methodology/` and `/sources/`.

Forbidden: a raw percentile presented as a cross-league rank; hiding the league;
a GBP value claim; a contract, wage or fee claim; an empty table without an
explicit state; presenting a reader scenario as the published default; hiding
the advanced filters or reset.

### `/scouting/player/<playerId>/` — scouting profile

One static page for every unique ranked player. Must remain visible:

- Name, current club, stats club, league, nationality, age with U23 badge and
  role. The profile must state when the current club and the stats club differ
  and show the transfer date and source.
- The shared statistical profile: **Overall profile** and **Position profile**
  Nightingale roses with labelled axes, an accessible title/description carrying
  the exact values and cohort n, the cohort basis and n, and the
  higher-is-better rule. No duplicate rose table.
- Minutes, appearances, provider rating, within-league percentile, adjusted
  percentile and value index.
- Team context: league position, points/played, team points-per-game percentile
  and team lift (role-adjusted percentile minus team PPG percentile), or an
  explicit no-table state. The lift is a contrast, not a valuation or
  recommendation.
- Scouting priority with the value index × age multiplier × Europe multiplier
  arithmetic, and the preference caveat.
- Europe: status, competitions, league-phase minutes and appearances, the
  90-minute threshold and the unknown-not-discounted rule.
- The seven archetype scores, raw and adjusted, with coverage.
- The role/cohort basis, coverage and limitations. The per-90 values are encoded
  by the rose axes and their accessible descriptions; there is no duplicate
  per-90 table.
- The statement that this is not a target, recommendation, fee or contract
  claim.
- Links back to the league search, the full search, the scouting board, method
  and sources.

Forbidden: a contract, wage or fee claim; a recommendation or target language;
a missing European status shown as zero; a profile without the priority
arithmetic or the profile scores.

### `/history/` — the Cormack era

Must remain visible:

- The era header and the scorecard: league finishes, major honours, people in
  charge (with the interim/stint rule), and the estimated-net range with its
  inferred/confidence/known/modelled labels.
- The thesis pillars, including the market-edge unknown share.
- The season-by-season table: Season, Manager(s), League, Pos, Pts, Honours,
  Review.
- The Cormack-era lookup: season, manager, honour and competition filters over
  the published season records, with a reset and a matching-season table. It
  navigates published rows only and does not rank or add a superlative.
- The current staff and the manager records table: Manager, Dates, Pld, W-D-L,
  GF, GA, Pts, PPG, with interim spells and pre-era stints labelled.
- The baseline table, labelled as a chosen comparison window rather than a
  neutral norm.
- The honours cabinet, the read block, and the coverage-by-season table.
- The page's source and method links.

May be disclosed: the full staff timeline and long method notes. The manager
records and league tables stay visible.

Forbidden: collapsing Europe to an unqualified "Europe"; removing the
estimated-net confidence or known/modelled split; presenting the baseline as
neutral; leaving heavy defeats or the European finishing position only in
prose; deleting position or points.

### `/sources/` — provenance and licences

Must remain visible:

- The layer truth table: Layer, Primary, Fallback, Status, Rows, Scope.
- The source registry: Source, Lane, Primary layers, Rows, Last checked.
- The league-migration gate, the availability special case, the excluded
  sources, and the derived/not-raw and no-redistribution statements.
- Source and unknown indicators.

May be disclosed: the long attribution notes.

Forbidden: removing a licence, source URL or last-checked date; a source list
that omits the layers it supports; a gated source presented as primary.

### `/methodology/` — method

Must remain visible:

- The source table: Source, Publication lane, Rows, Last checked.
- The definitions, cut-offs, cup formats, assumptions, coverage, reconstruction,
  matchday, transfer, history, player-output, register and policy sections.
- The source and unknown indicators.

May be disclosed: long method detail inside a section.

Forbidden: deleting method text to shorten the page; removing the corrections
policy or last-reviewed date; presenting a derived number as measured.

### `/corrections/` — policy, contact and log

Must remain visible:

- The corrections policy and what information to include.
- A public contact route and the last-reviewed date.
- A dated log with the affected page, the claim, the correction and the status.
- A change kind for every entry (correction, metric, source, page or data) and a
  link to the metric-changes narrative for a metric entry.
- Links to the method and source pages.

Forbidden: claiming a corrections policy without a contact route or log.

### `/search/` — search the record

Must remain visible:

- A flat, unranked index of published pages, matches, players, clubs, staff,
  seasons and claims, grouped by type.
- The scouting pool as a separate group that loads on request; the initial page
  does not embed the full scouting index.
- The statement that results link to the existing record and are not a ranking,
  target list or supplementary player profile.
- The source and as-of context on a result, and links to the scouting search,
  metrics and sources.

Forbidden: ranking by popularity or engagement; tracking queries or using
reader history; a second player profile presented in the result list.

### `/glossary/` — glossary and definitions

Must remain visible:

- One entry per active registered metric with its formula, unit, basis,
  coverage tier, source layer, limitations and registry version.
- The curated concept entries, grouped by category, with their aliases and the
  metric ids they explain.
- The statement that a metric entry is copied from the registry and a curated
  concept cannot override a registered definition.
- Links to `/metrics/`, `/sources/`, `/methodology/` and `/corrections/`.
- A stable `#def-<id>` anchor per entry so page provenance and future inline
  terms resolve.

Forbidden: a number outside the registry; a curated entry with a formula; a
definition hidden behind a default-closed disclosure; a metric entry without its
basis or coverage tier.

### `/unknowns/` — unknowns register

Must remain visible:

- One entry per unknown class, grouped by domain, with the label, description
  and the reason it is unknown.
- The affected surfaces, linked to their pages.
- Either a named public resolving source or an explicit **no public source**
  state. A no-source class never carries a fabricated URL or an estimate.
- A published count only where it already exists in a registered metric payload,
  linked to that metric and its glossary entry.
- The dedicated no-public-source section.
- Links to `/sources/`, `/glossary/`, `/metrics/` and `/corrections/`.

Forbidden: inventing a resolver; presenting an unknown as zero; a club-request
framing; a new aggregate count; ranking or prioritising the gaps.

### `/claims/` — claims and evidence

Must remain visible:

- Every published claim with its order, domain, status, evidence table, count,
  sample and confidence.
- The claim benchmark and the claim coverage block.
- The statement that the claims are fitba-owned, include the unflattering
  numbers and are not a club briefing.
- Links to the season overview, matchday and metrics.

Forbidden: removing an unflattering claim; a claim without its evidence or
status; presenting interpretation as a measured count.

### `/about/` — identity and editorial standard

Must remain visible:

- The identity line and lede.
- Who the site is for, and the explicit rejection of a hypothetical median user.
- On the club's side, not in its pocket.
- The Cormack-era frame: player, manager, structure.
- The line: what the site will not build.

Forbidden: the old "translation layer" identity line, question headings, a
simplified-reader rationale.

### `/metrics/` — metrics and audit

Must remain visible:

- Registry version, review date, dataset version and audit timestamp.
- Audit status, metric and parameter pass/fail counts, rows and fields checked.
- Every active metric: id, label, definition, formula, basis, source layer,
  coverage tier, verification mode and audit status.
- Every config-backed parameter: id, value, unit, used-by, config path and
  status.
- Registry and audit checksums, allowlist status and the validation summary.
- The verification modes and what each does and does not prove, including the
  `provenance_only` limitation.
- Links to status, methodology, sources and about.

The definitions and values are data, not method: they may not be hidden behind
a default-closed disclosure. Rows carry `data-contract="metrics.registry"` and
`data-contract="metrics.parameters"`, so a removed metric or parameter fails the
guard.

### `/status/` — build status and audit summary

Must remain visible:

- Dataset version, generation time, season, schema and profile.
- File count and size.
- Validation status, check count, errors and warnings.
- Metric-audit status, registry version and checksum, metric and parameter
  counts, and the `provenance_only` count.
- Cross-surface consistency status, passed/failed check counts, and any first
  failures.
- The update run: mode, run id, status, finished time, recorded step count and
  any non-ok steps, plus the result guard and its conflicts.
- Per-source freshness: age, TTL, state and whether the source is required,
  with every stale optional source named and linked to its payload labelling.
- The published mart list.
- Coverage for competitions, cups, transfers, history, rumours and forum.

## What the guard checks

1. Required route HTML exists and declares the expected page and state.
2. Every required marker exists at least the required number of times. Per-card
   markers can use `same_as` so every card must carry the field.
3. No required marker is inside a closed `<details>`, `hidden`, `aria-hidden`,
   `.sr-only`, a script/style/template, or an inline hidden style.
4. Required table columns exist in order; extra columns are allowed.
5. Required basis/confidence/availability/unknown/freshness/source indicators
   are visible in the required numbers.
6. Required anchors and links exist and are visible, with the base path
   normalised.
7. Required identity copy is present.
8. Exactly one visible H1 per route; no interrogative H1/H2/H3; no forbidden
   heading text.
9. Banned identity phrases are absent from visible text, title and description.
10. In CI, a page cannot pass by switching to a state the manifest does not
    allow.

The checker never counts words. **Word-count budgets are prohibited.** A budget
on prose creates an incentive to delete data; prose length is an editorial
judgement, not a build gate. The checker rejects any `max_words`, `word_budget`
or similar key in the manifest.

## Contract changes

A contract change is a product decision, not a style tweak.

1. Propose the diff to this document and `web/contracts/surfaces.json` in the
   same change.
2. Add or update a test for the new behaviour.
3. State what data becomes unavailable, and why the identity still holds.
4. Obtain owner approval. Never self-approve a deletion.
5. Do not edit the checker to make a failing change pass.

Adding a contract for a new surface is allowed without approval if it does not
weaken an existing one.

## Commands

```bash
cd web && npm run build
cd .. && uv run python scripts/check_web_contract.py --ci

cd web && NEXT_PUBLIC_BASE_PATH=/fitba npm run build
cd .. && uv run python scripts/check_web_contract.py --ci --base-path /fitba

make web-contract-check
make web-contract-check BASE_PATH=/fitba
```
