# Data analysis

**Status:** live. Last reviewed 2026-10-22.
**Route:** `/analysis/` (the old `/themes/` route redirects here). **Nav and H1:** Data analysis.
**Config:** `config/themes.yaml`, `config/xg.yaml`.
**Payloads:** `themes/aberdeen.json`, `xg/aberdeen.json`.
**Spec:** [case-spec.md](case-spec.md), [xg.md](xg.md).
**Guards:** `scripts/check_themes.py`, `scripts/check_xg.py`.

## What it is

Data analysis is the logical bridge between the team on the pitch, the squad built
off it, and the chairman's stated vision and record. It is not a dashboard, a
data-science appendix or a verdict machine.

The page opens with the chairman's frame, summarised from the public record,
then the owner's view, attributed as opinion. Six claims follow. Each claim
gives the count, the status, the evidence, what better data would settle and
what would change the view. Method and definitions live in long-form supporting
content, not before the argument.

## The claim unit

Every claim has the same six lines:

1. the claim, in football language;
2. the count, the sample and the period;
3. the status: **Supported**, **Mixed**, **Not supported** or **Can't test yet**;
4. two to four numbers with the comparison that makes them meaningful;
5. what better data would do, and what it would settle;
6. what would change the view.

A visible evidence table follows the claim. Method, definitions and long
caveats are linked from `/methodology/` and `/metrics/`, not repeated in the
page prose. Contracted evidence stays visible.

## The six claims

| Claim | Domain | What it tests |
|---|---|---|
| The team now | On the pitch | Rebuilt side, unsettled shape, mid-table record. |
| The defence | On the pitch | Three at the back, wide-role trade-off, Tobers/Knoester availability. |
| The attack | On the pitch | Goals, shot share, the set-play and error gap. |
| The managers | The chairman's record | Thelin's start and collapse, the cup, Leven, Robinson's first 18 matches. |
| The squad | Off the pitch | 2026-27 turnover, age, under-21 minutes, the Morris sale. |
| The chairman's record | The chairman's record | Seven seasons, league range, cup, Europe, sales, manager spells. |

The count is whatever `config/themes.yaml` lists. There is no fixed five-card
grid and no 80/20 weighting.

## fxG block

The page carries a compact fxG table and links to `/analysis/xg/`. fxG is
fitba's shot-on-target model, not provider xG. At the 2026-10-22 publish the
provider-xG gate fails, so fxG is descriptive only. The model card is in
[xg.md](xg.md).

## Benchmark

The chairman's record carries a "How the record compares" table. It compares
Aberdeen's league finishes, points range and current position with the other
SPFL clubs over the covered seasons, using the all-club league rows already in
the warehouse. Other clubs' transfer and wage models are not in the public
record held here, and the table says so. The benchmark is league performance
only; it is not a transfer-model comparison.

## What the page does not do

- It does not invent a model, composite score or ranking.
- It does not use a provider rating as a fitba rating or an individual verdict.
- It does not claim causation from four three-centre-back matches or 18
  Robinson matches.
- It does not infer injury, return dates or mid-game shape.
- It does not proxy set plays, errors, pressing or possession when the feed has
  no event data. Those claims say "not measured" and name the data that would
  settle them.
- It does not hide contracted tables, columns, confidence, coverage or unknown
  states to shorten the page.

## Data corrections

The current build fixes the contradictions found in the old themes page:

- the centre-back "thin behind it" headline now matches its table;
- "young minutes" is replaced by "high turnover" (median arrival age 26,
  under-21 minutes 8%);
- the centre-back 5-vs-4, fixture 15-vs-20, unknown-shape 2-vs-5 and AM/WM
  8-vs-7 counts are reconciled or labelled by scope;
- "seven straight league wins" replaces "record" unless a sourced comparator
  is approved;
- the 0.05 rating gap is described as what the supplier ratings show, not as
  proof that the centre-backs are not a weakness.

## Adding or retiring a claim

1. Add or remove the definition in `config/themes.yaml`: id, domain, order,
   title, claim, better data, change mind and links.
2. Add the evidence builder in `src/fitba/publish/case.py` if the claim needs a
   new calculation. Reuse the existing analytics in
   `src/fitba/analytics/themes.py`, `history.py`, `records.py`,
   `selection.py` and `recruitment.py`.
3. Add the metric family in `config/metrics.yaml`; every numeric evidence row
   needs a registered metric and a payload path.
4. Update the contract in `web/contracts/surfaces.json` and
   `docs/page-contracts.md` only if the page structure changes. The claim count
   is not contracted.
5. Run `make check`, `make check-all`, both web builds and
   `scripts/check_themes.py`.

A semantic claim change is an owner-approved change with a registry version
bump and an entry in [metric-changes.md](metric-changes.md).

## Commands

```bash
uv run fitba publish --season current --profile public --require-validation
uv run python scripts/check_themes.py
uv run python scripts/check_xg.py
uv run python scripts/check_metrics.py --strict
make themes-check
make xg-check
```
