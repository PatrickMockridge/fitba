# Player page specification

**Status:** normative. Last reviewed 2026-10-21.

This document defines what a player page is allowed to contain. Where a
component, comment or habit disagrees with this page, this page wins.

The page is a **projection** of one published result document. It does not merge
sources, choose between statistics or infer positions in React.

## Principles

1. **One page, one player, one document.** The route reads a single
   `players/<player_id>.json` result. The squad table is a different result and
   is not merged into the page.
2. **Named panels, fixed order.** Identity, Position, Playing time, Performance,
   Records. Only Records is conditional on having rows.
3. **One fact, one home.** A fact is not rendered as a primary value in two
   panels. A season summary and its per-competition breakdown may live in the
   same panel, labelled as summary and breakdown.
4. **Known-only attributes.** Preferred foot is shown only when a source states
   it. Unknown or conflicting foot is omitted from the page entirely. There is
   no “Unknown is not inferred” copy on the player page.
5. **Raw / derived / presentation split.** Raw feeds and normalized tables feed
   the Python publisher. The publisher emits the page result. React renders the
   result; it does not compute panels, choose tiles or merge records.
6. **Unknown is a state, not zero.** Missing data is `unavailable` or
   `not_applicable`, never zero. An unknown position never falls back to
   midfield.
7. **One chrome.** Every panel uses the same eyebrow / title / badge / body
   component. No bare stat rows, floating fine-print or unlabelled tables.

## Result types

The canonical result is `PlayerPageDocument`:

```ts
type DataStatus = "available" | "partial" | "unavailable" | "not_applicable";

type WarningCode =
  | "COVERAGE_PARTIAL"
  | "SOURCE_MISSING"
  | "NO_ROLE_EVIDENCE"
  | "POSITION_UNKNOWN"
  | "OTHER_RECORDS_ONLY";

interface Warning {
  code: WarningCode;
  message: string;
  field?: string;
}

interface KnownValue<T> {
  status: "known" | "unknown" | "conflict";
  value: T | null;
  reason?: string | null;
  source?: {
    id: string;
    url?: string | null;
    verified_at?: string | null;
  } | null;
}

interface Panel<T> {
  id: "position" | "playing_time" | "performance" | "records";
  eyebrow: string;
  title: string;
  status: DataStatus;
  badge?: string | null;
  data: T | null;
  note?: string | null;
  warnings: Warning[];
}
```

`PlayerPageDocument`:

```ts
interface PlayerPageDocument {
  schema_version: "1.0.0";
  player_id: number;
  season: string;
  generated_at: string;
  identity: IdentityBlock;
  panels: {
    position: Panel<PositionPanel>;
    playing_time: Panel<PlayingTimePanel>;
    performance: Panel<PerformancePanel>;
    records: Panel<RecordRow[]>;
  };
  warnings: Warning[];
}
```

The JSON Schema is `contracts/player-page.schema.json`. It uses
`additionalProperties: false` and closed enums. An accidental field or an
unknown status is a build failure, not a convention.

## Identity

| Field | Rule |
|---|---|
| name / full name / href | Required |
| display role | The primary position label shown on the page; a small info affordance links to the Position panel, with no header sentence |
| age / nationality / shirt number | Known only; omitted otherwise |
| side | Known only; omitted otherwise |
| preferred foot | `KnownValue`; render the value and source only when `known` |
| status / loan | One line; loan club and dates live here, not in a separate card |
| stats coverage | Not in identity; the Performance panel carries it |

## Position panel

- Title: **How this position was inferred**.
- The display role label is in the identity header; the panel does not repeat
  it as another heading.
- Body:
  - the display reason (current role override or career role);
  - current Aberdeen role starts, labelled **role starts**;
  - career slots and primary/secondary/stretch eligibility;
  - career heat map and season/team/scope history;
  - tactical notes, with source and date;
  - one method note.
- The same `RoleInferenceModel` is used by the squad position dialog, so the
  two views cannot drift.
- If there is no role evidence: `status` is `unavailable`/`partial`, the panel
  says so, and no position-specific tiles are shown. It still shows any
  available club history (season, team, competition, apps, starts, minutes);
  only when the provider has no history either does it say so explicitly.
- Every squad player therefore has a history surface: role history where
  observed, club history where only provider rows exist, and an explicit
  no-history state otherwise.

Time concepts are distinct:

- **role starts** — starts with a team-sheet role; Position panel only.
- **appearance starts / sub apps / minutes** — Playing time panel only.
- **matches / minutes on pitch** — defensive context subtable in Performance;
  labelled “matches”, not “starts”.

## Playing time panel

- Tiles: appearance starts, substitute appearances, minutes started, minutes as
  a substitute.
- Table: one row per competition with the same four fields.
- No role starts, no provider minutes and no duplicate note. The panel has one
  coverage badge and one note.

## Performance panel

- Season summary tiles selected in Python by the current display role family:
  goalkeeper, defensive, midfield, wide, forward. No React `if (group)`
  branches.
- Provider table: competition, team and role-relevant provider columns.
- Detail table: the remaining role-relevant provider columns; a caption, not a
  second panel heading.
- Defensive context subtable, defensive roles only: competition, matches,
  minutes on pitch, Conc, CS, OG.
- The panel has one coverage badge and one note. A metric may appear as a season
  summary tile and as a per-competition table row in the same panel, but not in
  another panel.
- If position is unknown: no role-specific tiles or detail columns; the panel
  says `position_unavailable` rather than defaulting to midfield.

## Records panel

- Only rendered when `other_stats` is non-empty.
- Title: **Records outside the main scope**.
- One table with the same row shape as the provider table, including time
  fields; badge “Not loan-club output”.
- Loan status is not repeated here; the identity line is the single status
  source.

## Repetition rules

| Fact | Single home |
|---|---|
| Display position | Identity header |
| Current/career role evidence | Position panel |
| Role starts | Position panel |
| Appearance starts / sub apps / minutes | Playing time panel |
| Matches / minutes on pitch | Performance defensive subtable |
| Goals, assists, cards, rating | Performance panel |
| Conc, CS, OG | Performance panel |
| Preferred foot | Identity, known only |
| Loan status | Identity line; records panel for loan-club records |
| Stats coverage | Performance panel |
| Provider caveats | Performance panel note |
| Role threshold/caveat prose | Position panel method note |

## Guards

- `scripts/check_player_page.py` validates every `players/<id>.json` against the
  schema and enforces:
  - one panel per id and the fixed order;
  - no unknown-foot text and no foot card;
  - no loan banner key;
  - no duplicate role heading;
  - no duplicate defensive section;
  - unknown position does not produce midfield tiles/detail;
  - the page route reads the document only.
- A field-parity test keeps `web/lib/player-page.ts` and the JSON Schema aligned.
- A rendered-page check for Müller, Devlin, Briedl and Yengi asserts one
  identity, one Position, one Playing time and one Performance block, with
  Records only when present.
