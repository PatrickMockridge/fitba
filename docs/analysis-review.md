# /analysis/ review and decision record

**Status:** decision record. Last reviewed 2026-10-23.

Six read-only reviews (match-going fan, manager/coach, CEO/recruitment,
Scottish football media, site editor/IA, data/QA) were run against the existing
`/analysis/` page and the proposed season-overview replacement. The panel
agreed on the clean-slate direction and rejected the first draft's availability,
suspension, market and fixture assumptions.

## Purpose

`/analysis/` is the one-scan season briefing: what Aberdeen play next, who is
genuinely available, what the season is for, and where the evidence lives. It is
a bridge to matchday, squad and scouting, not a claim register or a second
dashboard.

## What the panel changed

- **31 October double-booking.** The season schedule contains Rangers v
  Aberdeen in the Premiership at 15:00 and the League Cup semi at 17:30 at
  Hampden, both on 2026-10-31. The SPFL club feed has only the semi. The
  implementation must keep both rows, mark the league row `conflict_review`,
  prefer the SPFL cup row, exclude the conflict from all lookaheads and publish
  the conflict count. No silent dedupe.
- **Availability universe.** The ledger has 39 entries but the active squad
  universe is 29 current squad players plus ledger-only Tobers = 30; nine
  loan-outs are separate. Counts must sum to 30: one out (Tobers), one reported
  available (Knoester, not a medical clearance), 28 no verified entry. Never
  render a 37-name “available” roster; “available” means a ledger entry, not fit.
- **Suspensions.** Every state is competition- and fixture-scoped. Publish
  watch/review-required states until the current SFA rule version and effective
  date are sourced; do not publish a player-level cup ban or overlay an
  unverified projection into the predicted XI. The feed mislabels the Happe
  second yellow (fixture 1629022); derive second yellows from same-match
  yellow+red rows and test it.
- **Bench data.** Normalized appearances contain only starters and used subs.
  Build `player_squads.parquet` from the raw cached lineup responses, including
  named unused substitutes, and gate omission inference on complete bench
  coverage (at least seven named subs).
- **Inferred absence.** Never call it injury. The published state is “not in
  the last two matchday squads — reason not published”, confidence capped at
  medium, with the two fixture dates and coverage. AFC team news remains the
  only injury source.
- **Squad decisions.** The first draft's value-index “sell-high” market block is
  not supportable and is outside the brief. Replace it with factual, measured
  lenses (peak-age minutes, low minutes share, loan-outs, role depth and needs).
  No value index, valuation, fee, wage, contract expiry or “will leave” copy.
- **Season aims.** Do not conflate the split with Europe. Show the measured gap
  to the split cutoff, the League Cup semi, and the European route separately;
  label targets “Analyst-set baseline, not a published club target”.
- **Contract scope.** The old case payload and `matchday.themes` strip remain
  contracted and are not removed in this pass. `/analysis/` stops rendering the
  case content; the retired case payload/code waits for a separate owner
  decision.
- **Hero and bridges.** The hero is a measured status line, not a new thesis.
  The next fixture is owned by Next up. The primary bridges are Matchday, Squad
  and Scouting; Matches and fxG are secondary links.

## Final page order and limits

1. **Hero** — H1 “Season overview”, position/points/last-five, one freshness
   badge. No fixture row, no opinion lede.
2. **Next up** — next three competitive, non-conflict fixtures; date/kickoff,
   competition, opponent, venue (H/A/Neutral), kickoff status. Link to the
   six-game matchday lookahead and full schedule.
3. **Availability and selection** — counts first; official team news; derived
   selection signals; selection watch (max three). Official out/suspended rows
   are never truncated; inferred/selection rows have a named overflow count.
4. **Season aims** — at most three measurable aims with target/current/status.
5. **Squad decisions** — at most three factual lenses, one row per player,
   sample and coverage visible.
6. **Matchday, squad and scouting** — three primary bridge cards; secondary
   Matches/fxG links.
7. **Coverage** — one compact known/unknown table plus links to metrics/sources.

## States

- Availability: `available`, `doubtful`, `out_official`, `suspended_official`,
  `suspended_projected`, `absence_inferred`, `unknown`.
- Basis: `measured`, `inferred`, `curated`, `mixed`, `unknown`.
- Confidence: `high`, `medium`, `low`, `unknown`.
- Selection: `predicted_xi`, `contender`, `available_not_selected`,
  `out_of_squad`, `not_evaluated`.
- Last squad: `starter`, `sub_used`, `sub_unused`, `not_in_squad`, `unknown`.

## Residual questions

- The exact current SFA cup accumulation/reset rule and red-card category
  lengths still need a sourced, versioned rule before any cup ban is published.
- The 31 October league row is treated as a conflict until the SPFL resolves
  whether it is postponed or rearranged.
- Contract expiry, free agents, wages and fees remain unavailable; no player
  expiry is inferred.
