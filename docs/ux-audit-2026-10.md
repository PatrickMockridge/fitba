# UX persona audit: four readers, one mission

**Status:** audit and roadmap. **Date:** 2026-10-26.
**Owner-approved scope:** documentation only. No feature is implemented here.
**Not in scope:** user research, analytics, visual redesign, legal review, code,
contracts, generated data or metric changes.

## Verdict

fitba does not have a feature shortage. It has a **findability, citationality and
trust-at-the-point-of-use gap**.

The record is already unusually deep: 4,737 prerendered pages, a match page for
every played fixture, two standard player-profile routes, a 4,405-player scouting
search, former-player and sell-on records, a Cormack-era history, and a
per-source freshness and audit system. The audit found that much of this evidence
is hard to reach, hard to cite and hard to verify where it is read.

The strongest evidence is in the repository itself:

- a 565-entry site search index is published but has **no consumer**;
- **42 club entries** in that index have no destination;
- **6 search entries** point at `/analysis/#claim-*` anchors that no longer exist;
- the 4,405-player scouting index is a separate **2.0 MB** payload with no
  site-wide entry point;
- filters on the richest pages are **not shareable**;
- there is no citation, copy-with-basis or export affordance;
- freshness is visible globally, not beside the table being read;
- the public corrections log exists, but two mission documents still describe it
  as a future follow-up.

The cross-persona answer is therefore not "add more data". It is: make the same
evidence easier to find, understand, cite and trust.

**Top five recommended features**

1. **Site-wide search** over the existing index, with the scouting search as a
   separate lazy-loaded group.
2. **Shareable citation kit** — URL state, stable permalinks and copy-with-basis.
3. **Trust layer** — as-of freshness beside tables and a per-page provenance
   footer.
4. **Public what-changed/corrections log** built from the existing corrections
   route and metric changelog.
5. **Guarded player comparison** — same league and role, no winner.

Sticky table headers and a first column are the cheapest fast follower.

## Method and limits

Four simulated persona reviews were run read-only against the mission, contracts,
components and published payloads:

| Persona | Lens | Top three |
|---|---|---|
| Aberdeen FC representative | Composite communications/fan engagement with a secondary decision-support interest | Fact file/press desk; fan discussion digest; claim-check register |
| Super-fan | Season-ticket holder who wants depth, comparison and history | Player comparison; citation cards; sale chain |
| Phone-first / first-visit access lens | Supporter on a phone without data-specialist vocabulary | Site-wide search; inline definitions; share with basis |
| Podcaster/influencer | Creator needing defensible, citable material | On-air brief; basis-carrying share cards; what-changed finder |

Each persona produced user stories, the problem solved, the existing data that
could support it, static feasibility and mission risk. Requests were deduplicated
and screened through the six gates below.

**Limits.** These are simulated lenses, not user research. There is no analytics,
survey or representative sample. Rankings are judgements about mission fit,
evidence value, static feasibility and risk, not measured demand. The audit does
not claim a "silent majority" or speak for supporters it has not sampled.

## The audience test

The canonical primary reader is the **highly engaged, literate, numerate
Aberdeen fan** who knows the squad and the league and wants the evidence, the
sources and the uncertainty. The club, press, critics, Scottish football readers,
students, journalists and analysts read the same public record as secondary
readers. There is no separate simplified product.

`docs/identity.md` explicitly rejects designing for an imagined "average" or
"median" user. The audit therefore treats the "average fan" as a **phone-first /
first-visit access lens**, not an audience tier. The governing distinction is:

> Does the request remove friction to the same evidence, or does it remove
> evidence to fit an imagined reader?

**Accept as access:** search, inline definitions, sticky table headers,
citation/share, as-of freshness, reading-path links.

**Reject as subtraction:** a simple mode, hiding advanced columns by default,
"top three things" summaries, casual explainers that replace tables, or any
request justified by "average", "casual", "median", "simpler", "above the fold"
or a word count.

## Mission-fit gates

Every request must pass all six gates before it receives a verdict.

