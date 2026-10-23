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

At 2026-10-23 the curated ledger has two verified entries: Kristers Tobers
(`out`, official AFC press conference of 2026-10-08) and Mats Knoester
(`available`, official AFC interview of 2026-10-16, confidence `reported`). The
scouting layer reads them through the same resolved availability payload; it does
not keep a second ledger.

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
