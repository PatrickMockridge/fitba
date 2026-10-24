# Former players

**Status:** live. Last reviewed 2026-10-24.

This page is the canonical method for the former-player register and the
`/former-players/` route. It defines the universe, the Aberdeen record, the
post-Aberdeen record, the rival badge and the sell-on watch. Where a component,
comment or habit disagrees with this page, this page wins.

The register is **not** a transfer-target list and **not** a claim about whether
a sale was good. It records what is public: the departure, the fee basis, the
Aberdeen record, the league seasons that followed, any rival spell and whether a
sell-on clause can be computed.

## Universe

A former player is a player whose latest **outgoing** row in the published
transfer register is a `permanent` or `free` move, who is not an official squad
member and who has no later permanent or loan return. The rule is applied after
selecting the latest outgoing row, not by filtering loans first: a free exit
followed by a same-window `loan_return` record is still an exit, because a
`loan_return` row alone does not reinstate a player.

- Coverage starts at **2019-20**, the confirmed register's start. Earlier
  departures are outside the record and are not inferred.
- Loans out and loan returns are not former players. Current loanees stay on
  `/loans/`.
- A player who returns is current, not former.
- An `excluded_players` row does not by itself make a player current. The
  register decides; a lingering excluded profile with a confirmed permanent out
  is former and carries a reconciliation note.
- Cross-source duplicates are merged only with verified identity. The known case
  is `D. McGeouch`: the API key and curated slug resolve to one row, with the
  alias kept. Ambiguous duplicates stay separate and are reported as a gap.
- The register is self-contained. The published payload is authoritative; this
  document does not restate volatile counts.

## Profile links

Every former player with an API id links to the standard
`/scouting/player/<id>/` profile. That profile carries the shared scouting
sections and an additive **Former Aberdeen player** section. There is no
former-specific player route, dialog or drawer. A player without an API id stays
plain text with an explicit reason. When no post-Aberdeen league season is
available, the standard profile uses the last covered Aberdeen season and labels
that basis; no cross-league percentile is inferred. See
[player-profile-standard.md](player-profile-standard.md).

## Aberdeen record

The Aberdeen record uses the covered history (`history/season=*/appearances.parquet`
and `player_match_stats.parquet`), Aberdeen team rows only, competitive
competitions only, 2019-20 onward.

- A bench selection is a **squad selection**, not an appearance. An appearance
  is a start or a substitute run with minutes.
- `first_season` and `last_season` are the covered record's bounds, not a claim
  about the player's first career season at the club.
- The final playing season is the season before a summer exit, or the exit
  season for a winter/out-of-window exit.
- The **early-career proxy** is a first covered appearance at age 21 or younger
  and at least 10 Aberdeen starts, but only when the arrival is inside the
  covered record. If the player joined before 2019-20, the covered first
  appearance is not the career debut and the proxy is `unknown`. This is not an
  academy register.
- Competition names are not published in the tenure breakdown because the
  provider's historical “FA Cup” label means the Scottish Cup. Season totals are.

## Post-Aberdeen record

The post-career record reads API-Football player seasons from the departure
season to the current season plus the player's full transfer history. It is
cache-first, bounded and resumable. Publish reads only the local normalized
tables; it never calls the network.

- **League rows only** feed the published totals and per-90 rates. Cup and
  European provider rows are stored locally but excluded because the provider
  repeats season totals across some cup entries (for example a domestic cup row
  carrying the league minutes and goals).
- National-team and friendly entries are excluded from the club record.
- One row is one player/season/competition/team. A missing season is a gap, not
  zero.
- The current club is taken from current-season stats, then the latest transfer
  history, then the latest covered season, then the register destination. A
  register destination is labelled **last known** with `coverage: historical`;
  it is never presented as a current club.
- `status` is `at_club`, `on_loan`, `free_agent`, `retired` or `unknown`.
  `coverage` is `current` only when current-season statistics confirm the club;
  a transfer-history or last-known club is `historical`. `retired` requires an
  explicit provider “End of career” record; a future curated retirement note
  must cite a public source.
