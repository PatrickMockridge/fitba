# Roles, starts and shape

**Status:** live for the 2026-27 Aberdeen season. Last reviewed 2026-10-21.

Role is a primary dimension of the player data, not a decorative attribute. A
left back, a centre back and a holding midfielder are different jobs; grouping
them into “defender” or “midfielder” is not enough for scouting or team analysis.
A player can also play several positions. The current-season role block is the
Aberdeen usage; the career role block is the multi-position eligibility set. See
[career-roles.md](career-roles.md) for the FM-style slots, tiers and broad
group/side filter.

## Where a role comes from

The licensed API-Football team sheet (`/fixtures/lineups`) gives, for both teams:

- the formation string (`"4-2-3-1"`, `"5-3-2"`, ...);
- the starting XI, with each starter's grid slot (`"2:4"`);
- the substitutes, who have `grid: null`;
- substitution events, where the incoming player is the event's `assist`.

The grid is the evidence. The formation shape is derived from the row counts of
the starting-XI grid, not trusted from the formation string alone. A null
formation with a valid grid still yields a role. If the string and the grid
disagree, the mismatch is recorded and the grid wins.

The roles live in `config/roles.yaml`:

| Code | Label | Family | Side |
|---|---|---|---|
| GK | Goalkeeper | goalkeeper | — |
| CB | Centre back | centre_back | central |
| RB / LB | Right back / left back | full_back | right / left |
| RWB / LWB | Right / left wing-back | wing_back | right / left |
| DM | Defensive midfielder | defensive_midfield | central |
| CM | Centre midfielder | central_midfield | central |
| AM | Attacking midfielder | attacking_midfield | central |
| RM / LM | Right / left midfielder | wide_midfield | right / left |
| RW / LW | Right / left winger | wide_forward | right / left |
| ST | Centre forward | centre_forward | central |

The formation map is explicit per shape. `4-2-3-1`, `4-1-4-1`, `3-5-2`,
`5-3-2`, `4-1-3-2` are the observed 2026-27 shapes; common alternatives are
included. A shape that appears in a starting XI without a map fails
`scripts/check_roles.py`; it is not guessed from geometry.

## Role evidence

- **Starters only.** A role is assigned from the starter's grid slot. A
  substitute has no grid slot, so a substitute appearance carries playing time
  but no role.
- **No inference.** Role is not derived from preferred foot, a generic squad
  position, a shirt number, or the player a substitute replaced.
- **Goalkeeper fallback.** When a grid is missing but the lineup marks the
  starter `pos=G`, the role is `GK` from the lineup position. An outfield player
  without a grid is unknown.
- **Primary role.** Role rows are grouped by family; the family with the most
  starts wins, then family minutes, then the role with the most starts, then
  role minutes, then the config order. A player's full role history is
  published, not just the primary label.
- **Coverage.** `starts_with_role / starts_total` is published. A player who
  started some matches without a grid is `partial`, not silently promoted to a
  clean role history.

Examples from the current data: Cadden is a right back (6 RB starts, 4 RWB,
1 AM), Milne a centre back (2 CB, 1 RB), Ronan a centre midfielder (6 CM, 3 AM,
1 DM), Olusanya a right winger (wide-forward family 3 starts), Nisbet a centre
forward (13 ST).

## Starts, substitutes and minutes

`player_appearances.parquet` has one row per player per fixture for both teams.
It is built from the lineup and substitution events:

- starters begin at minute 0;
- a substitute begins at the substitution minute;
- a substitution or red card closes the outgoing interval;
- extra time uses a 120-minute match length;
- `minutes_started` and `minutes_as_sub` are separate, and sum to the on-pitch
  minutes.

The aggregates are `player_roles.parquet` (player/team/season/role) and
`playing_time.parquet` (player/team/season/competition). The squad table uses
Starts and Sub rather than a single “apps” column; the player profile shows the
minutes split by competition.

The current feed has a formation grid for 13 of 15 Aberdeen matches. The two
early League Cup matches have no grid; their starts and minutes are still
counted, but their roles are unknown. That is reported, not filled.

## Shape and balance

`team_shapes.parquet` records the kick-off formation for each team in each
covered fixture, plus centre-back, wing-back, holding-midfield and forward
counts. The club page’s **Shape and balance** view uses it to show:

- matches and starts by shape, with the matchday sequence visible;
- record, goals conceded per match and goalkeeper saves per match by shape;
- centre-back average provider rating by shape;
- the 2-vs-3-centre-back split and whether a defensive midfielder started.

Provider ratings are labelled as provider ratings, not re-modelled. Sample sizes
are small and the shape is not randomly assigned, so the view is descriptive,
not causal.

The feed does **not** report a formation change after a substitution. A reported
mid-game switch is recorded only in `reference/shape_notes.yaml`, with a fixture,
team, minute, from/to shapes, source URL and confidence. It is shown separately
and never counted as a kick-off shape. The absence of a note means “not
recorded”, not “no change”.

## League-agnostic model

The appearance and shape tables carry `team_id` and are not Aberdeen-specific.
Aberdeen is the first published view, not a special case. Any team in a covered
competition can use the same role, playing-time and shape tables; coverage per
league is reported. Where the provider does not return a lineup or grid, the
role is unknown rather than borrowed from a generic position.

Loan-club lineups are not ingested in this change. A loanee’s Aberdeen role
history is empty if they have not played for Aberdeen; the loan-club provider
stats remain on the profile.

## Files and guards

- `config/roles.yaml` — taxonomy, families, sides and formation maps.
- `reference/shape_notes.yaml` — curated, sourced mid-game switches; empty by
  default.
- `src/fitba/normalize/roles.py` — shape/grid parsing, role selection, config
  validation.
- `src/fitba/ingest/match_data.py` — appearances, roles, playing time,
  per-match stats and team shapes.
- `src/fitba/publish/shapes.py` — the shape/balance payload.
- `scripts/check_roles.py` — role evidence, formation coverage, starts/minutes
  arithmetic.
- `scripts/check_shapes.py` — shape counts, per-match joins and shape-note
  provenance.
- `tests/test_roles.py`, `tests/test_shapes.py`.

The 2026-27 rebuild and formation churn are recorded in
[the context diary](context/aberdeen-2026-27.md).
