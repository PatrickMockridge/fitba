@AGENTS.md

## Claude Code notes

- Work from `/home/patrick/footballstats`.
- Python: use `uv run ...`. Web: `cd web && npm ...`.
- Do not edit `web/data/generated/`; regenerate through the pipeline.
- For any public-copy, layout or engagement change, run the baseline contract
  check, make the smallest change, then run both the root and `/fitba` checks.
- If a change requires deleting a contract, stop and ask the owner. Do not edit
  the manifest or checker to pass.
- The identity line is "Aberdeen FC, without the noise." The reader is a highly
  engaged, literate, numerate Aberdeen fan, not an imagined median user.
- Do not use word-count budgets to justify removing data.
