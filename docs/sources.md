# Data sources

**Checked:** 2026-10-24. Re-run `uv run fitba probe` before relying on any claim.
The machine-readable registry is `config/sources.yaml`.

## The public-source rule

Public data must come from a **licensed source** or an official club/federation
listing whose terms permit the use. We do not scrape BBC, FotMob, Sofascore,
Transfermarkt or FBref into the public app. A person may read a public page
manually as a finding aid; that is fair use. The restriction is automated
collection, citation and republication. Unlicensed event/tracking data may be
used **locally for prototypes** but never committed or published.

The target is one licensed base for all Scottish competitions. **API-Football
Pro is active** and key-tested on 2026-10-21. It is primary for cup fixtures,
lineups/roles, player match stats and the squad. League results and team match
stats remain on Football-Data.co.uk until the strict current-season migration
gate passes for both results and required stats; the layer truth table is in
[provenance.md](provenance.md) and is published at `/sources/`.

## Active licensed base: API-Football

| Item | Detail |
|---|---|
| Cost | Pro subscription; the provider's published price and plan limits should be checked at checkout, not treated as a site fact |
| Coverage | All four Scottish leagues, Scottish Cup and League Cup; the provider advertises 1,200+ competitions, but only the Scottish coverage below is key-tested |
| Fields | Fixtures, full-season team schedule, rounds, AET/PEN status, penalty scores, standings, team-sheet lineups with formation and starting-XI grid and named substitutes, events/cards, basic player stats, UEFA league-phase player appearances, transfers/loans |
| Gaps | **No preferred foot, event coordinates, heat maps, market values or wages**; provider xG is partial (`expected_goals` in some Premiership statistics responses; 2026-27 SC0 `HxG`/`AxG`), not a historical location model; League Cup **group standings are not provided**; Scottish Cup feed is partial; current lower-tier player stats were empty at test time; **current-season Scottish injuries coverage is false**, so `/injuries` is not used as a team-news feed; the season `/players` endpoint has no round dimension, so the UEFA league-phase flag uses per-fixture player data |
| Public display | Non-commercial apps/websites are contemplated in API-Sports terms; raw resale prohibited; derived pages fine. The provider does not grant underlying fixture IP; confirm terms in writing. |
| Key-test | Passed with gaps: see below |

### Key-test result (2026-10-21)

- **Scottish competition IDs:** Premiership 179, Championship 180, League One
  183, League Two 184, League Cup 185, Scottish Cup/FA Cup 181, Challenge Cup
  182, Highland League 730, Lowland League 731.
- **League Cup:** 94 fixtures — 80 group matches, 8 round-of-16, 4
  quarter-finals, 2 semi-finals; penalty scores present. **Standings response
  empty**; the app computes the eight group tables.
- **Scottish Cup:** 50 fixtures — 20 "Round of 128" (mapped to **Second Round**
  by date) and 30 "1st Round" (**First Round**). The official format has 136
  ties; the preliminary rounds and later rounds are not provided.
- **European league phase:** the 2026-27 Champions League, Europa League and
  Conference League league phases are covered through their fixtures and the
  per-fixture player endpoint. Qualifiers and play-offs are excluded. The
  season `/players` endpoint mixes them, so it is not used for the flag.
- **Player stats:** Premiership and top European leagues (Eredivisie, Swiss
  Super League, Danish Superliga, Portuguese Primeira Liga, Belgian Pro League,
  Hungarian NB I) return player stats. Championship, League One, League Two,
  League Cup and Scottish Cup returned 0 for the current season at test time;
  the 2025 and 2024 lower-tier seasons returned data.
- **Lower tiers:** lineups and events (goals, cards, substitutions) are
  available; team statistics and player statistics were empty for the sample.
- **Fringe leagues:** Slovenia 1. SNL and Albania Superliga returned 0 player
  stats; Hungary NB I works, NB II is empty for 2026.
- **Squad stats:** `/players?id=<id>&season=2026` returns per-competition rows
  for senior Aberdeen players. Youth players can return 0 entries. Loan-club
  coverage is uneven: Žilina returned rows; Ross County, Dunfermline, Elgin
  City, Cove Rangers, Peterhead and Inverness CT returned none; the feed still
  listed Aberdeen rows for two loanees and Cerezo Osaka/Australia for a third.
  These gaps are labelled on `/squad/` and the player pages, never zero-filled.
  Named substitutes, including unused substitutes, are stored in
  `player_squads.parquet`; the full season schedule comes from the normalized
  history fixtures plus the SPFL club feed.
