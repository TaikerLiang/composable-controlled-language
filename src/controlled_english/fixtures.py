"""Fixture runner shared by the tests and `controlled-english check-fixtures` (PLAN § 7).

Per rule: `positive.md` marks each triggering line with `<!-- expect: RULE-ID -->` (repeat
the ID for two findings on one line); `negative.md` and `near-miss.md` must be silent. An
optional `profile` file names the profile to compose (default: the rule's layer) and a
first-line `<!-- surface: explanatory -->` picks the surface (default: runtime).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .engine import lint_document
from .findings import Finding
from .rules import SURFACES, ProfileStore, Rule, RuleSet
from .text import parse

RE_EXPECT = re.compile(
    r"<!--\s*expect:\s*([A-Z][A-Z0-9]*-[A-Z0-9]+(?:\s+[A-Z][A-Z0-9]*-[A-Z0-9]+)*)\s*-->"
)
RE_SURFACE = re.compile(r"<!--\s*surface:\s*(runtime|explanatory)\s*-->")
FIXTURE_FILES = ("positive.md", "negative.md", "near-miss.md")


def expected_lines(text: str, rule_id: str) -> list[int]:
    out = []
    for n, line in enumerate(text.split("\n"), 1):
        for m in RE_EXPECT.finditer(line):
            out.extend(n for rid in m.group(1).split() if rid == rule_id)
    return sorted(out)


def fixture_surface(text: str) -> str:
    m = RE_SURFACE.search(text.split("\n", 1)[0])
    return m.group(1) if m else "runtime"


def fixture_profile(rule_dir: Path, rule: Rule) -> str:
    p = rule_dir / "profile"
    return p.read_text().strip() if p.exists() else rule.layer


def lint_text(
    text: str, rule_id: str, ruleset: RuleSet, surface: str, name: str = "fixture.md"
) -> list[Finding]:
    doc = parse(text, name)
    findings, _ = lint_document(doc, surface, ruleset, only={rule_id})
    return findings


def strip_marked_lines(text: str) -> str:
    return "\n".join(line for line in text.split("\n") if not RE_EXPECT.search(line))


def check_rule(fixtures_dir: Path, rule: Rule, store: ProfileStore) -> list[str]:
    """Problems with one rule's fixtures; empty when all three files behave."""
    problems = []
    rule_dir = fixtures_dir / rule.id
    missing = [f for f in FIXTURE_FILES if not (rule_dir / f).exists()]
    if missing:
        return [f"{rule.id}: missing fixture file(s) {', '.join(missing)}"]
    if not rule.examples:
        problems.append(f"{rule.id}: no [[examples]] entry")
    ruleset = store.compose([fixture_profile(rule_dir, rule)])
    for name in FIXTURE_FILES:
        text = (rule_dir / name).read_text()
        surface = fixture_surface(text)
        got = sorted(f.line for f in lint_text(text, rule.id, ruleset, surface, name))
        want = expected_lines(text, rule.id) if name == "positive.md" else []
        if name == "positive.md" and not want:
            problems.append(f"{rule.id}/{name}: no <!-- expect --> markers")
        if got != want:
            problems.append(f"{rule.id}/{name}: findings on lines {got}, expected {want}")
    return problems


def check_judgment_fixtures(fixtures_dir: Path, rules: dict[str, Rule]) -> list[str]:
    problems = []
    jdir = fixtures_dir / "judgment"
    if not jdir.is_dir():
        return problems
    for path in sorted(jdir.glob("*.json")):
        rid = path.stem
        rule = rules.get(rid)
        if rule is None or rule.check == "deterministic":
            problems.append(f"{path.name}: {rid} is not a judgment rule in the composed set")
            continue
        try:
            cases = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            problems.append(f"{path.name}: {e}")
            continue
        if not isinstance(cases, list) or not cases:
            problems.append(f"{path.name}: expected a non-empty list")
            continue
        for i, c in enumerate(cases):
            keys = {"text", "surface", "expected", "why"}
            if not isinstance(c, dict) or set(c) != keys:
                problems.append(f"{path.name}[{i}]: keys must be exactly {sorted(keys)}")
                continue
            if c["surface"] not in SURFACES or c["expected"] not in ("violates", "ok"):
                problems.append(f"{path.name}[{i}]: bad surface or expected value")
        if cases and not any(c.get("expected") == "violates" for c in cases):
            problems.append(f"{path.name}: needs at least one violating case")
    for rid, rule in rules.items():
        if rule.check in ("judgment", "both") and not (jdir / f"{rid}.json").exists():
            problems.append(f"{rid}: judgment rule without tests/fixtures/judgment/{rid}.json")
    return problems


def check_metadata_prose(ruleset: RuleSet) -> list[str]:
    """Dogfood: title and message lint as runtime, rationale as explanatory."""
    problems = []
    for rid, rule in sorted(ruleset.rules.items()):
        for field, surface, text in (
            ("title", "runtime", rule.title),
            ("message", "runtime", rule.message),
            ("rationale", "explanatory", rule.rationale),
        ):
            doc = parse(text, f"{rid}.{field}")
            findings, _ = lint_document(doc, surface, ruleset)
            bad = [f for f in findings if surface == "runtime" or f.severity != "advisory"]
            for f in bad:
                problems.append(f"{rid}.{field}: {f.rule_id} {f.severity}: {f.message}")
    return problems
