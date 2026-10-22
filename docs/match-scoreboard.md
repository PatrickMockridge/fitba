# Match scoreboard and team split

**Status:** normative for `/matches/<fixture_id>/`.
**Last reviewed:** 2026-10-22.
**Read with:** [fixtures.md](fixtures.md), [page-contracts.md](page-contracts.md),
[design.md](design.md), [identity.md](identity.md).

## Purpose and placement

Every played-fixture page opens with a scoreboard after the page header and
before "The read". The scoreboard is the first evidence block: the final score,
the goals and the red cards. It does not replace the header H1 or the full
timeline.

The final score is authoritative. The event feed provides the goal and card
detail. If the event feed does not reconcile with the final score, the
scoreboard says so and lists only recorded events.

## Data contract

The fixture payload carries a `scoreboard` block:

```text
home / away: side, team_id, team_name, is_aberdeen, goals[], red_cards[]
shootout: {home, away} | null
events_available: boolean
goals_complete: boolean
note: string
```

Each goal carries `minute`, `extra_minute`, `side`, `team_name`, `player_name`,
`assist_name`, `is_penalty`, `is_own_goal` and `score_after`.

Each red card carries `minute`, `extra_minute`, `side`, `team_name`,
`player_name`, `card_type` (`straight_red` or `second_yellow`) and the provider
`detail`.

Timeline rows add:

- `side` and `beneficiary_side`;
- `card_type`;
- `is_missed_penalty`.

Player-stat rows add `team_name` and `is_aberdeen`. A null team is rendered
"Team unknown", never as the opponent.

## Event semantics

### Goals

- A goal is attributed to the **benefiting side**. For an own goal,
  API-Football's event `team` is the beneficiary, not the scorer's team. Do not
  flip the side.
- The scorer is the provider player name. If it is missing, "Scorer unknown".
- The assist is the provider assist name. If it is missing, "Assist not
  recorded"; do not claim there was no assist.
- A penalty goal is marked `Penalty`. A missed penalty is not a goal.
- A goal at 45+2 is shown as `45+2'`.
- `score_after` is the running match score for regular and extra-time goals.

### Own goals

An own goal is listed under the team that benefited. The scorer may belong to
the other team; the badge and the scorer name make that clear. There is no
side-flip in the timeline, summary or scoreboard.

### Shootouts

Shootout kicks are not match goals. They are excluded from the goal lists and
from the running score. The shootout score comes from the fixture
`home_penalties`/`away_penalties` fields and is shown separately.

If the provider leaves a shootout event unflagged, it is reclassified only when
excluding the 120+ penalty candidates reconciles to the final score. A genuine
extra-time penalty at 120+ stays a match goal.

### Red cards

- `straight_red`: a red card that is not a second yellow.
- `second_yellow`: a second yellow leading to a red card.

Plain yellow cards remain in the full timeline but are not in the scoreboard.
Do not infer a second yellow from two separate yellow events; the provider
declaration is the source.

### Unknown and incomplete

- `events_available` is false when the fixture has no event feed. The scoreboard
  still shows the final score and says "Goal events unavailable".
- `goals_complete` is true only when every regular goal has a known side and the
  per-side goal counts equal the final score.
- If `goals_complete` is false, the page says the event feed is incomplete and
  lists only recorded goals.
- Never show a missing event as zero, and never invent a scorer or card.

## Layout and team identity

The scoreboard has two side panels, home left and away right, matching the H1,
stats, xG and lineups.

- **Aberdeen is always red**, wherever it sits: a club-red wash, a 3px club-red
  edge, and the literal word "Aberdeen".
- The **opponent is neutral**: surface and line tokens, with its name. Do not
  use a new opponent hue.
- A visible team key shows the red Aberdeen swatch, the neutral opponent swatch
  and the sentence "Aberdeen is red throughout; the opposition is neutral."
- Every table and panel keeps the team name. Colour is never the only cue.
- The same rule applies to match stats, fxG sides, the timeline, both lineups
  and player stats. They carry `data-team="aberdeen"` or `"opponent"` and
  `data-team-split="aberdeen-opponent"`.
- League, history and recruitment tables are out of scope; they keep their
  existing treatment.

## States

| State | Scoreboard behaviour |
|---|---|
| Complete event feed | Final score, goals, running score and red cards; note says the final score is authoritative. |
| 0–0 with events | "No goals"; red-card list if any. |
| No event feed | Final score plus "Goal events unavailable"; no invented events. |
| Partial feed | Final score plus recorded goals and an explicit incomplete note. |
| Shootout | Final score, shootout score separately, shootout kicks excluded from goals. |
| No red cards | "No red cards in the event feed." |
| Missing scorer/assist | "Scorer unknown" / "Assist not recorded". |
| Null player team | "Team unknown", not the opponent. |

## Accessibility

- The scoreboard has an accessible name including the fixture and score.
- Every team panel, table and badge has a visible text label.
- Table headers use `scope="col"` and tables carry captions.
- Red card type is text, not colour: "Straight red" and "Second yellow".
- Check contrast and layout at 390px and 1440px in Merkland, Red Matchday,
  Aurora and Floodlight.

## Contract markers

- `match.scoreboard` on the scoreboard root;
- `match.scoreboard.side` on both side panels;
- `match.team-key` on the team key;
- `data-team-split="aberdeen-opponent"` on the scoreboard, stats, fxG, timeline,
  lineups and player stats;
- `data-team="aberdeen"|"opponent"` on the Aberdeen/opposition side, column or
  row.

The dynamic fixture route is guarded by `scripts/check_fixture_pages.py`, not by
the literal-path surface manifest.

## Checks and tests

The fixture guard verifies:

- scoreboard sides, team ids and exactly one Aberdeen side;
- goal and red-card lists group under the right side and reconcile with the
  timeline;
- no shootout goal in the goal lists;
- red-card types are valid and second-yellow flags agree;
- `events_available=False` means empty lists;
- `goals_complete` means counts match the final score and the summary reconciles;
- shootout scores match the fixture penalty fields;
- running scores do not decrease and end at the final when complete;
- every built page has the scoreboard, team key, team split and both team
  markers.

Unit tests cover normal goals, assists, penalties, own goals, straight reds,
second yellows, plain yellows, missed penalties, shootouts, 0–0, no events,
partial feeds, aliases and null teams. The page checker is the end-to-end guard
over all played fixtures.

## Change control

Adding or removing a marker, changing the event semantics or changing the
pagination/order is a contract change. Update `docs/fixtures.md`,
`docs/page-contracts.md`, the fixture checker and its tests in the same change.
Any changed published event or score value is recorded in
`docs/metric-changes.md` with before/after examples and audit impact.
