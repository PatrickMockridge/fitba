# Metric change log

**Status:** append-only record of metric-definition and parameter changes.
**Owner:** patrickmockridge. **Last reviewed:** 2026-10-22.

A semantic metric change is any change to an id, formula, input, denominator,
aggregation, rounding, basis, source layer, coverage tier, confidence rule,
parameter value or verification mode. Each change records owner approval, the
affected surfaces, the expected value impact and the audit impact.

## 1.0.0 — 2026-10-22

- Established the canonical registry in `config/metrics.yaml`.
- Registered the current published metric families and parameters.
- Established the generated audit, `/metrics/`, `/status/` summary and hard CI.
- This entry records the baseline. No published value was intentionally changed
  by the initial registry work; any change found during reconciliation is listed
  below when it lands.

### Value changes

None at baseline.

## 1.1.0 — 2026-10-22

Pipeline reconciliation of provenance source rows. No metric formula,
denominator, rounding mode or parameter value changed; the published payload
values that changed are the provenance source-row counts and the manifest
source summaries.

| Field | Before | After | Reason |
|---|---:|---:|---|
| `league_team_stats.football_data_uk.rows` | 0 | current-season matches with team stats | Placeholder replaced with the real row count. |
| `event_layer.api_football.rows` | 0 | appearance rows | Placeholder replaced with the reconstructed-event input count. |
| `transfers_candidate.api_football.rows` | 0 | candidate-feed rows | Placeholder replaced with the local candidate count; zero when the gitignored candidate file is absent. |
| `transfer_register.wikipedia.rows` | 0 | register rows with a Wikipedia source URL | Placeholder replaced with real corroboration rows. |
| `transfer_register.afc_news.rows` | 0 | register rows with an AFC source URL | Placeholder replaced with real corroboration rows. |
| `availability.afc_news.rows` | 0 | entries with an official AFC source | Computed; currently zero because every entry is `unknown`. |
| `rumours.afc_news.rows` | 0 | rumour rows with an AFC source | Computed; currently zero because the register is empty. |
| `history.wikipedia.rows` | 0 | history source references | Placeholder replaced with real source references. |
| `history.afc_news.rows` | — | history source references | AFC corroboration now counted. |
| `valuation.football_data_uk.rows` | 0 | — | Football-Data does not supply valuation anchors; the attribution was wrong. |
| `valuation.wikipedia.rows` | — | published anchor count | Public valuation anchors are AFC/Wikipedia only. |

Also in 1.1.0:

- Win/draw/loss, goals and points arithmetic moved to
  `fitba.analytics.records.record_totals`; matchday and history consume the same
  function.
- Valuation calibration and row estimates moved to a single
  `fitba.analytics.valuation.value_transfers` run. Transfers and history consume
  the same estimated rows and summary instead of recalculating.

`diff_published.py` reported zero changed numeric leaves for the consolidation
step. Affected surfaces: `/sources/`, `/methodology/`, `/status/`, `/metrics/`.
Audit impact: `provenance.layers` remains `provenance_only` and passes; the
audit is regenerated with the new dataset version. Owner approval: baseline
reconciliation approved with the metric-governance scope on 2026-10-22.

## 1.2.0 — 2026-10-22

Definition completeness for the `recompute` families. The registry now states
the arithmetic that the verification functions already implement for matchday
form, needs summary, transfer summary and windows, history baseline, squad
summary and rumours summary, and declares integer versus rate rounding. No
published value or calculation changed; `diff_published.py` is expected to
report zero changed numeric leaves after republishing.

## 2.0.0 — 2026-10-22

The themes section was rebuilt as **Data analysis**. The storage path stays
`themes/aberdeen.json` for pipeline stability; the reader-facing page is
`/analysis/`, with `/themes/` redirecting.

- The payload changed from five theme blocks to six claims with `claim`, `count`,
  `status`, `status_reason`, `evidence`, `better_data` and `change_mind`.
- The owner's view and the chairman's frame are published as attributed blocks.
- Added a peer benchmark: league performance of the other SPFL clubs, with the
  missing transfer/wage comparison labelled.
- Metric ids `themes.*` were replaced by `case.*`; the paths point to the same
  payload. The registry version is `2.0.0`.
- Added `param.case.thresholds` and `param.case.scope`.
- The 80/20 split, the fixed five-card count and the per-theme metric panels were
  retired.
- Data corrections: the centre-back "thin" headline, the young-minutes wording,
  the CB 5-vs-4, fixture 15-vs-20, shape 2-vs-5 and AM/WM 8-vs-7 counts, the
  "record" run wording and the 0.05 rating-gap claim.
- Overlapping measured values (league record, shape split, goals, recruitment
  counts) are unchanged by design.
- Affected surfaces: `/analysis/`, `/matchday/`, `/recruitment/`, `/status/`,
  `/sources/` and `/metrics/`.
- Audit impact: `case.*` families are `provenance_only` in this version with
  explicit limitations; the guard checks claim counts, statuses, evidence,
  benchmark and headline/table agreement.
