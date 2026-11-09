# Season overview

**Status:** live. Last reviewed 2026-11-08.
**Route:** `/analysis/` (the old `/themes/` route redirects here).
**Nav and H1:** Season overview.
**Payload:** `analysis/summary.json`.
**Guards:** `scripts/check_analysis.py`, `scripts/check_web_contract.py`.

## Purpose

The season overview is the one-scan bridge between the next matchday, the
results and form record, the squad and scouting. It answers, in order:

1. where Aberdeen rank in the league this season;
2. what Aberdeen play next;
3. who is genuinely available;
4. what the season is for;
5. which squad decisions are coming;
6. where the evidence lives.

The hero record is the league table row, not a second derivation. A finished
official result appears in the hero, the table and the form guide together.

It is not a claim register, a second matchday dashboard or a transfer-window
countdown. The old case page and owner view are not rendered here. A labelled
within-Premiership provider-xG rank is shown; the full fxG model table,
calibration and match-level ranges stay on `/analysis/xg/`.

## Sections

1. **Hero** — position, points, matches played, goal difference and last-five
   form. No opinion thesis and no duplicate fixture row.
2. **League rankings** — Aberdeen's within-Premiership rank for xG for, xG
   against, possession, goals scored, goals conceded and goal difference, with
   the direction, league median and leader; plus the full 12-team Premiership
   table with per-match goals, xG, xGA, possession and points. Scope, sources,
   coverage, as-of date, tie rule and unknown states stay visible.
3. **Next up** — the next three competitive fixtures with date, competition,
   opponent, venue (H/A/Neutral), local kickoff and status. Links to the
   six-game matchday lookahead and the full `/matches/` schedule.
4. **Availability and selection** — counts, official AFC team news, a
   **Team news needing review** block, derived selection signals and a capped
   selection watch. “Available” means a verified ledger entry, not fit.
   Contradicted claims are `unknown`, with the original claim, source,
   verification date and match evidence in the review block. Served suspensions
   are labelled `served`, not current.
5. **Season aims** — at most three analyst-set aims with target, current value
   and status. The top-six split, the League Cup semi-final and the European
   route are separate; the block says the targets are not published club
   targets.
6. **Squad decisions** — measured age, minutes and role lenses, loan-outs and
   needs priority. No value index, valuation, fee, wage, contract expiry or
   “will leave” copy.
7. **Bridges** — Matchday, Matches, Squad, Scouting; secondary links to fxG and
   confirmed business. Transfers are not presented as a window countdown.
8. **Coverage** — known/unknown availability, card and bench coverage, fixture
   conflicts and limitations, with links to metrics and sources.

## League ranking rules

- Join the current Premiership table to `team_match_features.parquet` on the
  canonical `team_id`; reject any feature row outside the table.
- Use the published provider-xG precedence: football-data.co.uk HxG/AxG, then
  API-Football `expected_goals` as the fallback. xG against is the opponent's
  provider xG in the same match.
- Publish per-match rates, not totals: teams have played 11–13 matches.
- Rank on the published two-decimal values: `rank = 1 + count of teams with a
  strictly better value`; ties share the better rank. Higher is better for xG
  for, possession, goals for and goal difference; lower is better for xG
  against and goals against.
- Publish the league median and leader, and the mean for audit transparency.
  Rank only when coverage is complete for every table team; a missing value and
  its rank are null, never zero.
- Provider xG is not fxG. Aberdeen's local fxG is labelled context below the
  rank and is not part of it.
- Possession is API-Football's provider-reported value, published as a labelled
  season average. It is not used in the matchday style lean.
- The scope is the Premiership only. No cross-league or cross-tier comparison
  is made.

## Availability rules

- Official availability is the curated AFC ledger only: source, confidence and
  verification date stay visible. The active universe is the 29-player squad
  (official list minus loanees out); the 5 official loan-outs are separate, and
  the availability and needs surfaces report the 34-player official universe.
- The provider injured boolean is never team news.
- Calculated suspensions are competition- and fixture-scoped. A rule is
  published only with its source and version; until then the row is `watch` or
  `review_required`, never a player ban.
- The feed’s second-yellow flag is unreliable; derive second yellows from
  same-match yellow+red rows and test fixture 1629022.
- Inferred absence requires two consecutive omissions from named squads with
  complete bench coverage, established squad inclusion and no official
  override. It is labelled “not in the last two matchday squads — reason not
  published” and is never an injury diagnosis.
- Selection watch is a projection from the matchday model, labelled “not team
  news”, capped at three.

## Fixture rules

- The merged schedule uses the normalized history fixtures plus the SPFL club
  feed; kickoff is converted to Europe/London.
- Same-team, same-day cross-competition conflicts are retained and marked
  `conflict_review`; they are excluded from next-up, lookahead, aims and
  inference. The 31 October Rangers league/League Cup double is the regression
  case.
- Friendlies stay in `/matches/` labelled, but are excluded from the next-up
  and lookahead. Scheduled fixtures have no page and are not in the sitemap.

## What this page does not do

- It does not diagnose injury, infer a return date or call an inferred absence
  “injury”.
- It does not publish a ban from an unverified rule.
- It does not claim a fee, wage, release clause, contract expiry, target or
  transfer recommendation.
- It does not treat a provider rating or a small-sample percentile as a verdict.
- It does not render a full fxG model table, calibration table, match-level fxG
  range or provider-vs-fxG comparison; those stay on `/analysis/xg/`.
- It does not blend provider xG with fitba fxG, or rank across leagues.
- It does not recompute a number in React; the publisher emits the document.

## Changing it

1. Update `config/analysis.yaml` for screening thresholds, display limits and
   the league-ranking policy.
2. Update `config/suspensions.yaml` only with a sourced, versioned rule.
3. Add or change the payload fields in `src/fitba/publish/analysis.py` or
   `src/fitba/analytics/league_stats.py`; register every numeric leaf in
   `config/metrics.yaml` and the changelog.
4. Update `web/contracts/surfaces.json`, `docs/page-contracts.md` and the pinned
   manifest test when a contracted marker or column changes.
5. Run `make check`, `make check-all`, both web builds and
   `uv run python scripts/check_analysis.py`.
