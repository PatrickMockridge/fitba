# fitba

**Aberdeen FC, without the noise.**

An independent, data-driven record of Aberdeen FC — the numbers, the sources and
the argument, without the hot takes.

fitba is built for highly engaged, literate, numerate Aberdeen fans who want to
see the evidence for themselves, and for the club, press, critics and Scottish
football readers who want the same evidence applied across the pyramid. It is
independent, non-commercial and explicitly not a club mouthpiece. The canonical
audience, essentiality and number rules are in
[docs/specification.md](docs/specification.md).

The identity and non-negotiables are in [docs/identity.md](docs/identity.md). The
product scope is in [docs/product-strategy.md](docs/product-strategy.md). The
full documentation index is [docs/README.md](docs/README.md).

## Documentation

| Document | Read it for |
|---|---|
| [Identity](docs/identity.md) | The public line, reader, editorial stance, voice rules and non-negotiables. |
| [Page contracts](docs/page-contracts.md) | The evidence each main route must keep visible, and the contract-change process. |
| [Design foundation](docs/design.md) | The System 7 grammar, the four themes and the visual rules. |
| [Product strategy](docs/product-strategy.md) | Product scope, content pillars, roadmap and delivery staging. |
| [Matchday dashboard](docs/matchday.md) | The next fixture, both predicted XIs, form, style and data states. |
| [Data analysis](docs/analysis.md) | The owner's view, the chairman's frame, six claims and the fxG block. |
| [Match record](docs/fixtures.md) | One page per played Cormack-era fixture, with events, lineups, stats and the deterministic read. |
| [fxG](docs/xg.md) | The experimental shot-on-target expected-goals model, interval and provider-xG gate. |
| [Match scoreboard](docs/match-scoreboard.md) | The top-level score, goal and red-card widget and the Aberdeen/opposition split. |
| [Methodology](docs/methodology.md) | How every number is produced and how uncertainty is shown. |
| [Data provenance](docs/provenance.md) | The layer-by-layer source truth table and the league migration gate. |
| [Sources](docs/sources.md) | Every source, its licence position, coverage and known gaps. |
| [Architecture](docs/architecture.md) | How ingestion, analytics, publication and the web app fit together. |
| [Roadmap](docs/roadmap.md) | What is live, what is next and what is deliberately out of scope. |

## Principles

- **Same evidence, not insider knowledge.** We show public-data proxies and say
  what is measured, inferred, curated or unknown.
- **Method disclosure, not data hiding.** Headline, visual, "what this means",
  then the method. Substantive panels and sources stay visible.
- **Uncertainty is a feature.** Sample sizes, coverage tiers and confidence are
  visible.
- **Show the trade-offs, not villains.** A trading club creates value and
  volatility; both are part of the story.
- **No licence landmines.** Public data comes from licensed sources; unlicensed
  event/tracking data stays local.

## What is live now

- **Results foundation** for all four SPFL tiers, backfilled to 2013/14.
- **Computed league tables** with points, goal difference, goals scored,
  head-to-head tiebreaks, form and **points deductions** with citations.
  Verified against the official 2025/26 tables for all four tiers.
- **Matchday dashboard**: the next fixture, both predicted XIs, form and style,
  a compact case strip, and a squad-needs board with a
  fee-only budget envelope. The old Aberdeen dashboard is a moved notice.
- **Match record**: every played Cormack-era fixture has a page with a top-level
  scoreboard (goals, scorers, assists, penalties, straight-red vs second-yellow
  cards), timeline, lineups, league/API stats, player stats where available and
  fxG. Aberdeen is red and the opposition neutral throughout; missing data is
  labelled, never zero-filled.
- **fxG**: an experimental shot-on-target xG model with an 80% interval and a
  provider-xG gate. The gate currently fails, so fxG is descriptive only.
- **Results & fixtures across all three Scottish competitions**: league results
  and team match stats from Football-Data.co.uk (clearly labelled, with a gated
  API-Football migration); League Cup and Scottish Cup fixtures from
  API-Football, with the Scottish Cup partial feed labelled.
- **Competition pages**: an Aberdeen current-season `/competitions/` index, a
  full League Cup page with computed group tables and every knockout round, and
  a Scottish Cup page for
  the rounds the licensed feed covers. The Scottish Cup feed is partial (50 of
  136 ties at the last check); missing rounds are labelled, not invented.
