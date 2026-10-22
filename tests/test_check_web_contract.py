from __future__ import annotations

import copy
import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_web_contract", ROOT / "scripts" / "check_web_contract.py"
)
assert SPEC is not None and SPEC.loader is not None
CONTRACT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CONTRACT
SPEC.loader.exec_module(CONTRACT)

LINE = "Aberdeen FC, without the noise."
LEDE = (
    "An independent, data-driven record of Aberdeen FC — the numbers, the sources "
    "and the argument, without the hot takes."
)

IDENTITY = {
    "line": LINE,
    "lede": LEDE,
    "banned_phrases": ["The Scottish pyramid", "from Pittodrie out"],
    "banned_headings": ["Who starts", "Who is next"],
}
SITE = {
    "markers": ["site.header", "site.footer"],
    "copy": {
        "site.header": [LINE],
        "site.footer": [LINE, "Not affiliated with Aberdeen FC"],
    },
    "links": ["/methodology/"],
}
SURFACE = {
    "id": "home",
    "path": "/",
    "owners": ["web/app/page.tsx"],
    "ci_states": ["full"],
    "states": {
        "full": {
            "markers": [
                {"id": "home.hero", "min": 1},
                {"id": "home.standings", "min": 1},
            ],
            "columns": {
                "home.standings": [
                    "#",
                    "Club",
                    "P",
                    "W",
                    "D",
                    "L",
                    "GF",
                    "GA",
                    "GD",
                    "Pts",
                ]
            },
            "indicators": {"unknown": 1, "freshness": 1},
            "links": ["/matchday/"],
            "headings": {
                "forbid_question": ["h1", "h2", "h3"],
                "h1": LINE,
            },
            "copy": {"home.hero": [LINE, LEDE]},
            "metadata": {
                "title_contains": LINE,
                "description_contains": "independent, data-driven record",
            },
        },
        "empty": {"markers": [{"id": "home.empty", "min": 1}]},
    },
}


def manifest() -> dict:
    return {
        "version": 1,
        "identity": copy.deepcopy(IDENTITY),
        "site": copy.deepcopy(SITE),
        "surfaces": [copy.deepcopy(SURFACE)],
    }


def page_html(
    *,
    state: str = "full",
    standings_marker: str = 'data-contract="home.standings"',
    standings_wrapper: tuple[str, str] = ("", ""),
    extra_head: str = "",
    extra_body: str = "",
    h2: str = "<h2>Current standings</h2>",
    omit_unknown: bool = False,
    omit_freshness: bool = False,
    omit_footer_copy: bool = False,
    link: str = "/matchday/",
) -> str:
    unknown = "" if omit_unknown else '<span data-contract-indicator="unknown">unknown</span>'
    freshness = "" if omit_freshness else '<span data-contract-indicator="freshness">fresh</span>'
    footer_copy = "" if omit_footer_copy else "Not affiliated with Aberdeen FC"
    before, after = standings_wrapper
    return f"""<!doctype html>
<html>
<head>
  <title>fitba — {LINE}</title>
  <meta name="description" content="An independent, data-driven record of Aberdeen FC.">
  {extra_head}
</head>
<body>
<header data-contract="site.header"><span>{LINE}</span></header>
<div data-contract-page="home" data-contract-state="{state}">
  <section data-contract="home.hero">
    <h1>{LINE}</h1>
    <p>{LEDE}</p>
  </section>
  <section {standings_marker}>
    {before}
    <table>
      <thead><tr>
        <th>#</th><th>Club</th><th>P</th><th>W</th><th>D</th><th>L</th>
        <th>GF</th><th>GA</th><th>GD</th><th>Pts</th>
      </tr></thead>
      <tbody><tr>
        <td>1</td><td>Aberdeen</td><td>10</td><td>5</td><td>2</td><td>3</td>
        <td>15</td><td>10</td><td>5</td><td>17</td>
      </tr></tbody>
    </table>
    {after}
    {h2}
  </section>
  {unknown}
  {freshness}
  <a href="{link}">Matchday</a>
  {extra_body}
</div>
<footer data-contract="site.footer"><span>{LINE} {footer_copy}</span></footer>
<a href="/methodology/">Method</a>
</body>
</html>"""


def check(html: str, document: dict | None = None, *, ci: bool = True, base: str = ""):
    data = document or manifest()
    return CONTRACT.check_document(
        html,
        data["surfaces"][0],
        data["identity"],
        data["site"],
        base,
        ci,
    )


def messages(issues) -> str:
    return "\n".join(issue.message for issue in issues)


def test_valid_page_passes():
    assert check(page_html()) == []


def test_missing_marker_fails():
    issues = check(page_html(standings_marker=""))
    assert "missing required marker 'home.standings'" in messages(issues)


def test_marker_in_closed_details_fails():
    issues = check(page_html(standings_wrapper=("<details>", "</details>")))
    assert "closed <details>" in messages(issues)


