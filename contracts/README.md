# Data contracts

Planned contracts for the ingestion and publication layers:

- `matches.yml` — match key, competition/season, date, status, score bounds.
- `player_match.yml` — minutes, goals/assists, shots and xG bounds.
- `events.yml` — period, coordinates, event type, duplicate source event ids.
- `published.yml` — JSON schema for each generated file, required fields, no
  NaN/Infinity, foreign-key existence and file-size limits.
- `player-page.schema.json` — **implemented**. Closed JSON Schema for the
  player-page result document (`identity`, fixed panel order, Position, Playing
  time, Performance and Records panels). Generated from the Pydantic result
  model in `src/fitba/publish/player_page.py` and checked by
  `scripts/check_player_page.py`.
- `history-index.schema.json` — **implemented**. Strict schema for the era
  index (era, staff stints, honours, season references, scorecard, coverage).
- `history-season.schema.json` — **implemented**. Strict schema for one season
  review (manager segments, cups/Europe, recruitment, style, selection, academy,
  staff changes, review and coverage). Generated from
  `src/fitba/publish/history.py` and checked by `scripts/check_history.py`.
- `matchday.schema.json` — **implemented**. Strict schema for the upcoming
  matchday document (next fixture, form, venue splits, style lean, strength,
  predicted XIs, matchup read and coverage). Generated from
  `src/fitba/publish/matchday.py` and checked by `scripts/check_matchday.py`.
- `themes.schema.json` — **implemented**. Strict schema for the medium/long-term
  themes document (five theme blocks, evidence, player/role rows, mission
  pillars, implications and coverage). Generated from
  `src/fitba/publish/themes.py` and checked by `scripts/check_themes.py`.
- `provenance.schema.json` — **implemented**. Layer truth table, source
  contributions, migration gate and availability state.
- `availability.schema.json` — **implemented**. Curated team-news ledger and
  optional provider snapshot with source/verified_at.
- `needs.schema.json` — **implemented**. Seven role-family needs, categories,
  market routes, roster space and role profiles. No targets or fees.

Phase 1 implements the equivalent checks in `src/fitba/validate/checks.py` and the
publication guard in `scripts/check_publication.py`. The YAML contracts will be wired
to Pandera/Pydantic when the player/event layer lands.


- `former-players.schema.json` — former-player index document.
- `former-seasons.schema.json` — former-player per-season detail document.
