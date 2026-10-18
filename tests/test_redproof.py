"""Red-proof by mutation, both directions, for every shipped rule (PLAN § 7).

Direction 1: remove the marked lines from positive.md → the rule falls silent, so the
findings came from the marked lines and nowhere else.
Direction 2: append each rule example's `bad` sentence to negative.md → the rule fires on
the appended text; append `good` → it stays silent.
"""

import pytest

from controlled_english import fixtures as fx

from .conftest import FIXTURES, shipped_rule_ids

RULE_IDS = shipped_rule_ids()


def _setup(store, rid):
    rule = store.compose(["agent"]).rules[rid]
    ruleset = store.compose([fx.fixture_profile(FIXTURES / rid, rule)])
    return rule, ruleset


@pytest.mark.parametrize("rid", RULE_IDS)
def test_removing_marked_lines_silences_the_rule(store, rid):
    rule, ruleset = _setup(store, rid)
    text = (FIXTURES / rid / "positive.md").read_text()
    assert fx.lint_text(text, rid, ruleset, fx.fixture_surface(text))
    mutated = fx.strip_marked_lines(text)
    assert fx.lint_text(mutated, rid, ruleset, fx.fixture_surface(text)) == []


@pytest.mark.parametrize("rid", RULE_IDS)
def test_injecting_the_bad_example_fires_on_the_injected_lines(store, rid):
    rule, ruleset = _setup(store, rid)
    negative = (FIXTURES / rid / "negative.md").read_text().rstrip("\n")
    base_lines = negative.count("\n") + 1
    for ex in rule.examples:
        mutated = negative + "\n\n" + ex["bad"].strip() + "\n"
        got = fx.lint_text(mutated, rid, ruleset, "runtime")
        assert got, f"{rid}: bad example did not fire inside negative.md"
        assert all(f.line > base_lines for f in got), f"{rid}: finding outside injected text"
        if "good" in ex:
            mutated = negative + "\n\n" + ex["good"].strip() + "\n"
            assert fx.lint_text(mutated, rid, ruleset, "runtime") == []
