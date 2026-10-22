# Roadmap

**Status:** staged plan. Last reviewed 2026-10-21.

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
| 4c. Squad and player profiles | **Live.** `/squad/`, one `/players/<id>/` page per player, loan tags, coverage states and site-wide player links. |
| 4d. Cormack-era historical record | **Live.** `/history/`, one season review per season, manager/staff timeline, honours, historical transfers, style and selection. |
| 4e. Upcoming-matchday dashboard | **Live.** `/matchday/`, both predicted XIs, form, venue splits, style lean and strength; `/clubs/aberdeen/` retired to a moved notice. |
| 4f. Medium and long-term themes | **Live.** `/themes/` and a matchday backdrop: role-family balance, wing-back trade-off, cover, attack-defence balance and the 20% Cormack-era mission context. |
| 4g. Provenance, availability and needs | **Live.** Layer truth table at `/sources/`, curated availability ledger in the predicted XI, and a squad-needs board on `/recruitment/` that feeds the scouting method. |
| 5. Fan-facing insight layer | **Next.** Trading analytics, scouting views and richer opposition context. |
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

## Phase 4 — Fan-facing insight layer (next)

- Trading-club dashboard: squad age/value, minutes by age, inferred transfer
  balance, sell-on candidates, contracts and loans.
- Opposition briefings using the same framework.
- Basic scouting board: position-aware percentiles, minutes reliability,
  league-strength adjustment, style fit, budget bands and coverage labels.
- Explainer cards, glossary and a clearer methodology layer.
- Progressive-disclosure components on every insight.

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

## Phase 4f — Medium and long-term themes (live)

- `/themes/` is the bridge between the matchday lookahead, squad, recruitment
  and history; `/matchday/` carries a compact “The bigger picture” strip.
- 80% current season: family balance, wing-back trade-off, defensive cover and
  the attack-defence balance. 20% Cormack-era mission: the documented
  trading-club pillars, turnover and young minutes.
- Provider ratings are one labelled, minutes-weighted family signal. No
  individual ratings as verdicts, no blame, no invented availability and no
  unmeasured channel claims.
- See [themes.md](themes.md).

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
  strengthen), `/themes/` carries implications and `/scouting/` carries priority
  role profiles. No targets, fees or wages.
- See [provenance.md](provenance.md), [availability.md](availability.md) and
  [needs.md](needs.md).

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
| Audience gate | Do casual fans and analysts use the same pages? | Simplify the presentation, not the evidence. |
| Enterprise gate | Is the product valuable enough to justify a data contract? | Keep the local prototype; do not buy. |

## Non-goals for this roadmap

- Betting odds or gambling advertising.
- A raw data dump or an API for third parties.
- Full tracking before a licensed contract.
- Player ratings as verdicts or blame narratives.
- A second, simplified site for casual fans.
