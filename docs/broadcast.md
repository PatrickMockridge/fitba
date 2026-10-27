# How to watch: broadcast and streaming

**Status:** curated fixture information. Last reviewed 2026-10-27.

`/matchday/`, `/matches/` and `/fixtures/` show a **How to watch** state for
upcoming fixtures. It answers a narrower question than a broadcaster schedule:
what does an official source say about this fixture, in each region, at the last
check?

## Source rule

Broadcast facts are curated from an **official club or SPFL page**. The
per-fixture AFC “How to watch | Live coverage … on RedTV” article and the SPFL
“TV selections and fixture changes” page are the sources. Broadcaster websites
are not scraped, and no broadcaster is inferred from team, competition, venue or
kickoff.

No article body, price, discount code, stream URL, account detail or paywall
content is published. The panel links to the official source and shows its
title and checked date.

## Regions and states

Domestic (**UK & Ireland**) and international are separate:

| State | Meaning |
|---|---|
| `confirmed` | An official source names a platform, medium and access for this fixture. |
| `blackout_window` | Domestic Saturday 15:00 only: the UK live-video blackout applies. No UK outlet is claimed; audio and overseas rights are not inferred. |
| `not_announced` | No outlet is announced in the checked official source. **This does not mean the match is not televised.** |
| `unknown` | The source does not state availability, or the fixture/source is in conflict. |

International is never derived. It is `confirmed` only when an official source
states an outlet; otherwise it stays `unknown`. A fixture not listed by a
broadcaster is not evidence that it is unavailable, and a previous season’s
article is never reused.

## Artifact

`broadcast.json` has one row per scheduled fixture, keyed by fixture id as a
string. Each row carries identity fields, `state` (`curated`, `derived`,
`fixture_conflict`, `source_conflict`), domestic and international blocks,
sources and the policy note. Rows without a curated match are rule-derived:
Saturday 15:00 is a blackout window; other slots are not announced; international
is unknown.

A curated row is joined only when its date, kickoff, competition, teams and
season match the canonical scheduled row. A mismatch withholds the broadcaster
rather than publishing a stale claim.

`reference/broadcast.yaml` is the curated ledger. `config/broadcast.yaml` holds
the allowed hosts, source hosts, exact policy copy, blackout rule and service
link. The builder is `src/fitba/publish/broadcast.py`; it makes no network
calls.

## Curation checklist

1. Open the official AFC or SPFL page for the fixture.
2. Confirm the date, kickoff, competition and teams against
   `fixtures/index.json`.
3. Record only the named platform, medium and access. Do not copy price, stream
   time, discount code or article text.
4. If the page does not state a region, set that region to `unknown`.
5. Set `verified_at` to the date checked; use only `afc.co.uk` or `spfl.co.uk`
   source URLs.
6. Run `fitba publish` and `scripts/check_broadcast.py`.

## Checks

`scripts/check_broadcast.py` validates the artifact and schema, one row per
scheduled fixture, identity matches, source hosts and HTTPS, outlet/status
combinations, blackout eligibility, policy copy, no numeric leaves, no
price/subscription/stream tokens, and curated orphans. `guard.semantic` runs it
after publish; `make broadcast-check` runs it directly.
