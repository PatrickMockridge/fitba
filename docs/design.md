# Design foundation: fitba

**Status:** canonical design foundation. Last reviewed 2026-10-24.
**Precedence:** [identity.md](identity.md) governs what fitba is, who it is for
and how it speaks. [page-contracts.md](page-contracts.md) governs what each route
must keep visible. This document governs how the record should look and feel.
Where they conflict, identity and the page contracts win.

## The failure this corrects

Two UI passes have been reverted.

- The first removed data and replaced declarative headings with questions. It
  treated "simpler" as the goal.
- The second added a place line, a serif display face, a gull mark and a
  heritage palette. It treated "tradition" as a costume.

Both were surface changes. Neither started from what the site is for. Gravitas
is not a typeface, a muted palette or an "est. 1903" badge. Tradition is not
nostalgia. A style that has to announce its seriousness is not serious.

This foundation starts from the record.

## What the design is for

fitba is a public record of Aberdeen FC for people who read closely. The design
has four jobs, in order:

1. **Make the evidence legible.** Tables, numbers, sources, confidence and
   coverage are the primary visual material. Nothing may compete with them.
2. **Make comparison possible.** The reader should be able to move between
   seasons, players, matches and sources without losing their place. Stable
   columns, aligned numerals, consistent labels and stable routes matter more
   than novelty.
3. **Make the record credible.** The page should look like it will still be
   true next week. Dates, sources, method notes and captions are part of the
   visual language, not footnotes to hide.
4. **Carry Aberdeen.** The city and club are specific. That specificity belongs
   in the content, the names, the record and the writing. It is not a theme
   park of gulls, tartan and slogans.
5. **Give the reader agency.** The reader chooses the depth: headline, table,
   method, source. The interface exposes those choices instead of funnelling the
   reader. This is the desktop-publishing idea: the reader is a builder with
   tools, not a passive feed consumer.

## Gravitas, operationally

Gravitas is a consequence of proportion, restraint and consistency. It is not a
mood.

- **One hierarchy.** A masthead, a page title, section rules, a data block, a
  note, a folio. The reader should never have to guess what level they are on.
- **Density with air.** Tables can be dense; the page around them needs enough
  margin to let them breathe. Do not confuse whitespace with seriousness.
- **Few accents.** Club red is the primary accent. Semantic colours are for
  data states. There is no third decorative accent.
- **Hard edges and rules.** Hairlines, rules and grids carry the structure.
  Rounded cards, floating shadows, pill-shaped controls and translucent app
  bars are not the default language of a record.
- **Tabular numbers.** Every number that can be compared is set in a tabular
  face and aligned. A table that cannot be scanned is not a table.
- **Quiet interaction.** No reveal animations, no hover effects that move the
  page, no gradients that pulse. Focus and hover states are clear and still.
- **Permanence.** Navigation, page anatomy and labels stay stable. A redesign
  is not a reason to move the furniture.

## Tradition, operationally

Tradition is continuity, not period styling.

- **The record is the tradition.** The club since 1903, the Cormack era as a
  chapter, the seasons, the managers, the transfers. The design should feel like
  an archive that is being kept, not a campaign that is being launched.
- **Dates and provenance are visible.** A record earns trust by saying when it
  was made and where it came from. The visual language should make dates,
  sources and method notes easy to find, not decorative.
- **The club's red is the club's.** It is not a generic accent. Use it where the
  club is the subject: the masthead, the primary action, the key emphasis.
- **The city is content.** Aberdeen is the granite city; Pittodrie is 500 yards
  from the North Sea; the gulls; "The Northern Lights of Old Aberdeen"; the
  one-club city; the New Firm derby with Dundee United. These belong in the
  writing, the history and the matchday context. They do not belong in icons,
  mascots, slogans or a "heritage" palette.
- **No pastiche.** No fake vintage, no sepia, no faux newspaper, no tartan, no
  shortbread, no "Granite City" in every sentence, no invented place lines.

## Interface grammar: System 7 as a constraint, not a costume

The 1990s Macintosh reference is a **system of constraints**, not a set of
stickers.

What the period gives us:

- square geometry, 1px frames and hard rules;
- a static masthead and a document sheet, not a floating app bar;
- controls that look like controls: buttons, segmented choices, pop-up menus,
  checkboxes and disclosure triangles;
- inverted selection (ink on paper, paper on ink) instead of decorative accent
  colours;
- mono labels and tabular numbers for data;
- a strict document grid and a visible hierarchy;
- the idea of the reader as a builder with tools and choices.

What the period does **not** license:

- fake traffic lights, bevels, folder tabs, menu-bar parody or wallpaper;
- pixel or bitmap body text;
- beige, platinum, sepia or "vintage" gradients;
- skeuomorphic icons, mascots, gulls, tartan, shortbread or slogans;
- a costume that announces "retro" before it explains the record.

