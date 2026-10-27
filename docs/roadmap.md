# Roadmap

**Status:** staged plan. Last reviewed 2026-10-24.

The order is deliberate: prove the audience and the analysis before buying
expensive data, and never let an unlicensed feed become the foundation.

## Current status

| Phase | Status |
|---|---|
| 0. Documentation and source gate | **Complete.** API key-tested; docs and in-app pages live. |
| 1. One licensed base | **Partially complete.** API-Football active for cups and player basics; league migration pending. |
| 2. Full cup data | **Partial by licence.** League Cup complete; Scottish Cup 50 of 136 ties, labelled. |
| 3. Competition pages | **Complete.** `/competitions/`, League Cup and Scottish Cup pages live. |
| 4. Transfers and loans | **Live for Aberdeen.** Confirmed-business register, `/transfers/` and `/loans/`. |
| 4b. Two doors and rumour mill | **Live.** `/matchday/`, `/recruitment/`, curated rumours, fan signal and the advisory profile; engagement deferred. |
| 4c. Squad and player profiles | **Live.** `/squad/`, one `/players/<id>/` page per player with the shared two-figure Nightingale rose, extended current-squad availability and recent-match log, loan tags, coverage states and site-wide player links. |
| 4d. Cormack-era historical record | **Live.** `/history/`, one season review per season, manager/staff timeline, honours, historical transfers, style and selection. |
| 4e. Upcoming-matchday dashboard | **Live.** `/matchday/`, both predicted XIs, form, venue splits, style lean and strength; `/clubs/aberdeen/` retired to a moved notice. |
| 4f. Season overview | **Live.** `/analysis/` is the season briefing: next fixtures, availability, aims, squad decisions and bridges; `/analysis/xg/` remains the xG deep page. |
| 4g. Provenance, availability and needs | **Live.** Layer truth table at `/sources/`, curated availability ledger in the predicted XI, and a squad-needs board on `/recruitment/` that feeds the scouting method. |
| 4h. Results, fixtures and fxG | **Live.** `/matches/` shows results and the known remaining schedule, with one page per played fixture and an experimental fxG model at `/analysis/xg/`. The provider gate is failing, so fxG is descriptive only. |
| 4i. Scouting board | **Live.** `/scouting/` and one page per league and a full cross-league search: role-family cohorts, verified availability and seven profiles, including split assist/goal attacker lenses. An empirical league alignment, a value index, U23/European scouting priority, a team-context lens for outperforming struggling teams, simple reader-selectable lenses on the hub, advanced reader filters (U23/Europe and value-index weights, team thresholds and eligibility) on the full search, and one profile page per ranked player are live; GBP value bands, style fit and budget bands are deferred. |
| 4j. Documentation book | **Live in the repository.** The Markdown docs are rendered with mdBook in the Merkland (light) and Aurora (dark) palettes, with search and accessibility markup. The book is not deployed to the website. |
| 4k. Former players | **Live.** `/former-players/` carries the confirmed departure register, Aberdeen and post-Aberdeen records, rival spells, sell-on watch and the development scorecard. Rumour affiliation separates former players from targets. |
| 4l. Access, citation and trust layer | **Live (first phase).** `entities/index.json`, `page-meta.json`, `definitions.json` and `changelog.json`; `/search/` with lazy scouted group; `/claims/`; expanded `/corrections/`; page provenance, citations and as-of badges; sticky tables; scouting search sharded under a page budget. See [Semantic layer](semantic-layer.md) and the [UX audit](ux-audit-2026-10.md). |
| 4m. Evidence navigation and comparison | **Live (except game state).** Claims at `/claims/`, definitions at `/glossary/`, the unknowns register at `/unknowns/`, first-use inline terms, a guarded comparison panel on `/scouting/search/` with a reviewed current-squad crosswalk, a ten-family depth chart on `/squad/`, the sale chain on `/former-players/` and profiles, and the Cormack-era lookup on `/history/`. Match game-state/streak context is deferred; no live or in-game updates. See the [UX audit](ux-audit-2026-10.md). |
| 4n. Distribution and export | **Deferred.** Print/OG cards, export/embed and full current-player multi-season output, pending licence, design and payload decisions. See [UX audit](ux-audit-2026-10.md). |
| 5. Fan-facing insight layer | **Next.** Trading analytics, richer opposition context and the style/budget fit layer. |
| 5. Local rich-visual prototype | Not started. |
| 6. Enterprise evaluation | Not started. |

