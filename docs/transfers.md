# Transfers and loans

**Status:** live for Aberdeen. Last reviewed 2026-10-21.

This document defines the confirmed-business register and its limits. The
machine-readable data is `reference/transfers.yaml`; the feed suggestions are
`reference/transfers.candidates.yaml`, a local review artifact that is
gitignored and never published.

## Confirmed business only

A row is in the public register only when it is a completed move and has a
verification record:

- **confirmed** — a licensed API-Football transfer record plus an official club
  announcement.
- **curated** — a licensed-feed record cross-checked against the Wikipedia
  season table; an official announcement is linked where one was found.
- **feed_only** — a feed record with no official confirmation; held in the
  candidates file and **never published**.
- **reported** — media-only; never published.
- **rejected** — duplicate, noise or not a transfer; never published.

There is no “in talks”, “medical pending” or rumour state in this register.
Unconfirmed links live in the separate [rumour mill](rumours.md), which is
curated and source-linked. A rumour becomes `confirmed` only by pointing at a row
in this register; the transfer register never imports rumour rows and the two are
published separately.

## What the licensed feed provides

API-Football `/transfers?team=252` returns **273 player records** for Aberdeen
(full history, one response, updated 2026-10-19). Each move is only:

```text
date, type, teams.in {id, name}, teams.out {id, name}
```

- **No fee field.** Some fee text is stuffed into `type` (`€ 1M`, `355K`), but
  it is inconsistent and not authoritative.
- **No loan end date, recall, obligation or option.** Loan terms must be curated.
- **~85–90% senior coverage.** A few senior moves are missing (e.g. Mouloua and
  Lewis Smith in; Keskinen and Kjartansson out in 2026/27) and about 16
  youth/Highland loans are absent.
- **Duplicates and date drift.** Announcement and registration dates can differ
  by days or weeks; the register keeps both dates and dedupes.
- **Pseudo-teams.** Out-of-contract players can appear with a “club” named after
  the player; these are normalised to free-agent departures.
- **Noise types.** `Raise`, `Swap`, `End of career` and youth U20 entries are
  filtered.

## Fee policy

- Fees are **curated only**. The feed’s fee-like strings are hints, not authority.
- Unknown or undisclosed fees are `fee_status: undisclosed` and display as
  **Undisclosed**. They are **never** stored as zero and never included in net
  spend.
- Free moves are `free`; loans are `loan`.
- Net spend is shown only for disclosed fees, with an explicit undisclosed count.
- Wages, sell-on percentages, instalments and agent fees are not public; they
  remain unknown.

## Loan policy

- Loans in and out are part of the register.
- `loan_end_date`, `recall_clause`, `obligation_to_buy` and `option_to_buy` are
  null/unknown unless an official source records them.
- Loan returns are recorded as `loan_return` rows. They appear in the register
  and in departure counts, but not in permanent-transfer counts or loan-in/out
  tiles.
- Lower-tier loan minutes use lineups/events where the feed covers the club, and
  a curated match log otherwise; the tier coverage is labelled.
- The current squad page (`/squad/`) joins the register to the squad and tags
  current loanees. Loan-club stats are shown when the licensed feed covers that
  club and are marked unavailable otherwise; see [squad.md](squad.md).

## Seasons and windows

The register covers 2019/20 through 2026/27. A summer deal in May/June belongs
to the season starting that year; winter deals belong to the season that started
the previous July.

The recent four windows are **audited** against the seniority policy. Earlier
windows are **curated partial**: they are built from the full API-Football
candidate history and the Wikipedia season tables, but they have not had the
same season-snapshot audit. The payload carries a per-window `coverage` field and
an `audited_from` date.

The page groups windows by their actual place in the calendar:

- **Recent** (default) — Summer 2026, Winter 2026, Summer 2025, Winter 2025.
- **Further back** — Summer 2024 and older summer/winter windows, including
  Summer 2019, which predates Cormack's chairmanship and is labelled `pre_era`.
- **Out of window** — moves after the winter window closed, such as Nilsen and
  Bwomono in March 2026. They are not dropped from the register.
- **Upcoming** — an expected window with no rows yet, so it does not silently
  disappear.

Each group has an “all” view and a per-window selector. Direction and deal-type
filters apply within the selected view. `window_groups` in the published payload
holds the group membership; the UI resolves it against `windows`.

Historical candidates are built separately so the daily ingest stays small:

