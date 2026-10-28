from datetime import date

import pytest

from fitba.normalize.schedule import load_schedule
from fitba.settings import NORMALIZED_DIR

pytestmark = pytest.mark.skipif(
    not (
        (NORMALIZED_DIR / "history" / "season=2026-27" / "fixtures.parquet").exists()
        and (NORMALIZED_DIR / "club_fixtures" / "aberdeen.parquet").exists()
    ),
    reason="requires the local normalized history and club-fixture feeds",
)


def test_schedule_uses_local_kickoff_and_marks_conflicts():
    rows = load_schedule("2026-27", today=date(2026, 10, 23))
    by_date = [row for row in rows if row["date"] == "2026-10-31"]
    assert by_date
    cup = next(row for row in by_date if row["competition_id"] == "sco:league-cup")
    assert cup["conflict_review"] is False
    assert cup["neutral"] is True
    assert cup["venue"] == "Hampden Park"
    assert cup["kickoff"] == "17:30"
    conflicts = [row for row in by_date if row["status"] == "conflict_review"]
    assert all(row["conflict_review"] for row in conflicts)


def test_schedule_converts_utc_to_london_across_dst():
    rows = load_schedule("2026-27", today=date(2026, 10, 23))
    october = next(row for row in rows if row["date"] == "2026-10-24")
    assert october["kickoff"] == "15:00"
    assert october["kickoff_tz"] == "Europe/London"
    assert october["kickoff_status"] == "provisional"


def test_schedule_excludes_played_rows_from_lookahead_and_marks_overdue():
    rows = load_schedule("2026-27", today=date(2026, 10, 23))
    scheduled = [row for row in rows if row["status"] == "scheduled"]
    assert scheduled
    assert all(row["date"] >= "2026-10-23" for row in scheduled)
    assert all(row["fixture_id"] is not None for row in scheduled)
