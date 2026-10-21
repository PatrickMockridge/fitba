# fitba

Scottish football data, Aberdeen-first.

A data-science project covering the SPFL pyramid — Premiership in depth, plus the
Championship, League One and League Two — with Aberdeen FC as the focal club. It is
built to grow into a regularly-updated web app with:

- league tables, form and match analysis for all four tiers;
- Aberdeen squad, style and season analysis;
- a scouting engine for players across Scotland and Europe who fit Aberdeen's
  budget, squad needs and style;
- tracking of Aberdeen loanees in the lower tiers;
- a 2D match viewer for goals and key passages, reconstructed from event data.

## What is live now

- **Results foundation** for all four SPFL tiers, backfilled to 2013/14.
- **Computed league tables** with points, goal difference, goals scored, head-to-head
  tiebreaks, form and **points deductions** with citations. Verified against the
  official 2025/26 tables for all four tiers.
- **Aberdeen dashboard**: current position, results, season history, intended style,
  squad needs and the fee-only budget envelope.
- **Static Next.js app**: home, pyramid, tier tables, Aberdeen, scouting method,
  loans, methodology and data-status pages.
- **Validation**: match counts (228/180/180/180), date bounds, unique match keys,
  team resolution, points arithmetic, goal balance, publication-size and provenance
  guards.

Scouting rankings, loanee entries and the 2D viewer are scaffolded with honest empty
states; they populate when the verified player/event layer lands. See
[docs/sources.md](docs/sources.md).

## Quick start

```bash
uv sync
uv run fitba probe                 # source reachability + coverage
uv run fitba ingest --season current
uv run fitba build --season all
uv run fitba validate --season current
uv run fitba tables --season current
uv run fitba publish --season current

cd web && npm install && npm run dev
```

`make check` runs Ruff, Pyright and pytest. The warehouse and raw feeds live in
`data/` and `.cache/` and are gitignored. The published web data lives in
`web/data/generated/` and is committed; Vercel builds the app with its project root
set to `web`.

## Layout

```
config/          sources, competitions, publication lanes, scouting, Aberdeen
reference/       canonical teams, loans, market values, disciplinary record
src/fitba/       sources → ingest → normalize → warehouse → analytics → publish
sql/             DuckDB views (phase 2+)
contracts/       dataframe and published-JSON contracts
scripts/         source probes and publication guard
tests/           pytest fixtures and unit tests
web/             Next.js app (static export)
data/, .cache/   gitignored raw/normalized/warehouse data
```

## Data sources

The primary results source is football-data.co.uk (`SC0`–`SC3`). The rich Scottish
layer is planned from pannadata/Opta events (Premiership 2019+), with Sofascore as a
secondary source. FBref is disabled because its terms prohibit automated collection;
there is no free player-level source for League One/Two.

## Licensing

Code is MIT. Source data is not redistributed raw. The public app publishes only
derived tables, aggregates, percentiles and compact sequences, with attribution.
See [DATA_LICENSE.md](DATA_LICENSE.md) and [docs/sources.md](docs/sources.md).
