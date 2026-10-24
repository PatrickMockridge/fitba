"""Tests for the result-aware post-match refresh gate."""

from __future__ import annotations

from datetime import UTC, date, datetime

import polars as pl

from fitba.update import refresh_due


def _schedule(*rows: dict) -> dict:
    return {"scheduled": list(rows)}


def _fixture(
    *,
    date_value: str = "2026-10-24",
    home: str = "sco:dundee-united",
    away: str = "sco:aberdeen",
) -> dict:
    return {
        "date": date_value,
        "kickoff": "15:00",
        "status": "scheduled",
        "home_team_id": home,
        "away_team_id": away,
    }


def _canonical(*rows: tuple[str, str, str]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "date": [date.fromisoformat(row[0]) for row in rows],
            "home_team_id": [row[1] for row in rows],
            "away_team_id": [row[2] for row in rows],
            "home_goals": [3 for _ in rows],
            "away_goals": [2 for _ in rows],
        }
    )


def test_due_when_a_finished_fixture_has_no_canonical_result() -> None:
    schedule = _schedule(_fixture())
    manifest = {"generated_at": "2026-10-24T19:00:00+00:00"}
    # A newer manifest does not make a missing result current.
    assert refresh_due(
        now=datetime(2026, 10, 24, 20, 0, tzinfo=UTC),
        fixtures_index=schedule,
        manifest=manifest,
        canonical_matches=_canonical(),
    )


def test_not_due_when_the_canonical_frame_has_the_result() -> None:
    schedule = _schedule(_fixture())
    manifest = {"generated_at": "2026-10-24T18:30:00+00:00"}
    assert not refresh_due(
        now=datetime(2026, 10, 24, 20, 0, tzinfo=UTC),
        fixtures_index=schedule,
        manifest=manifest,
        canonical_matches=_canonical(("2026-10-24", "sco:dundee-united", "sco:aberdeen")),
    )


def test_not_due_when_only_the_published_index_has_the_result() -> None:
    published = {
        "scheduled": [_fixture()],
        "fixtures": [
            {
                "date": "2026-10-24",
                "home_team_id": "sco:dundee-united",
                "away_team_id": "sco:aberdeen",
                "home_goals": 3,
                "away_goals": 2,
            }
        ],
    }
    assert not refresh_due(
        now=datetime(2026, 10, 24, 20, 0, tzinfo=UTC),
        fixtures_index=published,
        manifest={"generated_at": "2026-10-24T18:30:00+00:00"},
        canonical_matches=_canonical(),
    )


def test_no_refresh_before_the_finish_buffer() -> None:
    schedule = _schedule(_fixture())
    assert not refresh_due(
        now=datetime(2026, 10, 24, 16, 0, tzinfo=UTC),
        fixtures_index=schedule,
        manifest={"generated_at": "2026-10-24T10:00:00+00:00"},
        canonical_matches=_canonical(),
    )


def test_refresh_uses_winter_time() -> None:
    schedule = _schedule(_fixture(date_value="2026-12-05"))
    assert refresh_due(
        now=datetime(2026, 12, 5, 19, 0, tzinfo=UTC),
        fixtures_index=schedule,
        manifest={"generated_at": "2026-12-05T10:00:00+00:00"},
        canonical_matches=_canonical(),
    )


def test_no_refresh_for_a_future_fixture() -> None:
    schedule = _schedule(_fixture(date_value="2026-11-07"))
    assert not refresh_due(
        now=datetime(2026, 10, 24, 20, 0, tzinfo=UTC),
        fixtures_index=schedule,
        manifest={"generated_at": "2026-10-24T10:00:00+00:00"},
        canonical_matches=_canonical(),
    )


def test_no_refresh_without_a_kickoff_or_a_schedule() -> None:
    now = datetime(2026, 10, 24, 20, 0, tzinfo=UTC)
    row = _fixture()
    row["kickoff"] = None
    assert not refresh_due(
        now=now,
        fixtures_index=_schedule(row),
        manifest={"generated_at": "2026-10-24T10:00:00+00:00"},
        canonical_matches=_canonical(),
    )
    assert not refresh_due(
        now=now,
        fixtures_index={},
        manifest={"generated_at": "2026-10-24T10:00:00+00:00"},
        canonical_matches=_canonical(),
    )
