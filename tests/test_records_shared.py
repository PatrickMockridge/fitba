from __future__ import annotations

from fitba.analytics.history import _record
from fitba.analytics.matchday import record
from fitba.analytics.records import record_totals

ROWS = [
    {"date": "2026-08-01", "result": "W", "gf": 2, "ga": 1, "points": 3},
    {"date": "2026-08-08", "result": "D", "gf": 1, "ga": 1, "points": 1},
    {"date": "2026-08-15", "result": "L", "gf": 0, "ga": 2, "points": 0},
]


def test_record_totals_arithmetic() -> None:
    totals = record_totals(ROWS)
    assert totals == {
        "played": 3,
        "won": 1,
        "drawn": 1,
        "lost": 1,
        "gf": 3,
        "ga": 4,
        "gd": -1,
        "points": 4,
        "ppg": 1.33,
    }


def test_matchday_and_history_agree() -> None:
    matchday = record(ROWS)
    history = _record(ROWS)
    for key in ("played", "won", "drawn", "lost", "gf", "ga", "points", "ppg"):
        assert matchday[key] == history[key]


def test_empty_record() -> None:
    assert record_totals([])["ppg"] is None
    assert _record([])["first_match"] is None
