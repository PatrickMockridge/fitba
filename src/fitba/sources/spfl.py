"""SPFL official club fixtures/results adapter.

The SPFL club page is server-rendered and includes recent results and upcoming
fixtures across the league and the Premier Sports Cup. It is the consistent,
updating source for those two competitions. The Scottish Cup is run by the SFA
and is modelled from the SFA format page until fixtures are published.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import ClassVar

import polars as pl
from bs4 import BeautifulSoup

from fitba.ingest.cache import cache_path, fetch
from fitba.normalize.names import slugify
from fitba.sources.base import Capability, IngestResult, Lane
from fitba.util.dates import season_from_date, utc_now_iso

COMPETITION_MAP: dict[str, tuple[str, str]] = {
    "William Hill Premiership": ("sco:premiership", "William Hill Premiership"),
    "Premier Sports Cup": ("sco:league-cup", "Premier Sports Cup"),
    "Scottish Gas Men's Scottish Cup": ("sco:scottish-cup", "Scottish Gas Men's Scottish Cup"),
    "Scottish Cup": ("sco:scottish-cup", "Scottish Gas Men's Scottish Cup"),
}

FIXTURE_COLUMNS = [
    "match_id",
    "competition_id",
    "competition_name",
    "season",
    "date",
    "kickoff",
    "home_team_raw",
    "away_team_raw",
    "home_goals",
    "away_goals",
    "status",
    "source_id",
    "ingested_at",
]


def club_url(club_slug: str) -> str:
    return f"https://spfl.co.uk/clubs/{club_slug}/fixtures"


def download(club_slug: str = "aberdeen", *, force: bool = False) -> Path:
    return fetch(
        club_url(club_slug),
        cache_path("spfl", club_slug, "fixtures.html"),
        ttl_hours=1,
        force=force,
        expected_marker="fixtures-list__group",
    )


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _parse_day(value: str) -> date:
    value = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", _clean(value))
    return datetime.strptime(value, "%A %d %B %Y").date()


def _competition(title: str) -> tuple[str, str]:
    title = _clean(title)
    if title in COMPETITION_MAP:
        return COMPETITION_MAP[title]
    # Future competitions still get a stable id rather than being dropped.
    return f"sco:{slugify(title)}", title


def parse_html(html: str) -> pl.DataFrame:
    soup = BeautifulSoup(html, "html.parser")
    now = utc_now_iso()
    rows: list[dict[str, object]] = []

    for group in soup.select("div.fixtures-list__group"):
        title_node = group.select_one(".fixtures-list__group__title")
        day_node = group.select_one(".fixtures-list__group__day")
        if title_node is None or day_node is None:
            continue
        competition_id, competition_name = _competition(title_node.get_text())
        try:
            match_date = _parse_day(day_node.get_text())
        except ValueError:
            continue
        season = season_from_date(match_date)
        competition_slug = competition_id.split(":", 1)[-1]

        results = group.select_one(".fixtures-list__results")
        if results is not None:
            teams = [
                _clean(node.get_text()) for node in results.select(".fixtures-list__results__team")
            ]
            score_node = results.select_one(".fixtures-list__results__score")
            if len(teams) != 2 or score_node is None:
                continue
            score = re.match(r"(\d+)\s*-\s*(\d+)", _clean(score_node.get_text()))
            if not score:
                continue
            home, away = teams
            rows.append(
                {
                    "match_id": (
                        f"spfl-{competition_slug}-{match_date}-{slugify(home)}-{slugify(away)}"
                    ),
                    "competition_id": competition_id,
                    "competition_name": competition_name,
                    "season": season,
                    "date": match_date,
                    "kickoff": None,
                    "home_team_raw": home,
                    "away_team_raw": away,
                    "home_goals": int(score.group(1)),
                    "away_goals": int(score.group(2)),
                    "status": "played",
                    "source_id": "spfl",
                    "ingested_at": now,
                }
            )
            continue

        for dl in group.select("dl.fixtures-list__group__fixtures"):
            for time_node, team_node in zip(dl.find_all("dt"), dl.find_all("dd"), strict=False):
                teams = [_clean(node.get_text()) for node in team_node.select("a")]
                if len(teams) != 2:
                    continue
                home, away = teams
                rows.append(
                    {
                        "match_id": (
                            f"spfl-{competition_slug}-{match_date}-{slugify(home)}-{slugify(away)}"
                        ),
                        "competition_id": competition_id,
                        "competition_name": competition_name,
                        "season": season,
                        "date": match_date,
                        "kickoff": _clean(time_node.get_text()),
                        "home_team_raw": home,
                        "away_team_raw": away,
                        "home_goals": None,
                        "away_goals": None,
                        "status": "scheduled",
                        "source_id": "spfl",
                        "ingested_at": now,
                    }
                )

    if not rows:
        return pl.DataFrame({column: [] for column in FIXTURE_COLUMNS})
    return pl.DataFrame(
        rows,
        schema_overrides={
            "match_id": pl.String,
            "competition_id": pl.String,
            "competition_name": pl.String,
            "season": pl.String,
            "date": pl.Date,
            "kickoff": pl.String,
            "home_team_raw": pl.String,
            "away_team_raw": pl.String,
            "home_goals": pl.Int64,
            "away_goals": pl.Int64,
            "status": pl.String,
            "source_id": pl.String,
            "ingested_at": pl.String,
        },
    ).select(FIXTURE_COLUMNS)


def load(club_slug: str = "aberdeen", *, force: bool = False) -> pl.DataFrame:
    return parse_html(download(club_slug, force=force).read_text(encoding="utf-8"))


def ingest(club_slug: str = "aberdeen", *, force: bool = False) -> IngestResult:
    try:
        frame = load(club_slug, force=force)
        return IngestResult(
            source="spfl",
            status="ok",
            rows=frame.height,
            details={"club": club_slug, "url": club_url(club_slug)},
        )
    except Exception as exc:  # noqa: BLE001 - reported by the runner
        return IngestResult(source="spfl", status="error", errors=[str(exc)])


class SPFL:
    name = "spfl"
    capabilities: ClassVar[set[Capability]] = {Capability.FIXTURES, Capability.RESULTS}
    lane = Lane.DERIVED_DISPLAY