## Phase 0 — Documentation and source gate (complete)

- Write the product strategy, trading-model, methodology, scouting, competition
  format, sources, architecture and roadmap documents.
- Add the API-Football source entry and key-test script.
- Obtain a key; verify Scottish competition IDs, League Cup group fixtures,
  early Scottish Cup rounds, lineups/player stats and the cup-standings gap.
- Confirm public-display terms.
- **Gate:** no paid subscription and no cup-code expansion until the test passes.

## Phase 1 — One licensed base (partially complete)

- API-Football adapter and normalized league/cup ingestion.
- Migrate public league results to the licensed source.
- Keep football-data only as a local cross-check; retire the public scrapers.
- Coverage, attribution and last-checked data in the manifest and `/sources/`.

## Phase 2 — Full cup data (partial by licence)

- League Cup group fixtures and computed group tables (3/1 + shoot-out bonus).
- League Cup knockout rounds, including extra time and penalties.
- Scottish Cup rounds from the preliminary stage, byes and penalty shoot-outs.
- Team registry expansion for cup-only clubs.
- Validation against official results and formats.

**Current licensed coverage:** League Cup complete; Scottish Cup First and
Second Round (50 of 136 ties). The three preliminary rounds and later rounds are
not in the feed at the key-test date. They are labelled missing on the page.
Full coverage requires Sportmonks or an enterprise provider; it is not assumed.

## Phase 3 — Competition pages (complete)

- `/competitions/` index limited to the competitions Aberdeen are competing in
  this season.
- `/competitions/league-cup/` with group tables and knockout rounds.
- `/competitions/scottish-cup/` with round-by-round ties and Aberdeen's entry.
- Current-stage callouts and "awaiting draw" states; the full pyramid remains
  on `/scotland/`.

## Phase 4 — Fan-facing insight layer (scouting delivered)

The scouting board, full search, value index, U23/European priority,
team-context lens, reader-selectable lenses and advanced filters are live; see
row 4i. The documentation book is live; see row 4j. What remains from this
phase:

- Trading-club dashboard: squad age/value, minutes by age, inferred transfer
  balance, sell-on candidates, contracts and loans.
- Opposition briefings using the same framework.
- Style fit, budget bands and the remaining coverage labels for scouting.
- Explainer cards, glossary and a clearer methodology layer.
- Progressive-disclosure components on every insight.

### Phase 4l — reader-first data layer and UX serving (delivered)

Source to serve, in order: the source adapters and TTLs are unchanged; the
canonical entity namespace lands in `normalize/entities.py`; the semantic bundle
publishes five documents; `/search/`, `/claims/` and an expanded `/corrections/`
serve them. Scouting search is sharded into meta plus four payloads under a page
budget. The change is documented in [Semantic layer](semantic-layer.md) and
registered as registry 3.10.0.

### Phase 4o — how to watch (live)

A **How to watch** card on `/matchday/` and Watch labels on `/matches/` and
`/fixtures/`: curated official club/SPFL broadcast facts for UK & Ireland and
International, with a Saturday 15:00 UK blackout rule, explicit unknown states
and no price, stream URL or article-body copying. See
[broadcast.md](broadcast.md).

### Phase 4m — evidence navigation and comparison (delivered, except game state)

- **Definitions and glossary:** `/glossary/` over `definitions.json`, with
  related concepts and first-use `DefinitionTerm` links.
- **Unknowns register:** `/unknowns/` lists the curated unknown classes, the
  reason, the affected surfaces and either a public resolver or an explicit
  no-public-source state. Counts are existing registered coverage counts only.
- **Guarded comparison:** on `/scouting/search/`. Same league and role only; a
  reviewed `reference/comparison_crosswalk.yaml` gates current-squad selection;
  no winner, delta or recommendation.
- **Role-family depth chart:** ten families on `/squad/`, measured minutes and
  availability, no quality score.
