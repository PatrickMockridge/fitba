# SQL

DuckDB views and marts. The phase-1 warehouse is built in `src/fitba/warehouse/build.py`
and creates `fact_match_result`, `fact_team_match_stats`, `mart_league_table`,
`dim_competition`, `dim_team` and `dim_season`.

Planned views:

- `10_dimensions.sql` — source, competition, season, team, player, match.
- `20_facts.sql` — results, team/player match stats, shots, events, lineups.
- `30_marts.sql` — tables, form, player season/percentiles, style, scouting, loans,
  sequences.
- `40_checks.sql` — cross-table assertions run by `fitba validate`.

Keep the SQL portable to DuckDB and read-only against parquet paths under `data/`.
