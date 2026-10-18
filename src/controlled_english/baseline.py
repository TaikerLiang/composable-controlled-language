"""Baseline file: identity, versioned schema, compatibility refusals, write / diff (PLAN § 4.5)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .errors import BaselineError
from .findings import Finding
from .rules import SURFACES, RuleSet
from .text import TOKENIZER_VERSION

SCHEMA_VERSION = 1


def effective_revisions(
    ruleset: RuleSet, overrides: dict[str, dict[str, str]] | None
) -> dict[str, int]:
    """Rules that run on at least one surface, with their revisions."""
    out = {}
    for rid, rule in sorted(ruleset.rules.items()):
        if any(ruleset.severity_for(rid, s, overrides) != "disabled" for s in SURFACES):
            out[rid] = rule.revision
    return out


def build(findings: list[Finding], ruleset: RuleSet, overrides) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "engine_version": __version__,
        "tokenizer_version": TOKENIZER_VERSION,
        "profiles": list(ruleset.profiles),
        "rules": effective_revisions(ruleset, overrides),
        "ruleset_digest": ruleset.digest(),
        "written_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "findings": [
            {"id": f.identity, "rule": f.rule_id, "file": f.file, "sentence": f.sentence}
            for f in sorted(findings, key=lambda f: (f.file, f.line, f.col, f.rule_id))
        ],
    }


def write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def load(path: Path) -> dict:
    if not path.exists():
        raise BaselineError(f"no baseline file at {path}; run `controlled-english baseline write`")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise BaselineError(f"{path}: {e}") from e
    for key in (
        "schema_version",
        "engine_version",
        "tokenizer_version",
        "profiles",
        "rules",
        "findings",
    ):
        if key not in data:
            raise BaselineError(f"{path}: missing {key!r}")
    return data


def incompatibilities(data: dict, ruleset: RuleSet, overrides) -> list[str]:
    """Why this baseline cannot be applied to the current engine and rules; empty if it can."""
    reasons = []
    if data["schema_version"] != SCHEMA_VERSION:
        reasons.append(f"baseline schema {data['schema_version']} is not {SCHEMA_VERSION}")
    if data["tokenizer_version"] != TOKENIZER_VERSION:
        reasons.append(
            f"tokenizer_version {data['tokenizer_version']} is not "
            f"{TOKENIZER_VERSION} (re-baseline)"
        )
    if str(data["engine_version"]).split(".")[0] != __version__.split(".")[0]:
        reasons.append(
            f"engine_version {data['engine_version']} has a different major "
            f"version than {__version__}"
        )
    if list(data["profiles"]) != list(ruleset.profiles):
        reasons.append(f"profiles {data['profiles']} are not {list(ruleset.profiles)}")
    current = effective_revisions(ruleset, overrides)
    recorded = data["rules"]
    changed = [
        f"{rid} (baseline rev {recorded[rid]}, rules rev {rev})"
        for rid, rev in current.items()
        if rid in recorded and recorded[rid] != rev
    ]
    added = [rid for rid in current if rid not in recorded]
    if changed:
        reasons.append("rule revision changed: " + ", ".join(changed))
    if added:
        reasons.append("rules not in the baseline: " + ", ".join(added))
    return reasons


def check_compatible(data: dict, ruleset: RuleSet, overrides) -> None:
    reasons = incompatibilities(data, ruleset, overrides)
    if reasons:
        raise BaselineError(
            "baseline refused (run `controlled-english baseline diff`, then "
            "`baseline write`):\n  - " + "\n  - ".join(reasons)
        )


def apply(findings: list[Finding], data: dict) -> None:
    known = {f["id"] for f in data["findings"]}
    for f in findings:
        f.baselined = f.identity in known


def stale_rules(data: dict, ruleset: RuleSet, overrides) -> list[str]:
    current = effective_revisions(ruleset, overrides)
    return sorted(rid for rid in data["rules"] if rid not in current)


def diff(findings: list[Finding], data: dict, ruleset: RuleSet, overrides) -> dict:
    current = {f.identity: f for f in findings}
    recorded = {f["id"]: f for f in data["findings"]}
    return {
        "new": [current[i] for i in current if i not in recorded],
        "fixed": [recorded[i] for i in recorded if i not in current],
        "stale_rules": stale_rules(data, ruleset, overrides),
        "incompatibilities": incompatibilities(data, ruleset, overrides),
        "ruleset_changed": data.get("ruleset_digest") != ruleset.digest(),
    }


def failing(findings: list[Finding], mode: str) -> list[Finding]:
    """Error-level findings that fail the run under the baseline policy."""
    errors = [f for f in findings if f.severity == "error"]
    if mode == "new-only":
        return [f for f in errors if not f.baselined]
    return errors
