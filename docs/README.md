# Documentation

The documents below are the source of truth for what fitba is, how it works and
what it will not claim. Start with the specification; use the identity for voice,
the product strategy for scope, and the metrics and sources when you need to
check a number.

| Document | Read it for |
|---|---|
| [Specification](specification.md) | Intent, canonical audience, essential/conditional/non-essential, number governance and change control. Canonical for intent, audience and number semantics. |
| [Metrics](metrics.md) | The metric registry, verification modes, audit artifact and metric-change process. Technical companion to the specification. |
| [Metric changes](metric-changes.md) | Append-only log of metric-definition and parameter changes, with value and audit impact. |
| [Identity](identity.md) | The public line, reader, editorial stance, voice rules, non-negotiables and the Cormack-era analytical frame. Canonical for identity and voice. |
| [Page contracts](page-contracts.md) | The evidence each contracted route must keep visible, the marker convention and the contract-change process. Normative for the UI. |
| [Design foundation](design.md) | The System 7 grammar, the four themes, typography, colour roles, component rules and the design-change process. Canonical for the visual system. |
| [Identity review, October 2026](identity-review-2026-10.md) | The seven-lens panel record: identity decisions, corrections to the brief, the red-team matrix and the deferred follow-ups. |
| [Product strategy](product-strategy.md) | Product scope, content pillars, roadmap and delivery staging. Defers identity and voice to `identity.md`. |
| [Matchday dashboard](matchday.md) | The next fixture, both predicted XIs, form, venue splits, the three-way style lean, relative strength, data states and the bounded opponent refresh. |
| [Season overview](analysis.md) | The next fixtures, availability, season aims, squad decisions and the bridge to matchday, squad and scouting. |
| [Match record](fixtures.md) | One page per played Cormack-era fixture: canonical ids, depth states, timeline, lineups, stats and the deterministic read. |
| [fxG](xg.md) | The experimental shot-on-target expected-goals model, interval, provider-xG evaluation gate and limitations. |
| [Match scoreboard](match-scoreboard.md) | The top-level score, goal and red-card widget, event semantics and the Aberdeen/opposition split. |
| [Data provenance](provenance.md) | The layer-by-layer source truth table, API-Football coverage, the league migration gate and manifest attribution. |
| [Injuries and availability](availability.md) | The curated team-news ledger, provider snapshot policy, status taxonomy, staleness and predicted-XI confidence. |
| [Squad needs](needs.md) | The seven role families, measured depth, cover/replace/strengthen logic, market routes and roster caveats. |
| [Squad and player profiles](squad.md) | The roster, current-season stats, loan scoping, coverage states and the site-wide player-link policy. |
| [Player page specification](player-page-spec.md) | Normative panel contract, result document, repetition rules and the player-page guard. |
| [Roles and shape](roles.md) | Starting-XI role taxonomy, formation maps, starts/substitute minutes, kick-off shape, reported shape notes and coverage rules. |
| [Career roles](career-roles.md) | FM-style multi-position eligibility, primary/secondary/stretch tiers, career heat map, broad group/side filter and the historical backfill. |
| [Player data and provenance](player-data.md) | Preferred-foot source hierarchy, explicit-statement rules, conflict and unknown policy, Wikipedia last-resort conditions and the Sportmonks gate. Side is derived from role, not from this pipeline. |
| [2026-27 context diary](context/aberdeen-2026-27.md) | The qualitative rebuild and shape-instability context behind the role/shape work. Context only, never a data source. |
| [Transfers and loans](transfers.md) | The confirmed-business register, four-window and out-of-window views, position provenance, seniority-based completeness audit, verification statuses, fee and loan-term policy and known gaps. |
| [Rumour mill and fan signal](rumours.md) | The curated rumour register, status/confidence policy, AFC Chat reference use, cross-reference labels, sentiment limits, the advisory profile and the deferred engagement project. |
| [Trading model](trading-model.md) | Aberdeen's buy-low/sell-high and youth-development context, and how the app represents it without pretending to know the club's internal models. |
| [The Cormack era](history.md) | Managers, backroom and board changes, honours, season reviews, historical transfers, style and selection from 2019-20, with coverage and editorial rules. |
| [Competition formats](competition-formats.md) | League Cup and Scottish Cup structure, entry rules, group points, rounds and dates, with sources and the "top six" correction. |
| [Methodology](methodology.md) | Data definitions, coverage tiers, table and cup calculations, uncertainty and the event-reconstructed/tracking distinction. |
| [Scouting method](scouting-method.md) | Position groups, features, shrinkage, league-strength adjustment, fit score and budget bands. |
| [Sources](sources.md) | Every source, its licence/public-display position, coverage, gaps and last-checked date. |
| [Architecture](architecture.md) | How ingestion, cup data, publication and the web app fit together. |
| [Roadmap](roadmap.md) | The staged path from licensed basics to local event/tracking prototypes and a later enterprise decision. |

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
License v3.0 or later. See [../LICENSE](../LICENSE). Third-party football data
is not covered by that licence; see [../DATA_LICENSE.md](../DATA_LICENSE.md).
