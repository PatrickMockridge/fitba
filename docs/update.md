# Data update pipeline

**Status:** canonical. One command refreshes every published data area.

## The command

```bash
uv run fitba update --mode daily --force-results
uv run fitba update --mode matchday --force-results
uv run fitba update --mode ci --force-results
```

`scripts/local_update.sh` calls the same command from the local cron cadence;
`.github/workflows/update-daily.yml` calls it for the manual CI fallback.

Options:

- `--only` / `--skip`: comma-separated step ids.
- `--dry-run`: print the ordered plan and the due decision without writing.
- `--no-publish`: run ingest and build only; guards that read the published
  corpus are skipped.
- `--allow-stale`: do not mark the run degraded when an optional source is
  stale. It never downgrades a missing result or a table contradiction.
- `--resume`: skip steps already recorded as `ok` in the previous state file.
- `--force`: run matchday mode even when the due gate says no.
- `--json`: print the run report.

## Modes

| Mode | When | What refreshes |
|---|---|---|
| `daily` | Once a day | Every ingest area, including the scouting pool, roles, rose history, Europe, standings, clubs and xG enrichment. |
| `matchday` | Every two hours; runs only when a finished fixture has no result | Results, the official club feed, the fixture-dependent surfaces, build, validate, publish and the guards. Other sources keep their TTL and are reported with their age. |
| `ci` | Manual GitHub dispatch | The same list as daily. Steps that need `API_FOOTBALL_KEY` are recorded as `skipped` with `reason="missing_api_key"`, never silently omitted. |

## Ordered steps

Required steps are `ingest.results`, `ingest.api_results` (when the provider key
is present), `warehouse.build`, `validate`, `publish`,
`guard.results`, `guard.consistency`, `guard.freshness`, `guard.semantic` and
`guard.metrics`. A required failure stops the run before publish and leaves the
previous published directory in place.

`guard.semantic` runs `check_semantic.py`, `check_unknowns.py`,
`check_comparison.py` and `check_page_budget.py` in data mode after publish. It
proves that every entity id, alias and external id is unique, the core and
scouted groups are disjoint, every page-meta layer and metric resolves, every
claim points at `/claims/`, every definition and related id references a
registered entry, every unknown count resolves to a registered payload, every
comparison crosswalk row matches the published squad and cohort, and every
generated payload is inside its browser budget. It does not run the page-mode
href check, which needs a build; that runs in `make web-contract-check`.

Optional steps are cups, the official fixture overlay, history backfill,
matchday, transfers, former players, squad, availability, career, news, forum,
the six scouting steps and `xg.enrich`. A failure marks the source stale and
continues; the stale source is written into the run state and the manifest. The
fixture overlay is optional precisely because the result guard is required: if
the overlay did not run and a finished result is missing, validation blocks the
publish even though the step itself did not raise.

## Result-aware due gate

`fitba.update.refresh_due` reads the published fixture schedule and asks two
questions for every finish older than kickoff + 3 hours:

1. Is the fixture present with a score in the canonical match frame?
2. If not, is it present with a score in the published fixture index?

A missing result is due even when the manifest timestamp is newer. A
timestamp-only publish cannot mark a missing result as handled.

## State file

`data/normalized/update_state.json` is written atomically after every step:

```json
{
  "schema_version": "1.0.0",
  "run_id": "...",
  "update_id": "...",
  "mode": "daily",
  "season": "2026-27",
  "git_sha": "...",
  "status": "running|ok|degraded|failed",
  "steps": [
    {"id": "ingest.results", "required": true, "status": "ok", "rows": 55}
  ],
  "stale_sources": [{"source": "scouting_pool", "reason": "step_failed"}],
  "guards": {}
}
```

A budget or network interruption leaves the completed steps recorded; `--resume`
continues from the first failed or absent step. Cache-first ingest makes a rerun
safe.

## Guards

- **Results** — every official played Aberdeen league fixture is present in the
  canonical frame and the table counts reconcile. `fitba validate --strict`
  performs the same checks before publish.
- **Consistency** — the published corpus passes every cross-surface check,
  including `results.table`, `results.form`, `results.club`,
  `results.coverage`, `rules.epoch` and `rules.manifest`.
- **Freshness** — every payload is on the current dataset epoch or explicitly
  stale with a reason; required sources are inside their TTL; optional stale
  sources are listed in the manifest; manifest checksums match.
- **Metrics and publication** — `check_metrics.py --strict` plus the full
  publication checker set (transfers, former players, history, matchday,
  themes, xG, provenance, availability, needs, rumours, squad, scouting, roles,
  shapes, career roles, player pages and attributes).

Publish itself is atomic: the new directory replaces the live one only after
validation, consistency and the audit pass. Published file size is not capped;
the compact scouting search index is allowed to grow with the refreshed player
pool because it is a machine index, not page copy.
