"""Standard-library goal distributions for the fxG model.

The model is team-level, not shot-level. A binomial (or beta-binomial when the
observed dispersion is above one) is therefore an approximation to the
Poisson-binomial distribution of the shots behind a team's xG. It is deliberately
conservative: heterogeneous shot quality narrows the true variance.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping

MAX_SUPPORT = 5000
MAX_DISPERSION = 3.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def binomial_pmf(n: int, p: float) -> list[float]:
    if n <= 0:
        return [1.0]
    p = _clamp(float(p), 0.0, 1.0)
    if p <= 0.0:
        return [1.0] + [0.0] * n
    if p >= 1.0:
        return [0.0] * n + [1.0]
    return [
        math.comb(n, k) * (p**k) * ((1.0 - p) ** (n - k))
        for k in range(n + 1)
    ]


def beta_binomial_pmf(n: int, p: float, dispersion: float) -> list[float]:
    """Beta-binomial with the same mean and inflated variance.

    ``dispersion`` is the quasi-binomial scale: 1 is binomial, values above 1
    widen the distribution. The intra-class correlation is derived from the
    target variance and capped so the beta parameters stay positive.
    """
    if n <= 0:
        return [1.0]
    p = _clamp(float(p), 0.0, 1.0)
    phi = _clamp(float(dispersion), 1.0, MAX_DISPERSION)
    if phi <= 1.0 or n == 1:
        return binomial_pmf(n, p)
    rho = min(0.98, (phi - 1.0) / (n - 1.0))
    if rho <= 0.0:
        return binomial_pmf(n, p)
    concentration = (1.0 / rho) - 1.0
    alpha = max(1e-9, p * concentration)
    beta = max(1e-9, (1.0 - p) * concentration)
    log_norm = (
        math.lgamma(n + 1)
        - math.lgamma(alpha + beta)
        + math.lgamma(alpha)
        + math.lgamma(beta)
    )
    log_norm -= math.lgamma(n + alpha + beta)
    values = [
        math.exp(
            log_norm
            + math.lgamma(k + alpha)
            + math.lgamma(n - k + beta)
            - math.lgamma(k + 1)
            - math.lgamma(n - k + 1)
        )
        for k in range(n + 1)
    ]
    total = sum(values)
    return [value / total for value in values] if total else binomial_pmf(n, p)


def convolve_pmfs(
    left: list[float],
    right: list[float],
    *,
    max_support: int = MAX_SUPPORT,
) -> list[float]:
    size = min(max_support, len(left) + len(right) - 1)
    output = [0.0] * size
    for i, left_value in enumerate(left):
        if left_value == 0.0 or i >= size:
            continue
        limit = min(len(right), size - i)
        for j in range(limit):
            output[i + j] += left_value * right[j]
    return output


def convolve_many(
    pmfs: Iterable[list[float]],
    *,
    max_support: int = MAX_SUPPORT,
) -> list[float]:
    output = [1.0]
    for pmf in pmfs:
        output = convolve_pmfs(output, pmf, max_support=max_support)
        if len(output) >= max_support:
            break
    return output


def quantile_from_pmf(pmf: list[float], probability: float) -> int:
    if not pmf:
        return 0
    target = _clamp(probability, 0.0, 1.0)
    cumulative = 0.0
    for index, value in enumerate(pmf):
        cumulative += value
        if cumulative >= target:
            return index
    return len(pmf) - 1


def goal_pmf(
    *,
    open_xg: float,
    open_shots: int | None,
    penalties: int | None,
    penalty_xg: float,
    dispersion: float = 1.0,
) -> list[float]:
    """Distribution of goals from the same chances.

    The open-play component uses one average chance quality. Penalties are a
    separate binomial component. Both are convolved exactly.
    """
    open_n = max(0, int(open_shots or 0))
    open_mu = max(0.0, float(open_xg or 0.0))
    open_p = _clamp(open_mu / open_n, 0.0, 1.0) if open_n else 0.0
    open_pmf = beta_binomial_pmf(open_n, open_p, dispersion)
    pen_n = max(0, int(penalties or 0))
    pen_pmf = beta_binomial_pmf(pen_n, penalty_xg, dispersion) if pen_n else [1.0]
    return convolve_pmfs(open_pmf, pen_pmf)


def goal_range(
    *,
    open_xg: float,
    open_shots: int | None,
    penalties: int | None,
    penalty_xg: float,
    dispersion: float = 1.0,
    level: float = 0.80,
) -> tuple[int, int]:
    pmf = goal_pmf(
        open_xg=open_xg,
        open_shots=open_shots,
        penalties=penalties,
        penalty_xg=penalty_xg,
        dispersion=dispersion,
    )
    alpha = (1.0 - level) / 2.0
    return (
        quantile_from_pmf(pmf, alpha),
        quantile_from_pmf(pmf, 1.0 - alpha),
    )


def aggregate_goal_range(
    rows: Iterable[Mapping[str, float | int | None]],
    *,
    penalty_xg: float,
    dispersion: float = 1.0,
    level: float = 0.80,
    max_support: int = MAX_SUPPORT,
) -> tuple[int, int]:
    pmfs = [
        goal_pmf(
            open_xg=float(row.get("open_xg") or 0.0),
            open_shots=int(row.get("open_shots") or 0),
            penalties=int(row.get("penalties") or 0),
            penalty_xg=penalty_xg,
            dispersion=dispersion,
        )
        for row in rows
    ]
    pmf = convolve_many(pmfs, max_support=max_support)
    alpha = (1.0 - level) / 2.0
    return (
        quantile_from_pmf(pmf, alpha),
        quantile_from_pmf(pmf, 1.0 - alpha),
    )


__all__ = [
    "MAX_DISPERSION",
    "MAX_SUPPORT",
    "aggregate_goal_range",
    "beta_binomial_pmf",
    "binomial_pmf",
    "convolve_many",
    "convolve_pmfs",
    "goal_pmf",
    "goal_range",
    "quantile_from_pmf",
]
