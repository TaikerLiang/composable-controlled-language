"""Baseline identity (PLAN § 4.5 table), the versioned file, compatibility refusals, policy."""

import json

import pytest

from controlled_english import baseline
from controlled_english.engine import lint_document
from controlled_english.errors import BaselineError
from controlled_english.findings import Finding
from controlled_english.rules import ProfileStore
from controlled_english.text import parse


def _ids(text, rule="BASE-M02", file="commands/x.md"):
    rs = ProfileStore().compose(["base"])
    findings, _ = lint_document(parse(text, file), "runtime", rs, only={rule})
    return [f.identity for f in findings]


def test_identity_is_stable_under_rewrap_emphasis_and_unrelated_edits():
    a = _ids("Intro line.\n\nYou should apply `status: ready-for-dev`\nto the **issue**.\n")
    b = _ids("A different intro.\n\nYou should apply `status: ready-for-dev` to the issue.\n")
    assert a == b and len(a) == 1


def test_identity_changes_with_semantic_tokens_case_file_and_revision():
    base = _ids("You should apply `status: ready-for-dev`.")
    assert base != _ids("You should apply `status: ready-for-spec`.")
    assert _ids("You should merge `<feat-branch>` into `<spec-branch>`.") != _ids(
        "You should merge `<qa-branch>` into `<spec-branch>`."
    )
    assert _ids("You should wait 10 s.") != _ids("You should wait 30 s.")
    assert _ids("You should stop.") != _ids("You SHOULD stop.")
    assert base != _ids("You should apply `status: ready-for-dev`.", file="commands/y.md")
    f1 = Finding("BASE-M02", 1, "a.md", 1, 1, "runtime", "error", "m", "should", "You should.")
    f2 = Finding("BASE-M02", 2, "a.md", 1, 1, "runtime", "error", "m", "should", "You should.")
    assert f1.identity != f2.identity


def _run(text, file="commands/x.md", profiles=("base",), overrides=None):
    rs = ProfileStore().compose(list(profiles))
    findings, _ = lint_document(parse(text, file), "runtime", rs, overrides)
    return findings, rs


def test_build_write_load_roundtrip_and_fields(tmp_path):
    findings, rs = _run("You should push; then wait.")
    data = baseline.build(findings, rs, None)
    assert set(data) >= {
        "schema_version",
        "engine_version",
        "tokenizer_version",
        "profiles",
        "rules",
        "ruleset_digest",
        "written_at",
        "findings",
    }
    assert data["rules"]["BASE-S02"] == 1 and data["profiles"] == ["base"]
    assert {f["rule"] for f in data["findings"]} == {"BASE-M02", "BASE-S02"}
    assert all("sentence" in f for f in data["findings"])
    path = tmp_path / "b.json"
    baseline.write(path, data)
    assert baseline.load(path) == data
    assert baseline.incompatibilities(data, rs, None) == []


def test_every_incompatibility_is_named_and_refused(tmp_path):
    findings, rs = _run("You should push.")
    data = baseline.build(findings, rs, None)
    cases = {
        "tokenizer_version": ({"tokenizer_version": 99}, "tokenizer_version"),
        "schema": ({"schema_version": 7}, "schema"),
        "engine major": ({"engine_version": "9.0.0"}, "engine_version"),
        "profiles": ({"profiles": ["agent"]}, "profiles"),
        "revision": ({"rules": {**data["rules"], "BASE-S02": 2}}, "revision changed: BASE-S02"),
        "new rule": (
            {"rules": {k: v for k, v in data["rules"].items() if k != "BASE-M01"}},
            "not in the baseline: BASE-M01",
        ),
    }
    for name, (patch, needle) in cases.items():
        broken = {**data, **patch}
        reasons = baseline.incompatibilities(broken, rs, None)
        assert any(needle in r for r in reasons), (name, reasons)
        with pytest.raises(BaselineError, match="refused"):
            baseline.check_compatible(broken, rs, None)


def test_disabled_rule_is_stale_not_incompatible():
    findings, rs = _run("You should push.")
    data = baseline.build(findings, rs, None)
    overrides = {"BASE-V01": {"runtime": "disabled", "explanatory": "disabled"}}
    assert baseline.incompatibilities(data, rs, overrides) == []
    assert baseline.stale_rules(data, rs, overrides) == ["BASE-V01"]


def test_apply_diff_and_policy():
    old, rs = _run("You should push.\n\nOpen the PR; wait.")
    data = baseline.build(old, rs, None)
    new, _ = _run("You should push.\n\nOpen the PR. Wait.\n\nYou ought to rest.")
    baseline.apply(new, data)
    by_rule = {(f.rule_id, f.match): f.baselined for f in new}
    assert by_rule[("BASE-M02", "should")] is True
    assert by_rule[("BASE-M02", "ought to")] is False
    d = baseline.diff(new, data, rs, None)
    assert [f.match for f in d["new"]] == ["ought to"]
    assert [f["rule"] for f in d["fixed"]] == ["BASE-S02"]
    assert d["incompatibilities"] == [] and d["ruleset_changed"] is False
    assert [f.match for f in baseline.failing(new, "new-only")] == ["ought to"]
    assert len(baseline.failing(new, "off")) == 2
    assert len(baseline.failing(new, "all")) == 2


def test_load_refuses_missing_or_malformed(tmp_path):
    with pytest.raises(BaselineError, match="baseline write"):
        baseline.load(tmp_path / "none.json")
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    with pytest.raises(BaselineError):
        baseline.load(p)
    p.write_text(json.dumps({"schema_version": 1}))
    with pytest.raises(BaselineError, match="missing"):
        baseline.load(p)
