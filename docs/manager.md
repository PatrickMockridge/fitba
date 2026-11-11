# Manager record

**Status:** live. Last reviewed 2026-11-11.
**Route:** `/manager/`.
**Nav and H1:** Manager / The manager record.
**Payloads:** `history/aberdeen.json`, `history/seasons/<season>.json`,
`analysis/summary.json`, `xg/aberdeen.json`, `clubs/aberdeen.json`,
`forum/donstalk.json`.
**Guards:** `scripts/check_manager.py`, the `manager.records` consistency check,
`scripts/check_web_contract.py`.

## Purpose

The Cormack era's recurring story is manager churn and the pressure cycle around
it. Before this page, that story was split across `/history/` (register and
records), `/history/<season>/` (the season segment), `/analysis/` (season aims),
`/claims/` (the manager claim), `/rumours/` (next-manager market and fan signal)
and `/news/`.

`/manager/` consolidates the current manager situation without inventing a new
judgement:

1. the current permanent, interim or vacancy state;
2. the analyst-set season expectations and the three season aims;
3. the measured record at full-stint and within-season scope;
4. the fxG manager split as descriptive context;
5. the full Cormack-era churn, stint by stint;
6. links to manager news, the rumour mill, the gated market and the DonsTalk
   thread.

It is a **projection of published payloads**. It adds no manager rating, no
per-manager target, no tenure-day calculation, no interim count and no causal
verdict. Where a manager has no league match, the record is a zero sample, not a
zero-performance verdict.

## Sections

1. **Hero** — the current state in one sentence, with a vacancy/interim badge,
   a league-only scope badge and the corpus as-of date.
2. **Current situation** — manager status, league position and goal difference,
   the last permanent manager's full-stint record, the next fixture, and the
   club statement link where the season document publishes one.
3. **Season expectations** — baseline, target and context from the current
   season document, labelled **Analyst-set, not a published club target**, with
   visible sources.
4. **Season aims** — Aim, Target, Current, Status and Gap from
   `analysis/summary.json#/aims`. A null gap is labelled unknown, never zero.
5. **Measured manager record** — the full-stint league records for the managers
   in the current season, with interim spells separate, the measured-context
   note and the zero-sample note. League only.
6. **2026-27 segment** — the within-season league segment from the season
   document. The caption makes the scope explicit: a segment is not the full
   stint, because the full stint can include earlier seasons.
7. **fxG context** — the current-season manager split from
   `xg/aberdeen.json#/manager_splits`. Descriptive, not a causal verdict. An
   empty split is a visible unknown state.
8. **Cormack-era churn** — every manager stint overlapping the era, including
   interims and pre-era starts: Manager, Dates, Reason, Pld, W-D-L, GF, GA, Pts,
   PPG. The manager count is distinct people with at least one league match; the
   table also shows zero-match stints.
9. **Manager headlines** — up to five AFC news items whose title names a
   published manager, `manager` or `head coach`, newest first. Listing metadata
   only; article bodies are not copied.
10. **Next manager and fan signal** — link-only to `/rumours/` and the DonsTalk
    Next manager thread. No odds table and no candidate numbers are duplicated.
11. **Coverage and method** — league-only scope, the zero-sample rule, the
    analyst-set expectation rule, the fxG/model boundary, the news boundary, the
    gated-market boundary and the source links.

## Rules

- Manager records are league-only. Cup and European results are curated exit
  rounds on the season pages and are not counted in a manager record.
- A match in a gap between stints is not assigned to the nearest manager.
- Interim spells are separate stints. A zero-match interim stays in the staff
  register and the table with Pld 0 and no PPG.
- Season expectations are analyst-set. They are not a club target and not a
  per-manager target.
- The next-manager market stays on `/rumours/`. Its single-snapshot odds,
  candidates and counts are not repeated here.
- No pressure language, sacking verdict, rating or causal judgement is
  published.
- News rows are links and dates only.

## Failure states

- Missing `history/aberdeen.json`: the page renders the empty state
  (`data-contract="manager.empty"`) with the publish instruction.
- Missing season document, aims, news or xG rows: the relevant section keeps its
  marker and renders a visible unknown or empty state with the links intact.
  Nothing is zero-filled.

## Contract markers

`manager.hero`, `manager.situation`, `manager.expectations`, `manager.aims`,
`manager.record`, `manager.season-record`, `manager.xg`, `manager.churn`,
`manager.news`, `manager.rumours`, `manager.coverage`; empty state
`manager.empty`. The registered metric values shown are the history scorecard
and staff, the season document, the season overview, the fxG document and the
club news payload.
