# Preferred foot: source strategy and provenance

**Status:** live for preferred foot. Last reviewed 2026-10-21.

This document defines how the project resolves the one profile attribute the
licensed team sheet does not contain: preferred foot. Side is not resolved here.
It is derived from the starting-XI role; see [roles.md](roles.md).

The rule is simple: one Python resolver, one source per value, one provenance
record, and an explicit unknown state. The front end only presents the published
payload.

## Why this layer exists

API-Football provides identity, squad membership, roles and statistics, but not
preferred foot. The AFC official pages state a generic position, not a foot. The
team sheet cannot answer the question. Wikipedia carries a foot statement for
only a small minority of players. The field therefore needs a narrow,
auditable source policy rather than inference from role, side, name or shirt
number.

## Source hierarchy

| Tier | Source | Preferred foot | Current status |
|---|---|---|---|
| 0 | Verified manual override | Correction only | Empty until a correction is needed |
| 2 | **Sportmonks** | `metadata` include | Licensed source; adapter gated off until key, plan, terms and crosswalk are confirmed |
| 3 | Official club/federation | Only explicit statement | AFC pages state no foot, so no values today |
| 4 | **Wikipedia** | Only explicit left/right/both statement | Last-resort fallback, active |
| 5 | Unknown | `null` | A valid published state |

No source is allowed to infer a foot from a role, a side, a name, a shirt
number or a generic position.

## Accepted statements

Only an explicit statement is accepted: “left-footed”, “right-footed”, “left
foot”, “right foot”, “both feet”, “either foot”, “prefers his/her left or right
foot”. A phrase in a negative or irrelevant context (“not left-footed”,
“left-footed shot”, “right knee injury”) is rejected.

## Conflict and unknown policy

- A higher tier wins when sources disagree; the row records
  `conflict_state: resolved_by_precedence`.
- Two sources at the same tier that disagree produce a **conflict**:
  `value: null`, `status: conflict`, `conflict_state: unresolved`, and both
  source ids/URLs are listed. No value is published.
- A source that contains two different explicit values is also a conflict; the
  resolver does not pick the more convenient one.
- No allowed source, or only a generic position → `unknown` with a reason.
- Unknown is never filled with a zero, a guess or a front-end default.

## Provenance contract

The normalized table is
`data/normalized/squad/aberdeen_attributes.parquet`, one row per player. It
carries:

`player_id, player_key, attribute, value, source_id, source_tier, source_url,
source_revision, source_text, derivation, confidence, verified_at, status,
unknown_reason, conflict_state, conflict, conflict_sources, notes, ingested_at`.

`source_text` and `conflict_sources` are internal audit fields. The published
payload contains only the value, status, source id/tier, URL, revision,
verification date, confidence, derivation and conflict state. No article text,
wikitext or HTML is published.

The squad payload shape is:

```json
"attributes": {
  "preferred_foot": {
    "value": "left", "status": "known", "unknown_reason": null,
    "source": {
      "id": "wikipedia", "tier": 4,
      "url": "https://en.wikipedia.org/w/index.php?title=...&oldid=...",
      "revision": "123456", "verified_at": "2026-10-21",
      "confidence": "reference", "derivation": "explicit_foot_phrase"
    },
    "conflict_state": "none", "conflict_sources": []
  },
  "coverage": "known"
}
```

## Wikipedia as last resort

The Wikipedia adapter is deliberately narrow:

- one page per player per run, current squad and loanees only;
- a descriptive User-Agent; Wikimedia's generic API path returned 403, while
  the REST/raw path returned 200 with the project UA;
- a page metadata call first, then the raw wikitext fetched at that exact
  revision; the published source URL is a permalink with `oldid`;
- identity guard: the page title must match the player surname, the page must
  mention Aberdeen, and the birth date must match when the player profile has
  one; otherwise the page is rejected;
- only explicit foot phrases are parsed; positions are not read;
- a per-run page budget (default 200) and a one-request-per-second delay;
- a 403 stops the fallback for the run rather than rotating identities;
- no category or link traversal, no bulk crawl.

At the last check the adapter resolved **1 preferred foot** out of 38 players.
Only 2 of 89 cached Wikipedia player pages contain any foot phrase. This is a
source limitation, not a parsing choice: foot coverage cannot be fixed from the
free team sheet or from Wikipedia. It needs the licensed Sportmonks feed or an
explicit statement per player.

## Sportmonks: the preferred licensed source

Sportmonks API v3 exposes preferred foot through the `metadata` include. The
adapter is implemented behind a gate and makes **no HTTP request** until all of
the following are true:

- `SPORTMONKS_API_KEY` is set;
- `config/sources.yaml` has `sportmonks.adapter_ready: true`;
- `config/player_attributes.yaml` has `sportmonks.enabled`, `plan_confirmed`,
  `public_display_terms_confirmed` and `crosswalk_confirmed` set to true;
- `reference/player_crosswalk.yaml` has a reviewed exact-match row for the
  player.

`scripts/probe_sportmonks_attributes.py` prints the gate and makes no request
while it is blocked. When the gate opens, the probe fetches one crosswalked
player and reports the metadata types without printing the token or a raw
payload.

The crosswalk is strict: normalized full name, date of birth, nationality and
current club must all match exactly and uniquely. No fuzzy match is promoted at
ingest time. Unresolved players fall through to the lower tiers; they never
borrow another player's row.

## Manual overrides

`reference/player_attributes_overrides.yaml` is a correction layer, not a source.
Each row needs `player_key`, `attribute` (`preferred_foot` only), `value`,
`source_id`, `source_url`, `reason` and `verified_at`. Overrides are tier 0 and
win over resolver values, but they are reported as
`conflict_state: override_applied` and are subject to the same value validation.

## Guards and publication

- `fitba squad` runs the resolver after building the squad rows; a source failure
  is recorded and lower tiers still run.
- `fitba publish` joins the normalized foot rows into `squad/aberdeen.json`.
- `scripts/check_player_attributes.py` enforces the foot value domain,
  provenance, source registry permissions, Wikipedia revisions/permalink,
  conflict nulls and coverage. It also rejects `source_text`, `wikitext`,
  `raw_html`, `birth_date` and similar fields from the published payload.
- `scripts/check_squad.py` requires the attribute block and the role/playing-time
  blocks.
- CI runs the guards; the daily workflow runs the resolver before publication.

## Known gaps

- Foot coverage is low without Sportmonks; Wikipedia rarely states a preferred
  foot.
- Sportmonks metadata coverage for the Scottish Premiership and public-display
  terms still need to be confirmed.
- Wikipedia may be incomplete or wrong; the resolver records the revision and
  publishes unknown rather than guessing.
- Side is not a foot field and is not sourced here. See [roles.md](roles.md).
