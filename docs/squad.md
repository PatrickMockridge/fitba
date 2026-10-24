# Squad and player profiles

**Status:** live for the 2026-27 season. Last reviewed 2026-10-24.

The squad page is the structural bridge between **On the pitch** (`/matchday/`)
and **Off the pitch** (`/recruitment/`). It is the roster, the current-season
output and the loan status in one place, and every current player has a profile
page that other parts of the site link to. The 2026-27 rebuild and shape
instability are recorded in [the context diary](context/aberdeen-2026-27.md).

Machine-readable path:

- `data/normalized/squad/aberdeen_players.parquet` — one row per player
  (gitignored).
- `data/normalized/squad/aberdeen_stats.parquet` — one row per player and
  competition (gitignored).
- `data/normalized/squad/aberdeen_position_stats.parquet` — one row per player
  and competition for on-pitch conceded, clean sheets and own goals
  (gitignored), plus `position_stats_meta.json`.
- `data/normalized/matches/player_appearances.parquet` — one row per player per
  fixture for both teams, with the starting-XI role, starter/substitute flag and
  minutes split.
- `data/normalized/matches/player_roles.parquet` — player/team/season/role
  starts and minutes.
- `data/normalized/matches/playing_time.parquet` — starts, substitute
  appearances and the minutes split by competition.
- `data/normalized/matches/player_match_stats.parquet` — provider per-match
  ratings, saves and key stats.
- `data/normalized/matches/team_shapes.parquet` — kick-off shape and role counts
  per team per fixture.
- `data/normalized/career/player_role_evidence.parquet` — one row per player per
  historical/current start, with team, scope, season, formation and role.
- `data/normalized/career/player_career_roles.parquet` — career role starts by
  player/season/team/scope/competition/role.
- `data/normalized/career/career_backfill_state.parquet` — resumable backfill
  state; `career_roles_meta.json` records coverage and request budget.
- `data/normalized/squad/roster_meta.json` — official roster metadata and
  any unmatched official names (gitignored).
- `web/data/generated/squad/aberdeen.json` — published payload, including
  `roster_meta` and `roster_only`.
- `web/data/generated/players` routes are generated from the payload
  (`/players/<api_id>/`).

## Player identity

The API-Football player id is the stable spine. `reference/players.yaml` is the
correction layer: a curated canonical name, position and shirt number win over a
provider spelling. This matters when a provider merges or mislabels a player.
For example, API-Football returned "A. Morgan-Cummings" for Aaron Cummings; the
canonical override restores **Aaron Cummings**, and
`config/transfers.yaml` `candidate_exclusions` removes the false Potters Bar
Town transfer.

## Squad universe

The canonical roster reference is the official Aberdeen FC men's team page,
https://www.afc.co.uk/en/teams/mens. It determines squad inclusion, the position
section, the shirt number, the **On loan** section and the display order. The
current page lists 34 players: 29 in position sections and 5 on loan. Staff are
excluded.

API-Football remains the statistics and identity spine. A player on the official
list is included even when the API-Football squad omits him; Kristers Tobers is
the current example, with no 2026-27 statistics. A player with no unique
API-Football id is listed in the formal `roster_only` state; it is not dropped.

API-Football squad or transfer-loan rows that are **not** on the official list
are not squad players. They are retained in `excluded_players` with
`squad_member = false`, `roster_status = excluded_api` and
`exclusion_reason = not_on_official_list`, so existing player profiles and
transfer/news links still resolve. They are excluded from the squad table,
summary, search, matchday and every squad count. The page states the excluded
count; it does not present a separate "surfaced" squad list.

Statuses:

- `squad` — in the official position sections.
- `loan_out` — in the official On loan section; the loan club and dates come
  from the confirmed transfer register where present, otherwise the club is
  unknown and shown as such.
- `loan_in` — borrowed by Aberdeen; supported for future windows. There are no
  loan-ins in the 2026-27 register.
- `provider_fallback` — only when the official page is unavailable and the page
  visibly falls back to the API-Football snapshot; never presented as official.

Roster status is `official`, `official_loan` or `excluded_api`. The official
`official_order` is the presentation order. A conflict between the official
section and the confirmed loan register is surfaced, not silently resolved. No
injury is inferred from absence or from the official page: the page does not
label injuries.

## Statistics

Source: API-Football `/players?id=<id>&season=2026`. Statistics are
**current season only**, per competition.

