from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data" / "generated"
SPEC = importlib.util.spec_from_file_location("check_themes", ROOT / "scripts" / "check_themes.py")
assert SPEC and SPEC.loader
check_themes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_themes)


def _run(data: Path) -> int:
    previous = sys.argv
    try:
        sys.argv = ["check_themes", "--data", str(data)]
        return check_themes.main()
    finally:
        sys.argv = previous


def test_guard_passes_on_published_case() -> None:
    assert _run(DATA) == 0


def test_guard_catches_unknown_claim(tmp_path) -> None:
    copy = tmp_path / "generated"
    shutil.copytree(DATA, copy)
    path = copy / "themes" / "aberdeen.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["claims"][0]["id"] = "tampered"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert _run(copy) == 1
