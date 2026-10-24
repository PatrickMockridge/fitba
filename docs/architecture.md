# Architecture

**Status:** describes the implemented pipeline and the planned cup layer. Last
reviewed 2026-10-24.

## Pipeline

```text
licensed/source adapters
        │
        ▼
data/normalized (parquet, gitignored)
        │
        ▼
DuckDB warehouse + analytics marts
        │
        ▼
fitba publish (atomic JSON, checksums, manifest)
        │
        ▼
web/data/generated (committed)
        │
        ▼
Next.js static app (Vercel)
```

Raw payloads live in `.cache/`; normalized data and the warehouse live in
`data/`; both are gitignored. Only derived JSON in `web/data/generated/` is
committed.

## Implemented today

- **football-data.co.uk** adapter: SPFL league results (SC0–SC3).
- **API-Football** adapter: licensed League Cup and Scottish Cup fixtures,
  rounds, penalty scores, lineups/events and covered player stats.
- **SPFL club feed** adapter: Aberdeen's league and League Cup fixtures/results
  from the club page (transitional).
- **AFC news** adapter: headlines, categories, dates and links from the official
  listing.
- **Transfers/loans**: player registry, API-Football candidate feed, curated
  register, `/transfers/` and `/loans/`.
- **Historical record**: curated era, staff, honours and season reviews;
  historical transfer windows from 2019-20; a bounded lineup/statistics
  backfill; `/history/` and one `/history/<season>/` page per season. The
  source of truth is `reference/history/` and `docs/history.md`.
- **Rumour mill**: curated `reference/rumours.yaml`, publication, `/rumours/`,
  a separate advisory recruitment profile and the news/rumour bridge.
- **Fan signal**: AFC Chat Rumour Mill RSS plus sampled first pages; gazetteer
  name extraction, cross-reference labels and rule-based VADER sentiment. Raw
  post text stays in the gitignored normalized store.
- **Squad and player profiles**: current API squad plus current loanees out,
  current-season per-competition stats, explicit unavailable/partial coverage,
  `/squad/` and one static `/players/<id>/` page per player.
- **Player-link spine**: `PlayerLinkIndex` builds `player_href` and
  `player_mentions` for transfers, rumours, forum signals and news, so current
  players link to their profiles everywhere.
- **Ingestion**: normalized match partitions, club fixtures, news; upsert and
  dedupe by match/article ID.
- **Analytics**: flat league tables with points, goal difference, form,
  head-to-head, deductions, split handling and validation.
- **Publication**: league table JSON, Aberdeen club payload, search index,
  coverage, seasons, manifest; atomic swap.
- **Web**: home, matchday dashboard, pyramid, tier pages, fixtures, news,
  scouting/loans method pages, methodology, status.

## Cup layer (implemented, with a licensed coverage limit)

- **API-Football** adapter (licensed, key-tested 2026-10-21) for League Cup
  groups/knockout, Scottish Cup rounds, lineups, basic player stats and
  transfers/loans.
- **Cup ingestion**: normalized `data/normalized/cups/{slug}.parquet` with
  round, round order, group, scores, extra time, penalty scores and status.
- **Cup analytics**: group tables with the 3/1 + shoot-out bonus rule, best
  runners-up, round ordering and knockout progression.
- **Publication**: `competitions/index.json`, `competitions/league-cup.json` and
  `competitions/scottish-cup.json`. The index is limited to Aberdeen's current
  league and cups; European entry is checked separately from
  `reference/european_competitions.yaml`.
- **Web**: `/competitions/`, `/competitions/league-cup/`,
  `/competitions/scottish-cup/`; `CupGroupTable`, `CupRound` components.

**Coverage limit:** the licensed League Cup feed is complete (80 group + 8 R16 +
4 QF + 2 SF) but has no standings, so group tables are computed. The Scottish
Cup feed covered 50 of 136 ties (First and Second Round) at the key-test; the
page shows the official round structure and labels every missing round. Current
lower-tier player stats were empty at test time; lineups/events are available.

## Source adapters

| Adapter | Status | Role |
|---|---|---|
| `sources/football_data_uk.py` | Implemented | League results; local validation cross-check after migration. |
| `sources/spfl.py` | Implemented | Aberdeen club fixture/results page; public fallback/cross-check. |
| `sources/afc.py` | Implemented | AFC news listing metadata. |
| `sources/api_football.py` | Implemented | Licensed source for cups, transfers/loans, team-sheet lineups and starting-XI roles, events and covered player stats; league migration pending. |
| `ingest/career_roles.py` | Implemented | Capped, resumable historical lineup backfill for career role eligibility. |
| `ingest/matchday.py` | Implemented | Bounded next-opponent fixtures, lineups and events snapshot with cache/stale fallback. |
| `normalize/career.py` | Implemented | FM-style slot aggregation, primary/secondary/stretch tiers and the display-role rule. |
| `sources/pannadata.py` etc. | Not public | Local-only research; never published. |

## Publication payloads

Implemented:

- `tables/{slug}-{season}.json` — league table, cut-offs, qualification note.
- `clubs/aberdeen.json` — summary, results, fixtures, competitions, news,
  history, and the kick-off shape/balance view.
