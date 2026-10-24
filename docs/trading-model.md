# Aberdeen as a trading club

**Status:** product context. Last reviewed 2026-10-21.

This document records the project owner's framing of Aberdeen's strategy and
explains how fitba will represent it. It is **context, not an audited financial
account**. We do not have the club's internal valuations, wage structure,
sell-on clauses or board papers.

## The context

Aberdeen have operated as a **trading club**: buy low, develop, sell high, and
reinvest in young players and the squad. The model has been commercially
successful, grown the fanbase and delivered a Scottish Cup. It has also produced
**volatile league form** since Dave Cormack's chairmanship. That is not an
accident unique to Aberdeen; it is the kind of trade-off a
development-and-sale model tends to create.

The point of this page is not to defend or attack the model. It is to make its
logic and its costs visible enough for a fan to reason about them.

## What the model optimises for

- **Buying undervalued talent** — players whose current output or potential is
  priced below their likely future value.
- **Developing and giving minutes** — young players need match minutes to
  improve and to become sellable assets.
- **Selling at the right point** — balancing the sporting cost of losing a key
  player against the commercial value of the sale and the reinvestment it funds.
- **Wage discipline** — keeping the wage structure sustainable so transfer
  income is not absorbed by recurring costs.
- **Reinvestment** — replacing sold assets, ideally with a pipeline rather than a
  single signing.

## What it costs

- **Squad turnover** — replacing a sold player is not instant; the replacement
  may be younger, less proven or a different profile.
- **Youth variance** — young players produce inconsistent output; that is part of
  the development process, not a character flaw.
- **Replacement risk** — a sale that looks good commercially can leave a
  sporting hole for a season.
- **League volatility** — cup runs, European qualification and a changing squad
  can produce a season that looks inconsistent in the table even when the
  underlying process is coherent.
- **Fan expectation** — a Scottish Cup and commercial growth raise expectations;
  a trading model does not promise linear league progress.

## The confirmed-business register

The first implemented trading-club layer is the transfer/loan register across
2019/20–2026/27. The live row, confirmation and fee-anchor counts are in
`/transfers/` and `/metrics/`. The most recent audited windows have been
reviewed against the seniority rules; earlier windows are curated partial. It is
built from the licensed API-Football candidate feed and curated against official
AFC announcements and the Wikipedia season tables.

Only completed business is published. `feed_only`, `reported` and `rejected` rows
never reach the public payload. Fees are absent from the feed; disclosed and
reported fees are anchors with a public source, while undisclosed permanent
moves get an **inferred range** from age, position, market and those anchors.
The page does not call this an audited net spend. Free transfers count as zero
fee; loan fees are excluded. Sell-on clauses are tracked separately and labelled
confirmed or reported. Loan terms (end date, recall, obligation/option) are
unknown unless confirmed. See [transfers.md](transfers.md) and `/transfers/`.

## The current bridge

[Season overview](analysis.md) sets the chairman's approach against the current squad: the
role-family balance, the three-at-the-back record, the defensive depth and availability and
the attack-defence balance, with a separate Cormack-era analysis. It is the
short-horizon companion to the era record below.

## The era record

[The Cormack-era historical record](history.md) is the long-run version of this
page. It puts the league record, manager and staff changes, honours, transfer
windows, style proxies, selection and a labelled assessment side by side from
2019-20. It is deliberately not a verdict: the record shows the trade-off, and
the reading is labelled separately.

## How fitba represents it

The app will show public-data proxies, not the club's internal models:

| Panel | What it shows | What it is |
|---|---|---|
| Squad age/value curve | Age distribution and curated market-value bands | Public/curated proxy |
| Minutes by age | Who is actually playing, and how much | Measured |
| Transfer balance | Disclosed/reported fee anchors plus a modelled range for undisclosed moves | Curated/measured/inferred, with unknown flags |
| Former players | Departure, Aberdeen record, post-Aberdeen league seasons, rival spells | Measured/curated; gaps labelled |
| Sell-on watch | Clause, subsequent move, evidenced receipt or missing inputs | Curated/measured; never inferred |
| Contract expiry | Public contract end dates where known | Curated |
| Wage-band discipline | Club-level envelope, not individual wages | Modelled/unknown |
| Loan pathway | Minutes and output of Aberdeen loanees | Measured/curated by tier |

### The "explosion" diagrams

The breakdown visuals are layered, not a single score:

1. **Headline** — the player or squad fact in one line.
2. **Breakdown** — percentile bars, age/value curve, minutes cascade, fee/wage
   bands or transfer timeline.
3. **Context** — role, league strength, sample size and comparison with the
   squad.
4. **Method** — what is measured, what is inferred and what is missing.

This is the disclosure pattern used across the site: the headline and the
evidence are visible, and the method note can be opened. The reader can take the
headline and the visual, then open the method if they want it.

## What we cannot know

- Individual wages and bonus structures.
- Sell-on percentages and instalment terms.
- The club's internal player valuations and ranking.
- Boardroom intent, budget approvals and private negotiations.
- Medical, availability and disciplinary information that is not public.

We do not invent these. A budget-fit score is an estimate with a confidence band
and an "unknown" state, not a claim about what Aberdeen will pay.

## How to read the trading-club page

- A high squad value is not the same as a high league position; the model is
  deliberately realising value, not hoarding it.
- A young squad with volatile results may be executing the strategy, not failing
  it — but that does not make every result acceptable or every decision good.
- A sale can be commercially right and sportingly painful at the same time. The
  page should show both.
- A cup run is a real achievement and a source of variance; it is not proof that
  the league model is working.
- The data can show the trade-off. It cannot decide the club's risk appetite.

## Editorial guardrail

No blame narratives. No "data says sell him". No pretending that a public proxy
is the club's internal view. The aim is to let fans see the same trade-offs the
back room has to manage, and to argue about them with evidence rather than
certainty.
