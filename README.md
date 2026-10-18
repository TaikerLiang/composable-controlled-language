# composable-controlled-language

A composable controlled-English linter for prose that an agent executes: command
files, agent briefs, skill instructions, front-matter descriptions. The
structural rules follow the shape of ASD-STE100. The agent-language rules and
the project profiles are this framework's own.

> English used as executable agent context needs stronger rules than ordinary
> documentation. The goal is one intended executable interpretation, not shorter
> text.

## What it is not

- Not an ASD-STE100 implementation and not a compliance checker. Rules cite STE
  rule numbers and paraphrase them. No rule text, example or dictionary entry is
  reproduced, and the standard itself is never part of this repository.
- Not a rewriter. It detects and explains. It never edits your files.
- Not a proof of correctness. See "What green means".

## Layers

```
profiles/base       STE-derived structural discipline   BASE-*   (12 rules)
profiles/agent      generic agent-language policy       AGENT-*  (v0.2)
profiles/<project>  domain or project profiles          RG-*, …  (v0.2: roz-gate)
```

A profile is a directory: `profile.toml` (name, `extends`, severity overrides),
`rules/*.toml` (one file per rule), `glossary.toml` (concepts, actors,
imperative verbs, modality bindings, allow lists). `agent` extends `base`; a
project profile extends `agent`, or `base` alone for documentation that has no
agent in it. Rules are a union, a later profile's severity override wins, and
two profiles that disagree on a glossary canonical or a modality binding are an
error, never a silent choice.

## Install and run

Python 3.11 or newer, no runtime dependencies.

```
uvx --from git+https://github.com/TaikerLiang/composable-controlled-language@v0.1.0 \
    controlled-english lint .
```

Or in a checkout: `uv sync`, then `uv run controlled-english …`. `ccl` is the
short alias.

```
controlled-english lint [PATHS…] [--format human|compact|json] [--baseline off|new-only|all] [--no-fail]
controlled-english rules                 # effective rules: revision, source, check, severity per surface
controlled-english explain BASE-S02      # rationale, lineage, examples
controlled-english baseline write|diff
controlled-english judgment export       # judgment rules and their candidate sentences; no runner yet
controlled-english check-fixtures        # this repository's own rule validation
```

Exit codes: 0 clean under the baseline policy, 1 an error-level finding fails
the policy, 2 a usage, configuration, composition or baseline-compatibility
error.

## Configuration

`.controlled-english.toml` at the repository root:

```toml
profiles = ["roz-gate"]                      # extends supplies agent and base

[surfaces]
runtime     = ["commands/**/*.md", "agents/**/*.md", "references/*-brief.md"]
explanatory = ["README.md", "docs/**/*.md"]
ignore      = ["CHANGELOG.md", "evals/**"]
front_matter_keys = ["description"]          # front-matter strings that are prose

[rules]
"BASE-V01" = "disabled"                      # or { runtime = "advisory" }

[baseline]
file = ".controlled-english.baseline.json"
mode = "new-only"                            # off | new-only | all
```

Two surfaces describe the kind of prose. **runtime** is prose that influences
agent execution (word cap 20). **explanatory** is prose a human reads (cap 25).
Severity (`error`, `warning`, `advisory`, `disabled`) describes enforcement and
is set per rule, per surface. Only `error` fails a run.

## Adoption

1. Run `lint --no-fail` in CI and read the counts.
2. `baseline write` and commit the file. Findings are identified by a content
   hash of the rule, its revision, the file and the canonical sentence, never
   by line number. Re-wrapping a paragraph changes nothing. Changing a label,
   a placeholder or a number makes the sentence new prose.
3. Switch to `mode = "new-only"`: new or modified runtime prose must pass.
4. Shrink the baseline with prose-only changes.

The baseline records the schema version, engine version, tokenizer version,
profiles and every rule's revision. When any of those no longer match, the tool
refuses the baseline with the reason and exits 2. A framework upgrade is one
change: bump the pinned tag, run `baseline write`, review the diff.

## What green means

A clean run means no configured, detectable language-policy violation was
found on the linted surfaces, and judgment rules were not run. It does not mean
the instruction is correct, complete or safe. `Delete the database.` passes
every rule in this framework.

## Documents

- `docs/PLAN.md`: the design, its rulings, and the rule catalogue.
- `docs/ROADMAP.md`: milestones from this release to the first adopter.
- `docs/rule-model.md`: the file formats and the tokenizer contract.