| Gate | Question | Failure examples |
|---|---|---|
| Evidence integrity | Does it preserve contracted data, sources, basis, coverage and unknown states? | Hiding tables, cherry-picking club facts, inventing a composite score |
| Independence | Does it avoid club control, paid influence, insider data or club-set framing? | Club-controlled claim register, private decision memo |
| No verdict | Does it avoid player/manager verdicts, blame, recommendations or "data says" certainty? | "Best XI", "good sale", "sign him", cross-league winner |
| Static and legal | Can it work with the static export, no backend/accounts/notifications/tracking, using licensed/public data? | Accounts, alerts, sentiment dashboards, raw API dumps |
| Audience integrity | Does it improve access to the same evidence rather than create a simplified tier? | "Casual mode", removing columns for phones |
| Maintenance and governance | Does it avoid new manual curation or new metrics without an owner and registry entry? | Daily snapshot archive, unpublished derived streak metric |

Verdicts:

- **Accept** — build as proposed.
- **Adapt** — keep the need, constrain the form to protect the mission.
- **Defer** — valid, but a dependency is not ready.
- **Reject** — mission drift, forbidden, or no defensible data source.

The audit does not use numeric scores. A score would imply a precision the
simulated method cannot support. Verdicts are reasoned, not measured.

## Repository evidence

| Observation | Source | Consequence |
|---|---|---|
| 565 search entries: 369 match, 76 former-player, 42 club, 34 player, 22 staff, 8 page, 8 history-season, 6 analysis | `web/data/generated/search-index.json` | Site-wide search is a UI gap, not a data gap. |
| 42 entries have no `href`; all are club entries | same | Search must not render dead results. Add destinations or suppress them. |
| 6 entries point to `/analysis/#claim-*`, but `/analysis/` no longer renders claim cards | search index; `web/app/analysis/page.tsx`; `docs/analysis.md` | Live dead links. The claim payload exists but is orphaned; rehome it or remove the entries. |
| 4,415 scouting rows, 4,405 unique players, 34 leagues, 2,091,663 bytes | `web/data/generated/scouting/search-index.json` | Site-wide search must lazy-load scouting results, not ship 2 MB on first paint. |
| 0 current-squad player IDs appear in the scouting index | `squad/aberdeen.json`; scouting search index | Comparison is scouted-vs-scouted only unless a new squad/scout alignment is built. |
| Public corrections route and 9-entry dated log exist | `web/app/corrections/page.tsx`; `web/data/corrections.json` | The request is an expansion, not a new product. |
| Freshness is global, not beside tables | `FreshnessBadge.tsx`; `app/layout.tsx`; manifest | As-of is a presentation gap using existing timestamps. |
| Claim payload has 6 claims with evidence, status and change-mind | `themes/aberdeen.json`; `CaseClaimCard.tsx` | An independent claim surface can reuse it; a club-controlled register cannot. |
| `identity.md` and `product-strategy.md` still call the corrections route a future follow-up | `docs/identity.md`; `docs/product-strategy.md` | Documentation drift; factual one-line fix. |

## Persona briefs

### Aberdeen FC representative

**Role:** secondary reader, not a client. Communications and fan engagement, with
a secondary interest in decision support and brand reputation. The useful version
of this lens asks how the club can read the same record more accurately, not how
the record can be made friendlier to the club.

**Jobs to be done:** brief media and colleagues with one citable source;
understand what supporters are discussing; check a circulating claim; trust that
a number has not changed silently; see where the public record is genuinely
unknown.

**Top three**

1. **Fact file / press desk** — a citable per-topic register with anchors,
   sources, basis and as-of dates, including the unflattering facts.
2. **Fan discussion digest** — dated, sampled, anonymised trend of what
   supporters are discussing.
3. **Claim-check register** — circulating claims matched to measured evidence.

**Other requests:** corrections/changelog feed; unknowns register;
decision-questions memo; printable snapshot; per-page provenance footer.

**Verdicts:** the fact file is **Adapt** (a view of the same record, not a press
office); the fan digest is **Reject** (sampled forum data cannot support a
sentiment-trend product, and the club-monitoring framing is wrong); the claim
register is **Adapt** as an independent, owner-edited surface, or **Defer** if
editorial capacity is absent; corrections/changelog and provenance are **Accept**;
unknowns is **Accept**; the decision memo is **Defer**; the snapshot is **Adapt**.

**Must not get:** club control, private delivery, selective omission, a
"positive story" filter, or a dashboard that treats supporter sentiment as a
metric to manage.

### Super-fan

**Role:** primary-adjacent reader. Season-ticket holder, watches every match,
knows the squad, wants depth, comparison and history.

