# Metrics and audit

**Status:** technical companion to [specification.md](specification.md).
**Registry:** `config/metrics.yaml` (canonical). **Public view:** `/metrics/`.
**Audit:** `web/data/generated/audit/metrics.json`.
**Last reviewed:** 2026-10-24.

Every published number has a registry entry. The registry defines the metric;
the generated audit proves what was checked against the published payloads.
This document is the technical companion to the registry and audit; the
public `/metrics/` page is rendered from the published artefacts.

The provenance-only mode is a visible limitation, not a claim of independent
verification. Live totals are the audit summary and `/metrics/`; this document
does not restate them.

## Registry fields

Each metric has:

- `id`, `label`, `description`, `version`, `status`, `owner`, `reviewed`;
- `value_type`, `fields`, `formula`, `inputs`, `unit`, `aggregation`,
  `denominator`, `rounding`;
- `basis`, `source_layer`, `coverage_tier`, `confidence_rule`;
- `home_payload`, `payload_paths`, `home_surface`, `displayed_surfaces`;
- `verification`, `verification_checks`, `implementation`, `source_paths`,
  `limitations`.

Each parameter has:

- `id`, `label`, `kind`, `value`, `unit`, `used_by`, `config_path`,
  `config_keys`, `verification: config_match`, `reviewed`.

`config_path` is `<file>.<key...>` under `config/`. A parameter that is a subset
of a config mapping declares `config_keys`; the audit compares only those keys
and fails on a missing key. Every parameter is re-read from config on each
audit; a code default may not silently disagree.

The registry also declares structural number patterns for identifiers,
timestamps, file sizes and enums. Every numeric leaf in generated JSON must match
a metric path or a structural pattern.

### Payload path grammar

`payload_paths` entries are `<payload-glob>#<json-pointer-glob>`:

- `*` matches one object key or array index;
- `**` matches the whole subtree below that point;
- `*[field=value]` selects mapping or array children whose `field` equals
  `value`, for payloads that group several registered families in one list
  (for example `/themes/aberdeen.json#/claims/*[id=team_now]/**`).

`home_payload` is a document glob (`tables/*.json`, `players/*.json`). The same
grammar drives the numeric-leaf coverage check and the audit locations.

## Verification modes

| Mode | What it proves | What it does not prove |
|---|---|---|
| `recompute` | The value is re-derived from published rows using the registered formula. | Provider accuracy. |
| `cross_surface` | The same fact agrees across two payloads. | Formula correctness. |
| `config_match` | The registry parameter equals config. | The config is analytically correct. |
| `source_checksum` | The curated source files are present and their digests are recorded. | The source fact is true. |
| `provenance_only` | The value is present and its declared layer/source is active. | Independent recomputation. |

`provenance_only` is displayed as a limitation on `/metrics/` and counted in the
audit summary. It is not called verified.

## Audit artifact

Every publish writes:

- `web/data/generated/metrics/registry.json` — the published registry view.
- `web/data/generated/audit/metrics.json` — per-metric and per-parameter status,
  locations, row/field counts, checks and errors.
- `web/data/generated/audit/validation.json` — the compact validation report.

The manifest carries `manifest.metrics`, `manifest.validation` and
`manifest.consistency` with paths, checksums, status and counts. A failed audit
blocks the atomic publish. The public `/status/` page shows the audit status;
`/metrics/` shows the definitions, verification modes and audit results.

`audit/consistency.json` is the cross-surface report. It is generated from the
same corpus and run inside publish; `scripts/check_consistency.py` exposes it
in CI. It proves that two pages do not disagree about the same fact. It does not
prove that their shared formula is right; that is the metric audit.

## Numeric-leaf coverage

`scripts/check_metrics.py` walks every numeric leaf in published JSON (excluding
the manifest, registry and audit themselves). Each leaf must match:

- a registered `payload_paths` glob; or
- a declared structural pattern (id, timestamp, file size, enum).

Unmapped numbers fail CI. This is the “every number” guarantee.

Client formatting is a separate, shrinking baseline. `config/client-formatting.yaml`
records the existing direct `Math.round`/`toFixed` calls outside
`web/lib/format.ts`; the checker fails when a file exceeds its allowance or a
new file adds a call. Move formatting into shared helpers before adding one.
The baseline may fall, never grow.

## Verification functions

Every `recompute` metric names an implementation in
`src/fitba/metrics/checks.py`. A test asserts every such metric has a function.
`cross_surface` metrics declare the two payload locations. `config_match`
parameters are checked against their `config_path`. `source_checksum` metrics record digests for their declared `source_paths`.
No active metric uses this mode in the current registry; the checker keeps the
mode for future source digests.

## Change process

1. Propose the metric id, current and proposed definition, reason, affected
   surfaces, expected value impact and audit impact.
2. Obtain owner approval and link it in the pull request.
3. Bump the metric `version` and registry `version`; update
   [metric-changes.md](metric-changes.md).
4. Update the registry, implementation, config, tests, docs and page contracts in
   the same change.
5. Run `make metrics-check`, publish with validation and attach the
   `diff_published.py` output.
6. Do not merge with a failing audit, a stale schema or an active migration
   allowlist.

## Commands

```bash
uv run python scripts/check_metrics.py --strict
uv run python scripts/check_metrics.py --against-git origin/main
uv run python scripts/diff_published.py --before <baseline> --after web/data/generated
uv run fitba validate --season current --strict
uv run fitba publish --season current --profile public --require-validation
make metrics-check
```
