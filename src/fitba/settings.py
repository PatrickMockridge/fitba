"""Project paths and configuration loading."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
REFERENCE_DIR = ROOT / "reference"
CONTRACTS_DIR = ROOT / "contracts"
CACHE_DIR = ROOT / ".cache"
DATA_DIR = ROOT / "data"
NORMALIZED_DIR = DATA_DIR / "normalized"
MARTS_DIR = DATA_DIR / "marts"
WAREHOUSE_DIR = DATA_DIR / "warehouse"
WAREHOUSE_PATH = WAREHOUSE_DIR / "fitba.duckdb"
REPORTS_DIR = ROOT / "reports"
WEB_DATA_DIR = ROOT / "web" / "data" / "generated"


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@lru_cache(maxsize=1)
def competitions() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "competitions.yaml")


@lru_cache(maxsize=1)
def source_registry() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "sources.yaml")


@lru_cache(maxsize=1)
def publication() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "publication.yaml")


@lru_cache(maxsize=1)
def teams() -> dict[str, Any]:
    return load_yaml(REFERENCE_DIR / "teams.yaml")


@lru_cache(maxsize=1)
def aberdeen() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "clubs" / "aberdeen.yaml")


@lru_cache(maxsize=1)
def scouting_leagues() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "scouting" / "leagues.yaml")


@lru_cache(maxsize=1)
def disciplinary() -> dict[str, Any]:
    return load_yaml(REFERENCE_DIR / "disciplinary.yaml")


def ensure_dirs() -> None:
    for path in (CACHE_DIR, NORMALIZED_DIR, MARTS_DIR, WAREHOUSE_DIR, REPORTS_DIR, WEB_DATA_DIR):
        path.mkdir(parents=True, exist_ok=True)
