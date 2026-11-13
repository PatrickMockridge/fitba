from __future__ import annotations

from copy import deepcopy

from fitba.metrics.checks import verify_history_finances
from fitba.publish.history import build_finances_payload
from fitba.settings import history_finances
from fitba.validate.history import validate_finances

SEASONS = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]


def test_reference_finances_validate() -> None:
    errors = validate_finances(history_finances(), reference=True)
    assert errors == []


def test_builder_publishes_five_rows_without_verification_inputs() -> None:
    payload = build_finances_payload()
    assert [row["season"] for row in payload["rows"]] == SEASONS
    for row in payload["rows"]:
        assert "total_borrowings" not in row
        assert "cash" not in row
        assert row["fy"].startswith("FY")
    assert validate_finances(payload) == []


def test_net_registration_investment_is_accounting_basis() -> None:
    payload = build_finances_payload()
    values = [row["net_registration_investment"] for row in payload["rows"]]
    assert values == [None, -1.06, -7.03, 0.59, -2.54]

    document = deepcopy(history_finances())
    document["rows"][1]["net_registration_investment"] = 4.0
    errors = validate_finances(document, reference=True)
    assert any("net_registration_investment does not reconcile" in error for error in errors)


def test_missing_years_are_absent_and_listed() -> None:
    payload = build_finances_payload()
    seasons = {row["season"] for row in payload["rows"]}
    assert "2019-20" not in seasons
    assert "2025-26" not in seasons
    assert payload["coverage"]["missing_seasons"] == ["2019-20", "2025-26"]


def test_one_decimal_field_rejects_extra_precision() -> None:
    document = deepcopy(history_finances())
    document["rows"][0]["revenue"] = 11.15
    errors = validate_finances(document, reference=True)
    assert any("revenue exceeds 1dp" in error for error in errors)


def test_net_debt_allows_two_decimals() -> None:
    document = deepcopy(history_finances())
    document["rows"][0]["net_debt"] = 1.291
    errors = validate_finances(document, reference=True)
    assert any("net_debt exceeds 2dp" in error for error in errors)


def test_net_debt_must_reconcile_in_reference_mode() -> None:
    document = deepcopy(history_finances())
    document["rows"][0]["net_debt"] = 9.99
    errors = validate_finances(document, reference=True)
    assert any("net_debt does not reconcile" in error for error in errors)


def test_verifier_rejects_a_changed_value() -> None:
    payload = build_finances_payload()
    corpus = {"history/aberdeen.json": {"finances": payload}}
    assert verify_history_finances(corpus).status == "pass"

    broken = deepcopy(corpus)
    broken["history/aberdeen.json"]["finances"]["rows"][0]["revenue"] = 99.9
    result = verify_history_finances(broken)
    assert result.status == "fail"
    assert any("revenue does not match reference" in error for error in result.errors)


def test_verifier_rejects_incomplete_missing_year_coverage() -> None:
    payload = build_finances_payload()
    payload["coverage"]["missing_seasons"] = ["2019-20"]
    result = verify_history_finances({"history/aberdeen.json": {"finances": payload}})
    assert result.status == "fail"
    assert any("missing-year coverage" in error for error in result.errors)
