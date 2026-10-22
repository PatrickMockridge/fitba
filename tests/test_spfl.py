from pathlib import Path

from fitba.publish.publish import _stage_for
from fitba.sources.spfl import parse_html

FIXTURE = Path(__file__).parent / "fixtures" / "spfl_aberdeen.html"


def test_parse_spfl_results_and_cup_fixture():
    frame = parse_html(FIXTURE.read_text(encoding="utf-8"))
    assert frame.height == 2

    result = frame.filter(frame["status"] == "played").row(0, named=True)
    assert result["competition_id"] == "sco:premiership"
    assert str(result["date"]) == "2026-10-17"
    assert (result["home_team_raw"], result["away_team_raw"]) == ("Aberdeen", "St. Mirren")
    assert (result["home_goals"], result["away_goals"]) == (3, 1)

    cup = frame.filter(frame["status"] == "scheduled").row(0, named=True)
    assert cup["competition_id"] == "sco:league-cup"
    assert str(cup["date"]) == "2026-10-31"
    assert cup["kickoff"] == "17:30"
    assert (cup["home_team_raw"], cup["away_team_raw"]) == ("Rangers", "Aberdeen")


def test_stage_window_labels_the_league_cup_semi_final():
    from datetime import date

    assert _stage_for("sco:league-cup", date(2026, 10, 31)) == "Semi-final"
    assert _stage_for("sco:league-cup", date(2026, 12, 13)) == "Final"
    assert _stage_for("sco:premiership", date(2026, 10, 31)) is None