The identity is the consistency of the grammar, not a logo or an accent colour.
A reader should feel the system before they notice a single decorative choice.

## The core visual system

### Page anatomy

A page is a record sheet, not a feed.

- **Masthead:** the wordmark and the primary navigation on a solid paper ground,
  separated by a rule. It should read as a masthead, not an app bar.
- **Page head:** one H1, a short lede, the state and date. No decorative hero
  image is required.
- **Section:** a rule, a small label, a declarative heading, then the data or
  the argument.
- **Data block:** a table or a chart with a caption, units, scope and source.
  The table is the default for a register; a card is the exception for editorial.
- **Note:** method, caveat or definition, visually quiet but always present
  where it changes the reading.
- **Folio:** footer identity, independence, freshness, method and sources.

### Typography

Typography is a system of roles, not a font mood.

- **Display / H1:** a grotesque with a strong, quiet authority. Not a serif.
  Not a fashion face. Not a condensed sports-poster face. Not pixel or bitmap
  body text.
- **Section / H2:** the same family, one weight down. Hierarchy through size,
  weight and space, not through a second decorative face.
- **Text:** a readable sans with a large x-height and good numerals.
- **Data:** a mono or tabular sans for numbers, codes and table cells. The same
  face across the site.
- **Labels:** uppercase or small caps with generous tracking, used sparingly.

The final typefaces are chosen **after** the grid and reading modes are agreed,
in a specimen that tests: a league table, a transfer register, a long method
note, a matchday read, a mobile roster. System stacks are the first candidate;
a new font dependency is not required to prove the system. A face that cannot
set a table is not a candidate. A face that looks "heritage" is not a
qualification.

### Colour

Colour has a job. It is not a mood board.

| Role | Use |
|---|---|
| Paper | Page ground; a cool, quiet neutral |
| Ink | Primary text and rules |
| Club red | Masthead, primary action, club emphasis |
| Semantic green / amber / red | Confirmed, curated/warning, loss/danger |
| Europe blue | European cut-off only; semantic data, not decoration |

Rules:

- No decorative gradients in the application shell.
- No colour-only meaning. Every badge has a text label.
- Every text/background pair meets normal-text contrast in both themes.
- No sea, aurora or heritage palette in the UI. The city and coast are content,
  not chrome; they may appear in an editorial image or a single historical note,
  never as a site-wide accent scheme.

### Themes

A theme changes palette tokens only. It does not change the grammar, type,
layout, density, routes, data or contracts. The same table, controls and
hierarchy must work in every theme.

The current range is Aberdeen-grounded, not a set of Apple product colours:

| Theme | Reason |
|---|---|
| **Merkland** | The Merkland Road End: the city's granite and the club's red and white. The standard light theme. |
| **Red Matchday** | The AFC match programme: off-white paper, black ink, deep red. It absorbs the Mono high-contrast discipline; every state is carried by its text label. |
| **Aurora** | "The Northern Lights of Old Aberdeen": deep night sky with a restrained green-violet accent. The standard dark theme. |
| **Floodlight** | A night match at Pittodrie: dark green-black, white rules, club red. The alternative dark theme. |

Production behaviour:

- **Auto** follows the operating system: light uses Merkland, dark uses Aurora.
- The footer theme control can pin Merkland, Red Matchday, Aurora or Floodlight.
  The selection is stored in the browser and applied before paint; selecting
  **Auto** clears the override.
- Merkland and Aurora are the standard themes. Red Matchday and Floodlight are
  the alternatives.

Rules:

- No iMac product colours, arbitrary accent swaps or themes named after Apple
  hardware. A theme needs a reason in the record, the club or the city.
- Red Matchday must remain readable without colour; badges, form chips and
  cutoffs rely on text labels.
- Every theme must meet the same contrast and focus requirements.
- Themes are reviewed with the same screenshots and contract checks as any other
  visual change.

### Tables and data

- Tables are the default representation for registers, standings, form,
  strength, needs and source layers.
- Columns are stable, headers are scoped, numbers are tabular and right-aligned,
  and the unit is in the header or the caption.
- A table carries a caption or an accessible name, the scope/coverage and the
  source. Those are part of the design, not optional chrome.
- A chart must be accompanied by the table or the data it encodes. It does not
  replace the evidence.
- A Nightingale rose uses equal-angle sectors and a radius proportional to the
  square root of the percentile, so sector area encodes the value. It always has
  a title/description, a companion table with the raw value, percentile and
  cohort n, and an explicit unavailable state. It never draws a missing value
  as a zero petal.
- Cards are for editorial units: a theme, a transfer, a match read. They are not
  the default container for every section.

