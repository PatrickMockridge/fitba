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
        ("by_affiliation", "affiliation"),
    ):
        actual: dict[str, int] = {}
        for row in rows:
            value = row.get(row_key)
            actual[value] = actual.get(value, 0) + 1
        expected = summary.get(summary_key) or {}
        if expected != actual:
            result.fail(f"rumour summary {summary_key} mismatch")
    targets = sum(
        1
        for row in rows
        if row.get("direction") == "in" and row.get("affiliation") == "external_target"
    )
    if summary.get("targets") != targets:
        result.fail("rumour summary targets mismatch")
    returns = sum(
        1
        for row in rows
        if row.get("direction") == "in" and row.get("affiliation") == "former_player"
    )
    if summary.get("return_links") != returns:
        result.fail("rumour summary return_links mismatch")
    result.note("rumours.summary", result.status == "pass", f"{len(rows)} rumours checked")
    return result


def verify_forum_former_profile(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    data = _payload(corpus, "forum/afc_chat.json") or {}
    signals = data.get("signals") or []
    profile = data.get("profile") or {}
    result.rows_checked = len(signals)
    result.fields_checked = 3
    mix = profile.get("affiliation_mix") or {}
    if sum(int(value) for value in mix.values()) != len(signals):
        result.fail("forum affiliation_mix does not sum to signals")
    external = sum(
        1 for signal in signals if (signal.get("affiliation") or "unknown") == "external_target"
    )
    if profile.get("external_sample_size") != external:
        result.fail("forum external_sample_size mismatch")
    former = sum(
        1 for signal in signals if (signal.get("affiliation") or "unknown") == "former_player"
    )
    former_profile = profile.get("former_player_profile") or {}
    if former_profile.get("sample_size") != former:
        result.fail("forum former_player_profile sample_size mismatch")
    if former_profile.get("mentions") != sum(
        int(signal.get("mentions") or 0)
        for signal in signals
        if (signal.get("affiliation") or "unknown") == "former_player"
    ):
        result.fail("forum former_player_profile mentions mismatch")
    result.note("forum.former_profile", result.status == "pass", f"{len(signals)} signals checked")
    return result


def verify_rumours_former_lane(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    data = _payload(corpus, "rumours/aberdeen.json") or {}
    rows = data.get("rumours") or []
    lane = data.get("former_player_mentions") or []
    result.rows_checked = len(lane)
    result.fields_checked = 2
    expected = [row for row in rows if (row.get("affiliation") or "unknown") == "former_player"]
    if len(lane) != len(expected):
        result.fail("former_player_mentions does not match former rows")
    for row in lane:
        if row.get("former_href") is None and row.get("player_href") is None:
            result.fail(f"former lane {row.get('rumour_id')} has no link")
    result.note("rumours.former_lane", result.status == "pass", f"{len(lane)} rows checked")
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
        squad_coverage = coverage.get("squad") or {}
        summary = squad.get("summary") or {}
        expected = squad_coverage.get("count")
        actual = summary.get("total_players")
        if expected is not None and actual is not None and expected != actual:
            result.fail("coverage squad count != squad summary total_players")
        if (
            squad_coverage.get("squad") is not None
            and summary.get("squad_size") is not None
            and squad_coverage.get("squad") != summary.get("squad_size")
        ):
            result.fail("coverage squad size != squad summary squad_size")
    result.note("coverage.surfaces", result.status == "pass", "coverage cross-surface checks")
    return result


def verify_loan_scope(corpus: dict[str, Any]) -> VerificationResult:
    result = VerificationResult()
    squad = _payload(corpus, "squad/aberdeen.json") or {}
    transfers = _payload(corpus, "transfers/aberdeen.json") or {}
    left = squad.get("loan_scope") or {}
    right = transfers.get("loan_scope") or {}
    if not left or left != right:
        result.fail("squad and transfer loan_scope blocks are missing or differ")
        return result
    official = left.get("official_list") or {}
    active = sum(1 for player in squad.get("players") or [] if player.get("status") == "loan_out")
    if official.get("out_count") != active:
        result.fail("loan_scope official out_count != squad loan_out rows")
    current = left.get("register_current") or {}
    if current.get("out_count") != len(current.get("out") or []):
        result.fail("loan_scope current out_count != rows")
    result.rows_checked = int(official.get("out_count") or 0)
    result.fields_checked = 4
    result.note("loan.scope", result.status == "pass", "official and register scopes reconciled")
    return result


def verify_former_summary(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    data = _payload(corpus, "former-players/aberdeen.json") or {}
    players = data.get("players") or []
    summary = data.get("summary") or {}
    result.rows_checked = len(players)
    result.fields_checked = 10
    if summary.get("total") != len(players):
        result.fail("former summary total != player rows")
    for bucket in (
        "by_exit_kind",
        "by_fee_status",
        "by_fee_basis",
        "by_exit_season",
        "by_destination",
        "by_current_status",
        "by_current_coverage",
    ):
        values = summary.get(bucket) or {}
        if values and sum(int(value) for value in values.values()) != len(players):
            result.fail(f"former summary {bucket} does not sum to players")
    for field_name in (
        "at_rival_now",
        "rival_spell",
        "at_club",
        "on_loan",
        "free_agent",
        "retired",
        "current_unknown",
        "in_covered_feed",
        "not_in_covered_feed",
    ):
        if summary.get(field_name) is not None and int(summary[field_name]) < 0:
            result.fail(f"former summary {field_name} is negative")
    if summary.get("at_club") is not None and summary.get("at_club") != sum(
        1
        for row in players
        if (row.get("post_career") or {}).get("current", {}).get("status") == "at_club"
    ):
        result.fail("former summary at_club != player rows")
    if summary.get("rival_spell") != sum(
        1 for row in players if (row.get("post_career") or {}).get("at_rival")
    ):
        result.fail("former summary rival_spell != player rows")
    result.note("former.summary", result.status == "pass", f"{len(players)} players checked")
    return result


def verify_former_players(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    data = _payload(corpus, "former-players/aberdeen.json") or {}
    transfers = _payload(corpus, "transfers/aberdeen.json") or {}
    squad = _payload(corpus, "squad/aberdeen.json") or {}
    players = data.get("players") or []
    transfer_rows = {str(row.get("transfer_id")): row for row in transfers.get("transfers") or []}
    official = {
        str(row.get("player_key")) for row in squad.get("players") or [] if row.get("player_key")
    }
    keys: set[str] = set()
    result.rows_checked = len(players)
    result.fields_checked = 4
    for row in players:
        key = str(row.get("player_key") or "")
        if not key or key in keys:
            result.fail(f"former player key missing or duplicated: {key!r}")
            continue
        keys.add(key)
        if key in official:
            result.fail(f"former player {key} is in the official squad")
        departure = row.get("departure") or {}
        transfer = transfer_rows.get(str(departure.get("transfer_id")))
        if not transfer:
            result.fail(f"former player {key} has no published departure transfer")
            continue
        if transfer.get("direction") != "out" or transfer.get("transfer_kind") not in {
            "permanent",
            "free",
        }:
            result.fail(f"former player {key} departure is not a permanent/free out")
        if not row.get("href", "").startswith("/former-players/#"):
            result.fail(f"former player {key} has no board anchor")
    result.note("former.players", result.status == "pass", f"{len(players)} players checked")
    return result


def verify_former_post_seasons(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    index = _payload(corpus, "former-players/aberdeen.json") or {}
    detail = _payload(corpus, "former-players/seasons.json") or {}
    players = {str(row.get("player_key")): row for row in index.get("players") or []}
    seasons = detail.get("seasons") or {}
    result.rows_checked = len(seasons)
    result.fields_checked = 3
    if set(seasons) != set(players):
        result.fail("former season detail keys do not match the player index")
    for key, block in seasons.items():
        rows = block.get("post_seasons") or []
        totals = ((players.get(key) or {}).get("post_career") or {}).get("totals") or {}
        for field_name in ("appearances", "starts", "minutes", "goals", "assists"):
            expected = totals.get(field_name)
            if expected is None:
                continue
            actual = sum(int(row.get(field_name) or 0) for row in rows)
            if actual != int(expected):
                result.fail(f"former {key} post {field_name} {actual} != {expected}")
        present = {str(row.get("season")) for row in rows}
        coverage = block.get("coverage") or {}
        if set(coverage.get("present_seasons") or []) != present:
            result.fail(f"former {key} present_seasons do not match rows")
    result.note("former.post", result.status == "pass", f"{len(seasons)} players checked")
    return result


def verify_former_sell_on(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    index = _payload(corpus, "former-players/aberdeen.json") or {}
    transfers = _payload(corpus, "transfers/aberdeen.json") or {}
    watch = index.get("sell_on_watch") or {}
    clauses = watch.get("clauses") or []
    summary = watch.get("summary") or {}
    transfer_clauses = {str(row.get("clause_id")) for row in transfers.get("sell_on_clauses") or []}
    result.rows_checked = len(clauses)
    result.fields_checked = 4
    if {str(row.get("clause_id")) for row in clauses} != transfer_clauses:
        result.fail("sell-on watch clauses do not match the transfer register")
    computed = 0
    known: list[float] = []
    for row in clauses:
        receipt = row.get("receipt") or {}
        if receipt.get("status") == "computed":
            computed += 1
            value = receipt.get("receipt_gbp")
            if value is None:
                result.fail(f"sell-on {row.get('clause_id')} computed without a receipt")
            else:
                known.append(float(value))
        elif receipt.get("receipt_gbp") is not None:
            result.fail(f"sell-on {row.get('clause_id')} has a receipt without computed status")
        if receipt.get("status") == "missing_inputs" and not receipt.get("missing_inputs"):
            result.fail(f"sell-on {row.get('clause_id')} missing inputs but no reason")
    if summary.get("computed") != computed:
        result.fail("sell-on summary computed != clause rows")
    expected_known = round(sum(known), -3) if known else None
    if summary.get("known_receipts_gbp") != expected_known:
        result.fail("sell-on summary known receipts != computed rows")
    result.note("former.sell_on", result.status == "pass", f"{len(clauses)} clauses checked")
    return result


def verify_former_scorecard(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    index = _payload(corpus, "former-players/aberdeen.json") or {}
    players = index.get("players") or []
    scorecard = index.get("development_scorecard") or {}
    result.rows_checked = len(players)
    result.fields_checked = 3
    cohorts = scorecard.get("cohorts") or {}
    if int((cohorts.get("all") or {}).get("players") or 0) != len(players):
        result.fail("development scorecard all cohort != players")
    by_season = scorecard.get("by_exit_season") or []
    if by_season and sum(int(row.get("players") or 0) for row in by_season) != len(players):
        result.fail("development scorecard by_exit_season does not sum to players")
    young = sum(
        1
        for row in players
        if row.get("age_at_exit") is not None
        and int(row["age_at_exit"])
        <= int((scorecard.get("definitions") or {}).get("young_exit_age_max") or 23)
    )
    if int((cohorts.get("young") or {}).get("players") or 0) != young:
        result.fail("development scorecard young cohort mismatch")
    result.note("former.scorecard", result.status == "pass", f"{len(players)} players checked")
    return result


def verify_former_coverage(corpus: dict[str, Any], _: Any = None) -> VerificationResult:
    result = VerificationResult()
    index = _payload(corpus, "former-players/aberdeen.json") or {}
    coverage_payload = _payload(corpus, "coverage.json") or {}
    coverage = index.get("coverage") or {}
    counts = coverage.get("counts") or {}
    players = index.get("players") or []
    result.rows_checked = len(players)
    result.fields_checked = 4
    if counts.get("players") != len(players):
        result.fail("former coverage players != player rows")
    if int(counts.get("with_api_id") or 0) + int(counts.get("without_api_id") or 0) != len(players):
        result.fail("former coverage API ids do not sum to players")
    if int(counts.get("with_post_career_rows") or 0) + int(
        counts.get("without_post_career_rows") or 0
    ) != len(players):
        result.fail("former coverage post rows do not sum to players")
    block = coverage_payload.get("former_players") or {}
    if block.get("count") != len(players):
        result.fail("coverage.json former count != former player rows")
    result.note("former.coverage", result.status == "pass", f"{len(players)} players checked")
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
    "fitba.metrics.checks:verify_loan_scope": verify_loan_scope,
    "fitba.metrics.checks:verify_former_summary": verify_former_summary,
    "fitba.metrics.checks:verify_former_players": verify_former_players,
    "fitba.metrics.checks:verify_former_post_seasons": verify_former_post_seasons,
    "fitba.metrics.checks:verify_former_sell_on": verify_former_sell_on,
    "fitba.metrics.checks:verify_former_scorecard": verify_former_scorecard,
    "fitba.metrics.checks:verify_former_coverage": verify_former_coverage,
    "fitba.metrics.checks:verify_rumours_summary": verify_rumours_summary,
    "fitba.metrics.checks:verify_forum_former_profile": verify_forum_former_profile,
    "fitba.metrics.checks:verify_rumours_former_lane": verify_rumours_former_lane,
    "fitba.metrics.checks:verify_coverage": verify_coverage,
}
