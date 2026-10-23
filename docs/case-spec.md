# Case archive: matchday evidence strip

**Status:** superseded for `/analysis/` by [analysis.md](analysis.md). Retained
for the compact matchday evidence strip and the retained `themes/aberdeen.json`
payload.
**Owner:** patrickmockridge. **Drafted:** 2026-10-22.

## Decisions recorded

- **Voice:** the owner's opinion leads, stated and attributed as opinion. The
  chairman's vision and own words frame it. Fitba tests the record.
- **Name:** Case archive. The public season page is `/analysis/`.
- **Small samples:** state the claim, then the count, then what is and is not
  established. Do not hold the claim.
- **Structure:** claim-led rebuild with a property-based contract change. Six
  page-level claims.
- **Thelin run:** "seven straight league wins". Do not use "record" unless a
  sourced comparator is approved.
- **Owner statement:** the owner's thesis in the brief is the source; it is
  attributed to the owner and edited only for grammar.
- **Chairman frame:** a summary of the club's stated approach from
  `reference/history/era.yaml` and `docs/history.md`, labelled as a summary,
  not a direct quotation.

## Purpose

This document now describes the retained case archive. The claim cards are used
only by the compact matchday evidence strip; the public season page `/analysis/`
is the season overview described in [analysis.md](analysis.md). It is not a
dashboard, a data-science appendix or a verdict machine.

## Reader promise

A numerate, literate Aberdeen fan who is not a data scientist can read the page
once and say:

1. what the owner thinks and why it matters;
2. which parts the record supports, which are mixed, and which cannot be tested
   yet;
3. what data would reduce the uncertainty; and
4. what would change the owner's mind.

No jargon, no taxonomy lesson before the argument, no caveat attached to every
sentence, no invented model.

## Voice and attribution

- **The opinion is the owner's.** It is labelled "The site owner's view" or "Our
  view" once, at the top. It is not presented as a finding.
- **The chairman's frame is sourced.** Use two or three short official quotes or
  attributed statements from Dave Cormack, with source URLs and dates. If a
  quote cannot be sourced, use a labelled summary from
  `reference/history/era.yaml`; never invent a quote.
- **Fitba tests the record.** Each claim carries a status: **Supported**,
  **Mixed**, **Not supported** or **Can't test yet**.
- **The page can say the site owner's view is not supported.** That is the point of
  publishing it as a view.
- **Level is named every time.** Player, manager, squad or club. No claim about
  boardroom intent, wages or private valuations.

## The argument in one paragraph

Owner statement. The paragraph below is the owner's thesis from the brief,
edited only for grammar and attributed to the owner.

> I think the club is trying to lower its variance and become harder to beat:
> a high press, a direct and counter-attacking game, balls over the top for
> Olusanya, and three physical centre-backs at set plays. The cost has been
> unforced errors, cheap penalties and getting the players to gel. Thelin's side
> had a fast start, a long winless run, the Scottish Cup and then a recycled
> squad; Morris was sold and we lost a main goal threat; injuries and opponents
> adapting followed. Robinson steadied it. The question is whether the model is
> now producing a more resilient team, or just a different set of trade-offs.

This paragraph is the spine. Everything below either supports it, complicates
it or says it cannot yet be tested.

## Page structure

1. **The frame.** Two or three sourced sentences from the chairman on what the
   club is trying to do. Then the site owner's view, attributed. Then the one-
   paragraph case above.
2. **The team now.** What the reader watched on Saturday: league record, shape
   churn, the current question.
3. **The defence.** Three at the back; the Tobers/Knoester availability
   question; what the record does and does not show.
4. **The attack.** Goals for and against, where the goals come from, the last
   five versus the season, and the set-play/error gap.
5. **The managers.** Thelin's start and collapse, the Scottish Cup, Leven, and
   Robinson's first 18 league matches. "Steadying" as a reading, not a fact.
6. **The squad.** The 2026-27 rebuild: arrivals, exits, age, U21 minutes, the
   Morris sale and what replaced him.
