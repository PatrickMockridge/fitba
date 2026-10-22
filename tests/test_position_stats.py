from fitba.ingest.position_stats import (
    compute_position_stats,
    goal_events,
    on_pitch_intervals,
)

TEAM_ID = 252


def _lineup(*player_ids: int) -> dict:
    return {
        "team": {"id": TEAM_ID, "name": "Aberdeen"},
        "startXI": [{"player": {"id": player_id}} for player_id in player_ids],
    }


def _event(
    *,
    minute: int,
    event_type: str,
    detail: str,
    team_id: int = TEAM_ID,
    player_id: int | None = None,
    assist_id: int | None = None,
) -> dict:
    return {
        "time": {"elapsed": minute, "extra": None},
        "team": {"id": team_id},
        "player": {"id": player_id},
        "assist": {"id": assist_id},
        "type": event_type,
        "detail": detail,
    }


def test_on_pitch_intervals_substitution_and_red_card():
    lineup = _lineup(1, 2, 3)
    events = [
        _event(minute=60, event_type="subst", detail="Substitution 1", player_id=1, assist_id=4),
        _event(minute=70, event_type="Card", detail="Red Card", player_id=2),
    ]
    intervals = on_pitch_intervals(
        lineup,
        events,
        team_id=TEAM_ID,
        match_length=90,
    )
    assert intervals == {1: (0, 60), 2: (0, 70), 3: (0, 90), 4: (60, 90)}


def test_on_pitch_intervals_extra_time():
    lineup = _lineup(1)
    intervals = on_pitch_intervals(
        lineup,
        [],
        team_id=TEAM_ID,
        match_length=120,
    )
    assert intervals == {1: (0, 120)}


def test_goal_events_normal_and_own_goal_attribution():
    events = [
        _event(minute=30, event_type="Goal", detail="Normal Goal", team_id=999, player_id=99),
        _event(minute=40, event_type="Goal", detail="Normal Goal", team_id=TEAM_ID, player_id=1),
        _event(minute=50, event_type="Goal", detail="Own Goal", team_id=999, player_id=98),
        _event(minute=60, event_type="Goal", detail="Own Goal", team_id=999, player_id=1),
    ]
    conceded, own_goals = goal_events(events, team_id=TEAM_ID, squad_ids={1, 2})
    assert conceded == [30, 60]
    assert own_goals == {1: 1}


def _context(*, match_length: int = 90, events=None) -> dict:
    return {
        "fixture": {
            "fixture": {
                "id": 1,
                "date": "2026-08-01",
                "status": {"short": "FT", "elapsed": match_length},
            },
            "league": {"name": "Premiership"},
            "teams": {"home": {"id": TEAM_ID}, "away": {"id": 999}},
            "goals": {"home": 0, "away": 1},
        },
        "lineups": [_lineup(1, 2)],
        "events": events
        if events is not None
        else [
            _event(minute=30, event_type="Goal", detail="Normal Goal", team_id=999, player_id=99),
        ],
    }


def test_compute_position_stats_on_pitch_conceded_and_clean_sheet():
    rows, meta = compute_position_stats(
        [_context()],
        team_id=TEAM_ID,
        squad_ids={1, 2},
        ingested_at="2026-10-21T00:00:00Z",
    )
    assert meta["coverage"] == "available"
    by_player = {row["player_id"]: row for row in rows}
    assert by_player[1]["conceded_on_pitch"] == 1
    assert by_player[1]["clean_sheets"] == 0
    assert by_player[2]["minutes_on_pitch"] == 90


def test_compute_position_stats_clean_sheet_minimum_minutes():
    events = []  # 0-0
    rows, _ = compute_position_stats(
        [_context(events=events)],
        team_id=TEAM_ID,
        squad_ids={1, 2},
        ingested_at="2026-10-21T00:00:00Z",
    )
    by_player = {row["player_id"]: row for row in rows}
    assert by_player[1]["clean_sheets"] == 1
    assert by_player[2]["clean_sheets"] == 1


def test_compute_position_stats_partial_coverage():
    context = _context()
    context["lineups"] = []
    rows, meta = compute_position_stats(
        [context],
        team_id=TEAM_ID,
        squad_ids={1, 2},
        ingested_at="2026-10-21T00:00:00Z",
    )
    assert rows == []
    assert meta["coverage"] == "unavailable"
    assert meta["fixtures_total"] == 1
    assert meta["fixtures_covered"] == 0
    assert meta["missing_fixtures"]
