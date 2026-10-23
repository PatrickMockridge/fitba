# Data provenance

**Status:** live. Last reviewed 2026-10-22.

`/sources/` publishes a layer-by-layer truth table from
`config/provenance.yaml`. The rule is simple: **a source is called primary only
for the layer it actually supplies.** The truth table is joined to the source
registry and to the actual row contributions, so the page and the manifest
cannot drift into a single flattering “API-Football is primary” claim.

## Current truth table

| Layer | Primary | Fallback / note |
|---|---|---|
| League results, current season | Football-Data.co.uk | API-Football only after the strict migration gate passes |
| League results, historical | Football-Data.co.uk | Back to 2013-14 |
| League team match stats | Football-Data.co.uk | Shots, corners, fouls and cards; API-Football does not supply every tier |
| League tables | Computed | Split, deductions and tie-breaks |
| League Cup / Scottish Cup fixtures | API-Football | Scottish Cup is partial; missing rounds are labelled |
| Aberdeen club fixtures | SPFL club feed | API-Football is a cross-check |
| Lineups, roles, starts | API-Football | Starting-XI grid and events |
| Player match stats and ratings | API-Football | Premiership, current season |
| Event-derived Aberdeen stats | API-Football | Lineups + events; not tracking |
| Current squad | API-Football | Curated player overrides for identity gaps |
| Preferred foot | Sportmonks (gated) | AFC official, then Wikipedia; 1 known / 37 unknown |
| Transfer candidate feed | API-Football | Discovery only; it has no fees or loan terms |
| Transfer register | Curated | AFC announcements + Wikipedia + API candidates |
| Loans | Curated | Loan tags; end/recall/obligation terms unknown |
| News | AFC official listing | Metadata only |
| Availability | Curated AFC team news | API-Football `/injuries` is optional; current season coverage false |
| Rumours | Curated | Source-linked; separate from confirmed business |
| Fan signal | AFC Chat sample | Derived aggregates; no raw posts |
| History | Mixed | API-Football backfill, Football-Data style, AFC/Wikipedia curation |
| Valuation | Curated anchors + model | Ranges and confidence |
| Season overview | Derived | Local match/squad/history data |
| Needs | Derived | Case evidence + availability + squad/transfers |
| Odds | Not published | No betting content |

## League migration gate

`config/league_migration.yaml` is disabled by default. The probe
(`scripts/probe_league_migration.py`) checks all four leagues for:

- the complete fixture list and team set;
- zero unresolved teams and duplicate keys;
- every Football-Data played result matched once;
- 1.0 score agreement;
- the team match stats the style/case layers need.

A partial pass does not migrate. The current report fails: the Premiership API
fixture list is short (198 vs 228), and the Championship/League One/League Two
statistics are not covered. Football-Data therefore remains primary for league
results and team stats, and the page says so.

## Manifest and coverage

- `provenance.json` lists every layer, its primary/fallback sources,
  contributions and row counts.
- `manifest.sources` is built from the provenance summary, not from a separate
  ad-hoc count. A source's rows are its **primary contributions only**.
- Curated transfer rows are not counted as API-Football rows. A gated source
  can appear with zero rows.
- Coverage now reports real fixtures-with-lineups and player-stat rows instead
  of hardcoded zeros.

## Adding a layer

1. Add the source to `config/sources.yaml` if it is new.
2. Add the layer to `config/provenance.yaml` with primary, fallback, scope,
   fields and status.
3. Add the row contribution in `publish()`.
4. Update the source page copy and this document.
5. Run `uv run python scripts/check_provenance.py`.

No source may be described as primary for a layer it does not supply.
