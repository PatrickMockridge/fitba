# Documentation

**Aberdeen FC, without the noise.**

The documents in this directory are the source of truth for what fitba is, how
it works and what it will not claim. They are also rendered as a local mdBook
book in the repository (`mdbook build`, `mdbook serve`). The book is a view of
these files, not a second source of numbers.

Start with the specification; use the identity for voice, the product strategy
for scope, and the metrics and sources when you need to check a number.

## Reading paths

- **A supporter who wants the method:** [methods and data](#data-and-method),
  then the [scouting method](scouting-method.md) and
  [source list](sources.md).
- **An analyst or journalist checking a number:** [specification](specification.md),
  [metrics](metrics.md), [metric changes](metric-changes.md) and the
  [in-app metrics register](https://patrickmockridge.github.io/fitba/metrics/).
- **A contributor or coding agent:** [architecture](architecture.md),
  [page contracts](page-contracts.md), [documentation book](docs-book.md) and
  the repository [AGENTS.md](https://github.com/PatrickMockridge/fitba/blob/main/AGENTS.md).

## Start here

| Document | Read it for |
|---|---|
| [Specification](specification.md) | Intent, canonical audience, essential/conditional/non-essential, number governance and change control. Canonical for intent, audience and number semantics. |
| [Identity](identity.md) | The public line, reader, editorial stance, voice rules, non-negotiables and the Cormack-era analytical frame. Canonical for identity and voice. |
| [Metrics](metrics.md) | The metric registry, verification modes, audit artifact and metric-change process. Technical companion to the specification. |
| [Metric changes](metric-changes.md) | Append-only log of metric-definition and parameter changes, with value and audit impact. |
| [Page contracts](page-contracts.md) | The evidence each contracted route must keep visible, the marker convention and the contract-change process. Normative for the UI. |
| [Design foundation](design.md) | The System 7 grammar, the four themes, typography, colour roles, component rules and the design-change process. Canonical for the visual system. |

## Product and architecture

| Document | Read it for |
|---|---|
| [Product strategy](product-strategy.md) | Product scope, content pillars, roadmap and delivery staging. Defers identity and voice to `identity.md`. |
| [Roadmap](roadmap.md) | The staged path from licensed basics to local event/tracking prototypes and a later enterprise decision. |
| [Architecture](architecture.md) | How ingestion, cup data, publication, the web app and the docs book fit together. |
| [Documentation book](docs-book.md) | The mdBook source, Merkland/Aurora themes and build. |

## Matchday, results and history

| Document | Read it for |
|---|---|
| [Matchday dashboard](matchday.md) | The next fixture, both predicted XIs, form, venue splits, the three-way style lean, relative strength, data states and the bounded opponent refresh. |
| [Season overview](analysis.md) | The next fixtures, availability, season aims, squad decisions and the bridge to matchday, squad and scouting. |
| [Results and fixtures](fixtures.md) | Played and remaining Cormack-era fixtures, plus one page per played fixture with canonical ids, depth states, timeline, lineups, stats and the deterministic read. |
| [fxG](xg.md) | The experimental team-match expected-goals model, model and goals ranges, penalties, provider-xG gate and limitations. |
| [Match scoreboard](match-scoreboard.md) | The top-level score, goal and red-card widget, event semantics and the Aberdeen/opposition split. |
| [Competition formats](competition-formats.md) | League Cup and Scottish Cup structure, entry rules, group points, rounds and dates, with sources and the "top six" correction. |
| [The Cormack era](history.md) | Managers, backroom and board changes, honours, season reviews, historical transfers, style and selection from 2019-20, with coverage and editorial rules. |

## Squad and recruitment

| Document | Read it for |
|---|---|
| [Squad and player profiles](squad.md) | The roster, current-season stats, loan scoping, coverage states and the site-wide player-link policy. |
| [Player page specification](player-page-spec.md) | Normative panel contract, result document, repetition rules and the player-page guard. |
| [Player profile standard](player-profile-standard.md) | The normative shared standard for the two-figure profile, cohort and companion table. |
| [Roles and shape](roles.md) | Starting-XI role taxonomy, formation maps, starts/substitute minutes, kick-off shape, reported shape notes and coverage rules. |
| [Career roles](career-roles.md) | FM-style multi-position eligibility, primary/secondary/stretch tiers, career heat map, broad group/side filter and the historical backfill. |
| [Player data and provenance](player-data.md) | Preferred-foot source hierarchy, explicit-statement rules, conflict and unknown policy, Wikipedia last-resort conditions and the Sportmonks gate. |
| [Injuries and availability](availability.md) | The curated team-news ledger, provider snapshot policy, status taxonomy, staleness and predicted-XI confidence. |
| [Squad needs](needs.md) | The seven role families, measured depth, cover/replace/strengthen logic, market routes and roster caveats. |
| [Former players](former-players.md) | The confirmed departure register, Aberdeen and post-Aberdeen records, rival spells, sell-on watch and the descriptive development scorecard. |
| [Transfers and loans](transfers.md) | The confirmed-business register, four-window and out-of-window views, position provenance, completeness audit, verification statuses, fee and loan-term policy and known gaps. |
| [Rumour mill and fan signal](rumours.md) | The curated rumour register, status/confidence policy, AFC Chat reference use, affiliation, cross-reference labels, sentiment limits, the advisory profile and the deferred engagement project. |
| [Trading model](trading-model.md) | Aberdeen's buy-low/sell-high and youth-development context, and how the app represents it without pretending to know the club's internal models. |
| [Scouting method](scouting-method.md) | Position groups, archetypes, shrinkage, league-strength adjustment, the value index, U23/European priority, the team-context lens, reader-selectable lenses, advanced search filters and the coverage limits. |

## Data and method

| Document | Read it for |
|---|---|
| [Methodology](methodology.md) | Data definitions, coverage tiers, table and cup calculations, uncertainty and the event-reconstructed/tracking distinction. |
| [Data provenance](provenance.md) | The layer-by-layer source truth table, API-Football coverage, the league migration gate and manifest attribution. |
| [Sources](sources.md) | Every source, its licence/public-display position, coverage, gaps and last-checked date. |
| [Metric changes](metric-changes.md) | The append-only metric and parameter change log. |

## Records and context

| Document | Read it for |
|---|---|
| [Identity review, October 2026](identity-review-2026-10.md) | The seven-lens panel record: identity decisions, corrections to the brief, the red-team matrix and the deferred follow-ups. |
| [Season overview review](analysis-review.md) | The six-lens review and decision record behind the `/analysis/` season overview. |
| [2026-27 context diary](context/aberdeen-2026-27.md) | The qualitative rebuild and shape-instability context behind the role/shape work. Context only, never a data source. |

## Archive

These documents are retained for the record. They are not current guidance.

| Document | Why it is archived |
|---|---|
| [Case spec](case-spec.md) | Superseded for `/analysis/` by `analysis.md`; retained for the matchday evidence strip and the `themes/aberdeen.json` payload. |

## The documentation book

The book is built with mdBook 0.5.4 from these files. The source is the same
Markdown; `docs/SUMMARY.md` sets the chapter order. The book has two named
palettes, **Merkland** (light) and **Aurora** (dark), plus Auto. The theme
mapping and the build/check flow are in [Documentation book](docs-book.md).

```bash
mdbook build   # build book/
mdbook serve   # preview at http://localhost:3000
```

The book is a repository artifact. It is not a route on the fitba website and
is not copied into the Pages build. mdBook is a documentation build dependency;
it is not required to run the main site.

## Documentation rules

- Plain-language summary first, technical detail below.
- Separate **what we know**, **what we infer** and **what we do not know**.
- Every format or method claim carries a source and a last-reviewed date.
- No marketing claims and no pretending to be club insiders.
- Intent, audience, essentiality and number semantics are governed by
  [specification.md](specification.md). Voice and editorial stance are governed
  by [identity.md](identity.md). Product scope is governed by
  [product-strategy.md](product-strategy.md). Route visibility is governed by
  [page-contracts.md](page-contracts.md). Metric definitions are governed by
  `config/metrics.yaml` and [metrics.md](metrics.md).
- Do not use word-count budgets to justify removing evidence. Contracted data is
  visible by default; method and long caveats may be disclosed.
- Every published number has a registry entry, a home payload and an audit
  entry. Do not restate volatile counts in docs; link to the register or
  `/metrics/`.
- If a fact changes, update the document, the config and the in-app page in the
  same change. `scripts/check_docs.py` guards the links and the key format facts;
  `scripts/check_metrics.py` guards the registry and audit;
  `scripts/check_web_contract.py` guards the rendered routes.

## Licence

The code and documentation are licensed under the GNU Affero General Public
License v3.0 or later. See the repository
[LICENSE](https://github.com/PatrickMockridge/fitba/blob/main/LICENSE).
Third-party football data is not covered by that licence; see the repository
[DATA_LICENSE.md](https://github.com/PatrickMockridge/fitba/blob/main/DATA_LICENSE.md).