- `squad/aberdeen.json` — squad, current role, career eligibility and
  playing-time blocks, current-season provider stats, position context and
  preferred-foot provenance.
- `players/<id>.json` — the typed player-page result: identity plus Profile,
  Availability, Position, Playing time, Performance, Recent matches and
  Records panels, validated against `contracts/player-page.schema.json`. The
  Profile panel carries the two Nightingale rose figures, summary facts and the
  catalogue; current squad members also carry the availability projection and
  recent match log.
- `search-index.json`, `coverage.json`, `seasons.json`, `manifest.json`.

Implemented:

- `competitions/index.json` — all six competitions, status, stage, links.
- `competitions/league-cup.json` — format, computed groups, qualifiers and
  knockout rounds.
- `competitions/scottish-cup.json` — official round structure, covered ties and
  explicit missing-round coverage.
- `transfers/aberdeen.json` — confirmed permanent, loan and free moves, window
  summaries, fee basis and inferred ranges, sell-on clauses, a plausibility count
  and verification links, with per-window audited/curated coverage and expected
  windows from 2019-20.
- `history/aberdeen.json` — era, strategic pillars, staff stints and manager
  records, full honours, season references, era scorecard, coverage matrix and
  sources.
- `history/seasons/<season>.json` — typed season review: manager segments, cup/
  Europe runs, recruitment aggregates, style proxies, selection metrics,
  academy debuts, staff changes, the labelled "The read" and coverage. League
  numbers are joined from `clubs/aberdeen.json`; transfer and honour facts are
  referenced by id.
- `matchday/upcoming.json` — typed upcoming-matchday document: next fixture,
  both teams' form and home/away splits, style lean, strength percentiles,
  predicted XIs with contenders, the matchup read and coverage. Opponent
  lineups come from the bounded `data/normalized/matchday/` snapshot; league
  facts join from the tables and club payload at build time.
- `analysis/summary.json` — Season overview: current table/form, next three
  fixtures, official and derived availability, season aims, factual
  squad-decision lenses and bridges. Built from local payloads and the merged
  season schedule.
- `themes/aberdeen.json` — the retained case archive used by the compact
  matchday evidence strip; it is not rendered on `/analysis/`.
- `fixtures/index.json` — played rows with score, depth and link plus a
  `scheduled` array for the remaining schedule. Built from
  `normalize/fixture_registry.py` and `normalize/schedule.py`.
- `matches/<fixture_id>.json` — one document per played fixture: score, summary,
  stats, fxG, timeline, lineups, player stats, form and coverage. Events and
  lineups come from the normalized history backfill; league stats join from the
  team-stat mart.
- `xg/aberdeen.json` — fxG model card, rates, intervals, provider comparison,
  aggregates and coverage. Built by `analytics/xg.py`; no new network ingest.
- `provenance.json` — layer-by-layer source truth table, migration gate state
  and source contributions. Built from `config/provenance.yaml`.
- `availability/aberdeen.json` — curated team-news ledger and optional provider
  snapshot; out/doubtful/suspended/returned/unknown states with source and
  `verified_at`.
- `needs/aberdeen.json` — seven role-family needs with cover/replace/strengthen
  categories, measured depth, market routes and roster caveats. No targets.
- `rumours/aberdeen.json` — curated rumours, status/confidence/source counts and
  opinions; separate from the confirmed register.
- `rumours/profile.json` — advisory position/age/league/value profile from active
  curated links, weighted by confidence and recency.
- `forum/afc_chat.json` — sampled topics, name signals, cross-reference labels
  and aggregate sentiment; no raw posts or usernames.
- `squad/aberdeen.json` — roster, loan tags, per-competition stats, totals,
  coverage states and player hrefs.
- `search-index.json` also carries player entries.

## Web structure

```text
web/app/
  page.tsx                 home (two doors + bridge)
  matchday/                upcoming-matchday dashboard
  analysis/                Season overview: fixtures, availability, aims, squad decisions
  recruitment/             off-the-pitch hub + squad needs board
  scouting/                method + priority role profiles
  sources/                 layer truth table and source policy
  rumours/                 rumour register, profile and fan signal
  squad/                   current squad and loan board
  players/[playerId]/      static player profile pages
  scotland/[tier]/         league pages
  clubs/aberdeen/          moved notice (old club dashboard retired)
  fixtures/                Aberdeen results/fixtures
  history/                 the Cormack era index, timeline and honours
  history/[season]/        typed season reviews
  news/                    AFC news listing
  competitions/            index
  competitions/league-cup/ full League Cup page
  competitions/scottish-cup/ Scottish Cup page (partial feed labelled)
  scouting/, loans/        method/empty states
  methodology/, about/, sources/, status/
```

