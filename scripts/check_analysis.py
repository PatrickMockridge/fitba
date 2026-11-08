#!/usr/bin/env python3
"""Guard for the season-overview payload and rendered page."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data" / "generated" / "analysis" / "summary.json"
MATCHDAY = ROOT / "web" / "data" / "generated" / "matchday" / "upcoming.json"
OUT = ROOT / "web" / "out" / "analysis" / "index.html"
FORBIDDEN = (
    "will leave",
    "set to leave",
    "sold",
    "sell-high",
    "possible injury",
)
FORBIDDEN_KEYS = {
    "fee",
    "wage",
    "salary",
    "contract_end",
    "contract_expiry",
    "release_clause",
    "value_gbp",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk(value: Any) -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.append((str(key), child))
            found.extend(_walk(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk(child))
    return found


def main() -> int:
    errors: list[str] = []
    if not DATA.exists():
        print(f"missing {DATA}; run `uv run fitba publish`")
        return 1
    data = _load(DATA)
    if data.get("schema_version") != "1.0.0":
        errors.append("analysis summary schema_version is not 1.0.0")
    rankings = data.get("league_rankings") or {}
    if not rankings:
        errors.append("analysis summary is missing league_rankings")
    else:
        if rankings.get("scope") != "league_only":
            errors.append("league_rankings scope must be league_only")
        if rankings.get("state") not in {"available", "partial", "unavailable"}:
            errors.append("league_rankings state is invalid")
        if rankings.get("state") != "unavailable":
            table_path = (
                ROOT
                / "web"
                / "data"
                / "generated"
                / "tables"
                / f"premiership-{data.get('season')}.json"
            )
            table = _load(table_path) if table_path.exists() else {}
            table_rows = table.get("rows") or []
            table_ids = {str(row.get("team_id")) for row in table_rows}
            teams = rankings.get("teams") or []
            team_ids = {str(team.get("team_id")) for team in teams}
            if int(rankings.get("league_size") or 0) != len(table_rows):
                errors.append("league_rankings league_size does not match the league table")
            if team_ids != table_ids:
                errors.append("league_rankings teams do not match the league table")
            aberdeen = rankings.get("aberdeen") or {}
            table_row = next(
                (row for row in table_rows if str(row.get("team_id")) == "sco:aberdeen"),
                {},
            )
            for name in ("position", "played", "points"):
                if aberdeen.get(name) != table_row.get(name):
                    errors.append(f"league_rankings Aberdeen {name} does not match the table")
            played = int(table_row.get("played") or 0)
            if played > 0:
                expected = {
                    "goals_for_pm": round(int(table_row.get("gf") or 0) / played, 2),
                    "goals_against_pm": round(int(table_row.get("ga") or 0) / played, 2),
                    "gd_pm": round(
                        (int(table_row.get("gf") or 0) - int(table_row.get("ga") or 0)) / played,
                        2,
                    ),
                }
                for name, value in expected.items():
                    if (aberdeen.get("values") or {}).get(name) != value:
                        errors.append(
                            f"league_rankings Aberdeen {name} does not match the table rate"
                        )
            league_size = int(rankings.get("league_size") or 0)
            for team in teams:
                for metric in rankings.get("metrics") or []:
                    metric_id = str(metric.get("id"))
                    value = (team.get("values") or {}).get(metric_id)
                    rank = (team.get("ranks") or {}).get(metric_id)
                    if (value is None) != (rank is None):
                        errors.append(
                            f"league_rankings {team.get('team_id')}: {metric_id} "
                            "value/rank null state differs"
                        )
                    if rank is not None and not 1 <= int(rank) <= league_size:
                        errors.append(
                            f"league_rankings {team.get('team_id')}: {metric_id} "
                            "rank is out of bounds"
                        )
            coverage = rankings.get("coverage") or {}
            for name in ("provider_xg", "possession"):
                entry = coverage.get(name) or {}
                total = int(entry.get("team_rows_total") or 0)
                covered = int(entry.get("team_rows") or 0)
                if covered > total:
                    errors.append(f"league_rankings {name} covered rows exceed total")
                if bool(entry.get("complete")) != (total > 0 and covered == total):
                    errors.append(f"league_rankings {name} complete flag is inconsistent")
            if "not fitba fxG" not in str(rankings.get("note") or ""):
                errors.append("league_rankings must distinguish provider xG from fxG")
    next_up = data.get("next_up") or []
    if not 0 <= len(next_up) <= 3:
        errors.append("next_up must contain at most three rows")
    if any(row.get("conflict_review") for row in next_up):
        errors.append("next_up contains a conflict-review fixture")
    availability = data.get("availability") or {}
    counts = availability.get("counts") or {}
    official_total = sum(
        int(counts.get(key) or 0)
        for key in ("out_official", "suspended_official", "doubtful", "available", "returned")
    )
    if int(counts.get("active") or 0) != official_total + int(counts.get("unknown") or 0):
        errors.append(
            "availability counts do not sum: "
            f"active={counts.get('active')} official={official_total} "
            f"unknown={counts.get('unknown')}"
        )
    for row in availability.get("inferred") or []:
        if "injur" in str(row.get("note") or "").casefold():
            errors.append("inferred absence must not claim injury")
    for row in availability.get("suspensions") or []:
        if not row.get("competition_id") or not row.get("status"):
            errors.append("suspension row missing competition or status")
        if (
            row.get("rule_verified")
            and row.get("status") == "projected"
            and not row.get("rule_source")
        ):
            errors.append("projected suspension missing rule source")
    aims = data.get("aims") or []
    if len(aims) > 3:
        errors.append("aims must contain at most three rows")
    if not any("Analyst-set" in str(row.get("note") or "") for row in aims):
        errors.append("aims must carry the analyst-set baseline note")
    squad = data.get("squad_decisions") or {}
    if (squad.get("contract") or {}).get("status") != "unavailable":
        errors.append("squad decisions contract status must be unavailable")
    for key, _value in _walk(data):
        if key.casefold() in FORBIDDEN_KEYS:
            errors.append(f"forbidden analysis field {key!r}")
    if MATCHDAY.exists():
        matchday = _load(MATCHDAY)
        current = (matchday.get("fixture") or {}).get("date")
        if current and next_up and str(next_up[0].get("date")) != str(current):
            errors.append("analysis next fixture does not match matchday current fixture")
    if OUT.exists():
        html = OUT.read_text(encoding="utf-8")
        if len(re.findall(r"<h1[ >]", html)) != 1:
            errors.append("analysis page must have exactly one H1")
        for phrase in ("Where Aberdeen rank", "The Premiership, ranked"):
            if phrase not in html:
                errors.append(f"analysis page is missing the league rankings heading {phrase!r}")
        lowered = html.casefold()
        for phrase in ("case.claim", "owner view", "chairman frame", "how the record compares"):
            if phrase in lowered:
                errors.append(f"old analysis content still rendered: {phrase!r}")
        for phrase in FORBIDDEN:
            if phrase in lowered:
                errors.append(f"forbidden analysis copy: {phrase!r}")
    if errors:
        print("Analysis check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(
        f"Analysis check passed ({len(next_up)} next fixtures, "
        f"{int(counts.get('active') or 0)} active availability rows, "
        f"{int(rankings.get('league_size') or 0)} league teams, "
        f"{int(rankings.get('matches') or 0)} matches)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
