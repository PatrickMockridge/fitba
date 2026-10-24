from __future__ import annotations

import copy
from pathlib import Path

from fitba.metrics.audit import load_corpus
from fitba.metrics.consistency import run_consistency

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "web" / "data" / "generated"


def _corpus() -> dict:
    return load_corpus(GENERATED)


def test_published_corpus_is_consistent():
    results = run_consistency(_corpus())
    failures = [result for result in results if result.status != "pass"]
    assert not failures, failures


def test_loan_count_mutation_fails():
    corpus = copy.deepcopy(_corpus())
    corpus["squad/aberdeen.json"]["summary"]["loans_out"] += 1
    results = run_consistency(corpus)
    failed = {result.id for result in results if result.status != "pass"}
    assert "squad.counts" in failed


def test_player_minutes_mutation_fails():
    corpus = copy.deepcopy(_corpus())
    page = next(
        value
        for key, value in corpus.items()
        if key.startswith("players/") and key.endswith(".json")
    )
    summary = page["panels"]["profile"]["data"]["summary"]
    summary["minutes"] = int(summary["minutes"] or 0) + 1
    results = run_consistency(corpus)
    failed = {result.id for result in results if result.status != "pass"}
    assert "players.pages" in failed


def test_xg_aggregate_mutation_fails():
    corpus = copy.deepcopy(_corpus())
    aggregate = next(
        row
        for row in corpus["xg/aberdeen.json"]["aggregates"]
        if row.get("scope") == "season"
    )
    aggregate["shots"] = int(aggregate["shots"] or 0) + 1
    results = run_consistency(corpus)
    failed = {result.id for result in results if result.status != "pass"}
    assert "xg.aggregates" in failed


def test_scheduled_count_mutation_fails():
    corpus = copy.deepcopy(_corpus())
    corpus["fixtures/index.json"]["scheduled_count"] += 1
    results = run_consistency(corpus)
    failed = {result.id for result in results if result.status != "pass"}
    assert "fixtures.schedule" in failed