7. **The chairman's record.** Seven seasons, the league range, the cup, Europe,
   the sales, the manager spells. What the model buys and what it costs.
8. **What the record cannot say.** One block: availability, injury cause, set
   pieces, errors, pressing, possession, mid-game shape, wages, board intent.
9. **Go deeper.** Links to the full evidence tables, methodology, transfers,
   recruitment, history and metrics.

The page is a sequence, not a grid of equal cards. Headings are declarative and
plain: "The team now", "The defence", "The attack", "The managers", "The squad",
"The chairman's record". No metaphors in headings.

## The claim unit

Every claim uses the same six lines, in this order:

1. **The claim.** One sentence in football language.
2. **The count.** The number, the sample and the period. "4 matches", "9 league
   matches", "0 of 38 availability entries".
3. **The status.** Supported / Mixed / Not supported / Can't test yet.
4. **What the record shows.** Two to four numbers with the comparison that makes
   them meaningful.
5. **What better data would do.** The data class that would reduce uncertainty
   and what it would settle. Example: "A licensed event feed with set-piece
   goals and errors would separate coaching from personnel."
6. **What would change the view.** One line. The withdrawal condition.

A visible evidence table follows the claim. Method, definitions and long caveats
move to long-form.

## Claim register

### 1. The team now

- **Claim:** This is a rebuilt side with an unsettled shape, and the league
  record is mid-table.
- **Count:** 9 league matches; 3W 2D 4L, 11 points, 10 goals for and 10 against;
  44.1% shot share; 6 kick-off shapes in the covered fixtures.
- **Status:** Supported as description.
- **What the record shows:** the record and the shape churn; the last five are
  better than the season (8 points, 8-3, 56.6% shot share).
- **What better data would do:** an event feed would separate style from results;
  it would not change the record.
- **What would change the view:** a settled run of results and a stable shape.

### 2. The defence: three at the back and availability

- **Claim:** Three at the back is protecting a new defence at the cost of width.
- **Count:** 4 three-CB fixtures vs 9 two-CB; 2 shapes unknown. Wing-back starts
  2.0 vs 0.0; wide-forward starts 0.0 vs 1.33; 1.00 vs 1.89 points per game;
  1.25 vs 0.78 goals against per game.
- **Status:** **Mixed.** The selection cost is supported: the wide forwards do
  not start in the three-CB set. The performance effect is not established:
  four matches, non-random shape choice, different opponents and competitions.
- **What the record shows:** the counts above, with the match list.
- **What better data would do:** eight or more matches per shape, opponent
  strength, and event data for set plays and errors would separate shape from
  personnel and opponent.
- **What would change the view:** a run of three-CB games with the first-choice
  centre-backs available and goals conceded at or below the back four.

**Availability sub-claim:** the preferred centre-back pair has rarely been
available together.

- **Count:** Knoester 6 starts / 573 minutes, last 2026-10-17; Tobers last
  2025-09-27 and not in the 2026-27 squad; 0 known / 38 unknown availability
  entries; the most-used starting CB unit covers 54% of fixtures.
- **Status:** **Can't test yet.** The published record has no verified
  availability entry for either player. Absence is not injury.
- **What better data would do:** an official AFC team-news ledger would turn
  observed absence into a verified status and let the page compare goals
  conceded with and without the preferred pair.
- **What would change the view:** verified availability entries, or a run with
  both fit.

### 3. The attack

- **Claim:** The attack is keeping the team in games, but the balance is
  fragile; set plays and errors are part of the problem.
- **Count:** 10 goals for and 10 against in 9 league matches; 60% of goals from
  wide forwards and strikers; 44.1% shot share; last five 8-3, 8 points, 56.6%
  shot share; 6.4 corners against per match.
- **Status:** **Mixed.** The scoring output is supported. The set-play and error
  claims cannot be tested: the feed has corners and fouls, but no set-piece
  goals, error events or per-match penalties.
- **What the record shows:** goals, shot share and the last-five split.
- **What better data would do:** an event feed with set-piece goals, errors
  leading to shots/goals and penalties would test the claim directly instead of
  using corners as a proxy.
