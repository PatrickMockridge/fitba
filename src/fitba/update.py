"""One ordered update path for every published data area.

The shell cadence and the manual CI workflow both call this module through
``fitba update``. The point is that an update has one meaning: the same steps,
the same required/optional classification, the same persisted status, and a
publish that refuses to go out when a finished Aberdeen result is missing from
the canonical record or the league table.

Modes are tiered:

* ``daily`` refreshes every ingest area, including scouting and xG enrichment.
* ``matchday`` runs only when a finished fixture is unresolved, and refreshes
  the results core; other areas keep their TTL and are reported with their age.
* ``ci`` runs the same list, recording API-only steps as ``skipped`` when no
  key is configured instead of silently omitting them.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import polars as pl

from fitba.settings import NORMALIZED_DIR, ROOT, ensure_dirs
from fitba.util.dates import current_season, utc_now_iso

STATE_PATH = NORMALIZED_DIR / "update_state.json"
FIXTURES_PATH = ROOT / "web" / "data" / "generated" / "fixtures" / "index.json"
MANIFEST_PATH = ROOT / "web" / "data" / "generated" / "manifest.json"
LONDON = ZoneInfo("Europe/London")
FINISH_BUFFER = timedelta(hours=3)


@dataclass(slots=True)
class StepResult:
    id: str
    required: bool
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    duration_s: float | None = None
    rows: int | None = None
    error: str | None = None
    artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "required": self.required,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_s": self.duration_s,
            "rows": self.rows,
            "error": self.error,
            "artifacts": self.artifacts,
        }


@dataclass(slots=True)
class UpdateContext:
    mode: str
    season: str
    force_results: bool
    update_id: str
    dry_run: bool = False


Runner = Callable[[UpdateContext], dict[str, Any]]


@dataclass(slots=True)
class StepSpec:
    id: str
    runner: Runner
    required: bool = False
    network: bool = False
    api_only: bool = False
    modes: tuple[str, ...] = ("daily", "matchday", "ci")
    affects: str = ""
    ttl_hours: float | None = None


def _run_ingest_results(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.runner import ingest_season

    report = ingest_season(ctx.season, force=ctx.force_results)
    if report.has_errors:
        raise RuntimeError(f"results ingest reported errors: {report.to_dict()['results']}")
    return {"rows": report.rows, "artifacts": report.written}


def _run_ingest_api_results(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.api_results import ingest_api_results

    result = ingest_api_results(ctx.season, force=ctx.force_results)
    if result.status != "ok":
        raise RuntimeError(f"API league results failed: {result.errors}")
    return {"rows": result.rows, "artifacts": [str(result.path)] if result.path else []}


def _run_ingest_cups(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.cups import ingest_cups

    results = list(ingest_cups(force=ctx.force_results))
    failed = [result for result in results if result.status != "ok"]
    if failed:
        raise RuntimeError(f"cup ingest failed: {[result.errors for result in failed]}")
    return {"rows": sum(result.rows for result in results)}


def _run_ingest_fixtures(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.fixtures import ingest_club_fixtures

    result = ingest_club_fixtures("aberdeen", force=ctx.force_results)
    if result.status != "ok":
        raise RuntimeError(f"club fixture ingest failed: {result.errors}")
    return {"rows": result.rows, "artifacts": [str(result.path)] if result.path else []}


def _run_ingest_history(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.history import ingest_history_season
    from fitba.settings import source_ids

    team_id = int(source_ids()["teams"]["sco:aberdeen"]["api_football"])
    report = ingest_history_season(
        ctx.season,
        team_id=team_id,
        stages=("fixtures", "lineups", "events", "rosters", "players", "team_stats"),
        max_requests=80,
        force=False,
        dry_run=False,
    )
    errors = list(report.get("errors") or [])
    if errors:
        raise RuntimeError(f"history backfill reported errors: {errors[:3]}")
    return {"rows": int(report.get("rows") or 0)}


def _run_ingest_matchday(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.matchday import refresh_matchday

    result = refresh_matchday(max_requests=24, force=False, dry_run=False)
    if result.get("status") == "error":
        raise RuntimeError(str(result.get("error") or "matchday refresh failed"))
    return {"rows": int(result.get("played") or 0)}


def _run_ingest_transfers(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.transfers import ingest_transfers

    result = ingest_transfers(force=False)
    if result.status != "ok":
        raise RuntimeError(f"transfer ingest failed: {result.errors}")
    return {"rows": result.rows}


def _run_ingest_former_players(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.former_players import ingest_former_players

    result = ingest_former_players(mode="refresh", max_requests=180, force=False)
    if result.errors:
        raise RuntimeError(f"former-player refresh errors: {result.errors[:3]}")
    return {"rows": result.rows}


def _run_ingest_squad(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.squad import ingest_squad

    result = ingest_squad(force=False)
    if result.status != "ok":
        raise RuntimeError(f"squad ingest failed: {result.errors}")
    return {"rows": result.rows}


def _run_ingest_availability(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.availability import refresh_availability
    from fitba.publish.squad import squad_payload

    meta = refresh_availability(squad_data=squad_payload(ctx.season), force=False)
    if meta.get("errors"):
        raise RuntimeError(f"availability refresh errors: {meta['errors'][:3]}")
    return {"rows": int((meta.get("counts") or {}).get("entries") or 0)}


def _run_ingest_career(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.career_roles import refresh_career_roles

    result = refresh_career_roles()
    if result.status != "ok":
        raise RuntimeError(f"career refresh failed: {result.errors}")
    return {"rows": result.rows}


def _run_ingest_news(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.news import ingest_news

    result = ingest_news(force=False)
    if result.status != "ok":
        raise RuntimeError(f"news ingest failed: {result.errors}")
    return {"rows": result.rows}


def _run_ingest_forum(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.forum import ingest_forum

    result = ingest_forum(limit=6, force=False)
    if result.status != "ok":
        raise RuntimeError(f"forum ingest failed: {result.errors}")
    return {"rows": result.rows}


def _run_scouting_pool(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.scouting import ingest_pool

    meta = ingest_pool(season=ctx.season, refresh=False, league_ids="all")
    failed = [item for item in meta.get("leagues") or [] if item.get("status") == "error"]
    if failed:
        raise RuntimeError(f"scouting pool errors: {failed[:3]}")
    return {"rows": int((meta.get("totals") or {}).get("rows") or 0)}


def _run_scouting_roles(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.scouting import ingest_roles

    meta = ingest_roles(season=ctx.season, budget=6500, refresh=False, league_ids="all")
    return {"rows": int((meta.get("totals") or {}).get("role_players") or 0)}


def _run_scouting_rose_history(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.scouting import ingest_rose_history

    meta = ingest_rose_history(seasons=[2024, 2025], refresh=False)
    return {"rows": int((meta.get("totals") or {}).get("rows") or 0)}


def _run_scouting_europe(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.scouting_europe import ingest_europe

    meta = ingest_europe(season=ctx.season, budget=2000, refresh=False)
    return {"rows": int(meta.get("players") or 0)}


def _run_scouting_standings(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.scouting_standings import ingest_standings

    meta = ingest_standings(season=ctx.season, refresh=False)
    return {"rows": int((meta.get("totals") or {}).get("teams") or 0)}


def _run_scouting_clubs(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.scouting_clubs import ingest_current_clubs

    meta = ingest_current_clubs(budget=1000, refresh=False)
    if meta.get("errors"):
        raise RuntimeError(f"scouting club resolution errors: {meta['errors'][:3]}")
    return {"rows": int(meta.get("players") or 0)}


def _run_xg_enrich(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.xg_enrichment import enrich_premiership

    report = enrich_premiership(ctx.season, max_requests=120, refresh=False)
    if report.get("stopped_at_budget"):
        return {"rows": int(report.get("team_rows") or 0)}
    return {"rows": int(report.get("team_rows") or 0)}


def _run_build(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.warehouse.build import build_warehouse

    result = build_warehouse(season=None)
    return {"rows": int(result.matches)}


def _run_validate(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.validate.checks import run_validation

    report = run_validation(season=ctx.season, strict=True)
    if report.get("status") != "pass":
        raise RuntimeError(f"validation failed: {report.get('errors')} error(s)")
    return {"rows": len(report.get("checks") or [])}


def _run_publish(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.publish.publish import publish

    report = publish(
        season=ctx.season,
        profile="public",
        require_validation=True,
        update_id=ctx.update_id,
    )
    return {"rows": report.files, "artifacts": [report.out]}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _run_guard_results(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.ingest.fixtures import load_club_fixtures
    from fitba.ingest.runner import load_matches
    from fitba.normalize.results import OverlayReport, canonical_key, official_played_rows

    report = OverlayReport(club="aberdeen", precedence="spfl")
    matches = load_matches([ctx.season], report=report)
    official = official_played_rows(load_club_fixtures("aberdeen"), seasons={ctx.season})
    by_key = {canonical_key(row): row for row in matches.to_dicts()}
    missing = [
        f"{item.get('date')} {item.get('home_team_id')} v {item.get('away_team_id')}"
        for item in official.to_dicts()
        if canonical_key(item) not in by_key
    ]
    if missing:
        raise RuntimeError(f"finished official results missing from canonical frame: {missing}")
    published = _read_json(ROOT / "web" / "data" / "generated" / "audit" / "results.json")
    if published and published.get("status") not in (None, "pass", "warning"):
        raise RuntimeError(f"published result audit is {published.get('status')}")
    return {"rows": official.height}


def _run_guard_consistency(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.metrics.audit import load_corpus
    from fitba.metrics.consistency import run_consistency
    from fitba.settings import WEB_DATA_DIR

    results = run_consistency(load_corpus(WEB_DATA_DIR), root=WEB_DATA_DIR)
    failed = [result for result in results if result.status != "pass"]
    if failed:
        raise RuntimeError(
            "cross-surface consistency failed: "
            + "; ".join(f"{item.id}: {item.errors[:2]}" for item in failed[:3])
        )
    return {"rows": len(results)}


def _run_guard_freshness(ctx: UpdateContext) -> dict[str, Any]:
    from fitba.freshness import check_freshness

    report = check_freshness(ROOT / "web" / "data" / "generated", strict=True)
    if report.get("status") != "pass":
        raise RuntimeError(f"freshness check failed: {report.get('errors')}")
    return {"rows": len(report.get("sources") or {})}


def _run_guard_metrics(ctx: UpdateContext) -> dict[str, Any]:
    scripts = [
        ("check_publication.py", []),
        ("check_metrics.py", ["--strict"]),
        ("check_transfers.py", []),
        ("check_former_players.py", []),
        ("check_names.py", []),
        ("check_history.py", []),
        ("check_matchday.py", []),
        ("check_themes.py", []),
        ("check_xg.py", ["--published"]),
        ("check_provenance.py", []),
        ("check_availability.py", []),
        ("check_needs.py", []),
        ("check_rumours.py", []),
        ("check_squad.py", []),
        ("check_scouting.py", []),
        ("check_roles.py", []),
        ("check_shapes.py", []),
        ("check_career_roles.py", []),
        ("check_player_page.py", []),
        ("check_player_attributes.py", []),
    ]
    commands = [[sys.executable, str(ROOT / "scripts" / name), *args] for name, args in scripts]
    for command in commands:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(
                f"{Path(command[1]).name} failed: {completed.stdout[-800:]}"
                f"{completed.stderr[-800:]}"
            )
    return {"rows": None}


STEP_SPECS: list[StepSpec] = [
    StepSpec("ingest.results", _run_ingest_results, required=True, network=True, ttl_hours=6),
    StepSpec(
        "ingest.api_results",
        _run_ingest_api_results,
        required=True,
        network=True,
        api_only=True,
        ttl_hours=1,
        affects="complete current-season league results for every SPFL tier",
    ),
    StepSpec("ingest.cups", _run_ingest_cups, network=True, api_only=True, ttl_hours=1),
    StepSpec(
        "ingest.fixtures",
        _run_ingest_fixtures,
        network=True,
        ttl_hours=1,
        affects="official result overlay; the result guard blocks a missing core result",
    ),
    StepSpec("ingest.history", _run_ingest_history, network=True, api_only=True, ttl_hours=24),
    StepSpec("ingest.matchday", _run_ingest_matchday, network=True, api_only=True, ttl_hours=20),
    StepSpec("ingest.transfers", _run_ingest_transfers, network=True, api_only=True, ttl_hours=12),
    StepSpec(
        "ingest.former_players",
        _run_ingest_former_players,
        network=True,
        api_only=True,
        ttl_hours=24,
    ),
    StepSpec("ingest.squad", _run_ingest_squad, network=True, api_only=True, ttl_hours=12),
    StepSpec("ingest.availability", _run_ingest_availability, ttl_hours=504),
    StepSpec("ingest.career", _run_ingest_career, ttl_hours=24),
    StepSpec("ingest.news", _run_ingest_news, network=True, ttl_hours=1),
    StepSpec("ingest.forum", _run_ingest_forum, network=True, ttl_hours=3),
    StepSpec("ingest.scouting_pool", _run_scouting_pool, network=True, api_only=True, ttl_hours=24),
    StepSpec(
        "ingest.scouting_roles", _run_scouting_roles, network=True, api_only=True, ttl_hours=6
    ),
    StepSpec(
        "ingest.scouting_rose_history",
        _run_scouting_rose_history,
        network=True,
        ttl_hours=168,
    ),
    StepSpec(
        "ingest.scouting_europe", _run_scouting_europe, network=True, api_only=True, ttl_hours=24
    ),
    StepSpec(
        "ingest.scouting_standings",
        _run_scouting_standings,
        network=True,
        api_only=True,
        ttl_hours=24,
    ),
    StepSpec(
        "ingest.scouting_clubs", _run_scouting_clubs, network=True, api_only=True, ttl_hours=24
    ),
    StepSpec("xg.enrich", _run_xg_enrich, network=True, api_only=True, ttl_hours=24),
    StepSpec("warehouse.build", _run_build, required=True),
    StepSpec("validate", _run_validate, required=True),
    StepSpec("publish", _run_publish, required=True),
    StepSpec("guard.results", _run_guard_results, required=True),
    StepSpec("guard.consistency", _run_guard_consistency, required=True),
    StepSpec("guard.freshness", _run_guard_freshness, required=True),
    StepSpec("guard.metrics", _run_guard_metrics, required=True),
]

STEP_IDS = [spec.id for spec in STEP_SPECS]

CORE_MATCHDAY_IDS = {
    "ingest.results",
    "ingest.api_results",
    "ingest.fixtures",
    "ingest.news",
    "ingest.availability",
    "ingest.squad",
    "warehouse.build",
    "validate",
    "publish",
    "guard.results",
    "guard.consistency",
    "guard.freshness",
    "guard.metrics",
}


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _kickoff(row: dict[str, Any]) -> datetime | None:
    date_value = str(row.get("date") or "").strip()
    kickoff = str(row.get("kickoff") or "").strip()
    if not date_value or not kickoff:
        return None
    try:
        local = datetime.fromisoformat(f"{date_value}T{kickoff}:00")
    except ValueError:
        return None
    return local.replace(tzinfo=LONDON)


def refresh_due(
    *,
    now: datetime | None = None,
    fixtures_index: dict[str, Any] | None = None,
    manifest: dict[str, Any] | None = None,
    canonical_matches: pl.DataFrame | None = None,
) -> bool:
    """Return True when a finished Aberdeen fixture has no canonical result.

    A publish that only re-stamps timestamps does not make a missing result up
    to date: the result itself is checked, first in the canonical frame and then
    in the published fixture index.
    """
    now = now or datetime.now(UTC)
    index = fixtures_index if fixtures_index is not None else _read_json(FIXTURES_PATH)
    manifest = manifest if manifest is not None else _read_json(MANIFEST_PATH)
    if canonical_matches is None:
        try:
            from fitba.ingest.runner import load_matches

            canonical_matches = load_matches([current_season()])
        except Exception:  # noqa: BLE001 - fall back to the published index
            canonical_matches = pl.DataFrame()
    canonical_keys: set[tuple[str, str, str]] = set()
    if canonical_matches.height:
        for row in canonical_matches.to_dicts():
            if row.get("home_goals") is None or row.get("away_goals") is None:
                continue
            canonical_keys.add(
                (
                    str(row.get("date"))[:10],
                    str(row.get("home_team_id") or ""),
                    str(row.get("away_team_id") or ""),
                )
            )
    published_keys: set[tuple[str, str, str]] = set()
    for row in index.get("fixtures") or []:
        if row.get("home_goals") is None or row.get("away_goals") is None:
            continue
        published_keys.add(
            (
                str(row.get("date"))[:10],
                str(row.get("home_team_id") or ""),
                str(row.get("away_team_id") or ""),
            )
        )
    generated = _parse_time(manifest.get("generated_at")) if manifest else None
    for row in index.get("scheduled") or []:
        kickoff = _kickoff(row)
        if kickoff is None:
            continue
        finished = kickoff + FINISH_BUFFER
        if now < finished:
            continue
        key = (
            str(row.get("date"))[:10],
            str(row.get("home_team_id") or ""),
            str(row.get("away_team_id") or ""),
        )
        if key not in canonical_keys and key not in published_keys:
            return True
        if generated is None or generated < finished:
            return True
    return False


def _write_state(state: dict[str, Any]) -> None:
    ensure_dirs()
    temp = STATE_PATH.with_suffix(".json.tmp")
    temp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, STATE_PATH)


def _api_available() -> bool:
    return bool(os.environ.get("API_FOOTBALL_KEY"))


def _select_steps(mode: str, only: set[str] | None, skip: set[str]) -> list[StepSpec]:
    selected: list[StepSpec] = []
    for spec in STEP_SPECS:
        if only and spec.id not in only:
            continue
        if spec.id in skip:
            continue
        if mode == "matchday" and spec.id not in CORE_MATCHDAY_IDS:
            continue
        selected.append(spec)
    return selected


def run_update(
    *,
    mode: str = "daily",
    force_results: bool = False,
    only: str | None = None,
    skip: str | None = None,
    dry_run: bool = False,
    publish: bool = True,
    allow_stale: bool = False,
    resume: bool = False,
    force_run: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    season = current_season()
    update_id = f"{utc_now_iso()}-{os.getpid()}"
    only_ids = {part.strip() for part in (only or "").split(",") if part.strip()}
    skip_ids = {part.strip() for part in (skip or "").split(",") if part.strip()}
    steps = _select_steps(mode, only_ids or None, skip_ids)
    if not publish:
        steps = [
            spec
            for spec in steps
            if spec.id
            not in {
                "publish",
                "guard.results",
                "guard.consistency",
                "guard.freshness",
                "guard.metrics",
            }
        ]

    if mode == "matchday" and not force_run:
        due = refresh_due(now=now)
        if not due:
            return {
                "status": "not_due",
                "mode": mode,
                "season": season,
                "update_id": update_id,
                "steps": [],
                "message": "no finished fixture is unresolved",
            }

    previous: dict[str, Any] = {}
    if resume and STATE_PATH.exists():
        previous = _read_json(STATE_PATH)
    completed = {
        step.get("id") for step in previous.get("steps") or [] if step.get("status") == "ok"
    }

    state: dict[str, Any] = {
        "schema_version": "1.0.0",
        "run_id": update_id,
        "update_id": update_id,
        "mode": mode,
        "season": season,
        "git_sha": _git_sha(),
        "started_at": utc_now_iso(),
        "finished_at": None,
        "status": "running",
        "force_results": force_results,
        "steps": [],
        "stale_sources": [],
        "guards": {},
    }
    ctx = UpdateContext(
        mode=mode,
        season=season,
        force_results=force_results,
        update_id=update_id,
        dry_run=dry_run,
    )
    if dry_run:
        return {
            "status": "dry_run",
            "mode": mode,
            "season": season,
            "update_id": update_id,
            "steps": [
                {"id": spec.id, "required": spec.required, "network": spec.network}
                for spec in steps
            ],
        }

    failed_required = False
    for spec in steps:
        if resume and spec.id in completed:
            state["steps"].append(
                {
                    "id": spec.id,
                    "required": spec.required,
                    "status": "ok",
                    "resumed": True,
                }
            )
            continue
        if spec.api_only and mode == "ci" and not _api_available():
            state["steps"].append(
                {
                    "id": spec.id,
                    "required": spec.required,
                    "status": "skipped",
                    "error": "missing_api_key",
                }
            )
            continue
        result = StepResult(
            id=spec.id,
            required=spec.required,
            status="running",
            started_at=utc_now_iso(),
        )
        started = time.monotonic()
        try:
            details = spec.runner(ctx) or {}
            result.status = "ok"
            result.rows = details.get("rows")
            result.artifacts = [
                str(item) for item in (details.get("artifacts") or []) if item is not None
            ]
        except Exception as exc:  # noqa: BLE001 - recorded per step
            result.status = "failed"
            result.error = str(exc)
            if spec.required:
                failed_required = True
            else:
                state["stale_sources"].append(
                    {"source": spec.id, "reason": "step_failed", "error": str(exc)}
                )
        finally:
            result.finished_at = utc_now_iso()
            result.duration_s = round(time.monotonic() - started, 2)
        state["steps"].append(result.to_dict())
        _write_state(state)
        if failed_required:
            break

    if failed_required:
        state["status"] = "failed"
        state["finished_at"] = utc_now_iso()
        _write_state(state)
        return state

    if state["stale_sources"] and not allow_stale:
        # Optional failures are allowed to publish, but they are always labelled
        # in the manifest and in the payloads; they never block the results.
        state["status"] = "degraded"
    else:
        state["status"] = "ok"
    state["finished_at"] = utc_now_iso()
    _write_state(state)
    if publish:
        _finalise_manifest(state)
    return state


def _finalise_manifest(state: dict[str, Any]) -> None:
    """Rewrite the manifest update block once every step has finished.

    Publish writes the manifest mid-run because the payload epoch must be
    stamped before the atomic swap. The final status and the post-publish guard
    steps are added here so `/status/` shows the complete run, not a prefix.
    """
    path = ROOT / "web" / "data" / "generated" / "manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    update_block = manifest.get("update") or {}
    if str(update_block.get("id") or "") != str(state.get("run_id") or ""):
        return
    stale_sources = sorted(
        set((manifest.get("freshness") or {}).get("stale_sources") or [])
        | {
            str(item.get("source"))
            for item in state.get("stale_sources") or []
            if item.get("source")
        }
    )
    status = state.get("status")
    if status == "ok" and stale_sources:
        status = "degraded"
    update_block.update(
        {
            "status": status,
            "finished_at": state.get("finished_at"),
            "steps": state.get("steps") or [],
            "stale_sources": state.get("stale_sources") or [],
        }
    )
    manifest["update"] = update_block
    freshness = manifest.get("freshness") or {}
    freshness["stale_sources"] = stale_sources
    manifest["freshness"] = freshness
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _git_sha() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return completed.stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def load_update_state() -> dict[str, Any]:
    return _read_json(STATE_PATH) if STATE_PATH.exists() else {}


__all__ = [
    "CORE_MATCHDAY_IDS",
    "FINISH_BUFFER",
    "STATE_PATH",
    "STEP_IDS",
    "STEP_SPECS",
    "UpdateContext",
    "load_update_state",
    "refresh_due",
    "run_update",
]
