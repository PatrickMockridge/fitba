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

## Metric checklist

<!-- Complete when the change adds or alters any published number. -->

- [ ] The number has a `config/metrics.yaml` entry with definition, formula,
      inputs, denominator, rounding, basis, source layer, coverage tier,
      confidence rule, home payload, paths and verification mode.
- [ ] Parameter values match config; no code default disagrees.
- [ ] Every `recompute` metric has a verification function; `cross_surface`
      and `source_checksum` checks are declared; `provenance_only` carries an
      explicit limitation.
- [ ] `uv run python scripts/check_metrics.py --strict` passes and the audit
      status is `pass`.
- [ ] Any semantic change has owner approval, a metric/registry version bump
      and a `docs/metric-changes.md` entry.
- [ ] `uv run python scripts/diff_published.py --before <baseline> --after
      web/data/generated` is attached; every value change is recorded old/new
      with the reason.
- [ ] No migration allowlist is active at merge.

## Screenshots

<!-- For copy or layout changes: before/after at 1440px and 390px. -->
