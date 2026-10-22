# Career roles and multi-position eligibility

**Status:** live for the 2026-27 Aberdeen squad. Last reviewed 2026-10-21.

A player is not one position. A full-back can play in a back four or as a
wing-back in a back five. A defensive midfielder can also play centre midfield,
or fill in on the left. A centre-back can cover right back at a stretch. The
career layer models this as an **eligibility set**, using Football Manager-style
position slots, rather than forcing one label.

## What the data can support

API-Football has no career endpoint:

- `/players?id=X&season=S` returns one season, with one entry per team/league
  and generic position, lineups and minutes — no grid.
- `/transfers?player=X` returns the full transfer history in one call.
- A specific historical position needs `/fixtures?team=T&league=L&season=S`,
  then one `/fixtures/lineups?fixture=F` per played fixture.
- There is no player match-log endpoint.

The backfill therefore runs on demand, not every day. It is capped at the
current season plus two previous seasons, 15 checked fixtures per player-season,
a target of six starts, 1,500 network requests per run, a 0.25-second minimum
interval and a resumable state table.

At the last run: 694 evidence starts, 59 complete player/season/team/league
pairs, 55 capped pairs, 0 errors and 434 network calls. Thirty-three of the 38
players had some role evidence; the rest are explicitly unknown, not
zero-filled.

The backfill also performs an **Aberdeen club-season scan** for the two prior
seasons (2025-26 and 2024-25): every played Aberdeen fixture is checked once,
regardless of whether the individual player has a provider stats entry or a
nonzero lineups count. This is what covers players such as Frame and Gyamfi,
whose provider rows were missing or reported `lineups: 0`. The scan reports its
fixtures and starts in `career_roles_meta.json`; the per-player cap does not
apply to it.

## Position slots

The slots are in `config/roles.yaml` under `career.slots`:

| Slot | FM label | Roles | Broad groups | Side |
|---|---|---|---|---|
| GK | GK | Goalkeeper | goalkeeper | — |
| D_C | D C | Centre back | defender | centre |
| D_WB_L | D/WB L | Left back / left wing-back | defender, midfielder | left |
| D_WB_R | D/WB R | Right back / right wing-back | defender, midfielder | right |
| DM_C | DM C | Defensive midfielder | midfielder | centre |
| M_C | M C | Centre midfielder | midfielder | centre |
| AM_C | AM C | Attacking midfielder | midfielder | centre |
| M_L | M L | Left midfielder | midfielder | left |
| M_R | M R | Right midfielder | midfielder | right |
| AM_L | AM L | Left winger | attacker | left |
| AM_R | AM R | Right winger | attacker | right |
| ST_C | ST C | Centre forward | attacker | centre |

This is the point of the model: a full-back / wing-back is one slot and counts
as **both** a defender and a midfielder; a DM is a midfielder; a winger is an
attacker. The broad squad filter uses these group memberships.

## Evidence tiers

Career starts are starting-XI observations from lineups. Substitute appearances
are excluded. Each slot gets a tier:

- **primary** — the most-started slot. It needs at least 5 starts, 40% of role
  starts and a 15-point lead over the next slot; otherwise the career is
  `low_evidence` or `mixed` and the primary is provisional or withheld.
- **secondary** — at least 3 starts and 15% of role starts.
- **stretch** — at least one start but below the secondary threshold. This is
  the “in an injury crisis he could just about play left back” option; it is
  shown, not promoted to the primary.
- **other** — no starts in the configured window.

A single stray start cannot relabel a centre-back as a striker. The heat map and
the role-mix bar show the whole distribution, not just the primary.

## Career summary

For each player, the published `career_role` block contains:

- `primary_slot` (slot, FM label, role code, family, side, groups, starts, share);
- `slots` / `eligibility` — every slot with starts and a tier;
- `broad_groups` and `sides` — the union of eligible slots;
- `fm_label` — a compact FM-style label, e.g. `D/WB R` or `DM/M C/L`;
- `seasons` — per-season slot shares for the heat map;
- `scopes` — Aberdeen, previous club, loan club and national team shares;
- `history` — season/team/competition/role rows.

