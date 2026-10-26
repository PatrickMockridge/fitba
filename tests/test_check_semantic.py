from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_semantic", ROOT / "scripts" / "check_semantic.py"
)
assert SPEC is not None and SPEC.loader is not None
CHECK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECK
SPEC.loader.exec_module(CHECK)


def _write(path: Path, document) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def _data(tmp_path: Path, *, index_entities: list[dict], scouted: list[dict] | None = None) -> Path:
    data = tmp_path / "generated"
    _write(
        data / "entities" / "index.json",
        {"schema_version": "1.0.0", "state": "available", "entities": index_entities},
    )
    _write(
        data / "entities" / "scouted.json",
        {"schema_version": "1.0.0", "state": "available", "entities": scouted or []},
    )
    _write(
        data / "page-meta.json",
        {
            "surfaces": {
                "home": {
                    "route_patterns": ["/"],
                    "layers": [],
                    "no_layers_reason": "Editorial page.",
                    "metrics": [],
                }
            }
        },
    )
    _write(data / "definitions.json", {"entries": []})
    _write(data / "changelog.json", {"append_only": True, "entries": []})
    _write(data / "fixtures" / "index.json", {"fixtures": []})
    _write(data / "themes" / "aberdeen.json", {"claims": []})
    _write(data / "provenance.json", {"layers": []})
    _write(data / "metrics" / "registry.json", {"metrics": []})
    return data


def _page(entity_id: str, href: str, kind: str = "page") -> dict:
    return {
        "entity_id": entity_id,
        "type": kind,
        "name": entity_id,
        "href": href,
        "indexable": True,
    }


def test_clean_data_passes(tmp_path: Path) -> None:
    data = _data(tmp_path, index_entities=[_page("page:home", "/")])
    assert CHECK.check_data(data) == []


def test_duplicate_entity_id_is_reported(tmp_path: Path) -> None:
    data = _data(
        tmp_path,
        index_entities=[_page("page:home", "/"), _page("page:home", "/")],
    )
    errors = CHECK.check_data(data)
    assert any("duplicate entity id page:home" in error for error in errors)


def test_an_entity_href_must_be_internal(tmp_path: Path) -> None:
    data = _data(tmp_path, index_entities=[_page("page:home", "https://example.com/")])
    errors = CHECK.check_data(data)
    assert any("href is not internal" in error for error in errors)


def test_scouted_entities_may_not_overlap_core(tmp_path: Path) -> None:
    data = _data(
        tmp_path,
        index_entities=[_page("player:api:player:7", "/scouting/player/7/", "player")],
        scouted=[{"i": "7", "n": "Player"}],
    )
    errors = CHECK.check_data(data)
    assert any("overlaps core entities" in error for error in errors)


def test_a_stale_search_index_is_rejected(tmp_path: Path) -> None:
    data = _data(tmp_path, index_entities=[_page("page:home", "/")])
    _write(data / "search-index.json", {"players": []})
    errors = CHECK.check_data(data)
    assert any("search-index.json still exists" in error for error in errors)


def test_a_missing_fragment_fails_page_mode(tmp_path: Path) -> None:
    data = _data(
        tmp_path,
        index_entities=[_page("page:scouting", "/scouting/#priority-profiles")],
    )
    out = tmp_path / "out"
    _write_page = out / "scouting" / "index.html"
    _write_page.parent.mkdir(parents=True, exist_ok=True)
    _write_page.write_text("<html><body>No anchor</body></html>", encoding="utf-8")
    errors = CHECK.check_pages(data, out)
    assert any("missing fragment #priority-profiles" in error for error in errors)


def test_a_present_fragment_and_missing_page_both_resolve(tmp_path: Path) -> None:
    data = _data(
        tmp_path,
        index_entities=[
            _page("page:scouting", "/scouting/#priority-profiles"),
            _page("page:search", "/search/"),
        ],
    )
    out = tmp_path / "out"
    scouting = out / "scouting" / "index.html"
    scouting.parent.mkdir(parents=True, exist_ok=True)
    scouting.write_text('<section id="priority-profiles"></section>', encoding="utf-8")
    errors = CHECK.check_pages(data, out)
    assert any("missing built page for /search/" in error for error in errors)
    assert not any("priority-profiles" in error for error in errors)


