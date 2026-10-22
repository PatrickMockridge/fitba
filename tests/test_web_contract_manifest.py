from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "web" / "contracts" / "surfaces.json"

IDENTITY = "Aberdeen FC, without the noise."

# Pinned independently of the manifest. An agent can edit surfaces.json, but it
# must also edit this test (and pass owner review) to remove a contracted
# surface. Additions are allowed.
PINNED_MARKERS = {
    "/": {
        "home.hero",
        "home.matchday",
        "home.off-pitch",
        "home.squad",
        "home.news-rumours",
        "home.competitions",
        "home.standings",
    },
    "/matchday/": {
        "matchday.fixture",
        "matchday.matchup-read",
        "matchday.predicted-xis",
        "matchday.lineup",
        "matchday.lineup.pitch",
        "matchday.lineup.formation-confidence",
        "matchday.lineup.selection-weights",
        "matchday.lineup.availability",
        "matchday.lineup.contenders",
        "matchday.not-considered",
        "matchday.form-guide",
        "matchday.style",
        "matchday.strength",
        "matchday.themes",
        "matchday.head-to-head",
        "matchday.coverage",
    },
    "/themes/": {
        "themes.hero",
        "themes.scope",
        "themes.season",
        "themes.theme",
        "themes.evidence",
        "themes.mission",
        "themes.metric-family-balance",
        "themes.metric-wing-back-tax",
        "themes.metric-cover-question",
        "themes.metric-leaky-boat",
        "themes.metric-mission-check",
        "themes.coverage",
        "themes.coverage.missing",
    },
    "/recruitment/": {
        "recruitment.hero",
        "recruitment.needs-board",
        "recruitment.needs-summary",
        "recruitment.needs-family",
        "recruitment.needs-priority",
        "recruitment.needs-confidence",
        "recruitment.needs-market-route",
        "recruitment.needs-roster",
        "recruitment.needs-players",
        "recruitment.transfer-summary",
        "recruitment.rumour-summary",
        "recruitment.profile",
        "recruitment.forum-signals",
    },
    "/transfers/": {
        "transfers.hero",
        "transfers.board",
        "transfers.summary",
        "transfers.register",
        "transfers.card",
        "transfers.card.verification",
        "transfers.card.identity",
        "transfers.card.fee",
        "transfers.card.loan-terms",
        "transfers.card.sources",
        "transfers.sell-on",
        "transfers.audit",
        "transfers.coverage",
    },
    "/loans/": {
        "loans.hero",
        "loans.out",
        "loans.in",
        "loans.card",
        "transfers.card.loan-terms",
        "loans.coverage",
    },
    "/history/": {
        "history.hero",
        "history.scorecard",
        "history.thesis",
        "history.season-table",
        "history.people",
        "history.baseline",
        "history.managers",
        "history.honours",
        "history.read",
        "history.coverage",
    },
    "/about/": {
        "about.hero",
        "about.audience",
        "about.club-side",
        "about.cormack",
        "about.line",
    },
}

PINNED_COLUMNS = {
    "home.standings": ["#", "Club", "P", "W", "D", "L", "GF", "GA", "GD", "Pts", "Form"],
    "matchday.form-guide": ["Split", "P", "W-D-L", "Pts", "PPG", "GF", "GA", "Shots"],
    "matchday.style": ["Split", "Shots for", "Shots against", "Shot share"],
    "matchday.head-to-head": ["Date", "Match", "Score", "Aberdeen"],
    "recruitment.needs-players": [
        "Player",
        "Category",
        "Starts",
        "Minutes",
        "Sub apps",
        "Availability",
    ],
    "transfers.sell-on": ["Player", "Buyer", "Sale", "Clause", "Confidence", "Source"],
    "history.season-table": [
        "Season",
        "Manager(s)",
        "League",
        "Pos",
        "Pts",
        "Honours",
        "Review",
    ],
    "history.baseline": ["Season", "Pos", "Pts"],
    "history.managers": ["Manager", "Dates", "Pld", "W-D-L", "GF", "GA", "Pts", "PPG"],
    "history.coverage": [
        "Season",
        "League",
        "Transfers",
        "Lineups",
        "Match stats",
        "Review",
    ],
}