The current Aberdeen role is also a multi-slot summary (`current_role.slots`,
`current_role.fm_label`, broad groups and sides). Current usage is a small
sample, so a slot with at least 15% of current starts is secondary; a one-start
role is a stretch. This is how a fluid current role — Olusanya across right
wing, attacking midfield, centre forward and left wing — stays visible instead
of being flattened.

The display label is the career primary by default. It switches to the current
Aberdeen role only when the current role is clearly and obviously different:

- 5+ current starts with a role;
- 40%+ of current starts in that family;
- 10+ career starts over at least two seasons;
- the current family is under 25% of the career record;
- the current and career families are in different broad groups.

That last rule blocks near-neighbour relabels such as left back to right back or
centre back to defensive midfielder. The career distribution is never
overwritten; the current role is a display override, not a replacement.

## Why this is general, not Aberdeen-only

Formations are fluid and players increasingly cover what used to be called
utility roles: inverted full-backs, inside forwards, midfielders dropping into a
back three, the total positional fluidity associated with Atalanta. A single
nominal position cannot represent that. The slot/eligibility model is therefore
the general case; Aberdeen is one expression of it, especially in the central
midfield/defence balance and the way wide players are used.

The kick-off grid records the nominal slot, not the in-possession role. For
interpretations the grid cannot see, `reference/role_notes.yaml` carries a small
curated note (inside forward, inverted full-back, utility player, No. 10). The
note is context, not role evidence: it never changes the slot arithmetic or the
filter. The Olusanya note explains why a career centre-forward is used as a
current inside forward/No. 10 while Nisbet and Mouloua hold the pure CF slots.

## Broad filter

The squad page filters on:

- **Group:** all, goalkeepers, defenders, midfielders, attackers.
- **Side:** all, left, centre, right.

A player appears if **any** eligible slot matches. That means a full-back can
appear under both defenders and midfielders, and a utility player can appear
under more than one side. A stretch slot is included but labelled; it is not a
claim that the player is a regular there.

The main squad table shows only the primary position. Clicking the position
opens the inference panel: current Aberdeen usage, career clubs/seasons, slot
tiers, heat map and tactical context. The player profile keeps the current role
in view and hides the full career evidence behind “How this position was
inferred”. The detail is background, not the headline.

## Refresh

Historical position evidence does not change daily or weekly. Run:

```bash
uv run fitba career backfill --max-requests 1500
uv run fitba career status
```

at the start of a season, after a transfer/loan, or when a new formation map is
added. The daily `fitba squad` job does not fetch historical lineups; it rebuilds
the current Aberdeen slice locally (`fitba career refresh`) and publishes the
cached career history.

## Schemas

Under `data/normalized/career/`:

- `player_role_evidence.parquet` — one row per player per start, with season,
  fixture, team, scope, role, grid, formation and policy version.
- `player_career_roles.parquet` — starts and weighted starts per
  player/season/team/scope/competition/role.
- `career_backfill_state.parquet` — resumable player/season/team/league state.
- `career_roles_meta.json` — coverage, request count, budget, errors and
  unknown-role reasons.

The current Aberdeen slice is copied from `player_appearances.parquet`, so it
matches `player_roles.parquet` exactly.

## Guards

- `scripts/check_career_roles.py` validates evidence, aggregates, state,
  slots/tiers, the display decision and the current Aberdeen crosswalk. It has a
  `--published-only` mode for a fresh checkout.
- `scripts/check_roles.py` remains current-season only.
- `scripts/check_squad.py` validates the published eligibility blocks and
  summary counts.
- `tests/test_career_roles.py` covers equal weighting, stray starts, low
  evidence, mixed roles, the override threshold, loan/national evidence and the
  no-evidence fallback.
- `tests/test_career_ingest.py` covers scope, caps, resume and the shortcut.
