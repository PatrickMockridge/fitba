# Semantic layer

**Status:** canonical note on reader-facing identity, page metadata, definitions
and the public change log. Last reviewed 2026-10-26.

The semantic layer sits between the published facts and the pages that serve
them. It owns **identity** (which entity a page is about and where its one
canonical page lives), **page metadata** (which provenance layers and metrics
belong to a surface), **definitions** (what a term or registered metric means)
and the **public change log**. It does not own a value. Every number it shows is
read from the registry or an existing published payload.

## Path from source to reader

| Stage | Owner | Output |
|---|---|---|
| Source | the ingest adapters and TTLs in `docs/update.md` | caches under `.cache/`, normalized frames |
| Normalize | `normalize/results.py`, `analytics/*`, `normalize/entities.py` | one canonical fact and one canonical entity id |
| Publish | `publish/semantic.py` | `entities/index.json`, `entities/scouted.json`, `page-meta.json`, `definitions.json`, `changelog.json` |
| Serve | `web/lib/data.ts` and the page components | `/search/`, `/claims/`, `/corrections/`, page provenance and citations |

The semantic bundle is built after `seasons.json` and before the result audit in
`publish/publish.py`. It reads the squad, former-player, scouting, fixture,
history, case and table payloads; it does not recompute a metric.

## Entity identity

`normalize/entities.py` is the only place that builds a reader-facing entity
href. A page component must not assemble a player, club, fixture or claim link
by hand.

| Type | Namespace | Canonical destination |
|---|---|---|
| Page | `page:` | the route, preserving any fragment |
| Club | `club:` | `/scotland/<tier>/#club-<team>` for a current table row |
| Player | `player:` | see the one-profile rule below |
| Fixture | `fixture:` | `/matches/<fixture_id>/` |
| Season | `season:` | `/history/<season>/` |
| Staff | `staff:` | `/history/#staff-<person>` |
| Claim | `claim:` | `/claims/#claim-<claim>` |

An entity carries `entity_id`, `type`, `name`, `aliases`, `external_ids`,
`href`, `href_kind`, `routes`, `indexable`, `no_href_reason`, `search_group`,
`sitemap`, `source_layers`, and, for scouted players, `league` and
`role_family`. `external_ids` values are strings. An entity with no public
destination is published with `indexable: false` and a `no_href_reason`; it is
never silently dropped.

### One-profile rule

There is one player profile shape, and one canonical route for each player
state:

- a current squad member uses `/players/<id>/`;
- every other player, including a former Aberdeen player and a scouted player,
  uses `/scouting/player/<id>/`;
- a former player without an API id uses the former-player register anchor
  `/former-players/#former-<key>` until a reviewed crosswalk supplies a
  profile id.

A former player's scouting profile carries the shared statistical profile plus
an additive Former Aberdeen section. There is no third player route, dialog,
drawer or card.

### Core and scouted groups

`entities/index.json` is the core index: pages, clubs, current and former
players, fixtures, seasons, staff and claims. `entities/scouted.json` is a
compact projection of scouted-only players (`i`, `n`, `a`, `h`, `l`, `rf`). The
two groups are disjoint by `entity_id`; a scouted row that duplicates a core
player is removed from the scouted group, not merged into the core index.

`/search/` ships the core index and lazy-loads the scouted group only when the
reader asks for it. `/scouting/search/` paints metadata and the first 100 rows,
then loads the four shards on interaction.

## Page metadata

`config/pages.yaml` is the editorial page registry. One entry per surface id
used by `ContractPage` or the non-contracted data pages, with route patterns,
provenance layer ids and a `no_layers_reason` for editorial or descriptive
surfaces. `publish/semantic.py` inverts that with the metric registry into
`page-meta.json`, keyed by surface id. Each surface records its route patterns,
layers, metric ids, the dataset epoch, the registry version and checksum and the
canonical base URL. It stores references only; it never copies a value.

The serving layer resolves a citation at render from page metadata, the
provenance payload, the manifest and the manifest freshness fields. A citation
names the page, canonical URL, dataset id, basis, source list and metric links.
A bare number without that context is not a citation.

## Definitions

`definitions.json` has two provenance values:

- `registry`: generated from every active entry in `config/metrics.yaml`. The
  formula, unit, basis, coverage tier and source layer are copied from the
  registry at publish time.
- `curated_overlay`: concept terms from `reference/definitions.yaml` for ideas
  the registry does not own, such as basis, coverage tier, unknown, role family
  or the value index. A curated term may name metric ids but may not override a
  formula, unit, basis, coverage tier or source layer.

`check_semantic.py` fails an unknown metric id, a duplicate id or alias, an
unknown related id, a self-reference, and a curated entry that sets a formula.
`/glossary/` renders every entry at a stable `#def-<id>` anchor and lists its
related concepts. Page provenance, the metric registry and the first-use
`DefinitionTerm` links resolve to the same anchors; a missing term renders plain
text, never a dead link.

## Public change log

`reference/changelog.yaml` is the append-only public log. It records factual
corrections (a value or label changed against a public source) and structured
metric or payload changes. A disagreement with fitba's reading is not a
correction.

Each entry carries id, date, kind (`correction`, `metric`, `source`, `page`,
`data`), status (`fixed`, `reviewing`, `withdrawn`, `published`), title, summary,
affected pages and entities, metric ids, evidence and `fixed_in_dataset`. A
metric entry also names the registry version and the heading in
`docs/metric-changes.md`; that narrative remains the normative change-control
record. `changelog.json` is a sorted projection of the YAML and is never
hand-edited. `/corrections/` renders it.

## Performance budgets

`config/web-budgets.yaml` sets browser payload budgets, not a content cap:

- `/search/` under 400 KB of initial HTML;
- `/scouting/search/` under 350 KB of initial HTML;
- `/claims/` under 450 KB;
- `/glossary/` under 500 KB;
- `/unknowns/` under 300 KB;
- the scouted entity payload under 800 KB (it is fetched only on an explicit
  reader action) and every scouting shard under 700 KB.

A breach is fixed by sharding or lazy loading. Deleting evidence to fit a
budget is forbidden. `scripts/check_page_budget.py` measures the generated
payloads and, after a build, the HTML and JSON the browser actually fetches.

## Guards

`fitba update` runs `guard.semantic` before `guard.metrics`. It runs
`check_semantic.py` in data mode and `check_page_budget.py` in data mode, and a
failure blocks the publish. A built site additionally runs:

```bash
uv run python scripts/check_semantic.py --pages --out web/out
uv run python scripts/check_page_budget.py --out web/out
```

The semantic checks are also part of the consistency audit as
`semantic.entities`, `semantic.pages`, `semantic.claims` and
`semantic.definitions`, so a disagreement is named in `audit/consistency.json`.

## Verification

```bash
uv run python scripts/check_semantic.py
uv run python scripts/check_page_budget.py
uv run python scripts/check_consistency.py
uv run python scripts/check_metrics.py --strict
make semantic-check
make page-budget-check
```

## Non-negotiables

- No duplicate entity id, alias or external id; core and scouted are disjoint.
- No hand-built entity link; use `normalize/entities.py`.
- No second player-profile route.
- No number in the semantic layer; definitions reference the registry.
- No hand-edited generated JSON; regenerate through `fitba publish`.
- No content cap; a payload breach is sharded or lazy-loaded.
- No deletion of a claim, correction or source to shorten a page.
