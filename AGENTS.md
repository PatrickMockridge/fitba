# Agent instructions: fitba

This file is canonical for all coding agents. `CLAUDE.md` points here.

## Read first

Before changing public copy, layout or a number:

1. [`docs/specification.md`](docs/specification.md) — intent, audience,
   essential/conditional/non-essential, number governance and change control.
2. [`docs/identity.md`](docs/identity.md) — identity, voice, stance and
   non-negotiables.
3. [`docs/design.md`](docs/design.md) — the System 7 grammar and the four themes.
4. [`docs/page-contracts.md`](docs/page-contracts.md) — what each route must keep
   visible.
5. [`web/contracts/surfaces.json`](web/contracts/surfaces.json) — the
   machine-readable route contracts.
6. `config/metrics.yaml` — the metric registry; [`docs/metrics.md`](docs/metrics.md)
   and [`docs/metric-changes.md`](docs/metric-changes.md) for verification and
   change control.
7. [`docs/product-strategy.md`](docs/product-strategy.md) — scope and roadmap
   only.
8. The relevant page specification: `docs/matchday.md`, `docs/analysis.md`,
   `docs/fixtures.md`, `docs/match-scoreboard.md`, `docs/xg.md`, `docs/needs.md`,
   `docs/transfers.md`, `docs/squad.md`, and the shared
   `docs/player-profile-standard.md` for player profiles.
9. [`docs/docs-book.md`](docs/docs-book.md) — the mdBook source,
   Merkland/Aurora themes and build commands.

Do not start a style, copy or number change without reading 1–6.

## Essential, conditional, non-essential

- **Essential:** contracted data, columns and values; sources, basis,
  confidence, coverage and unknown/empty states; identity line/lede, reader and
  editorial stance; metric definitions and audit. Owner approval required to
  remove, hide or semantically change.
- **Conditional:** method notes, caveats and editorial reads. May be disclosed
  or reworded if the evidence and source remain visible.
- **Non-essential:** layout, theme, decoration, headline/lede phrasing and
  component styling. May change if contracts, design rules and audit pass.

If unsure, treat the change as essential.

## Non-negotiables

- Do not remove contracted data, columns, caveats, confidence or sources.
- Do not hide contracted data behind default-closed `<details>`, tabs,
  accordions, `hidden`, `aria-hidden`, `.sr-only` or inline CSS.
- Do not replace declarative H1/H2/H3 headings with questions.
- Do not invent a median, casual or "average" user to justify deletion.
- Do not use word-count budgets, engagement targets, "simplification" or
  "above the fold" as a reason to remove evidence.
- Do not change the identity line or lede, audience or editorial stance without
  owner approval.
- Do not edit `web/data/generated/*` or the audit by hand. Regenerate it through
  the pipeline.
- Do not add a dependency for a style change.
- Do not edit the manifest or checker to make a failing change pass. Adding a
  contract for a new surface is allowed; removing, loosening or bypassing an
  existing contract requires owner approval.
- Do not add an unregistered number, duplicate a production calculation, or
  change a formula, denominator, rounding mode, source, coverage or parameter
  without owner approval and a registry version bump.
- Do not add a direct client-side `Math.round` or `toFixed` call outside
  `web/lib/format.ts`. `config/client-formatting.yaml` is a shrinking baseline;
  a file may not exceed its allowance and a new file may not add one.

## Before changing a number

A number is any value, rate, percentage, count, rank, range, confidence,
coverage label, threshold or weight. It is not done until:

1. It has a `config/metrics.yaml` entry with id, definition, formula, inputs,
   unit, aggregation, denominator, rounding, basis, source layer, coverage,
   confidence rule, home payload, paths, verification mode and implementation.
2. Its parameter values match config; no code default silently disagrees.
3. It has a verification function (for `recompute`) or a declared
   cross-surface/source/checksum check.
4. It has a test and an audit entry; `make metrics-check` passes.
5. Any semantic change has owner approval, a metric/registry version bump and an
   entry in `docs/metric-changes.md`.
6. Any changed published value is recorded old/new with the reason and audit
   impact. Do not change a value to make a page look better.

## Required process for a style or copy change

1. Run a baseline build and checker.
2. Make the smallest change that achieves the goal.
3. Run `git diff --stat` and list every contracted marker, column, anchor or
   indicator touched. Any removal is a contract change, not a style change.
4. Build root and base path; run the checker both ways.
5. Take before/after screenshots at 1440px and 390px.
6. In the PR, state the identity reason, the evidence, the contract diff and the
   verification commands.

## When a change genuinely requires removing a contract or changing a metric

- Propose the diff to `docs/page-contracts.md` / `web/contracts/surfaces.json`
  or `docs/specification.md` / `config/metrics.yaml` in the same PR.
- Add or update tests.
- State what data or value becomes unavailable/changed and why the identity and
  audit still hold.
- Require owner approval. Never self-approve a contract or metric deletion.

## Commands

```bash
# Root build and contract check
cd web && npm run build
cd .. && uv run python scripts/check_web_contract.py --ci

# Base path
cd web && NEXT_PUBLIC_BASE_PATH=/fitba npm run build
cd .. && uv run python scripts/check_web_contract.py --ci --base-path /fitba

# Documentation book
mdbook build
mdbook serve

# Metrics
uv run python scripts/check_metrics.py --strict
uv run python scripts/diff_published.py --before <baseline> --after web/data/generated
uv run fitba publish --season current --profile public --require-validation
make metrics-check

# Full checks
make check
make check-all
make web-contract-check
```

## Done means

- The specification, registry and any page contract are updated where relevant.
- The docs Markdown, `docs/SUMMARY.md` and any affected docs page are updated;
  `mdbook build` succeeds.
- Root and base-path builds pass; `make check` and `make check-all` pass.
- `check_metrics.py --strict` passes and the audit status is pass.
- Every changed number is registered, tested, audited and documented.
- No essential data is hidden or deleted.
- The PR records the checks, screenshots and any value diff.
- Nothing is committed, pushed or deployed unless the owner asked.
