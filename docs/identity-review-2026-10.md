# Identity review: October 2026

**Status:** final review record. Not a second charter.
**Date:** 2026-10-22.
**Panel:** eight agents, review-only: seven lenses plus a synthesis/verifier.
**Inputs:** the owner's identity brief, the six main pages and About, the built
static export, `docs/product-strategy.md`, `docs/history.md`, the generated
history and transfer payloads, and the proposed page-contract guard.

## Method

The panel read the site, the generated record and the proposed guardrail
independently, then the synthesis resolved disagreements rather than averaging
them. Findings were checked against the generated payloads. The owner's brief was
treated as the identity anchor, but not as a source of measured facts: where the
brief and the record disagreed, the record won and the disagreement is recorded
below. The accepted changes were applied to `docs/identity.md`,
`docs/page-contracts.md`, the site copy and `web/contracts/surfaces.json`.

## Panel and lenses

| Lens | Question |
|---|---|
| Club-context analyst | Does the Cormack-era framing match the measured record, and where does it overreach? |
| Engaged-fan reader | Does the site respect a numerate Aberdeen fan, or talk down and withhold evidence? |
| Editorial independence | Is the site on the club's side without becoming a mouthpiece or a false both-sides machine? |
| Data provenance | Are measured, inferred, curated and unknown visible at the point of the number? |
| Design/UX, constrained | Does the hierarchy serve the evidence without deleting it? |
| Accessibility and semantics | Are headings, tables, disclosures and anchors part of the record? |
| Adversarial style-agent red team | How would a future "simplify the site" agent defeat the guardrail? |
| Synthesis/verifier | What is agreed, what is rejected, and what is deferred? |

## What the site already does well

- The data layer is strong: measured/inferred/curated/unknown fields exist
  throughout `web/lib/data.ts` and the generated payloads.
- The Cormack-era record is cautious and well sourced: one major honour, two
  Conference League campaigns, nine people in charge, 103 arrivals and 86
  departures.
- The transfer register is complete at 229 rows and separates confirmed,
  curated, modelled and undisclosed money.
- The themes and needs pages already separate a measured surface from a labelled
  read; the reverted phase-1 change did not need to remove them.
- The independent/non-commercial stance is already stated in the footer, About
  and methodology.

## Identity decisions

- The line is **"Aberdeen FC, without the noise."** The lede is: "An independent,
  data-driven record of Aberdeen FC — the numbers, the sources and the argument,
  without the hot takes."
- The primary reader is the engaged, literate, numerate Aberdeen fan. The club,
  press and critics are secondary readers of the same public record. There is no
  casual, median or "average" reader to design for.
- The site is independent and on the club's side: it wants Aberdeen to succeed,
  will not soften an uncomfortable fact, and is not the club's mouthpiece. It may
  reach a labelled conclusion; "not a verdict" means not a verdict on a named
  person, not no position.
- Every number carries its basis. A number in assessed prose must also appear in
  a measured table on the same page. History-relative superlatives require the
  comparison that establishes them.
- The organising question is player, manager or structure. The site separates the
  three levels and says which one the evidence supports.
- Density is the product. Method and caveats may be disclosed; data, tables,
  columns, sources, anchors, confidence and unknown states may not.

## Corrections to the brief

The panel checked the owner's framing against the generated record. These
corrections are binding on published copy:

1. **"Narrowly avoided the relegation playoff" is not supported.** The record
   shows 10th in 2021-22 on 41 points and 9th in 2025-26 on 40 points; 11th is
   the playoff place. The site now says "relegation worry" only as a labelled
   reading, and the charter requires the final points and the margin to 11th
   before any playoff-escape claim is published.
2. **"Some of the worst losses and winless streaks in the club's history" is a
   superlative without a comparison.** The record documents 6-0 defeats
   (Hibernian, Celtic, AEK Athens) and a winless away run in 2026. The site now
   states those measured facts and forbids "worst"/"longest" without a
   historical comparison table.