Components: `LeagueTable`, `FixtureList`, `CompetitionStrip`, `NewsGrid`,
`CupGroupTable`, `CupRound`, `TransferCard`, `TransferBoard`, `RumourCard`,
`RumourBoard`, `ForumSignalPanel`, `SquadBoard`, `PlayerLink`, `BucketBars`,
`StatTile`, `FormStrip`, `HistoryTimeline`, `HonoursCabinet`,
`ManagerRecordTable`, `PredictedLineupPanel`, `PitchLineup`, `FormGuide`,
`StyleMatchup`, `StrengthComparison`, `MatchupRead`, `ConfidenceBadge`,
`KickoffNotice`, `ThemeCard`, `ThemeMetrics`, `FamilyBalanceChart`,
`ShapeSplitTable`, `DepthChart`, `BalancePanel`, `MissionPanel`, `NeedsBoard`,
`PriorityProfiles`, `AvailabilityBadge`.

## Refresh cadence

The data cadence runs on the operator's machine with the gitignored `.env` key;
GitHub Actions has no API-Football key and its data workflows are manual only.

- **Daily:** cron at 06:17 local time runs `scripts/local_update.sh daily`:
  current-season ingest, match detail, matchday, squad, availability, build,
  validation, publication and checks. It commits the generated payloads and
  pushes to `main`.
- **Post-match:** cron runs `scripts/local_update.sh matchday` every two hours.
  The gate compares the committed fixture schedule and manifest; when a
  scheduled Aberdeen fixture has finished and the manifest predates that
  finish, the full daily path runs. Empty checks do no data work.
- Both jobs only run when the checkout is on `main`; logs are written to
  `~/.local/state/fitba/update.log`. `scripts/install_local_cadence.sh` installs
  the two cron entries.
- The data push triggers the Pages deployment through the normal `main` push
  or the existing `workflow_run` hook for manual updates.

## Documentation book

The documentation is a local mdBook built from the same Markdown as the
repository docs:

```text
docs/*.md, docs/context/*.md  canonical documentation
docs/SUMMARY.md               chapter order
book.toml                     mdBook configuration (src = "docs", output = "book/")
theme/                        local template, head, palette overrides
book/                         generated output; gitignored, not deployed
```

`mdbook build` builds `book/`; `mdbook serve` previews it locally. The book is
not copied into the Pages artifact and is not a route on the website.

The Markdown remains the source of truth. The book has no independent payload
and no independent numbers; reader scenarios are still browser-only and the
published registry/audit remain the source of published values.

## File map

```text
config/            sources, competitions, cups, matchday, themes (case archive), publication, scouting, Aberdeen
reference/         teams, loans, market values, disciplinary
reference/history/ era, staff, honours, markets and season reviews
src/fitba/
  sources/         one adapter per source
  ingest/          fetch, normalize, cache, upsert (incl. squad stats)
  normalize/       names, teams, coordinates
  analytics/       tables, cup tables, style, scouting, loans
  publish/         atomic JSON and manifest
  validate/        contracts, checks, publication guard
sql/               DuckDB views
contracts/         dataframe and publication schemas
scripts/           source probes, publication/doc guards
tests/             parsers, arithmetic, fixtures
web/               Next.js app
data/, .cache/     gitignored
```

## Invariants

1. No raw source payload or full proprietary feed is committed. Forum post text,
   usernames and quotes never enter the published payload.
2. Every published file has a manifest entry and checksum.
3. Publishing is atomic; a failed validation leaves the previous dataset intact.
4. Team and player resolution is explicit; unresolved names are reported, never
   silently dropped.
5. A source can be disabled in `config/sources.yaml` and the app rebuilt.
6. Cup group tables are computed and labelled, not scraped from a third party.
7. An unpublished draw is a state, not an invented fixture.
8. Event-reconstructed visuals are labelled and never presented as tracking.
9. The historical record keeps one fact in one home: league rows join from the
   club payload, and season documents reference staff, honours and transfers by
   id. The history guard rejects duplicated league facts in the index.
10. Club display names are canonical or conservatively title-cased. Resolved
    Scottish clubs use `reference/teams.yaml`; `ST Johnstone` and
    `St. Johnstone` display as **St Johnstone**. `scripts/check_names.py`
    rejects all-caps Saint spellings and lower-case place names.

## Migration to one licensed source

After the API-Football key-test passes:

- public league results and fixtures move to API-Football;
- football-data.co.uk becomes a local validation cross-check only;
- the SPFL/AFC fixture scrapers leave the public path;
- the AFC news listing remains (headline/link metadata);
- raw API payloads stay in the gitignored cache.

## Testing

- Parsers are pure functions with HTML/CSV fixtures in `tests/fixtures/`.
- Table arithmetic and cup group tables are tested on in-memory frames.
- Publication guard checks size, provenance and tracked raw data.
- Doc check verifies links and the key competition-format facts.
- `mdbook build` is the docs book build check.
- `npm run build` is the end-to-end static build check.


## Former-player modules

- `normalize/transfer_history.py` — provider transfer type parsing and event
  sequencing.
- `analytics/former_players.py` — universe, Aberdeen tenure, post-career record,
  sell-on watch and development scorecard.
- `analytics/affiliation.py` — canonical affiliation for rumours, forum signals
  and needs.
- `ingest/former_players.py` — bounded/cache-first backfill and refresh.
- `publish/former_players.py` — strict result documents for
  `former-players/aberdeen.json` and `former-players/seasons.json`.
