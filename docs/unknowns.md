# Unknowns register

**Status:** canonical note on the public unknowns register. Last reviewed
2026-10-26.

`/unknowns/` records what the public record does not know, why, and what would
resolve it. It is a register of **classes**, not a list of missing rows and not a
request to the club. Unknown is a published state; it is never zero and never an
estimate.

## Source and shape

`reference/unknowns.yaml` is the editorial source. Each class has:

- `id`, `domain`, `label`, `description` and `reason`;
- `affected_surfaces`, using page ids from `config/pages.yaml`;
- exactly one of `resolving_source {label, url, note}` or
  `no_public_source: true`;
- an optional `count {payload, pointer, metric_id}`.

`src/fitba/publish/unknowns.py` builds `unknowns.json` at publish time. A count
is a JSON pointer into an existing published payload and must cite the registered
metric that owns that payload. The builder never computes a new aggregate: if a
class has no published, registered count, it has no count.

The eight no-public-source classes are:

1. contract length, wages, release clauses and agent fees;
2. instalments, add-ons, agent and solidarity terms;
3. advanced event data (progressive passes, carries, pressures, aerial wins,
   crosses, xG/xA, coordinates);
4. possession;
5. boardroom intent and internal valuations;
6. needs fees, wages and targets;
7. rumour identity outside the gazetteer;
8. provider injury data (only official AFC team news resolves availability).

A class with a possible future public source — an undisclosed fee, loan terms, a
missing player statistic, a sell-on receipt — names that source and still
publishes unknown until it appears.

## Page and checks

`/unknowns/` groups the classes by domain and shows the reason, the affected
surfaces, the resolver or the no-source state, and any published count with its
metric and glossary link. It introduces no number of its own.

`scripts/check_unknowns.py` enforces:

- unique class ids and a non-empty reason, description and label;
- exactly one source mode;
- valid affected page ids and internal paths;
- every count's payload is registered to the cited metric, the pointer resolves,
  and the published value matches;
- no numeric leaf originates in the register outside a published count;
- the published class order matches `reference/unknowns.yaml`.

`guard.semantic` runs the check before the metrics guard.

## Policy

- Do not invent a resolver or a URL for a gap.
- Do not add a count that is not already registered and published.
- Do not frame a gap as a club request, a target list or a recommendation.
- Do not turn an unknown into zero, a range or a guess.
