from fitba.ingest.player_attributes import (
    AttributeCandidate,
    _foot_from_text,
    _validate_override,
    resolve_attributes,
)
from fitba.settings import player_attributes as attributes_config

CONFIG = attributes_config()


class FakeSource:
    status = "used"

    def __init__(self, name: str, candidates: list[AttributeCandidate]) -> None:
        self.name = name
        self._candidates = candidates

    def candidates(self, player):
        return self._candidates


def _candidate(attribute: str, value: str, *, source_id: str, tier: int) -> AttributeCandidate:
    return AttributeCandidate(
        attribute=attribute,
        value=value,
        source_id=source_id,
        source_tier=tier,
        source_url="https://example.com/source",
        source_text="explicit statement",
        derivation="explicit_phrase",
        confidence="reference",
        verified_at="2026-10-21",
    )


def test_foot_mapping_only_explicit_statements():
    value, _ = _foot_from_text(
        "Nicky Devlin is a left-footed defender.",
        name="Nicky Devlin",
        phrase_map=CONFIG["foot_phrases"],
    )
    assert value == "left"
    value, _ = _foot_from_text(
        "Marius Müller is comfortable with both feet.",
        name="Marius Müller",
        phrase_map=CONFIG["foot_phrases"],
    )
    assert value == "both"
    value, _ = _foot_from_text(
        "Nicky Devlin is a right-back.",
        name="Nicky Devlin",
        phrase_map=CONFIG["foot_phrases"],
    )
    assert value is None


def test_foot_mapping_rejects_negative_or_irrelevant_context():
    value, _ = _foot_from_text(
        "Nicky Devlin is not left-footed.",
        name="Nicky Devlin",
        phrase_map=CONFIG["foot_phrases"],
    )
    assert value is None
    value, _ = _foot_from_text(
        "Nicky Devlin took a left-footed shot.",
        name="Nicky Devlin",
        phrase_map=CONFIG["foot_phrases"],
    )
    assert value is None


def _player() -> dict:
    return {"player_id": 1, "player_key": "api:player:1", "name": "Test Player"}


def test_precedence_override_wins():
    override = FakeSource(
        "override", [_candidate("preferred_foot", "right", source_id="override", tier=0)]
    )
    wikipedia = FakeSource(
        "wikipedia", [_candidate("preferred_foot", "left", source_id="wikipedia", tier=4)]
    )
    rows, meta = resolve_attributes(
        [_player()], [override, wikipedia], config=CONFIG, ingested_at="2026-10-21T00:00:00Z"
    )
    foot = next(row for row in rows if row["attribute"] == "preferred_foot")
    assert foot["value"] == "right"
    assert foot["status"] == "known"
    assert foot["conflict_state"] == "override_applied"
    assert meta["known"] == 1


def test_same_tier_conflict_withholds_value():
    left = FakeSource("a", [_candidate("preferred_foot", "left", source_id="a", tier=4)])
    right = FakeSource("b", [_candidate("preferred_foot", "right", source_id="b", tier=4)])
    rows, meta = resolve_attributes(
        [_player()], [left, right], config=CONFIG, ingested_at="2026-10-21T00:00:00Z"
    )
    foot = next(row for row in rows if row["attribute"] == "preferred_foot")
    assert foot["value"] is None
    assert foot["status"] == "conflict"
    assert foot["conflict_state"] == "unresolved"
    assert meta["conflicts"] == 1


def test_lower_tier_disagreement_is_resolved_by_precedence():
    primary = FakeSource(
        "primary", [_candidate("preferred_foot", "right", source_id="primary", tier=2)]
    )
    fallback = FakeSource(
        "fallback", [_candidate("preferred_foot", "left", source_id="fallback", tier=4)]
    )
    rows, _ = resolve_attributes(
        [_player()], [primary, fallback], config=CONFIG, ingested_at="2026-10-21T00:00:00Z"
    )
    foot = next(row for row in rows if row["attribute"] == "preferred_foot")
    assert foot["value"] == "right"
    assert foot["conflict_state"] == "resolved_by_precedence"


def test_unknown_when_no_source_states_attribute():
    rows, meta = resolve_attributes(
        [_player()], [], config=CONFIG, ingested_at="2026-10-21T00:00:00Z"
    )
    assert len(rows) == 1
    assert rows[0]["attribute"] == "preferred_foot"
    assert rows[0]["status"] == "unknown"
    assert rows[0]["value"] is None
    assert meta["unknown"] == 1


def test_override_validation_requires_provenance():
    base = {
        "player_key": "api:player:1",
        "attribute": "preferred_foot",
        "value": "right",
        "source_id": "wikipedia",
        "source_url": "https://en.wikipedia.org/wiki/Example",
        "reason": "The page states right-footed.",
        "verified_at": "2026-10-21",
    }
    _validate_override(base, CONFIG)
    for field in ("source_id", "source_url", "reason", "verified_at"):
        broken = {**base, field: ""}
        try:
            _validate_override(broken, CONFIG)
        except ValueError:
            continue
        raise AssertionError(f"missing {field} was accepted")


def test_side_cannot_be_overridden():
    row = {
        "player_key": "api:player:1",
        "attribute": "side",
        "value": "right",
        "source_id": "wikipedia",
        "source_url": "https://en.wikipedia.org/wiki/Example",
        "reason": "Not a foot attribute.",
        "verified_at": "2026-10-21",
    }
    try:
        _validate_override(row, CONFIG)
    except ValueError:
        return
    raise AssertionError("side override was accepted")