- **Roles and position context:** `/fixtures/lineups` and `/fixtures/events`
  cover the current season's played Premiership and League Cup matches (15 of
  15 at the last check). The lineup supplies the formation and starting-XI grid,
  which is the role source, plus on-pitch goals conceded, clean sheets, own
  goals and the starts/substitute minutes split. Thirteen of the 15 matches had
  a grid; the two early League Cup matches did not.

**Fallback:** Sportmonks Starter (€29/month) for cups if the Scottish Cup gap is
unacceptable; confirmed cup catalogue and standings, five competition slots.
No scraping fallback.

## Current public sources and scope

| Source | Coverage | Access | Terms | Status |
|---|---|---|---|---|
| football-data.co.uk | All four SPFL tiers (`SC0`–`SC3`) | Free CSV | Private/non-commercial research; site cautions against automated/AI data products | **Current league results and team match stats**; fallback/cross-check if the API-Football gate passes |
| SPFL club feed | Aberdeen's league fixtures/results | Server-rendered HTML, 1 request/run, cached 1h | SPFL copyright; used for the club page | **Current Aberdeen club fixtures and the official result overlay**; API-Football is a cross-check |
| AFC news listing | Club news, interviews, galleries, women's team, partners | Server-rendered HTML, 1 request/run, cached 1h | Official club content; listing metadata only | **Keep** for headlines, categories, dates and links |
| AFC men's team roster | Canonical current roster, position sections, shirt numbers and On loan section | Server-rendered HTML, one listed page/run, cached 12h | Official club content; names, numbers, positions and links only | **Canonical roster inclusion/status source**; API-Football remains the statistics and identity spine |
| SFA Scottish Cup format/rules | Round calendar, entry rules, 137 clubs/136 ties | Official HTML/PDF | SFA copyright; reference use | **Keep** as format source |

URL pattern for the current league data:
`https://www.football-data.co.uk/mmz4281/{season}/{div}.csv`, where season is
`2627` for 2026/27. The league CSVs contain 228 Premiership matches and 180 in
each lower tier per completed season; play-offs are not included.

## News

| Source | Coverage | Access | Use |
|---|---|---|---|
| **Aberdeen FC news listing** | Club news, interviews, galleries, women's team, partners | Server-rendered HTML, one request per run, cached 1h | Headlines, categories, dates and links on the front page and `/news/` |
| **X profile timeline** | @aberdeenfc posts | Official X embedded widget (`platform.x.com/widgets.js`) | High-frequency embed on `/news/`; not ingested or stored |

Only listing metadata is published. Article bodies and images are not copied;
every card links to the original afc.co.uk article. The X timeline is a
third-party embed: fitba does not fetch, store or republish X content; the widget
may require an X login and can be blocked by privacy settings or ad blockers.
The page always provides an “Open @aberdeenfc on X” fallback link.

## Roles: starting-XI grid and career history

Role is not an attribute lookup. API-Football `/fixtures/lineups` supplies the
formation and each starter's grid slot; `config/roles.yaml` maps the slot to a
role code and an FM-style position slot. The feed covers both teams, so the same
tables are league-agnostic. A substitute has no grid slot, so a substitute
appearance has playing time but no role. A missing grid or an unmapped formation
is unknown. See [roles.md](roles.md) and [career-roles.md](career-roles.md).

The career layer needs one `/players?id&season` call per season, one
`/fixtures?team&league&season` per team/competition and one
`/fixtures/lineups?fixture` per checked fixture. There is no career or player
match-log endpoint, so the backfill is capped at three seasons and 15 fixtures
per player-season, throttled and resumable. It runs on demand, not daily; daily
publishing reads the cached career evidence.

## Preferred foot

The licensed base does not provide preferred foot. It is resolved through a
separate provenance pipeline documented in [player-data.md](player-data.md).
The source order is:

1. **Sportmonks** — preferred foot via the `metadata` include. Licensed source;
   disabled until the key, plan, public-display terms and player crosswalk are
   confirmed.
2. **Official club/federation pages** — only an explicit statement. The AFC
   player pages state a generic position only, so they yield no foot today.
3. **Wikipedia** — last resort. Only explicit foot statements are parsed; the
   page must match the player and mention Aberdeen; the page revision and
   permalink are recorded; the adapter is rate-limited and does not crawl in
   bulk. No article text is published. The same source is a last-resort citation
   for historical managers, honours, cup/European runs and season records where
   no AFC page states the fact.
4. **Unknown** — `null` with a reason. No inference from role, side, name, shirt
   number or generic position.

`scripts/check_player_attributes.py` rejects any published value without a
registered source, URL, verification date and derivation. `config/sources.yaml`
records the allowed lane and capabilities for each source.

## Fan signal: AFC Chat Rumour Mill

