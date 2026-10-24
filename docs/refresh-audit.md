# Data refresh audit

**Date:** 2026-10-24. **Owner:** patrickmockridge. **Status:** remediated in
registry 3.8.0. This is the record of the audit that followed the 2026-10-24
Dundee United 3–2 Aberdeen result appearing on some pages and not others.

## Verdict

The update path was not atomic. One malformed field let the official result
through the fixture record but not through the league table, form guide,
analysis hero, history or club summary. The same publish re-stamped the dataset
and reported success, so the mismatch was invisible to the freshness checks.

## Findings

### P0 — correctness and silent staleness

1. **The official result was dropped by the table filter.** The SPFL overlay in
   `src/fitba/ingest/runner.py` appended the 2026-10-24 row with
   `phase = null`; `playable_matches` in `src/fitba/analytics/tables.py`
   requires `phase == "regular"`. Every table-driven surface therefore showed
   nine matches and form `WLDWD` while the fixture pages showed the 3–2 loss.
2. **The published corpus contradicted itself.** `coverage.json` counted 55
   Premiership matches; the league table summed to 54. The club page showed the
   loss in `results` but not in `summary` or `history`.
3. **The due gate trusted timestamps.** `scripts/matchday_refresh_due.py`
   compared the manifest time with kickoff + 3h, not the result, so a publish
   that only re-stamped stale data marked the fixture as handled.
4. **The update path was incomplete.** `scripts/local_update.sh` ran no
   scouting ingest and no `xg-enrich`; ten of twelve ingest steps used
   `run_optional`, which logged a warning and continued. The manual CI workflow
   was a different step list and omitted former-player refresh.
5. **The results cache could be six hours old after a match.** `fitba ingest`
   used its download TTL and the post-match run did not force a refresh.

### P1 — duplicate derivations and missing guards

6. **Two overlays with different matching rules.** The match layer matched on
   date and team ids; the fixture publisher matched on date and display names.
7. **Form and points were derived in more than one place.** Matchday form was
   recomputed from matches while the strength block read the table; club
   `results` was recomputed while `summary` read the table; warehouse team
   stats re-derived from matches.
8. **No check compared results with tables, form, club results, history or
   coverage.** The only result check compared shootout labels.
9. **The epoch was not authoritative.** `dataset_version` appeared in two of
   489 documents; 22 had no top-level `generated_at`; stale fallbacks could
   re-stamp the current epoch.

### P2 — visibility and hygiene

10. **Freshness metadata was thin.** The manifest carried one per-surface
    timestamp and two TTLs; most source ages were invisible.
11. **`/status/` did not show update or source freshness.**
12. **The themes fallback was called with no previous document**, so a failure
    produced an empty unavailable document rather than carrying a labelled
    stale one.
13. **No guard verified manifest checksums or that every published file was
    listed.**

## Remediation

| Finding | Fix | Status |
|---|---|---|
| 1, 2 | Canonical results module appends complete rows with `phase="regular"`, `status="played"`, season, division and source; `normalise_phase` repairs legacy rows on read. | done |
| 3 | `fitba.update.refresh_due` checks the canonical and published result, not only the manifest time. | done |
| 4 | One `fitba update` orchestrator runs the same ordered steps locally and in CI; scouting and xG are explicit optional steps, and API-only steps are recorded as skipped without a key. | done |
| 5 | `--force-results` bypasses the results and SPFL caches in daily and post-match runs. | done |
| 6 | One shared matcher; the fixture publisher matches on canonical display names with a configured date tolerance. | done |
| 7 | All consumers read `load_matches`; the result consistency checks compare the derived surfaces. | done |
| 8 | New checks: `results.table`, `results.form`, `results.club`, `results.coverage`, `rules.epoch`, `rules.manifest`, `rules.checksums`. | done |
| 9 | Epoch fields stamped into every payload; array payloads covered by `manifest.files[]`; stale fallbacks keep the content id and name their reason. | done |
| 10, 11 | Manifest per-source freshness; `/status/` update and freshness cards. | done |
| 12 | Documented limitation: no last-good themes document is persisted; the case publishes an explicit unavailable state, never an empty success. | open, labelled |
| 13 | `scripts/check_freshness.py` verifies checksums, listing and epoch; the consistency manifest checks run at publish. | done |

## Values corrected

| Field | Before | After |
|---|---:|---:|
| Aberdeen table played / lost / GF / GA / GD | 9 / 4 / 10 / 10 / 0 | 10 / 5 / 12 / 13 / −1 |
| Aberdeen form | `WLDWD` | `LWLDW` |
| Premiership coverage vs table | 55 vs 54 | 55 vs 55 |
| Manager record played / last match | 9 / 2026-10-17 | 10 / 2026-10-24 |

No formula, denominator, rounding mode, source layer or parameter changed. See
`docs/metric-changes.md` entry 3.8.0.

## Limits

The overlay covers Aberdeen league fixtures only. A provider result for another
club is not corrected from the Aberdeen club feed. Optional sources may still be
late; they are labelled with their age and never block a correct result from
publishing. The canonical results layer cannot detect a provider result that is
missing from both football-data and the official club feed; the result audit
records the official fixture count so such a gap is visible.
