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
        and summary["official_squad_size"] + summary["loans_out"] != summary["official_players"]
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
        1 for player in players if player.get("roster_status") in {"official", "official_loan"}
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
        str(item.get("player_key")) for item in current.get("out") or [] if item.get("player_key")
    }
    for player in _players(squad):
        if player.get("status") != "loan_out":
            continue
        if str(player.get("player_key")) not in register_keys:
            outcome.fail(f"official loanee {player.get('name')} is not in the current register")


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
            "shots_on_target": sum(int(row.get("shots_on_target_for") or 0) for row in rows),
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
                    outcome.fail(f"fixture {fixture_id} xg {side} {value} != payload {expected}")


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
    expected_conflicts = sum(1 for row in scheduled if row.get("status") == "conflict_review")
    if fixtures.get("conflict_count") != expected_conflicts:
        outcome.fail(f"conflict_count {fixtures.get('conflict_count')} != {expected_conflicts}")
    matchday = _payload(corpus, "matchday/upcoming.json") or {}
    fixture = matchday.get("fixture") or {}
    if fixture and scheduled:
        confirmed = [row for row in scheduled if row.get("status") == "scheduled"]
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


def _check_former_register(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    former = _payload(corpus, "former-players/aberdeen.json") or {}
    transfers = _payload(corpus, "transfers/aberdeen.json") or {}
    squad = _payload(corpus, "squad/aberdeen.json") or {}
    players = former.get("players") or []
    summary = former.get("summary") or {}
    transfer_rows = {str(row.get("transfer_id")): row for row in transfers.get("transfers") or []}
    official = {
        str(row.get("player_key")) for row in squad.get("players") or [] if row.get("player_key")
    }
    outcome.rows_checked = len(players)
    outcome.fields_checked = 5
    if summary.get("total") != len(players):
        outcome.fail("former summary total != player rows")
    keys = [str(row.get("player_key")) for row in players]
    if len(keys) != len(set(keys)):
        outcome.fail("former player keys are not unique")
    for row in players:
        key = str(row.get("player_key") or "")
        if key in official:
            outcome.fail(f"former player {key} is in the official squad")
        departure = row.get("departure") or {}
        transfer = transfer_rows.get(str(departure.get("transfer_id")))
        if not transfer:
            outcome.fail(f"former player {key} has no published departure")
            continue
        if transfer.get("direction") != "out" or transfer.get("transfer_kind") not in {
            "permanent",
            "free",
        }:
            outcome.fail(f"former player {key} departure is not permanent/free")


def _check_former_post(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    former = _payload(corpus, "former-players/aberdeen.json") or {}
    detail = _payload(corpus, "former-players/seasons.json") or {}
    players = {str(row.get("player_key")): row for row in former.get("players") or []}
    seasons = detail.get("seasons") or {}
    outcome.rows_checked = len(seasons)
    outcome.fields_checked = 3
    if set(seasons) != set(players):
        outcome.fail("former season detail keys do not match the index")
    for key, block in seasons.items():
        rows = block.get("post_seasons") or []
        totals = ((players.get(key) or {}).get("post_career") or {}).get("totals") or {}
        for field_name in ("appearances", "starts", "minutes", "goals", "assists"):
            expected = totals.get(field_name)
            if expected is None:
                continue
            actual = sum(int(row.get(field_name) or 0) for row in rows)
            if actual != int(expected):
                outcome.fail(f"former {key} {field_name} {actual} != {expected}")


def _check_former_sell_on(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    former = _payload(corpus, "former-players/aberdeen.json") or {}
    transfers = _payload(corpus, "transfers/aberdeen.json") or {}
    watch = former.get("sell_on_watch") or {}
    clauses = watch.get("clauses") or []
    summary = watch.get("summary") or {}
    transfer_ids = {str(row.get("clause_id")) for row in transfers.get("sell_on_clauses") or []}
    outcome.rows_checked = len(clauses)
    outcome.fields_checked = 3
    if {str(row.get("clause_id")) for row in clauses} != transfer_ids:
        outcome.fail("sell-on watch clauses do not match the transfer register")
    computed = 0
    for row in clauses:
        receipt = row.get("receipt") or {}
        if receipt.get("status") == "computed":
            computed += 1
            if receipt.get("receipt_gbp") is None:
                outcome.fail(f"sell-on {row.get('clause_id')} computed without a receipt")
        elif receipt.get("receipt_gbp") is not None:
            outcome.fail(f"sell-on {row.get('clause_id')} has a receipt without computed status")
    if summary.get("computed") != computed:
        outcome.fail("sell-on summary computed != clauses")


def _check_former_affiliation(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    rumours = _payload(corpus, "rumours/aberdeen.json") or {}
    forum = _payload(corpus, "forum/afc_chat.json") or {}
    profile = _payload(corpus, "rumours/profile.json") or {}
    rows = rumours.get("rumours") or []
    signals = forum.get("signals") or []
    outcome.rows_checked = len(rows) + len(signals)
    outcome.fields_checked = 4
    for row in rows:
        affiliation = str(row.get("affiliation") or "unknown")
        if (
            row.get("direction") == "in"
            and row.get("is_target")
            and affiliation != "external_target"
        ):
            outcome.fail(f"rumour {row.get('rumour_id')} is a target outside external_target")
        if row.get("is_return_link") and affiliation != "former_player":
            outcome.fail(f"rumour {row.get('rumour_id')} return link is not former_player")
    target_ids = {
        str(row.get("rumour_id"))
        for row in rows
        if row.get("status") == "active"
        and row.get("direction") == "in"
        and str(row.get("affiliation") or "unknown") == "external_target"
    }
    profile_ids = {str(row.get("rumour_id")) for row in profile.get("signals") or []}
    if profile_ids - target_ids:
        outcome.fail("target profile contains a non-external row")
    mix = (forum.get("profile") or {}).get("affiliation_mix") or {}
    if sum(int(value) for value in mix.values()) != len(signals):
        outcome.fail("forum affiliation_mix does not sum to signals")


def _check_former_coverage(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    former = _payload(corpus, "former-players/aberdeen.json") or {}
    coverage_payload = _payload(corpus, "coverage.json") or {}
    counts = (former.get("coverage") or {}).get("counts") or {}
    players = former.get("players") or []
    outcome.rows_checked = len(players)
    outcome.fields_checked = 3
    if counts.get("players") != len(players):
        outcome.fail("former coverage players != player rows")
    if int(counts.get("with_api_id") or 0) + int(counts.get("without_api_id") or 0) != len(players):
        outcome.fail("former coverage API ids do not sum to players")
    block = coverage_payload.get("former_players") or {}
    if block.get("count") != len(players):
        outcome.fail("coverage.json former count != former rows")


def _table_documents(corpus: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return sorted(
        (path, payload)
        for path, payload in corpus.items()
        if path.startswith("tables/") and isinstance(payload, dict)
    )


def _aberdeen_table_row(corpus: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    for path, payload in _table_documents(corpus):
        for row in payload.get("rows") or []:
            if str(row.get("team_id")) == "sco:aberdeen":
                return path, row
    return None


def _league_fixture_rows(corpus: dict[str, Any], season: str) -> list[dict[str, Any]]:
    index = _payload(corpus, "fixtures/index.json") or {}
    rows = []
    for row in index.get("fixtures") or []:
        if str(row.get("season")) != season:
            continue
        if str(row.get("competition_id")) != "sco:premiership":
            continue
        if row.get("home_goals") is None or row.get("away_goals") is None:
            continue
        home = bool(row.get("aberdeen_is_home"))
        goals_for = int(row.get("home_goals") if home else row.get("away_goals"))
        goals_against = int(row.get("away_goals") if home else row.get("home_goals"))
        result = "W" if goals_for > goals_against else "D" if goals_for == goals_against else "L"
        rows.append(
            {
                "date": str(row.get("date") or "")[:10],
                "opponent_name": row.get("away_team_name") if home else row.get("home_team_name"),
                "venue": "H" if home else "A",
                "gf": goals_for,
                "ga": goals_against,
                "result": result,
            }
        )
    rows.sort(key=lambda item: item["date"], reverse=True)
    return rows


def _record(rows: list[dict[str, Any]]) -> dict[str, Any]:
    recent = rows[:5]
    return {
        "played": len(rows),
        "won": sum(1 for row in rows if row["result"] == "W"),
        "drawn": sum(1 for row in rows if row["result"] == "D"),
        "lost": sum(1 for row in rows if row["result"] == "L"),
        "gf": sum(row["gf"] for row in rows),
        "ga": sum(row["ga"] for row in rows),
        "gd": sum(row["gf"] - row["ga"] for row in rows),
        "points": sum(
            3 if row["result"] == "W" else 1 if row["result"] == "D" else 0 for row in rows
        ),
        "form": "".join(row["result"] for row in recent),
    }


def _check_results_table(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    found = _aberdeen_table_row(corpus)
    if found is None:
        outcome.fail("no table contains an Aberdeen row")
        return
    path, row = found
    season = str(row.get("season") or "")
    rows = _league_fixture_rows(corpus, season)
    expected = _record(rows)
    for name, value in expected.items():
        outcome.fields_checked += 1
        if row.get(name) != value:
            outcome.fail(f"{path}: Aberdeen {name} {row.get(name)!r} != fixtures {value!r}")
    outcome.rows_checked = len(rows)


def _check_results_form(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    found = _aberdeen_table_row(corpus)
    if found is None:
        outcome.fail("no table contains an Aberdeen row")
        return
    _, table_row = found
    expected = _record(_league_fixture_rows(corpus, str(table_row.get("season") or "")))
    surfaces: list[tuple[str, dict[str, Any]]] = []
    matchday = _payload(corpus, "matchday/upcoming.json") or {}
    form = (matchday.get("form_guide") or {}).get("aberdeen")
    if isinstance(form, dict):
        surfaces.append(("matchday/upcoming.json:form_guide", form))
    analysis = _payload(corpus, "analysis/summary.json") or {}
    hero = analysis.get("hero")
    if isinstance(hero, dict):
        surfaces.append(("analysis/summary.json:hero", hero))
    club = _payload(corpus, "clubs/aberdeen.json") or {}
    summary = club.get("summary")
    if isinstance(summary, dict):
        surfaces.append(("clubs/aberdeen.json:summary", summary))
    for path, surface in surfaces:
        for name in ("played", "won", "drawn", "lost", "gf", "ga", "form"):
            if name not in surface:
                continue
            outcome.fields_checked += 1
            if surface.get(name) != expected[name]:
                outcome.fail(f"{path} {name} {surface.get(name)!r} != {expected[name]!r}")
        if "gd" in surface:
            outcome.fields_checked += 1
            if surface.get("gd") != expected["gd"]:
                outcome.fail(f"{path} gd {surface.get('gd')!r} != {expected['gd']!r}")
        if "points" in surface:
            outcome.fields_checked += 1
            if surface.get("points") != expected["points"]:
                outcome.fail(f"{path} points {surface.get('points')!r} != {expected['points']!r}")
        outcome.rows_checked += 1
    sample = (form or {}).get("sample") if isinstance(form, dict) else None
    if isinstance(sample, dict) and "season_matches" in sample:
        outcome.fields_checked += 1
        if sample.get("season_matches") != expected["played"]:
            outcome.fail(
                f"matchday form sample {sample.get('season_matches')} "
                f"!= table played {expected['played']}"
            )


def _check_results_club(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    club = _payload(corpus, "clubs/aberdeen.json") or {}
    found = _aberdeen_table_row(corpus)
    if found is None:
        outcome.fail("no table contains an Aberdeen row")
        return
    _, table_row = found
    season = str(table_row.get("season") or "")
    expected_rows = _league_fixture_rows(corpus, season)
    published = [
        row
        for row in club.get("results") or []
        if str(row.get("competition_id")) == "sco:premiership"
    ]
    published.sort(key=lambda item: str(item.get("date") or "")[:10], reverse=True)
    if len(published) != len(expected_rows):
        outcome.fail(
            f"clubs/aberdeen.json results {len(published)} league rows != fixtures "
            f"{len(expected_rows)}"
        )
    for actual, expected in zip(published, expected_rows, strict=False):
        outcome.rows_checked += 1
        for name in ("date", "opponent_name", "venue", "gf", "ga", "result"):
            outcome.fields_checked += 1
            actual_name = (
                "goals_for" if name == "gf" else "goals_against" if name == "ga" else name
            )
            if actual.get(actual_name) != expected[name]:
                outcome.fail(
                    f"clubs/aberdeen.json results {name} {actual.get(actual_name)!r} "
                    f"!= fixtures {expected[name]!r}"
                )
    recent = [
        row
        for row in club.get("recent_results") or []
        if str(row.get("competition_id")) == "sco:premiership"
    ]
    for index, row in enumerate(recent[: len(published)]):
        outcome.fields_checked += 1
        reference = published[index]
        same = (
            str(row.get("date") or "")[:10] == str(reference.get("date") or "")[:10]
            and row.get("opponent_name") == reference.get("opponent_name")
            and row.get("venue") == reference.get("venue")
            and row.get("goals_for") == reference.get("goals_for")
            and row.get("goals_against") == reference.get("goals_against")
            and row.get("result") == reference.get("result")
        )
        if not same:
            outcome.fail("clubs/aberdeen.json recent_results does not match results")
            break
    history_rows = [row for row in club.get("history") or [] if row.get("season") == season]
    if history_rows:
        for name in ("played", "won", "drawn", "lost", "gf", "ga", "points", "form"):
            if name not in history_rows[0]:
                continue
            outcome.fields_checked += 1
            if history_rows[0].get(name) != table_row.get(name):
                outcome.fail(
                    f"clubs/aberdeen.json history {name} "
                    f"{history_rows[0].get(name)!r} != table {table_row.get(name)!r}"
                )
    else:
        outcome.fail(f"clubs/aberdeen.json history has no {season} row")
    season_doc = _payload(corpus, f"history/seasons/{season}.json") or {}
    managers = season_doc.get("managers") or []
    if managers:
        totals = {
            name: sum(int(row.get(name) or 0) for row in managers)
            for name in ("played", "won", "drawn", "lost", "gf", "ga", "points")
        }
        for name, value in totals.items():
            outcome.fields_checked += 1
            if value != table_row.get(name):
                outcome.fail(
                    f"history/seasons/{season}.json managers {name} {value} "
                    f"!= table {table_row.get(name)}"
                )
        latest = max((str(row.get("last_match") or "") for row in managers), default="")
        if expected_rows and latest != expected_rows[0]["date"]:
            outcome.fail(
                f"history manager last_match {latest!r} "
                f"!= latest fixture {expected_rows[0]['date']!r}"
            )
    else:
        outcome.fail(f"history/seasons/{season}.json has no manager record")


def _check_results_coverage(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    coverage = _payload(corpus, "coverage.json") or {}
    table_docs = dict(_table_documents(corpus))
    for row in coverage.get("competitions") or []:
        competition_id = str(row.get("id") or "")
        table = next(
            (
                payload
                for payload in table_docs.values()
                if str(payload.get("competition_id")) == competition_id
            ),
            None,
        )
        if table is None:
            continue
        played_sum = sum(int(team.get("played") or 0) for team in table.get("rows") or [])
        outcome.rows_checked += 1
        outcome.fields_checked += 2
        if played_sum % 2 != 0:
            outcome.fail(f"coverage {competition_id}: table played sum {played_sum} is odd")
        matches = int(row.get("matches") or 0)
        if matches != played_sum // 2:
            outcome.fail(
                f"coverage {competition_id} matches {matches} != table matches {played_sum // 2}"
            )
        if row.get("season") is not None and str(row.get("season")) != str(table.get("season")):
            outcome.fail(f"coverage {competition_id} season != table season")


def _parse_time(value: Any):
    from datetime import UTC, datetime

    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _entity_id(entity: dict[str, Any]) -> str:
    value = str(entity.get("entity_id") or "")
    if value:
        return value
    compact = str(entity.get("i") or "")
    return f"player:api:player:{compact}" if compact else ""


def _entity_documents(corpus: dict[str, Any]) -> list[tuple[str, list[dict[str, Any]]]]:
    index = _payload(corpus, "entities/index.json") or {}
    scouted = _payload(corpus, "entities/scouted.json") or {}
    return [
        ("entities/index.json", list(index.get("entities") or [])),
        ("entities/scouted.json", list(scouted.get("entities") or [])),
    ]


def _check_semantic_entities(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    seen: dict[str, str] = {}
    aliases: dict[str, str] = {}
    external: dict[tuple[str, str], str] = {}
    core_ids: set[str] = set()
    for name, entities in _entity_documents(corpus):
        for entity in entities:
            entity_id = _entity_id(entity)
            outcome.rows_checked += 1
            if not entity_id:
                outcome.fail(f"{name}: entity without an id")
                continue
            if name == "entities/index.json":
                core_ids.add(entity_id)
            previous = seen.get(entity_id)
            if previous is not None:
                outcome.fail(f"{name}: duplicate entity id {entity_id}")
            seen[entity_id] = name
            kind = str(entity.get("type") or "player")
            outcome.fields_checked += 2
            if not entity_id.startswith(f"{kind}:"):
                outcome.fail(f"{name}: {entity_id}: id does not match type {kind}")
            href = entity.get("href")
            if entity.get("indexable") and not (
                isinstance(href, str) and href.startswith("/")
            ):
                outcome.fail(f"{name}: {entity_id}: indexable without an internal href")
            for alias in entity.get("aliases") or []:
                key = str(alias).casefold().strip()
                if not key:
                    continue
                previous = aliases.get(key)
                if previous is not None and previous != entity_id:
                    outcome.fail(f"{name}: alias {alias!r} identifies {previous} and {entity_id}")
                aliases[key] = entity_id
            for source, value in (entity.get("external_ids") or {}).items():
                key = (str(source), str(value))
                previous = external.get(key)
                if previous is not None and previous != entity_id:
                    outcome.fail(f"{name}: external id {source}:{value} is duplicated")
                external[key] = entity_id
    scouted_ids = {
        _entity_id(entity)
        for name, entities in _entity_documents(corpus)
        if name == "entities/scouted.json"
        for entity in entities
    }
    overlap = core_ids & scouted_ids
    if overlap:
        outcome.fail(f"core and scouted entities overlap: {sorted(overlap)[:5]}")


def _check_semantic_pages(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    meta = _payload(corpus, "page-meta.json") or {}
    provenance = _payload(corpus, "provenance.json") or {}
    registry = _payload(corpus, "metrics/registry.json") or {}
    layers = {str(row.get("id")) for row in provenance.get("layers") or []}
    metrics = {str(row.get("id")) for row in registry.get("metrics") or []}
    surfaces = meta.get("surfaces") or {}
    if not surfaces:
        outcome.fail("page-meta: no surfaces")
    for surface_id, surface in surfaces.items():
        outcome.rows_checked += 1
        outcome.fields_checked += 2
        if not surface.get("route_patterns"):
            outcome.fail(f"page-meta: {surface_id}: no route patterns")
        surface_layers = surface.get("layers") or []
        if not surface_layers and not surface.get("no_layers_reason"):
            outcome.fail(f"page-meta: {surface_id}: no layers and no reason")
        for layer in surface_layers:
            if layer not in layers:
                outcome.fail(f"page-meta: {surface_id}: unknown layer {layer}")
        for metric in surface.get("metrics") or []:
            if metric not in metrics:
                outcome.fail(f"page-meta: {surface_id}: unknown metric {metric}")


def _check_semantic_claims(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    case = _payload(corpus, "themes/aberdeen.json") or {}
    known = {str(row.get("id")) for row in case.get("claims") or []}
    for name, entities in _entity_documents(corpus):
        for entity in entities:
            if entity.get("type") != "claim":
                continue
            outcome.rows_checked += 1
            entity_id = _entity_id(entity)
            value = entity_id.split(":", 1)[-1]
            if value not in known:
                outcome.fail(f"{name}: claim {value}: not in themes/aberdeen.json")
            href = str(entity.get("href") or "")
            outcome.fields_checked += 1
            if not href.startswith("/claims/#claim-"):
                outcome.fail(f"{name}: claim {value}: href {href!r} is not the claims surface")
    for entity in (_payload(corpus, "entities/index.json") or {}).get("entities") or []:
        if "/analysis/#claim-" in str(entity.get("href") or ""):
            outcome.fail(f"{_entity_id(entity)}: stale analysis claim href")


def _check_semantic_definitions(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    definitions = _payload(corpus, "definitions.json") or {}
    registry = _payload(corpus, "metrics/registry.json") or {}
    metrics = {str(row.get("id")): row for row in registry.get("metrics") or []}
    ids: set[str] = set()
    for entry in definitions.get("entries") or []:
        outcome.rows_checked += 1
        entry_id = str(entry.get("id") or "")
        if not entry_id or entry_id in ids:
            outcome.fail(f"definitions: duplicate or missing id {entry_id!r}")
        ids.add(entry_id)
        for metric_id in entry.get("metric_ids") or []:
            metric = metrics.get(str(metric_id))
            outcome.fields_checked += 1
            if metric is None:
                outcome.fail(f"definitions: {entry_id}: unknown metric {metric_id}")
                continue
            if entry.get("provenance") == "registry":
                for field in ("basis", "coverage_tier", "source_layer"):
                    outcome.fields_checked += 1
                    if entry.get(field) != metric.get(field):
                        outcome.fail(f"definitions: {entry_id}: {field} does not match registry")
        if entry.get("provenance") == "curated_overlay" and entry.get("formula"):
            outcome.fail(f"definitions: {entry_id}: curated overlay may not override a formula")


def _check_rules_epoch(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    manifest = _payload(corpus, "manifest.json") or {}
    dataset_id = str(manifest.get("dataset_version") or "")
    update_id = str((manifest.get("update") or {}).get("id") or "")
    manifest_time = _parse_time(manifest.get("generated_at"))
    if not dataset_id or not update_id:
        outcome.fail("manifest has no dataset_version or update id")
        return
    for path, payload in sorted(corpus.items()):
        if path == "manifest.json" or not isinstance(payload, dict):
            continue
        state = str(payload.get("dataset_state") or "")
        outcome.rows_checked += 1
        if state == "stale":
            outcome.fields_checked += 1
            if not payload.get("stale_reason"):
                outcome.fail(f"{path}: stale payload has no reason")
        else:
            outcome.fields_checked += 1
            if payload.get("dataset_id") != dataset_id:
                outcome.fail(
                    f"{path}: dataset_id {payload.get('dataset_id')!r} != {dataset_id!r}"
                )
        served = payload.get("served_by_update_id")
        if served:
            outcome.fields_checked += 1
            if served != update_id:
                outcome.fail(f"{path}: served_by_update_id {served!r} != {update_id!r}")
        generated = _parse_time(payload.get("generated_at"))
        outcome.fields_checked += 1
        if generated is None:
            outcome.fail(f"{path}: generated_at is missing or unparseable")
        elif manifest_time and generated > manifest_time:
            outcome.fail(f"{path}: generated_at is later than the manifest")


def _check_rules_manifest(corpus: dict[str, Any], outcome: CheckOutcome) -> None:
    manifest = _payload(corpus, "manifest.json") or {}
    listed = {
        str(entry.get("path"))
        for entry in manifest.get("files") or []
        if entry.get("path")
    }
    for path in sorted(corpus):
        if path == "manifest.json":
            continue
        outcome.rows_checked += 1
        if path not in listed:
            outcome.fail(f"{path} is published but not listed in manifest.files")
    for path in sorted(listed):
        outcome.fields_checked += 1
        if path not in corpus:
            outcome.fail(f"manifest lists {path} but it is not in the corpus")


def _check_epoch_with_root(corpus: dict[str, Any], outcome: CheckOutcome, root) -> None:
    import hashlib

    manifest = _payload(corpus, "manifest.json") or {}
    for entry in manifest.get("files") or []:
        path = root / str(entry.get("path") or "")
        outcome.rows_checked += 1
        outcome.fields_checked += 1
        if not path.exists():
            outcome.fail(f"manifest file does not exist: {entry.get('path')}")
            continue
        digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry.get("checksum"):
            outcome.fail(f"checksum mismatch: {entry.get('path')}")


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
    (
        "former.register",
        "Former-player rows reconcile to published permanent/free departures",
        ["former-players/aberdeen.json", "transfers/aberdeen.json", "squad/aberdeen.json"],
        _check_former_register,
    ),
    (
        "former.post",
        "Former-player post-career totals reconcile to their season rows",
        ["former-players/aberdeen.json", "former-players/seasons.json"],
        _check_former_post,
    ),
    (
        "former.sell_on",
        "Sell-on clauses and receipts reconcile across former and transfer payloads",
        ["former-players/aberdeen.json", "transfers/aberdeen.json"],
        _check_former_sell_on,
    ),
    (
        "former.affiliation",
        "Rumour and forum affiliations keep former players out of the target profile",
        ["rumours/aberdeen.json", "rumours/profile.json", "forum/afc_chat.json"],
        _check_former_affiliation,
    ),
    (
        "former.coverage",
        "Former-player coverage counts equal the payload and coverage document",
        ["former-players/aberdeen.json", "coverage.json"],
        _check_former_coverage,
    ),
    (
        "results.table",
        "League table record and form equal the published fixture results",
        ["tables/*.json", "fixtures/index.json"],
        _check_results_table,
    ),
    (
        "results.form",
        "Matchday, analysis and club form equal the league table record",
        [
            "tables/*.json",
            "matchday/upcoming.json",
            "analysis/summary.json",
            "clubs/aberdeen.json",
        ],
        _check_results_form,
    ),
    (
        "results.club",
        "Club results, recent results and history equal the fixture record",
        [
            "clubs/aberdeen.json",
            "fixtures/index.json",
            "history/seasons/*.json",
        ],
        _check_results_club,
    ),
    (
        "results.coverage",
        "Coverage match counts equal the league tables they summarise",
        ["coverage.json", "tables/*.json"],
        _check_results_coverage,
    ),
    (
        "semantic.entities",
        "Canonical entity ids, aliases and external ids are unique and disjoint",
        [
            "entities/index.json",
            "entities/scouted.json",
        ],
        _check_semantic_entities,
    ),
    (
        "semantic.pages",
        "Page metadata references published provenance layers and registry metrics",
        ["page-meta.json", "provenance.json", "metrics/registry.json"],
        _check_semantic_pages,
    ),
    (
        "semantic.claims",
        "Claim entities resolve to the case payload and the claims surface",
        ["entities/index.json", "entities/scouted.json", "themes/aberdeen.json"],
        _check_semantic_claims,
    ),
    (
        "semantic.definitions",
        "Definition entries reference registry metrics without overriding them",
        ["definitions.json", "metrics/registry.json"],
        _check_semantic_definitions,
    ),
    (
        "rules.epoch",
        "Every payload belongs to the current dataset epoch or is explicitly stale",
        ["manifest.json", "**/*.json"],
        _check_rules_epoch,
    ),
    (
        "rules.manifest",
        "The manifest lists every published file and every listed file exists",
        ["manifest.json"],
        _check_rules_manifest,
    ),
]


def run_consistency(
    corpus: dict[str, Any], *, root: Any = None
) -> list[CheckResult]:
    results = [
        _check(check_id, description, corpus, payloads, function)
        for check_id, description, payloads, function in CHECKS
    ]
    if root is not None:
        outcome = CheckOutcome()
        try:
            _check_epoch_with_root(corpus, outcome, root)
        except Exception as error:  # noqa: BLE001
            outcome.fail(f"{type(error).__name__}: {error}")
        results.append(
            CheckResult(
                id="rules.checksums",
                description="Every manifest checksum matches the published bytes",
                status=outcome.status,
                rows_checked=outcome.rows_checked,
                fields_checked=outcome.fields_checked,
                errors=outcome.errors,
                payloads=["manifest.json"],
            )
        )
    return results


__all__ = ["CHECKS", "CheckOutcome", "CheckResult", "run_consistency"]
