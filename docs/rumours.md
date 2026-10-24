# Rumour mill and fan signal

**Status:** live, data-tolerant. Last reviewed 2026-10-21.

The rumour mill is a curated, source-linked register of Aberdeen-linked links,
plus a derived fan signal from AFC Chat's Rumour Mill forum. It is **not** the
confirmed transfer register. The two registers never merge.

Machine-readable inputs:

- `reference/rumours.yaml` — curated rumours and opinions (human-maintained).
- `reference/transfers.yaml` — confirmed business (see [transfers.md](transfers.md)).
- AFC Chat RSS and sampled topic first pages — fan signal only.

Published outputs:

- `web/data/generated/rumours/aberdeen.json` — rumour rows, counts, opinions.
- `web/data/generated/rumours/profile.json` — advisory recruitment profile.
- `web/data/generated/forum/afc_chat.json` — topics, name signals,
  cross-reference labels and aggregate sentiment.

## Two registers, one bridge

| Register | What it means | Where it lives |
|---|---|---|
| Confirmed business | A completed move with a verification record. | `/transfers/` |
| Rumour | An unconfirmed link, denial or historical claim, with public sources. | `/rumours/` |
| Fan signal | A name mentioned in sampled forum posts, with a mention count. | `/rumours/` |

A rumour becomes `confirmed` only when the same move is in the transfer register.
The row then carries `linked_transfer_id` and is a historical record, not a second
source of truth. A fan mention is never promoted to a rumour automatically.

## Rumour statuses, confidence and sources

`status` is a lifecycle label, not a probability:

- **active** — the link is still live as of `last_seen`.
- **denied** — the club or a credible source has denied it.
- **confirmed** — the move is completed and present in the transfer register.
- **stale** — no new source within the editorial window.

`confidence` is editorial and must be justified by `source_types`:

- **high** — a direct club announcement or a named, reliable reporter, or
  multiple independent sources.
- **medium** — one credible outlet or reporter, not yet corroborated.
- **low** — forum-led, aggregator-led, or otherwise thin sourcing.

`source_types` is a subset of `press`, `journalist`, `forum`, `club`. Every row
requires at least one `source_url`. The guard rejects rows without URLs, invalid
statuses, a confirmed row without a transfer link, and a non-confirmed row with
one.

No fabricated quotes, no player abuse, no betting/odds framing.

## Fan signal: what is ingested

Source: **AFC Chat — The Rumour Mill**
(`https://afc-chat.co.uk/forums/index.php?/forum/20-the-rumour-mill/`).

The forum advertises `search=yes, ai-train=no, use=reference`. fitba uses the text
as a reference signal only:

- the RSS feed provides the recent topic index;
- the **first page** of up to 8 recent topics is sampled, rate-limited;
- post text is stored only in the gitignored normalized store
  (`data/normalized/forum/`);
- **no raw post bodies, usernames, avatars or quotes are published**;
- the text is **not used for AI training** and no model is trained on it.

This is a sample of recent topics, not the whole forum, the whole thread or the
fanbase. The page states the sample size.

## Name extraction

A gazetteer is assembled from:

- the Aberdeen squad (API-Football `/players/squads`);
- the confirmed transfer register;
- curated rumour rows and `reference/players.yaml`;
- repeated capitalised names in the sampled posts, validated one-by-one against
  Scottish league squads (Premiership, Championship, League One, League Two).

Matching rules:

- full names match anywhere;
- a surname-only mention is accepted only when the surname is unique in the
  gazetteer, is at least four characters, is not on the ambiguous-surname list,
  and is not the first word of a sentence;
- quoted posts are removed before extraction so the same words are not counted
  twice;
- AMBIGUOUS surnames are rejected rather than guessed.

This is a rule-based gazetteer, not NER or an LLM. It will miss names outside the
covered leagues and it can still produce false positives; the mention count is a
signal, not a fact.

## Cross-reference labels

Each name signal gets a source-coverage label. It records **where else the name
appears**, not whether the rumour is true:

| Label | Meaning |
|---|---|
| `fan_only` | Mentioned on the forum, no matching press, club or confirmed record. |
| `cross_referenced_press` | The player has a curated press/journalist rumour row. |
| `cross_referenced_club` | The surname appears in official AFC news titles. |
| `cross_referenced_transfer` | The player appears in the confirmed register in the last 550 days; this is a register cross-reference, not a current deal. |
| `club_player` | The player is in the current Aberdeen squad. |
| `official_confirmed` | A curated rumour row for the player is confirmed and linked. |

Priority: press → confirmed rumour → current squad → recent confirmed transfer →
club output → fan only. The payload exposes the individual cross-reference flags
as well, so the reader can see the full set.

## Identity lookup

A capitalised name in a sampled post is resolved in this order:

1. the current squad, curated register and transfer register, as before;
2. the **former-player register**;
3. the **published scouted pool** (players at or above the scouting
   `pool.min_minutes` threshold, so the name has a public scouting profile);
