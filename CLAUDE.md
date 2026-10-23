@AGENTS.md

## Claude Code notes

- Work from `/home/patrick/footballstats`.
- Python: use `uv run ...`. Web: `cd web && npm ...`.
- Do not edit `web/data/generated/` or the audit by hand; regenerate through
  `fitba publish`.
- Read `docs/specification.md` and `config/metrics.yaml` before changing a
  number. Every published number needs a registry entry, verification and audit.
- Any formula, denominator, rounding, source, coverage or parameter change needs
  owner approval, a registry version bump and an entry in
  `docs/metric-changes.md`.
- For style/copy changes, run the baseline contract check, make the smallest
  change, then run both root and `/fitba` checks.
- If a change requires deleting a contract or changing a metric definition, stop
  and ask the owner. Do not edit the manifest, registry or checker to pass.
- The identity line is "Aberdeen FC, without the noise." The primary reader is a
  highly engaged, literate, numerate Aberdeen fan, not an imagined median user.
- Do not use word-count budgets to justify removing data.
- Docs are source-first: edit `docs/*.md`, add the page to `docs/SUMMARY.md`, then
  run `mdbook build`. The mdBook themes are in `theme/`; the book output is
  generated and gitignored.
