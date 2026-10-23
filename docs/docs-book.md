# Documentation book

**Status:** live in the repository. Last reviewed 2026-10-24.

The Markdown files in `docs/` are the source of truth. mdBook renders the same
files as a local, browsable book; it is not a second source of numbers and it is
not a route on the fitba website. The book is built in the repository and
served locally with `mdbook serve`.

## Source layout

```text
book.toml          mdBook configuration (src = "docs", build-dir = "book")
docs/              the documentation source, including SUMMARY.md
docs/SUMMARY.md    the book navigation and the chapter order
theme/             the local mdBook template, head and palette overrides
book/              generated output; gitignored, never edited
```

The book is built from the same files that are read in the repository. A change
to a documentation page appears in both places; do not create a second copy.

## Themes

The book has two named palettes and an Auto option:

- **Merkland** — the light palette, mapped onto mdBook's `.light` class.
- **Aurora** — the dark palette, mapped onto mdBook's `.coal` class.
- **Auto** — follows the operating system's `prefers-color-scheme`.

The theme popup keeps mdBook's class names, so syntax highlighting, the
pre-paint theme script and `localStorage` continue to work. The visible labels
are set in `theme/index.hbs`; the colours and the System 7 grammar are in
`theme/fitba.css`. The canonical tokens live in `web/app/system.css`.

The book follows the design grammar: square geometry, 1px rules, no soft
shadows, mono labels, tabular numbers, club red as the accent, and no
colour-only meaning. The content measure is capped and wide tables scroll
inside their wrapper rather than forcing page-level overflow.

The `theme/` overrides are local copies. They do not receive upstream mdBook
fixes automatically; when mdBook is upgraded, compare them with the bundled
theme and carry over the relevant changes.

## Build and serve

```bash
mdbook build   # build book/
mdbook serve   # local preview at http://localhost:3000
```

The main site build does not depend on mdBook. The book is not published to the
website.

## Adding or changing a chapter

1. Edit the Markdown in `docs/`.
2. Add the page to `docs/SUMMARY.md` under the correct part. Chapter titles must
   be unique.
3. Keep relative links inside `docs/`. Link to the repository URL for files
   outside `docs/` (licence, config, code), and use code spans for local paths
   that are not book chapters.
4. Run `mdbook build` and the relevant documentation checks.
5. If the change affects a published number or a metric definition, follow
   `docs/metric-changes.md` and the registry process; the book never replaces
   the audit.

## Accessibility and search

Every content page carries a skip link to `#main-content` and the main landmark
id. mdBook provides search and keyboard navigation; the theme keeps visible
focus and a readable contrast in both palettes. The generated `toc.html` is a
noindex sidebar iframe fallback, not a content page.

The documentation is a repository artifact. It is not linked from the main site
footer, is not in the site sitemap, and is not copied into the Pages build.
