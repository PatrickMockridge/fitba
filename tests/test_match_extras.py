from __future__ import annotations

from fitba.ingest.match_extras import normalize_events, normalize_lineups
from fitba.ingest.team_stats import parse_team_stats


def test_normalize_events_classifies_goals_cards_and_var() -> None:
    payload = [
        {
            "time": {"elapsed": 12, "extra": None},
            "team": {"id": 252, "name": "Aberdeen"},
            "player": {"id": 1, "name": "A. Scorer"},
            "assist": {"id": 2, "name": "B. Creator"},
            "type": "Goal",
            "detail": "Normal Goal",
            "comments": None,
        },
        {
            "time": {"elapsed": 44, "extra": None},
            "team": {"id": 1386, "name": "Dundee United"},
            "player": {"id": 3, "name": "C. Defender"},
            "assist": {"id": None, "name": None},
            "type": "Goal",
            "detail": "Own Goal",
            "comments": None,
        },
        {
            "time": {"elapsed": 55, "extra": None},
            "team": {"id": 252, "name": "Aberdeen"},
            "player": {"id": 4, "name": "D. Penalty"},
            "assist": {"id": None, "name": None},
            "type": "Goal",
            "detail": "Penalty",
            "comments": None,
        },
        {
            "time": {"elapsed": 61, "extra": None},
            "team": {"id": 1386, "name": "Dundee United"},
            "player": {"id": 5, "name": "E. Booked"},
            "assist": {"id": None, "name": None},
            "type": "Card",
            "detail": "Second Yellow card",
            "comments": None,
        },
        {
            "time": {"elapsed": 78, "extra": None},
            "team": {"id": 252, "name": "Aberdeen"},
            "player": {"id": None, "name": None},
            "assist": {"id": None, "name": None},
            "type": "Var",
            "detail": "Goal cancelled",
            "comments": None,
        },
        {
            "time": {"elapsed": 90, "extra": 4},
            "team": {"id": 252, "name": "Aberdeen"},
            "player": {"id": 6, "name": "F. Late"},
            "assist": {"id": None, "name": None},
            "type": "Goal",
            "detail": "Normal Goal",
            "comments": "Penalty Shootout",
        },
    ]
    rows = normalize_events(payload, fixture_id=1, season="2025-26", ingested_at="now")

    assert len(rows) == 6
    assert rows[0]["is_goal"] is True
    assert rows[0]["is_own_goal"] is False
    assert rows[0]["assist_name"] == "B. Creator"
    assert rows[1]["is_own_goal"] is True
    assert rows[2]["is_penalty"] is True
    assert rows[3]["is_red_card"] is True
    assert rows[3]["is_second_yellow"] is True
    assert rows[4]["is_var"] is True
    assert rows[5]["is_goal"] is True
    assert rows[5]["is_shootout"] is True
    assert rows[5]["extra_minute"] == 4


def test_normalize_events_infers_second_yellow_after_two_yellows() -> None:
    payload = [
        {
            "time": {"elapsed": 31},
            "team": {"id": 252, "name": "Aberdeen"},
            "player": {"id": 7, "name": "D. Happe"},
            "type": "Card",
            "detail": "Yellow Card",
        },
        {
            "time": {"elapsed": 58},
            "team": {"id": 252, "name": "Aberdeen"},
            "player": {"id": 7, "name": "D. Happe"},
            "type": "Card",
            "detail": "Yellow Card",
        },
        {
            "time": {"elapsed": 58},
            "team": {"id": 252, "name": "Aberdeen"},
            "player": {"id": 7, "name": "D. Happe"},
            "type": "Card",
            "detail": "Red Card",
        },
    ]
    rows = normalize_events(payload, fixture_id=1629022, season="2026-27", ingested_at="now")
    assert [row["event_order"] for row in rows] == [0, 1, 2]
    assert rows[2]["is_red_card"] is True
    assert rows[2]["is_second_yellow"] is True


def test_normalize_events_keeps_straight_red_after_one_yellow() -> None:
    payload = [
        {
            "time": {"elapsed": 31},
            "team": {"id": 252, "name": "Aberdeen"},
            "player": {"id": 7, "name": "D. Happe"},
            "type": "Card",
            "detail": "Yellow Card",
        },
        {
            "time": {"elapsed": 58},
            "team": {"id": 252, "name": "Aberdeen"},
            "player": {"id": 7, "name": "D. Happe"},
            "type": "Card",
            "detail": "Red Card",
        },
    ]
    rows = normalize_events(payload, fixture_id=2, season="2026-27", ingested_at="now")
    assert rows[1]["is_red_card"] is True
    assert rows[1]["is_second_yellow"] is False


def test_normalize_events_drops_missed_penalty_from_goals() -> None:
    payload = [
        {
            "time": {"elapsed": 20},
            "team": {"id": 252, "name": "Aberdeen"},
            "player": {"id": 1, "name": "A. Taker"},
            "type": "Goal",
            "detail": "Missed Penalty",
            "comments": None,
        }
    ]
    rows = normalize_events(payload, fixture_id=1, season="2025-26", ingested_at="now")
    assert rows[0]["is_goal"] is False
    assert rows[0]["is_penalty"] is False


def test_normalize_lineups_keeps_coach_and_formation() -> None:
    payload = [
        {
            "team": {"id": 252, "name": "Aberdeen"},
            "formation": "4-2-3-1",
            "coach": {"id": 9, "name": "The Manager"},
        }
    ]
    rows = normalize_lineups(payload, fixture_id=1, season="2025-26", ingested_at="now")
    assert rows == [
        {
            "fixture_id": 1,
            "season": "2025-26",
            "team_id": 252,
            "team_name": "Aberdeen",
            "formation": "4-2-3-1",
            "coach_id": 9,
            "coach_name": "The Manager",
            "ingested_at": "now",
        }
    ]


def test_parse_team_stats_keeps_shot_locations_and_xg() -> None:
    payload = [
        {
            "team": {"id": 252, "name": "Aberdeen"},
            "statistics": [
                {"type": "Ball Possession", "value": "55%"},
                {"type": "Total Shots", "value": 14},
                {"type": "Shots on Goal", "value": 6},
                {"type": "Shots off Goal", "value": 5},
                {"type": "Blocked Shots", "value": 3},
                {"type": "Shots insidebox", "value": 9},
                {"type": "Shots outsidebox", "value": 5},
                {"type": "expected_goals", "value": "1.43"},
                {"type": "goals_prevented", "value": "0.32"},
                {"type": "Total passes", "value": 500},
                {"type": "Passes accurate", "value": 410},
                {"type": "Passes %", "value": "82%"},
                {"type": "Corner Kicks", "value": 7},
                {"type": "Fouls", "value": 11},
                {"type": "Offsides", "value": 2},
                {"type": "Yellow Cards", "value": 1},
                {"type": "Red Cards", "value": None},
                {"type": "Goalkeeper Saves", "value": 3},
            ],
        }
    ]
    rows = parse_team_stats(payload, fixture_id=1)
    assert rows[0]["shots"] == 14
    assert rows[0]["shots_on_target"] == 6
    assert rows[0]["shots_off"] == 5
    assert rows[0]["shots_blocked"] == 3
    assert rows[0]["shots_insidebox"] == 9
    assert rows[0]["expected_goals"] == 1.43
    assert rows[0]["goals_prevented"] == 0.32
    assert rows[0]["passes_pct"] == 82.0
    assert rows[0]["red_cards"] is None
