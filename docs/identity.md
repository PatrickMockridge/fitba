# Identity: fitba

**Status:** canonical identity, voice and page-contract charter. Version 1.0.
**Last reviewed:** 2026-10-22.
**Precedence:** identity, audience and voice are governed here. Product scope and
roadmap stay in [product-strategy.md](product-strategy.md). The route contracts
are normative in [page-contracts.md](page-contracts.md); player-page specifics
remain normative in [player-page-spec.md](player-page-spec.md).

## The line

> Aberdeen FC, without the noise.

An independent, data-driven record of Aberdeen FC — the numbers, the sources and
the argument, without the hot takes.

## What fitba is

fitba is a data-driven Aberdeen FC site for supporters who already know the club
and want to see the evidence for themselves. It is also an independent public
record: the same evidence is available to supporters, the club, the press and
critics. It does not claim insider knowledge, and it does not ask to be trusted
on authority. It shows the numbers, the sources and the uncertainty.

The site has an interpretation. It is not a wire service. The data is the
evidence; the read is fitba's own, labelled as a read. Bias is not the presence
of a view; it is a view that survives contrary evidence. Every read names its
basis and links to the evidence that could overturn it.

## What fitba is not

- Not a club mouthpiece, and not an insider account.
- Not a hot-take blog, a transfer-gossip feed or a betting product.
- Not a simplified explainer for an imagined casual reader.
- Not a doom merchant: the record includes the cup, the two Conference League
  campaigns and the sales.
- Not a happy-clapper: the record includes the heavy defeats, the 2026 winless
  away run and the league positions.
- Not a both-sides machine that treats a measured fact and a rumour as equal.

## Who it is for

The primary reader is a highly engaged, literate, numerate Aberdeen fan. They
know the squad, the league and the arguments. They may not be a statistician,
but they want the numbers, the sources and the uncertainty, and they can tell
when evidence is being removed to make a page feel lighter.

The club, the press, critics and Scottish football readers are secondary readers
of the same public record. They are not a reason to simplify the primary reader's
evidence.

**There is no median user to invent.** Do not design for a hypothetical casual
fan, an "average" reader or a persona assembled from engagement data. Design for
the reader described above, and make the page navigable for everyone else.

## Editorial stance: on the club's side, not in its pocket

We want Aberdeen to succeed. That is not the same as defending the club. Being
on the club's side means taking its problems seriously enough to measure them:
not softening bad numbers, not turning every setback into a morality play, and
not treating a bad result as proof that a player or a manager is the whole
problem.

Criticism is aimed at decisions and structures, with evidence. No abuse, no
blame narratives, no invented wages or fees, no claim to know the boardroom's
private intent. The club is not a villain, and neither are its supporters.

fitba is independent and non-commercial. No betting advertising, no paid club
influence, no player abuse. Corrections are part of the product; the public
corrections route is a tracked follow-up, and until it exists the methodology and
sources pages carry the correction policy.

## The Cormack era: player, manager, structure

The analytical frame is the Cormack era, from Dave Cormack's chairmanship on 16
December 2019. At the 2026-10-22 publish the generated record covers seven
seasons, nine people in charge of at least one league match (including interim
spells; 13 stints), a best finish of third, a worst finish of tenth, one major
honour (the Scottish Cup), 103 arrivals and 86 departures
(`web/data/generated/history/aberdeen.json`).

The record contains a Scottish Cup, two Conference League campaigns (2023-24
group stage, third of Group G; 2025-26 league phase, 35th of 36), heavy defeats
including 6-0 losses, a winless away run in 2026, and significant player sales.
This is context, not an audited boardroom account.

The owner's framing of the era includes relegation worry. The measured record
shows finishes of 10th in 2021-22 (41 points) and 9th in 2025-26 (40 points),
with 11th the playoff place. Do not publish "narrowly avoided the playoff"
without the final points and the margin to 11th, or the date the club was in the
zone. Do not publish a history-relative superlative ("worst", "longest") without
the comparison table that establishes it; otherwise state the scoreline, streak
length, competition and date. Name the competition and round whenever Europe is
cited.

The era is best read as a trade-off, not a verdict. The site's job is to
separate three levels before reaching a conclusion:

1. **Player:** role, minutes, output, availability and sample size.
2. **Manager:** selection, shape, rotation and the use of the squad.
3. **Structure:** recruitment, trading model, squad turnover, wage and budget
   constraints, and the decisions above the manager.

If a pattern is unexplained by the model, the site says so; it does not fill the
gap with a story. Attribution to the model, the manager or the players is a
labelled reading, not a measured conclusion. Do not promote a player-level
explanation, a manager-level explanation or a structural explanation without
naming the level and showing the evidence.

