"""One percentile vocabulary for the published record.

A percentile is a rank of a value within a stated population. The platform
uses one definition for every displayed percentile: the midrank of the value,
including the value itself in the population, on a 0-100 scale. The population
and the minutes gate must be published beside the number.

Distribution quantiles (for example the 25th percentile of a set of ratings)
are a different statistic. They use :func:`nearest_rank_quantile` and are
labelled as quantiles (``p25``), not as percentile ranks.
"""

from __future__ import annotations

from collections.abc import Iterable


def midrank_percentile(
    value: float | None,
    values: Iterable[float | None],
    *,
    decimals: int = 1,
) -> float | None:
    """Midrank percentile, 0-100, with the value included in the population.

    Ties take the midpoint. The maximum of a finite sample is below 100 because
    the value itself occupies half a position. An empty sample, or a non-finite
    value, returns ``None`` rather than a made-up number.
    """
    if value is None:
        return None
    items = [float(item) for item in values if item is not None]
    if not items:
        return None
    below = sum(1 for item in items if item < value)
    equal = sum(1 for item in items if item == value)
    return round((below + 0.5 * equal) / len(items) * 100.0, decimals)


def nearest_rank_quantile(
    values: Iterable[float | None],
    share: float,
    *,
    decimals: int = 2,
) -> float | None:
    """Nearest-rank quantile of a distribution (not a percentile rank)."""
    items = sorted(float(item) for item in values if item is not None)
    if not items:
        return None
    index = max(0, min(len(items) - 1, round((len(items) - 1) * share)))
    return round(items[index], decimals)


__all__ = ["midrank_percentile", "nearest_rank_quantile"]
