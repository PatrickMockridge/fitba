import pytest

from fitba.analytics.availability_rules import card_summary, suspension_rows
from fitba.normalize.schedule import load_schedule
from fitba.settings import NORMALIZED_DIR

pytestmark = pytest.mark.skipif(
    not (
        (NORMALIZED_DIR / "history" / "season=2026-27" / "fixtures.parquet").exists()
        and (NORMALIZED_DIR / "history" / "season=2026-27" / "events.parquet").exists()
        and (NORMALIZED_DIR / "club_fixtures" / "aberdeen.parquet").exists()
    ),
    reason="requires the local normalized history, event and club-fixture feeds",
)


def test_second_yellow_is_recovered_and_scoped_to_the_cup():
    cards = card_summary("2026-27")
    row = cards["players"]["18068:sco:league-cup"]
    assert row["reds"] == 1
    assert row["red_type"] == "second_yellow"
    suspensions = suspension_rows("2026-27", cards)
    happe = next(item for item in suspensions if item["player_id"] == 18068)
    assert happe["competition_id"] == "sco:league-cup"
    assert happe["status"] == "review_required"
    # The next fixture is the earliest scheduled cup tie after the card, not
    # the next league match. It is None once the cup run has no fixture left;
    # do not pin the assertion to a date that the data will overtake.
    upcoming = [
        row
        for row in load_schedule("2026-27")
        if row.get("competition_id") == "sco:league-cup"
        and row.get("status") == "scheduled"
        and not row.get("conflict_review")
        and str(row.get("date") or "") > str(happe["last_card_date"])
    ]
    expected = min(upcoming, key=lambda row: str(row.get("date") or "")) if upcoming else None
    if expected is None:
        assert happe["next_fixture"] is None
    else:
        assert happe["next_fixture"]["fixture_id"] == expected["fixture_id"]
        assert happe["next_fixture"]["date"] == expected["date"]
    mayo = next(item for item in suspensions if item["player_id"] == 125695)
    assert mayo["status"] in {"watch", "review_required", "projected"}
    assert mayo["threshold"] == 6
