from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_page_budget", ROOT / "scripts" / "check_page_budget.py"
)
assert SPEC is not None and SPEC.loader is not None
CHECK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECK
SPEC.loader.exec_module(CHECK)


def _config(tmp_path: Path, *, config_path: Path, content: dict) -> Path:
    config_path.write_text(yaml.safe_dump(content), encoding="utf-8")
    cast(Any, CHECK).CONFIG = config_path
    return tmp_path


def _write(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


def test_a_payload_under_budget_passes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(CHECK, "CONFIG", tmp_path / "budgets.yaml")
    _config(
        tmp_path,
        config_path=CHECK.CONFIG,
        content={"json": {"entities/scouted.json": 100}},
    )
    data = tmp_path / "data"
    _write(data / "entities" / "scouted.json", 50)
    assert CHECK.check(data) == []


def test_an_oversize_payload_names_the_sharding_remedy(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(CHECK, "CONFIG", tmp_path / "budgets.yaml")
    _config(
        tmp_path,
        config_path=CHECK.CONFIG,
        content={"json": {"entities/scouted.json": 100}},
    )
    data = tmp_path / "data"
    _write(data / "entities" / "scouted.json", 101)
    errors = CHECK.check(data)
    assert any("shard or lazy-load" in error for error in errors)


def test_a_configured_pattern_with_no_file_is_an_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(CHECK, "CONFIG", tmp_path / "budgets.yaml")
    _config(
        tmp_path,
        config_path=CHECK.CONFIG,
        content={"json": {"entities/scouted.json": 100}},
    )
    errors = CHECK.check(tmp_path / "data")
    assert any("no file matches" in error for error in errors)


def test_page_budgets_are_measured_on_built_html(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(CHECK, "CONFIG", tmp_path / "budgets.yaml")
    _config(
        tmp_path,
        config_path=CHECK.CONFIG,
        content={"pages": {"/search/": 100}, "built_json": {"search/scouted.json": 100}},
    )
    out = tmp_path / "out"
    _write(out / "search" / "index.html", 50)
    _write(out / "search" / "scouted.json", 50)
    assert CHECK.check(tmp_path / "data", out) == []


def test_an_oversize_page_is_reported(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(CHECK, "CONFIG", tmp_path / "budgets.yaml")
    _config(
        tmp_path,
        config_path=CHECK.CONFIG,
        content={"pages": {"/search/": 100}},
    )
    out = tmp_path / "out"
    _write(out / "search" / "index.html", 101)
    errors = CHECK.check(tmp_path / "data", out)
    assert any("/search/" in error and "budget 100" in error for error in errors)


def test_a_missing_built_page_is_an_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(CHECK, "CONFIG", tmp_path / "budgets.yaml")
    _config(
        tmp_path,
        config_path=CHECK.CONFIG,
        content={"pages": {"/search/": 100}},
    )
    errors = CHECK.check(tmp_path / "data", tmp_path / "out")
    assert any("no built HTML for /search/" in error for error in errors)


def test_the_real_budgets_name_the_lazy_scouting_payloads() -> None:
    config = yaml.safe_load(
        (ROOT / "config" / "web-budgets.yaml").read_text(encoding="utf-8")
    )
    assert "entities/scouted.json" in config["json"]
    assert "scouting/search/players-*.json" in config["json"]
    assert "/search/" in config["pages"]
    assert "/scouting/search/" in config["pages"]
