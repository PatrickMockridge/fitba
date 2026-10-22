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

## 2.1.0 — 2026-10-22

The API-Football match record, fxG and the confidence ledger.

- Added `matches.document`, `fixtures.index`, `xg.document` and
  `confidence.document` metric families. Each covers a published document family
  with wildcard payload paths; all are `provenance_only` with explicit
  limitations in this version. No existing metric or published value was
  changed.
- Added `param.xg`, `param.confidence` and `param.fixtures`. The values are the
  live `config/xg.yaml`, `config/confidence.yaml` and `config/fixtures.yaml`
  nodes.
- The registry version moves to `2.1.0`. The audit grows from 53 to 57 metrics
  and from 14 to 17 parameters. Numeric coverage now includes 370 fixture
  documents plus the fixture index, xG and confidence payloads.
- New surfaces: `/matches/` and `/analysis/xg/`; new markers on `/analysis/` and
  `/matchday/`. Existing surfaces and contracts are unchanged.
- fxG gate: fit before 2026-27, validate on 2026-27 provider xG. At this publish
  the gate fails, so fxG is descriptive and is not used in a confidence verdict.
- Confidence ledger: team form and up to 12 current-squad players, with 80%
  intervals and mechanical verdicts. 2019-20 has no historical provider player
  stats; later seasons are partial.
- Affected surfaces: `/matches/`, `/analysis/`, `/analysis/xg/`, `/matchday/`,
  `/methodology/`, `/metrics/`, `/status/`.
- Audit impact: the four new families are present and sourced; they do not add
  an independent recomputation of the fxG model or the confidence intervals in
  this version.
- Change-control comparison now normalises the previous registry through the
  same metric/parameter models, so default-valued fields are not reported as
  semantic changes. A real formula, parameter or path change still fails.

### Value changes in 2.1.0

The current-season football-data.co.uk re-ingest added one Championship result
before the 2026-10-22 18:17 publish. The table formula did not change.

| Field | Before | After | Reason |
|---|---:|---:|---|
| Dunfermline Athletic played / points / position | 9 / 14 / 6 | 10 / 15 / 5 | New 2026-27 Championship result in the source CSV. |
| Partick Thistle played / points / position | 10 / 21 / 3 | 11 / 22 / 2 | Same result. |
| Livingston position | 5 | 6 | Same result. |
| Raith Rovers position | 2 | 3 | Same result. |

Affected surfaces: `/`, `/competitions/`, `/status/`, `/metrics/`. The other
three 2026-27 league tables are unchanged. The audit is regenerated with the new
dataset version and passes.

The same release completed the historical match-stat backfill. Coverage counts
in `history` and the availability of lineup/event/player-stat fields increased
where the provider returned data; no history formula or denominator changed.

## 2.2.0 — 2026-10-22

Removed the confidence ledger. It repeated obvious statements and factoids
without adding evidence to the argument. This is an owner-directed removal, not
a formula repair.

- Removed the `confidence.document` metric family, the `param.confidence`
  parameter, the `confidence/aberdeen.json` payload and mart, the
  `ConfidenceTable` component, the confidence types and getter, and the
  `/analysis/` and `/matchday/` confidence blocks.
- Removed the `confidence.ledger` and `matchday.confidence` contract markers and
  their pinned tests. No other surface contract changed.
- Removed `docs/confidence.md` and the confidence method sections from
  `docs/analysis.md`, `docs/matchday.md` and `docs/methodology.md`.
- Retained from 2.1.0: `matches.document`, `fixtures.index`, `xg.document`,
  `param.xg` and `param.fixtures`.
- Registry version `2.2.0`; 56 metrics and 16 parameters.
- fxG remains, descriptive only while the provider gate fails. It is no longer
  described as entering a confidence verdict.
- Affected surfaces: `/analysis/`, `/matchday/`, `/methodology/`, `/metrics/`,
  `/status/`.

## 2.2.1 — 2026-10-22

Match scoreboard and event attribution corrections.

- Added `scoreboard`, timeline `side`/`beneficiary_side`/`card_type`/
  `is_missed_penalty`, and player-stat `team_name`/`is_aberdeen` to the fixture
  document. `matches.document` moves to version 2; registry version 2.2.1.
- Corrected own-goal attribution. API-Football's own-goal event team is the
  benefiting team; the old timeline flipped it. Examples:
  - `1174068` Aberdeen 3–1 Kilmarnock now ends 3–1 (was 2–2 in the timeline);
  - `569617` Aberdeen 0–2 Livingston now ends 0–2 (was 1–1);
  - `1382671` Hearts 2–0 Aberdeen now ends 2–0 (was 1–1).
- Corrected team alias matching (`Dundee Utd`, `Heart OF Midlothian`, etc.) via
  the team registry, with an exact-name fallback.
- Reclassified unflagged penalty-shootout events for PEN fixtures when excluding
  them reconciles to the final score. `693837` is 2–2 with 5–3 penalties; its
  timeline no longer runs to 7–5.
- Summaries now consume the corrected timeline, so the read reconciles with the
  final score.
- Nine fixtures have no event feed and one (`288887`) is partial; the scoreboard
  labels them unavailable/incomplete rather than inventing goals.
- Affected surfaces: `/matches/`, `/matches/<fixture_id>/`, `/analysis/`,
  `/metrics/`, `/status/`.
- Audit impact: the existing `matches.document` wildcard covers the new numeric
  leaves; the audit passes and the fixture checker verifies scoreboard/timeline
  reconciliation.
