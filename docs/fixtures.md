# Results and fixtures: fixtures and match pages

**Status:** page specification for `/matches/` and `/matches/<fixture_id>/`.
**Last reviewed:** 2026-10-22.

## Purpose

Every Aberdeen fixture in the Cormack era has one address. Played fixtures have
a full page; the remaining scheduled fixtures are listed on `/matches/` but do
not have a page. The page shows
what the record actually supports: the score first, then events, lineups, team
statistics, player statistics, fxG and coverage. Missing data is labelled; it is
never filled with a zero or a guess.

The scope is 2019-20 to 2026-27: 367 canonical played fixtures at the last
check, plus the remaining scheduled fixtures from the merged season schedule at the
2026-10-22 publish, including 16 friendlies. Three provider duplicate records
(different fixture ids for the same match) are retained as labelled alias pages
but excluded from counts, search and navigation. Friendlies are marked and
excluded from competitive season and player aggregates. The pre-2019-20 baseline
remains on the history pages.

## One fixture, one key

- Canonical key: `api:fixture:<fixture_id>`.
- Route: `/matches/<fixture_id>/`.
- Aliases: the football-data.co.uk `match_id`, the SPFL fixture id and the cup
  ids. `src/fitba/normalize/fixture_registry.py` joins them by date, competition
  and canonical team ids. An ambiguous or missing league alias is an error, not
  a guess.
- Duplicate records are detected by date, competition and the unordered team
  pair with a compatible score: `870984`/`871150`, `870479`/`891298`/`922189`.
  The canonical record wins; the aliases carry `duplicate_of` and are excluded
  from counts and navigation.
- The registry reports canonical total, played, competitive, friendly, alias and
  duplicate counts. The generated index is
  `web/data/generated/fixtures/index.json`.
- The document contract is generated from `FixtureDocument` into
  `contracts/fixture-page.schema.json`; the every-page checker validates each
  document against it.

## Page order

1. Header: competition, round, date, venue, referee, score, half-time, extra
   time and penalties.
2. Scoreboard: final score, goals with scorer/minute/assist/penalty badge, red
   cards with straight-red vs second-yellow labels, shootout score and the
   Aberdeen/opposition team key. See [match-scoreboard.md](match-scoreboard.md).
3. The read: a deterministic summary from events and measured stats.
4. Match stats: the shared league stat row first; API possession, passes, shot
   locations, saves and provider xG where available. Every row names its source.
5. fxG and provider xG, separately. fxG is never blended with provider xG.
6. Timeline: goals, assists, own goals, penalties, cards, substitutions, VAR
   and shootouts, with the score after each regular goal.
7. Lineups: observed formation, starting XI, substitutes and coach.
8. Player stats: provider rating and match output where available.
9. Coverage: events, lineups, team stats, player stats and fxG availability.
10. Form context and the previous/next links.

Aberdeen is red throughout the scoreboard, stats, fxG sides, timeline, lineups
and player stats. The opponent is neutral. Team names and a visible team key
remain, so colour is never the only cue.

## Depth states

- `full`: events, lineups, team stats and player stats.
- `result`: events and lineups; the coverage block lists which stat classes are
  also present.
- `partial`: at least one detail class (events, lineups, team stats or player
  stats) but not both events and lineups.
- `score`: none of the four detail classes; the score is authoritative.

The label is the highest record class present, not a claim that other classes are
absent. The coverage block is the authoritative list.

Every played fixture gets a page. A page is never omitted because a data class is
missing.

## The read

`src/fitba/analytics/summary.py` selects stock phrases from measured facts:
score, shootout, comeback, decisive late goal, red card, own goal, penalty and
every scoring event. The measured half is labelled `measured`; the fxG sentence
is labelled `inferred`. A shootout is named before the draw branch. A late-win
phrase requires a one-goal margin and a decisive late goal; it is never used for a
multi-goal defeat. When the event feed is absent the read says so and does not
print "0 goals"; when it is partial, it says the record does not reconcile. Every
recorded goal gets a bullet with scorer, minute and score after.

The read never says "deserved", "dominated", "lucky", "should have won" or
"bottled". It never predicts a result and never turns a player into a verdict.
Every number in the summary must appear in the fixture payload; the guard
enforces this.

## Coverage and sources

- League scores and shots: football-data.co.uk.
- Events, lineups, player match stats and cup/European team stats: API-Football.
- Provider xG: football-data.co.uk 2026-27 SC0 and API-Football where returned.
- Missing provider team statistics are `unavailable`, not zero.

## Adding or changing a fixture page

- Do not edit `web/data/generated` by hand. Run `uv run fitba publish`.
- A new metric or a changed fixture field needs a registry entry, audit, test and
  `docs/metric-changes.md`.
- Run `uv run python scripts/check_fixture_pages.py` after a build. It checks
  every document and every built page, score/timeline reconciliation, required
  markers, summary-number containment and banned verdict language.
- Update `web/contracts/surfaces.json` and `docs/page-contracts.md` if a
  contracted marker changes.
