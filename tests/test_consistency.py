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
        row for row in corpus["xg/aberdeen.json"]["aggregates"] if row.get("scope") == "season"
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


def test_table_played_mutation_fails():
    corpus = copy.deepcopy(_corpus())
    table = corpus["tables/premiership-2026-27.json"]
    row = next(row for row in table["rows"] if row["team_id"] == "sco:aberdeen")
    row["played"] += 1
    results = run_consistency(corpus)
    failed = {result.id for result in results if result.status != "pass"}
    assert "results.table" in failed


def test_analysis_league_rank_mutation_fails():
    corpus = copy.deepcopy(_corpus())
    ranking = corpus["analysis/summary.json"]["league_rankings"]
    ranking["aberdeen"]["ranks"]["xg_for_pm"] += 1
    results = run_consistency(corpus)
    failed = {result.id for result in results if result.status != "pass"}
    assert "analysis.league-rankings" in failed


def test_analysis_league_goal_mutation_fails():
    corpus = copy.deepcopy(_corpus())
    table = corpus["tables/premiership-2026-27.json"]
    row = next(row for row in table["rows"] if row["team_id"] == "sco:aberdeen")
    row["gf"] += 1
    results = run_consistency(corpus)
    failed = {result.id for result in results if result.status != "pass"}
    assert "analysis.league-rankings" in failed


def test_matchday_form_mutation_fails():
    corpus = copy.deepcopy(_corpus())
    form = corpus["matchday/upcoming.json"]["form_guide"]["aberdeen"]
    form["form"] = "X" + form["form"][1:]
    results = run_consistency(corpus)
    failed = {result.id for result in results if result.status != "pass"}
    assert "results.form" in failed


def test_club_result_mutation_fails():
    corpus = copy.deepcopy(_corpus())
    results_rows = corpus["clubs/aberdeen.json"]["results"]
    results_rows[0]["goals_against"] = int(results_rows[0]["goals_against"] or 0) + 1
    results = run_consistency(corpus)
    failed = {result.id for result in results if result.status != "pass"}
    assert "results.club" in failed


def test_coverage_matches_mutation_fails():
    corpus = copy.deepcopy(_corpus())
    row = next(
        row for row in corpus["coverage.json"]["competitions"] if row["id"] == "sco:premiership"
    )
    row["matches"] += 1
    results = run_consistency(corpus)
    failed = {result.id for result in results if result.status != "pass"}
    assert "results.coverage" in failed


def test_manager_gate_mutation_fails():
    corpus = copy.deepcopy(_corpus())
    gate = corpus["rumours/manager-market.json"]["market"]["gate"]
    gate["is_open"] = not gate["is_open"]
    results = run_consistency(corpus)
    failed = {result.id for result in results if result.status != "pass"}
    assert "manager.records" in failed


def test_manager_segment_mutation_fails():
    corpus = copy.deepcopy(_corpus())
    season = corpus["analysis/summary.json"]["season"]
    manager = corpus[f"history/seasons/{season}.json"]["managers"][0]
    manager["played"] = int(manager["played"]) + 1
    results = run_consistency(corpus)
    failed = {result.id for result in results if result.status != "pass"}
    assert "manager.records" in failed


def test_history_finance_year_mutation_fails():
    corpus = copy.deepcopy(_corpus())
    corpus["history/aberdeen.json"]["finances"]["rows"][0]["season"] = "2019-20"
    results = run_consistency(corpus)
    failed = {result.id for result in results if result.status != "pass"}
    assert "history.finances" in failed


def test_epoch_mismatch_fails():
    corpus = copy.deepcopy(_corpus())
    corpus["squad/aberdeen.json"]["dataset_id"] = "not-the-current-dataset"
    results = run_consistency(corpus)
    failed = {result.id for result in results if result.status != "pass"}
    assert "rules.epoch" in failed


def test_stale_payload_is_allowed_with_a_reason():
    corpus = copy.deepcopy(_corpus())
    corpus["squad/aberdeen.json"]["dataset_state"] = "stale"
    corpus["squad/aberdeen.json"]["dataset_id"] = "older-dataset"
    corpus["squad/aberdeen.json"]["stale_reason"] = "test_carry_forward"
    results = run_consistency(corpus)
    epoch = next(result for result in results if result.id == "rules.epoch")
    assert epoch.status == "pass"