```bash
uv run fitba history --backfill-transfers
uv run fitba transfers
uv run fitba transfers --audit
```

## Club names

Displayed club names are canonical. Scottish clubs resolve through
`reference/teams.yaml`; for example `ST Johnstone` and `St. Johnstone` both
resolve to **St Johnstone**, and `ST Mirren` to **St Mirren**. Unresolved
provisional clubs are title-cased conservatively (`FC ST. Gallen` becomes
**FC St. Gallen**; `St. Louis City` is left as a proper name). The fallback
preserves short club acronyms such as FC, HJK, IBV and IFK.

`scripts/check_names.py` rejects all-caps `ST Johnstone`/`ST Mirren`,
lower-case place names and `FC ST.` spellings in published JSON and the
transfer registers.

### Provider corrections

`config/transfers.yaml` `candidate_exclusions` records provider rows that must
never enter the review files or the published register. Each entry carries the
`transfer_id` and a written reason; this is a correction, not a silent dedupe.
For example, API-Football merged the provider name "A. Morgan-Cummings" with
Aaron Cummings. `reference/players.yaml` now resolves that API id to **Aaron
Cummings**, and the false Potters Bar Town transfer is excluded. The real
Elgin City loan remains in the register.

## Positions

Every row has a position where an allowed source states one. The precedence is:

1. curated correction in `reference/transfer_player_positions.yaml`;
2. the current squad position;
3. the player’s season-specific API profile (transfer season, then up to two
   earlier seasons);
4. the current player’s career-role family;
5. explicit unknown.

`position_source`, `position_source_season` and `position_unknown_reason` are
published so an unknown is visible, not guessed. At this check 217 of 230 rows
have a position; the 13 unknowns are mostly youth/Highland loans with no
position in any allowed source. Pre-2024-25 rows without a curated position are
marked `historical_scope`; they are not profile-enriched from a current-season
record.

## Inferred fees and market values

Aberdeen's fees are usually undisclosed. The register therefore separates:

- **disclosed** — an exact amount stated by an allowed public source;
- **reported** — a fee reported in the Wikipedia season record or an AFC
  announcement, cited but not treated as an audited amount;
- **free** — zero transfer fee, but the player still has a market value;
- **loan** — the loan fee is unknown and excluded from the net;
- **modelled** — an inferred range, never a point estimate.

The model is deliberately simple and public:

1. a base value by source/destination market and position group;
2. an age curve (peak 24–27, discounts before 21 and after 29);
3. a calibration factor from the reported/disclosed fee anchors;
4. a per-row range of 0.6×–1.6× the modelled midpoint, with a confidence label.

The aggregate net range uses modelled midpoints plus a 20% portfolio band on
modelled gross flows, rather than adding every row's extremes. That avoids a
fake-precise or implausibly wide "net spend". Negative means income exceeds
spend. Free transfers count as zero fee; loan fees are excluded.

At the last check the model had 14 anchors and produced:
**−£21.4m to −£5.6m** across 2019/20–2026/27. It is an inferred range, not an
audited balance and not the club's internal valuation.

Manual calibration may use a restricted page as a private sanity check, but no
restricted value, URL or scraped table is published. The published anchors are
AFC/Wikipedia only. See [methodology.md](methodology.md).

## Sell-on clauses

`reference/sell_on_clauses.yaml` tracks clauses on Aberdeen's outgoing sales.
Each row records:

- the transfer, player and buyer;
- the percentage, or `null` when the clause is reported but the percentage is
  undisclosed;
- the basis (`profit`, `gross_fee` or `unknown`);
- confidence (`confirmed` or `reported`);
- source URLs or a `verification_aid` finding-aid label.

`confirmed` requires an allowed public URL. A `reported` clause may have no
allowed URL; the page labels it as unverified and does not link a restricted
source. A blank percentage is never inferred. The current register has Calvin
Ramsay's 17.5% (Wikipedia-confirmed), Lewis Ferguson's reported 20% and Bojan
Miovski's reported clause with an undisclosed percentage.

## Plausibility screen

A citation alone does not make a transfer real. A curated row is withheld when
it triggers at least three high-confidence flags:

- a permanent incoming move from an unknown/provisional club;
- no player profile or birth date in the covered record;
- no position;
- a Wikipedia-only citation;
- a hyphenated name that looks like two players merged, with no profile.

