# The bigger picture: medium and long-term themes

**Status:** live. Last reviewed 2026-10-22.

The matchday dashboard answers the next game. This layer is the backdrop: the
squad structure, shape trade-off, defensive cover, attack-defence balance and
the club's longer trading mission. It is the bridge between the on-field view,
the squad, recruitment and the historical record — the place where the
arguments fans have in the stands meet the evidence the backroom works with.

The page is deliberately **80% current season and 20% Cormack-era mission**.
The split is editorial, not a statistical model. Four season themes carry the
current picture; one mission theme carries the longer context.

## Where it lives

- A compact **“The bigger picture”** section on `/matchday/`, after the style and
  strength panels and before the recent meetings/coverage.
- A full **`/themes/`** page with the evidence tables, player/role detail,
  caveats, method and links into `/squad/`, `/transfers/`, `/recruitment/` and
  `/history/`.
- Nav label: **Themes**. The page is also linked from the squad and recruitment
  pages.

The payload is `web/data/generated/themes/aberdeen.json`, produced on every
publish from local data. Themes are independent of the matchday snapshot: a
missing opponent lineup does not remove them, and a theme failure does not
break the matchday page.

## The five themes

| Theme | Horizon | Fan question |
|---|---|---|
| Family balance | Season | Where are Aberdeen strong and weak? |
| The wing-back tax | Season | What does three at the back cost? |
| The cover question | Season | Who is actually covering the defence? |
| The leaky boat | Season | Are the forwards covering the defence? |
| The mission check | Mission (20%) | Is the trading model working, or just a leaky boat? |

### Family balance

Groups: GK, CB, FB/WB, midfield (DM/CM), AM/WM, wide forward (W), ST.

- Starts and minutes use the observed starting role across all competitive
  fixtures.
- Provider ratings use Premiership starters only, weighted by minutes. The
  table reports the mean, median, 25th percentile, sample and confidence.
- Goals and assists use the player's **primary squad role** so substitutes
  count.
- The read reports what the data shows, including when it does **not** support
  the simple “weak centre-backs” framing. A family mean can hide a
  high-variance unit, so the 25th percentile is shown.

### The wing-back tax

- Splits kick-off shapes into two centre-backs and three centre-backs. A back
  three and a back five are treated together as three centre-backs; unknown
  shapes are excluded and counted.
- Counts wing-back, full-back and wide-forward starts per match, named bench
  wide forwards and wide-forward substitute minutes.
- Names the players in the shape evidence (for example Guinness-Walker, Cadden,
  Yogane, Lewis Smith) but never publishes individual ratings.
- The sample is small. The read says “associated”, never “caused”.
- **Channels are unknown.** The feed has no event coordinates, crosses or xG.
  The page cannot measure “doubling up in the channels”; it shows wing-back
  dependency and goals/shots/corners against as proxies, and labels the gap.

### The cover question

- CB and FB/WB depth: starts, minutes, named bench rows, category
  (starter/rotation/fringe), arrival season and curated notes.
- Concentration: the top player's share of group minutes and the number of
  players with three or more starts.
- Recent 2026-27 defensive arrivals and their minutes; limited samples are
  labelled.
- Availability: the curated official team-news ledger is the special case; the
  provider `injured` flag is not team news and current-season provider injuries
  are not populated. Tobers has a curated transfer-gap note, not a published
  availability status. The minutes pattern is consistent with limited rotation;
  the data **cannot distinguish selection from curated availability**. “Trust”
  is an inference, not a fact.

### The leaky boat

- League goals for/against, points, shots for/against, shot share and
  conversion, with the last five games alongside the season.
- Goals by primary family: attack (W/ST), midfield, defence/GK.
- The read describes the balance. It does not claim the forwards are literally
  “bailing out” the defence; there is no xG or shot-quality model.

### The mission check (20%)