- **What would change the view:** event data, or a run of clean sheets and
  lower goals against.

### 4. The managers

- **Claim:** Thelin's side had a high ceiling and a low floor; Robinson has
  steadied it, but 18 league matches is not a verdict.
- **Count:** Thelin 58 league matches, 1.34 points per game; seven straight
  league wins, a 14-match winless run, and the 2024-25 Scottish Cup; Leven 9
  matches, 0.44; Robinson 18 matches, 1.22, in two nine-match spells of 3W 2D
  4L.
- **Status:** **Mixed.** The aggregate records are supported. "Steadying" and
  "lower variance" are readings, not established: 18 matches, two squads, and
  no pre-declared variance measure.
- **What the record shows:** the phase table and the run lengths, league only.
- **What better data would do:** a full season under Robinson, opponent strength
  and a pre-declared variance measure would test "steadier"; a sourced
  comparator is required before the word "record" is used.
- **What would change the view:** a full season, or a sustained points and
  goals-against trend.

### 5. The squad

- **Claim:** The squad was rebuilt, but this window was experienced, not a youth
  project; Morris was sold and not directly replaced.
- **Count:** 15 arrivals and 25 departures (8 permanent, 8 free, 9 loans out);
  median arrival age 26; U21 minutes 8%; 37 players used; four defensive
  arrivals; Morris to Luton on 2025-09-01, fee undisclosed, modelled range
  £0.6m–£1.7m.
- **Status:** **Mixed.** The turnover is supported. "Young" is not supported:
  the median age is 26 and U21 minutes are 8%. The goal-threat replacement
  effect cannot be tested with the current output data.
- **What the record shows:** the in/out split, age, U21 minutes and the Morris
  transfer row.
- **What better data would do:** disclosed fees, player output before and after
  the sale, and an event feed would test the replacement claim.
- **What would change the view:** a disclosed fee, a replacement's output, or a
  full season.

### 6. The chairman's record

- **Claim:** The public record is consistent with the chairman's trading-club
  argument, and the sporting cost is visible; it cannot prove the argument.
- **Count:** 7 completed seasons; finishes 3rd to 10th, average 6th; one major
  honour (2024-25 Scottish Cup); two European campaigns; nine people in charge
  including interims; the era arrival/departure counts, Miovski's disclosed
  £6.8m and the inferred net range are in the transfer register and the history
  payload.
- **Status:** **Supported as record; not supported as proof.** The record shows
  the pattern. It cannot show boardroom intent, wages, private valuations or
  that the model caused the results.
- **What the record shows:** the phase strip and the four anchors: 2024-25,
  2025-26, 2026-27 and the cup.
- **What better data would do:** audited accounts, disclosed fees and wages
  would test the financial side; they are not public.
- **What would change the view:** audited accounts, or a sustained league trend
  under a stable squad.

## Evidence and language rules

- **Counts, not scores.** No composite index, "depth score", "trust score",
  "gelling index" or provider rating used as a verdict.
- **One limitation per claim.** The sample count sits next to the claim. The
  provenance note sits in the method link, not in every sentence.
- **Plain words.** Centre-backs, full-backs and wing-backs, wide forwards,
  attacking and wide midfielders, goals conceded, points per game, starts,
  minutes. Expand every abbreviation on first use.
- **"Match ratings from our data supplier"**, not "provider rating", on first
  use. Say they are Premiership-only, weighted by minutes and not adjusted for
  position; do not compare across positions as a verdict.
- **"Our reading"**, not "the read"; **"what would change our mind"**, not
  "confidence rule"; **"not measured yet"**, not "unknown" in running prose
  (keep "unknown" in coverage tables).
- **No "not a verdict" badge.** Show the basis and the count instead.
- **No 80/20.** No editorial weights presented as a model.
- **No causal metaphor in a heading.** "Tax", "leaky boat", "bailing out" and
  "unsettled" are out of headings; use the measured cost or the count.