Withheld rows are not published. The public payload reports only the count;
the review queue is local. A reviewer can accept a legitimate row in
`reference/transfer_plausibility.yaml` with a reason, a public source and a
check date. `config/transfers.yaml` `candidate_exclusions` handles known
provider errors before they reach the review files.

## Completeness and seniority

The register must be complete enough that a missing move is a known, recorded
gap. Missing a 17-year-old on a development loan is tolerable; missing a regular
senior squad member is not.

| Tier | Rule | Expectation |
|---|---|---|
| Established senior | 5+ starts or 450+ minutes in the reference season, 10+ career starts, or a first-team number with an appearance | Should be in the register; a residual gap is prominent |
| Fringe senior | 1–4 starts or 1–449 minutes, or a squad number without an appearance | Should be accounted for |
| Youth/development | Under-21, fewer than five appearances, under 10 career starts | Best effort; a recorded gap is tolerated |

Thresholds are in `config/transfers.yaml`. Curated overrides can move a player
between tiers with a written reason.

`reference/transfer_gaps.yaml` is the ledger of expected moves that are not in
the register. It records direction, window, seniority, status (`open`,
`accepted`, `resolved`), reason, check date and a generic `verification_aid`.
An accepted or resolved row removes the player from the audit review queue; an
open row is reported but does not block CI.

`fitba transfers --audit` fetches bounded 2024-25 and 2025-26 Aberdeen
team-season snapshots, writes `prior_squads.parquet`, and builds the audit. The
daily publish reads the local snapshot and never calls the network. The audit
labels candidates **needs review**, not missing, because the provider snapshot
can omit injured or unregistered players. It is report-only.

## Current register (2026-10-21)

- 229 published rows across 19 windows with rows, plus one expected upcoming
  window. The recent four are audited; 2019-20..2023-24 are curated partial.
- 4 confirmed rows (official announcement linked); 225 curated against the
  Wikipedia season table or the API feed.
- 31 loans out and 31 loans in across the register.
- Fee basis: 2 disclosed, 12 reported, 69 modelled, 83 free, 63 loan.
- Inferred net range at this check: **−£21.4m to −£5.6m** (income exceeds
  spend), with 14 anchors. This is a modelled range, not an audited balance.
- 3 sell-on clauses: Calvin Ramsay 17.5% (confirmed), Lewis Ferguson 20%
  (reported), Bojan Miovski (reported, percentage undisclosed).
- Audit: no established or fringe senior moves awaiting review; one
  unclassified prior player remains. Nine gaps are accepted in the ledger
  (academy/development, a squad-list omission, a provider identity duplicate and
  the Aaron Cummings provider-name correction).

## Sources and guardrails

- API-Football is the licensed candidate feed; the player API id is the identity
  spine.
- Official AFC announcements and the Wikipedia season tables are the
  publication sources. Wikipedia is a finding aid, not an authority.
- A person may read BBC Sport, Transfermarkt or another public page to spot a
  missing move. That is fair use, not scraping. The page is never fetched
  automatically, cited or copied, and the move is published only when an
  allowed source independently confirms it. If no allowed source confirms it,
  it stays a gap with a generic `verification_aid`.
- `scripts/check_transfers.py` blocks feed-only/reported/rejected rows from the
  published payload, requires source URLs, rejects zero fees, validates the
  window groups and position provenance, and rejects a source not allowed for
  publication. Open gaps are reported, not failed.
- `scripts/check_publication.py` also rejects a source host not allowed for
  publication in any committed JSON.

## Known gaps

- The API feed is not 100% complete; curated rows fill the senior gaps.
  Mouloua, Lewis Smith, Frame and Bwomono in, and Keskinen, Kjartansson,
  Aouchiche and Nilsen out, were added from Wikipedia/AFC sources.
- Youth/Highland loans are incomplete in the feed and need official/Wikipedia
  curation. They are recorded as tolerated youth gaps rather than invented.
- Loan terms and most fees are unknown; the UI labels them rather than inventing
  them.
- Thirteen rows still have no position because no allowed source states one;
  each carries an explicit `position_unknown_reason`.
- One unclassified prior player remains in the audit review queue; no
  established or fringe senior move is outstanding.
- One provider duplicate identity (Gyamfi, `api:player:334359` and
  `api:player:550363`) is recorded in the gap ledger rather than silently
  merged; the current squad uses the latter key.
