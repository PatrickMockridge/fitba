# Page contracts

**Status:** normative for the contracted routes. Last reviewed 2026-10-22.
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
- Themes strip, head-to-head table with Date/Match/Score/Aberdeen, and the
  coverage/limits card with snapshot counts and source/method links.

May be disclosed: long method notes. The XIs, selection weights, form, style and
not-considered data are visible.

Forbidden: "Who imposes what?", "Who starts?", bare form rows without GF/GA/
shots, strength bars without percentiles, a predicted XI without confidence.

### `/analysis/` — Data analysis

Must remain visible:

- The chairman's frame, sourced and labelled as a summary.
- The site owner's view, attributed as opinion.
- The thesis.
- Every published claim with its title, claim, count, status, status reason,
  evidence table, what better data would do and what would change the view.
- The evidence table columns: Claim, Count, Sample, Period, Status, Source.
- The peer benchmark table and its note that other clubs' transfer and wage
  models are not in the public record.
- The compact fxG aggregate table and the link to `/analysis/xg/`.
- Coverage: availability, historical appearances and the missing data classes.
- Links to matchday, matches, squad, recruitment, transfers, history,
  methodology, metrics and sources.

May be disclosed: method, definitions, long caveats and the full data-science
supporting content. They are linked, not repeated before the argument.

Forbidden: the old five-card/five-panel grid, the 80/20 split, a question
heading, a claim without a count or status, a causal claim from a small sample,
a proxy presented as a measured set-play/error claim, or hidden contracted data.


### `/analysis/xg/` — fxG model

Must remain visible:

- The model id, label, experimental status and fit size.
- The provider-xG evaluation: status, validation season, matches, bias, MAE and
  calibration slope.
- The aggregate table with columns Scope, Matches, fxG, 80% interval, Goals,
  Goals − fxG, 80% interval.
- Coverage: played fixtures, with fxG, with provider xG, missing team stats.
- The model card: what it does, what it does not do and the gate result.
- Links to Data analysis, methodology and the match record.

Forbidden: calling fxG provider xG, hiding the gate failure, a point estimate
without its interval, or a result prediction.

### `/matches/` — match record

Must remain visible:

- Every played fixture grouped by season, with Date, Competition, Home, Score,
  Away, Result and Depth.
- Links to each fixture page.
- The depth labels and the note that missing classes are unavailable.
- Links to Data analysis, fxG, matchday and the Cormack era.

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
  timeline, lineups and player stats. Team names and a visible team key remain;
  colour is never the only cue.
- The deterministic read with measured/inferred/unknown basis.
- Match stats table with source and basis per row.
- fxG and provider xG separately, or an explicit unavailable state. When the
  fxG gate has failed, the gate status and a link to the model page are visible
  beside the number.
- Timeline with goals, cards, substitutions and VAR where available.
- Both lineups and the substitutes.
- Player match stats where available.
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

### `/squad/` — current squad

Must remain visible:

- The squad summary: size, loans out, role evidence, stats unavailable.
- The roster table: Player, Role, Age, Status, Starts, Sub, Mins, Conc, CS, G,
  A, OG, Rating, Stats, with loan status and availability labels.
- The role-mix card and the "what is measured and what is missing" card.
- The coverage note and the source/method link.

May be disclosed: the role-inference dialog and its career heat map, and long
method notes. The roster table stays visible.

Forbidden: removing the stats-unavailable or coverage labels; zero-filling
missing stats; presenting provider ratings as verdicts; hiding per-player data
behind a default-closed disclosure.

### `/history/` — the Cormack era

Must remain visible:

- The era header and the scorecard: league finishes, major honours, people in
  charge (with the interim/stint rule), and the estimated-net range with its
  inferred/confidence/known/modelled labels.
- The thesis pillars, including the market-edge unknown share.
- The season-by-season table: Season, Manager(s), League, Pos, Pts, Honours,
  Review.
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
- Links to the method and source pages.

Forbidden: claiming a corrections policy without a contact route or log.

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
- Source freshness and the published mart list.
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
