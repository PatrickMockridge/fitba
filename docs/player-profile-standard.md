# Player profile standard

**Status:** normative. Last reviewed 2026-10-23.

This document defines the shared standard for every dedicated player profile.
Where a component, page or habit disagrees with this page, this page wins.

## Profile types and tiers

There are two dedicated profile routes:

- `/players/<playerId>/` — Aberdeen profile, **extended** tier. It uses
  `PlayerPageDocument` and adds the role, playing-time, performance and records
  panels. Current squad members (`status == "squad"`) also show Availability
  and Recent matches.
- `/scouting/player/<playerId>/` — licensed-feed scouting profile, **standard**
  tier. It uses the pool/search model and adds scouting context: current and
  stats club, priority, Europe, value index and archetypes.

Loan-out Aberdeen players keep their role and loan record; Availability and
Recent matches are not applicable to them.

## Section order

Every profile follows this order. Sections marked "extended" are present only
on the Aberdeen route; "current squad" sections are present only for current
Aberdeen squad members.

1. **Profile header** — name, role, age, nationality, status/loan (Aberdeen) or
   current club, stats club, league, role and U23 (scouting). One visible H1.
2. **Statistical profile** — exactly two Nightingale rose figures:
   **Overall profile** and **Position profile**, in that order. Each figure has
   labelled axes and an accessible title/description carrying the exact values
   and cohort n; there is no duplicate rose table.
3. **Key facts** — minutes, appearances, provider rating and cohort percentile,
   with the cohort basis and n. The provider rating is labelled opaque and not a
   verdict.
4. **Role and cohort basis** — the Aberdeen Position panel, or the scouting
   role family/share/status and cohort basis.
5. **Output** — the Aberdeen Playing time and Performance panels, or the
   scouting Per-90 rates table.
6. **Profile scores** — archetype raw and adjusted scores and coverage.
7. **Context** — Aberdeen Availability and team news (current squad); scouting
   priority arithmetic, Europe and current/stats club.
8. **Recent matches** — Aberdeen current squad only: latest 10 competitive
   current-season rows with date, competition, opponent, venue, score, result,
   minutes, rating, goals and assists.
9. **Coverage and limits** — the source, cohort, confidence and explicit
   limitations.
10. **Back links** — the relevant squad, matchday, recruitment, scouting,
    method and sources links.

The Aberdeen extended panels keep their existing ids and order after the
profile, availability and recent-match sections.

## Rose rules

- **Cohort:** both figures compare with the same role-family cohort (provider
  position group when the role cohort is below its minimum), at the league
  cohort minutes threshold. Aberdeen uses Premiership-only statistics; scouting
  uses the row's league statistics. No cross-league percentiles.
- **Axes:** the overall figure is the shared all-round set; the position figure
  is the role-specific set from `config/player-rose.yaml`.
- **Encoding:** equal-angle sectors; radius is `sqrt(percentile / 100)`, so
  sector area is proportional to the percentile. Grid rings are 25/50/75/100.
- **Percentile:** midrank rank in the cohort, 0–100, one decimal. Higher is
  better after direction handling. `conceded_p90` is ranked on negated values;
  direction is never applied in React.
- **Missing:** a missing value is null, omitted from the petals, and named in
  the accessible description. It is never zero, imputed or drawn as a zero petal.
- **Status:** `available` at four or more non-null petals, `partial` at one to
  three, `unavailable` at none. An unavailable figure states why
  (`below_min_minutes`, `no_role`, `cohort_too_small`, `no_values` or
  `not_built`).
- **Text alternative:** the chart is `role="img"` with a unique title and a
  description that lists the raw value, percentile and per-axis cohort n. The
  page keeps its existing per-90/performance tables; the rose does not repeat
  them as a second table.

## Number and copy rules

- The rose catalogue and axis sets live in `config/player-rose.yaml`; thresholds
  come from `config/scouting/model.yaml`. Do not duplicate a threshold in code
  or copy.
- The provider rating is opaque and league-relative; it is not a verdict and
  not a cross-league rank.
- No contracts, wages, fees, release clauses or recommendations are claimed.
- Availability is shown only from the curated ledger, with source and
  verification date; unknown is not an injury.
- A missing recent-match field is a dash, not zero. Player match statistics are
  partial and the coverage note says so.

## Implementation

- Shared presentation: `web/components/ProfileHeader.tsx`,
  `web/components/ProfileSection.tsx`, `web/components/PlayerRose.tsx`.
- Shared types: `web/lib/rose.ts`; the two result documents stay separate.
- Contracts: `web/contracts/surfaces.json` is static-path only. The dynamic
  profile routes are guarded by the bespoke profile-page checker and by
  `docs/page-contracts.md`; adding the shared markers does not remove or
  weaken an existing contract.
