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
        "matchday.lookahead",
        "matchday.watch",
        "matchday.coverage",
    },
    "/themes/": {
        "themes.redirect",
    },
    "/analysis/": {
        "analysis.hero",
        "analysis.next-up",
        "analysis.availability",
        "analysis.aims",
        "analysis.squad-decisions",
        "analysis.bridges",
        "analysis.coverage",
    },
    "/matches/": {
        "matches.hero",
        "matches.season",
        "matches.upcoming",
    },
    "/analysis/xg/": {
        "xg.hero",
        "xg.model",
        "xg.aggregate",
        "xg.uncertainty",
        "xg.overperformance",
        "xg.style",
        "xg.provider",
        "xg.coverage",
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
        "history.lookup",
        "history.people",
        "history.baseline",
        "history.managers",
        "history.honours",
        "history.read",
        "history.coverage",
    },
    "/squad/": {
        "squad.hero",
        "squad.summary",
        "squad.roster",
        "squad.depth-chart",
        "squad.coverage",
        "squad.role-mix",
        "squad.how-to",
        "squad.source",
    },
    "/scouting/": {
        "scouting.hero",
        "scouting.layer-zero",
        "scouting.weakness-board",
        "scouting.archetypes",
        "scouting.filters",
        "scouting.lenses",
        "scouting.attackers",
        "scouting.goal-scoring",
        "scouting.team-lens",
        "scouting.weights",
        "scouting.league-index",
        "scouting.squad-profile",
        "scouting.coverage",
    },
    "/scouting/search/": {
        "scouting.search.hero",
        "scouting.lenses",
        "scouting.advanced-filters",
        "scouting.search.board",
        "scouting.search.comparison",
        "scouting.search.coverage",
    },
    "/sources/": {
        "sources.hero",
        "sources.layers",
        "sources.registry",
        "sources.migration",
        "sources.availability",
        "sources.excluded",
        "sources.derived",
        "sources.no-raw",
    },
    "/methodology/": {
        "methodology.hero",
        "methodology.sources",
        "methodology.tables",
        "methodology.cutoffs",
        "methodology.cups",
        "methodology.assumptions",
        "methodology.coverage",
        "methodology.reconstruction",
        "methodology.matchday",
        "methodology.transfers",
        "methodology.history",
        "methodology.player-output",
        "methodology.registers",
        "methodology.policy",
    },
    "/about/": {
        "about.hero",
        "about.audience",
        "about.club-side",
        "about.cormack",
        "about.line",
    },
    "/metrics/": {
        "metrics.hero",
        "metrics.summary",
        "metrics.registry",
        "metrics.parameters",
        "metrics.audit",
        "metrics.method",
        "metrics.links",
    },
    "/search/": {
        "search.hero",
        "search.board",
    },
    "/claims/": {
        "claims.hero",
        "claims.register",
        "claims.benchmark",
        "claims.coverage",
    },
    "/glossary/": {
        "glossary.hero",
        "glossary.concepts",
        "glossary.metrics",
    },
    "/unknowns/": {
        "unknowns.hero",
        "unknowns.register",
        "unknowns.no-public-source",
        "unknowns.sources",
    },
    "/status/": {
        "status.hero",
        "status.build",
        "status.update",
        "status.freshness",
        "status.validation",
        "status.metrics",
        "status.consistency",
        "status.sources",
        "status.marts",
        "status.coverage",
    },
}

