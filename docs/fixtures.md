# Match record: fixtures and match pages

**Status:** page specification for `/matches/` and `/matches/<fixture_id>/`.
**Last reviewed:** 2026-10-22.

## Purpose

Every played Aberdeen fixture in the Cormack era has one address. The page shows
what the record actually supports: the score first, then events, lineups, team
statistics, player statistics, fxG and coverage. Missing data is labelled; it is
never filled with a zero or a guess.

The scope is 2019-20 to 2026-27: 370 played fixtures at the 2026-10-22 publish,
including 19 friendlies. Friendlies are marked and excluded from form and
league aggregates. The pre-2019-20 baseline remains on the history pages.

## One fixture, one key

- Canonical key: `api:fixture:<fixture_id>`.
- Route: `/matches/<fixture_id>/`.
- Aliases: the football-data.co.uk `match_id`, the SPFL fixture id and the cup
  ids. `src/fitba/normalize/fixture_registry.py` joins them by date, competition
  and canonical team ids. An ambiguous or missing league alias is an error, not
  a guess.
- The registry reports total, played, competitive, friendly and league-alias
  counts. The generated index is `web/data/generated/fixtures/index.json`.
- The document contract is generated from `FixtureDocument` into
  `contracts/fixture-page.schema.json`; the every-page checker validates each
  document against it.

## Page order

1. Header: competition, round, date, venue, referee, score, half-time, extra
   time and penalties.
2. The read: a deterministic summary from events and measured stats.
3. Match stats: the shared league stat row first; API possession, passes, shot
   locations, saves and provider xG where available. Every row names its source.
4. fxG and provider xG, separately. fxG is never blended with provider xG.
5. Timeline: goals, assists, own goals, penalties, cards, substitutions, VAR
   and shootouts, with the score after each goal.
6. Lineups: observed formation, starting XI, substitutes and coach.
7. Player stats: provider rating and match output where available.
8. Form context: the five matches before and after.
9. Coverage: events, lineups, team stats, player stats and fxG availability.

## Depth states

- `full`: events, lineups, team stats and player stats.
- `result`: events and lineups, no team or player stats.
- `score`: score only; the event and lineup feeds are unavailable.

Every played fixture gets a page. A page is never omitted because a data class is
missing.

## The read

`src/fitba/analytics/summary.py` selects stock phrases from measured facts:
score, half-time, first goal, equaliser, late goal, comeback, red card, own goal,
penalty and shootout. The measured half is labelled `measured`; the fxG sentence
is labelled `inferred`. Missing data produces an explicit sentence.

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
