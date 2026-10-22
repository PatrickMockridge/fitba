from fitba.ingest.cups import _normalise
from fitba.normalize.teams import TeamRegistry
from fitba.settings import cups as cups_config


def _item(fixture_id, date, league_round, home, away, home_goals, away_goals, pens=None):
    score = {
        "fulltime": {"home": home_goals, "away": away_goals},
        "penalty": pens or {"home": None, "away": None},
        "extratime": {"home": None, "away": None},
    }
    return {
        "fixture": {
            "id": fixture_id,
            "date": date,
            "status": {"short": "PEN" if pens else "FT"},
            "venue": {"name": "Test Park"},
        },
        "league": {"id": 185, "season": 2026, "round": league_round},
        "teams": {
            "home": {"name": home, "winner": bool(pens)},
            "away": {"name": away, "winner": False},
        },
        "goals": {"home": home_goals, "away": away_goals},
        "score": score,
    }


def test_normalise_league_cup_shootout():
    cup = next(item for item in cups_config()["cups"] if item["id"] == "sco:league-cup")
    row = _normalise(
        _item(
            1,
            "2026-07-11T14:00:00+00:00",
            "Group Stage",
            "Aberdeen",
            "Celtic",
            1,
            1,
            {"home": 4, "away": 3},
        ),
        cup,
        TeamRegistry(),
    )
    assert row["competition_id"] == "sco:league-cup"
    assert row["round"] == "Group Stage"
    assert row["status"] == "played"
    assert row["home_team_id"] == "sco:aberdeen"
    assert row["away_team_id"] == "sco:celtic"
    assert (row["home_penalties"], row["away_penalties"]) == (4, 3)
    assert row["extra_time"] is True
    assert row["winner_team_id"] == "sco:aberdeen"
    assert row["season"] == "2026-27"


def test_scottish_cup_round_is_mapped_from_date_window():
    cup = next(item for item in cups_config()["cups"] if item["id"] == "sco:scottish-cup")
    row = _normalise(
        _item(
            2,
            "2026-10-24T14:00:00+00:00",
            "Round of 128",
            "Clyde",
            "Penicuik Athletic",
            0,
            0,
        ),
        cup,
        TeamRegistry(),
    )
    assert row["round"] == "Second Round"
    assert row["round_order"] == 5
    assert row["api_round"] == "Round of 128"