PINNED_MINIMUMS = {
    "matchday.lineup": 2,
    "matchday.lineup.pitch": 2,
    "transfers.card": 50,
    "themes.theme": 5,
    "themes.evidence": 5,
    "recruitment.needs-family": 7,
    "recruitment.needs-priority": 7,
    "recruitment.needs-confidence": 7,
    "recruitment.needs-market-route": 7,
    "recruitment.needs-roster": 7,
    "recruitment.needs-players": 7,
}

PINNED_INDICATORS = {
    "/": {"unknown": 1, "freshness": 1, "source": 1},
    "/matchday/": {
        "basis": 2,
        "confidence": 2,
        "availability": 1,
        "unknown": 1,
        "source": 1,
    },
    "/themes/": {"basis": 5, "confidence": 5, "unknown": 1, "source": 1},
    "/recruitment/": {
        "confidence": 2,
        "availability": 2,
        "unknown": 1,
        "source": 1,
    },
    "/transfers/": {"confidence": 2, "unknown": 1, "source": 1},
    "/loans/": {"unknown": 1, "source": 1},
    "/history/": {"confidence": 1, "source": 1},
}


def load() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def full_state(document: dict, path: str) -> dict:
    for surface in document["surfaces"]:
        if surface["path"] == path:
            assert "full" in surface["states"], f"{path} has no full state"
            assert "full" in surface.get("ci_states", []), f"{path} does not require full in CI"
            return surface["states"]["full"]
    raise AssertionError(f"missing surface {path}")


def assert_contract(document: dict) -> None:
    assert document["identity"]["line"].strip() == IDENTITY
    for path, expected_markers in PINNED_MARKERS.items():
        state = full_state(document, path)
        actual_markers = {spec["id"] for spec in state.get("markers", [])}
        missing = expected_markers - actual_markers
        assert not missing, f"{path} lost contracted markers: {sorted(missing)}"
        for marker, expected_headers in PINNED_COLUMNS.items():
            if marker in actual_markers:
                assert state["columns"][marker] == expected_headers, (
                    f"{marker} column contract changed"
                )
        for marker, minimum in PINNED_MINIMUMS.items():
            spec = next(
                (item for item in state.get("markers", []) if item["id"] == marker),
                None,
            )
            if spec is not None:
                assert spec.get("min", 1) >= minimum, f"{path} lowered the minimum for {marker}"
        for indicator, minimum in PINNED_INDICATORS.get(path, {}).items():
            assert state.get("indicators", {}).get(indicator, 0) >= minimum, (
                f"{path} lowered the {indicator} indicator minimum"
            )


def test_manifest_matches_the_pinned_contract():
    assert_contract(load())


def test_removing_a_marker_fails_the_pinned_contract():
    document = load()
    full_state(document, "/")["markers"] = [
        spec for spec in full_state(document, "/")["markers"] if spec["id"] != "home.standings"
    ]
    with pytest.raises(AssertionError, match=r"home\.standings"):
        assert_contract(document)


def test_lowering_a_cardinality_fails_the_pinned_contract():
    document = load()
    state = full_state(document, "/recruitment/")
    for spec in state["markers"]:
        if spec["id"] == "recruitment.needs-family":
            spec["min"] = 1
    with pytest.raises(AssertionError, match="needs-family"):
        assert_contract(document)


def test_removing_a_column_fails_the_pinned_contract():
    document = load()
    state = full_state(document, "/")
    state["columns"]["home.standings"] = ["#", "Club", "Pts"]
    with pytest.raises(AssertionError, match="column contract changed"):
        assert_contract(document)


def test_removing_full_from_ci_states_fails_the_pinned_contract():
    document = load()
    for surface in document["surfaces"]:
        if surface["path"] == "/transfers/":
            surface["ci_states"] = ["empty"]
    with pytest.raises(AssertionError, match="full"):
        assert_contract(document)
