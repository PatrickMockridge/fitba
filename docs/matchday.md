# Matchday dashboard

**Status:** live. Last reviewed 2026-10-22.

`/matchday/` answers the question a fan arrives with before the next game:
**what is this match going to look like, and why?** It is not a season hub and
not a club profile. The page owns one upcoming fixture, both teams' form and
style projections, both predicted XIs and the matchup read. Fixtures, tables,
the squad, transfers and the historical record stay on their own pages and are
linked from the bottom of the page.

The old `/clubs/aberdeen/` dashboard is retired. It tried to be a club profile,
transfer board, shape report and news page at once. The URL is kept as a moved
notice so bookmarks do not break; there is no server redirect in a static
export.

## Panel order

1. **Fixture header** — competition, stage, date, kickoff, venue, home/away,
   freshness and the **Next six** lookahead (current fixture plus the next five
   competitive matches).
2. **The read** — 3–5 evidence-backed bullets and the keys to the match.
3. **Predicted XIs** — side-by-side pitches, XI, 4–6 contenders, confidence and
   the disclaimer.
4. **Form guide** — last five league results and season home/away splits.
5. **Style matchup** — the three-way lean and the measured evidence.
6. **Relative strength** — league position and shot percentiles.
7. **Case archive strip** — a compact selection of the claims about the team, with
   a link to `/analysis/` for the full case. Claims are computed independently of
   the opponent snapshot; a missing lineup does not remove them. See
   [analysis.md](analysis.md).
8. **Recent meetings and coverage** — context, limits and source links.

The panel order is deliberate: the immediate read is above the fold; the
evidence follows; the methodology and limits are at the bottom.

## Data states

| State | Meaning | Page behaviour |
|---|---|---|
| `fresh` | The opponent snapshot is inside the refresh window. | Full page. |
| `stale` | The last snapshot is older than `stale_after_hours`, or the daily refresh failed and the previous document was carried forward. | Banner; content remains visible. |
| `no_fixture` | No scheduled Aberdeen fixture in the local feed. | Empty state and links. |
| `unavailable` | The fixture exists but the opponent snapshot or league row is missing. | Form and strength remain; missing blocks are labelled. |

A predicted XI is `available`, `partial` or `unavailable`. A missing lineup is
never filled with invented players. A `partial` XI has fewer than eleven filled
slots or a small sample; the coverage fraction is shown.

## Sources and refresh

- **Fixtures and results:** the merged season schedule (history fixtures plus
  the SPFL club feed) for the next fixture and the six-game lookahead;
  football-data.co.uk for league match rows and the venue splits.
- **Opponent lineups, events and match ratings:** API-Football, bounded to the
  next opponent only. The refresh fetches the opponent's recent finished
  fixtures, then `/fixtures/lineups`, `/fixtures/events` and
  `/fixtures/players` for each, cache-first. The player call supplies the
  per-match provider ratings used in the opponent XI form line; without it the
  rating is explicitly unavailable, never zero. Team-statistics calls remain
  off by default.
- **League table and form:** the same local match rows used by the rest of the
  site. The matchday document does not republish a full league table.

```bash
uv run fitba matchday --status
uv run fitba matchday --refresh [--fixtures 6] [--max-requests 24] [--force]
uv run fitba matchday --refresh --dry-run
```

The daily workflow runs `--refresh` with `continue-on-error`. A provider outage
does not block the publish: the previous snapshot is carried forward as
`stale`, or the page is built from local league data with the opponent XI
labelled unavailable. `publish()` never calls the network.

The snapshot lives under `data/normalized/matchday/` and is not committed. It
contains the next fixture, the opponent's recent fixtures, lineups, team shapes
and a player-form aggregate. Raw API payloads stay in the gitignored cache.

## Form guide

Form is league-only. It uses the last five results for the form strip and
recent record, and every league match in the season for the home and away
splits. The split table shows played, W-D-L, points, PPG, goals for/against and
shots for/against per match.

The opponent's form is measured with the same function as Aberdeen's. It is not
a prediction and it does not mix cup and league matches silently. Form and the
strength block read the same canonical result frame as the league table; a
finished official Aberdeen result cannot appear in one and not the other.

## Style and the three-way lean

Style is a set of measured, opponent-unadjusted shot proxies:

- shots for and against per match;
- shots on target for and against;
- shot share = shots for / (shots for + shots against);
- goals for and against, conversion and shot accuracy;
- corners, fouls and cards.

The **approach index** is a weighted average of league percentiles: shots for
40%, shot share 25%, goals for 20%, shots on target 15%. Missing metrics are
dropped and the remaining weights renormalised; fewer than two metrics means
`unknown`.

