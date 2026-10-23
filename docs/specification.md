# Specification: fitba

**Status:** canonical product, audience and number-governance specification.
**Version:** 1.0.
**Last reviewed:** 2026-10-22.
**Precedence:** this document governs intent, audience, essentiality, number
semantics and change control. [identity.md](identity.md) governs voice and
editorial stance. [page-contracts.md](page-contracts.md) governs route
visibility. `config/metrics.yaml` and the generated audit govern metric
definitions. [design.md](design.md) governs visual grammar.
Page specs and [methodology.md](methodology.md) carry detailed method.

## Intent

fitba is an independent, data-driven record of Aberdeen FC: the numbers, the
sources and the argument, without the hot takes. It exists so that supporters,
the club, the press and critics can look at the same evidence, and so that the
argument about the club can be conducted on the record rather than on noise.

The site has an interpretation. It is not a wire service. The data is the
evidence; the read is fitba's own and is labelled as a read. It is independent,
non-commercial, correctable and on the club's side without being its mouthpiece.

## Audience

There is one public record, with one primary reader and a set of secondary
readers. There is no separate simplified product and no tertiary tier.

- **Primary:** highly engaged, literate, numerate Aberdeen fans who know the
  squad and the league and want the evidence, the sources and the uncertainty.
- **Secondary:** the club, press, critics, Scottish football readers, students,
  journalists and analysts reading the same public record.
- **Not a design target:** a hypothetical median, casual or “average” user.
  Never remove evidence to make a page feel lighter for an imagined reader.

Navigation and hierarchy may serve a first-time reader. Evidence may not be
removed, hidden or replaced to do so. `identity.md` remains canonical for how
the record speaks; this section is canonical for who it is for.

## Essential, conditional and non-essential

**Essential** means the record would be materially less true or less auditable
without it. It requires owner approval to remove, hide or semantically change.

- Contracted data, columns and values.
- Source links, basis, confidence, coverage and unknown/empty states.
- The identity line and lede, the reader definition and the editorial stance.
- Metric definitions, parameters and the audit trail.
- Route anchors and required links that make the evidence reachable.
- Accessibility: one visible H1, declarative headings, table headers and
  keyboard access.

**Conditional** means it supports or qualifies the record. It may be disclosed,
reworded or reorganised if the evidence and source remain visible.

- Method notes, definitions and long caveats.
- Editorial reads and interpretation.
- Secondary explanations and examples.

**Non-essential** means it may change within the contracts and design rules.

- Layout, spacing, theme, decoration and component styling.
- Headline and lede phrasing beyond the contracted identity line/lede.
- Ordering within a section when every contracted marker remains visible.
- Explanatory prose that does not carry a number, source or required state.

### Per-route examples

| Route | Essential | Conditional | Non-essential |
|---|---|---|---|
| `/` | identity line/lede, matchday data, off-pitch counts, squad summary, full standings, unknown/freshness | door explanations, method | layout, theme, headline phrasing |
| `/matchday/` | fixture, predicted XIs, selection weights, availability, form columns, style, strength percentiles, head-to-head, coverage | long method notes | visual arrangement |
| `/analysis/` | Season overview: next fixtures, official and derived availability, season aims, factual squad-decision lenses, bridges and coverage | method, definitions, long caveats | layout and visual treatment |
| `/analysis/xg/` | fxG model card, provider-xG gate, aggregates, coverage | model detail, limitations | layout |
| `/matches/` | played-fixture index, scores, depth and links | grouping | layout |
| `/matches/<fixture_id>/` | scoreboard (score, goals, assists, penalties, red cards), Aberdeen/opposition split, summary, stats, fxG, timeline, lineups, player stats, form, coverage | summary variants, method | layout |
| `/recruitment/` | seven families, priority/urgency/category/confidence, slots, counts, market route, roster, player table | caveats/method | layout |
| `/transfers/` | verification badges, net range, position/fee/loan/source, sell-on table, completeness, coverage | how-to-read, fee method | card styling |
| `/loans/` | in/out counts, every loan card with terms or unknown, coverage, sources | coverage prose | styling |
| `/squad/` | summary, roster columns, role mix, coverage | role dialog, method | styling |
| `/history/` | scorecard, thesis, season table, managers, baseline, honours, read, coverage | full staff timeline, method | layout |
| `/sources/` | layer table, source registry, migration, availability, excluded, derived/no-raw | attribution notes | styling |
| `/methodology/` | source table, all method sections, indicators | long method detail | styling |
| `/metrics/` | all definitions, formulas, parameters, basis/source/coverage/verification/status, audit summary | implementation notes | layout |
| `/status/` | build identity, validation, audit summary, counts, coverage, marts | notes | styling |
| `/about/` | identity line/lede, audience, club-side stance, Cormack frame, what will not be built | examples | styling |

The exhaustive visible-surface list remains in [page-contracts.md](page-contracts.md)
and `web/contracts/surfaces.json`.

## Number governance

A **number** is any value, rate, percentage, count, rank, range, confidence,
coverage label, threshold or weight. Every published number is either:

- registered in `config/metrics.yaml`; or
- explicitly classified as structural metadata (an identifier, timestamp, file
  size or enum) in the registry’s structural patterns.

There is no third category. An unregistered numeric leaf in generated JSON fails
CI.

### Rules

1. **One fact, one home.** Every metric has one registry id, one home payload and
   one production implementation. Displayed surfaces read the home payload; they
   do not recompute it.
