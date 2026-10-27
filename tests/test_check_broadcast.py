from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_broadcast", ROOT / "scripts" / "check_broadcast.py"
)
assert SPEC is not None and SPEC.loader is not None
CHECK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECK
SPEC.loader.exec_module(CHECK)


def test_the_published_broadcast_document_passes() -> None:
    assert CHECK.check() == []


def test_the_checked_in_schema_is_current() -> None:
    from fitba.publish.broadcast import broadcast_schema

    assert CHECK._load(CHECK.SCHEMA) == broadcast_schema()
