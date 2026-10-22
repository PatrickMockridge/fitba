## What changed

<!-- One paragraph. State the identity reason, not just the visual change. -->

## Identity and contract check

- [ ] I read `docs/identity.md`, `docs/page-contracts.md` and the relevant page
      spec.
- [ ] No contracted data, table, column, caveat, confidence or source was
      removed or hidden.
- [ ] No declarative heading was replaced with a question.
- [ ] No invented median/casual user or word-count budget was used to justify
      deleting evidence.
- [ ] `uv run python scripts/check_web_contract.py --ci` passes for the root
      build.
- [ ] `uv run python scripts/check_web_contract.py --ci --base-path /fitba`
      passes for the Pages build.
- [ ] `make check` passes.
- [ ] `git diff --exit-code -- web/data/generated` is clean.
- [ ] If a contract changed: the diff to `docs/page-contracts.md` and
      `web/contracts/surfaces.json` is included, a test was added, and owner
      approval is linked.

## Screenshots

<!-- For copy or layout changes: before/after at 1440px and 390px. -->
