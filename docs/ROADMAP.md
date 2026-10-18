# Roadmap

Milestones, each with an exit check a reader can run. Dates are not
committed; order is. Versions follow semver; the rule set is the public API,
so a rule's default severity change or a message rewording is a minor bump,
an ID removal is a major one.

```
M0 plan review ─► M1 framework v0.1 ─► M2 agent layer + roz-gate profile ─► M3 report-only in Roz Gate
                                                                                      │
                                              M6 second profile ◄─ M5 judgment runner ◄─ M4 enforce new prose
```

## M0 — plan review (done 2026-10-18)

- `docs/PLAN.md` § 9: twelve rulings, all ruled as recommended on 2026-10-18.
- Exit: rulings recorded at the top of `PLAN.md` (done); go signal for M1.

## M1 — framework v0.1 (`v0.1.0`)

Scope: `PLAN.md` § 3–4, the twelve `base` rules in § 5.1, and the `agent`
profile skeleton. Order and exit checks are `PLAN.md` § 11:

1. `text.py` — region model, tokenizer, sentence splitter, `canonical_sentence`,
   `TOKENIZER_VERSION`. Exit: `test_text.py` covers every § 4.1 row and every
   § 4.5 identity row (inline-code and placeholder edits change identity;
   re-wrapping does not).
2. `rules.py` — rule schema (`revision`, `source`, `lineage`), profile
   loading, resolution and merge. Exit: `test_compose.py` proves later-wins
   severity, duplicate-ID error, canonical conflict error, modality conflict
   error, cycle error on fixture profiles.
3. Checker kinds `length`, `char`, `phrase`, `pattern` (`subject`, `clause`),
   `list`, `glossary`, `judgment` (fixture-only) → twelve BASE rules with
   positive / negative / near-miss fixtures. Exit: `test_rules.py` green;
   `test_redproof.py` flips every rule in both directions.
4. `config.py` — `.controlled-english.toml`, surfaces `runtime` /
   `explanatory` / `ignore`, `front_matter_keys`, severity overrides.
5. `baseline.py` — identity, file schema, compatibility refusals, `write`,
   `diff`, `new-only`. Exit: `test_baseline.py`: a stale baseline is refused
   with the reason; an edited `may`-sentence fails `new-only`; a re-wrapped one
   passes.
6. `cli.py` + `report.py` — `lint`, `rules`, `explain`, `baseline`,
   `judgment export`, `check-fixtures`; exit codes 0 / 1 / 2; JSON with
   `tokenizer_version`, `rules`, `not_run`.
7. `profiles/agent/` skeleton (`extends = ["base"]`, generic actors, no rules
   yet) so the shipped tree has a real `extends` chain.
8. Dogfood CI: `docs/**` as explanatory; rule titles and messages as runtime;
   rationales as explanatory; `ruff`; `pytest`. README: what it is, what it is
   not, what green means, install, config shape, the version contract.

Exit for M1: `uvx --from . controlled-english lint .` on this repo is clean;
`controlled-english rules --profiles base` prints twelve rules with revision,
source and per-surface severity.

## M2 — agent layer + Roz Gate profile (`v0.2.0`)

1. `profiles/agent/rules/`: AGENT-M01 (modality by subject class), M02, M03,
   M04 deterministic; AGENT-A01, R01 with deterministic companions; AGENT-J01
   as judgment fixtures (ten cases, half violating).
2. `profiles/roz-gate/` (`extends = ["agent"]`): glossary (actors, gate
   labels, workflow-verb concepts with `clause = "action"`, the MAY / CAN
   modality convention, `allow` lists), RG-T01, RG-S01, RG-A01, RG-W01
   deterministic, RG-J01 fixtures. Each rule `source = "project"`.
3. `profiles/roz-gate/examples/`: five to ten real sentences from Roz Gate's
   current runtime prose with their rewritten forms, each naming the rules it
   trips. These double as the near-miss design for RG rules.
4. `docs/adoption/roz-gate.md`: the measured baseline from `PLAN.md` § 1.3
   re-run with the real tokenizer, per rule, per file.

