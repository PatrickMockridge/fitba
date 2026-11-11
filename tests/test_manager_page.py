from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

from fitba.metrics.audit import load_corpus
from fitba.metrics.consistency import run_consistency

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "web" / "data" / "generated"
SPEC = importlib.util.spec_from_file_location(
    "check_manager", ROOT / "scripts" / "check_manager.py"
)
assert SPEC is not None and SPEC.loader is not None
CHECK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECK
SPEC.loader.exec_module(CHECK)


def _corpus() -> dict:
    return load_corpus(GENERATED)


def test_published_corpus_passes_manager_records():
    results = run_consistency(_corpus())
    check = next(result for result in results if result.id == "manager.records")
    assert check.status == "pass", check.errors


def test_published_payload_passes_manager_guard():
    errors, state = CHECK._payload_errors()
    assert errors == []
    assert state["season"] == "2026-27"


def test_current_manager_state_is_unambiguous():
    errors, state = CHECK._payload_errors()
    assert errors == []
    assert len(state["permanent"]) <= 1
    assert len(state["interim"]) <= 1


def test_market_gate_mutation_fails_consistency():
    corpus = copy.deepcopy(_corpus())
    gate = corpus["rumours/manager-market.json"]["market"]["gate"]
    gate["interim_manager"] = "Not the interim"
    results = run_consistency(corpus)
    failed = {result.id for result in results if result.status != "pass"}
    assert "manager.records" in failed


def test_market_gate_mutation_fails_payload_guard(monkeypatch, tmp_path):
    market = json.loads(CHECK.MARKET.read_text(encoding="utf-8"))
    market["market"]["gate"]["interim_manager"] = "Not the interim"
    mutated = tmp_path / "manager-market.json"
    mutated.write_text(json.dumps(market), encoding="utf-8")
    monkeypatch.setattr(CHECK, "MARKET", mutated)
    errors, _ = CHECK._payload_errors()
    assert any("interim manager" in error for error in errors)


def test_season_segment_mutation_fails_payload_guard(monkeypatch):
    season = "2026-27"
    document = json.loads((CHECK.SEASON_DIR / f"{season}.json").read_text(encoding="utf-8"))
    document["managers"][0]["played"] = int(document["managers"][0]["played"]) + 1
    original_load = CHECK._load

    def fake_load(path: Path):
        if path.name == f"{season}.json":
            return document
        return original_load(path)

    monkeypatch.setattr(CHECK, "_load", fake_load)
    errors, _ = CHECK._payload_errors()
    assert any("played" in error for error in errors)