3. **"Nine manager spells" needs a defined rule.** Nine people took charge of at
   least one league match, including interim spells; there are 13 stints, and
   Derek McInnes's stint begins in 2013, before the era start. Copy says "nine
   people in charge, including interim spells"; the charter requires pre-era
   stints to be flagged.
4. **"Europe" is not an unqualified achievement.** The two campaigns were the
   2023-24 Conference League group stage (third of Group G) and the 2025-26
   Conference League league phase (35th of 36). The site names the competition
   and round whenever Europe is cited.
5. **"The model does not explain the turnover" is an attribution, not a
   measurement.** The record measures 103 arrivals and 86 departures; it does not
   fit or test the trading model. The site says "if a pattern is unexplained by
   the model, we say so" and labels attribution to the model, manager or players
   as a reading.
6. **The 41.7% unknown source market must travel with the market-edge claim.**
   43 of 103 arrivals have an unknown source market. Any market-mix or
   market-edge statement must carry the unknown share.

## What changed this round

- Home h1, lede, metadata, header, footer and About now express the identity.
- `docs/identity.md` is the canonical identity, voice and non-negotiable charter.
  `docs/product-strategy.md` defers identity and voice to it.
- `docs/page-contracts.md` and `web/contracts/surfaces.json` define the visible
  evidence for eleven routes: `/`, `/matchday/`, `/themes/`, `/recruitment/`,
  `/transfers/`, `/loans/`, `/history/`, `/squad/`, `/sources/`,
  `/methodology/` and `/about/`.
- The theme question now follows the declarative headline as secondary context;
  it no longer leads the card.
- The needs player table and the "Not considered" list are open by default.
- The corrections promise is now a published policy; a public corrections route
  is a tracked follow-up, not a claim.
- Dead `/scouting/#priority-*` links are emitted only for families that have a
  profile.
- The home standings requires the Form column and carries a "computed from
  league results" provenance line; the transfer register declares and checks its
  rendered card count.
- The transfer board has an h2 before the cards; the checker now rejects skipped
  heading levels.
- Themes carry a visible source indicator in addition to the basis, confidence
  and unknown indicators.
- `/history/` is now contracted: the scorecard, thesis, season table, staff and
  manager records, baseline, honours, read block and coverage table. The
  manager tile is "people in charge" with the stint count; the baseline is
  labelled a chosen comparison; the market-edge unknown share and the two
  Conference League campaigns are stated on the page.
- `/squad/` is now contracted: the summary, roster table with its full column
  set, role mix, coverage note and the measured/missing card. The page's
  "bridge" and "rumour mill" framing was replaced with the concrete squad
  record.
- `/sources/` and `/methodology/` are now contracted: the layer truth table,
  source registry, migration gate, excluded sources, and the method sections
  from definitions through policy. The provenance pages can no longer be
  emptied by a style pass.

## Guardrail design

- `scripts/check_web_contract.py` parses the built HTML and fails when a
  contracted marker, table column, value, indicator, anchor, link, identity
  string or heading rule is missing, hidden or downgraded.
- It runs in the `web` job of CI after `npm run build`, and in `deploy-pages`
  after the `/fitba` build and before the artifact upload. The deploy gate is the
  one that matters; CI and deploy both fail closed.
- `make web-contract-check` and `make check-all` run the same gate locally.
- The checker rejects word-count budgets in the manifest outright.
- `tests/test_web_contract_manifest.py` pins the required markers, columns,
  cardinalities and indicators independently of the manifest. Removing a
  contract requires editing that test too, and `.github/CODEOWNERS` puts the
  identity, manifest, checker and tests under owner review.
- `AGENTS.md` and `CLAUDE.md` make the rules binding for future agents; the PR
  template records the contract check.

## Adversarial red-team matrix