| Item | Detail |
|---|---|
| Source | `https://afc-chat.co.uk/forums/index.php?/forum/20-the-rumour-mill/` |
| Feed | `.../forum/20-the-rumour-mill.xml/` |
| Terms signal | robots.txt advertises `search=yes, ai-train=no, use=reference` |
| Access | RSS topic index plus the **first page** of up to 8 recent topics, rate-limited |
| Use | name mentions, cross-reference labels and rule-based sentiment |
| Publication | derived aggregates only; **no raw posts, usernames or quotes** |

The forum is used as a reference signal, not a corpus. fitba does not train a
model on it, does not follow every page and does not republish post text. The
sampled text is stored in the gitignored normalized store and is not part of the
committed JSON. The page states the sample size, that it is first pages only and
that a mention is not a transfer link. See [rumours.md](rumours.md).

## Cup data details

- **League Cup:** API-Football fixtures supply the 80 group matches, group
  labels, penalty scores and knockout rounds. Because group standings are not
  provided, the app computes the eight group tables using the official 3/1 +
  shoot-out bonus rule and tie-breaks in
  [competition-formats.md](competition-formats.md).
- **Scottish Cup:** API-Football supplied 50 of 136 ties at the key-test —
  First and Second Round only. The three preliminary rounds and later rounds are
  not in the feed; the page shows the official round structure and labels every
  missing round. The fallback is Sportmonks or an enterprise provider. No
  scraping fallback.
- **Awaiting draw:** an unpublished draw is a state, not an invented tie.

## Matchday opponent refresh

The `/matchday/` dashboard refreshes only the next Aberdeen opponent:

- one `/fixtures?team=<opponent>&season=<year>` call for the opponent's season;
- up to six `/fixtures/lineups` and `/fixtures/events` calls for the recent
  finished fixtures, cache-first;
- optional `/fixtures/players` and `/fixtures/statistics` calls are off by
  default. Events already carry goals, assists and cards, and possession is not
  dependable enough to use.

The run is capped by `config/matchday.yaml` (`max_api_requests: 24`) and is
gated by a 20-hour refresh window. The daily workflow treats the refresh as
`continue-on-error`; publish reads the local snapshot and never calls the
network. A missing snapshot still leaves league form, strength and Aberdeen's
XI available. Opponent API ids live in `reference/source_ids.yaml`; an id is
never inferred from a club name, and a provider search is a bounded fallback
recorded as a warning, not written back automatically.

## Season overview and provider ratings

The season overview (`/analysis/`) is derived from the same local data as the rest of the site:

- provider per-match ratings and goals from `/fixtures/players` for Aberdeen's
  Premiership fixtures (current season only; the historical player-match-stat
  files are empty);
- lineups and events for role family, starts, minutes and bench rows;
- the league match rows for goals, shots and points;
- the published transfer register and Cormack-era history payloads for the
  mission context.

Provider ratings are labelled as provider ratings, not a fitba rating. They are
minutes-weighted, not position-adjusted, and are never published as individual
verdicts. Provider xG is partial: `expected_goals` appears in some Premiership
statistics responses and football-data.co.uk 2026-27 SC0 carries `HxG`/`AxG`;
there is no historical shot-location feed. fitba's own fxG is a separate,
labelled model ([xg.md](xg.md)). There is no channel, possession-backfill or
mid-game shape feed. Injuries are a curated team-news special case
([availability.md](availability.md)); the provider injury feed is not populated
for current-season Scotland. See [analysis.md](analysis.md).

## Transfers and loans

API-Football `/transfers?team=252` is the candidate feed for Aberdeen:

- 273 player records, full back-history, one response, updated daily.
- Each move has only date, `type`, and the in/out clubs. **No fee field, no
  loan end date, no recall/obligation/option fields.**
- Senior coverage is about 85–90%; some senior moves and roughly 16 youth/
  Highland loans are missing in the 2026/27 window.
- `type` mixes kind and occasional fee text (`Loan`, `Free agent`, `Transfer`,
  `€ 1M`, `355K`, `N/A`, `-`, `Raise`); the register normalises it.
- Duplicate announcement/registration rows and pseudo-team rows for out-of-
  contract players are normalised and deduped.
- No `season` or pagination parameter exists on `/transfers`; fetch the full
  history and filter by date.

The public register is curated: API rows become `reference/transfers.candidates.yaml`
(review-only), and only rows promoted into `reference/transfers.yaml` with an
official/Wikipedia source are published. Fees are curated only; undisclosed is
never zero. Loan terms are curated. Wikipedia is a finding aid; official club
announcements are preferred. Transfermarkt and other restricted sites are not
scraped; a person may read them to spot a gap, but the published row must be
confirmed by an allowed source. See [transfers.md](transfers.md).

