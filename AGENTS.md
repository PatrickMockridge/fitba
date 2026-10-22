# Agent instructions: fitba

This file is canonical for all coding agents. `CLAUDE.md` points here.

## Read before changing public copy or layout

1. [`docs/identity.md`](docs/identity.md) — the identity, reader, voice and
   non-negotiables.
2. [`docs/page-contracts.md`](docs/page-contracts.md) — what each route must keep
   visible.
3. [`web/contracts/surfaces.json`](web/contracts/surfaces.json) — the
   machine-readable contracts.
4. [`docs/product-strategy.md`](docs/product-strategy.md) — scope and roadmap
   only. It defers identity and voice to `docs/identity.md`.
5. The relevant page specification: `docs/matchday.md`, `docs/themes.md`,
   `docs/needs.md`, `docs/transfers.md`, `docs/squad.md`.

Do not start a style, copy or engagement change without reading 1–3.

## Non-negotiables

- Do not remove contracted data, columns, caveats, confidence or sources.
- Do not hide contracted data behind default-closed `<details>`, tabs,
  accordions, `hidden`, `aria-hidden`, `.sr-only` or inline CSS.
- Do not replace declarative H1/H2/H3 headings with questions.
- Do not invent a median, casual or "average" user to justify deletion.
- Do not use word-count budgets, engagement targets, "simplification" or
  "above the fold" as a reason to remove evidence.
- Do not change the identity line or lede without owner approval.
- Do not edit `web/data/generated/*` by hand. Regenerate it through the pipeline.
- Do not add a dependency for a style change.
- Do not edit the manifest or checker to make a failing change pass. Adding a
  contract for a new surface is allowed; removing, loosening or bypassing an
  existing contract requires owner approval.

The reader is a highly engaged, literate, numerate Aberdeen fan. The site is also
a public record for the club, press and critics. It is independent, on the club's
side and not in its pocket.

## Required process for any style or engagement change

1. Run a baseline build and checker.
2. Make the smallest change that achieves the goal.
3. Run `git diff --stat` and list every contracted marker, column, anchor or
   indicator touched. Any removal is a contract change, not a style change.
4. Build root and base path; run the checker both ways.
5. Take before/after screenshots of the affected routes at 1440px and 390px.
6. In the PR, state the identity reason, the evidence, the contract diff and the
   verification commands.

## When a change genuinely requires removing a contract

- Propose the diff to `docs/page-contracts.md` and
  `web/contracts/surfaces.json` in the same PR.
- Add or update a test for the new behaviour.
- State what data becomes unavailable and why the identity still holds.
- Require owner approval. Never self-approve a contract deletion.

## Commands

```bash
# Root build and contract check
cd web && npm run build
cd .. && uv run python scripts/check_web_contract.py --ci

# GitHub Pages base path
cd web && NEXT_PUBLIC_BASE_PATH=/fitba npm run build
cd .. && uv run python scripts/check_web_contract.py --ci --base-path /fitba

# Make targets
make check
make web-contract-check
make web-contract-check BASE_PATH=/fitba
make check-all
```

## Done means

- The root and base-path builds pass.
- `uv run python scripts/check_web_contract.py --ci` passes both ways.
- `make check` passes.
- `git diff --exit-code -- web/data/generated` is clean.
- No contracted data is hidden or deleted.
- The PR records the contract checks and screenshots.
- Nothing is committed, pushed or deployed unless the owner asked.