- **Transfers and loans**: a confirmed-business register for Aberdeen across
  2019/20–2026/27, with permanent, loan and free moves in and out, source-linked
  verification and no rumour lane. The recent four windows are audited; earlier
  windows are curated partial. Fees are usually undisclosed: disclosed/reported
  amounts are anchors, other permanent moves carry an inferred range with a
  confidence label, and sell-on clauses are tracked separately.
- **The Cormack era**: `/history/` and one season review page per season from
  2019-20, tracking managers and backroom changes, honours, recruitment, style,
  selection and a labelled assessment. The measured record is separated from the
  reading; league facts join from the club payload, and the transfer, honour and
  staff registers remain the single source of truth.
- **Aberdeen news**: official afc.co.uk headlines, categories and links, plus
  the embedded @aberdeenfc X timeline for high-frequency posts. X content is
  embedded, not ingested or stored.
- **Upcoming-matchday dashboard**: `/matchday/` is the next fixture and the
  immediate read — both predicted XIs with contenders and confidence, form and
  home/away splits, opponent style and relative strength, the likely approach
  and the keys to the match. It is explicitly predicted, not team news. The old
  `/clubs/aberdeen/` dashboard is retired to a moved notice. Fixtures, results,
  tables and competitions remain one click away.
- **Data analysis**: `/analysis/` is the evidence-led bridge between the
  matchday lookahead, the squad, recruitment and the Cormack-era mission. It
  starts with the owner's view, framed by the chairman's stated approach, then
  tests six claims about the team, the squad and the Cormack-era record. Each
  claim has a count, a status, an evidence table and what would change the view.
  Provider ratings are labelled, minutes-weighted and never an individual
  verdict; there are no blame narratives or invented availability claims.
- **Provenance, availability and needs**: `/sources/` publishes a layer
  truth table (API-Football primary for cups, lineups, player stats and squad;
  Football-Data primary for league results/stats until the migration gate
  passes). Injuries are a curated team-news special case, not a provider
  boolean. `/recruitment/` carries a seven-family squad-needs board for cover,
  replace and strengthen, with no named targets or invented fees.
- **Two doors and a bridge**: `/matchday/` for the next game; `/recruitment/`
  for transfers, loans, scouting and rumours; and `/news/` between the club's
  voice and the rumour mill.
- **Squad and player profiles**: `/squad/` is the structural bridge, with every
  current player and current loanee, FM-style multi-position eligibility
  (`D/WB L`, `DM/M C`, `AM R`), primary/secondary/stretch career roles, starts
  and substitute appearances with the minutes split, current-season output,
  position-specific goals conceded, clean sheets and own goals, preferred foot
  with source provenance, and an explicit unavailable or unknown state where
  the data does not exist. The broad filter is defenders/midfielders/attackers
  and left/centre/right; a full-back counts as both a defender and a midfielder,
  a DM is a midfielder, and a winger is an attacker. Every current player has a
  static `/players/<id>/` page, and current-player names link to it across the
  site. Positions come from the licensed team sheet; preferred foot is the one
  profile field the team sheet does not contain. The multi-position model is
  general, not Aberdeen-only: it covers utility players, inverted full-backs and
  inside forwards, with curated tactical notes where the kick-off grid cannot
  tell the whole role.
- **Rumour mill and fan signal**: a curated, source-linked rumour register
  separate from confirmed business, plus sampled AFC Chat Rumour Mill first
  pages for name mentions, cross-reference labels and rule-based sentiment. No
  raw posts or usernames are published. The active links produce an advisory
  recruitment profile; community engagement is a deferred separate project.
- **Static Next.js app**: the matchday dashboard, Data analysis,
  two hub pages, the squad and player profiles, competitions, fixtures,
  transfers, the Cormack-era history and season reviews, rumours, news,
  pyramid, tier tables, scouting, loans, methodology, metrics/audit and
  data-status pages.
- **Validation**: match counts (228/180/180/180), date bounds, unique match keys,
  team resolution, points arithmetic, goal balance, cup group arithmetic,
  publication-size and provenance guards. Every published number is registered
  in `config/metrics.yaml`; the generated audit and the registry are on
  `/metrics/`, with the build summary on `/status/`.

## Next: scouting and the trading-club layer