The fixture-venue sample is used when it has at least three matches:
`0.6 × venue index + 0.4 × overall index`. Otherwise the overall index carries
the read and the page says so.

- `attack`: index ≥ 60 and shot share ≥ 0.50.
- `sit_deep_counter`: index ≤ 40 and shot share ≤ 0.48.
- `balanced`: everything else.

A deep label needs some counter evidence — goals, shots on target or conversion
above the league middle. Without it the confidence is lowered and the evidence
says the counter punch is not established. This prevents a low-volume, low-output
team from being incorrectly described as a counter-attacking side.

Confidence is high with at least eight matches, full stat coverage, four of the
last five matches on the same side of 50% shot share and a venue sample of at
least three. It is medium with at least four matches and three of five
consistent. Otherwise it is low.

**Possession is not used.** The provider statistics endpoint is not dependable
at scale; the payload records `possession: unknown` and a reason. There is no
xG and no tactical model claim.

## Relative strength

Position, points, PPG, goals and shots are taken from the current league table.
Percentiles are within the same league:

```text
below = count(values < x)
equal = count(values == x) - 1
percentile = 100 × (below + 0.5 × equal) / (n - 1)
```

clamped to 0–100, or unknown when the sample is smaller than two. The bar uses
the percentile, but the visible label is a **league rank**, not a percentile:

```text
rank = 1 + count(values better than x)
league_size = number of teams in the league
```

For goals against, lower is better. With a 12-team league, the labels run from
1st to 12th of 12; a percentile in the 50s is a mid-table rank, not 59th place.
A cross-tier cup opponent is marked `cross_tier`; raw values and the tier gap are
shown instead of a like-for-like percentile.

## Predicted XI

The prediction is a projection from observed lineups, not team news.

1. **Formation:** the recency-weighted mode of the last six observed shapes. A
   missing formation is `unavailable`; no shape is assumed. Unmapped shapes are
   low confidence or unavailable.
2. **Candidates:** Aberdeen's current squad excluding loan-outs and
   players marked out/suspended by the curated availability ledger (doubtful
   players remain selectable with a confidence downgrade); the opponent's
   players observed in the
   fetched lineup window. The opponent has no curated availability record unless one is added; availability stays unknown.
3. **Score:** start rate 22%, recency-weighted starts 18%, minute share 10%,
   role fit 15%, player form 20% and recent provider rating 15%. Form combines
   recency-weighted minutes with goals and assists from events. The recent
   rating is a minutes-weighted average of the last six Premiership provider
   ratings, normalised from the provider's 6–8 band to 0–1. Player form and
   recent ratings therefore carry 35% of the selection score; team form is the
   matchday context, while player form and ratings drive the XI. Missing ratings
   are not zero: the remaining weights are renormalised and the player's rating
   coverage is shown. Provider ratings are a selection signal, not a fitba
   rating and not an individual verdict.
4. **Role fit:** the player's most frequent observed role code against the
   target slot, using the adjacency table in `config/matchday.yaml`. A player
   without a role history falls back to the coarse position group at a maximum
   fit of 0.3.
5. **Assignment:** the goalkeeper is assigned first and only a goalkeeper can
   fill it. Outfield slots are filled greedily by score and role fit; every
   player is used once. A slot with no eligible player is left empty.
6. **Confidence:** per-player margin over the next candidate, start rate and
   role fit; team confidence from the number of high/medium picks and the
   formation confidence. Coverage below 60% downgrades confidence; below 30%,
   or fewer than three lineup matches, means no prediction.

Contenders are the next 4–6 best unused players across slots. Aberdeen players
link to their profile pages; opponent players do not.

Every lineup block carries: **"Predicted, not official team news. Based on
recent starts, minutes, formation and position fit."** The guard rejects
"confirmed XI", "will start" and "guaranteed".

## Editorial rules

- The read describes measured form and shot profiles. It is not a result
  prediction and not betting advice.
- Do not present a provider injury flag as team news. It may be stale.
- Do not publish a lineup, formation, possession value or percentile that the
  data does not support.
- A cross-tier comparison is labelled.
- The old Aberdeen dashboard URL is a moved notice, not a second dashboard.

## Known gaps

- Opponent lineups may be missing for lower-tier or early-cup opponents.
- Opponent availability is unknown unless a curated official team-news record exists; the provider injury boolean is not team news.
- Possession is not dependable and is not used.
- Early-season samples are small; confidence is lowered visibly.
- The page is built from the last publish. A kickoff between publishes shows the
  preview plus a client-side "may have kicked off" notice.
- Provider request budgets can truncate the lineup window; the snapshot is
  marked partial.
