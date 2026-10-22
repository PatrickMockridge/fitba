# Brand: fitba

**Status:** canonical visual and verbal brand system. Last reviewed 2026-10-22.
**Relationship:** [identity.md](identity.md) governs what fitba is and who it is
for. This document governs how that identity looks and sounds. [Page
contracts](page-contracts.md) govern what the pages must keep visible.

## The idea: Granite & North Sea

Aberdeen is a grey stone city on a cold coast under a rare sky. fitba should
feel like a civic record printed on granite paper: solid, cool, precise, with
sudden colour from the club red and the aurora. Not tartan. Not shortbread. Not
a seagull mascot.

The brand is built from five facts, used as structure rather than decoration:

1. **Granite.** The city's stone. The neutral palette, the paper texture, the
   weight of the type.
2. **The North Sea.** Pittodrie is about 500 yards from the water. The sea is the
   secondary colour and the horizon motif.
3. **The aurora.** The fans sing "The Northern Lights of Old Aberdeen". The
   aurora is a rare accent, not a background.
4. **1903.** The club was founded in 1903. The year is a quiet mark, not a
   headline.
5. **A one-club city.** Aberdeen is not Glasgow, Edinburgh or Dundee. The
   traditional rivalry is the New Firm against Dundee United. The city and the
   club are one identity; the site should sound like it knows that.

The imagery must never crowd out the record. The data is the product; the brand
is the room it sits in.

## Palette

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#f4f3ee` | `#0e1416` | Page ground; granite paper |
| `--surface` | `#fbfaf6` | `#151d20` | Cards and panels |
| `--ink` | `#15181a` | `#eef0ec` | Primary text |
| `--muted` | `#697176` | `#a7b0b2` | Secondary text |
| `--line` | `#b7bcbe` | `#344145` | Rules and borders |
| `--accent` | `#c8102e` | `#ff4d63` | Club red; primary action and eyebrow |
| `--sea-700` | `#0f4c5c` | `#6fc7d1` | North Sea; secondary labels, links |
| `--aurora-green` | `#4fd1a1` | `#6ee7b7` | Aurora accent; used sparingly |
| `--aurora-violet` | `#7a6bd6` | `#9b8cf0` | Aurora accent; used sparingly |
| `--green` | `#1c6b45` | `#63d29a` | Data success / confirmed |
| `--amber` | `#8a6100` | `#e9bf61` | Data warning / curated |
| `--red` | `#a3261e` | `#ff8a80` | Data danger / loss |

Rules:

- Club red is the only primary accent. Do not use the aurora as a general
  highlight.
- The sea is a secondary colour. It may carry labels, links and the horizon
  rule; it does not replace red for the club.
- Semantic data colours stay semantic. Never use the aurora to mean "good" or
  the sea to mean "unknown".
- Every colour combination must meet normal-text contrast in both themes.

## Typography

- **Display:** `"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia,
  "Times New Roman", serif`. Used for H1, H2 and the wordmark. A civic,
  print-record voice.
- **Body:** the system sans stack. Used for prose, navigation, controls and H3.
- **Data:** the system mono stack with tabular numbers. Used for tables, metric
  values and codes.
- Do not load a web font that requires a network request at build or runtime.
  The system stacks are the brand.
- Do not use all-caps for body copy. Eyebrows and the place line may be
  uppercase with generous tracking.

## Motifs

### Granite paper

A very low-opacity speckle behind the page, layered with a cool radial wash. It
should read as paper, not as a pattern. The texture is in the CSS token
`--speckle`; do not add a second texture.

### The horizon

A short rule under the home hero and in the city card: sea to aurora green to
aurora violet. One rule per page at most. It is a horizon, not a rainbow.

### The gull mark

Three simple curved strokes, used once in the footer and once in the city card.
It is a coastal mark, not a mascot. No eyes, beaks, bodies or cartoon gulls.

### 1903

The founding year appears in the place line and the city card. It is a quiet
fact. Do not turn it into a crest, a badge or a large numeral.

## Voice

- **Dry, direct, civic.** Aberdeen humour is deadpan; the site should be too.
- **Warm underneath.** This is a club the owner has supported for 35+ years, not
  a neutral wire service.
- **Specific.** Name the street, the stand, the sea, the competition, the year.
- **Never pastiche.** No "fit like?", no tartan, no shortbread, no fake Doric, no
  "Granite City" in every sentence.
- **The city is context, not a marketing claim.** The record remains the point.

## Where the brand appears

- **Header:** the granite-cut brand mark, the wordmark, the identity line.
- **Home hero:** the place line, the identity line and the horizon rule.
- **Footer:** the gull mark and the place line next to the independence line.
- **About:** a "city and club" card with the granite, North Sea, aurora, 1903 and
  New Firm context.
- **History:** the place line in the era header; the record is otherwise
  unchanged.
- **Data pages:** the palette and type carry the brand. Do not add decorative
  motifs to tables, charts or transfer cards.

## What the brand may not do

- Remove, hide or reorder contracted data.
- Replace a declarative heading with a question.
- Turn the aurora, gulls or granite into a repeated gimmick.
- Use the city's imagery to imply the club endorses the site.
- Introduce a new font, icon set or image dependency for decoration.
- Change the identity line, the reader or the editorial stance without owner
  approval.

## Implementation

- Tokens live in `web/app/globals.css`.
- The gull mark is `web/components/GullMark.tsx`.
- The place line is `.place-line`; the horizon is `.hero::after`; the reusable
  rule is `.aurora-rule`.
- The city card is `.city-card` on `/about/`.
- The page contract still wins: every brand change must pass
  `uv run python scripts/check_web_contract.py --ci` for the root and `/fitba`
  builds.