The next phase turns the licensed basic stats into the fan-facing scouting and
trading-club views: position-aware percentiles, budget bands, squad age/value,
opposition comparisons and loanee tracking with explicit coverage labels. See
[scouting method](docs/scouting-method.md), [trading model](docs/trading-model.md)
and the [roadmap](docs/roadmap.md).

## Requirements

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js 20+ for the static Next.js app

## Quick start

```bash
uv sync
uv run fitba probe                 # source reachability + coverage
uv run fitba ingest --season current
uv run fitba cups
uv run fitba fixtures --club aberdeen
uv run fitba matchday --refresh      # next opponent: fixtures, lineups, events
uv run fitba transfers
uv run fitba squad
uv run fitba availability --refresh  # curated team news + optional provider
uv run fitba news
uv run fitba forum                 # AFC Chat first-page sample (reference use)
uv run fitba history --backfill --from-season 2019-20 --to-season 2025-26
uv run fitba build --season all
uv run fitba validate --season current
uv run fitba tables --season current
uv run fitba publish --season current

cd web && npm install && npm run dev
```

## Quality checks

```bash
make check                 # Ruff, Pyright, pytest and every publication guard
cd web && npm run build    # static export; fails on a broken route
```

CI runs the publication guards against the committed payloads; guards that
need the local warehouse (roles, shapes) run in full after a build. The
warehouse and raw feeds live in `data/` and `.cache/` and are gitignored.
The published web data lives in `web/data/generated/` and is committed.

## Deployment

GitHub Pages serves the project site at
**https://patrickmockridge.github.io/fitba/**. The
[`deploy-pages`](.github/workflows/deploy-pages.yml) workflow builds `web` with
`NEXT_PUBLIC_BASE_PATH=/fitba`, writes `.nojekyll` and publishes `web/out`.

- Every push to `main` deploys.
- Completed `update-daily` and `update-weekly` runs deploy the fresh data commit
  even though a bot push made with `GITHUB_TOKEN` does not trigger `on: push`.
- Local builds and the CI check use no base path and serve from the root.

The project site sits under `/fitba/`, so a new hard-coded internal link must
use `next/link` or include the base path. A custom domain would remove that
requirement.

## Layout

```
config/          sources, competitions, cups, matchday, publication, scouting, Aberdeen
reference/       canonical teams, loans, market values, disciplinary record
src/fitba/       sources → ingest → normalize → warehouse → analytics → publish
sql/             DuckDB views
contracts/       dataframe and published-JSON contracts
docs/            product strategy, formats, methodology, scouting, sources
scripts/         source probes, publication and documentation guards
tests/           pytest fixtures and unit tests
web/             Next.js app (static export)
data/, .cache/   gitignored raw/normalized/warehouse data
```

## Data sources

The licensed base is **API-Football Pro**, active and key-tested 2026-10-21. It
supplies the League Cup and Scottish Cup fixtures/rounds/penalties, plus
Premiership and top-European player stats. Its known limits are documented: no
League Cup standings (computed), a partial Scottish Cup feed (50 of 136 ties),
no current lower-tier player stats, only partial provider xG and no shot
locations/heat maps, and no market values.

League results still come from football-data.co.uk and Aberdeen's club fixtures
from the official SPFL feed until the migration is completed; those become local
cross-checks. The AFC news listing remains for headline/link metadata. We do not
scrape BBC, FotMob, Sofascore, Transfermarkt or FBref into the public app.
Reading a public page manually as a finding aid is fair use; the restriction is
automated collection, citation and republication. Market values are curated and
cited. Event/tracking data is not published.

See [docs/sources.md](docs/sources.md) for coverage, licences, gaps and
last-checked dates.

## Licence

Copyright (C) 2026 Patrick Mockridge.

The code and documentation in this repository are licensed under the **GNU
Affero General Public License, version 3 or later** (AGPL-3.0-or-later). See
[LICENSE](LICENSE). The AGPL's network clause applies: if you run a modified
version of fitba and let users interact with it over a network, you must offer
them the corresponding source.

The licence covers the code only. It does not grant rights to any third-party
football data. Source data is not redistributed raw; the public app publishes
only derived tables, aggregates, percentiles and short listings, with
attribution. See [DATA_LICENSE.md](DATA_LICENSE.md) and
[docs/sources.md](docs/sources.md).

fitba is an independent, non-commercial research project. It is not affiliated
with Aberdeen FC, the SPFL, the SFA or any data provider.