### Club identity in match views

Match records have two sides and a persistent identity rule:

- **Aberdeen is red.** Use a club-red wash, a 3px club-red edge and the literal
  word "Aberdeen" on its scoreboard side, stat column, fxG side, timeline rows,
  lineup and player rows.
- **The opponent is neutral.** Use surface and line tokens; do not introduce a
  second opponent hue. `--s-europe` is reserved for European cut-offs.
- **Colour is not the only cue.** Every side keeps its team name and a visible
  team key. The rule works in Red Matchday and in both dark themes.
- The rule is normative on `/matches/<fixture_id>/`; see
  [match-scoreboard.md](match-scoreboard.md). It does not change league,
  history or recruitment tables.

### Interaction

- Filters look like controls, not pills. Controls are square, labelled and
  invert when selected. Buttons are for actions, not for decoration.
- The default state is the evidence-complete state. A filter may narrow a view;
  it may not become the only way to see the record.
- No animation is required to understand the page. `prefers-reduced-motion` is
  respected.
- Focus is visible. Keyboard order follows reading order.

### Accessibility

Accessibility is part of the record, not a later pass.

- One visible H1; no skipped heading levels.
- Table captions or accessible names; `scope` on headers.
- Meaningful link text; no repeated "source" links without context.
- Text alternatives for charts and decorative images.
- Contrast, zoom and 390px layouts checked before a design is called done.

## What not to do

These are the moves that produced the reverted passes:

- Remove data, shorten a table or hide a caveat to make a page feel lighter.
- Replace a declarative heading with a question.
- Add a serif display face, an "est. 1903" badge, a gull icon, a tartan motif or
  a "Granite City" slogan as a shortcut to identity.
- Use a muted "heritage" palette, faux vintage, sepia or a texture that reads as
  a filter rather than a material.
- Confuse the System 7 grammar (square controls, rules, panes, inverted
  selection) with the System 7 costume (traffic lights, bevels, folder tabs,
  pixel body text, wallpaper).
- Turn every section into a card, every action into a pill, every page into a
  landing page.
- Invent a tagline, place line or brand concept and present it as the club's.
- Let a decorative element sit above the evidence in the hierarchy.
- Change the visual system without a written reason tied to this document and a
  page-contract check.

## The documentation book

The docs are rendered as a local mdBook book in the repository. The book uses
the same System 7 grammar as the app: square geometry, 1px rules, no soft
shadows, mono labels, tabular numbers and club red as the accent. The palette is
limited to the two standard themes:

- **Merkland** (light) is mapped onto mdBook's `.light` class: paper
  `#f0f0ed`, surface `#fcfcfa`, ink `#17181a`, club `#c8102e`.
- **Aurora** (dark) is mapped onto mdBook's `.coal` class: paper `#0b1020`,
  surface `#121a2e`, ink `#eef1f8`, club `#ff5a6e`.
- **Auto** follows `prefers-color-scheme`.

The theme switcher is labelled Merkland, Aurora and Auto. The book does not
offer the Red Matchday or Floodlight alt themes; they remain app themes. The
palette mapping and component overrides live in `theme/fitba.css`, and the
canonical tokens remain in `web/app/system.css`. The book keeps the identity
line on its landing page and a skip link; it does not repeat the line on every
chapter. The palettes and the skip link are part of the local theme.

## Implementation order

No UI change starts with a font, a colour swatch or a motif. The order is:

1. **Agree this foundation.** The owner confirms the meaning, the reading modes
   and the non-negotiables.
2. **Build a specimen.** A noindex, unlinked route with the type roles, a real
   league table, a transfer register, controls, data states, a labelled read,
   provenance, notes and mobile. Use real published data, read-only. Choose the
   faces and the grid here; no production page changes.
3. **Apply the shell.** Masthead, page anatomy, rules, footer. No data page
   redesign.
4. **Apply one data page.** The most table-heavy page, reviewed against the page
   contract and at 1440px and 390px.
5. **Roll out in reviewed steps.** Each step passes
   `uv run python scripts/check_web_contract.py --ci` for the root and `/fitba`
   builds.

A design change that cannot say which of the jobs it serves is not ready.

## Open decisions

These are decisions for the owner, not for an agent to invent:

- How much of the city and club story belongs on the site, and where. The
  history page and About are the natural homes; the data pages should stay
  data-led.
- Whether the masthead is sticky or static. The specimen uses a static masthead;
  confirm or choose sticky after review.
- Whether club red is used only for actions and club emphasis, or also for
  section labels.
- Whether there is any editorial photography, and if so under what licence.
- The final typefaces, chosen in the specimen.
- How much the site says about the New Firm rivalry and the one-club city
  without turning context into a marketing line.
