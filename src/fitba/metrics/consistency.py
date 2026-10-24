"""Cross-surface consistency checks over the published corpus.

A metric audit proves one value was computed as registered. This module proves
the same fact has not been re-derived into a different value on another
surface. It deliberately reads only published JSON and config; it never runs a
publish calculation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckOutcome:
    status: str = "pass"
    rows_checked: int = 0
    fields_checked: int = 0
    errors: list[str] = field(default_factory=list)

    def fail(self, message: str) -> None:
        self.status = "fail"
        self.errors.append(message)


@dataclass
class CheckResult:
    id: str
    description: str
    status: str
    rows_checked: int = 0
    fields_checked: int = 0
    errors: list[str] = field(default_factory=list)
    payloads: list[str] = field(default_factory=list)


def _payload(corpus: dict[str, Any], path: str) -> Any:
    return corpus.get(path)


def _players(squad: dict[str, Any]) -> list[dict[str, Any]]:
    return list(squad.get("players") or [])


def _check(
    check_id: str,
    description: str,
    corpus: dict[str, Any],
    payloads: list[str],
    function,
) -> CheckResult:
    outcome = CheckOutcome()
    try:
        function(corpus, outcome)
    except Exception as error:  # noqa: BLE001 - a broken payload is a failed check
        outcome.fail(f"{type(error).__name__}: {error}")
    return CheckResult(
        id=check_id,
        description=description,
        status=outcome.status,
        rows_checked=outcome.rows_checked,
        fields_checked=outcome.fields_checked,
        errors=outcome.errors,
        payloads=payloads,
    )


def _check_squad_counts(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    squad = _payload(corpus, "squad/aberdeen.json") or {}
    players = _players(squad)
    excluded = list(squad.get("excluded_players") or [])
    summary = squad.get("summary") or {}
    outcome.rows_checked = len(players) + len(excluded)
    outcome.fields_checked = 6
    if summary.get("total_players") != len(players):
        outcome.fail(
            f"squad summary total_players {summary.get('total_players')} != {len(players)}"
        )
    if summary.get("official_players") != len(players):
        outcome.fail(
            f"squad summary official_players {summary.get('official_players')} != {len(players)}"
        )
    expected_squad = sum(1 for player in players if player.get("status") != "loan_out")
    if summary.get("squad_size") != expected_squad:
        outcome.fail(f"squad_size {summary.get('squad_size')} != {expected_squad}")
    expected_loans = sum(1 for player in players if player.get("status") == "loan_out")
    if summary.get("loans_out") != expected_loans:
        outcome.fail(f"loans_out {summary.get('loans_out')} != {expected_loans}")
    expected_excluded = len(excluded)
    if summary.get("excluded_api") != expected_excluded:
        outcome.fail(f"excluded_api {summary.get('excluded_api')} != {expected_excluded}")
    if (
        summary.get("official_players") is not None
        and summary.get("official_squad_size") is not None
        and summary["official_squad_size"] + summary["loans_out"]
        != summary["official_players"]
    ):
        outcome.fail("official_squad_size + loans_out != official_players")
    for field_name, attr in (
        ("by_primary_group_squad", "squad_size"),
        ("by_role_family_squad", "squad_size"),
    ):
        values = summary.get(field_name) or {}
        if sum(int(value) for value in values.values()) != summary.get(attr):
            outcome.fail(f"{field_name} does not sum to {attr}")
    for field_name in ("by_primary_group", "by_role_family", "by_status", "by_position"):
        values = summary.get(field_name) or {}
        if values and sum(int(value) for value in values.values()) != len(players):
            outcome.fail(f"{field_name} does not sum to official players")


def _check_roster(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    squad = _payload(corpus, "squad/aberdeen.json") or {}
    meta = squad.get("roster_meta") or {}
    players = _players(squad)
    outcome.rows_checked = len(players)
    outcome.fields_checked = 4
    if meta.get("status") != "available":
        return
    expected = sum(
        1
        for player in players
        if player.get("roster_status") in {"official", "official_loan"}
    )
    if meta.get("official_players") != expected:
        outcome.fail(f"roster_meta official_players {meta.get('official_players')} != {expected}")
    if int(meta.get("matched") or 0) + int(meta.get("ambiguous") or 0) != int(
        meta.get("official_players") or 0
    ):
        outcome.fail("roster_meta matched + ambiguous != official_players")
    if meta.get("excluded_api") != len(squad.get("excluded_players") or []):
        outcome.fail("roster_meta excluded_api != excluded_players length")


def _check_loans(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    squad = _payload(corpus, "squad/aberdeen.json") or {}
    transfers = _payload(corpus, "transfers/aberdeen.json") or {}
    scope = squad.get("loan_scope") or transfers.get("loan_scope") or {}
    outcome.rows_checked = len(scope.get("official_list", {}).get("out") or [])
    outcome.fields_checked = 6
    if not scope:
        outcome.fail("loan_scope is missing from squad and transfers payloads")
        return
    if scope != (transfers.get("loan_scope") or scope):
        outcome.fail("squad and transfers loan_scope blocks differ")
    official = scope.get("official_list") or {}
    current = scope.get("register_current") or {}
    all_time = scope.get("register_all_time") or {}
    for label, block in (
        ("official_list", official),
        ("register_current", current),
        ("register_all_time", all_time),
    ):
        for direction in ("out", "in"):
            rows = block.get(direction)
            if rows is not None and block.get(f"{direction}_count") != len(rows):
                outcome.fail(f"{label}.{direction}_count != {direction} rows")
    squad_loans = sum(1 for player in _players(squad) if player.get("status") == "loan_out")
    if official.get("out_count") != squad_loans:
        outcome.fail(f"official loan count {official.get('out_count')} != squad {squad_loans}")
    register_keys = {
        str(item.get("player_key"))
        for item in current.get("out") or []
        if item.get("player_key")
    }
    for player in _players(squad):
        if player.get("status") != "loan_out":
            continue
        if str(player.get("player_key")) not in register_keys:
            outcome.fail(
                f"official loanee {player.get('name')} is not in the current register"
            )


def _totals_from_stats(rows: list[dict[str, Any]], scope: str) -> dict[str, Any] | None:
    items = [row for row in rows if row.get("scope") == scope]
    if not items:
        return None
    fields = ("appearances", "starts", "minutes", "goals", "assists")
    output: dict[str, Any] = {}
    for field_name in fields:
        values = [row.get(field_name) for row in items if row.get(field_name) is not None]
        output[field_name] = sum(int(value or 0) for value in values) if values else None
    return output


def _check_player_totals(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    squad = _payload(corpus, "squad/aberdeen.json") or {}
    for player in _players(squad):
        if player.get("squad_member") is False:
            continue
        outcome.rows_checked += 1
        outcome.fields_checked += 5
        expected = _totals_from_stats(player.get("stats") or [], "club")
        totals = player.get("totals")
        if expected is None:
            if totals is not None:
                outcome.fail(f"{player.get('name')}: club totals without club rows")
            continue
        if totals is None:
            outcome.fail(f"{player.get('name')}: club rows without club totals")
            continue
        for field_name, value in expected.items():
            if int(totals.get(field_name) or 0) != int(value or 0):
                outcome.fail(
                    f"{player.get('name')}: totals {field_name} {totals.get(field_name)} != {value}"
                )
        playing = player.get("playing_time") or {}
        by_comp = playing.get("by_competition") or []
        if by_comp:
            if sum(int(row.get("minutes") or 0) for row in by_comp) != int(
                playing.get("minutes") or 0
            ):
                outcome.fail(f"{player.get('name')}: playing-time minutes do not sum")
            if sum(int(row.get("starts") or 0) for row in by_comp) != int(
                playing.get("starts") or 0
            ):
                outcome.fail(f"{player.get('name')}: playing-time starts do not sum")


def _check_player_pages(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    squad = _payload(corpus, "squad/aberdeen.json") or {}
    expected_ids = {
        str(player.get("player_id"))
        for player in [
            *_players(squad),
            *(squad.get("excluded_players") or []),
        ]
    }
    page_ids = {
        key.split("/", 1)[1].removesuffix(".json")
        for key in corpus
        if key.startswith("players/") and key.endswith(".json")
    }
    outcome.rows_checked = len(expected_ids)
    outcome.fields_checked = 4
    if expected_ids != page_ids:
        outcome.fail(
            f"player page ids differ: missing={sorted(expected_ids - page_ids)[:5]} "
            f"extra={sorted(page_ids - expected_ids)[:5]}"
        )
    squad_by_id = {int(player["player_id"]): player for player in _players(squad)}
    for key in sorted(page_ids):
        page = corpus.get(f"players/{key}.json") or {}
        player_id = int(page.get("player_id") or key)
        player = squad_by_id.get(player_id)
        if player is None:
            continue
        summary = ((page.get("panels") or {}).get("profile") or {}).get("data", {}).get(
            "summary"
        ) or {}
        totals = player.get("totals") or {}
        if summary.get("minutes") is not None:
            event_minutes = int((player.get("playing_time") or {}).get("minutes") or 0)
            if int(summary.get("minutes") or 0) != event_minutes:
                outcome.fail(
                    f"player {key}: summary minutes {summary.get('minutes')} != "
                    f"squad event minutes {event_minutes}"
                )
        if (
            totals
            and summary.get("rating") is not None
            and totals.get("rating") is not None
            and abs(float(summary["rating"]) - float(totals["rating"])) > 0.011
        ):
            outcome.fail(
                f"player {key}: summary rating {summary['rating']} != "
                f"squad rating {totals['rating']}"
            )


def _check_xg(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    xg = _payload(corpus, "xg/aberdeen.json") or {}
    matches = [row for row in xg.get("matches") or [] if row.get("fxg_for") is not None]
    league = [row for row in matches if row.get("competition_id") == "sco:premiership"]
    outcome.rows_checked = len(matches)
    outcome.fields_checked = 6
    by_season: dict[str, list[dict[str, Any]]] = {}
    for row in league:
        by_season.setdefault(str(row.get("season")), []).append(row)
    for aggregate in xg.get("aggregates") or []:
        if aggregate.get("scope") != "season":
            continue
        season = str(aggregate.get("season"))
        rows = by_season.get(season)
        if rows is None:
            outcome.fail(f"xg aggregate {season} has no match rows")
            continue
        checks = {
            "matches": len(rows),
            "fxg": round(sum(float(row["fxg_for"]) for row in rows), 2),
            "goals": sum(int(row.get("goals_for") or 0) for row in rows),
            "shots": sum(int(row.get("shots_for") or 0) for row in rows),
            "shots_on_target": sum(
                int(row.get("shots_on_target_for") or 0) for row in rows
            ),
            "penalties": sum(int(row.get("penalties_for") or 0) for row in rows),
        }
        for field_name, expected in checks.items():
            actual = aggregate.get(field_name)
            if actual is None:
                continue
            if abs(float(actual) - float(expected)) > (0.02 if field_name == "fxg" else 0):
                outcome.fail(f"xg {season} {field_name} {actual} != match sum {expected}")
    for row in xg.get("aggregates") or []:
        if row.get("scope") == "era":
            expected_fxg = round(sum(float(item["fxg_for"]) for item in league), 2)
            if abs(float(row.get("fxg") or 0) - expected_fxg) > 0.02:
                outcome.fail(f"xg era fxg {row.get('fxg')} != league sum {expected_fxg}")
            if int(row.get("matches") or 0) != len(league):
                outcome.fail("xg era matches != league match rows")


def _check_xg_fixtures(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    xg = _payload(corpus, "xg/aberdeen.json") or {}
    rows = {
        int(row["fixture_id"]): row
        for row in xg.get("matches") or []
        if row.get("fixture_id") is not None
    }
    for key, page in corpus.items():
        if not key.startswith("matches/") or not key.endswith(".json"):
            continue
        fixture = page.get("fixture") or {}
        fixture_id = fixture.get("fixture_id")
        if fixture_id not in rows:
            continue
        outcome.rows_checked += 1
        outcome.fields_checked += 2
        block = page.get("xg") or {}
        row = rows[fixture_id]
        if block.get("available") and block.get("for") and block.get("against"):
            for side, prefix in (("for", "for"), ("against", "against")):
                value = (block.get(side) or {}).get("value")
                expected = row.get(f"fxg_{prefix}")
                if (
                    value is not None
                    and expected is not None
                    and abs(float(value) - float(expected)) > 0.001
                ):
                    outcome.fail(
                        f"fixture {fixture_id} xg {side} {value} != payload {expected}"
                    )


def _check_results(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    fixtures = _payload(corpus, "fixtures/index.json") or {}
    for row in fixtures.get("fixtures") or []:
        outcome.rows_checked += 1
        outcome.fields_checked += 3
        fixture_id = row.get("fixture_id")
        page = corpus.get(f"matches/{fixture_id}.json") or {}
        document = page.get("fixture") or {}
        if not document:
            continue
        if row.get("aberdeen_result") != document.get("aberdeen_result"):
            outcome.fail(f"fixture {fixture_id}: result differs from match page")
        if document.get("decided_by") == "penalties":
            if document.get("aberdeen_result") != "D":
                outcome.fail(f"fixture {fixture_id}: shootout regulation result is not D")
            if document.get("aberdeen_result_label", "").startswith("D") is False:
                outcome.fail(f"fixture {fixture_id}: shootout label does not preserve D")
            if not document.get("shootout_result"):
                outcome.fail(f"fixture {fixture_id}: shootout has no outcome")


def _check_schedule(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    fixtures = _payload(corpus, "fixtures/index.json") or {}
    scheduled = fixtures.get("scheduled") or []
    outcome.rows_checked = len(scheduled)
    outcome.fields_checked = 3
    expected = sum(1 for row in scheduled if row.get("status") == "scheduled")
    if fixtures.get("scheduled_count") != expected:
        outcome.fail(
            f"scheduled_count {fixtures.get('scheduled_count')} != scheduled rows {expected}"
        )
    expected_conflicts = sum(
        1 for row in scheduled if row.get("status") == "conflict_review"
    )
    if fixtures.get("conflict_count") != expected_conflicts:
        outcome.fail(
            f"conflict_count {fixtures.get('conflict_count')} != {expected_conflicts}"
        )
    matchday = _payload(corpus, "matchday/upcoming.json") or {}
    fixture = matchday.get("fixture") or {}
    if fixture and scheduled:
        confirmed = [
            row
            for row in scheduled
            if row.get("status") == "scheduled"
        ]
        if confirmed:
            first = min(
                confirmed,
                key=lambda row: (str(row.get("date") or ""), str(row.get("kickoff") or "")),
            )
            if str(fixture.get("date")) != str(first.get("date")):
                outcome.fail(
                    f"matchday fixture {fixture.get('date')} != first scheduled {first.get('date')}"
                )


def _check_availability(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    availability = _payload(corpus, "availability/aberdeen.json") or {}
    universes = availability.get("universes") or {}
    outcome.rows_checked = len(availability.get("entries") or [])
    outcome.fields_checked = 4
    if not universes:
        outcome.fail("availability universes are missing")
        return
    for name in ("official_list", "active_squad"):
        block = universes.get(name) or {}
        if block.get("known") is None or block.get("unknown") is None:
            outcome.fail(f"availability {name} has no known/unknown counts")
            continue
        if int(block["known"]) + int(block["unknown"]) != int(block.get("players") or 0):
            outcome.fail(f"availability {name}: known + unknown != players")
    coverage = availability.get("coverage") or {}
    if coverage.get("entries") != len(availability.get("entries") or []):
        outcome.fail("availability coverage entries != entries length")


def _check_coverage(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    coverage = _payload(corpus, "coverage.json") or {}
    squad = _payload(corpus, "squad/aberdeen.json") or {}
    transfers = _payload(corpus, "transfers/aberdeen.json") or {}
    outcome.fields_checked = 3
    squad_coverage = coverage.get("squad") or {}
    summary = squad.get("summary") or {}
    transfer_coverage = coverage.get("transfers") or {}
    if squad_coverage.get("count") != summary.get("total_players"):
        outcome.fail("coverage squad count != squad summary total_players")
    if squad_coverage.get("squad") != summary.get("squad_size"):
        outcome.fail("coverage squad size != squad summary squad_size")
    if squad_coverage.get("loans_out") != summary.get("loans_out"):
        outcome.fail("coverage loans_out != squad summary loans_out")
    if transfer_coverage.get("count") != (transfers.get("summary") or {}).get("total"):
        outcome.fail("coverage transfer count != transfers summary total")
    availability = coverage.get("availability") or {}
    if not availability.get("universes"):
        outcome.fail("coverage availability universes are missing")


CHECKS = [
    (
        "squad.counts",
        "Squad summary and role buckets reconcile with player rows",
        ["squad/aberdeen.json"],
        _check_squad_counts,
    ),
    (
        "squad.roster",
        "Official roster metadata reconciles with player rows",
        ["squad/aberdeen.json"],
        _check_roster,
    ),
    (
        "loans.scopes",
        "Official and register loan counts are separate and reconciled",
        ["squad/aberdeen.json", "transfers/aberdeen.json"],
        _check_loans,
    ),
    (
        "players.totals",
        "Squad totals and playing time reconcile with their source rows",
        ["squad/aberdeen.json"],
        _check_player_totals,
    ),
    (
        "players.pages",
        "Player pages use the same minutes and rating as the squad payload",
        ["squad/aberdeen.json", "players/*.json"],
        _check_player_pages,
    ),
    (
        "xg.aggregates",
        "xG aggregates equal the sum of their match rows",
        ["xg/aberdeen.json"],
        _check_xg,
    ),
    (
        "xg.fixtures",
        "Fixture xG equals the xG payload row",
        ["xg/aberdeen.json", "matches/*.json"],
        _check_xg_fixtures,
    ),
    (
        "results.shootouts",
        "Fixture results and shootout labels agree with match pages",
        ["fixtures/index.json", "matches/*.json"],
        _check_results,
    ),
    (
        "fixtures.schedule",
        "Scheduled counts and the matchday fixture use the same schedule rule",
        ["fixtures/index.json", "matchday/upcoming.json"],
        _check_schedule,
    ),
    (
        "availability.universes",
        "Availability counts reconcile to their declared universes",
        ["availability/aberdeen.json"],
        _check_availability,
    ),
    (
        "coverage.counts",
        "Coverage counts equal the payloads they summarise",
        ["coverage.json", "squad/aberdeen.json", "transfers/aberdeen.json"],
        _check_coverage,
    ),
]


def run_consistency(corpus: dict[str, Any]) -> list[CheckResult]:
    return [
        _check(check_id, description, corpus, payloads, function)
        for check_id, description, payloads, function in CHECKS
    ]


__all__ = ["CHECKS", "CheckOutcome", "CheckResult", "run_consistency"]