The squad row's headline output is **all Aberdeen competitions** (league, cup
and Europe; friendlies excluded). The player profile also publishes the
Premiership-only comparison. Loan-club rows are never mixed into an Aberdeen
total; they stay on the player profile, labelled. The roster table names
`Starts (all)`, `Sub (all)`, `Mins (all)` and `League mins`, and its G/A/cards/
rating columns use the all-competition club rows. If a competition has no
player statistics, the total is marked partial and the gap is named; it is not
filled from another competition.

Loan counts are scoped: the official team list's **On loan** section is the
squad count (currently 5). The current-season transfer register has 9, because
four development loanees are not on the official first-team page. The all-time
register has 31. The squad, loans and recruitment pages publish these as
separate scopes and link to one another.

Fields published:

| Field | Source |
|---|---|
| appearances | `games.appearences` (the provider spells it this way) |
| starts | `games.lineups` |
| minutes | `games.minutes` |
| goals, assists | `goals.total`, `goals.assists` |
| yellow cards | `cards.yellow` |
| red cards | `cards.red + cards.yellowred` |
| rating | `games.rating`, provider rating, not a fitba rating |
| shots, shots on | `shots.total`, `shots.on` |
| passes, key passes, pass accuracy | `passes.total`, `passes.key`, `passes.accuracy` |
| saves, conceded | `goals.saves`, `goals.conceded` |
| tackles, blocks, interceptions | `tackles` |
| duels, dribbles, fouls | `duels`, `dribbles`, `fouls` |
| penalties | `penalty` (won, committed, scored, missed, saved) |

No per-90, save percentage, xG or other derived metric is published on this
page. The provider rating is labelled as the provider's rating and is aggregated
by appearances; it is not used to rank players.

The provider's `goals.conceded` field is retained for audit but is **not** the
headline conceded figure for goalkeepers or defenders. At the last check it
undercounted Aberdeen's Premiership goals against for the first-choice
goalkeeper (8 provider vs 10 in the results). The event-reconstructed on-pitch
figure is the headline; the provider figure is not displayed as a competing
number.

## Zero, partial and unavailable

- **Zero is measured.** A player with a row and 0 appearances shows 0.
- **Unavailable is not zero.** A youth player with no statistics entries is
  `unavailable`; the totals are `null` and the page says so.
- **Partial** means a relevant row exists but a key field (usually minutes) is
  missing. The page labels it and does not invent a value.
- **Null fields** display as an em dash, not as zero.

The squad summary shows the number of players with unavailable stats so the gap
is visible at the top of the page.

## Loan-club scope

Every statistics row is assigned a scope:

- `club` — the row is at Aberdeen (team id 252).
- `loan` — the row is at the registered loan club.
- `other` — any other 2026-27 row: a national team, a previous club, a different
  loan club, or a stale parent-club row.

Loan-club matching is accent- and case-insensitive with a conservative fuzzy
fallback. If the provider does not return the loan club, the loan is
**unavailable**; parent-club rows are not presented as loan output.

Verified examples at the last check:

- K. Bilalovic (Žilina): loan stats available — 4 apps, 45 minutes.
- N. Suman (Ross County) and D. Lobban (Dunfermline): the provider still lists
  Aberdeen rows with 0 appearances; loan-club stats are unavailable, and the
  Aberdeen rows appear only under “Other 2026-27 records”.
- K. Yengi (Sanfrecce Hiroshima): the provider returns Cerezo Osaka and
  Australia rows; Sanfrecce loan stats are unavailable, and the other rows are
  labelled separately.
- Several lower-tier and youth loanees return no statistics entries.

These are coverage gaps, not errors to fill.

## Player pages

Each current player has a static page at `/players/<api_id>/`. The page is a
projection of `players/<id>.json`; its panel contract and result types are
specified in [player-page-spec.md](player-page-spec.md). In short:

- **Identity** — roundel, name, display role, age, nationality, shirt number,
  side, known preferred foot and one status/loan line. No loan banner, no
  stats-coverage badge, no unknown-foot copy.
- **Position** — “How this position was inferred”: display reason, current
  Aberdeen role starts (labelled role starts), career slots, heat map,
  season/team history and tactical notes. The display role sits in the identity
  header, not a second heading.
- **Playing time** — appearance starts, substitute appearances, minutes started
  and minutes as substitute, by competition. One note, no duplicate caveat.
- **Performance** — role-selected summary tiles, provider table, detail columns
  and a defensive context subtable for defensive roles. One coverage badge; no
  separate defensive section.
- **Records** — only when the provider returns rows outside the main club/loan
  scope; also the home for loan-club record context.
- A panel with no data says so once. Unknown position does not fall back to
  midfield.

Player photographs are **not** published. The API photo URL exists, but its
licence is not established; the page uses initials.

## Roles, foot and cards

