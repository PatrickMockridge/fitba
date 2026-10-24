from __future__ import annotations

import math

from fitba.analytics.xg_uncertainty import (
    aggregate_goal_range,
    beta_binomial_pmf,
    binomial_pmf,
    goal_pmf,
    goal_range,
    quantile_from_pmf,
)


def test_binomial_pmf_sums_to_one() -> None:
    for n, p in ((0, 0.0), (1, 0.5), (12, 0.11), (30, 1.0)):
        assert math.isclose(sum(binomial_pmf(n, p)), 1.0, abs_tol=1e-12)


def test_beta_binomial_widens_the_tail() -> None:
    plain = binomial_pmf(20, 0.1)
    wide = beta_binomial_pmf(20, 0.1, 2.0)
    assert sum(wide) == 1.0
    assert wide[-1] > plain[-1]


def test_goal_range_orders_and_penalty_component() -> None:
    low, high = goal_range(
        open_xg=1.2,
        open_shots=12,
        penalties=1,
        penalty_xg=0.76,
        dispersion=1.0,
    )
    assert 0 <= low <= high
    pmf = goal_pmf(
        open_xg=1.2,
        open_shots=12,
        penalties=1,
        penalty_xg=0.76,
    )
    assert math.isclose(sum(pmf), 1.0, abs_tol=1e-9)
    assert quantile_from_pmf(pmf, 0.1) == low
    assert quantile_from_pmf(pmf, 0.9) == high


def test_aggregate_range_is_not_a_linear_sum() -> None:
    row = {"open_xg": 1.2, "open_shots": 12, "penalties": 0}
    one_low, one_high = aggregate_goal_range([row], penalty_xg=0.76)
    four_low, four_high = aggregate_goal_range([row] * 4, penalty_xg=0.76)
    assert four_high - four_low < 4 * (one_high - one_low)
