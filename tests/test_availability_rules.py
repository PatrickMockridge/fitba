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
    assert happe["status"] == "review_required"
    assert happe["next_fixture"]["date"] == "2026-10-31"
    mayo = next(item for item in suspensions if item["player_id"] == 125695)
    assert mayo["status"] in {"watch", "review_required", "projected"}
    assert mayo["threshold"] == 6