Role is derived from the starting-XI formation grid in the licensed team sheet;
the method and taxonomy are in [roles.md](roles.md) and
[career-roles.md](career-roles.md). The squad table shows a primary position,
the FM-style eligibility label (for example `D/WB R`, `DM/M C`), a role-mix bar
and the broad group/side filter. A full-back / wing-back counts as both a
defender and a midfielder; a DM is a midfielder; a winger is an attacker. A
stretch slot is a low-evidence emergency option, not a new primary. A player
with no role evidence shows the generic squad position, labelled as such; no
role is inferred from a generic position, a shirt number or a substitute's
entry.

The main table shows only the primary position. Clicking it opens the inference
panel, which is where the FM label, role mix, career seasons/teams, heat map and
tactical note live. The player profile keeps the current role visible and puts
the career evidence behind “How this position was inferred”.

Preferred foot is curated through the [player-data pipeline](player-data.md) and
shown on the player profile only, with its source and verification date or an
explicit **Unknown**. The team sheet does not contain foot. At the last check,
1 player had a preferred foot; the rest were unknown because no allowed source
states it.

Starts, substitute appearances and on-pitch minutes are reconstructed from
lineups and substitution events. The provider's starts/minutes fields are not
used as the headline because they can be incomplete; they remain in the
provider per-competition table where available.

Yellow and red cards are rendered as vertical card marks in the column
headings; the row cells contain only the counts, so the rows stay numeric and
sortable. Red includes second yellows. A null count is shown as an em dash, not
zero.

## Site-wide player links

A current player's name links to their profile wherever it appears in structured
data:

- squad and player pages;
- transfer cards and the loan register;
- rumour cards and the recruitment-profile table;
- forum signal rows and sampled topic titles;
- home-page and news-page player lists;
- AFC news titles with a current-player mention, shown as a separate “Mentioned”
  line so the article link is not nested inside a profile link.

Links are precomputed in the published JSON (`player_href`, `player_mentions`) so
client-side filters never need to read files. Current players link to their
profile; former players link to the former-player register anchor; rumour
targets and fan-only names stay plain text.

Free-text matching uses full names and unique surnames, accent-folded, with
ambiguous surnames rejected. Players whose provider profile has no full name
only match by their available display name.

## Publication and guards

- `uv run fitba squad` refreshes the official roster, normalized squad,
  position, appearance, role, playing-time and shape tables and their metadata.
  The official page is read once per refresh; no other AFC pages are crawled.
- `uv run fitba publish` writes `squad/aberdeen.json`, adds the player links to
  transfers, rumours, forum signals and news, and adds player entries to the
  search index.
- `scripts/check_squad.py` verifies unique ids and hrefs, valid statuses,
  official-order and excluded-row labels, roster metadata and
  coverage, loan tagging, totals arithmetic, role/playing-time arithmetic, no
  photos, no parent-club rows in loan stats, summary counts and every
  cross-payload player href.
- `scripts/check_roles.py` verifies role evidence, formation coverage and
  starts/minutes arithmetic.
- `scripts/check_shapes.py` verifies kick-off shape counts, per-match joins and
  the provenance of reported mid-game switches.
- The daily workflow runs the squad ingest before publication and fails the
  guard if the squad payload is empty, so a failed ingest cannot silently ship a
  squad-less site.

## Known gaps

- Current-season playing time and provider stats, plus a career role history
  from the last three seasons. The career history is a capped, on-demand
  backfill; if it has not run, the profile says so and shows the current role
  only.
- Role evidence is a starting-XI observation. Two early 2026-27 League Cup
  matches had no formation grid, so starts in those matches count for playing
  time but not for role. Substitute appearances have no team-sheet role. At the
  last check, 20 of the 29 registered squad players had a specific role; the
  other nine had no start and show the generic squad position.
- Mid-game formation switches are not in the feed. Sourced switches live in
  `reference/shape_notes.yaml`; the platform never infers one from substitutions.
- Lower-tier loan-club player stats are often absent, and loan-club lineups are
  not ingested. A loanee's Aberdeen role history is empty if they have not
  played for Aberdeen.
- Position context (conceded, clean sheets, own goals) is built from Aberdeen
  lineups and events. For a loanee it covers Aberdeen appearances only; the
  loan club's event coverage is not ingested.
- Provider ratings are not available for every row and are not a fitba rating.
- Event-reconstructed minutes can differ from provider minutes by a minute or
  two because of event rounding. The playing-time card is the event-derived
  figure; the provider per-competition table is separate.
- Own goals are zero at the last check; the method is in place for when one
  occurs.
- No photos, wages, contract lengths or transfer values are added from this
  source.
