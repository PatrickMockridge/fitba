from datetime import date

import pytest

from fitba.util.dates import (
    current_season,
    previous_season,
    season_bounds,
    season_code,
    season_from_date,
    seasons_between,
    validate_season,
)


def test_season_code():
    assert season_code("2026-27") == "2627"
    assert season_code("1994-95") == "9495"


def test_season_from_date():
    assert season_from_date(date(2026, 10, 21)) == "2026-27"
    assert season_from_date(date(2026, 5, 31)) == "2025-26"
    assert season_from_date(date(2026, 7, 1)) == "2026-27"


def test_current_season():
    assert current_season(date(2026, 10, 21)) == "2026-27"


def test_bounds_and_previous():
    assert season_bounds("2026-27") == (date(2026, 7, 1), date(2027, 6, 30))
    assert previous_season("2026-27") == "2025-26"


def test_seasons_between():
    assert seasons_between("2013-14", "2016-17") == [
        "2013-14",
        "2014-15",
        "2015-16",
        "2016-17",
    ]


@pytest.mark.parametrize("bad", ["2026", "2026-28", "26-27", ""])
def test_validate_season_rejects_bad_values(bad):
    with pytest.raises(ValueError):
        validate_season(bad)
