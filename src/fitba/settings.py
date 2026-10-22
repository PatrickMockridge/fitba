"""Project paths and configuration loading."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
# Load local secrets from .env; the file is gitignored and never committed.
load_dotenv(ROOT / ".env")

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


@lru_cache(maxsize=1)
def cups() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "cups.yaml")


@lru_cache(maxsize=1)
def european_competitions() -> dict[str, Any]:
    path = REFERENCE_DIR / "european_competitions.yaml"
    if not path.exists():
        return {"season": None, "aberdeen": {"in_europe": False, "competitions": []}}
    return load_yaml(path)


@lru_cache(maxsize=1)
def history_policy() -> dict[str, Any]:
    path = CONFIG_DIR / "history.yaml"
    return load_yaml(path) if path.exists() else {}


@lru_cache(maxsize=1)
def history_era() -> dict[str, Any]:
    path = REFERENCE_DIR / "history" / "era.yaml"
    return load_yaml(path) if path.exists() else {"era": {}}


@lru_cache(maxsize=1)
def history_staff() -> dict[str, Any]:
    path = REFERENCE_DIR / "history" / "staff.yaml"
    return load_yaml(path) if path.exists() else {"people": []}


@lru_cache(maxsize=1)
def history_honours() -> dict[str, Any]:
    path = REFERENCE_DIR / "history" / "honours.yaml"
    return load_yaml(path) if path.exists() else {"honours": []}


@lru_cache(maxsize=1)
def history_markets() -> dict[str, Any]:
    path = REFERENCE_DIR / "history" / "markets.yaml"
    return load_yaml(path) if path.exists() else {"markets": []}


@lru_cache(maxsize=1)
def history_seasons() -> dict[str, Any]:
    path = REFERENCE_DIR / "history" / "seasons"
    if not path.exists():
        return {"seasons": []}
    seasons = []
    for file in sorted(path.glob("*.yaml")):
        document = load_yaml(file)
        if document:
            seasons.append(document)
    return {"seasons": seasons}


@lru_cache(maxsize=1)
def source_ids() -> dict[str, Any]:
    return load_yaml(REFERENCE_DIR / "source_ids.yaml")


@lru_cache(maxsize=1)
def matchday() -> dict[str, Any]:
    path = CONFIG_DIR / "matchday.yaml"
    return load_yaml(path) if path.exists() else {}


@lru_cache(maxsize=1)
def themes() -> dict[str, Any]:
    path = CONFIG_DIR / "themes.yaml"
    return load_yaml(path) if path.exists() else {}


@lru_cache(maxsize=1)
def fixtures_policy() -> dict[str, Any]:
    path = CONFIG_DIR / "fixtures.yaml"
    return load_yaml(path) if path.exists() else {}


@lru_cache(maxsize=1)
def xg_policy() -> dict[str, Any]:
    path = CONFIG_DIR / "xg.yaml"
    return load_yaml(path) if path.exists() else {}


@lru_cache(maxsize=1)
def confidence_policy() -> dict[str, Any]:
    path = CONFIG_DIR / "confidence.yaml"
    return load_yaml(path) if path.exists() else {}


@lru_cache(maxsize=1)
def provenance() -> dict[str, Any]:
    path = CONFIG_DIR / "provenance.yaml"
    return load_yaml(path) if path.exists() else {"layers": [], "excluded": []}


@lru_cache(maxsize=1)
def league_migration() -> dict[str, Any]:
    path = CONFIG_DIR / "league_migration.yaml"
    return load_yaml(path) if path.exists() else {}


@lru_cache(maxsize=1)
def availability_policy() -> dict[str, Any]:
    path = CONFIG_DIR / "availability.yaml"
    return load_yaml(path) if path.exists() else {}


@lru_cache(maxsize=1)
def availability_ledger() -> dict[str, Any]:
    path = REFERENCE_DIR / "availability.yaml"
    return load_yaml(path) if path.exists() else {"entries": []}


@lru_cache(maxsize=1)
def availability_candidates() -> dict[str, Any]:
    path = REFERENCE_DIR / "availability.candidates.yaml"
    return load_yaml(path) if path.exists() else {"candidates": []}


@lru_cache(maxsize=1)
def needs_policy() -> dict[str, Any]:
    path = CONFIG_DIR / "needs.yaml"
    return load_yaml(path) if path.exists() else {}


@lru_cache(maxsize=1)
def transfers() -> dict[str, Any]:
    return load_yaml(REFERENCE_DIR / "transfers.yaml")


@lru_cache(maxsize=1)
def transfer_policy() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "transfers.yaml")


@lru_cache(maxsize=1)
def transfer_positions() -> dict[str, Any]:
    path = REFERENCE_DIR / "transfer_player_positions.yaml"
    if not path.exists():
        return {"players": []}
    return load_yaml(path)


@lru_cache(maxsize=1)
def transfer_plausibility() -> dict[str, Any]:
    path = REFERENCE_DIR / "transfer_plausibility.yaml"
    if not path.exists():
        return {"accepted": []}
    return load_yaml(path)


@lru_cache(maxsize=1)
def sell_on_clauses() -> dict[str, Any]:
    path = REFERENCE_DIR / "sell_on_clauses.yaml"
    if not path.exists():
        return {"clauses": []}
    return load_yaml(path)


@lru_cache(maxsize=1)
def transfer_gaps() -> dict[str, Any]:
    path = REFERENCE_DIR / "transfer_gaps.yaml"
    if not path.exists():
        return {"gaps": []}
    return load_yaml(path)


@lru_cache(maxsize=1)
def players() -> dict[str, Any]:
    return load_yaml(REFERENCE_DIR / "players.yaml")


@lru_cache(maxsize=1)
def contracts() -> dict[str, Any]:
    return load_yaml(REFERENCE_DIR / "contracts.yaml")


@lru_cache(maxsize=1)
def rumours() -> dict[str, Any]:
    path = REFERENCE_DIR / "rumours.yaml"
    if not path.exists():
        return {"rumours": [], "opinions": []}
    return load_yaml(path)


@lru_cache(maxsize=1)
def engagement() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "engagement.yaml")


@lru_cache(maxsize=1)
def roles() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "roles.yaml")


@lru_cache(maxsize=1)
def shape_notes() -> dict[str, Any]:
    path = REFERENCE_DIR / "shape_notes.yaml"
    if not path.exists():
        return {"matches": []}
    return load_yaml(path)


@lru_cache(maxsize=1)
def role_notes() -> dict[str, Any]:
    path = REFERENCE_DIR / "role_notes.yaml"
    if not path.exists():
        return {"players": []}
    return load_yaml(path)


@lru_cache(maxsize=1)
def player_attributes() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "player_attributes.yaml")


@lru_cache(maxsize=1)
def player_attributes_overrides() -> dict[str, Any]:
    path = REFERENCE_DIR / "player_attributes_overrides.yaml"
    if not path.exists():
        return {"players": []}
    return load_yaml(path)


def ensure_dirs() -> None:
    for path in (CACHE_DIR, NORMALIZED_DIR, MARTS_DIR, WAREHOUSE_DIR, REPORTS_DIR, WEB_DATA_DIR):
        path.mkdir(parents=True, exist_ok=True)
