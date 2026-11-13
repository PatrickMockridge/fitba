# The Cormack-era historical record

**Status:** implemented. Last reviewed 2026-10-21.

This document defines the `/history/` layer: what it records, how each panel is
produced and what it deliberately does not claim. It is the companion to
[the trading model](trading-model.md), [Season overview](analysis.md) and
[the methodology](methodology.md).

## Purpose

The site's argument is that Aberdeen have run a trading model — buy low,
develop, sell high, reinvest in young players — and that the model can produce
both a Scottish Cup and volatile league form. The history layer makes that
argument inspectable season by season.

A manager change is a stint boundary. When the current manager is interim and
no permanent manager is in post, the page says so visibly; an interim with no
league match is shown with Pld 0 and an Interim badge. It is not a defence of
the model or a verdict on any manager or player. It puts
the measured record, the curated public facts and a clearly labelled assessment
side by side.

## Scope

- **Era:** Dave Cormack became chairman on **16 December 2019** (announced during
  the November international break). The detailed record starts with 2019-20,
  which is labelled a transition season because it began under Stewart Milne.
- **Seasons:** 2019-20 through 2026-27. Completed seasons have an end-of-season
  review; 2026-27 is `in_progress` and has no final verdict.
- **Staff:** key named football-operations and board roles only — manager/head
  coach, assistant, first-team coach, goalkeeping coach, sporting director,
  head of recruitment, academy director, CEO, chair and named board changes.
  This is not a full staff directory. The index shows the current key staff and
  keeps the full appointment/departure timeline collapsed by default; the
  season pages show the changes within each season.
- **Honours:** the full major register — four league titles, eight Scottish
  Cups, six League Cups, the 1982-83 European Cup Winners' Cup and the 1983
  European Super Cup.
- **Transfers:** 2019-20 onward. The recent four windows are audited against the
  seniority policy; earlier windows are curated partial.
- **Style and selection:** measured from football-data.co.uk match rows and the
  historical lineup backfill. Possession/pass accuracy only if the provider
  team-statistics backfill is available.

**Not in scope:** the scouting/fit model. The history records the pattern and
outcome of signings — source market, age, known fee, minutes and role — not a
player-level "undervalued" score. Quantifying outperformers in poor teams is the
next piece.

## Measured, curated, assessed

Every panel follows the site-wide taxonomy:

- **Measured:** league records, manager W-D-L (league-only), shots/corners/fouls/
  cards, formations, minutes, ages where a roster or birth date is known.
- **Curated:** staff stints, honours, cup/European exit rounds, expectations,
  academy debuts, source-market mapping, season narrative.
- **Inferred:** the era averages and comparisons; labelled as such.
- **Assessment:** "The read" — an argument based on the public record, not a
  measurement and not the club's internal view.

Numeric league facts are not stored in the history payload; the one exception is
the quoted club-accounts block, which is curated external data rather than a
league fact. The web joins `clubs/aberdeen.json` `history` by season. Manager
career records live on the index staff stints; season documents hold only the
season segment. The manager
records are computed from the same canonical result frame as the league table,
so their played/won/drawn/lost/GF/GA/points totals and latest match date must
equal the table row.

The index also carries two visible measured blocks: defeats by four or more
goals (date, season, competition, opponent, score, match link) and European
campaigns (competition, stage reached, outcome). They are not left in prose.
Season and player totals use competitive matches; friendlies are excluded and
labelled separately.

## One fact, one home

| Fact | Canonical home |
|---|---|
| League season row | `clubs/aberdeen.json` `history` |
| Transfer row | `transfers/aberdeen.json` |
| Staff stint | `history/aberdeen.json` `staff` |
| Honour | `history/aberdeen.json` `honours` |
| Manager career record | the staff stint |
| Season manager segment | `history/seasons/<season>.json` |
| Style/selection/recruitment aggregates | the season document |
| Club-account headline lines | `reference/history/finances.yaml` → `history/aberdeen.json` `finances` |
| Season narrative and "The read" | the season document |

The index `seasons[]` rows contain references and navigation metadata only. A
guard rejects `position`, `points`, `played`, `gf` or `gd` in those rows.

## Data files

```text
config/history.yaml                    policy, expected totals, backfill caps
reference/history/era.yaml             era definition and strategic pillars
reference/history/staff.yaml           people and stints
reference/history/honours.yaml         full major honours
reference/history/markets.yaml         source-market map for recruitment
reference/history/finances.yaml        quoted club-account headline lines
reference/history/seasons/<season>.yaml
```

The season YAML carries the headline, expectations, cup/Europe runs, honour
references, key-transfer references, academy debuts, tactical notes, the
review and the sources. League numbers are computed.

## Manager records

- Every match in the SPFL league competition the club is in that season is
  assigned to the manager stint covering its date. The scan covers all four
  tiers, so a future relegation does not break the record.
- Stint dates are curated at day, month, year or season precision. A
  month/year boundary is marked as boundary-ambiguous; the record does not
  invent a day.
- A match in a gap between stints is `unattributed`, never assigned to the
  nearest manager. Boundary days are assigned once, not double-counted.
- Records are **league-only** by default. Historical cup data is incomplete;
  mixing a full league with a partial cup sample would mislead. Cup and European
  outcomes are curated exit rounds.

## Club accounts

