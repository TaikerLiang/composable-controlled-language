"""`controlled-english` / `ccl` command line (PLAN § 6)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, baseline, fixtures, report
from .config import BASELINE_MODES, Config, collect_files, load_config
from .engine import lint_document
from .errors import BaselineError, ConfigError
from .findings import Finding
from .rules import ProfileStore, RuleSet
from .text import parse


def _store(args) -> ProfileStore:
    return ProfileStore([Path(d) for d in (args.profiles_dir or [])])


def _config(args) -> Config:
    cfg = load_config(Path(args.config) if args.config else None, Path.cwd())
    if getattr(args, "profiles", None):
        cfg.profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]
    return cfg


def _lint_all(
    cfg: Config, ruleset: RuleSet, paths: list[Path], force_surface: str | None
) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    not_run: list[str] = []
    for abs_path, rel, surface in collect_files(cfg, paths, force_surface):
        doc = parse(abs_path.read_text(encoding="utf-8"), rel, cfg.front_matter_keys)
        got, nr = lint_document(doc, surface, ruleset, cfg.rules)
        findings.extend(got)
        not_run.extend(nr)
    return findings, not_run


def cmd_lint(args) -> int:
    cfg = _config(args)
    ruleset = _store(args).compose(cfg.profiles)
    findings, not_run = _lint_all(cfg, ruleset, [Path(p) for p in args.paths], args.surface)
    mode = args.baseline or cfg.baseline_mode
    if mode != "off":
        data = baseline.load(cfg.baseline_file)
        baseline.check_compatible(data, ruleset, cfg.rules)
        baseline.apply(findings, data)
    fails = baseline.failing(findings, mode)
    if args.format == "json":
        sys.stdout.write(report.as_json(findings, not_run, ruleset, cfg.rules, mode, len(fails)))
    else:
        sys.stdout.write(
            report.compact(findings) if args.format == "compact" else report.human(findings)
        )
        sys.stderr.write(report.summary(findings, not_run, mode, len(fails)) + "\n")
    return 1 if fails and not args.no_fail else 0


def cmd_rules(args) -> int:
    cfg = _config(args)
    ruleset = _store(args).compose(cfg.profiles)
    if args.format == "json":
        out = {
            rid: {
                "revision": r.revision,
                "title": r.title,
                "layer": r.layer,
                "check": r.check,
                "kind": r.kind,
                "source": r.source,
                "lineage": list(r.lineage),
                "inspired_by": list(r.inspired_by),
                "severity": {
                    s: ruleset.severity_for(rid, s, cfg.rules) for s in ("runtime", "explanatory")
                },
            }
            for rid, r in sorted(ruleset.rules.items())
        }
        sys.stdout.write(json.dumps(out, indent=1) + "\n")
    else:
        sys.stdout.write(report.rules_table(ruleset, cfg.rules))
    return 0


def cmd_explain(args) -> int:
    cfg = _config(args)
    ruleset = _store(args).compose(cfg.profiles)
    if args.rule_id not in ruleset.rules:
        raise ConfigError(f"unknown rule {args.rule_id}; `controlled-english rules` lists them")
    sys.stdout.write(report.explain(ruleset, args.rule_id))
    return 0


def cmd_baseline(args) -> int:
    cfg = _config(args)
    ruleset = _store(args).compose(cfg.profiles)
    findings, _ = _lint_all(cfg, ruleset, [Path(p) for p in args.paths], None)
    if args.action == "write":
        data = baseline.build(findings, ruleset, cfg.rules)
        baseline.write(cfg.baseline_file, data)
        sys.stderr.write(f"wrote {len(findings)} findings to {cfg.baseline_file}\n")
        return 0
    data = baseline.load(cfg.baseline_file)
    d = baseline.diff(findings, data, ruleset, cfg.rules)
    for reason in d["incompatibilities"]:
        sys.stdout.write(f"incompatible: {reason}\n")
    if d["ruleset_changed"] and not d["incompatibilities"]:
        sys.stdout.write("rule set digest changed (rules disabled or profiles reordered)\n")
    for rid in d["stale_rules"]:
        sys.stdout.write(f"stale: {rid} is in the baseline but no longer in effect\n")
    for f in d["new"]:
        sys.stdout.write(f"new:   {f.file}:{f.line} {f.rule_id} {f.severity}: {f.message}\n")
    for f in d["fixed"]:
        sys.stdout.write(f"fixed: {f['file']} {f['rule']}: {f['sentence']}\n")
    sys.stderr.write(
        f"{len(d['new'])} new, {len(d['fixed'])} fixed, {len(d['stale_rules'])} stale rules\n"
    )
    return 0


def cmd_judgment(args) -> int:
    cfg = _config(args)
    ruleset = _store(args).compose(cfg.profiles)
    out = []
    for rid, rule in sorted(ruleset.rules.items()):
        if rule.check == "deterministic":
            continue
        entry = {
            "rule": rid,
            "revision": rule.revision,
            "prompt": rule.judgment_prompt,
            "candidates": [],
        }
        for abs_path, rel, surface in collect_files(cfg, [Path(p) for p in args.paths], None):
            if ruleset.severity_for(rid, surface, cfg.rules) == "disabled":
                continue
            doc = parse(abs_path.read_text(encoding="utf-8"), rel, cfg.front_matter_keys)
            if rule.check == "both":
                found, _ = lint_document(doc, surface, ruleset, cfg.rules, only={rid})
                entry["candidates"] += [
                    {"file": f.file, "line": f.line, "sentence": f.sentence} for f in found
                ]
            else:
                entry["candidates"] += [
                    {"file": rel, "line": s.line, "sentence": s.canonical}
                    for s in doc.sentences
                    if s.kind != "heading"
                ]
        out.append(entry)
    sys.stdout.write(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    return 0


def cmd_check_fixtures(args) -> int:
    store = _store(args)
    fixtures_dir = Path(args.fixtures)
    store = ProfileStore([Path(d) for d in (args.profiles_dir or [])] + [fixtures_dir / "profiles"])
    names = [p.strip() for p in (args.profiles or "agent").split(",")]
    ruleset = store.compose(names)
    problems = []
    for rule in ruleset.rules.values():
        problems += fixtures.check_rule(fixtures_dir, rule, store)
    problems += fixtures.check_judgment_fixtures(fixtures_dir, ruleset.rules)
    problems += fixtures.check_metadata_prose(ruleset)
    for p in problems:
        sys.stdout.write(p + "\n")
    sys.stderr.write(f"{len(ruleset.rules)} rules checked, {len(problems)} problem(s)\n")
    return 1 if problems else 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="controlled-english",
        description="Composable controlled English for agent-facing repositories. A clean run "
        "means no configured, detectable violation on the linted surfaces, and "
        "judgment rules not run. It never means the instruction is correct.",
    )
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="command", required=True)

    def common(p, paths=True):
        p.add_argument("--config", help="path to .controlled-english.toml")
        p.add_argument("--profiles", help="comma-separated profile names (overrides config)")
        p.add_argument(
            "--profiles-dir",
            action="append",
            help="extra directory to search for profiles (repeatable)",
        )
        if paths:
            p.add_argument("paths", nargs="*", help="files or directories (default: config root)")

    p = sub.add_parser("lint", help="lint prose files")
    common(p)
    p.add_argument("--format", choices=("human", "compact", "json"), default="human")
    p.add_argument("--baseline", choices=BASELINE_MODES, help="override baseline.mode")
    p.add_argument(
        "--surface",
        choices=("runtime", "explanatory"),
        help="treat every given path as this surface",
    )
    p.add_argument("--no-fail", action="store_true", help="always exit 0 (report-only)")
    p.set_defaults(func=cmd_lint)

    p = sub.add_parser("rules", help="list the effective rules")
    common(p, paths=False)
    p.add_argument("--format", choices=("table", "json"), default="table")
    p.set_defaults(func=cmd_rules)

    p = sub.add_parser("explain", help="show one rule in full")
    common(p, paths=False)
    p.add_argument("rule_id")
    p.set_defaults(func=cmd_explain)

    p = sub.add_parser("baseline", help="write or diff the baseline file")
    p.add_argument("action", choices=("write", "diff"))
    common(p)
    p.set_defaults(func=cmd_baseline)

    p = sub.add_parser("judgment", help="export judgment rules and their candidate sentences")
    p.add_argument("action", choices=("export",))
    common(p)
    p.set_defaults(func=cmd_judgment)

    p = sub.add_parser("check-fixtures", help="validate rule files, fixtures and rule prose")
    common(p, paths=False)
    p.add_argument("--fixtures", default="tests/fixtures")
    p.set_defaults(func=cmd_check_fixtures)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, BaselineError) as e:
        sys.stderr.write(f"error: {e}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
