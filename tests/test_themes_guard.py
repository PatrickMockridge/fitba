from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_themes", ROOT / "scripts" / "check_themes.py")
assert SPEC and SPEC.loader
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


def _family_theme() -> dict:
    return {
        "status": "available",
        "metrics": {
            "groups": [
                {"family": family, "provider_rating": 7.0, "starts": 1, "starter_minutes": 90}
                for family in ("GK", "CB", "FB/WB", "MID", "AM/WM", "W", "ST")
            ]
        },
    }


def _shape_theme() -> dict:
    return {
        "status": "available",
        "metrics": {
            "coverage": {"fixtures_total": 3, "unknown_shapes": 1},
            "groups": [
                {"group": "two_cb", "matches": 1, "wb_starts_pm": 0.0, "wf_starts_pm": 2.0},
                {"group": "three_cb", "matches": 1, "wb_starts_pm": 2.0, "wf_starts_pm": 0.0},
                {"group": "unknown", "matches": 1, "wb_starts_pm": 0.0, "wf_starts_pm": 0.0},
            ],
        },
    }


def test_family_missing_group_and_bad_rating_fail():
    errors: list[str] = []
    theme = _family_theme()
    theme["metrics"]["groups"] = theme["metrics"]["groups"][:-1]
    GUARD._check_family(theme, errors)
    assert any("missing groups" in error for error in errors)

    errors = []
    theme = _family_theme()
    theme["metrics"]["groups"][0]["provider_rating"] = 12
    GUARD._check_family(theme, errors)
    assert any("out of range" in error for error in errors)


def test_shape_match_count_mismatch_fails():
    errors: list[str] = []
    theme = _shape_theme()
    theme["metrics"]["coverage"]["fixtures_total"] = 4
    GUARD._check_shape(theme, errors)
    assert any("!=" in error for error in errors)


def test_cover_loan_out_and_bad_category_fail():
    errors: list[str] = []
    theme = {
        "metrics": {
            "groups": [
                {
                    "group": "CB",
                    "top_share": 0.4,
                    "items": [
                        {"name": "A", "category": "loan_out"},
                        {"name": "B", "category": "unknown"},
                    ],
                }
            ]
        }
    }
    GUARD._check_cover(theme, errors)
    assert any("invalid category" in error for error in errors)
    assert any("loan-out" in error for error in errors)


def test_balance_reconciles_goals():
    errors: list[str] = []
    theme = {
        "metrics": {
            "season": {"gf": 10, "ga": 10},
            "goals_by_family": {
                "attack": 6,
                "midfield": 2,
                "defence": 2,
                "total": 10,
                "attack_share": 0.6,
            },
        }
    }
    GUARD._check_balance(theme, {"summary": {"gf": 10, "ga": 10}}, errors)
    assert errors == []
    theme["metrics"]["season"]["gf"] = 9
    GUARD._check_balance(theme, {"summary": {"gf": 10, "ga": 10}}, errors)
    assert any("season gf" in error for error in errors)


def test_mission_requires_pillars_and_no_ratings():
    errors: list[str] = []
    theme = {
        "status": "available",
        "metrics": {"pillars": [], "coverage": {"ratings_used": True}},
        "links": [],
    }
    GUARD._check_mission(theme, errors)
    assert any("5 pillars" in error for error in errors)
    assert any("ratings_used" in error for error in errors)
    assert any("/history/" in error for error in errors)


def test_narrative_scan_collects_reads_and_caveats():
    document = {
        "themes": [
            {
                "theme_id": "x",
                "headline": "Headline",
                "read": "Read",
                "caveats": ["Caveat"],
                "evidence": [{"label": "L", "note": "N"}],
            }
        ]
    }
    text = " ".join(GUARD._narrative_strings(document))
    assert "Read" in text
    assert "Caveat" in text
    assert "N" in text


def test_forbidden_host_is_detected():
    text = " ".join(GUARD._strings({"url": "https://www.transfermarkt.com/x"}))
    assert "transfermarkt." in text
