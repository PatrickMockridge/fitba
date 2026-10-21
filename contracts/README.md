# Data contracts

Planned contracts for the ingestion and publication layers:

- `matches.yml` — match key, competition/season, date, status, score bounds.
- `player_match.yml` — minutes, goals/assists, shots and xG bounds.
- `events.yml` — period, coordinates, event type, duplicate source event ids.
- `published.yml` — JSON schema for each generated file, required fields, no
  NaN/Infinity, foreign-key existence and file-size limits.

Phase 1 implements the equivalent checks in `src/fitba/validate/checks.py` and the
publication guard in `scripts/check_publication.py`. The YAML contracts will be wired
to Pandera/Pydantic when the player/event layer lands.
