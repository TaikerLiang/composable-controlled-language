"""Run the effective rules over one document."""

from __future__ import annotations

from .checkers import CHECKERS
from .findings import Finding
from .rules import RuleSet
from .text import Document


def lint_document(
    doc: Document,
    surface: str,
    ruleset: RuleSet,
    overrides: dict[str, dict[str, str]] | None = None,
    only: set[str] | None = None,
) -> tuple[list[Finding], list[str]]:
    """Return (findings, judgment rules not run) for one document on one surface."""
    findings: list[Finding] = []
    not_run: list[str] = []
    for rid, rule in sorted(ruleset.rules.items()):
        if only is not None and rid not in only:
            continue
        severity = ruleset.severity_for(rid, surface, overrides)
        if severity == "disabled":
            continue
        if rule.check in ("judgment", "both"):
            not_run.append(rid)
        if rule.check == "judgment":
            continue
        for f in CHECKERS[rule.kind](rule, doc, surface, ruleset):
            f.severity = severity
            findings.append(f)
    findings.sort(key=lambda f: (f.file, f.line, f.col, f.rule_id))
    return findings, not_run
