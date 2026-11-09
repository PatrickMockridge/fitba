import pytest

from fitba.analytics.availability_rules import card_summary, suspension_rows
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
    # The second yellow is a one-match, same-competition ban. Happe was absent
    # from the 2026-10-31 League Cup semi-final, so the ban is served; it was
    # never a league suspension.
    assert happe["status"] == "served"
    assert happe["suspension_state"] == "served"
    assert happe["served_fixture_id"] == 1639572
    assert happe["served_date"] == "2026-10-31"
    assert happe["ban_matches"] == 1
    assert happe["rule_verified"] is False
    assert happe["next_fixture"] is None
    mayo = next(item for item in suspensions if item["player_id"] == 125695)
    assert mayo["status"] in {"watch", "review_required", "projected"}
    assert mayo["threshold"] == 6