PINNED_COLUMNS = {
    "home.standings": ["#", "Club", "P", "W", "D", "L", "GF", "GA", "GD", "Pts", "Form"],
    "matchday.form-guide": ["Split", "P", "W-D-L", "Pts", "PPG", "GF", "GA", "Shots"],
    "matchday.style": ["Split", "Shots for", "Shots against", "Shot share"],
    "matchday.head-to-head": ["Date", "Match", "Score", "Aberdeen"],
    "matchday.lookahead": [
        "Date",
        "Competition",
        "Opponent",
        "Venue",
        "Kickoff",
        "Watch",
    ],
    "matches.upcoming": [
        "Date",
        "Competition",
        "Home",
        "Away",
        "Venue",
        "Kickoff",
        "Status",
        "Watch",
    ],
    "analysis.next-up": ["Date", "Competition", "Opponent", "Venue", "Kickoff", "Status"],
    "analysis.aims": ["Aim", "Target", "Current", "Status"],
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
    "xg.managers": [
        "Manager",
        "Stint",
        "Season",
        "Matches",
        "fxG for",
        "fxG against",
        "Goals for",
        "Goals against",
        f"Goals {chr(8722)} fxG for",
        f"Goals {chr(8722)} fxG against",
        "Provider xG for",
        "Provider xG against",
        "Provider basis",
    ],
    "history.managers": ["Manager", "Dates", "Pld", "W-D-L", "GF", "GA", "Pts", "PPG"],
    "history.coverage": [
        "Season",
        "League",
        "Transfers",
        "Lineups",
        "Match stats",
        "Review",
    ],
    "squad.roster": [
        "Player",
        "No.",
        "Role",
        "Age",
        "Status",
        "Starts (all)",
        "Sub (all)",
        "Mins (all)",
        "League mins",
        "Conc",
        "CS",
        "G",
        "A",
        "OG",
        "Rating",
        "Stats",
    ],
    "scouting.layer-zero": [
        "Player",
        "Role",
        "Status",
        "Current mins",
        "Prior rating",
        "Prior mins",
        "Source",
        "Verified",
    ],
    "scouting.weakness-board": [
        "Role family",
        "Players",
        "Minutes",
        "Aberdeen rating",
        "Cohort median",
        "Percentile",
        "Availability",
        "Reading",
    ],
    "scouting.squad-profile": [
        "Player",
        "Role",
        "Mins",
        "Rating",
        "Pct",
        "G+A/90",
        "Shots/90",
        "Dribbles/90",
        "Passes/90",
        "Pass %",
        "Key passes/90",
        "Tackles/90",
        "Interceptions/90",
        "Duels won %",
    ],
    "scouting.goal-scoring": [
        "Player",
        "Club",
        "League",
        "Age",
        "Mins",
        "Goals",
        "Assists",
        "Goals/90",
        "G+A/90",
        "Shots/90",
        "Conversion",
        "Priority",
    ],
    "scouting.team-lens": [
        "Player",
        "Club",
        "League",
        "Team",
        "Team PPG %",
        "Adj %",
        "Lift",
        "Priority",
    ],
    "scouting.search.board": [
        "Player",
        "Club",
        "Team",
        "Lift",
        "League",
        "Nationality",
        "Role",
        "Age",
        "Mins",
        "Rating",
        "Pct",
        "Adj Pct",
        "Value index",
        "Priority",
        "Europe",
        "G+A/90",
        "Dribbles/90",
        "Passes/90",
        "Pass %",
        "Key passes/90",
        "Tackles/90",
        "Interceptions/90",
        "Duels won %",
        "Profile",
    ],
    "xg.aggregate": [
        "Scope",
        "Matches",
        "fxG",
        "80% model range",
        "xG per shot",
        "Goals",
        "80% goals range",
        "Goals " + chr(8722) + " fxG",
    ],
    "matches.season": ["Date", "Competition", "Home", "Score", "Away", "Result", "Depth"],
    "sources.layers": ["Layer", "Primary", "Fallback", "Status", "Rows", "Scope"],
    "sources.registry": ["Source", "Lane", "Primary layers", "Rows", "Last checked"],
    "methodology.sources": ["Source", "Publication lane", "Rows", "Last checked"],
    "metrics.registry": [
        "Metric",
        "Definition",
        "Formula",
        "Basis",
        "Source",
        "Coverage",
        "Verification",
        "Status",
    ],
    "metrics.parameters": [
        "Parameter",
        "Value",
        "Unit",
        "Used by",
        "Config",
        "Verification",
        "Status",
    ],
}

PINNED_MINIMUMS = {
    "matchday.lineup": 2,
    "matchday.lineup.pitch": 2,
    "transfers.card": 50,
    "recruitment.needs-family": 7,
    "recruitment.needs-priority": 7,
    "recruitment.needs-confidence": 7,
    "recruitment.needs-market-route": 7,
    "recruitment.needs-roster": 7,
    "recruitment.needs-players": 7,
    "metrics.registry": 52,
    "metrics.parameters": 14,
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
    "/recruitment/": {
        "confidence": 2,
        "availability": 2,
        "unknown": 1,
        "source": 1,
    },
    "/transfers/": {"confidence": 2, "unknown": 1, "source": 1},
    "/loans/": {"unknown": 1, "source": 1},
    "/history/": {"confidence": 1, "source": 1},
    "/squad/": {"unknown": 1, "source": 1},
    "/scouting/": {
        "availability": 2,
        "basis": 1,
        "confidence": 1,
        "unknown": 1,
        "source": 1,
    },
    "/scouting/search/": {"basis": 1, "confidence": 1, "unknown": 1, "source": 1},
    "/sources/": {"unknown": 1, "source": 1},
    "/methodology/": {"unknown": 1, "source": 1},
}


def load() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def full_state(document: dict, path: str) -> dict:
    for surface in document["surfaces"]:
        if surface["path"] == path:
            ci_states = surface.get("ci_states", [])
            assert ci_states, f"{path} has no CI state"
            state = next((name for name in ci_states if name in surface["states"]), None)
            assert state is not None, f"{path} CI state is not defined"
            return surface["states"][state]
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
    with pytest.raises(AssertionError, match=r"lost contracted markers|full"):
        assert_contract(document)