2. **Basis is visible.** Every metric declares `measured`, `inferred`, `curated`,
   `mixed` or `unknown`, and a source layer.
3. **Coverage is visible.** Every metric declares its coverage tier and any
   denominator/sample rules. A value-only player is never silently ranked against
   event data.
4. **Unknown stays unknown.** Unknown is not zero, not an em dash that reads as
   not applicable, and not a guess. Undisclosed fees are never zero. Wages,
   internal valuations and boardroom intent are never invented.
5. **Rounding is declared once.** Every metric declares a rounding method,
   decimals/step and display format. Calculations use full precision; the source
   value is rounded once; clients use the shared formatter.
6. **Parameters are registered.** Weights, thresholds, sample limits, age curves,
   FX rates and similar constants are config-backed and registered. Code defaults
   may not silently disagree with config.
7. **No duplicate production calculation.** A shared analytics function may be
   called from several publish paths; it may not be copied. Verification code may
   independently re-derive a value to catch bugs; that is not duplicate
   production calculation.
8. **No silent value changes.** A fix that changes a published value records the
   old/new values, the reason, the metric id and the audit entry in the pull
   request and `docs/metric-changes.md`.
9. **No volatile prose counts.** Docs do not restate exact register counts,
   anchors or net ranges unless the value is pinned by the audit. Link to the
   live register or `/metrics/` instead.

### Verification modes

Every metric declares how it is verified:

| Mode | Proves | Does not prove |
|---|---|---|
| `recompute` | The value is re-derived from published rows using the registered formula. | Upstream provider accuracy. |
| `cross_surface` | The same fact agrees across two published payloads. | The formula is correct. |
| `config_match` | The registered parameter equals the config value. | The config value is analytically right. |
| `source_checksum` | The curated source files are present and their digests are recorded. | The source fact is true. |
| `provenance_only` | The value is present and its declared layer/source is active with recorded rows. | Independent recomputation. |

`provenance_only` is a visible limitation, not a synonym for verified. The
`/metrics/` page must show the mode and the audit must count it.

### Registry and audit

- `config/metrics.yaml` is the canonical registry: definitions, formulas,
  inputs, denominators, aggregation, rounding, basis, source, coverage,
  confidence, home payload, paths, verification mode, implementation, limitations,
  owner, review date and version.
- `scripts/check_metrics.py` validates the registry, the published registry, the
  audit and every numeric leaf.
- Every publish writes `web/data/generated/metrics/registry.json` and
  `web/data/generated/audit/metrics.json`; the manifest carries their checksums
  and status.
- A failed audit blocks the atomic publish. There is no production allowlist at
  release; any temporary migration allowlist must be owner-approved, expiring,
  visible on `/status/`, and removed before merge.
- `docs/metrics.md` documents the registry, audit and change process; the
  public `/metrics/` page is rendered from the published registry and audit.

## Change control

### Owner approval required

- Any metric definition, formula, input, denominator, aggregation, rounding,
  basis, source layer, coverage tier, confidence rule or parameter value.
- Adding a new metric, deprecating a metric, or changing essentiality.
- Removing or loosening a page contract, anchor or source requirement.
- Changing the identity line/lede, audience or editorial stance.
- A registry version bump is part of the same change.
- Add an entry to `docs/metric-changes.md` with before/after, reason, affected
  surfaces, value impact and owner approval reference.

### May change without owner approval

- Non-essential layout, theme, spacing, decoration and component styling that
  preserves every contracted marker, column, source and state.
- Additive definitions, tests, documentation links and additive contracts.
- Bug fixes that preserve published values and audit semantics.
- Copy clarifications that do not change a number, source, basis or stance.

## Agent decision procedure

Before changing a page, number or component:

1. **Classify the change.** Essential, conditional, non-essential, or a metric
   semantic change. If unsure, treat it as essential.
2. **Stop if essential or semantic.** Propose the change to the owner with the
   metric id, current/proposed definition, expected value impact and audit impact.
   Do not edit first.
3. **For conditional changes**, keep the evidence and source visible. Update the
   page spec and any definition the change makes stale.
4. **For non-essential changes**, proceed only if the page contract, design rules
   and metric audit pass.
5. **For every number**, ensure the registry entry, formula, denominator,
   rounding, basis, source, coverage, verification, test and audit are present.
6. **Never** hand-edit generated JSON or the audit; regenerate through publish.

## Definition of done

A change is done when:

- the specification/contracts are updated;
- the metric registry and `docs/metric-changes.md` are updated where relevant;
- `make check`, `make check-all`, both web builds and both contract checks pass;
- the audit reports pass and every changed value is documented;
- no essential content is hidden or removed;
- the PR records the checks, screenshots and any value diff.

## Relationship to other documents

- [identity.md](identity.md): voice, stance and non-negotiables. It defers
  audience to this document.
- [page-contracts.md](page-contracts.md): route visibility and the contract-change
  process.
- [metrics.md](metrics.md): the technical metric registry and audit companion.
- [metric-changes.md](metric-changes.md): versioned metric change log.
- [design.md](design.md): visual grammar and themes.
- [methodology.md](methodology.md), [sources.md](sources.md) and the page specs:
  detailed method and provenance.
- [product-strategy.md](product-strategy.md) and [roadmap.md](roadmap.md): scope
  and sequencing. They defer intent, audience and number rules here.