4. if it is in none of those, one **API-Football player-profile search**
   (`/players/profiles?search=`) for the surname, accepted only when the
   surname and first name (or initial) leave exactly one identity.

The lookup label is published on each signal:

| Lookup | Meaning |
|---|---|
| `local` | A current squad or register identity. |
| `former_player` | Resolved in the former-player register. |
| `scouted_player` | Resolved in the published scouted pool. |
| `api_match` | Found only through the provider profile search. |
| `api_not_found` / `ambiguous` | Checked but not published as a resolved player; ambiguous names are never guessed. |

The lookup result is identity and current-club context, not a probability or a
transfer claim. A name that resolves in the scouted pool is still an external
name, not automatically a target.

## Affiliation

Every curated row and fan-signal name carries a canonical affiliation:

| Affiliation | Meaning |
|---|---|
| `current_squad` | An official current squad player. |
| `loan_out` | An official player out on loan. |
| `current_non_official` | An excluded API profile still at Aberdeen; not an official squad member. |
| `former_player` | A player in the former-player register. |
| `external_target` | A resolved player who is not at Aberdeen. |
| `unknown` | No resolved key or unique full-name match. |

Affiliation is derived from the current squad payload and the former-player
register, never from a transfer guess. A former player named as an incoming
link is a **return link** and is listed separately. The curated recruitment
profile and the fan-signal position/age mixes count `external_target` only;
current squad, current non-official and former players are excluded. The fan
table still shows every affiliation, so the split is visible rather than hidden.
A name-only row is unknown, not a target.

## Sentiment

Rule-based VADER (`vaderSentiment`) is applied to:

- sampled forum posts (quotes removed);
- curated press rumour claims;
- official AFC news titles.

Published aggregates only: count, mean and median compound, and positive /
neutral / negative shares (compound thresholds ±0.05). No post text or quote is
published.

Limits: VADER is a lexicon method tuned for social media. It is noisy on
sarcasm, football idiom, quoted opinion and short posts. The comparison is
**descriptive**, not a measure of truth, credibility or fanbase opinion. A small
sample is shown with its count.

## Recruitment profile

The advisory profile is derived from **active incoming external-target** curated
rumours only. Confirmed, denied and stale rows do not shape it, and current
squad, current non-official and former players are excluded. Return links are
published separately.

Each active row is weighted by:

```text
weight = confidence_weight * recency_weight
confidence_weight: high 1.0, medium 0.6, low 0.3
recency_weight: 0.5 ** (days_since_last_seen / 180), floored at 0.35
```

The profile publishes the weighted position, age-band, league and value-band
mixes, the cohort size, a short generated narrative, and `low_confidence: true`
when there are fewer than five active rows. It is **advisory**: the data-driven
scouting fit stays primary and a small cohort never overrides it.

## Opinions

Opinion cards live in `reference/rumours.yaml` under `opinions`. Each card must
cite at least one rumour id as evidence and must be human-written, data-cited and
clearly labelled as an opinion. The payload drops an opinion with no surviving
evidence. Opinions are not club guidance.

## Publication and guards

- `scripts/check_rumours.py` blocks raw post text, usernames, quotes and
  engagement counts from the web payload.
- It verifies that confirmed rumours link a real transfer, that non-confirmed
  rows do not, that every row is sourced and that `engagement` stays null.
- It verifies the small-cohort flag and the first-page/raw-post coverage flags.
- The confirmed transfer guard (`scripts/check_transfers.py`) remains separate.

## Engagement — separate project

Community engagement is deliberately **not built** in this phase.

`config/engagement.yaml` sets `enabled: false`, `provider: undecided` and lists
the intended features (votes, polls, rumour submissions). The static export has
no backend, so the page shows no vote counts and no local-only widget pretending
to be a shared community. `TODO(engagement)` marks the code boundaries.

Researched options, none chosen:

- **Supabase** — anonymous auth plus row-level security; lowest-effort fit for a
  static site.
- **Cloudflare D1 + Workers** — $0 self-managed alternative, more backend work.
- **Firebase** — mature auth and realtime, heavier vendor coupling.
- **Third-party embeds** (Giscus, Discourse) — not suitable for structured votes
  and polls.

Before anything ships it needs a moderation policy, abuse-resistant anonymous
identity, rate limiting, a privacy note, export and deletion, and a rule that an
unmoderated submission is never presented as fact.

## Known gaps

- The curated rumour register starts empty. It fills only when a human adds a
  sourced row; the page is honest about the empty state.
- Forum coverage is first pages of recent topics only, and the gazetteer covers
  the Scottish pyramid plus the Aberdeen squad, not every European target.
- VADER sentiment is noisy and should not be read as a poll.
- Cross-reference labels are coverage labels, not credibility probabilities.
- Club output is the official news listing; the X timeline is embedded by X and
  is not ingested, so it is not part of the cross-reference.
