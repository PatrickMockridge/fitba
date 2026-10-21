# Data licence and publication policy

The MIT licence in `LICENSE` covers the code in this repository only. It does
not grant rights to any third-party football data.

## What is published

Only derived outputs are committed:

- league tables and match results computed by this project;
- aggregated team and player metrics;
- percentile and scouting scores computed by this project;
- compact, event-reconstructed goal/key-passage sequences;
- a manifest recording freshness, coverage and provenance.

Raw source payloads, full event feeds, source-shaped tables and raw market-value
feeds are never committed. They live in gitignored `data/` and `.cache/`.

## Source terms (checked 2026-10-21)

- **football-data.co.uk** — free CSVs for research; attribution expected. The
  site now cautions against commercial or automated/AI data products. This is a
  non-commercial research project; use is documented and attributed.
- **pannadata (cached Opta)** — no licence stated. Raw data is never
  redistributed; only derived visuals and metrics are published.
- **Sofascore via datafc** — Sofascore terms prohibit automated access and
  restrict use to personal, non-commercial purposes. Used only for local,
  derived analysis; no raw data is published.
- **FBref / Sports Reference** — automated collection and redistribution are
  prohibited by their terms. Not part of the public publication pipeline unless
  permission is granted.
- **Transfermarkt** — scraping is prohibited by its terms. Market values are
  cached locally for budget bands only; raw values are never published.
- **StatsBomb Open Data** — no Scottish competition. Used only to test the
  animation engine on non-Scottish demo matches, with required attribution.
- **Wikipedia** — CC BY-SA; used for loan cross-checks with attribution.
- **ClubElo** — free CSV, used as a labelled league-strength input with
  attribution.

## Takedown and opt-out

`fitba publish --profile public` is the only path to the committed web data.
A source can be disabled in `config/sources.yaml` (`ingest_allowed`,
`publication_allowed`) or with `SOURCES_ENABLED`; the site can then be rebuilt
from the remaining sources. If a rights holder asks for removal, disable the
source, republish, and revert the data commit. Do not mirror the generated JSON
to other hosts.

## No affiliation

This project is not affiliated with Aberdeen FC, the SPFL, Opta, Stats Perform,
Sofascore or any other provider. It is a non-commercial research project.
