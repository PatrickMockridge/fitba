"""Independent verification functions for registered metrics.

These functions re-derive published values from the published corpus. They are
not production calculations; production has one home. A recompute check is
allowed to duplicate the arithmetic precisely to catch drift.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class VerificationResult:
    status: str = "pass"
    checks: list[dict[str, str]] = field(default_factory=list)
    rows_checked: int = 0
    fields_checked: int = 0
    errors: list[str] = field(default_factory=list)

    def fail(self, message: str) -> None:
        self.status = "fail"
        self.errors.append(message)
        self.checks.append({"name": "error", "status": "fail", "message": message})

    def note(self, name: str, passed: bool, message: str) -> None:
        self.checks.append(
            {"name": name, "status": "pass" if passed else "fail", "message": message}
        )
        if not passed:
            self.status = "fail"
            self.errors.append(message)


def _payload(corpus: dict[str, Any], path: str) -> Any:
    return corpus.get(path)


def _round(value: float, decimals: int = 2) -> float:
    return round(value, decimals)


def verify_table_record(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    tables = [key for key in corpus if key.startswith("tables/") and key.endswith(".json")]
    if not tables:
        result.fail("no table payloads found")
        return result
    for key in tables:
        rows = _payload(corpus, key).get("rows", [])
        for row in rows:
            result.rows_checked += 1
            result.fields_checked += 5
            if row["played"] != row["won"] + row["drawn"] + row["lost"]:
                result.fail(f"{key}: played != W+D+L for {row.get('team_name')}")
            if row["gd"] != row["gf"] - row["ga"]:
                result.fail(f"{key}: gd != GF-GA for {row.get('team_name')}")
            if row["raw_points"] != 3 * row["won"] + row["drawn"]:
                result.fail(f"{key}: raw points != 3W+D for {row.get('team_name')}")
            if row["points"] != row["raw_points"] - row["deduction"]:
                result.fail(f"{key}: points != raw points - deduction for {row.get('team_name')}")
    result.note("table.record", result.status == "pass", f"{result.rows_checked} rows checked")
    return result


def _check_form_record(record: dict[str, Any], label: str, result: VerificationResult) -> None:
    result.rows_checked += 1
    result.fields_checked += 5
    if record.get("played") != record.get("won", 0) + record.get("drawn", 0) + record.get(
        "lost", 0
    ):
        result.fail(f"{label}: played != W+D+L")
    if record.get("points") != 3 * record.get("won", 0) + record.get("drawn", 0):
        result.fail(f"{label}: points != 3W+D")
    if record.get("gd") != record.get("gf", 0) - record.get("ga", 0):
        result.fail(f"{label}: gd != GF-GA")
    played = record.get("played") or 0
    if played:
        expected_ppg = _round(record.get("points", 0) / played, 2)
        if record.get("ppg") is not None and abs(float(record["ppg"]) - expected_ppg) > 0.011:
            result.fail(f"{label}: ppg mismatch")
        expected_gf = _round(record.get("gf", 0) / played, 2)
        if record.get("gf_pg") is not None and abs(float(record["gf_pg"]) - expected_gf) > 0.011:
            result.fail(f"{label}: gf_pg mismatch")
        expected_ga = _round(record.get("ga", 0) / played, 2)
        if record.get("ga_pg") is not None and abs(float(record["ga_pg"]) - expected_ga) > 0.011:
            result.fail(f"{label}: ga_pg mismatch")


def verify_matchday_form(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    data = _payload(corpus, "matchday/upcoming.json")
    if not data:
        result.fail("matchday payload missing")
        return result
    guide = data.get("form_guide") or {}
    for team, block in guide.items():
        for split in ("recent", "season_record", "home", "away"):
            record = block.get(split)
            if isinstance(record, dict):
                _check_form_record(record, f"{team}.{split}", result)
    result.note(
        "matchday.form", result.status == "pass", f"{result.rows_checked} form records checked"
    )
    return result


def verify_matchday_strength(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    data = _payload(corpus, "matchday/upcoming.json")
    if not data:
        result.fail("matchday payload missing")
        return result
    table_rows: dict[str, dict[str, Any]] = {}
    for key in corpus:
        if key.startswith("tables/") and key.endswith(".json"):
            for row in _payload(corpus, key).get("rows", []):
                table_rows[row["team_id"]] = row
    for side, strength in (data.get("strength") or {}).items():
        team_id = strength.get("team_id")
        row = table_rows.get(team_id)
        if not row:
            continue
        result.rows_checked += 1
        result.fields_checked += 8
        for key in ("position", "played", "points", "gf", "ga", "gd"):
            if strength.get(key) != row.get(key):
                result.fail(f"{side}: strength {key} != table {key}")
    result.note(
        "matchday.strength", result.status == "pass", f"{result.rows_checked} strength rows checked"
    )
    return result


def verify_matchday_coverage(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    data = _payload(corpus, "matchday/upcoming.json")
    if not data:
        result.fail("matchday payload missing")
        return result
    snapshot = (data.get("coverage") or {}).get("snapshot") or {}
    fixtures = snapshot.get("fixtures")
    lineups = snapshot.get("fixtures_with_lineups")
    result.rows_checked = 1
    result.fields_checked = 2
    if isinstance(fixtures, int) and isinstance(lineups, int) and lineups > fixtures:
        result.fail("lineups exceed fixtures in matchday snapshot")
    age = snapshot.get("age_hours")
    if isinstance(age, (int, float)) and age < 0:
        result.fail("negative matchday snapshot age")
    result.note("matchday.coverage", result.status == "pass", "snapshot coverage checked")
    return result


def verify_needs_summary(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    data = _payload(corpus, "needs/aberdeen.json")
    if not data:
        result.fail("needs payload missing")
        return result
    families = data.get("families") or []
    summary = data.get("summary") or {}
    result.rows_checked = len(families)
    result.fields_checked = 5
    if summary.get("families") != len(families):
        result.fail("needs summary family count != families length")
    counts = summary.get("counts") or {}
    actual: dict[str, int] = {}
    for family in families:
        category = family.get("category")
        actual[category] = actual.get(category, 0) + 1
    for category, value in counts.items():
        if actual.get(category, 0) != value:
            result.fail(f"needs summary count mismatch for {category}")
    # Availability is counted once per squad player, not once per family. The
    # needs page filters family lists, so reconcile against the squad payload.
    squad = _payload(corpus, "squad/aberdeen.json") or {}
    squad_players = squad.get("players") or []
    if squad_players:
        known = sum(
            1
            for player in squad_players
            if (player.get("availability") or {}).get("status") != "unknown"
        )
        unknown = len(squad_players) - known
    else:
        known = summary.get("availability_known") or 0
        unknown = summary.get("availability_unknown") or 0
    if summary.get("availability_known") is not None and summary["availability_known"] != known:
        result.fail("needs availability_known mismatch")
    if (
        summary.get("availability_unknown") is not None
        and summary["availability_unknown"] != unknown
    ):
        result.fail("needs availability_unknown mismatch")
    coverage_availability = (data.get("coverage") or {}).get("availability") or {}
    if coverage_availability.get("known") != summary.get("availability_known"):
        result.fail("needs coverage known != summary known")
    if coverage_availability.get("unknown") != summary.get("availability_unknown"):
        result.fail("needs coverage unknown != summary unknown")
    result.note("needs.summary", result.status == "pass", f"{len(families)} families checked")
    return result


def verify_transfer_summary(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    data = _payload(corpus, "transfers/aberdeen.json")
    if not data:
        result.fail("transfers payload missing")
        return result
    rows = data.get("transfers") or []
    summary = data.get("summary") or {}
    result.rows_checked = len(rows)
    result.fields_checked = 6
    if summary.get("total") != len(rows):
        result.fail("transfer summary total != row count")
    if summary.get("confirmed") != sum(
        1 for row in rows if row.get("verification_status") == "confirmed"
    ):
        result.fail("transfer summary confirmed mismatch")
    if summary.get("curated") != sum(
        1 for row in rows if row.get("verification_status") == "curated"
    ):
        result.fail("transfer summary curated mismatch")
    if summary.get("players") != len({row.get("player_key") for row in rows}):
        result.fail("transfer summary player count mismatch")
    if summary.get("seasons_covered") != len({row.get("season") for row in rows}):
        result.fail("transfer summary season count mismatch")
    if summary.get("windows_covered") != len(
        {(row.get("season"), row.get("window")) for row in rows}
    ):
        result.fail("transfer summary window count mismatch")
    result.note("transfers.summary", result.status == "pass", f"{len(rows)} rows checked")
    return result


def verify_transfer_windows(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    data = _payload(corpus, "transfers/aberdeen.json")
    if not data:
        result.fail("transfers payload missing")
        return result
    rows = data.get("transfers") or []
    windows = data.get("windows") or []
    result.rows_checked = len(windows)
    result.fields_checked += 5
    for window in windows:
        key = (window.get("season"), window.get("window"))
        scoped = [row for row in rows if (row.get("season"), row.get("window")) == key]
        if window.get("arrivals") != sum(1 for row in scoped if row.get("direction") == "in"):
            result.fail(f"{key}: arrivals mismatch")
        if window.get("departures") != sum(1 for row in scoped if row.get("direction") == "out"):
            result.fail(f"{key}: departures mismatch")
    result.note("transfers.window", result.status == "pass", f"{len(windows)} windows checked")
    return result


def verify_transfer_coverage(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    data = _payload(corpus, "transfers/aberdeen.json")
    if not data:
        result.fail("transfers payload missing")
        return result
    coverage = data.get("coverage") or {}
    result.rows_checked = 1
    result.fields_checked = 3
    if not coverage.get("audited_from"):
        result.fail("transfer coverage missing audited_from")
    if not coverage.get("historical_from"):
        result.fail("transfer coverage missing historical_from")
    result.note("transfers.coverage", result.status == "pass", "coverage fields present")
    return result


def verify_history_scorecard(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    data = _payload(corpus, "history/aberdeen.json")
    if not data:
        result.fail("history payload missing")
        return result
    scorecard = data.get("scorecard") or {}
    seasons = data.get("seasons") or []
    staff = data.get("staff") or []
    honours = data.get("honours") or []
    era_id = (data.get("era") or {}).get("id")
    result.rows_checked = len(seasons)
    result.fields_checked = 5
    # The scorecard is era-scoped: completed seasons and honours in this era.
    completed = [season for season in seasons if season.get("status") == "completed"]
    if scorecard.get("seasons") != len(completed):
        result.fail("history scorecard seasons != completed seasons length")
    era_honours = [honour for honour in honours if era_id is None or honour.get("era") == era_id]
    if scorecard.get("honours_total") != len(era_honours):
        result.fail("history scorecard honours_total != era honours length")
    manager_people = {
        person.get("person_id")
        for person in staff
        for stint in person.get("stints", [])
        if stint.get("role_group") == "manager" and (stint.get("record") or {}).get("played")
    }
    if scorecard.get("manager_count") != len(manager_people):
        result.fail("history scorecard manager_count mismatch")
    result.note(
        "history.scorecard",
        result.status == "pass",
        f"{len(completed)} completed seasons, {len(era_honours)} era honours checked",
    )
    return result


def verify_history_baseline(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    data = _payload(corpus, "history/aberdeen.json")
    if not data:
        result.fail("history payload missing")
        return result
    baseline = data.get("baseline") or {}
    rows = baseline.get("seasons") or []
    result.rows_checked = len(rows)
    result.fields_checked = 3
    if baseline.get("count") != len(rows):
        result.fail("history baseline count != seasons length")
    if rows:
        positions = [
            row.get("position") for row in rows if isinstance(row.get("position"), (int, float))
        ]
        points = [row.get("points") for row in rows if isinstance(row.get("points"), (int, float))]
        if (
            positions
            and baseline.get("average_position") is not None
            and abs(float(baseline["average_position"]) - round(sum(positions) / len(positions), 1))
            > 0.11
        ):
            result.fail("history baseline average_position mismatch")
        if (
            points
            and baseline.get("average_points") is not None
            and abs(float(baseline["average_points"]) - round(sum(points) / len(points), 1)) > 0.11
        ):
            result.fail("history baseline average_points mismatch")
    result.note("history.baseline", result.status == "pass", f"{len(rows)} baseline rows checked")
    return result


def verify_history_coverage(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    data = _payload(corpus, "history/aberdeen.json")
    if not data:
        result.fail("history payload missing")
        return result
    coverage = data.get("coverage") or {}
    seasons = data.get("seasons") or []
    result.rows_checked = 1
    result.fields_checked = 2
    completed = coverage.get("completed_seasons")
    if isinstance(completed, int) and completed + 1 < len(seasons):
        result.fail("history coverage completed seasons inconsistent with seasons list")
    if coverage.get("seasons_curated") is not None and coverage["seasons_curated"] > len(seasons):
        result.fail("history coverage curated seasons exceed seasons list")
    result.note("history.coverage", result.status == "pass", "history coverage checked")
    return result


def verify_squad_summary(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    data = _payload(corpus, "squad/aberdeen.json")
    if not data:
        result.fail("squad payload missing")
        return result
    players = data.get("players") or []
    summary = data.get("summary") or {}
    result.rows_checked = len(players)
    result.fields_checked = 5
    if summary.get("total_players") != len(players):
        result.fail("squad summary total_players != players length")
    by_status = summary.get("by_status") or {}
    actual: dict[str, int] = {}
    for player in players:
        status = player.get("status")
        actual[status] = actual.get(status, 0) + 1
    for status, value in by_status.items():
        if actual.get(status, 0) != value:
            result.fail(f"squad summary by_status mismatch for {status}")
    if summary.get("loans_out") != actual.get("loan_out", 0):
        result.fail("squad summary loans_out mismatch")
    if summary.get("loans_in") != actual.get("loan_in", 0):
        result.fail("squad summary loans_in mismatch")
    result.note("squad.summary", result.status == "pass", f"{len(players)} players checked")
    return result


def verify_rumours_summary(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    data = _payload(corpus, "rumours/aberdeen.json")
    if not data:
        result.fail("rumours payload missing")
        return result
    rows = data.get("rumours") or []
    summary = data.get("summary") or {}
    result.rows_checked = len(rows)
    result.fields_checked = 4
    if summary.get("total") != len(rows):
        result.fail("rumour summary total != row count")
    for summary_key, row_key in (
        ("by_status", "status"),
        ("by_confidence", "confidence"),
        ("by_direction", "direction"),
    ):
        actual: dict[str, int] = {}
        for row in rows:
            value = row.get(row_key)
            actual[value] = actual.get(value, 0) + 1
        expected = summary.get(summary_key) or {}
        if expected != actual:
            result.fail(f"rumour summary {summary_key} mismatch")
    result.note("rumours.summary", result.status == "pass", f"{len(rows)} rumours checked")
    return result


def verify_coverage(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    coverage = _payload(corpus, "coverage.json")
    transfers = _payload(corpus, "transfers/aberdeen.json")
    squad = _payload(corpus, "squad/aberdeen.json")
    if not coverage:
        result.fail("coverage payload missing")
        return result
    result.rows_checked = 1
    result.fields_checked = 3
    if transfers:
        expected = (coverage.get("transfers") or {}).get("count")
        actual = (transfers.get("summary") or {}).get("total")
        if expected is not None and expected != actual:
            result.fail("coverage transfers count != transfer summary total")
    if squad:
        expected = (coverage.get("squad") or {}).get("players")
        actual = (squad.get("summary") or {}).get("total_players")
        if expected is not None and actual is not None and expected != actual:
            result.fail("coverage squad players != squad summary total")
    result.note("coverage.surfaces", result.status == "pass", "coverage cross-surface checks")
    return result


CHECKS = {
    "fitba.metrics.checks:verify_table_record": verify_table_record,
    "fitba.metrics.checks:verify_matchday_form": verify_matchday_form,
    "fitba.metrics.checks:verify_matchday_strength": verify_matchday_strength,
    "fitba.metrics.checks:verify_matchday_coverage": verify_matchday_coverage,
    "fitba.metrics.checks:verify_needs_summary": verify_needs_summary,
    "fitba.metrics.checks:verify_transfer_summary": verify_transfer_summary,
    "fitba.metrics.checks:verify_transfer_windows": verify_transfer_windows,
    "fitba.metrics.checks:verify_transfer_coverage": verify_transfer_coverage,
    "fitba.metrics.checks:verify_history_scorecard": verify_history_scorecard,
    "fitba.metrics.checks:verify_history_baseline": verify_history_baseline,
    "fitba.metrics.checks:verify_history_coverage": verify_history_coverage,
    "fitba.metrics.checks:verify_squad_summary": verify_squad_summary,
    "fitba.metrics.checks:verify_rumours_summary": verify_rumours_summary,
    "fitba.metrics.checks:verify_coverage": verify_coverage,
}