## Voice rules

- **Declarative headings.** A section heading names its subject. A contracted
  H1, H2 or H3 never asks the reader a question.
- **Specific and dated.** Numbers carry units, scope, sample size and basis.
  Avoid "a lot", "huge" and "clearly" where a number exists.
- **Measured, inferred, curated, unknown** are visible words, not hidden
  metadata.
- **Plain language, not simplified evidence.** No dumbing down by subtraction.
  No "TL;DR", no "simply", no "obviously", no "fans will".
- **Challenge the argument, not the person.** No hype, doom, exclamation marks
  or emoji. No second-person rhetorical questions.
- **British English, sentence case.** "We" is the site, never the club.
- **"Without the noise" is a standard, not a slogan.** Do not repeat it on every
  page. The work is the proof.

A genuine question may appear in editorial prose when the section answers it.
It does not become the heading.

## Data principles

- The same framework applies to Aberdeen, opponents and scouted players.
- Never invent fees, wages, valuations or internal knowledge.
- Source links, coverage labels, confidence and unknown states stay visible.
- No unlicensed raw data, no betting odds, no raw forum posts.
- Distinguish measured, inferred, curated and unknown. A modelled estimate is
  labelled as one.
- Corrections and last-reviewed dates are part of the product.
- Do not use engagement as an excuse for certainty.

## Presentation principles

- **Density is the product.** The reader came for the data. A page that is
  lighter because evidence was removed is a worse page, not a cleaner one.
- **Simplify the prose, never the evidence.** Hierarchy, labels, captions,
  spacing, typography and responsive layout are the tools. Deletion is not.
- **Method and caveats may be disclosed. Data may not.** A default-closed
  `<details>` is acceptable for a method note, a caveat or a definition. It is
  not acceptable for a table, metric, column, source, confidence or unknown
  state that the page contract says must be visible.
- **One representation per fact** where possible; registers are tables, cards
  are editorial.
- **Accessibility is not optional.** One H1, table headers, captions, visible
  focus, keyboard-operable controls and text alternatives for charts.

## Page-contract principle

A contract is a floor, not a ceiling. The machine-readable contracts live in
`web/contracts/surfaces.json`; the human-readable contracts and the reasoning
live in [page-contracts.md](page-contracts.md). Contracted data is visible in the
default rendered state. If the data is absent, render an explicit unavailable
state with the same marker; do not delete the surface.

A contract change is a product decision with an explicit diff, not a styling
tweak. It requires owner approval, an update to the contract document and
manifest, and tests.

## Non-negotiables

1. The evidence stays. Data, tables, columns, caveats and sources are not
   removed, hidden behind default-closed disclosure, or replaced by a question.
2. Headings name the subject. A contracted H1, H2 or H3 never asks the reader a
   question.
3. Every claim carries its basis: measured, inferred, curated or unknown.
4. On the club's side is not the club's mouthpiece.
5. No imagined median user. Write for the engaged, numerate Aberdeen fan; do not
   simplify by subtraction.
6. Uncertainty is visible, not buried.
7. The Cormack era is a trade-off, not a verdict. Separate player, manager and
   structural causes.
8. A contract change needs an explicit diff and owner approval.

## What future style and engagement agents may do

May:

- improve hierarchy, spacing, typography, contrast, responsive behaviour,
  semantics and accessibility;
- add explanation, definitions and source links;
- reorganise within a page if every contracted marker, header, anchor and
  indicator remains visible;
- add tests, contracts for new surfaces and better diagnostics.

May not:

- remove or hide contracted data;
- move it into default-closed details, tabs, accordions, `hidden`,
  `aria-hidden`, `.sr-only` or inline CSS;
- replace declarative headings with questions;
- use word-count budgets, "casual fans", a "median user", "engagement" or
  "above the fold" to justify deleting evidence;
- change the identity line or lede without owner approval;
- edit the manifest or checker to make a failing change pass. Contract
  additions are allowed; removals, loosening and bypasses require owner
  approval.

## Relationship to other documents

- [brand.md](brand.md): the visual and verbal brand system (Granite & North Sea).
- [product-strategy.md](product-strategy.md): product scope, content pillars and
  roadmap. It defers identity, audience and voice to this document.
- [page-contracts.md](page-contracts.md): normative route contracts and the
  marker convention.
- [history.md](history.md): the Cormack-era record and its coverage rules.
- [methodology.md](methodology.md) and [sources.md](sources.md): definitions,
  provenance and correction policy.
- [player-page-spec.md](player-page-spec.md): remains normative for player pages;
  this charter and the route contracts apply on top.
