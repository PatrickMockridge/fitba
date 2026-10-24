# Data licence and publication policy

**Last reviewed:** 2026-10-24.

The GNU Affero General Public License v3.0 or later in `LICENSE` covers the code
and documentation in this repository only. It does not grant rights to any
third-party football data.

## The rule

Public data must come from a **licensed source** or an official club/federation
listing whose terms permit the use. We do not scrape sources whose terms
prohibit scraping into the public app. Unlicensed event/tracking data may be used
locally for prototypes but is never committed or published.

## What is published

Only derived outputs are committed:

- league tables and match results computed by this project;
- cup groups, rounds, fixtures and results derived from a licensed feed;
- aggregated team and player metrics;
- percentile and scouting scores computed by this project;
- curated fee bands and contract/loan status with citations;
- AFC news headlines, categories, dates and links;
- a manifest recording freshness, coverage and provenance;
- team-match shot-zone and penalty features derived from the licensed feed for
  the fxG calibration. Raw team-statistics responses are not committed; the
  model coefficients, ranges and evaluation are derived outputs.

Raw source payloads, full event feeds, source-shaped tables and raw market-value
feeds are never committed. They live in gitignored `data/` and `.cache/`.

## Source terms

### Active licensed base: API-Football

- Public non-commercial websites/apps are contemplated in API-Sports terms.
- Raw resale/redistribution is prohibited; derived pages are permitted.
- The provider does not grant a licence to the underlying fixture IP of leagues
  or broadcasters; that remains the user's responsibility.
- No attribution requirement is stated, but the app attributes all sources.
- Team statistics include shot zones, blocked shots and expected goals where
  returned; they do not include shot coordinates, pressure or xGOT. The
  league-wide 2026-27 enrichment is used only for model calibration and is not
  redistributed as raw provider data.
- League Cup group standings are not provided; the app computes them from the
  fixtures and labels them as computed.
- Key-tested 2026-10-21. Coverage is partial: the Scottish Cup feed had 50 of
  136 ties, current lower-tier player stats were empty, and current-season
  Scottish injuries coverage is false. Team match stats are not available for
  every tier. The app labels those gaps and keeps Football-Data primary for
  league results and team stats until the strict migration gate passes. If a
  gap is unacceptable, the fallback is Sportmonks for the cups, not a scraper.

### Current league data

- **football-data.co.uk** — free CSVs for research; attribution expected. The
  site cautions against commercial or automated/AI data products. This is a
  non-commercial research project; use is documented and attributed. It remains
  primary for league results and team match stats until the API-Football
  migration gate passes.

### Official club/federation listings

- **SPFL club feed** — Aberdeen's league fixtures/results. Used for the club
  page; API-Football is a cross-check.
- **AFC news listing** — listing metadata only (headline, category, date, link).
  Article bodies and images are not copied. The curated availability ledger may
  cite an official AFC team-news URL; no article text is republished.
- **X profile timeline** — an official X embedded widget for @aberdeenfc. fitba
  does not ingest, store or republish X posts; the widget is subject to X's
  terms and may require a login. A direct link to X is always provided.
- **SFA format/rules** — competition structure and dates, cited on the
  competition-format page.
- **Aberdeen FC player profiles** — shirt number, nationality and generic
  position only. No preferred foot or side is stated.
- **Sportmonks** — preferred licensed source for preferred foot (metadata) and
  detailed position. The adapter is disabled until the key, plan and
  public-display terms are confirmed; no request is made before then.
- **Wikipedia** — CC BY-SA. Used as a last-resort fallback for preferred foot and
  side only, and only when an explicit statement exists. The page revision and
  permalink are recorded; no article text is published. It is never the primary
  cup feed and never a tie-breaker between licensed sources.

### Excluded from the public pipeline

- **BBC Sport, FotMob, Sofascore, datafc** — terms prohibit scraping or
  republication; not used for public data.
- **pannadata (cached Opta)** — no licence stated; local research only, never
  published.
- **FBref / Sports Reference** — automated collection and redistribution are
  prohibited; disabled.
- **Transfermarkt / Capology** — scraping prohibited; market values are curated
  and cited instead.
- **StatsBomb Open Data** — no Scottish competition; non-Scottish demo/prototype
  use only, with attribution.
- **Wyscout / Opta / Sportradar** — enterprise event/tracking licences; not
  purchased in this phase. Public-display rights require a contract.

### Market values, wages and tracking

- Market values: curated, cited bands in `reference/market_values.yaml`; raw
  feeds are never published.
- Wages: no reliable public Scottish wage data; fee-only budget mode by default.
- Tracking/event data: event-reconstructed visuals only once a licensed source
  exists; tracking is not published. Local prototypes do not enter the public
  repo.

## Takedown and opt-out

`fitba publish --profile public` is the only path to the committed web data.
A source can be disabled in `config/sources.yaml` (`ingest_allowed`,
`publication_allowed`) or with `SOURCES_ENABLED`; the site can then be rebuilt
from the remaining sources. If a rights holder asks for removal, disable the
source, republish, and revert the data commit. Do not mirror the generated JSON
to other hosts.

## No affiliation

This project is not affiliated with Aberdeen FC, the SPFL, the SFA, Opta, Stats
Perform, Sportmonks, Sofascore or any other provider. It is a non-commercial
research project.