- Uses the Cormack-era pillars in `reference/history/era.yaml`: buy
  low/develop/sell high, the youth pathway, a defined style, market edge and the
  squad-turnover trade-off.
- Metrics: 2026-27 arrivals/departures, median arrival age, U21 minutes share,
  players used, manager spells, honours, era league range, formation mix and
  defensive arrivals.
- The read shows the trade-off: high turnover and young minutes are the model
  visible in the squad; the sporting cost is an unsettled back line. It does
  not decide whether the club's risk appetite is right.
- Commercial and fanbase growth are labelled context only; the public football
  data cannot measure them.

## Data and role bases

| Purpose | Role source | Scope |
|---|---|---|
| Family ratings and family minutes | observed starting role from `player_appearances` | all competitive fixtures for minutes; Premiership starters for ratings |
| Goals and assists by family | squad `display_role` / career primary family | all players, including substitutes |
| Shape splits | observed starting role; kick-off `team_shapes` | all competitive fixtures; ratings/bench league-only |
| Bench and impact minutes | `player_match_stats` unused-bench and substitute rows; squad primary family | Premiership only |
| Depth | `player_appearances` plus squad primary family | all competitive fixtures |
| Mission | published history, recruitment and transfer payloads | 2019-20 to date |

Provider ratings are a measured input, **not a fitba rating**. They are
Premiership-only, current-season, minutes-weighted and not position-adjusted.
Cross-family comparison is descriptive. They are never used to rank individual
players in the theme player lists.

The squad-page position-group rating is a different measure: an equal-weighted
season aggregate that mixes full-backs with centre-backs. The theme layer uses
per-match starters so the role family and the sample are explicit. The two
numbers can differ; the theme table shows the per-match sample and spread.

## Confidence and coverage

- Family: high at ≥900 rated minutes and ≥6 matches; medium at ≥450 and ≥3;
  otherwise low.
- Shape: a three-CB sample below five is low confidence; two-CB is medium.
- Depth: starter at ≥5 starts or ≥450 minutes; rotation at ≥1 start or ≥90
  minutes; fringe otherwise. Concentration is high at ≥55% of group minutes;
  thin rotation when fewer than three players have ≥3 starts.
- Balance: season medium; last five low.
- Mission: medium, curated/measured mix.

Missing data is `unavailable` or `partial`, never zero. The document records
the rating scope, role coverage, rated minutes, bench scope and the list of
unavailable layers.

## What is not measured

- Injury severity, return dates or suspensions. There is no feed.
- xG, shot quality, channel location, crosses, possession or tracking.
- Mid-game formation changes; only kick-off shapes are measured.
- Historical provider ratings; the history player-match-stat files are empty.
- Individual player verdicts or a fitba rating.
- The club's internal valuations, wage structure or boardroom intent.

## Editorial rules

- Evidence before narrative; context before blame.
- Label measured, inferred, curated and unknown.
- No “doesn't trust”, “not good enough”, “must sign”, “to blame” or claims about
  what the manager or board privately want.
- No invented availability and no unmeasured channel claims.
- A theme can qualify or contradict the fan framing. The first pass does not
  support a simple “centre-back family is weakest” story; the page publishes the
  measured result.
- Provider ratings are labelled and never an individual verdict.

## Commands

```bash
uv run fitba publish              # builds themes from local data
uv run python scripts/check_themes.py
```

The daily workflow runs the guard after the matchday guard. There is no
separate network ingest: the theme layer is derived from the same local frames
and published payloads as the rest of the site.

## Adding a theme

1. Add the definition and order to `config/themes.yaml`.
2. Add a pure function in `src/fitba/analytics/themes.py` and wire it into
   `build_theme_document`.
3. Add the typed fields to `src/fitba/publish/themes.py`, regenerate
   `contracts/themes.schema.json`, and extend the guard and tests.
4. Add the component or table to `web/components/ThemeMetrics.tsx` and the
   `/themes/` page.
5. Update this document and the methodology page in the same change.