| Attempt | Result | Residual gap |
|---|---|---|
| Delete markers from the manifest and remove the DOM | Caught: pinned contract test fails; CODEOWNERS review | The test and manifest are editable by the same actor if branch protection is absent |
| Switch a data page to its empty state | Caught: `ci_states` requires `full`; the empty state has its own markers | A legitimate data outage still blocks deploy, by design |
| Keep headers but blank every cell | Caught: every contracted column must have at least one non-placeholder value | A single surviving value per column passes; full payload cross-check is deferred |
| Hide data in a closed `<details>` | Caught: closed disclosure with a table, marker or indicator fails | An unmarked table in a closed disclosure can still hide; deferred |
| Hide data with a bespoke CSS class | Not caught: the checker reads attributes and inline styles, not stylesheet rules | Add a computed-style/CSS scan in a later pass |
| Move register rows behind the default filter | Partly caught: the register declares its rendered count and requires at least 50 cards | 122 of 229 rows are still client-side; full payload cross-check is deferred |
| Reintroduce a question heading | Caught: `?` headings, the question-word regex, and an exact banned-heading list | A question phrased as a statement without a banned stem can pass; review still needed |
| Replace the home/About identity line | Caught: exact h1 and copy assertions | Other routes' h1 is not pinned to the identity line; deferred |
| Delete `/history/` tables or sources | Caught: the `/history/` contract checks the season, manager, baseline and coverage tables, honours and read block | An unmarked table in a closed disclosure can still hide; deferred |
| Edit the checker or its tests to pass | CODEOWNERS and the pinned test raise the cost | No mechanical owner signature; branch protection is required |
| Edit the contract docs to declare a surface optional | Code review catches the diff; the pinned test catches the marker removal | No mechanical owner approval gate beyond CODEOWNERS |
| Change metadata to a neutral aggregator line | Home and About are pinned; other routes are not | Route-level identity copy assertions are deferred |

## Deferred, with reasons

- **Player pages, `/scouting/`, `/competitions/`, `/scotland/` and `/news/`
  contracts.** The main data and provenance routes are now covered; these are
  the remaining routes.
- **Computed-style/CSS hiding scan.** The static checker cannot see a bespoke
  stylesheet rule; a Playwright/computed-style pass is the correct fix.
- **Full payload cross-check.** Compare rendered card/row/player counts with the
  generated JSON, rather than the current declared-count check.
- **Table captions and `scope` on headers.** No table currently has either; this
  is an accessibility debt, not a reason to remove data.
- **Per-evidence basis, theme.basis and fee-estimate method/source visible in the
  UI.** The data exists; the render layer still hides some of it.
- **Page-level source lists on `/themes/`, `/matchday/` and `/recruitment/`.**
  The payloads carry sources; the pages do not render them yet.
- **A public corrections route/log and submission channel.** The site now claims
  only a published policy.
- **Theme title rename.** "The leaky boat" and the mission question's
  "working, or just a leaky boat?" remain a later editorial pass.
- **The 2024-25 "five wins in 27" claim.** It needs a within-season form-split
  table or a non-numeric rewrite.
- **Baseline framing.** Done: the 2013-14 to 2018-19 window is labelled a chosen
  comparison, not a neutral norm.
- **Transfer id slug.** Replace the colon in `transfer-afc:...` before those
  anchors are contracted.
- **Mobile and source-link accessibility fixes.** The predicted-XI grid orphan
  and repeated source-link names are recorded.
- **Whether the fan question survives at all.** It is now secondary; the panel
  was split on removing it entirely.

## Verification

- Root build and `/fitba` build both pass.
- `uv run python scripts/check_web_contract.py --ci` reports 11 surfaces and 111
  contracted markers; the base-path check reports the same.
- The full Python suite passes: 233 tests, including the 30 checker/contract
  tests, plus all publication guards (`make check`).
- Deliberate-break tests:
  - removing `data-contract="home.standings"` fails with "missing required
    marker";
  - closing the needs player disclosure fails with "contracted data hidden";
  - an interrogative About heading failed the checker before it was renamed.
- `git diff --exit-code -- web/data/generated` is clean.
- No commit, push or deploy was made as part of this review.

## Sign-off

**Reviewed:** 2026-10-22.
**Identity line:** ratified by the owner's selection on 2026-10-22.
**Next review:** when the corrections route, the computed-style guard or the
next major UI change is added.