def test_marker_in_open_details_passes():
    issues = check(page_html(standings_wrapper=("<details open>", "</details>")))
    assert issues == []


def test_interrogative_heading_fails():
    issues = check(page_html(h2="<h2>Who starts?</h2>"))
    assert "interrogative heading" in messages(issues)


def test_declarative_heading_passes():
    issues = check(page_html(h2="<h2>How the styles meet</h2>"))
    assert issues == []


def test_heading_level_jump_fails():
    issues = check(page_html(h2="<h3>Current standings</h3>"))
    assert "heading level jumps" in messages(issues)


def test_banned_heading_without_question_mark_fails():
    issues = check(page_html(h2="<h2>Who starts</h2>"))
    assert "banned fan-first heading" in messages(issues)


def test_banned_phrase_fails():
    issues = check(page_html(extra_body="<p>The Scottish pyramid, from Pittodrie out.</p>"))
    assert "banned identity phrase" in messages(issues)


def test_banned_phrase_in_script_is_ignored():
    issues = check(page_html(extra_body="<script>const copy = 'The Scottish pyramid';</script>"))
    assert issues == []


def test_missing_column_fails():
    html = page_html().replace("<th>Pts</th>", "")
    issues = check(html)
    assert "missing required columns" in messages(issues)


def test_extra_column_passes():
    html = page_html().replace("<th>Pts</th>", "<th>Pts</th><th>Form</th>")
    assert check(html) == []


def test_blank_table_values_fail():
    html = re.sub(r"<td>[^<]*</td>", "<td>—</td>", page_html())
    issues = check(html)
    assert "contain no values" in messages(issues)


def test_reordered_columns_fail():
    html = page_html().replace("<th>P</th><th>W</th>", "<th>W</th><th>P</th>")
    issues = check(html)
    assert "missing required columns" in messages(issues)


def test_missing_indicator_fails():
    issues = check(page_html(omit_unknown=True))
    assert "indicator 'unknown'" in messages(issues)


def test_missing_freshness_fails():
    issues = check(page_html(omit_freshness=True))
    assert "indicator 'freshness'" in messages(issues)


def test_missing_site_copy_fails():
    issues = check(page_html(omit_footer_copy=True))
    assert "site marker 'site.footer'" in messages(issues)


def test_missing_required_link_fails():
    issues = check(page_html(link="/squad/"))
    assert "missing required link '/matchday/'" in messages(issues)


def test_base_path_is_normalised():
    html = page_html(link="/fitba/matchday/").replace(
        "</head>", '<script src="/fitba/_next/static/chunks/app.js"></script></head>'
    )
    assert check(html, manifest(), base="/fitba") == []
    assert CONTRACT.detect_base_path_from_html(html) == "/fitba"


def test_ci_rejects_disallowed_empty_state():
    html = page_html(state="empty").replace(
        '<section data-contract="home.hero">', '<section data-contract="home.empty">'
    )
    issues = check(html, ci=True)
    assert "not allowed in CI" in messages(issues)
    assert check(html, ci=False) == []


def test_word_budget_is_rejected():
    document = manifest()
    document["surfaces"][0]["states"]["full"]["max_words"] = 350
    with pytest.raises(CONTRACT.ManifestError, match="word-count budgets are prohibited"):
        CONTRACT.validate_manifest(document)


def test_unknown_manifest_key_is_rejected():
    document = manifest()
    document["surfaces"][0]["states"]["full"]["word_budget"] = 100
    with pytest.raises(CONTRACT.ManifestError):
        CONTRACT.validate_manifest(document)


def test_malformed_marker_is_rejected():
    document = manifest()
    document["surfaces"][0]["states"]["full"]["markers"][0]["id"] = "Home"
    with pytest.raises(CONTRACT.ManifestError, match="malformed"):
        CONTRACT.validate_manifest(document)


def test_declared_count_must_match_rendered_cards():
    document = manifest()
    state = document["surfaces"][0]["states"]["full"]
    state["markers"].append({"id": "home.cards", "min": 1})
    state["markers"].append({"id": "home.card", "min": 1})
    html = page_html(
        extra_body=(
            '<div data-contract="home.cards" data-contract-count="2" '
            'data-contract-count-of="home.card">'
            '<article data-contract="home.card">one</article></div>'
        )
    )
    issues = check(html, document)
    assert "page declares 2" in messages(issues)


def test_same_as_requires_every_card():
    document = manifest()
    full = document["surfaces"][0]["states"]["full"]
    full["markers"].append({"id": "home.card", "min": 1})
    full["markers"].append({"id": "home.card.fee", "same_as": "home.card"})
    html = page_html(
        extra_body=(
            '<article data-contract="home.card">'
            '<span data-contract="home.card.fee">£1m</span></article>'
            '<article data-contract="home.card"><span>no fee</span></article>'
        )
    )
    issues = check(html, document)
    assert "expected 2 (one per 'home.card'), found 1" in messages(issues)