For inferred fees, restricted pages may be read privately as a sanity check on
the model, but no restricted value, URL or table is published. Disclosed and
reported fees cite AFC/Wikipedia; modelled ranges carry a method and confidence
label. Sell-on clauses are `confirmed` only with an allowed URL; a `reported`
clause without one is labelled unverified and does not link the restricted page.
The plausibility screen can withhold a row before publication; the public audit
reports a count, not the withheld names.

## Historical club record

The Cormack-era record ([history.md](history.md)) uses:

- **AFC official** — preferred citation for staff appointments, honours,
  cup/European runs and season records.
- **Wikipedia** — last-resort citation for historical managers, honours and
  season records where no AFC page states the fact. Season pages and final
  pages are linked; no article text is copied.
- **API-Football** — historical fixtures, lineups, events, rosters and the
  transfer candidate history.
- **football-data.co.uk** — league results and match-stat proxies.

The lineup/roster backfill is bounded, cached and manual. The daily publish reads
local parquet only. BBC, Transfermarkt and other `no_publication` sources may be
read manually as a finding aid but are never fetched automatically, cited or
republished; `scripts/check_history.py` rejects their ids and hosts.

## Fallback licensed provider: Sportmonks

| Item | Detail |
|---|---|
| Free | Scottish Premiership + Danish Superliga only |
| Starter | €29/month (€24 annual) — 5 competitions |
| Growth | €99/month (€79 annual) — 30 competitions |
| Cup coverage | Catalogue lists Scottish Cup and Scotland League Cup; cup group standings available |
| xG | Basic add-on from €19/month on Starter; covers the Premiership, **not the cups** |
| Gaps | No heat maps/tracking; public-display terms need confirmation |

Use Sportmonks only if API-Football fails the cup key-test. It does not cover all
six Scottish competitions within the five-slot Starter tier.

## Excluded from automated ingestion and publication

These sources are not scraped or republished. That is a restriction on automated
collection and republication, not on reading: a person may look at a public page
as a finding aid to spot a missing move. The fact must then be confirmed by an
allowed source before it is published, and the third-party page is never cited.

| Source | Why not ingested or published |
|---|---|
| BBC Sport | Terms prohibit scraping/republication; the data is complete but not licensed for this use. |
| FotMob / Sofascore | Terms prohibit scraping; no public-display licence. |
| pannadata (cached Opta) | No licence stated; local research only, never published. |
| datafc (Sofascore) | Sofascore terms prohibit automated access. |
| FBref | Terms prohibit automated collection and redistribution. |
| Transfermarkt / Capology | Terms prohibit scraping; no clean licence. Market values are curated and cited instead. |
| Understat / OpenLigaDB | No Scottish coverage. |
| StatsBomb Open Data | No Scottish competition; usable only for non-Scottish prototype/demo work with attribution. |
| Wyscout / Opta / Sportradar | Enterprise event/tracking licences; not purchased in this phase. Public-display rights require a contract. |

## Market values, wages and loans

- Market values: `reference/market_values.yaml`, curated and cited; only value
  bands are published.
- Wages: no reliable public Scottish wage data; fee-only budget mode by default.
- Loans: API-Football transfers/loans where covered; Wikipedia and official
  announcements as cross-checks; the curated register remains the source of
  truth.

## Publication lanes

`open` — raw or derived may be published. `derived_display` — only our derived
metrics/visuals; never raw or source-shaped rows. `no_publication` — may be read
manually as a finding aid, but never ingested automatically, cited or
republished. The public profile publishes `open` + `derived_display`; the
publication guard rejects a `no_publication` source id or URL in committed JSON.

## Scouting team context

The team-context lens uses the licensed provider's league tables, one request
per enabled scouting league. The current group is the one with the most played
rounds; team points per game is `points / played`, and the team percentile is
within that league only. The full season scope and per-league coverage are in
`data/normalized/scouting/team_standings_meta.json` and the `/scouting/`
coverage block. A league without a table is shown as unknown, not a
zero-strength team. The lens does not use budgets, wages or market values.


## Former players and post-Aberdeen careers

The former-player universe and departure facts come from the confirmed transfer
register. Aberdeen tenure comes from the covered historical record. Post-career
league seasons and transfer histories come from the licensed API-Football
`/players?id=&season=` and `/transfers?player=` endpoints. Cup and European
provider rows are stored locally but excluded from published league totals
because the provider repeats season totals across some cup entries. Missing
seasons, leagues and curated-only identities are labelled gaps. No raw provider
response, logo, photograph or fee hint is published.
