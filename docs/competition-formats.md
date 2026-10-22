# Competition formats

**Status:** reference. Last reviewed 2026-10-21. Licensed coverage key-tested
2026-10-21.

This document defines the formats the app models. Official sources are cited;
community sources are used only as cross-checks and are labelled.

## European competition check

Aberdeen’s UEFA entry is checked separately from the SPFL pyramid in
`reference/european_competitions.yaml`. When Aberdeen are not in Europe, the
competitions page says **Not applicable this season** rather than omitting the
section. When they qualify, set `in_europe: true` and add the competition,
stage, next fixture and UEFA source. This is a current-season check, not a
claim that Europe is permanently absent.

## League Cup (Premier Sports Cup) 2026/27

### The rule correction

The project brief originally described the **top six Premiership clubs** joining
the knockout stage. The official 2026/27 format does **not** use that rule. It
uses the **five European representatives**:

- Celtic and Heart of Midlothian (Champions League)
- Rangers (Europa League)
- Motherwell and Hibernian (Conference League)

Those five receive byes to the second round. Any page that still says the old top-six rule is stale; this is a correction.

### Structure

- **Group stage: 8 groups of 5 = 40 clubs.**
- Entrants: the 37 SPFL clubs not in Europe, plus three guests — Linlithgow Rose,
  Brora Rangers and Brechin City.
- **5 European representatives** receive byes to the second round.
- **8 group winners + 3 best runners-up** join the five byes in a **16-team
  second round**.
- The second round is seeded: the five European clubs plus the three group
  winners with the best records are seeded; the other five group winners and the
  three best runners-up are unseeded.

### Group points and table columns

- **3 points for a win.**
- **1 point for a draw**, then a penalty shoot-out; the shoot-out winner earns
  **1 bonus point**.
- Effective points: win = 3, shoot-out win = 2, shoot-out loss = 1.
- Group tables therefore use **W / PW / PL / L** columns, not a flat W/D/L.

### Group tie-breaks (official order)

1. Goal difference
2. Goals scored
3. Away goals scored
4. Matches won
5. Away matches won
6. Head-to-head record
7. Drawing of lots

### Knockout

- Single-leg throughout.
- Extra time and penalties if level after 90 minutes.
- Second round: 15/16 August 2026 (first tie 14 August).
- Quarter-finals: 12/13 September 2026 (first tie 11 September).
- Semi-finals: 31 October / 1 November 2026 at Hampden Park.
- Final: Sunday 13 December 2026 at Hampden Park.

### Current state (21 October 2026)

- Group stage complete.
- Second round and quarter-finals complete.
- Semi-finals:
  - **Rangers v Aberdeen — 31 October 2026, 17:30, Hampden Park**
  - **Heart of Midlothian v Hibernian — 1 November 2026, 15:00, Hampden Park**
- Final: 13 December 2026, participants TBC.

### Data availability and the standings gap

The licensed API-Football feed (key-tested 2026-10-21) supplies **all 80 group
matches and the knockout ties, including penalty scores**, but its League Cup
**standings response is empty**. The app therefore **computes the eight group
tables from the 80 group fixtures** using the points and tie-break rules above.
This is a deliberate, reproducible calculation, not a scraped table.

The feed does not expose the official draw letters. The app groups teams by the
group-fixture graph (each group is a five-team clique) and assigns A–H; the table
contents are group-correct. No scraping fallback.

