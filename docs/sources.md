# Data sources

Checked 2026-10-21. Re-run `uv run fitba probe` before relying on any claim.
The machine-readable registry is `config/sources.yaml`.

## Results and team stats

| Source | Coverage | Access | Terms | Use |
|---|---|---|---|---|
| football-data.co.uk | All four SPFL tiers (`SC0`–`SC3`); top two from 1994/95, all four from 1997/98 | Free CSV, no key | Private/non-commercial research; attribution; site cautions against automated/AI data products | **Primary results backbone** |

URL pattern: `https://www.football-data.co.uk/mmz4281/{season}/{div}.csv`,
where season is `2627` for 2026/27. The league CSVs contain 228 Premiership
matches and 180 matches in each lower tier per completed season; playoffs are
not included.

## Rich Scottish data

| Source | What it provides | Coverage | Licence | Verdict |
|---|---|---|---|---|
| pannadata (cached Opta) | events, shots, ~280 player-match columns, lineups, event x/y | Scottish Premiership 2019+; Scottish Cup/League Cup | none stated | **Primary rich layer**; raw data never published |
| datafc (Sofascore) | heat maps, average positions, lineups, match stats | SPFL via Sofascore tournament ID, not a configured league | MIT code only; Sofascore terms prohibit automated access | Secondary/cross-check; derived only |
| PitchAPI | 16×12 heat maps, shot xG, pass networks, xT/VAEP | 77 leagues; Scottish coverage unverified; key required | none stated | Probe before use; publication disabled |
| Bzzoiro | shotmaps, stats | No heat-map endpoint; Scottish coverage absent from docs | none stated | Dropped |
| Sportmonks | fixtures, lineups, stats | Free tier = Scottish Premiership; **no player heat maps at any tier** | commercial | Optional live layer |
| statsbombpy / Open Data | event data | **No Scottish competition** | open data with attribution | Engine tests on demo matches only |

## Player data gaps

- FBref has the Premiership (comp 40) and part of the Championship (comp 72),
  but its terms prohibit automated collection and redistribution. It is
  disabled until written permission exists.
- There is **no free player-level source for League One/Two**. Aberdeen loanees
  there use `reference/loan_appearances.csv`, a curated match log, and every
  card is labelled `curated`.

## Values, wages and loans

- Transfermarkt: market values and loan records. Terms prohibit scraping; values
  are cached locally, overridden by `reference/market_values.yaml`, and only
  value bands are published.
- Capology/Salarysport: wage estimates only; no reliable public Scottish wage
  data. Budget fit is fee-only by default.
- Wikipedia season pages (CC BY-SA) and Aberdeen official announcements are the
  cross-checks for loans.

## Publication lanes

`open` — raw or derived may be published. `derived_display` — only our derived
metrics/visuals; never raw or source-shaped rows. `prohibited` — not published.
The public profile publishes `open` + `derived_display`; a test asserts no
prohibited source appears in committed JSON.
