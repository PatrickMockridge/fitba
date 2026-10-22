# Squad needs

**Status:** live. Last reviewed 2026-10-22.

The needs model is the bridge from the themes layer to recruitment. It answers
a narrower question than “who should Aberdeen sign?”:

> Which role families are short of ready, available depth, and is the
> proportionate response short-term cover, a replacement scenario, or a
> structural strengthening need?

It publishes **role profiles and market routes**, not targets, fees or wages.

## Families

| Family | Themes families | Scouting groups |
|---|---|---|
| GK | goalkeeper | GK |
| CB | centre_back | CB |
| FB/WB | full_back, wing_back | FB |
| MID | defensive_midfield, central_midfield | DM, CM |
| AM/WM | attacking_midfield, wide_midfield | AM |
| W | wide_forward | W |
| ST | centre_forward | ST |

## Expected slots

The model uses the observed kick-off formations, weighted by formation share:

```text
slots[family] = sum(formation_share * count_family_slots(formation, family))
```

If no observed formation exists, the family is `unavailable`; no shape is
assumed.

## Measured depth

For each family:

- `available_players`: squad players not loaned out and not `out`/`suspended`.
- `ready_count`: available players with ≥2 starts or ≥180 minutes.
- `starter_count`: available players with ≥5 starts or ≥450 minutes.
- `trusted_count`: available players with ≥3 starts.
- `projected`: the top `ceil(slots)` available players by minutes.
- `depth_gap = clamp((max(ceil(slots), min_available) + cover_buffer -
  available_count) / max(ceil(slots), min_available))`.
- `quality_gap = clamp(1 - mean(projected minutes) / 900)`.
- `top_share = top player minutes / family minutes`.
- `availability_risk = (out/suspended in projected + 0.5 × doubtful) /
  known projected players`; it is null when no projected player has a known
  availability status. Unknown is not zero.
- `age_risk = share of projected players aged 30+`.

The measured score is a transparent weighted mean of the available components
for ordering only: depth 30%, quality 20%, concentration 10%, availability 25%,
age 15%. If availability is unknown, its weight is removed and the score is
labelled partial; it is not silently treated as zero. It is not a verdict.

The curated `squad_needs` prior from `config/clubs/aberdeen.yaml` is shown
separately as **Analyst intent (curated)**. It is not blended into the measured
score.

## Categories

Precedence:

1. **replace** — only with an active public outgoing rumour for a current
   starter. Age/value alone produces `watch`, never `replace`. No contract,
   bid, wage or release-clause claim.
2. **unknown** — measured depth unavailable and no replace evidence.
3. **cover** — availability risk above zero and either a projected shortfall
   or a large depth gap. Market route: loan, then free agent; horizon now.
4. **strengthen** — weak family rating, high concentration, thin rotation,
   quality gap or age risk. Market route: permanent, then free; long term.
5. **monitor / none** — residual states.

Urgency is critical for a two-body shortfall or two projected starters out;
high for one; medium for a cover/strengthen need; low for monitor.

## Roster space

- `max_squad` is a policy configuration, not a public registration rule.
- If a family is at or above `max_squad`, the card says a signing requires an
  outgoing first.
- `outgoing_first_families: [CB]` is analyst policy, not a measured fact.
- `senior_squad_limit` stays null unless a public source exists.

## Market route

`market_route.primary` is `loan`, `permanent` or `none`; alternatives are
free agents where appropriate. `fee_expectation` is always `unknown` while the
club budget has no public ceiling. Wages are not public.

## Surfaces

- `/recruitment/#squad-needs` — the full board, with every family, evidence,
  availability and roster caveat.
- `/analysis/` — the evidence behind the team and squad claims.
- `/scouting/#priority-profiles` — role profiles only. The shortlist engine is
  not live; no candidates are ranked or named.

## Guardrails

- No named targets, incoming player URLs, fees or wages.
- No “must sign”, “should sign” or “data says sign” language.
- Current-squad players may appear only as depth evidence; outgoing names may
  appear only with an active public rumour.
- Unknown availability stays unknown; it is not assumed fit.
- The model can say “strengthen”; it cannot decide the club's risk appetite.
