from pathlib import Path

from fitba.sources.afc import parse_html

FIXTURE = Path(__file__).parent / "fixtures" / "afc_news.html"


def test_parse_news_cards_and_deduplicate():
    frame = parse_html(FIXTURE.read_text(encoding="utf-8"))
    assert frame.height == 2
    rows = {row["article_id"]: row for row in frame.to_dicts()}

    article = rows["three-goal-dons-down-saints"]
    assert article["title"] == "Three Goal Dons Down Saints"
    assert article["category"] == "News"
    assert str(article["published_date"]) == "2026-10-17"
    assert article["url"] == "https://www.afc.co.uk/en/news/three-goal-dons-down-saints"

    women = rows["aberdeen-women-0-celtic-6-report-and-reaction"]
    assert women["category"] == "Women's Team"
    assert str(women["published_date"]) == "2026-10-18"
