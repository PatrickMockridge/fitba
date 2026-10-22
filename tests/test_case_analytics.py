from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from fitba.ingest.match_data import (
    load_player_appearances,
    load_player_match_stats,
    load_team_shapes,
)
from fitba.ingest.runner import load_matches
from fitba.publish.case import build_case_payload

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data" / "generated"
BANNED = ("role family", "provider rating", "inferred", "80/20", "leaky boat", "not a verdict")


@pytest.fixture(scope="module")
def payload() -> dict:
    all_matches = load_matches(None)
    season = "2026-27"
    return build_case_payload(
        season=season,
        generated_at="2026-10-22T00:00:00+00:00",
        matches=all_matches.filter(pl.col("season") == season),
        all_matches=all_matches,
        squad_data=json.loads((DATA / "squad" / "aberdeen.json").read_text()),
        transfers_data=json.loads((DATA / "transfers" / "aberdeen.json").read_text()),
        history_index=json.loads((DATA / "history" / "aberdeen.json").read_text()),
        history_season=json.loads(
            (DATA / "history" / "seasons" / "2026-27.json").read_text()
        ),
        history_seasons={
            path.stem: json.loads(path.read_text())
            for path in (DATA / "history" / "seasons").glob("*.json")
        },
        availability=json.loads((DATA / "availability" / "aberdeen.json").read_text()),
        appearances=load_player_appearances(),
        match_stats=load_player_match_stats(),
        team_shapes=load_team_shapes(),
    )


def _claim(payload: dict, claim_id: str) -> dict:
    return next(item for item in payload["claims"] if item["id"] == claim_id)


def test_six_claims_and_three_domains(payload) -> None:
    assert len(payload["claims"]) == 6
    assert {item["domain"] for item in payload["claims"]} == {
        "matchday",
        "off_pitch",
        "chairman",
    }


def test_every_claim_has_the_unit(payload) -> None:
    for claim in payload["claims"]:
        assert claim["claim"]
        assert claim["count"]
        assert claim["status"] in {"supported", "mixed", "not_supported", "cant_test"}
        assert claim["status_reason"]
        assert claim["evidence"]
        assert claim["better_data"]
        assert claim["change_mind"]
        assert claim["links"]


def test_team_now_uses_plain_record(payload) -> None:
    claim = _claim(payload, "team_now")
    text = " ".join(item["count"] for item in claim["evidence"])
    assert "3 wins, 2 draws and 4 defeats" in text
    assert "15 competitive fixtures" in text
    assert "2 unknown" in text


def test_defence_is_plain_and_availability_unknown(payload) -> None:
    claim = _claim(payload, "defence")
    text = " ".join(
        [claim["count"], claim["status_reason"]]
        + [f"{item['metric']} {item['count']}" for item in claim["evidence"]]
    )
    assert "three-centre-back" in text
    assert "0 known / 38 unknown" in text
    assert "Tobers is not in the current squad" in text
    assert "CB" not in text


def test_managers_use_seven_wins_not_record(payload) -> None:
    claim = _claim(payload, "managers")
    text = " ".join(
        [claim["claim"], claim["status_reason"]]
        + [f"{item['metric']} {item['count']} {item['note'] or ''}" for item in claim["evidence"]]
    )
    assert "7 straight league wins" in text
    assert "8-match run in 2014-15" in text
    assert "not a verdict" not in text


def test_squad_is_turnover_not_youth(payload) -> None:
    claim = _claim(payload, "squad")
    text = " ".join(
        [claim["claim"], claim["count"], claim["status_reason"]]
        + [item["count"] for item in claim["evidence"]]
    )
    assert "15 arrivals and 25 departures" in text
    assert "median 26" in text
    assert "8%" in text
    assert "2025-09-01" in text


def test_chairman_record_and_benchmark(payload) -> None:
    claim = _claim(payload, "chairman_record")
    text = " ".join([claim["count"]] + [item["count"] for item in claim["evidence"]])
    assert "7 seasons" in text
    assert "3rd to 10th" in text
    assert "1 Scottish Cup" in text
    assert "2" in text  # European campaigns
    benchmark = payload["benchmark"]
    assert benchmark["rows"]
    assert any(row["Club"] == "Aberdeen" for row in benchmark["rows"])
    assert "transfer" in benchmark["note"]


def test_no_banned_jargon_in_reader_strings(payload) -> None:
    for claim in payload["claims"]:
        text = " ".join(
            [claim["title"], claim["claim"], claim["count"], claim["status_reason"]]
            + [item["metric"] for item in claim["evidence"]]
        ).casefold()
        for phrase in BANNED:
            assert phrase not in text, (claim["id"], phrase)