- Provider ratings are league-relative. They stay per season and are not
  compared across leagues, aggregated into one rating or turned into a
  cross-league percentile.
- `top_flight_abroad` is published only where the league tier is configured;
  an unlisted league is tier-unknown, not tier 1.

## Rival badge

The configured rivals are Celtic, Rangers and Dundee United. The badge applies
to **any post-Aberdeen spell**, not only the current club. `rival_current` is
separate from `rival_spell`. The badge is a club fact, not a verdict on the
player.

A `sco:provisional-*` id is not proof of a Scottish club. Scottish/abroad and
rival resolution use `TeamRegistry` and `reference/history/markets.yaml`; an
unresolved club stays unknown.

## Sell-on watch

The watch lists the clauses in `reference/sell_on_clauses.yaml` and detects the
first subsequent permanent or free move away from the buyer club. A later loan
is not a trigger; a free move is `no_sale`.

A receipt is computed **only** when every required input is publicly evidenced:

- the clause percentage is known;
- the basis is `gross_fee` or `profit` (not unknown);
- the subsequent fee has a public anchor in `reference/sell_on_events.yaml`;
- for a `profit` basis, the original Aberdeen fee is disclosed or reported.

The arithmetic is `pct × fee` for gross fee, or
`pct × max(0, subsequent fee - original fee)` for profit, converted with the
configured FX rates and rounded once to the nearest £1,000. A receipt is an
**implied gross share before deductions**; instalments, add-ons, agent and
solidarity terms are unknown. Zero computed is not zero future income.

## Development and exit outcomes

The scorecard is descriptive:

- **young exit** — permanent/free departure at age 23 or younger;
- **early-career exit** — the developed proxy above;
- **with a fee** — disclosed, reported or undisclosed permanent/free exit,
  excluding free transfers;
- **post-career minutes** — covered league minutes only;
- **rival spell** — any post-Aberdeen club in the configured rival list.

It also shows, by exit season, exits, young exits, early-career exits and exits
with a fee. There is no composite score, no success rate and no good/bad-price
verdict. The counterfactual is unobservable: a later career does not prove a
sale was wrong, and a fee does not prove the sale was sportingly costless. The
identity charter's player / manager / structure split still applies.

## Nostalgia and selection bias

The page puts the Aberdeen record and the post-Aberdeen record side by side, with
minutes and seasons, so a single highlight or a later move cannot substitute for
the record. "What he did at Aberdeen" and "what happened next" are different
facts. A rival badge records a club move; it does not say the player betrayed
anyone or that the club was right to sell.

## Rumour affiliation

Former players are a separate affiliation lane in the rumour mill. The canonical
values are `current_squad`, `loan_out`, `current_non_official`,
`former_player`, `external_target` and `unknown`. A former player linked back is
a **return link**, listed separately; it is not a normal target. The fan-signal
position and age mixes count external-target names only. See
[rumours.md](rumours.md).

## Guards and coverage

- `scripts/check_former_players.py` validates the published index and seasons
  documents against the schema, the transfer register, the summary arithmetic,
  the sell-on missing-input states and the coverage block.
- `fitba.metrics.consistency:former.*` checks that the register, season totals,
  sell-on watch, affiliations and coverage reconcile with the other published
  payloads.
- The registry entries are `former.definition`, `former.summary`,
  `former.players`, `former.post-seasons`, `former.sell-on`, `former.scorecard`,
  `former.coverage`, `forum.former-profile` and `rumours.former-lane`.

## Commands

```bash
uv run fitba former-players status
uv run fitba former-players backfill --dry-run
uv run fitba former-players backfill --max-requests 400
uv run fitba former-players refresh --max-requests 180
uv run fitba publish --season current --profile public --require-validation
uv run python scripts/check_former_players.py
```
