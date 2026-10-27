# Injuries and availability

**Status:** live. Last reviewed 2026-10-22.

Injuries and suspensions are a **special case of team news**, not a normal
statistic. They are time-sensitive, often uncertain, and easy to present as
fact when they are not. This layer keeps them separate from the news feed and
from the provider `injured` boolean.

## Sources

- **Primary:** a curated ledger of official AFC team news.
- **Optional:** API-Football `/injuries`, only when the provider's league
  coverage says injuries are covered for the season.
- **Not team news:** the provider `injured` boolean on a player profile. It has
  no type, reason, date or expected return.
- **Unknown:** no verified public entry. It is never converted to “fit” or
  “available”.

At the last check API-Football reports `injuries=false` for Scottish 2026, so
the provider snapshot is `unavailable`. The app says so; it does not advertise
a feed that returns nothing.

At 2026-10-27 the curated ledger has seven verified entries, all from the
official AFC Falkirk press conference: Mats Knoester (out, thigh tendon),
Connor Ronan (out, medial knee ligament), Lewis Mayo (out for around two
months, foot injury), Dan Happe (suspended), Kristers Tobers (doubtful,
returning from a long-term knee injury and a virus), Findlay Marshall and Tony
Yogane (doubtful, back in training after illness). No return date is invented
where the club gives no timeframe. The scouting layer reads them through the
same resolved availability payload; it does not keep a second ledger.

The published payload carries two universes. The **official list** covers all 34
players including loanees out (7 known / 27 unknown at the last check). The
**active squad** covers the 29 players not out on loan (7 known / 22 unknown).
Analysis uses the active universe; the availability and needs surfaces use the
official universe. Every count names its universe, so the two numbers are not
mistaken for a contradiction.

## Ledger

`reference/availability.yaml`:

```yaml
entries:
  - player_key: api:player:...
    player_name: ...
    status: out | doubtful | suspended | returned | available | unknown
    reason_category: injury | illness | suspension | international | personal | unknown
    reason: ...
    expected_return: null
    effective_from: YYYY-MM-DD
    effective_to: null
    source_id: afc_news | afc_official | api_football
    source_url: https://www.afc.co.uk/...
    source_title: ...
    verified_at: YYYY-MM-DD
    confidence: confirmed | reported | curated | unknown
    note: ...
```

Rules:

- `out`, `doubtful`, `suspended`, `returned` and `available` require an allowed
  AFC source URL and `verified_at`.
- `unknown` may omit a URL and is a valid published state.
- A stale entry becomes `unknown` for selection; the ledger status is retained
  and marked stale.
- A provider signal never sets `available`, `returned` or `suspended`; a
  provider “Missing Fixture” row is a `provider_signal`, not team news.
- A conflict between a curated `available` and a provider `out` is shown, not
  silently resolved.
- Context-only names without a public URL live in
  `reference/availability.candidates.yaml` (private, not published) until a
  curator verifies an official source. They do not affect the predicted XI or
  needs.

## Predicted XI

- `out` and `suspended` players are excluded.
- `doubtful` players remain selectable with a confidence downgrade.
- `returned` players are selectable with a small availability weight.
- `unknown` players remain selectable. If the ledger is entirely unavailable,
  selection confidence is not blanket-downgraded; the page says availability is
  unknown, not assumed fit.
- A player with no verified availability cannot retain high confidence when a
  partial ledger exists.
- The lineup block publishes availability counts (`known`, `unknown`, `out`,
  `suspended`, `doubtful`, `returned`, `conflicts`), `as_of`, source ids and
  selection risks.

## Commands

```bash
uv run fitba availability            # show the local snapshot
uv run fitba availability --refresh  # optional provider + ledger merge
```

The daily refresh is `continue-on-error` and cannot block publish. The publish
path reads local data only.

## What is not measured

- Injury type, severity, expected return or doubtfulness without a public source.
- Suspensions without a public source.
- Opponent availability without a curated entry.
- A player's fitness or “trust” from minutes.

No blame narratives and no “confirmed team news” claims.

## Derived selection signals (season overview)

The `/analysis/` availability block separates three evidence tiers:

1. **Official team news** — the curated AFC ledger only, with source URL,
   confidence and verification date. “Available” is a ledger entry, not a
   medical clearance.
2. **Derived selection signals** — competition-scoped suspension watch and
   inferred absence. These are not official team news.
3. **No verified news** — a count, never a fit list.

Suspension rules live in `config/suspensions.yaml` with `verified` flags. Until
the current SFA protocol is sourced and signed off, a row is `watch` or
`review_required`, never a player-level ban. Second yellows are derived from
same-match yellow+red events; the provider’s flag is not trusted.

Inferred absence uses named-squad membership from
`data/normalized/matches/player_squads.parquet` (starters and named substitutes,
including unused). It requires two consecutive omissions over a six-fixture
window with complete bench coverage, established squad inclusion, and no
official override. It is labelled “not in the last two matchday squads — reason
not published” and is never an injury diagnosis. AFC team news remains the only
injury source.
