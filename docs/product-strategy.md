# Product strategy: fitba

**Status:** canonical product document. Last reviewed 2026-10-21.

## In one sentence

fitba is the translation layer between the data that shapes Scottish football and
the people who watch it — the same evidence, in the same language, for the stand
and the analyst, with the context and uncertainty that hot takes leave out.

## The problem

Football has two audiences for analysis and they rarely meet:

- the **analysis tier**, which works in percentiles, xG, role-adjusted output,
  budgets, age curves and confidence intervals;
- the **spectator tier**, which watches results, form, individual mistakes and
  narrative, and is often offered either raw numbers without meaning or
  simplified content without evidence.

Attempts to bridge them are frequently one-dimensional: a single player rating, a
"data says" take, or a chart with no explanation. Fans are told they should
understand data, but the data is rarely translated into the decisions they
actually care about — who plays, who is signed, why a team is inconsistent, why a
good process can produce a bad run.

The result is predictable. Frustration gets aimed at individuals, confidence
swings with the last result, and the structural reasons for a club's behaviour
disappear from the conversation.

## Who fitba is for

- **Primary:** Aberdeen fans who want to understand the club's trading model,
  recruitment, inconsistency and the gap between performance and results.
- **Secondary:** Scottish football fans, students, journalists and analysts who
  want the same lens applied across the pyramid and to opponents.
- **Tertiary:** people working in clubs who want a public-facing explanation of
  the frameworks, not an internal tool.

The product is not a club mouthpiece. It is independent, non-commercial and
correctable.

## The promise: same evidence, not insider knowledge

We do not have Aberdeen's internal models, scouting reports, wage structure or
board discussions. The product must never imply otherwise.

What we can do is show the **publicly observable proxies** that a back room
works from — minutes, roles, output, style, squad age and value, budget bands,
contract and loan status — and explain the questions those proxies raise. Every
panel should make clear whether it is:

- **measured** from a licensed source;
- **inferred** from a model or a comparison;
- **curated** from public reporting; or
- **unknown**, in which case we say so.

The same framework is applied to Aberdeen, to opponents and to scouted players.
That is what makes the comparison fair, and what lets a fan see the game the way
the analysis tier sees it without being handed a conclusion.

## The Aberdeen context: a trading club

This section records the project owner's framing of Aberdeen's recent strategy.
It is context, not an audited financial or boardroom account.

Aberdeen have operated as a **trading club**: buy low, develop, sell high, and
reinvest in young players and the squad. The model has had commercial success,
grown the fanbase and delivered a Scottish Cup. It has also produced **volatile
league form** since Dave Cormack's chairmanship — the kind of volatility a
development-and-sale model tends to create.

The app should show both sides of that trade-off:

- **The logic:** buying undervalued talent, giving young players minutes,
  generating sell-on income, keeping the wage structure disciplined and
  reinvesting.
- **The costs:** squad turnover, reliance on young players, replacement risk,
  the gap between potential and current output, and the week-to-week variance
  that comes from a changing squad.
- **The tension:** a cup run and a strong balance sheet do not guarantee league
  consistency; a trading model deliberately accepts some sporting risk in
  exchange for commercial and developmental upside.

This is not a story about a villain or a single bad decision. It is a story about
a strategy with trade-offs, and the data should let a fan see those trade-offs
clearly.

## Principles

1. **Evidence before narrative, context before blame.**
   A striker's drought is shown alongside role, minutes, shot quality, team
   style and sample size — not as a single verdict.
2. **Progressive disclosure.**
   Every insight has a headline, a visual, a "what this means" line and a
   methodology drawer. Casual fans stop at the first; analysts go all the way
   down.
3. **Uncertainty is a feature.**
   Sample-size badges, coverage tiers, confidence intervals and "we don't know"
   states are visible. Precision is never faked.
4. **Show the trade-offs, not villains.**
   The trading model's benefits and costs are presented together.
5. **One framework, many clubs.**
   Aberdeen, opponents and scouted players are measured with the same
   position-aware, league-adjusted method.
6. **Independent and correctable.**
   Non-commercial, no betting advertising, a corrections route, and a clear
   separation between our analysis and the club's actual decisions.
7. **No licence landmines.**
   Public data comes from licensed feeds. Unlicensed event or tracking data stays
   local and unpublished.
8. **No dumbing down, no showing off.**
   Plain language is not the same as removing the evidence; technical depth is
   not the same as being useful.

## Two doors and a bridge

The site is organised around the question a fan actually arrives with:

- **Matchday** (`/matchday/`) — the next fixture, both predicted XIs, form and
  home/away splits, opponent style and relative strength, the likely approach
  and the keys to the match. Fixtures, results, tables, cup rounds and the
  cut-offs that decide Europe, the split and relegation are one click away.
- **Off the pitch** (`/recruitment/`) — confirmed transfers and loans, the
  scouting method and the rumour mill.
- **Squad** (`/squad/`) — the structural bridge: every current player and
  current loanee, with current-season output, loan tags and a profile page. The
  same player is the destination from matchday, transfers, rumours and news.
- **News & rumours** (`/news/`) — the editorial bridge: the club's own voice, the
  X timeline and the curated rumour register side by side.