Exit for M2: `controlled-english lint --profile roz-gate` run from a Roz Gate
checkout (read-only, from this repo's CI against a pinned Roz Gate SHA)
produces the report; the per-rule counts land in `docs/adoption/roz-gate.md`;
the brief's three bad/better pairs (§ 14) are fixtures that fire on the bad
and stay silent on the better.

## M3 — report-only in Roz Gate (Roz Gate issue, not this repo)

Filed and planned in Roz Gate with its `/plan-issue` flow. Shape:

1. `.controlled-english.toml` in Roz Gate: `profiles = ["roz-gate"]`;
   runtime = `commands/**`, `agents/**`, `references/*-brief.md`;
   explanatory = `README.md`, `docs/**`, `references/*.md`; ignore =
   `CHANGELOG.md`, `evals/**`, `docs/learn/**`.
2. One CI job: `uvx --from git+…composable-controlled-language@v0.2.0
   controlled-english lint --format json`, never failing, count published in
   the job summary.
3. `controlled-english baseline write` → `.controlled-english.baseline.json`
   committed. This is the "establish a baseline" step.

Exit: three consecutive Roz Gate PRs show the count in CI; nobody's PR was
blocked.

## M4 — enforce on new or modified runtime prose (Roz Gate issue; this repo `v0.3.0`)

1. Roz Gate flips `baseline.mode = "new-only"`; the CI job may now fail on
   `error`-level findings not in the baseline. Because identity is a content
   hash that preserves inline code, placeholders and numbers, an edited
   sentence is new prose and must pass.
2. Framework upgrades in Roz Gate are one PR each: bump the pinned tag, run
   `baseline write`, review the baseline diff. A stale baseline is refused by
   the tool, so the step cannot be skipped silently.
3. Roz Gate's pre-push gains one line (same command, `--format compact`).
4. Shrinking the baseline: **prose-only PRs**, one runtime file each, no
   behaviour change, lint-tier case asserts the baseline count went down and
   nothing else moved. Order by leverage: the `may` and `should` sites first
   (tens, meaning-level), then STOP sites, then dash-chains and semicolons
   (hundreds, structure-level).
5. This repo: whatever M3 taught about false positives becomes near-miss
   fixtures; severities that proved wrong move, with a changelog line each; a
   detection change bumps the rule's `revision`.

Exit: Roz Gate CI red on a PR that adds `should` to `commands/*.md`; green on
the same PR with `MUST`.

## M5 — judgment runner (`v0.4.0`)

1. `controlled-english judgment run --model … --k 2` over the sentences the
   judgment rules apply to, **changed sentences only** by default.
2. Reuses Roz Gate's judgment-tier shape: judge fingerprint recorded, red-proof
   (known-violating fixtures must be judged violating) before any recorded
   run, k runs with agreement reported, never a hard CI gate in its first
   release.
3. AGENT-J01, RG-J01, and the deterministic rules' judgment companions
   (AGENT-A01, AGENT-R01) run here.

Exit: red-proof green under a recorded fingerprint; one Roz Gate PR carries a
judgment report as a comment.

## M6 — second profile and new inputs (`v0.5.0`)

1. A second profile that is not Roz Gate — candidate: `claude-code-plugin`
   (skills, commands, hooks prose for any plugin) — proving the composition
   semantics with a real conflict to resolve.
2. Hook message extraction: Python string literals assigned to `*_MSG` names
   (Roz Gate's deny messages) linted as runtime prose via `ast`.
3. Glossary `scope` grows (operation families) only if a second adopter needs
   it; the § 4.7 shape already has the slot.

Exit: two profiles compose in one config (`profiles = ["agent",
"claude-code-plugin"]`); a glossary or modality conflict produces the error,
not a silent override.

## Explicitly not planned

From the brief's § 15 and kept: no STE certification, no dictionary, no
auto-rewrite, no IDE plugin, no SaaS, no LLM requirement for a lint run, no
natural-language parser, no Roz Gate workflow semantics in base, no edits to
Roz Gate from here, Markdown/text only.

Added from the reading: no quotation of the standard's text or examples in
this repository, ever; a POS-tagger-backed noun-cluster rule stays out until a
profile shows a need the pattern kind cannot meet.
