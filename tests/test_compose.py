"""Profile resolution and merge semantics (PLAN § 4.3), every error case included."""

import pytest

from controlled_english.engine import lint_document
from controlled_english.errors import ConfigError
from controlled_english.text import parse


def test_resolution_order_is_depth_first_parents_first_left_to_right(store):
    assert store.resolve(["diamond-x", "diamond-y"]) == ["base", "diamond-x", "diamond-y"]
    assert store.resolve(["pattern-test"]) == ["base", "glossary-test", "pattern-test"]
    assert store.resolve(["agent", "glossary-test"]) == ["base", "agent", "glossary-test"]


def test_later_profile_wins_on_severity(store):
    assert store.compose(["diamond-x", "diamond-y"]).severity_for("BASE-S02", "runtime") == "error"
    assert (
        store.compose(["diamond-y", "diamond-x"]).severity_for("BASE-S02", "runtime") == "advisory"
    )
    rs = store.compose(["diamond-y"])
    assert rs.severity_for("BASE-S06", "runtime") == "disabled"
    assert rs.severity_for("BASE-S06", "explanatory") == "disabled"
    assert rs.severity_for("BASE-S02", "explanatory") == "warning"  # untouched surface keeps base


def test_repo_overrides_win_over_every_profile(store):
    rs = store.compose(["diamond-y"])
    assert (
        rs.severity_for("BASE-S02", "runtime", {"BASE-S02": {"runtime": "disabled"}}) == "disabled"
    )


def test_rules_are_a_union_and_duplicate_ids_are_an_error(store):
    rs = store.compose(["pattern-test"])
    assert "TEST-M01" in rs.rules and "BASE-S01" in rs.rules
    with pytest.raises(ConfigError, match="BASE-S02.*'base'.*'dup-rule'"):
        store.compose(["dup-rule"])


def test_glossary_members_union_and_canonical_conflict_is_an_error(store):
    g = store.compose(["glossary-test"]).glossary
    assert g.concepts["fix-finding"].canonical == "fix"
    assert "patrol" in g.actors and "you" in g.actors
    with pytest.raises(ConfigError, match="fix-finding.*'fix'.*'repair'"):
        store.compose(["conflict-canonical"])


def test_modality_binding_conflict_is_an_error(store):
    with pytest.raises(ConfigError, match="permission"):
        store.compose(["conflict-modality"])


def test_cycle_unknown_and_invalid_rule_are_errors(store):
    with pytest.raises(ConfigError, match="cycle"):
        store.compose(["cycle-a"])
    with pytest.raises(ConfigError, match="not found"):
        store.compose(["no-such-profile"])
    with pytest.raises(ConfigError, match="lineage"):
        store.compose(["bad-rule"])


def test_digest_tracks_profiles_and_revisions(store):
    a, b = store.compose(["base"]), store.compose(["glossary-test"])
    assert a.digest() == store.compose(["base"]).digest()
    assert a.digest() != b.digest()
    assert a.revisions()["BASE-S01"] == 1


def test_subject_classification_drives_pattern_rules(store):
    rs = store.compose(["pattern-test"])

    def fires(text):
        doc = parse(text, "t.md")
        return [f.rule_id for f in lint_document(doc, "runtime", rs, only={"TEST-M01"})[0]]

    assert fires("The ref may survive the force-push.") == ["TEST-M01"]
    assert fires("A label may contain spaces.") == ["TEST-M01"]
    assert fires("Patrol may run it.") == []
    assert fires("A human may run it.") == []
    assert fires("You may run it.") == []
    assert fires("It may fail.") == []  # unknown subject is never an error


def test_glossary_allow_masks_a_phrase_rule(store):
    rs = store.compose(["glossary-test"])
    doc = parse("Roll back the deploy and set up the stub.", "t.md")
    got = [f.match for f in lint_document(doc, "runtime", rs, only={"BASE-V01"})[0]]
    assert got == ["set up"]


def test_base_alone_has_structure_but_no_actors(store):
    rs = store.compose(["base"])
    assert rs.glossary.actors == []
    assert all(rid.startswith("BASE-") for rid in rs.rules)
