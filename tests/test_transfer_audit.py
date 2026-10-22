from fitba.ingest import transfers
from fitba.normalize.transfer_audit import build_transfer_audit, classify_seniority
from fitba.sources import api_football

CONFIG = {
    "audit": {
        "start_season": "2024-25",
        "recent_windows": 4,
        "seniority": {
            "established_min_starts": 5,
            "established_min_minutes": 450,
            "established_min_career_starts": 10,
            "youth_max_age": 20,
            "youth_max_appearances": 4,
        },
    }
}


def _player(**overrides):
    player = {
        "player_id": 1,
        "player_key": "api:player:1",
        "name": "Current Player",
        "age": 27,
        "number": 9,
        "playing_time": {"starts": 10, "sub_apps": 0, "minutes": 900},
        "career_role": {"starts_with_role": 20},
    }
    player.update(overrides)
    return player


def _prior(player_id=2, **overrides):
    row = {
        "player_id": player_id,
        "player_name": f"Prior {player_id}",
        "season": "2025-26",
        "team_id": 252,
        "appearances": 10,
        "starts": 10,
        "minutes": 900,
        "position": "Defender",
        "age": 27,
        "snapshot_at": "2026-10-21T00:00:00Z",
    }
    row.update(overrides)
    return row


def test_seniority_tiers():
    assert classify_seniority(_player(), CONFIG) == "established"
    assert (
        classify_seniority(
            _player(
                age=24,
                number=30,
                playing_time={"starts": 0, "sub_apps": 0, "minutes": 0},
                career_role={},
            ),
            CONFIG,
        )
        == "fringe"
    )
    assert (
        classify_seniority(
            _player(
                age=17,
                number=53,
                playing_time={"starts": 0, "sub_apps": 2, "minutes": 19},
                career_role={},
            ),
            CONFIG,
        )
        == "youth"
    )
    assert (
        classify_seniority(
            _player(
                age=25,
                number=None,
                playing_time={"starts": 0, "sub_apps": 0, "minutes": 0},
                career_role={},
            ),
            CONFIG,
        )
        == "unclassified"
    )
    assert (
        classify_seniority({}, CONFIG, prior=_prior(starts=6, appearances=6, minutes=540))
        == "established"
    )
    assert (
        classify_seniority({}, CONFIG, prior=_prior(starts=2, appearances=2, minutes=120))
        == "fringe"
    )
    assert (
        classify_seniority(
            {},
            CONFIG,
            prior=_prior(age=19, starts=2, appearances=2, minutes=120),
        )
        == "youth"
    )


def test_audit_marks_arrival_and_departure_needs_review():
    audit = build_transfer_audit(
        players=[_player()],
        prior_seasons=[_prior()],
        transfers=[],
        candidates=[],
        gaps=[],
        config=CONFIG,
        generated_at="2026-10-21T00:00:00Z",
    )
    assert audit["status"] == "ok"
    assert audit["current_squad_arrivals"][0]["player_key"] == "api:player:1"
    assert audit["current_squad_arrivals"][0]["seniority"] == "established"
    assert audit["prior_departures"][0]["player_key"] == "api:player:2"


def test_audit_accepts_gap_and_registered_move():
    gaps = [
        {
            "player_key": "api:player:1",
            "direction": "in",
            "status": "accepted",
            "seniority": "youth",
            "reason": "academy graduate",
        }
    ]
    transfers = [
        {
            "player_key": "api:player:2",
            "direction": "out",
            "season": "2025-26",
            "window": "summer",
            "position": "Defender",
        }
    ]
    audit = build_transfer_audit(
        players=[_player()],
        prior_seasons=[_prior()],
        transfers=transfers,
        candidates=[],
        gaps=gaps,
        config=CONFIG,
        generated_at="2026-10-21T00:00:00Z",
    )
    assert not audit["current_squad_arrivals"]
    assert not audit["prior_departures"]


def test_audit_ignores_loan_returns_and_queues_candidates():
    transfers = [
        {
            "player_key": "api:player:2",
            "direction": "in",
            "transfer_kind": "loan",
            "season": "2024-25",
            "window": "winter",
            "position": "Defender",
        }
    ]
    candidates = [
        {
            "transfer_id": "afc:one",
            "player_key": "api:player:9",
            "direction": "in",
            "season": "2026-27",
            "window": "summer",
            "verification_status": "feed_only",
        }
    ]
    audit = build_transfer_audit(
        players=[],
        prior_seasons=[_prior()],
        transfers=transfers,
        candidates=candidates,
        gaps=[],
        config=CONFIG,
        generated_at="2026-10-21T00:00:00Z",
    )
    assert not audit["prior_departures"]
    assert audit["candidate_review"] == [
        {"key": "2026-27-summer", "season": "2026-27", "window": "summer", "count": 1}
    ]


def test_audit_unavailable_without_snapshot():
    audit = build_transfer_audit(
        players=[_player()],
        prior_seasons=[],
        transfers=[],
        candidates=[],
        gaps=[],
        config=CONFIG,
        generated_at="2026-10-21T00:00:00Z",
    )
    assert audit["status"] == "unavailable"
    assert audit["summary"]["needs_review"]["established"] == 0


def test_position_precedence(monkeypatch):
    monkeypatch.setattr(
        transfers,
        "_load_curated_positions",
        lambda: {
            "api:player:1": {
                "position": "Midfielder",
                "source_urls": ["x"],
                "verified_at": "y",
            }
        },
    )
    monkeypatch.setattr(transfers, "_load_career_positions", lambda: {"api:player:4": "Attacker"})
    monkeypatch.setattr(
        transfers,
        "_profiles",
        lambda needs: ({(3, 2026): {"position": "Defender", "season": "2025-26"}}, False),
    )
    rows = [
        {
            "player_key": "api:player:1",
            "season": "2026-27",
            "position": "Defender",
            "position_source": "squad",
        },
        {
            "player_key": "api:player:2",
            "season": "2026-27",
            "position": "Goalkeeper",
            "position_source": "squad",
        },
        {"player_key": "api:player:3", "season": "2026-27", "position": None},
        {"player_key": "api:player:4", "season": "2026-27", "position": None},
        {"player_key": "api:player:5", "season": "2026-27", "position": None},
    ]
    transfers.resolve_positions(rows)
    assert (rows[0]["position"], rows[0]["position_source"]) == ("Midfielder", "curated")
    assert (rows[1]["position"], rows[1]["position_source"]) == ("Goalkeeper", "squad")
    assert (rows[2]["position"], rows[2]["position_source"], rows[2]["position_source_season"]) == (
        "Defender",
        "api_player_stats",
        "2025-26",
    )
    assert (rows[3]["position"], rows[3]["position_source"]) == ("Attacker", "career_role")
    assert (
        rows[4]["position"],
        rows[4]["position_source"],
        rows[4]["position_unknown_reason"],
    ) == (
        None,
        "unknown",
        "no_allowed_source",
    )


def test_players_by_team_follows_bounded_pagination(monkeypatch):
    calls = []

    def fake_request(path, **params):
        calls.append(params["page"])
        rows = [{"player": {"id": params["page"]}}]
        return {"response": rows, "paging": {"total": 2}}

    monkeypatch.setattr(api_football, "request_payload", fake_request)
    rows = api_football.players_by_team(252, 2025, max_pages=2)
    assert len(rows) == 2
    assert calls == [1, 2]