**Jobs to be done:** compare players fairly; follow a player or season over time;
understand the trading model sale by sale; cite evidence in an argument; prepare
for and review a match.

**Top three**

1. **Head-to-head player comparison** — same league and role basis, no winner.
2. **Evidence citation/permalink cards** — fact, basis, coverage, source and date.
3. **Sale chain / what happened next** — departure, fee basis, successor and
   measured output, with the counterfactual left open.

**Other requests:** role-family depth chart; multi-season player history; match
game-state context; scouting shortlist/saved filters/CSV; season form and cut-off
tracker.

**Verdicts:** comparison **Adapt** (same league/role only); citation **Accept**;
sale chain **Adapt** (no good/bad sale verdict); depth chart **Accept** (measured
minutes/role/availability, not "quality drop-off"); multi-season **Adapt**
(former-player timeline is supported; full current-player per-season output needs
a new payload); game-state **Adapt** (neutral state facts, no player gloss);
shortlist/CSV **Adapt** (localStorage, provenance columns); cut-off tracker
**Adapt** (descriptive margins first; any computed gap needs a registry entry).

**Must not get:** cross-league rankings, winner/loser verdicts, accounts, a
"best XI" recommendation, or a private scouting target list.

### Phone-first / first-visit access lens

**Role:** not an audience tier. A supporter on a phone, without the vocabulary of
the analysis tier, looking for a fact and wanting to pass it on without losing
the caveat.

**Jobs to be done:** find the right player, match or page; understand a term in
place; read a dense table on a phone; know whether the data is current; share a
fact with its basis.

**Top three**

1. **Site-wide search** — type a player, match or page and land on the existing
   profile/page, never a new mini-profile.
2. **Inline term definitions** — registered definitions beside unfamiliar terms.
3. **Share/copy a fact with its basis** — basis, coverage, as-of and link travel
   with the fact.

**Other requests:** sticky table headers/first column; first-visit reading path;
visible as-of freshness; public what-changed log.

**Verdicts:** search **Accept**; definitions **Accept**; share **Accept**; sticky
tables **Accept**; reading path **Adapt** (links and order, not a simplified
digest); freshness **Accept**; changelog **Accept**.

**Must not get:** a simplified mode, hidden columns, a separate casual content
tier, or a definition that paraphrases away the registered basis.

### Podcaster/influencer

**Role:** secondary distributor. Produces Aberdeen analysis for an audience and
needs defensible, citable material without turning fitba into a content farm.

**Jobs to be done:** find a distinctive, evidence-backed story; read a number
with its basis and uncertainty on air; create shareable material that carries
the caveat; compare within a fair cohort; review a match against what was said
beforehand.

**Top three**

1. **On-air brief** — a per-page citation and uncertainty strip.
2. **Basis-carrying share cards/OG images** — basis, source, sample and link in
   the image.
3. **What-changed story finder** — dated, evidence-linked changelog, not a
   "biggest movers" feed.

**Other requests:** read-a-number explainer; guarded comparison; match prep/review
pack; era lookup; export/embed; audience-question index.

**Verdicts:** on-air brief **Accept** (overlaps citation); share cards **Defer**
(build-time image work; basis must be baked in); what-changed **Accept**;
read-a-number **Accept** (overlaps definitions); comparison **Adapt**; match
prep/review **Adapt** (respect the guarded summary and descriptive-only fxG);
era lookup **Accept**; export/embed **Defer** (licence review); audience-question
index **Reject** (no audience data; requires tracking).

**Must not get:** hot-take cards, decontextualised clips, unsourced numbers,
engagement-ranked "biggest movers", cross-league rankings, or audience tracking.

## Cross-persona convergence

The strongest signal is the overlap:

1. **Findability** — site-wide search and a usable player/match index.
2. **Comprehension** — inline definitions, glossary and read-a-number explainer.
3. **Citationality** — copy/share with basis, on-air brief, permalink cards.
4. **Trust at the point of use** — visible as-of freshness and provenance.
5. **What changed** — a dated corrections/changelog surface.

Every persona independently asked for at least three of these five. None asked
for a new data source.

## Request inventory