- **Sale chain:** departure → post-Aberdeen → clause → trigger → receipt on the
  former register and the shared profile; missing inputs name their reason.
- **Era lookup:** season, manager, honour and competition filters on `/history/`.
- **Deferred:** match game-state/streak context. No live or real-time updates.

## Phase 4b — Two doors and the rumour mill (live)

- `/matchday/` and `/recruitment/` hubs, grouped navigation, two-door home page
  and the news/rumour bridge.
- `reference/rumours.yaml`: curated, source-linked rumours with a status,
  editorial confidence, source types and a confirmed-transfer link.
- `/rumours/`: rumour board, opinions, advisory recruitment profile and fan
  signal.
- AFC Chat Rumour Mill first-page sampling: gazetteer name extraction,
  cross-reference labels and rule-based VADER sentiment; no raw posts published.
- Scouting overlay: advisory rumour profile; the data-driven fit stays primary.
- **Deferred:** community votes, polls and submissions are a separate project
  (`config/engagement.yaml`, `TODO(engagement)`, docs/rumours.md).

## Phase 4d — Cormack-era historical record (live)

- `/history/` index: era context, strategic pillars, staff timeline, honours
  cabinet, season table and coverage matrix.
- One typed review page per season from 2019-20; 2026-27 is in progress.
- Historical transfer windows from 2019-20: recent four audited, earlier
  windows curated partial.
- Style proxies from football-data.co.uk and a bounded historical lineup/
  roster backfill for selection, with explicit coverage states.
- Curation and source rules: [history.md](history.md).
- **Next for this layer:** add a full historical league table to each season
  page if the audience needs it; extend the curated staff register as roles are
  publicly documented.

## Phase 4e — Upcoming-matchday dashboard (live)

- `/matchday/` is the matchday front door: next fixture, both predicted XIs,
  form, home/away splits, opponent style and relative strength, the likely
  approach and the keys to the match.
- The old `/clubs/aberdeen/` dashboard is retired to a moved notice; every
  internal link points at `/matchday/` or the relevant deep page.
- Daily, bounded opponent refresh: recent fixtures, lineups and events for the
  next opponent only, cache-first with stale fallback.
- Predicted XIs are projections with confidence and 4–6 contenders, explicitly
  not team news. Possession is unknown and is not used.
- See [matchday.md](matchday.md).

## Phase 4f — Season overview (live)

- `/analysis/` is the bridge between the next matchday, the results/form record,
  the squad and scouting; `/matchday/` carries the six-game lookahead.
- The season overview shows next fixtures, official AFC team news, derived
  selection signals, measured aims and factual squad-decision lenses.
- Provider ratings are labelled and relative, never individual verdicts; no
  blame, invented availability, contract or fee claims.
- See [analysis.md](analysis.md) and [analysis-review.md](analysis-review.md).

## Phase 4g — Provenance, availability and needs (live)

- `/sources/` is a layer truth table; API-Football is primary for cups, lineups,
  player stats and the squad, while Football-Data remains primary for league
  results/stats until the strict migration gate passes. The current gate fails
  on fixture completeness and lower-tier team stats.
- A curated official AFC availability ledger is the special case for injuries;
  the provider `/injuries` snapshot is optional and currently unavailable for
  Scottish 2026. Out/suspended players are excluded from the predicted XI;
  doubtful players are downgraded; unknown stays unknown.
- `/recruitment/` carries a seven-family needs board (cover / replace /
  strengthen), `/analysis/` carries implications and `/scouting/` carries priority
  role profiles. No targets, fees or wages.
- See [provenance.md](provenance.md), [availability.md](availability.md) and
  [needs.md](needs.md).

## Phase 4j — Documentation book (live)

- `book.toml`, `docs/SUMMARY.md` and the local `theme/` turn the canonical
  Markdown into a local mdBook book.
- Two named palettes, Merkland (light) and Aurora (dark), plus Auto; the theme
  keeps the System 7 grammar and the club-red accent.
- The book is built locally with `mdbook build`; it is not copied into the Pages
  artifact and is not a route on the website.
- See [docs-book.md](docs-book.md).

