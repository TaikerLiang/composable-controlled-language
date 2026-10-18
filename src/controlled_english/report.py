"""Human, compact and JSON output."""

from __future__ import annotations

import json
from collections import Counter

from . import __version__
from .findings import Finding
from .rules import RuleSet
from .text import TOKENIZER_VERSION


def human(findings: list[Finding]) -> str:
    blocks = []
    for f in findings:
        tag = f"{f.rule_id} {f.severity}" + ("  (baselined)" if f.baselined else "")
        blocks.append(f"{f.file}:{f.line}\n{tag}\n{f.message}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def compact(findings: list[Finding]) -> str:
    return "".join(
        f"{f.file}:{f.line}:{f.col}: {f.rule_id} {f.severity}"
        + (" (baselined)" if f.baselined else "")
        + f": {f.message}\n"
        for f in findings
    )


def summary(findings: list[Finding], not_run: list[str], mode: str, failing: int) -> str:
    by_sev = Counter(f.severity for f in findings)
    parts = [f"{len(findings)} finding{'s' if len(findings) != 1 else ''}"]
    detail = ", ".join(f"{by_sev[s]} {s}" for s in ("error", "warning", "advisory") if by_sev[s])
    if detail:
        parts[0] += f" ({detail})"
    if mode != "off":
        parts.append(f"{sum(f.baselined for f in findings)} baselined")
        parts.append(
            f"{failing} new error{'s' if failing != 1 else ''}"
            if mode == "new-only"
            else f"{failing} failing"
        )
    line = "; ".join(parts) + "."
    if not_run:
        line += " Judgment rules not run: " + ", ".join(sorted(set(not_run))) + "."
    return line


def as_json(
    findings: list[Finding],
    not_run: list[str],
    ruleset: RuleSet,
    overrides,
    mode: str,
    failing: int,
) -> str:
    from .baseline import effective_revisions

    return (
        json.dumps(
            {
                "engine_version": __version__,
                "tokenizer_version": TOKENIZER_VERSION,
                "profiles": list(ruleset.profiles),
                "rules": effective_revisions(ruleset, overrides),
                "baseline_mode": mode,
                "not_run": sorted(set(not_run)),
                "failing": failing,
                "findings": [f.to_json() for f in findings],
            },
            indent=1,
            ensure_ascii=False,
        )
        + "\n"
    )


def rules_table(ruleset: RuleSet, overrides) -> str:
    rows = [("ID", "rev", "source", "check", "runtime", "explanatory", "title")]
    for rid, r in sorted(ruleset.rules.items()):
        rows.append(
            (
                rid,
                str(r.revision),
                r.source,
                r.check,
                ruleset.severity_for(rid, "runtime", overrides),
                ruleset.severity_for(rid, "explanatory", overrides),
                r.title,
            )
        )
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]) - 1)]
    out = []
    for row in rows:
        cells = [row[i].ljust(widths[i]) for i in range(len(widths))] + [row[-1]]
        out.append("  ".join(cells).rstrip())
    return "\n".join(out) + "\n"


def explain(ruleset: RuleSet, rid: str) -> str:
    r = ruleset.rules[rid]
    cites = (
        ("lineage: " + ", ".join(r.lineage))
        if r.lineage
        else ("inspired by: " + ", ".join(r.inspired_by) if r.inspired_by else "")
    )
    lines = [
        f"{r.id} (revision {r.revision}) — {r.title}",
        f"layer {r.layer} · {r.check} · kind {r.kind} · source {r.source}"
        + (f" · {cites}" if cites else ""),
        "severity: " + ", ".join(f"{s}={v}" for s, v in sorted(r.severity.items())),
        "",
        r.rationale.strip(),
        "",
        "message: " + r.message,
    ]
    for ex in r.examples:
        lines += ["", "bad:  " + ex["bad"].strip()]
        if "good" in ex:
            lines.append("good: " + ex["good"].strip())
    if r.judgment_prompt:
        lines += ["", "judgment prompt: " + r.judgment_prompt]
    return "\n".join(lines) + "\n"