The page publishes five headline lines from the filed group accounts for
FY2021–FY2025, quoted with attribution from
[PSRwatch's Aberdeen financials](https://psrwatch.com/club/sco-aberdeen/financials):

- revenue;
- staff costs;
- profit on player disposals;
- pre-tax result;
- net debt.

It also derives **net registration investment**: the change in player-registration
cost less profit on disposals. This is an accounting measure, not cash transfer
spend or the transfer-register net. It is shown for FY2022–FY2025; FY2021 is
unknown because the FY2020 opening registration cost is not in the source table.

FY is the year ended 30 June. FY2021 maps to 2020-21 and FY2025 to 2024-25.
Revenue, staff costs and pre-tax result are £m to one decimal; profit on player
disposals, net registration investment and net debt are £m to two. Negative net
debt means net cash. Staff costs are the filed aggregate, not individual wages, a
wage structure or a budget.

The underlying record is the Companies House filing history for Aberdeen
Football Club Limited (SC005364). fitba does not fetch, bulk-ingest or
republish the PSRwatch table and has not independently audited the accounts.
FY2020 (2019-20) and FY2026 (2025-26) are not in the source table; they are
unknown, never zero, and no row is interpolated.

## Style and selection

**Style** is measured from football-data.co.uk league rows:

- shots for/against per match, shots on target, shot accuracy, goals per shot;
- corners, fouls, yellow and red cards;
- possession/pass accuracy only if the provider team-statistics backfill exists.

These are opponent-unadjusted team proxies, not xG and not a tactical model. A
missing stat is unknown, not zero.

**Selection** is measured from the historical lineup backfill:

- formation mix at kick-off;
- players used, average starter age, U21 minutes share, minutes by age band;
- new players/debutants, with `debut_basis: covered_history` — first appearance
  in the covered record, not career debut;
- top 11 by starts, which is not a claim that those players started together.

Ages come from the season roster or a known birth date. Below 60% lineup
coverage is `partial`; no lineups is `unavailable`. Missing ages are excluded
and the coverage fraction is shown.

## Historical transfers

- The daily ingest keeps its 2024-05-01 candidate cutoff.
- `fitba history --backfill-transfers` writes a historical candidate file from
  the full API-Football transfer history.
- Senior moves are curated against the Wikipedia season tables and AFC
  announcements. Pre-2024-25 windows are `curated_partial`, not audited.
- `config/history.yaml` carries a small `required_moves` list for defining
  business (McKenna, Ramsay, Ferguson, Miovski). It is a recall net, not a
  completeness claim.
- Fees are usually undisclosed. Disclosed/reported amounts are anchors; other
  permanent moves carry an inferred range with a confidence label. The aggregate
  is an inferred net range, never an audited balance. Free transfers count as
  zero fee; loan fees are excluded.
- Sell-on clauses are tracked in `reference/sell_on_clauses.yaml` and shown on
  `/transfers/`; confirmed clauses carry an allowed source, reported clauses are
  labelled unverified.

## Backfill commands

```bash
uv run fitba history --status
uv run fitba history --probe --season 2019-20
uv run fitba history --backfill --season 2019-20 --max-requests 200
uv run fitba history --backfill --from-season 2019-20 --to-season 2025-26
uv run fitba history --backfill-transfers
```

The backfill is bounded, cached and resumable. It is manual/local; the daily
publish never calls a provider. Raw API payloads stay in the gitignored cache.
Lineups, rosters and team statistics live in `data/normalized/history/` and are
gitignored.

## Coverage

The index publishes a coverage matrix by season and layer. At the last check:

- league record: measured for all seasons;
- transfers: audited 2024-25 onward, curated partial before;
- lineups: available or partial for all 2019-20..2026-27, with the per-season
  fraction shown;
- match stats: measured league proxies for all seasons;
- reviews: complete for 2019-20..2025-26, in progress for 2026-27.

Known gaps:

- The 2023-24 League Cup was a runners-up finish, not a major honour. It appears
  as a cup run on that season page.
- 2019-20 began before Cormack and was curtailed; the review labels both.
- Manager records are league-only.
- Club accounts cover FY2021–FY2025 only; FY2020 and FY2026 are unknown.
- Pre-2024-25 transfer windows are curated partial.
- The 2025-26 European league-phase finish (35th of 36) is a curated season
  record, not a provider-measured table and not a season verdict.

## Sources

- **AFC official:** preferred citation for staff, honours, appointments and
  season records.
- **Wikipedia:** last-resort citation for historical managers, honours, cup and
  European runs, and season records where no AFC page states the fact.
- **API-Football:** fixtures, lineups, events, rosters and transfers.
- **football-data.co.uk:** league results and match-stat proxies.
- **PSRwatch:** the citation-lane compilation of the filed club accounts; only
  the five quoted headline lines are published.
- **Companies House:** the underlying filing history for Aberdeen Football Club
  Limited (SC005364), linked as the primary record and not re-keyed.

BBC, Transfermarkt and other `no_publication` sources may be read manually as a
finding aid, but are never fetched automatically, cited or republished. The
guard rejects their ids and hosts.

## Corrections

If a source, role, date or result changes, update the reference YAML, the
season document, this document and the in-app page in the same change. Do not
leave a stale claim in one place and fix it in another.

## Cormack-era lookup

`/history/` carries a lookup over the published season index, staff stints and
honours. It filters by season, manager, honour and competition and links to the
matching season pages; state lives in the URL hash so a view can be shared. The
lookup only navigates published rows. It does not rank seasons, add a
superlative or replace the season table, manager records or honours cabinet,
which stay visible.
