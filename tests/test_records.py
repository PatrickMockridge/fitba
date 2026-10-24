from __future__ import annotations

from fitba.analytics.records import match_result


def test_regulation_result_has_no_shootout():
    result = match_result(2, 1)
    assert result["result"] == "W"
    assert result["outcome"] == "W"
    assert result["decided_by"] == "regulation"
    assert result["shootout_result"] is None


def test_shootout_preserves_draw_and_reports_outcome():
    result = match_result(1, 1, shootout_for=4, shootout_against=3)
    assert result["result"] == "D"
    assert result["outcome"] == "W"
    assert result["shootout_result"] == "won"
    assert result["result_label"] == "D (won 4-3 pens)"


def test_shootout_loss_is_not_a_draw_outcome():
    result = match_result(2, 2, shootout_for=3, shootout_against=5)
    assert result["result"] == "D"
    assert result["outcome"] == "L"
    assert result["shootout_result"] == "lost"


def test_regulation_win_with_shootout_is_possible():
    result = match_result(2, 1, shootout_for=None, shootout_against=None)
    assert result["outcome"] == "W"
    assert result["decided_by"] == "regulation"