def test_a_claim_must_point_at_the_claims_surface(tmp_path: Path) -> None:
    data = _data(
        tmp_path,
        index_entities=[
            {
                "entity_id": "claim:team-now",
                "type": "claim",
                "name": "The team now",
                "href": "/analysis/#claim-team-now",
                "indexable": True,
            }
        ],
    )
    _write(data / "themes" / "aberdeen.json", {"claims": [{"id": "team-now"}]})
    errors = CHECK.check_data(data)
    assert any("still points at the removed analysis anchors" in error for error in errors)
    assert any("is not the claims surface" in error for error in errors)


def test_page_meta_rejects_an_unknown_layer(tmp_path: Path) -> None:
    data = _data(tmp_path, index_entities=[_page("page:home", "/")])
    _write(
        data / "page-meta.json",
        {
            "surfaces": {
                "home": {
                    "route_patterns": ["/"],
                    "layers": ["not_a_layer"],
                }
            }
        },
    )
    errors = CHECK.check_data(data)
    assert any("unknown layer not_a_layer" in error for error in errors)


def test_definitions_reject_an_unknown_metric(tmp_path: Path) -> None:
    data = _data(tmp_path, index_entities=[_page("page:home", "/")])
    _write(
        data / "definitions.json",
        {
            "entries": [
                {
                    "id": "def.example",
                    "metric_ids": ["unknown.metric"],
                    "provenance": "curated_overlay",
                }
            ]
        },
    )
    errors = CHECK.check_data(data)
    assert any("unknown metric unknown.metric" in error for error in errors)


def test_a_definition_must_resolve_its_anchor(tmp_path: Path) -> None:
    data = _data(tmp_path, index_entities=[_page("page:home", "/")])
    _write(
        data / "definitions.json",
        {
            "entries": [
                {
                    "id": "def.example",
                    "metric_ids": [],
                    "provenance": "curated_overlay",
                    "href": "/glossary/#def-example",
                }
            ]
        },
    )
    out = tmp_path / "out"
    glossary = out / "glossary" / "index.html"
    glossary.parent.mkdir(parents=True, exist_ok=True)
    glossary.write_text("<html><body>No anchor</body></html>", encoding="utf-8")
    errors = CHECK.check_pages(data, out)
    assert any("missing fragment #def-example" in error for error in errors)


def test_definition_related_ids_must_resolve(tmp_path: Path) -> None:
    data = _data(tmp_path, index_entities=[_page("page:home", "/")])
    _write(
        data / "definitions.json",
        {
            "entries": [
                {
                    "id": "def.basis",
                    "metric_ids": [],
                    "provenance": "curated_overlay",
                    "related": ["def.missing"],
                }
            ]
        },
    )
    errors = CHECK.check_data(data)
    assert any("unknown related id def.missing" in error for error in errors)


def test_an_inline_term_must_resolve_to_a_definition(tmp_path: Path) -> None:
    data = _data(tmp_path, index_entities=[_page("page:home", "/")])
    _write(data / "definitions.json", {"entries": []})
    out = tmp_path / "out"
    page = out / "index.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(
        '<span data-definition-term="def.nope">term</span>', encoding="utf-8"
    )
    errors = CHECK.check_pages(data, out)
    assert any("unknown definition term def.nope" in error for error in errors)


def test_changelog_requires_an_append_only_log(tmp_path: Path) -> None:
    data = _data(tmp_path, index_entities=[_page("page:home", "/")])
    _write(data / "changelog.json", {"append_only": False, "entries": []})
    errors = CHECK.check_data(data)
    assert any("append_only must be true" in error for error in errors)