Sources: [SPFL League Cup format](https://spfl.co.uk/league/league-cup/format),
[SPFL League Cup fixtures](https://spfl.co.uk/league/league-cup/fixtures),
[SPFL League Cup table](https://spfl.co.uk/league/league-cup/table),
[Wikipedia 2026–27 Scottish League Cup](https://en.wikipedia.org/wiki/2026%E2%80%9327_Scottish_League_Cup)
(cross-check only; not an official source).

## Scottish Cup (Scottish Gas Men's Scottish Cup) 2026/27

### Structure

- **137 clubs, 136 ties**, pure single-elimination knockout.
- Final at Hampden Park.
- **No replays** for drawn matches: 30 minutes of extra time, then penalty kicks.
- Only the **first preliminary round** has byes: 45 clubs, 5 ties, 35 byes to
  preliminary round two.

### Rounds and dates

| Round | Date | Clubs | Ties | Composition |
|---|---|---|---|---|
| Preliminary Round One | Sat 1 Aug 2026 | 45 | 5 (+35 byes) | 2 North/Midlands league winners, 1 SAFA amateur winner, 42 unlicensed member clubs |
| Preliminary Round Two | Sat 22 Aug 2026 | 40 | 20 | 5 PR1 winners + 35 byes |
| Preliminary Round Three | Sat 12 Sep 2026 | 20 | 10 | 20 PR2 winners |
| First Round | Sat 3 Oct 2026 | 60 | 30 | 10 PR3 winners + 18 Highland League + 16 Lowland East + 16 Lowland West |
| Second Round | Sat 24 Oct 2026 | 40 | 20 | 30 R1 winners + 10 League Two |
| Third Round | Sat 28 Nov 2026 | 40 | 20 | 20 R2 winners + 10 League One + 10 Championship |
| Fourth Round | Sat 16 Jan 2027 | 32 | 16 | 20 R3 winners + **12 Premiership** |
| Fifth Round | Sat 6 Feb 2027 | 16 | 8 | R4 winners |
| Quarter-finals | Sat 6 Mar 2027 | 8 | 4 | R5 winners |
| Semi-finals | Sat 17–18 Apr 2027 | 4 | 2 | QF winners |
| Final | Sat 22 May 2027 | 2 | 1 | SF winners |

### Aberdeen

Aberdeen enter in the **fourth round**, weekend of **16 January 2027**. There is
no Aberdeen tie to show before the draw. The app must say "awaiting draw", not
invent an opponent.

### Current state (21 October 2026)

- Preliminary rounds one to three and the first round are complete.
- The second round was drawn on 3 October 2026; all 20 ties are scheduled for the
  weekend of 24 October 2026 and have not yet been played.
- 72 clubs remain. No Premiership clubs are involved yet.

### Data availability

API-Football's Scottish Cup coverage is **partial**: the key-test returned **50
of 136 ties** — 30 First Round and 20 Second Round (the provider labels the
latter "Round of 128"; the app maps it by date). The three preliminary rounds and
the rounds after the Second Round are not provided. The page shows the rounds the
feed covers and labels every missing round as "not in licensed feed"; it does not
invent ties. If that gap is unacceptable, the fallback is Sportmonks Starter or
an enterprise provider. No scraping fallback.

Sources: [SFA format and rules](https://www.scottishfa.co.uk/en/scottish-cup/scottish-gas-mens-scottish-cup/format-rules),
[SFA 2026/27 format announcement](https://www.scottishfa.co.uk/en/news/scottish-gas-mens-scottish-cup-format-and-composition-finalised-ahead-of-2026-2027-season),
[SFA format and composition PDF](https://assets.ctfassets.net/qu0slcxvbwp6/1BfTz9IMRE7ckhocCF5TOj/6e33387a50a820f4f86c4c1eecb10659/2026-27_Scottish_Cup_Format___Composition.pdf),
[SFA rules PDF](https://assets.ctfassets.net/qu0slcxvbwp6/4TZlz8yWaTibtBRSUk8Ai0/48f87db2a4679b5ad04a0039fe8683a5/Men-s_Scottish_Cup_Rules_2026-27.pdf).

## How the app models a cup

- **Round order** is stored in config, not inferred from dates.
- **Group** is stored for League Cup fixtures; the group table is computed.
- **Penalty shoot-outs** are stored separately from the 90/120-minute score:
  `home_penalties`, `away_penalties`, `status` and `winner`.
- **Extra time** is a flag; the score remains the score after extra time.
- **Byes** are modelled as advancement events, not fake fixtures.
- **Awaiting draw** is a real state, not a placeholder tie.
