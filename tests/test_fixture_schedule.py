from datetime import date

from fitba.normalize.schedule import load_schedule


def test_schedule_uses_local_kickoff_and_keeps_31_october_conflict():
    rows = load_schedule("2026-27", today=date(2026, 10, 23))
    by_date = [row for row in rows if row["date"] == "2026-10-31"]
    assert len(by_date) == 2
    league = next(row for row in by_date if row["competition_id"] == "sco:premiership")
    cup = next(row for row in by_date if row["competition_id"] == "sco:league-cup")
    assert league["conflict_review"] is True
    assert league["status"] == "conflict_review"
    assert cup["conflict_review"] is False
    assert cup["neutral"] is True
    assert cup["venue"] == "Hampden Park"
    assert cup["kickoff"] == "17:30"


def test_schedule_converts_utc_to_london_across_dst():
    rows = load_schedule("2026-27", today=date(2026, 10, 23))
    october = next(row for row in rows if row["date"] == "2026-10-24")
    assert october["kickoff"] == "15:00"
    assert october["kickoff_tz"] == "Europe/London"
    assert october["kickoff_status"] == "confirmed"


def test_schedule_excludes_played_rows_from_lookahead_and_marks_overdue():
    rows = load_schedule("2026-27", today=date(2026, 10, 23))
    scheduled = [row for row in rows if row["status"] == "scheduled"]
    assert scheduled
    assert all(row["date"] >= "2026-10-23" for row in scheduled)
    assert all(row["fixture_id"] is not None for row in scheduled)