| ID | Request | Sources | Existing payload/component | New data | Verdict | Horizon |
|---|---|---|---|---|---|---|
| R01 | Site-wide search across pages, matches, players, clubs, staff, history; separate scouting group | Access lens, podcaster, super-fan | `search-index.json`; `scouting/search-index.json`; `getSearchIndex()`; scouting filters | No; fix hrefs, lazy-load scouting | Accept | Now |
| R02 | Inline definitions and consolidated glossary | Access lens, podcaster | `metrics/registry.json`; `methodology.md`; `StatTile`/`Panel` | No numbers; editorial prose | Accept | Next |
| R03 | Sticky table headers/first column | Access lens | `.table-wrap`; semantic tables | No | Accept | Now |
| R04 | First-visit reading path | Access lens | `/about/`, home doors, `SiteNav` | No | Adapt | Next |
| R05 | Shareable URL state, copy fact with basis, stable permalink | Super-fan, access lens, podcaster | Client filter state; basis/confidence badges; anchors | No | Accept | Now |
| R06 | Visible as-of freshness beside tables | Access lens, club | `FreshnessBadge`; manifest; `source_snapshots` | No | Accept | Now |
| R07 | Per-page provenance footer | Club, podcaster | `provenance.json`; footer; source snapshots | No | Accept | Now |
| R08 | Public what-changed/corrections log | Access lens, club, podcaster | `/corrections/`; `corrections.json`; `metric-changes.md` | No; expanded schema | Accept | Now |
| R09 | Unknowns register | Club | `coverage.json`; provenance; page coverage blocks | No | Accept | Next |
| R10 | Independent claim-check surface | Club, podcaster | `themes/aberdeen.json`; `CaseClaimCard` | No | Adapt | Next |
| R11 | Export/embed with provenance | Podcaster, super-fan | Visible tables; licence review | No, but licence review | Defer | Later |
| R12 | Printable evidence brief/snapshot | Club, podcaster | Matchday/match/analysis/history payloads | No for print; archive would duplicate | Adapt | Later |
| R13 | Basis-carrying OG/share cards | Podcaster | Route metadata; new image generation | No | Defer | Later |
| R14 | Head-to-head player comparison, same league/role | Super-fan, podcaster | Scouting rows; `ScoutingProfile`; `PlayerRose`; filters | No for scouted-vs-scouted | Adapt | Next |
| R15 | Role-family depth chart | Super-fan | `squad` by role; analysis lenses; needs | No | Accept | Next |
| R16 | Player multi-season history/timeline | Super-fan | Former-player seasons; current `career_role.seasons`; history season rows | Full current output is new | Adapt | Next–Later |
| R17 | Sale chain / what happened next | Super-fan | Former players; sell-on watch; transfer chain | No | Accept | Next |
| R18 | Reader shortlist, saved filters, CSV | Super-fan | Scouting filters; localStorage | No | Adapt | Later |
| R19 | Season form/cut-off tracker | Super-fan | Tables/cutoffs; form; fixtures | Computed gap is new | Adapt | Later |
| R20 | Match game-state/streak context | Super-fan | Match timeline `score_after`; form before/after | Streak metric is new | Adapt | Next |
| R21 | Cormack-era context lookup | Podcaster | History payload; comparison table | No | Accept | Next |
| R22 | Fan discussion digest/trends | Club | Forum sample only; no history | No, but sample cannot support trend | Reject | — |
| R23 | Decision-questions memo | Club | Analysis/needs/history reads | No; editorial | Defer | Later |
| R24 | Sourced audience-question index | Podcaster | No source; needs audience tracking | Yes | Reject | — |

## Strongest rejects and defers

| Variant | Why it fails or waits | What would change the verdict |
|---|---|---|
| Accounts, notifications, alerts | No backend or persistent identity; privacy and maintenance cost; not evidence. | Nothing in this product scope. |
| Analytics or engagement dashboards | `product-strategy.md` says engagement is not a success metric; tracking creates surveillance and drift. | Nothing; use manual comprehension and trust checks. |
| Club-controlled claim register | The club is a reader, not an editor. Independence requires fitba-owned status and evidence. | Only the independent R10 adaptation, with owner editorial sign-off. |
| Fan-sentiment digest or trend product | The sample is first-page, small and rule-based; a trend implies representativeness and engagement optimisation. | A one-off, hand-curated, source-linked editorial piece; never an automated product. |
| Cross-league comparison or ranking | Scouting percentiles are within-league and within-role; the contract forbids cross-league ranking. | No ranking. A cross-league note may cite the published alignment with its caveat, but no winner. |
| Hot-take or verdict share cards | Identity rejects verdicts, blame and "data says" certainty. | Bounded, basis-carrying OG cards only. |
| Simplified or "average fan" mode | Identity rejects an imagined median user and evidence removal. | Access-only features reframed as navigation/citation. |
| Raw data dump, API or bulk export | Roadmap non-goal; licence risk; support burden. | Visible-row CSV with provenance, after licence review. |
| Per-date snapshot archive | Duplicates data, creates stale copies and ongoing storage/curation. | Print stylesheet plus dated as-of and stable URL. |
| Private decision memo | Club-facing advisory product; risks club influence and unsourced recommendations. | Public, owner-edited "questions the evidence raises" section only. |
| Full current-player multi-season stats | The payload does not contain per-season output; React must not invent it. | Add a registered per-season player payload. |
| Computed cut-off gap, projection or streak metric | New published number; needs registry, verification, audit and change log. | Add a `config/metrics.yaml` entry, verification and owner approval. |
| Audience-question index | Requires audience collection or tracking; conflicts with no-analytics constraint. | A manually curated, owner-supplied index only. |