## Phase 4k — Former players (live)

- `/former-players/` is a register of confirmed permanent and free departures
  from 2019-20, with filters and links to the standard scouting profile for each
  player. The scouting profile carries an additive Former Aberdeen player
  section; there is no separate former-player profile route.
- The Aberdeen record comes from the covered history; post-Aberdeen league
  seasons and transfer histories come from a bounded API-Football backfill.
- A sell-on watch detects subsequent moves and computes a receipt only when
  every required input is public.
- The development scorecard is descriptive; it is not a good-price or
  should-have-kept verdict.
- The rumour mill labels current squad, current non-official, former players and
  external targets, and excludes current/former players from the target profile.
- See [former-players.md](former-players.md).

## Phase 4l — Access, citation and trust layer (recommended)

From the [October 2026 UX persona audit](ux-audit-2026-10.md). These are
recommendations, not delivered features.

- **Site-wide search** over the published 565-entry index, with the 4,405-player
  scouting index as a separate lazy-loaded group. Fix the 42 club entries without
  destinations and the 6 dead `/analysis/#claim-*` links first.
- **Shareable citation kit** — URL state, stable permalinks and copy-with-basis.
  The copied text must carry basis, coverage, as-of and link, never a bare number.
- **Trust layer** — as-of freshness beside tables and a per-page provenance
  footer, using the existing manifest and provenance payloads.
- **Corrections/what-changed log** — expand the existing `/corrections/` route
  and log; date-ordered, evidence-linked, no "trending" ranking.
- **Sticky table headers and first column** on dense tables; additive CSS only.

No new data or metrics. Owner approval is required for `/search/` becoming a
contracted route and for any expanded correction schema.

## Phase 4m — Evidence navigation and comparison (recommended)

- Definitions and glossary sourced from the metric registry; no paraphrase and no
  hidden data.
- Unknowns register aggregating existing coverage and provenance gaps.
- Independent claim surface rehomed from the orphaned `themes` claims; fitba-owned
  and including unflattering claims. A club-controlled register is rejected.
- Guarded player comparison within the same league and role; no cross-league
  ranking or winner.
- Role-family depth chart, sale chain, match game-state context and Cormack-era
  context lookup, all descriptive and without verdicts.

R16 (full current-player multi-season output), R19/R20 (computed gaps or streaks)
need new payloads or registered metrics before they can be published.

## Phase 4n — Distribution and export (deferred)

- Printable evidence briefs and OG share cards with basis baked in.
- CSV/export and embed of visible rows only, after a licence review.
- Full current-player multi-season output, saved filters and reader shortlists
  (`localStorage` only).
- Fan discussion trends, private decision memos and audience-question indexes are
  not part of this roadmap; see the audit's rejected/deferred register.

## Phase 5 — Local rich-visual prototype

- Heat maps, xG visuals and the 2D event-reconstructed viewer designed against
  StatsBomb Open Data or local-only data.
- The prototype is not published; the method and design rationale are.
- Define the data spec for an event/tracking provider.

## Phase 6 — Enterprise evaluation

- Approach Stats Perform/Opta, Wyscout or SkillCorner with a written spec:
  competitions, fields, public vs internal display, duration and budget.
- Only sign when the audience and product justify it.
- Never publish unlicensed data or imply tracking.

## Decision gates

| Gate | Question | If no |
|---|---|---|
| Source gate | Does the licensed API cover the cups, group fixtures, early rounds and required fields? | Fall back to Sportmonks for cups; no scraping. |
| Public-display gate | Are the terms compatible with a non-commercial public site? | Do not publish that source. |
| Cup-table gate | Do computed group tables reconcile with official results? | Fix the model before publishing. |
| Depth gate | Does the same page serve a reader who wants the headline and one who wants the method? | Improve hierarchy, not evidence. |
| Enterprise gate | Is the product valuable enough to justify a data contract? | Keep the local prototype; do not buy. |

## Non-goals for this roadmap

- Betting odds or gambling advertising.
- A raw data dump or an API for third parties.
- Full tracking before a licensed contract.
- Player ratings as verdicts or blame narratives.
- A second, simplified site that withholds evidence from one audience.
