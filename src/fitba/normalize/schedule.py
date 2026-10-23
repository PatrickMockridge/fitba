"""Canonical Aberdeen season schedule.

The live SPFL club page carries only a short horizon (three upcoming fixtures).
The normalized history season already holds the full API-Football season, so the
publisher merges the two rather than making another request. This module owns
the merge, status mapping, local kickoff, neutral-venue and conflict rules.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from fitba.ingest.fixtures import load_club_fixtures
from fitba.ingest.history import load_history_fixtures
from fitba.normalize.competitions import canonical_name
from fitba.normalize.teams import TeamRegistry, slugify

LONDON = ZoneInfo("Europe/London")
ABERDEEN_ID = "sco:aberdeen"

PLAYED_STATUSES = {"FT", "AET", "PEN"}
SCHEDULED_STATUSES = {"NS", "TBD"}
IN_PLAY_STATUSES = {"1H", "HT", "2H", "ET", "BT", "P", "S", "LIVE"}
STATUS_MAP = {
    **{status: "played" for status in PLAYED_STATUSES},
    **{status: "scheduled" for status in SCHEDULED_STATUSES},
    **{status: "in_play" for status in IN_PLAY_STATUSES},
    "PST": "postponed",
    "CANC": "cancelled",
    "ABD": "abandoned",
    "AWD": "awarded",
    "WO": "walkover",
}


def _local_datetime(value: Any) -> tuple[date | None, str | None, str | None]:
    """Return local date, HH:MM and ISO source from an API UTC timestamp."""
    if value is None or str(value).strip() == "":
        return None, None, None
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None, None, None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    local = parsed.astimezone(LONDON)
    return local.date(), local.strftime("%H:%M"), text


def _stage(competition_id: str, round_name: str | None) -> str | None:
    if not round_name:
        return None
    text = str(round_name).strip()
    if competition_id == "sco:premiership" and text.lower().startswith("regular season"):
        return None
    if text.lower() in {"semi-finals", "semi-final"}:
        return "Semi-final"
    if text.lower() in {"quarter-finals", "quarter-final"}:
        return "Quarter-final"
    if text.lower() in {"round of 16", "last 16"}:
        return "Round of 16"
    return text


def _team(registry: TeamRegistry, name: str | None, provider_id: Any = None) -> tuple[str, str]:
    raw = str(name or "Unknown")
    resolved = registry.resolve(raw)
    if resolved is None:
        return f"sco:provisional-{slugify(raw) or 'unknown'}", raw
    return resolved, registry.canonical_name(resolved)


def _is_friendly(competition_id: str) -> bool:
    return competition_id.startswith("sco:other:friendlies")


def _venue(venue: str | None, stage: str | None, competition_id: str) -> tuple[str | None, bool]:
    text = str(venue or "").strip() or None
    neutral = bool(text and "hampden" in text.casefold())
    if (
        not neutral
        and competition_id in {"sco:league-cup", "sco:scottish-cup"}
        and stage in {"Semi-final", "Final"}
    ):
        neutral = True
    return text, neutral


def load_schedule(season: str, *, today: date | None = None) -> list[dict[str, Any]]:
    """Return the merged, canonical schedule for one season.

    Rows are sorted by local date and kickoff. `conflict_review` rows are kept
    for the record but excluded by the callers from lookaheads, aims and
    inference.
    """
    registry = TeamRegistry()
    today = today or datetime.now(UTC).astimezone(LONDON).date()
    api = load_history_fixtures(season)
    spfl = load_club_fixtures("aberdeen")
    rows: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    for raw in api.to_dicts() if api.height else []:
        if str(raw.get("season") or "") not in {"", season} and str(raw.get("season")) != season:
            # History files are season-scoped; keep this guard for malformed input.
            continue
        competition_id = str(raw.get("competition_id") or "")
        if not competition_id:
            continue
        local_date, kickoff, source_date = _local_datetime(raw.get("date"))
        if local_date is None:
            continue
        home_id, home_name = _team(registry, raw.get("home_team_name"), raw.get("home_team_id"))
        away_id, away_name = _team(registry, raw.get("away_team_name"), raw.get("away_team_id"))
        provider_status = str(raw.get("status") or "").upper()
        status = STATUS_MAP.get(provider_status, "unknown")
        is_home = home_id == ABERDEEN_ID
        is_away = away_id == ABERDEEN_ID
        stage = _stage(competition_id, raw.get("round"))
        venue, neutral = _venue(raw.get("venue"), stage, competition_id)
        key = (str(local_date), competition_id, home_id, away_id)
        rows[key] = {
            "schedule_key": f"{local_date}|{competition_id}|{home_id}|{away_id}",
            "fixture_id": raw.get("fixture_id"),
            "match_id": None,
            "season": season,
            "date": str(local_date),
            "kickoff": kickoff,
            "kickoff_tz": "Europe/London",
            "kickoff_status": "provisional",
            "source_date": source_date,
            "provider_status": provider_status,
            "status": status,
            "competition_id": competition_id,
            "competition_name": canonical_name(
                competition_id, str(raw.get("competition_name") or "")
            ),
            "stage": stage,
            "home_team_id": home_id,
            "home_team_name": home_name,
            "away_team_id": away_id,
            "away_team_name": away_name,
            "is_home": is_home,
            "is_away": is_away,
            "opponent_id": away_id if is_home else home_id,
            "opponent_name": away_name if is_home else home_name,
            "venue": venue,
            "neutral": neutral,
            "is_friendly": _is_friendly(competition_id),
            "sources": ["api_football"],
            "conflict_review": False,
        }

    for raw in spfl.to_dicts() if spfl.height else []:
        if str(raw.get("season") or "") != season:
            continue
        competition_id = str(raw.get("competition_id") or "")
        if not competition_id:
            continue
        raw_date = raw.get("date")
        local_date = raw_date if isinstance(raw_date, date) else None
        if local_date is None:
            continue
        home_id = str(raw.get("home_team_id") or "")
        away_id = str(raw.get("away_team_id") or "")
        home_name = str(raw.get("home_team_name") or home_id)
        away_name = str(raw.get("away_team_name") or away_id)
        status = "played" if str(raw.get("status")) == "played" else "scheduled"
        stage = None
        venue, neutral = _venue(None, stage, competition_id)
        key = (str(local_date), competition_id, home_id, away_id)
        target = rows.get(key)
        if target is None:
            # Try a source-name match when one side of the key differs.
            for candidate_key, candidate in rows.items():
                if (
                    candidate_key[0] == str(local_date)
                    and candidate_key[1] == competition_id
                    and {candidate["home_team_id"], candidate["away_team_id"]} == {home_id, away_id}
                ):
                    target = candidate
                    break
        if target is not None:
            target["match_id"] = raw.get("match_id")
            target["kickoff"] = raw.get("kickoff") or target.get("kickoff")
            target["kickoff_status"] = "confirmed" if raw.get("kickoff") else "provisional"
            target["status"] = status
            target["source_id"] = "spfl"
            target["sources"] = sorted(set(target["sources"] + ["spfl"]))
            continue
        key = (str(local_date), competition_id, home_id, away_id)
        rows[key] = {
            "schedule_key": f"{local_date}|{competition_id}|{home_id}|{away_id}",
            "fixture_id": None,
            "match_id": raw.get("match_id"),
            "season": season,
            "date": str(local_date),
            "kickoff": raw.get("kickoff"),
            "kickoff_tz": "Europe/London",
            "kickoff_status": "confirmed",
            "source_date": None,
            "provider_status": None,
            "status": status,
            "competition_id": competition_id,
            "competition_name": canonical_name(
                competition_id, str(raw.get("competition_name") or "")
            ),
            "stage": None,
            "home_team_id": home_id,
            "home_team_name": home_name,
            "away_team_id": away_id,
            "away_team_name": away_name,
            "is_home": home_id == ABERDEEN_ID,
            "is_away": away_id == ABERDEEN_ID,
            "opponent_id": away_id if home_id == ABERDEEN_ID else home_id,
            "opponent_name": away_name if home_id == ABERDEEN_ID else home_name,
            "venue": None,
            "neutral": neutral,
            "is_friendly": _is_friendly(competition_id),
            "sources": ["spfl"],
            "conflict_review": False,
        }

    # Same team pair on the same local date in different competitions is a
    # conflict. The SPFL listed fixture wins; the other row stays visible but is
    # excluded from every forward-looking surface until resolved.
    by_pair: dict[tuple[str, tuple[str, str]], list[dict[str, Any]]] = {}
    for row in rows.values():
        if row["is_friendly"] or row["status"] not in {"scheduled", "postponed"}:
            continue
        home = str(row["home_team_id"])
        away = str(row["away_team_id"])
        pair = (min(home, away), max(home, away))
        by_pair.setdefault((str(row["date"]), pair), []).append(row)
    for group in by_pair.values():
        if len({row["competition_id"] for row in group}) < 2:
            continue
        spfl_rows = [row for row in group if "spfl" in row["sources"]]
        preferred = spfl_rows[0] if spfl_rows else None
        for row in group:
            if preferred is not None and row is preferred:
                continue
            row["conflict_review"] = True
            row["status"] = "conflict_review"
            if (
                preferred is not None
                and preferred.get("kickoff")
                and row.get("kickoff")
                and row["kickoff"] != preferred["kickoff"]
            ):
                row["kickoff_status"] = "conflict"

    out = sorted(
        rows.values(),
        key=lambda row: (
            str(row["date"]),
            str(row.get("kickoff") or "99:99"),
            str(row["competition_id"]),
        ),
    )
    for row in out:
        if row["status"] == "scheduled" and str(row["date"]) < str(today):
            row["status"] = "overdue"
    return out


__all__ = ["STATUS_MAP", "load_schedule"]
