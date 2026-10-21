from pathlib import Path

from fitba.sources.football_data_uk import parse_csv

FIXTURE = Path(__file__).parent / "fixtures" / "sc0_sample.csv"


def test_parse_scottish_csv_handles_bom_and_dates():
    frame = parse_csv(FIXTURE, "2025-26")
    assert frame.height == 4
    assert frame.columns[:5] == ["division", "date", "kickoff", "home_team_raw", "away_team_raw"]
    assert frame["division"].to_list() == ["SC0"] * 4
    assert str(frame["date"][0]) == "2025-08-02"
    assert frame["home_goals"].to_list() == [1, 0, 3, 1]
    assert frame["away_goals"].to_list() == [2, 0, 1, 2]
    assert frame["result"].to_list() == ["A", "D", "H", "A"]
    assert frame["home_shots"].to_list() == [10, 14, 15, 8]
    assert frame["season"].to_list() == ["2025-26"] * 4


def test_parse_handles_two_digit_years_and_drops_blank_rows(tmp_path):
    path = tmp_path / "old.csv"
    path.write_text(
        "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\nSC0,02/08/13,Aberdeen,Celtic,0,0,D\n,,,,,,\n"
    )
    frame = parse_csv(path, "2013-14")
    assert frame.height == 1
    assert str(frame["date"][0]) == "2013-08-02"


def test_parse_keeps_optional_columns_null_when_absent(tmp_path):
    path = tmp_path / "minimal.csv"
    path.write_text(
        "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\nSC0,02/08/2025,Aberdeen,Celtic,0,0,D\n"
    )
    frame = parse_csv(path, "2025-26")
    assert frame.height == 1
    assert frame["home_shots"][0] is None
    assert frame["referee"][0] is None
