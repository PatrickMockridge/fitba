from __future__ import annotations

from fitba.sources.afc_official import parse_html

HTML = """
<html><body>
<h2>Goalkeepers</h2>
<div data-component="ProfileCard">
  <a href="/en/teams/mens/marius-mueller">
    <span class="profileCard_position__x">Goalkeeper</span>
    <span class="profileCard_squadNumber__x">27</span>
    <span class="profileCard_firstName__x">Marius</span>
    <span class="profileCard_surname__x">Müller</span>
  </a>
</div>
<h2>On loan</h2>
<div data-component="ProfileCard">
  <a href="/en/teams/mens/kenan-bilalovic">
    <span class="profileCard_position__x">Forward</span>
    <span class="profileCard_firstName__x">Kenan</span>
    <span class="profileCard_surname__x">Bilalovic</span>
  </a>
</div>
<h2>Staff</h2>
<div data-component="ProfileCard">
  <a href="/en/teams/mens/stephen-robinson">
    <span class="profileCard_firstName__x">Stephen</span>
    <span class="profileCard_surname__x">Robinson</span>
  </a>
</div>
</body></html>
"""


def test_parse_sections_exclude_staff_and_keep_loan_section() -> None:
    players = parse_html(HTML)
    assert [player["name"] for player in players] == ["Marius Müller", "Kenan Bilalovic"]
    assert players[0]["number"] == 27
    assert players[0]["section"] == "Goalkeepers"
    assert players[0]["official_order"] == 0
    assert players[1]["official_order"] == 1
    assert players[1]["section"] == "On loan"
    assert players[1]["number"] is None
    assert all("robinson" not in player["href"] for player in players)
