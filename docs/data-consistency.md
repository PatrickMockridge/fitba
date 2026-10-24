# Data consistency and scope

**Status:** canonical note on cross-surface derivations. Last reviewed
2026-10-24.

fitba publishes one fact through several pages. The same player appears on
`/squad/`, `/players/<id>/`, `/scouting/`, `/analysis/` and `/recruitment/`; the
same match appears in the fixture index, the match page and the xG payload.
Those projections must not disagree about a fact they both claim.

A number may legitimately differ between pages when the **scope** differs. The
scope must then be named beside the number. A number may not differ because two
publishers silently applied different filters to the same scope.

## Scope vocabulary

| Scope | Meaning |
|---|---|
| `league` | One competition, current season, club rows only. No cups, friendlies or loan-club rows. |
| `all_competitions` | Aberdeen league, cup and European club rows; friendlies excluded; loan-club rows excluded. |
| `loan` | The registered loan club only. Never mixed into an Aberdeen total. |
| `official_list` | The official AFC men's team page, including the On loan section. Currently 34 players. |
| `active_squad` | The official list minus `loan_out`. Currently 29 players. |
| `register_current` | Confirmed transfer-register loan rows for the current season. Currently 9 out. |
| `register_all_time` | Every confirmed loan row in the register. Currently 31 out. |
| `event_reconstructed` | Starts, substitute appearances and minutes reconstructed from lineups and substitution events. |
| `provider` | The licensed provider's season rows. |
| `regulation` | The 90/120-minute result, used for W-D-L and league points. |
| `outcome` | The result including a penalty shootout; published separately. |

`config/scopes.yaml` is the machine-readable vocabulary. A published block
should carry its scope id; a table column or caption must name it when the page
also shows another scope.

## One fact, one home

| Fact | Canonical owner |
|---|---|
| Official squad, order, number, loan section | `publish/squad.py` |
| Loan scopes and reconciliation | `analytics/loans.py` |
| Player club totals and rating | `analytics/player_facts.py` |
| Playing time | `ingest/match_data.py` via `player_facts` |
| Percentile rank | `analytics/percentiles.py` |
| Match result and shootout outcome | `analytics/records.py` |
| Current/historical team match stats | `analytics/team_stats.py` |
| Availability universes | `analytics/availability_facts.py` |
| Next fixture | `analytics/schedule.py` |
| Role family and group | `config/roles.yaml` through `normalize/roles.py` |

The display layer reads the published value. It does not sum, re-filter,
re-rank or re-round a published fact. The only permitted client calculation is
formatting through `web/lib/format.ts` and an explicit interactive lens in
`web/lib/scouting-filters.ts`.

## Deliberate scope differences

These are not inconsistencies, provided both numbers are labelled:

- **Loans.** The official list says 5 out; the 2026-27 register says 9; the
  all-time register says 31. The four register-only loanees are retained
  profiles, not squad members.
- **Availability.** The official list has 34 players (2 known / 32 unknown);
  the active squad has 29 (2 known / 27 unknown). Analysis uses active;
  availability and needs use the official universe and name it.
- **Minutes and output.** The headline player output is all Aberdeen
  competitions. The league comparison is Premiership-only and is labelled
  separately. Loan-club output is shown on the player profile, not in the
  squad row.
- **Percentiles.** Player and rose percentiles are a Premiership-cohort
  comparison of the league-only rating. All-competition output is not ranked
  against a league-only cohort.
- **xG.** The aggregate table is Scottish Premiership only. Cup and European
  fxG is shown on match pages and is not added to the league aggregates.
- **Team stats.** Current-season shots, SOT, corners and fouls use
  API-Football; historical seasons use football-data. The source travels with
  the number.

## The consistency guard

`scripts/check_consistency.py` reads the published corpus and runs named
checks:

- squad counts, role buckets and roster metadata reconcile with player rows;
- official and register loan counts reconcile and every official loanee is in
  the current register;
- squad totals and playing time reconcile with their source rows;
- player pages use the same minutes and rating as the squad payload;
- every xG aggregate equals the sum of its match rows, and fixture xG equals
  the xG payload row;
- fixtures, match pages and shootout labels agree;
- scheduled counts and the matchday fixture use the same schedule rule;
- availability counts sum to their declared universes;
- coverage counts equal the payloads they summarise.

The same checks run inside `fitba publish`; a failure writes
`audit/consistency.json` and blocks the atomic swap. CI also runs
`make consistency-check`. The audit is a disagreement detector, not a claim
that a shared formula is correct; the metric audit covers formula verification.

## Commands

```bash
uv run python scripts/check_consistency.py
make consistency-check
uv run fitba publish --season current --profile public --require-validation
uv run python scripts/check_metrics.py --strict
make check
make check-all
```