- **The bigger picture** (`/themes/`) — the analytical bridge between the
  matchday lookahead, the squad, recruitment and the Cormack-era mission. It
  turns the recurring fan arguments into evidence: role-family balance, the
  wing-back trade-off, defensive cover, the attack-defence balance and the
  trading-club trade-off. Its squad-needs board on `/recruitment/` turns the
  themes into role profiles and market routes; it names no targets.

The rumour mill is a distinct product lane, not a feed of links:

- **curated and source-linked** — every row has a public source, a status and an
  editorial confidence;
- **separate from confirmed business** — a rumour becomes confirmed only when it
  is in the transfer register, and then it links to that row;
- **data-backed opinion** — opinion cards must cite rumour ids and a measured
  comparison, and are labelled as opinions;
- **a recruitment signal** — the active links produce an advisory profile of the
  position, age, league and value mix the club may be looking at, which can
  expand or challenge the scouting shortlist without overriding the fit ranking;
- **a fan-signal read** — sampled AFC Chat Rumour Mill first pages produce name
  mentions, cross-reference labels and rule-based sentiment, compared with press
  claims and the club's output.

Fan chatter is not published as rumour, and a mention is not a transfer link. The
forum is used as a reference signal only (`ai-train=no`), with no raw posts,
usernames or quotes in the public payload.

## What the first public version does

- Full competition pages: the four leagues, the League Cup group stage and
  knockout rounds, and the Scottish Cup's pure knockout rounds.
- An upcoming-matchday dashboard and a trading-club view: the next opponent,
  predicted XIs, form, style and strength; squad age/value, minutes by age,
  transfers, sell-on candidates, contract and loan status on the club pages.
- A scouting board using basic licensed stats: position-aware percentiles,
  minutes reliability, league-strength adjustment, style fit, budget bands and
  coverage labels.
- Opposition briefings using the same framework.
- Fan explainers and a methodology/sources layer that a casual fan can follow.
- The official AFC news feed, clearly separated from our analysis.

## Content pillars

1. **Matchday and competitions** — the next fixture, predicted XIs, form,
   opponent style and strength, keys to the match; tables, cup groups and
   rounds, fixtures and cut-offs.
2. **Aberdeen performance and style** — results vs performance, shot quality,
   build-up, pressing, set pieces, game states.
3. **The trading club** — squad age/value, minutes by age, inferred transfer
   balance, sell-on candidates, contract expiry, wage bands, the commercial
   logic and its costs.
4. **Recruitment and scouting** — role-aware percentiles, style fit, budget
   bands, coverage warnings, shortlists.
5. **Loans and the youth pathway** — lower-tier minutes, development, recall
   readiness.
6. **Opposition briefings** — style, budget and squad comparison.
7. **Fan explainers** — "what xG does and doesn't say", "why the table lies in
   October", "why a trading club is volatile", glossary and method.
8. **News and the bridge** — official AFC headlines and links, the embedded
   @aberdeenfc X timeline for high-frequency posts, and the curated rumour mill.
   X is embedded, not ingested or stored.
9. **The rumour mill** — sourced links with a status and confidence, data-backed
   opinion, an advisory recruitment profile and a rule-based read of fan
   sentiment. Separate from the confirmed register.
10. **The Cormack era** — a season-by-season historical record of managers,
    backroom and board changes, honours, transfers, style and selection, with a
    labelled assessment. See [history.md](history.md).
11. **The bigger picture** — medium and long-term themes that connect the
    matchday lookahead to squad structure, recruitment and the club's mission.
    Four current-season themes and one mission-context theme, with measured
    evidence and a labelled read. See [themes.md](themes.md).

## Editorial policy

- We are independent and non-commercial. No betting advertising, no paid club
  influence, no player abuse.
- We distinguish measured, inferred, curated and unknown. A modelled estimate is
  labelled as one.
- We do not claim to know the club's internal models or private conversations.
  We show the public proxies and the questions they raise.
- We publish corrections and keep a last-reviewed date on method pages.
- We do not use engagement as an excuse for certainty. A quieter, more accurate
  explanation is the product.

## What we will not build

- Player ratings presented as verdicts, or "data says sign him" certainty.
- Blame narratives that single out a player without role, sample and context.
- Raw scraped data in the public repo, unlicensed Opta/Sofascore feeds or
  betting odds.
- Invented wages, fees or internal valuations.
- A full graphical bracket or tracking visual before the licensed data and the
  audience justify it.

## How we measure success

- **Comprehension:** can a fan explain the main idea of a panel after reading it?
- **Breadth:** do casual fans and analysts both use the same pages, not two
  separate products?
- **Trust:** corrections are visible, sources are linked, uncertainty is
  respected.
- **Return:** readers come back for the next match, the next window, the next
  explainer.
- **Tone:** fewer individual-blame reactions and more questions about structure,
  budget and trade-offs in the places where the project is discussed.

Engagement alone is not a success metric. A product that makes fans more certain
and less accurate has failed.

## Open questions

- The public name and brand (currently "fitba").
- How much editorial voice to use alongside the data.
- How to present budget bands without implying a precision the public data does
  not have.
- Which enterprise event/tracking provider, if any, is worth approaching later.
