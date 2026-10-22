#!/usr/bin/env python3
"""CI guard for metric definitions, audit integrity and numeric coverage.

The registry is canonical. This checker proves the published registry matches
it, the audit is reproducible from the published corpus, every numeric leaf is
registered (or explicitly structural), every parameter matches config, and a
metric definition cannot change without a version bump and changelog entry.

Exit codes: 0 pass; 1 failure; 2 bad usage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import orjson
import yaml

from fitba.metrics.audit import (
    _matches,
    _parameter_entry,
    _segments,
    build_audit,
    build_registry_payload,
    load_corpus,
    numeric_leaf_pointers,
    pointer_matches,
)
from fitba.metrics.checks import CHECKS
from fitba.metrics.models import Metric, Parameter
from fitba.metrics.registry import (
    SCHEMA_PATH,
    load_registry,
    registry_checksum,
    registry_schema,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "web" / "data" / "generated"
CHANGELOG = ROOT / "docs" / "metric-changes.md"
WEB_APP = ROOT / "web" / "app"
WEB_SRC = ROOT / "web"
EXCLUDED_PREFIXES = ("audit/", "metrics/")
EXCLUDED_FILES = {"manifest.json"}

SEMANTIC_METRIC_FIELDS = (
    "description",
    "value_type",
    "fields",
    "formula",
    "inputs",
    "unit",
    "aggregation",
    "denominator",
    "rounding",
    "basis",
    "source_layer",
    "coverage_tier",
    "confidence_rule",
    "home_payload",
    "payload_paths",
    "home_surface",
    "displayed_surfaces",
    "verification",
    "verification_checks",
    "implementation",
    "source_paths",
    "limitations",
    "status",
)
SEMANTIC_PARAMETER_FIELDS = (
    "kind",
    "value",
    "unit",
    "used_by",
    "config_path",
    "config_keys",
    "verification",
    "status",
)

IDENTITY_PATTERNS = (
    re.compile(r"\bTEAM_ID\s*=\s*252\b"),
    re.compile(r"\bSEASON_YEAR\s*=\s*2026\b"),
    re.compile(r"(?:team_id|TEAM_ID)\s*==\s*252\b"),
    re.compile(r"\bteam_id\s*==\s*252\b"),
    re.compile(r"verified_at\s*=\s*['\"]20\d\d-\d\d-\d\d['\"]"),
)


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.notes: list[str] = []
        self.passed = 0

    def check(self, ok: bool, name: str, message: str, *, warning: bool = False) -> bool:
        if ok:
            self.passed += 1
        elif warning:
            self.warnings.append(f"{name}: {message}")
        else:
            self.errors.append(f"{name}: {message}")
        return ok

    def note(self, name: str, message: str) -> None:
        self.notes.append(f"{name}: {message}")

    def summary(self) -> str:
        return f"{self.passed} passed, {len(self.warnings)} warning(s), {len(self.errors)} error(s)"


def _canonical(value: Any) -> bytes:
    return orjson.dumps(value, option=orjson.OPT_SORT_KEYS)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _route_exists(surface: str) -> bool:
    if surface.startswith("/players/"):
        return True
    base = WEB_APP / surface.strip("/")
    if (base / "page.tsx").exists() or (base / "route.ts").exists():
        return True
    return any(base.glob("*/page.tsx")) or any(base.glob("*/route.ts"))


def _check_registry(registry: Any, report: Report) -> None:
    report.check(
        _canonical(registry_schema()) == _canonical(_load_json(SCHEMA_PATH)),
        "registry.schema",
        (
            f"{SCHEMA_PATH.relative_to(ROOT)} is stale; "
            "regenerate from MetricRegistry.model_json_schema()"
        ),
    )
    report.check(
        registry.schema_version == 1,
        "registry.schema_version",
        f"unsupported schema_version {registry.schema_version}",
    )
    report.check(
        bool(registry.metrics),
        "registry.metrics",
        "no metrics registered",
    )
    report.check(
        bool(registry.registry_version),
        "registry.version",
        "registry_version is empty",
    )

    for metric in registry.metrics:
        if metric.status != "active":
            report.note("registry.status", f"{metric.id} is {metric.status}")
            continue
        formula_text = str(metric.formula or "")
        report.check(
            not any(
                placeholder in formula_text
                for placeholder in (
                    "Registered family",
                    "Registered case family",
                    "Registered document family",
                )
            ),
            "registry.formula",
            (
                f"{metric.id}: placeholder formula; publish a real definition "
                "or an explicit document envelope"
            ),
        )
        if metric.verification == "recompute":
            report.check(
                metric.implementation in CHECKS,
                "registry.implementation",
                f"{metric.id}: {metric.implementation!r} is not a known verification function",
            )
        elif metric.verification == "cross_surface":
            report.check(
                bool(metric.implementation or metric.verification_checks),
                "registry.cross_surface",
                f"{metric.id}: no cross-surface check declared",
            )
        report.check(
            _route_exists(metric.home_surface),
            "registry.home_surface",
            f"{metric.id}: {metric.home_surface} has no route",
        )
        for surface in metric.displayed_surfaces:
            report.check(
                _route_exists(surface),
                "registry.displayed_surface",
                f"{metric.id}: {surface} has no route",
            )


def _check_source_layers(corpus: dict[str, Any], registry: Any, report: Report) -> None:
    provenance = corpus.get("provenance.json") or {}
    layers = {layer.get("id"): layer for layer in provenance.get("layers") or []}
    for metric in registry.metrics:
        if metric.source_layer == "computed":
            continue
        layer = layers.get(metric.source_layer)
        report.check(
            layer is not None,
            "registry.source_layer",
            f"{metric.id}: {metric.source_layer} not in provenance.json",
        )
        if layer is not None:
            report.check(
                layer.get("status") != "not_published",
                "registry.source_layer",
                f"{metric.id}: {metric.source_layer} is not published",
            )


def _check_parameters(registry: Any, report: Report) -> None:
    for parameter in registry.parameters:
        entry = _parameter_entry(parameter)
        report.check(
            entry["status"] == "pass",
            "parameters.config_match",
            f"{parameter.id}: {'; '.join(entry['errors']) or 'mismatch'}",
        )


def _check_published_registry(registry: Any, data: Path, report: Report) -> dict[str, Any] | None:
    path = data / "metrics" / "registry.json"
    if not path.exists():
        report.check(False, "published.registry", f"missing {path}")
        return None
    published = _load_json(path)
    expected = build_registry_payload(registry)
    report.check(
        _canonical(published) == _canonical(expected),
        "published.registry",
        "metrics/registry.json does not match config/metrics.yaml; republish",
    )
    report.check(
        published.get("checksum") == registry_checksum(registry),
        "published.registry_checksum",
        "registry checksum mismatch",
    )
    return published


def _check_audit(data: Path, registry: Any, report: Report) -> dict[str, Any] | None:
    path = data / "audit" / "metrics.json"
    if not path.exists():
        report.check(False, "published.audit", f"missing {path}")
        return None
    audit = _load_json(path)
    manifest_path = data / "manifest.json"
    if not manifest_path.exists():
        report.check(False, "published.manifest", f"missing {manifest_path}")
        return audit
    manifest = _load_json(manifest_path)

    report.check(audit.get("status") == "pass", "audit.status", "audit status is not pass")
    report.check(
        audit.get("registry_checksum") == registry_checksum(registry),
        "audit.registry_checksum",
        "audit registry checksum does not match the current registry",
    )
    report.check(
        audit.get("registry_version") == registry.registry_version,
        "audit.registry_version",
        "audit registry version does not match the current registry",
    )
    report.check(
        audit.get("dataset_version") == manifest.get("dataset_version"),
        "audit.dataset_version",
        "audit dataset version does not match the manifest",
    )
    report.check(
        audit.get("generated_at") == manifest.get("generated_at"),
        "audit.generated_at",
        "audit generated_at does not match the manifest",
    )
    report.check(
        audit.get("season") == manifest.get("season"),
        "audit.season",
        "audit season does not match the manifest",
    )

    metric_ids = [metric["id"] for metric in audit.get("metrics", [])]
    parameter_ids = [parameter["id"] for parameter in audit.get("parameters", [])]
    report.check(
        len(metric_ids) == len(set(metric_ids)) == len(registry.metrics),
        "audit.metric_coverage",
        f"{len(metric_ids)} audit entries for {len(registry.metrics)} metrics",
    )
    report.check(
        len(parameter_ids) == len(set(parameter_ids)) == len(registry.parameters),
        "audit.parameter_coverage",
        f"{len(parameter_ids)} audit entries for {len(registry.parameters)} parameters",
    )
    report.check(
        set(metric_ids) == {metric.id for metric in registry.metrics},
        "audit.metric_ids",
        "audit metric ids do not match the registry",
    )
    report.check(
        set(parameter_ids) == {parameter.id for parameter in registry.parameters},
        "audit.parameter_ids",
        "audit parameter ids do not match the registry",
    )

    for entry in audit.get("metrics", []):
        entry_id = entry.get("id")
        report.check(
            entry.get("status") == "pass",
            "audit.metric_status",
            f"{entry_id}: {entry.get('errors') or 'not pass'}",
        )
        report.check(
            bool(entry.get("locations")),
            "audit.metric_locations",
            f"{entry_id}: no payload location resolved",
        )
        if entry.get("verification") == "provenance_only":
            report.check(
                entry.get("provenance_only") is True,
                "audit.provenance_only",
                f"{entry_id}: provenance_only flag missing",
            )
            report.check(
                bool(entry.get("limitations")),
                "audit.limitation",
                f"{entry_id}: provenance_only metric has no limitation",
            )
    for entry in audit.get("parameters", []):
        report.check(
            entry.get("status") == "pass",
            "audit.parameter_status",
            f"{entry.get('id')}: {entry.get('errors') or 'not pass'}",
        )

    # Reproduce the audit from the published corpus. This is the anti-hand-edit
    # check: a modified value or audit entry fails here.
    corpus = load_corpus(data)
    reproduced = build_audit(
        corpus=corpus,
        registry=registry,
        dataset_version=str(manifest.get("dataset_version") or ""),
        generated_at=str(manifest.get("generated_at") or ""),
        season=str(manifest.get("season") or ""),
        audited_at=audit.get("audited_at"),
        allowlist=audit.get("allowlist"),
    )
    report.check(
        _canonical(reproduced) == _canonical(audit),
        "audit.reproducible",
        "audit/metrics.json does not reproduce from the published corpus and registry",
    )

    metrics_block = manifest.get("metrics") or {}
    report.check(
        metrics_block.get("status") == audit.get("status"),
        "manifest.metrics.status",
        "manifest metric status does not match the audit",
    )
    for key in (
        "registry_version",
        "registry_checksum",
        "audited_at",
    ):
        report.check(
            metrics_block.get(key) == audit.get(key),
            f"manifest.metrics.{key}",
            "manifest metric block does not match the audit",
        )
    for key in (
        "metrics_total",
        "metrics_passed",
        "metrics_failed",
        "parameters_total",
        "parameters_passed",
        "parameters_failed",
        "verification_modes",
        "provenance_only",
    ):
        report.check(
            metrics_block.get(key) == audit.get("summary", {}).get(key),
            f"manifest.metrics.{key}",
            "manifest metric block does not match the audit summary",
        )
    report.check(
        metrics_block.get("audit_checksum") == _sha256_file(path),
        "manifest.metrics.audit_checksum",
        "audit file checksum does not match the manifest",
    )

    allowlist = audit.get("allowlist") or {}
    status = allowlist.get("status")
    report.check(
        status in {"none", "active"},
        "audit.allowlist",
        f"unknown allowlist status {status!r}",
    )
    if status == "active":
        entries = allowlist.get("entries") or []
        report.check(
            bool(entries) and bool(allowlist.get("expires")),
            "audit.allowlist",
            "active allowlist needs entries and an expiry",
        )
        report.note("audit.allowlist", f"{len(entries)} temporary allowlist entries")
    return audit


def _check_validation(data: Path, report: Report) -> None:
    path = data / "audit" / "validation.json"
    if not path.exists():
        report.check(False, "published.validation", f"missing {path}")
        return
    validation = _load_json(path)
    manifest = _load_json(data / "manifest.json")
    block = manifest.get("validation") or {}
    report.check(
        block.get("status") == validation.get("status"),
        "manifest.validation.status",
        "manifest validation status does not match the report",
    )
    for key in ("errors", "warnings", "generated_at", "season", "strict"):
        report.check(
            block.get(key) == validation.get(key),
            f"manifest.validation.{key}",
            "manifest validation block does not match the report",
        )
    report.check(
        block.get("checksum") == _sha256_file(path),
        "manifest.validation.checksum",
        "validation file checksum does not match the manifest",
    )
    report.check(
        len(validation.get("checks") or []) == block.get("checks"),
        "manifest.validation.checks",
        "validation check count does not match the report",
    )


def _check_numeric_coverage(corpus: dict[str, Any], registry: Any, report: Report) -> None:
    covered: set[tuple[str, str]] = set()
    for metric in registry.metrics:
        for pattern in metric.payload_paths:
            payload_pattern, _, pointer = pattern.partition("#")
            for key in _matches(corpus, payload_pattern):
                for concrete, _ in numeric_leaf_pointers(corpus[key], _segments(pointer or "/**")):
                    covered.add((key, concrete))

    uncovered: list[str] = []
    total = structural = 0
    for key in sorted(corpus):
        if key in EXCLUDED_FILES or key.startswith(EXCLUDED_PREFIXES):
            continue
        for pointer, value in numeric_leaf_pointers(corpus[key], []):
            total += 1
            if (key, pointer) in covered:
                continue
            if any(
                pointer_matches(pattern, pointer) for pattern in registry.structural_number_patterns
            ):
                structural += 1
                continue
            uncovered.append(f"{key}#{pointer}={value}")

    report.check(
        not uncovered,
        "numbers.registered",
        f"{len(uncovered)} unregistered numeric leaf/leaves, e.g. {uncovered[:5]}",
    )
    report.note(
        "numbers.coverage",
        f"{total} numeric leaves: {total - structural - len(uncovered)} registered, "
        f"{structural} structural, {len(uncovered)} unregistered",
    )


def _check_manifest_marts(data: Path, report: Report) -> None:
    manifest = _load_json(data / "manifest.json")
    files = {item["path"]: item for item in manifest.get("files") or []}
    marts = manifest.get("marts") or []
    covered: set[str] = set()

    for mart in marts:
        mart_id = str(mart.get("id"))
        path = str(mart.get("path") or "")
        checksum = mart.get("checksum")
        if path.endswith("/"):
            covered.update(key for key in files if key.startswith(path))
            payload = None
        else:
            covered.add(path)
            report.check(path in files, "marts.file", f"{mart_id}: {path} is not in manifest.files")
            if checksum is not None:
                report.check(
                    checksum == files.get(path, {}).get("checksum"),
                    "marts.checksum",
                    f"{mart_id}: checksum does not match manifest.files",
                )
            try:
                payload = _load_json(data / path)
            except (OSError, json.JSONDecodeError):
                report.check(False, "marts.payload", f"{mart_id}: cannot read {path}")
                continue
        expected = _mart_rows(mart_id, payload)
        if expected is not None:
            report.check(
                mart.get("rows") == expected,
                "marts.rows",
                f"{mart_id}: rows {mart.get('rows')} != {expected}",
            )

    missing = sorted(set(files) - covered)
    report.check(
        not missing,
        "marts.coverage",
        f"{len(missing)} file(s) not covered by a mart, e.g. {missing[:5]}",
    )


def _mart_rows(mart_id: str, payload: Any) -> int | None:
    if payload is None:
        return None
    if mart_id.startswith("league_table."):
        return len(payload.get("rows") or [])
    if mart_id.startswith("squad."):
        return len(payload.get("players") or [])
    if mart_id.startswith("club."):
        return len(payload.get("results") or [])
    if mart_id.startswith("availability."):
        return len(payload.get("entries") or [])
    if mart_id.startswith("transfers-audit."):
        return len(payload.get("current_squad_arrivals") or []) + len(
            payload.get("prior_departures") or []
        )
    if mart_id.startswith("transfers."):
        return len(payload.get("transfers") or [])
    if mart_id == "history.sco:aberdeen":
        return len(payload.get("seasons") or [])
    if mart_id.startswith("history.season."):
        return len(payload.get("managers") or [])
    if mart_id.startswith("needs."):
        return len(payload.get("families") or [])
    if mart_id.startswith("analysis."):
        return len(payload.get("analyses") or [])
    if mart_id.startswith("rumours.sco"):
        return len(payload.get("rumours") or [])
    if mart_id.startswith("competitions.index"):
        return len(payload.get("competitions") or [])
    if mart_id.startswith("competitions."):
        return len(payload.get("fixtures") or [])
    if mart_id in {
        "search.index",
        "provenance",
        "coverage",
        "seasons",
        "metrics.registry",
        "audit.metrics",
        "audit.validation",
    }:
        if mart_id == "search.index":
            return len(payload) if isinstance(payload, list) else None
        if mart_id == "provenance":
            return len(payload.get("layers") or [])
        if mart_id == "coverage":
            return 1
        if mart_id == "seasons":
            return len(payload.get("seasons") or [])
        if mart_id in {"metrics.registry", "audit.metrics"}:
            return len(payload.get("metrics") or [])
        if mart_id == "audit.validation":
            return len(payload.get("checks") or [])
    if mart_id == "forum.afc_chat":
        return int((payload.get("coverage") or {}).get("posts_sampled") or 0)
    if mart_id == "matchday.upcoming":
        return 1
    if mart_id == "rumours.profile":
        return 0
    return None


def _check_identity(report: Report) -> None:
    hits: list[str] = []
    for path in sorted((ROOT / "src" / "fitba").rglob("*.py")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for pattern in IDENTITY_PATTERNS:
                if pattern.search(line):
                    hits.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")
                    break
    report.check(
        not hits,
        "identity.hardcoded",
        f"hardcoded identity or verification date: {hits[:5]}",
    )


def _check_client_formatting(report: Report) -> None:
    config_path = ROOT / "config" / "client-formatting.yaml"
    if not config_path.exists():
        report.check(False, "client.formatting", f"missing {config_path.relative_to(ROOT)}")
        return
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    allowed = {str(key): int(value) for key, value in (config.get("files") or {}).items()}
    counts: dict[str, int] = {}
    for path in sorted(WEB_SRC.rglob("*")):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        if "node_modules" in path.parts or path.name == "format.ts":
            continue
        relative = str(path.relative_to(ROOT))
        count = sum(
            1
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
            if "Math.round(" in line or ".toFixed(" in line
        )
        if count:
            counts[relative] = count
    for relative, count in sorted(counts.items()):
        limit = allowed.get(relative, 0)
        report.check(
            count <= limit,
            "client.formatting",
            f"{relative}: {count} direct Math.round/toFixed call(s), baseline allows {limit}; "
            "move formatting into web/lib/format.ts",
        )
    total = sum(counts.values())
    report.note(
        "client.formatting",
        f"{total} direct Math.round/toFixed call(s) outside web/lib/format.ts "
        f"(baseline {sum(allowed.values())}); the count may fall but may not grow",
    )


def _raw_registry(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: registry must be a mapping")
    return payload


def _check_change_control(registry: Any, git_ref: str, report: Report) -> None:
    try:
        old_text = subprocess.run(
            ["git", "show", f"{git_ref}:config/metrics.yaml"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip()
        if "does not exist" in message or "exists on disk, but not in" in message:
            report.check(
                True,
                "change_control",
                f"no registry at {git_ref}; treating this registry as the baseline",
            )
            return
        report.check(
            False,
            "change_control.git",
            f"cannot read config/metrics.yaml at {git_ref}: {message}",
        )
        return
    old = yaml.safe_load(old_text)
    if not isinstance(old, dict):
        report.check(False, "change_control.git", f"{git_ref} registry is not a mapping")
        return

    changelog = CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.exists() else ""
    old_registry_version = str(old.get("registry_version") or "")
    registry_version_changed = old_registry_version != registry.registry_version
    headings = re.findall(r"^##\s+(\S+)", changelog, re.M)

    def changelog_mentions(identifier: str) -> bool:
        section = None
        for line in changelog.splitlines():
            if line.startswith("## "):
                section = line.split()[1]
                continue
            if identifier in line and section == registry.registry_version:
                return True
        return False

    # Load the old entries through the same model as the current registry, so
    # default-valued fields are compared canonically rather than as missing.
    old_metrics = {
        item["id"]: Metric.model_validate(item).model_dump(mode="json")
        for item in old.get("metrics") or []
    }
    new_metrics = {item["id"]: item for item in registry.model_dump(mode="json")["metrics"]}
    changed: list[tuple[str, str]] = []
    for identifier in sorted(set(old_metrics) | set(new_metrics)):
        before = old_metrics.get(identifier)
        after = new_metrics.get(identifier)
        if before is None:
            changed.append((identifier, "added"))
            continue
        if after is None:
            changed.append((identifier, "removed"))
            continue
        fields = [
            field
            for field in SEMANTIC_METRIC_FIELDS
            if _canonical(before.get(field)) != _canonical(after.get(field))
        ]
        if fields:
            changed.append((identifier, fields[0]))
            if int(after.get("version") or 0) <= int(before.get("version") or 0):
                changed.append((identifier, "version not bumped"))

    old_parameters = {
        item["id"]: Parameter.model_validate(item).model_dump(mode="json")
        for item in old.get("parameters") or []
    }
    new_parameters = {item["id"]: item for item in registry.model_dump(mode="json")["parameters"]}
    for identifier in sorted(set(old_parameters) | set(new_parameters)):
        before = old_parameters.get(identifier)
        after = new_parameters.get(identifier)
        if before is None or after is None:
            changed.append((identifier, "parameter added/removed"))
            continue
        fields = [
            field
            for field in SEMANTIC_PARAMETER_FIELDS
            if _canonical(before.get(field)) != _canonical(after.get(field))
        ]
        if fields:
            changed.append((identifier, fields[0]))

    if not changed:
        report.check(True, "change_control", f"no semantic change against {git_ref}")
        return

    report.check(
        registry_version_changed,
        "change_control.version",
        f"registry_version must change (still {registry.registry_version})",
    )
    report.check(
        registry.registry_version in headings,
        "change_control.changelog",
        f"docs/metric-changes.md has no '## {registry.registry_version}' section",
    )
    for identifier, detail in changed:
        if not changelog_mentions(identifier):
            report.check(
                False,
                "change_control.changelog",
                f"{identifier} changed ({detail}) without a changelog entry",
            )
    report.note("change_control", f"{len(changed)} semantic change(s) against {git_ref}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="published data directory")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument(
        "--published-only",
        action="store_true",
        help="check published artifacts only (deploy gate)",
    )
    parser.add_argument(
        "--against-git",
        metavar="REF",
        help="require a version bump and changelog for semantic changes since REF",
    )
    args = parser.parse_args()

    data = args.data.resolve()
    report = Report()
    try:
        registry = load_registry()
    except Exception as error:  # noqa: BLE001
        print(f"registry invalid: {error}", file=sys.stderr)
        return 1

    _check_registry(registry, report)
    _check_parameters(registry, report)

    if not data.exists():
        report.check(False, "data", f"{data} does not exist")
    else:
        corpus = load_corpus(data)
        _check_source_layers(corpus, registry, report)
        _check_published_registry(registry, data, report)
        _check_audit(data, registry, report)
        _check_validation(data, report)
        _check_manifest_marts(data, report)
        if not args.published_only:
            _check_numeric_coverage(corpus, registry, report)
            _check_identity(report)
            _check_client_formatting(report)

    if args.against_git:
        _check_change_control(registry, args.against_git, report)

    for note in report.notes:
        print(f"note: {note}")
    for warning in report.warnings:
        print(f"warning: {warning}")
    for error in report.errors:
        print(f"error: {error}")

    failed = bool(report.errors) or (args.strict and bool(report.warnings))
    print(f"{'FAIL' if failed else 'PASS'} metrics check: {report.summary()}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