## Roadmap

### Now — accepted

| ID | Feature | Why now | Dependency/risk |
|---|---|---|---|
| R01 | Site-wide search | Largest discoverability gap; 565-entry index already published | Fix 42 missing hrefs and 6 dead claim links; lazy-load scouting; flat, unranked results |
| R03 | Sticky table headers/first column | Cheapest mobile legibility win; semantic tables already exist | CSS only; never delete columns to fit |
| R05 | Shareable citation kit | Cross-persona and identity-critical; makes the record citable | One URL-state/citation convention; copied text must carry basis, coverage, as-of |
| R06 | As-of freshness beside tables | Trust at the point of use; timestamps exist | Distinguish dataset vs source freshness; show stale/unknown |
| R07 | Per-page provenance footer | Core trust; provenance payload exists | Must not replace page sources or add unregistered counts |
| R08 | Corrections/what-changed log | Route and log already exist; trust infrastructure | Expand schema; date-ordered, no "trending" |

### Next — accepted or adapted

| ID | Feature | Verdict | Adaptation |
|---|---|---|---|
| R02 | Definitions/glossary | Accept | Registered definitions, not paraphrase |
| R09 | Unknowns register | Accept | Record gaps, not club requests |
| R10 | Independent claim surface | Adapt | Fitba-owned, includes unflattering claims; owner editorial capacity |
| R14 | Guarded player comparison | Adapt | Same league/role; cohort n/minutes visible; no winner; scouted-vs-scouted only |
| R15 | Role-family depth chart | Accept | Measured minutes/role/availability; no "quality drop-off" |
| R17 | Sale chain | Accept | Departure/successor/output with fee basis; no good/bad sale |
| R20 | Match game-state context | Adapt | Neutral leading/level/trailing; no derived streak metric yet |
| R21 | Era context lookup | Accept | Superlatives require the comparison table and margin |

### Later — adapted or deferred

| ID | Feature | Verdict | Condition |
|---|---|---|---|
| R11 | Export/embed with provenance | Defer | Licence review; visible rows only |
| R12 | Printable brief/snapshot | Adapt | Print stylesheet and dated as-of; no snapshot archive |
| R13 | OG/share cards | Defer | Build-time image work; basis in image |
| R16 | Full current-player multi-season output | Adapt | New registered per-season payload for current players |
| R18 | Shortlist/saved filters/CSV | Adapt | localStorage only; provenance columns; not a community feature |
| R19 | Cut-off tracker | Adapt | Descriptive margins first; register any computed gap |
| R23 | Public decision questions | Defer | Owner editorial capacity; no private delivery |

### Rejected

- Accounts, cross-device sync, live notifications and personalised feeds.
- Comments, votes, polls and community submissions.
- Social monitoring or feeds; X/YouTube/Instagram ingestion.
- Betting and odds.
- Club-controlled PR, endorsement, sponsorship or editorial influence.
- Fan-sentiment scoring or trend products.
- Hot-take cards, decontextualised clips and engagement-ranked "biggest movers".
- Cross-league player rankings or verdicts.
- Predictive points or outcomes.
- A third player-profile route.

## Reuse map and no-new-data ledger

