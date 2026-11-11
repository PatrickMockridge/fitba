from __future__ import annotations

from fitba.analytics.manager_market import extract_manager_mentions, manager_vacancy
from fitba.sources import donstalk

BOARD_HTML = """
<ul>
  <li data-ips-hook="topicRow" class="ipsData__item" data-rowid="9479">
    <h4><a href="https://www.donstalk.co.uk/topic/9479-next-manager/">Next manager</a></h4>
    <time datetime="2026-11-11T12:20:22Z"></time>
  </li>
  <li data-ips-hook="topicRow" class="ipsData__item" data-rowid="10901">
    <h4><a href="https://www.donstalk.co.uk/topic/10901-january-2027-transfer-window/">
      January 2027 Transfer Window
    </a></h4>
    <time datetime="2026-09-01T16:04:47Z"></time>
  </li>
</ul>
"""

TOPIC_HTML = """
<div data-ipsPagination-pages="86" data-pages="86"></div>
<article class="ipsEntry ipsEntry--first-simple ipsEntry--post" id="elComment_241253">
  <time datetime="2022-02-13T10:49:12Z"></time>
  <div data-role="commentContent">Right, thoughts? My money is on the Fergie statue.</div>
</article>
<article class="ipsEntry ipsEntry--post" id="elComment_293817">
  <time datetime="2026-11-10T17:21:48Z"></time>
  <div data-role="commentContent">
    Couple of names: Michael Wimmer and Karel Geraerts.
    <blockquote>Quoted text should disappear.</blockquote>
  </div>
</article>
"""


def test_parse_board_reads_invision_topic_rows() -> None:
    rows = donstalk.parse_board(BOARD_HTML)
    assert rows == [
        {
            "topic_id": "9479",
            "title": "Next manager",
            "url": "https://www.donstalk.co.uk/topic/9479-next-manager/",
            "latest_post": "2026-11-11T12:20:22Z",
        },
        {
            "topic_id": "10901",
            "title": "January 2027 Transfer Window",
            "url": "https://www.donstalk.co.uk/topic/10901-january-2027-transfer-window/",
            "latest_post": "2026-09-01T16:04:47Z",
        },
    ]


def test_parse_page_count() -> None:
    assert donstalk.parse_page_count(TOPIC_HTML) == 86
    assert donstalk.parse_page_count("<html></html>") is None


def test_parse_topic_excludes_the_2022_opening_post_and_quotes() -> None:
    posts = donstalk.parse_topic(TOPIC_HTML)
    assert len(posts) == 1
    assert posts[0]["comment_id"] == "293817"
    assert posts[0]["posted_at"] == "2026-11-10T17:21:48Z"
    text = str(posts[0]["text"])
    assert "Michael Wimmer" in text
    assert "Quoted text" not in text
    assert "username" not in posts[0]


def test_manager_mentions_are_full_name_only() -> None:
    candidates = [
        {"candidate_id": "alex-neil", "name": "Alex Neil", "aliases": []},
        {"candidate_id": "neil-lennon", "name": "Neil Lennon", "aliases": []},
        {"candidate_id": "scott-brown", "name": "Scott Brown", "aliases": []},
    ]
    counts = extract_manager_mentions(
        "Alex Neil and Neil Lennon are mentioned; Lennon is not enough; Brown neither.",
        candidates,
    )
    assert counts == {"alex-neil": 1, "neil-lennon": 1}


def _staff(current_role: str, *, interim: bool, start: str = "2026-11-09") -> dict:
    return {
        "people": [
            {
                "person_id": "test-person",
                "name": "Test Person",
                "stints": [
                    {
                        "stint_id": "test-stint",
                        "role": current_role,
                        "role_group": "manager",
                        "start": start,
                        "end": None,
                        "interim": interim,
                    }
                ],
            }
        ]
    }


def test_vacancy_gate_open_for_interim_only() -> None:
    gate = manager_vacancy(_staff("Interim manager", interim=True))
    assert gate["is_open"] is True
    assert gate["interim_manager"] == "Test Person"
    assert gate["state"] == "open"


def test_vacancy_gate_closed_for_permanent_manager() -> None:
    gate = manager_vacancy(_staff("Manager", interim=False))
    assert gate["is_open"] is False
    assert gate["permanent_manager"] == "Test Person"
    assert gate["state"] == "closed"