## Page versus long-form

**On the page:** the chairman's sourced frame; the owner's attributed view; the
six claims with count, status, evidence table and withdrawal condition; one
coverage block; links.

**Long-form supporting content:** role definitions; provider-rating method;
percentile and confidence definitions; full player and match tables; the
sensitivity checks; the xG, set-piece, error, pressing, possession and
mid-game-shape material; the notebook. These live on `/methodology/`,
`/metrics/` and a linked evidence appendix.

Contracted evidence stays visible. Moving method prose is allowed; deleting a
contracted table, column, confidence or unknown state is not.

## Contract and governance

- `/analysis/` is the canonical season-overview route; `/themes/` redirects. The case archive is not rendered there.
- The contract becomes property-based:
  - every published claim is visible with claim, count, status, evidence table,
    limitation and withdrawal condition;
  - at least one claim per domain, or an explicit "no current claim" state;
  - evidence columns are declared; a generic table is the fallback;
  - the chairman's frame and the owner's attribution are visible;
  - coverage and unknown states are visible;
  - method may be disclosed or linked.
- No fixed five ids, no fixed count, no 80/20, no per-id metric markers.
- Claim numbers get field-level registry entries with formula, denominator,
  rounding, basis, source, coverage, verification and audit. Object-level
  `provenance_only` entries are not enough for a claim number.
- The contract change and the renaming of any contracted theme require owner
  approval and a visible diff. This specification is that proposal.

## Data corrections before the rewrite

These must be fixed or explicitly scoped before the page is rebuilt:

1. The centre-back headline says the minutes are "thin behind it", but the CB
   group has five players with three or more starts; the thin group is FB/WB.
2. "Young minutes" is used next to 8% U21 minutes and a median arrival age of
   26. Say "high turnover", not "young squad", for 2026-27.
3. The CB evidence says "5 with 3+ starts" in one place and 4 in another.
4. The theme layer says 15 fixtures and 2 unknown shapes; the selection layer
   says 20 and 5. Reconcile the scope or label why they differ.
5. AM/WM reports 8 players but 7 player-match rows. Verify the count.
6. "Record win streak" needs a comparator: the covered league record contains
   an 8-match winning run in 2014-15 against Thelin's 7. The page uses "seven
   straight league wins" and does not use "record" unless a sourced comparator
   is approved.
7. "Not the weak spot" from a 0.05 rating gap is a null result from a small,
   non-position-adjusted sample. State what the supplier's ratings show, not
   what they prove.
8. The cover headline and the family-balance headline must agree with their own
   tables.

## What better data would change

The page should say, per claim, what would reduce uncertainty:

- **Official AFC team news and a populated availability ledger** for
  Tobers/Knoester and the rest of the squad.
- **A licensed event feed (Opta/StatsBomb-class)** for xG, set-piece goals,
  errors leading to shots/goals, penalties, pressures, progressive passes and
  mid-game shape.
- **Disclosed fees and audited accounts** for the trading model.
- **Opponent strength and a pre-declared variance measure** for the manager
  comparison.

Better data lowers measurement uncertainty. It does not prove the opinion, and
the page must not say it does.

## Out of scope for this change

- Buying or integrating an Opta/StatsBomb feed.
- Inventing a model, composite score or ranking.
- Causal claims about shape, sales, injuries, managers or the board.
- Full notebooks and the data-science blog.
- A verdict on individual players or managers.
- Removing contracted data to shorten the page.

## Open items for the owner

None for this build. The owner's thesis is the brief; the chairman frame is a
labelled summary from the public record. The six claims, status rule and
contract change are confirmed. A later claim change is an owner-approved spec
change.

## Definition of done

- The site owner's view is visible and attributed; the chairman's frame is sourced.
- Every claim has a count, a status, an evidence table, one limitation and a
  withdrawal condition.
- The data corrections above are fixed; no headline contradicts its table.
- Method and TBA data science are linked, not in the page prose.
- Contract, page, tests, metrics, audit and docs change together.
- The page reads as one case, not six cards.