| Need | Existing payloads | Existing components |
|---|---|---|
| Search and navigation | `search-index.json`; `scouting/search-index.json` | `ScoutingGlobalSearch`, `ScoutingLensSelector`, `SiteNav` |
| Player evidence | `players/<id>.json`; `squad/aberdeen.json`; `scouting/search-index.json`; `former-players/seasons.json` | `PlayerRose`, `ScoutingProfile`, `ScoutingSquadTable`, `CareerRoleHeatmap` |
| Match evidence | `matches/<id>.json`; `fixtures/index.json`; `matchday/upcoming.json` | `MatchTimeline`, `MatchSummary`, `MatchScoreboard`, `FormGuide` |
| Season/table evidence | `tables/*.json`; `analysis/summary.json`; `history/seasons/<season>.json` | `LeagueTable`, `FormGuide`, `ManagerRecordTable`, `HonoursCabinet` |
| Trust evidence | `manifest.json`; `provenance.json`; `coverage.json`; `metrics/registry.json`; `corrections.json` | `FreshnessBadge`, provenance sections, `/sources/`, `/metrics/` |
| Claims evidence | `themes/aberdeen.json` | `CaseClaimCard`, `CaseEvidenceTable`, `CaseBenchmark` |
| Forum reference | `forum/afc_chat.json` | `ForumSignalPanel` |

**No new data is required for:** R01–R10, R12, R14 (scouted-vs-scouted), R15,
R17, R19 (descriptive only), R20 (timeline only) and R21.

**New data is required for:** full current-player multi-season output (R16),
computed cut-off gaps or streak metrics (R19/R20), and audience questions (R24).
R02 needs editorial prose, not data. R11 needs a licence review.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Identity drift through "access" features | The six gates; keep the phone-first lens explicitly non-audience; no simplified tier |
| Club capture | Club remains a secondary reader; no club control, private delivery or selective claims |
| Comparison becomes a verdict | Same league/role; cohort size and minutes visible; no winner; no cross-league ranking |
| Share artefacts become hot takes | Basis, coverage, as-of and link travel with the fact or image |
| Search surfaces dead or duplicated content | Fix the 42 missing hrefs and 6 dead claim anchors; one flat index; profile links only |
| Performance | Keep the 565-entry index initial; lazy-load the 2 MB scouting index; no client sums |
| Accessibility | Sticky tables preserve captions, `scope`, keyboard access; definitions do not hide numbers |
| Licence | Defer CSV/embed until review; publish only derived payloads |
| Metric governance | Any computed cut-off/streak/delta needs a registry entry, verification, audit and changelog |
| Maintenance | Prefer generated/static surfaces; no daily snapshot archive; owner editorial capacity for claims |

## Documentation and contract changes

Documentation only in this change:

- add this audit and link it from `docs/SUMMARY.md` and `scripts/check_docs.py`;
- update `docs/roadmap.md` with the recommended phases;
- add a pointer in `docs/product-strategy.md`;
- remove the stale statement that the public corrections route is a future
  follow-up from `docs/identity.md` and `docs/product-strategy.md`.

No code, generated data, page contracts, `web/contracts/surfaces.json`, metric
registry or metric changelog changes. Contract additions for `/search/` or
`/claims/`, if approved later, belong to the implementation phase.

## Verification

```bash
uv run python scripts/check_docs.py
mdbook build
git diff --stat
```

Checklist:

- every persona request has an ID and a verdict with a reason;
- every persona's top three has an explicit verdict;
- no accepted item removes or hides evidence, creates a median-user tier or a
  third player-profile path;
- no new unregistered number is proposed;
- no code, generated data, metrics or contracts change;
- the report states its limits: simulated personas, no analytics or user
  research, rankings are judgements not demand measurements.

## Appendix: search-index composition

| Type | Entries |
|---|---:|
| Match | 369 |
| Former player | 76 |
| Club | 42 |
| Player | 34 |
| Staff | 22 |
| Page | 8 |
| History season | 8 |
| Analysis claim | 6 |
| **Total** | **565** |

## Appendix: owner decisions for any implementation

1. Approve `/search/` and `/claims/` as new public routes and contract additions.
2. Choose the definitions source: `config/metrics.yaml` descriptions or a curated
   `reference/definitions.yaml`.
3. Approve the expanded corrections-log schema and whether it remains JSON or
   becomes source-first YAML.
4. Approve editorial ownership of the independent claim surface.
5. Decide whether any cut-off gap, streak or comparison delta is a registered
   metric or stays descriptive.
6. Approve a licence review for CSV export.
