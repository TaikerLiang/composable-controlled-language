"""Every shipped rule: schema, the three fixtures, its examples, and its own prose."""

import pytest

from controlled_english import fixtures as fx
from controlled_english.rules import ProfileStore
from controlled_english.text import parse

from .conftest import FIXTURES, shipped_rule_ids

RULE_IDS = shipped_rule_ids()


def _rule(store, rid):
    return store.compose(["agent"]).rules[rid]


def test_twelve_base_rules_ship():
    assert len([r for r in RULE_IDS if r.startswith("BASE-")]) == 12


@pytest.mark.parametrize("rid", RULE_IDS)
def test_fixtures_behave(store, rid):
    problems = fx.check_rule(FIXTURES, _rule(store, rid), store)
    assert problems == []


@pytest.mark.parametrize("rid", RULE_IDS)
def test_examples_bad_fires_and_good_is_silent(store, rid):
    rule = _rule(store, rid)
    ruleset = store.compose([fx.fixture_profile(FIXTURES / rid, rule)])
    assert rule.examples, "a rule ships at least one example"
    for ex in rule.examples:
        assert fx.lint_text(ex["bad"], rid, ruleset, "runtime"), f"bad example silent: {ex['bad']}"
        if "good" in ex:
            assert fx.lint_text(ex["good"], rid, ruleset, "runtime") == [], ex["good"]


def test_judgment_fixtures_are_well_formed(store):
    rules = store.compose(["agent"]).rules
    assert fx.check_judgment_fixtures(FIXTURES, rules) == []


def test_rule_metadata_prose_dogfoods_clean():
    assert fx.check_metadata_prose(ProfileStore().compose(["agent"])) == []


def test_messages_name_their_fields(store):
    for rid in RULE_IDS:
        rule = _rule(store, rid)
        doc = parse(rule.message, rid)
        assert doc.sentences, rid
