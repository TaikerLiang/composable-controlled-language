# v0.1 plan — composable controlled language for agent-facing repositories

Status: **revision 2, rulings recorded 2026-10-18**. The maintainer ruled
all twelve § 9 decisions as recommended. Nothing here is implemented;
implementation starts on the go signal, in the § 11 order. Revision 2 answers the maintainer's review of revision 1: it
fixes the baseline identity, versions the rule/baseline contract, splits
`base` from `agent`, renames the surfaces, replaces the MUST/MAY-only
modality model with a four-category taxonomy, narrows the vague-qualifier
rule, labels the em-dash handling as a framework extension, tightens the
one-instruction rule, scopes glossary rules to action clauses, separates
STE lineage from framework and project adaptation, and fixes the dogfood
surfaces. The direction is unchanged.

The guiding principle, from the brief: *English used as executable agent
context needs stronger rules than ordinary documentation.* The goal is **one
intended executable interpretation**, not shorter text. The success criterion:
*reduce the number of plausible interpretations without pretending that lint
proves semantic correctness.*

```
ASD-STE100-derived structural discipline      base
        ↓
generic agent-language policy                 agent
        ↓
domain / project profiles                     roz-gate, …
        ↓
repository-specific adoption                  .controlled-english.toml + baseline
```

---

## 1. What the sources actually give us

### 1.1 ASD-STE100 Issue 9 (read in full: Part 1, 53 rules; Part 2 introduction)

What ports to "English as executable context" **without the dictionary**. The
last column says how the framework uses the rule: *derived* means the
framework rule implements the shape of the STE rule; *inspired* means the STE
rule motivated a framework rule that STE itself does not state.

| STE rule | What it says (paraphrased) | Framework use |
|---|---|---|
| 3.6 | Active voice; passive only in description when the agent is unknown. | inspired → AGENT-A01 |
| 4.1 | Short, clear, **not abstract**: name the action. | inspired → the modality layer, AGENT-J01 |
| 4.2 | Do not omit words or use contractions to shorten. | the non-goal "shorter ≠ better" (§ 2) |
| 4.3 | Vertical lists for complex text; every item connects to the lead-in. | derived → BASE-S07 |
| 5.1 / 6.3 | 20 words per procedural sentence, 25 per descriptive. | derived → BASE-S01 (surface defaults) |
| 5.2 | One instruction per sentence unless the actions are simultaneous. | derived → BASE-S03, BASE-S08 |
| 5.3 | Instructions in the imperative; "must" only for safety or an important condition. | inspired → BASE-M02, AGENT-M01 |
| **5.4** | **Condition first, comma, then the command.** | derived → AGENT-M02 |
| 5.5 | Notes give information, never instructions. | roadmap |
| 6.5 / 6.6 | One topic per paragraph; six sentences max. | roadmap (explanatory) |
| **7.1–7.3** | **Safety instruction = level word, then command or condition, then the risk.** | inspired → RG-S01 (a project rule, not an STE safety rule) |
| 8.1 | No semicolons. | derived → BASE-S02 |
| 8.2 | Hyphens join directly related words. A dash is a different mark; STE gives it **no counting rule**. | the em-dash handling is therefore a **framework extension** (§ 4.1) |
| 8.3 | Parentheses have seven permitted uses. | inspired → BASE-S05 |
| **8.4–8.7** | **Word-count rules**: a colon before a list ends a sentence; a parenthetical counts as one word in its host and is counted on its own; quoted text, titles, numbers with units, hyphenated words count as one. | derived → tokenizer contract (§ 4.1) |
| 9.3 | No phrasal verbs. | derived → BASE-V01 (configured list) |
| **9.4** | **Same step, same wording, every time.** | derived → BASE-L01 |
| 1.5 / 1.8 / 1.11 / 1.12 | Technical nouns and verbs come from **your company glossary**. | derived → the profile glossary *is* STE's "company terminology" |
| 1.1 | One word, one meaning. | inspired → BASE-L02 (two-reading connectives; no dictionary) |
| GR-1 | Keep the conjunction "that". | roadmap, advisory |
| GR-3 / GR-4 | A pronoun or "this" with several possible referents is ambiguous. | derived → AGENT-R01 |
| GR-6 | No Latin abbreviations. | derived → BASE-S06 |

What does **not** port: 1.2–1.4, 1.6, 3.1, 9.2 — every rule that is "use the
word only as the dictionary approves it". We have no dictionary and must not
build one from the standard. Rule 1.1's principle (one word, one meaning)
ports without the dictionary in two places: the profile glossary (STE's own
company-terminology mechanism) and BASE-L02, a five-line list of connectives
whose two readings are two execution timings.

Two dictionary facts that constrain our claims: STE **approves** `usually`,
`could` (as "be able to") and uses `as necessary` in approved examples. A
framework rule that flags those words is a framework rule, never an STE rule,
and its metadata must say so (§ 4.2 `source`).

**Licensing — a hard constraint.** Issue 9's copyright notice permits no
reproduction "in whole or in part" without ASD's written authority, and its
distribution page prohibits unauthorized distribution. Consequences:

- This repository is **public**. `.gitignore` excludes `references/*.pdf`.
  The standard is local reading material and is never tracked.
- Rule files **cite rule numbers and paraphrase**. No rule statement, example
  sentence, or dictionary entry is copied.
- The README says: inspired by STE, not an STE implementation, no compliance
  claim.

### 1.2 danyuchn/asd-ste100-skill (MIT)

Ideas reused as ideas (the code is one flat regex list and is not reused):
two modes → our surfaces; two levels → our four severities; `--baseline N`
→ our finding-based baseline; masking of code, tables and quotes; sentence
splitting that respects abbreviations; synonym groups; `--selftest` → our
fixtures and red-proof; its stance that hedges are content and that a clean
run means "the configured checks found nothing".

### 1.3 The first adopter, measured — this reshapes the Roz Gate profile

Measured over the 18 runtime files the brief names (`commands/*.md`,
`agents/*.md`, `references/*-brief.md`; code fences, inline code and table
rows removed; 26 137 words, 1 002 sentences):

| signal | count | reading |
|---|---|---|
| `if possible`, `when appropriate`, `as needed`, `as necessary`, `try to`, `typically`, `when ready`, `if needed` | **0** | the brief's phrase list fires ~0 times on day one |
| `normally` / `usually` | 5 / 1 | the only frequency adverbs present |
| sentences over 20 words | **523 (52 %)** | average 26.1 words |
| sentences over 35 words | 227 (22 %) | |
| semicolons in prose | **366** | |
| em-dashes in prose | **685** | dash-chains are the house style |
| open parentheses in prose | 682 | often nested, often inside a dash-chain |
| `may` | 30 | permission ("a human may run it") and possibility ("the ref may survive") mixed |
| `should` | 10 | obligation or recommendation — unpinned |
| `once` / `since` / `while` | 23 / 18 / 19 | two-reading connectives; `once` occurs in **both** readings ("once the implementation has landed" vs "you act once") |
| `resolve(d)` / `answer(ed)` / `fix(ed)` / `address(ed)` | 33 / 54 / 37 / 11 | `address` names none of the other three |
| `STOP` (bold) / `stop` | 59 / 41 | ~100 stop points |
| YAML front matter `description:` | every command | runtime prose; one is 53 words with three em-dashes |

Three consequences:

1. **Day-one volume is in the hundreds for structure, in the tens for
   meaning.** Structural rules start as baseline-tracked warnings. Meaning
   rules are few enough to be `error` from the first enforcing run, and they
   are the rules that change what an agent does.
2. **The tokenizer decides whether BASE-S01 is signal or noise.** STE's own
   counting rules (8.4–8.7) handle inline code, placeholders, numbers and
   parentheticals. Dash insertions need a framework decision (§ 4.1, § 9).
3. **Roz Gate rules are designed against Roz Gate's text**: the `may` / `can`
   convention, the answer/resolve/fix/address glossary, STOP-with-resume,
   gate-label actor, target-state naming.

---

## 2. Design principles (binding for v0.1)

1. **Readability and instruction correctness are two different problems.**
   `base` serves the first; `agent` and project profiles serve the second.
2. **Detect and explain. Never rewrite.**
3. **Strength words are content.** The linter flags an *ambiguous* strength
   word. It never suggests removing MUST, MUST NOT, MAY, CAN, or a hedge.
4. **Rules are data; checkers are code.** A rule is a TOML file; a profile is
   a directory; the engine knows seven checker kinds and no project.
5. **Deterministic, judgment, or both — declared per rule.** `lint` reports
   judgment rules as `not_run`, never as passed.
6. **Green means "no configured detectable violation".** `Delete the
   database.` lints clean.
7. **Baselines are first-class.** Report → baseline → enforce on new or
   modified prose → shrink.
8. **Lineage is honest.** Every rule declares `source = ste-derived |
   framework | project`. A project workflow rule never implies ASD requires it.
9. **Contracts are versioned.** Rule `revision`, `tokenizer_version` and the
   baseline `schema_version` exist from day one; an incompatible baseline is
   refused, never silently applied.

---

## 3. Repository layout (v0.1)

```
.
├── profiles/
│   ├── base/                     # layer 1: STE-derived structural discipline
│   │   ├── profile.toml          # no extends
│   │   ├── rules/BASE-*.toml
│   │   └── glossary.toml         # modality taxonomy, imperative verbs, phrasal verbs
│   ├── agent/                    # layer 2: generic agent-language policy
│   │   ├── profile.toml          # extends = ["base"]
│   │   ├── rules/AGENT-*.toml
│   │   └── glossary.toml         # generic actors: you, the agent, the user, the human
│   └── roz-gate/                 # layer 3: first project profile
│       ├── profile.toml          # extends = ["agent"]
│       ├── rules/RG-*.toml
│       ├── glossary.toml         # seats, gate labels, workflow verbs, MAY/CAN convention
│       └── examples/             # before/after from real Roz Gate prose
├── src/controlled_english/
│   ├── text.py                   # region model, tokenizer, sentence splitter, canonical_sentence; TOKENIZER_VERSION
│   ├── rules.py                  # Rule / Profile / Glossary dataclasses, loader, schema, composition
│   ├── config.py                 # .controlled-english.toml, surfaces
│   ├── checkers/                 # one module per checker kind
│   ├── baseline.py               # identity, file schema, compatibility, write / diff
│   ├── report.py                 # human, compact, JSON
│   └── cli.py
├── tests/
│   ├── fixtures/<RULE-ID>/{positive,negative,near-miss}.md
│   ├── fixtures/judgment/<RULE-ID>.json
│   ├── fixtures/profiles/        # tiny profiles that exercise composition and its errors
│   ├── test_text.py              # tokenizer contract, canonicalization
│   ├── test_rules.py             # every rule dir; schema; source/lineage validation
│   ├── test_redproof.py          # mutation both directions
│   ├── test_compose.py           # resolution order, later-wins, canonical conflict, cycles
│   ├── test_baseline.py          # identity table (§ 4.5), compatibility refusals
│   └── test_config.py
├── docs/{PLAN.md, ROADMAP.md, rule-model.md, adoption/roz-gate.md}
└── pyproject.toml                # uv project, Python ≥ 3.11 (tomllib), stdlib-only runtime
```

Every layer, including `base`, is a profile directory under `profiles/`, so
the loader has one code path. `base` is distinguished only by having no
`extends`. Runtime dependencies: none. Dev: pytest, ruff.

---

## 4. The models

### 4.1 Text model — a versioned contract

`text.py` turns a Markdown file into **prose regions** (each with a surface),
regions into **sentences**, sentences into **tokens** with a word count, and
gives every sentence a **canonical form** (§ 4.5). `TOKENIZER_VERSION = 1` is
a constant in `text.py`; any change to a row below bumps it, and a baseline
written under another version is refused (§ 4.5).

| element | treatment | source |
|---|---|---|
| fenced code, HTML blocks, link reference definitions | not prose; skipped | framework |
| YAML front matter | string values of configured keys (default `description`) **are prose**; all other keys skipped | framework |
| headings | one word each; never length-checked; phrase rules apply | derived (8.6 titles) |
| table cells | each cell is its own prose region | framework |
| list items | a list item is a sentence boundary even without terminal punctuation; a lead-in sentence ends at its colon | derived (8.4) |
| inline code `` `x` `` | one word; content invisible to phrase and glossary rules | framework, by analogy with 8.6 |
| `<placeholder>` | one word | framework, by analogy with 8.6 |
| `[text](url)` | the text's words; URL invisible | framework |
| **bold**, *emphasis* | markers removed; words count | framework |
| numbers, `10 s`, `v2.1.0`, `#144` | one word | derived (8.6) |
| hyphenated word | one word | derived (8.7) |
| `(parenthetical)` | one word in the host sentence **and** its own sentence, checked separately | derived (8.5) |
| em-dash insertion (` — x — ` or ` — x` to sentence end) | **framework extension**: treated like a parenthetical for counting (one word in the host, its own sentence); insertion count feeds BASE-S05 | framework (8.2 gives dashes no rule) |
| sentence end | `.` `!` `?`, a lead-in colon, end of list item or table cell; abbreviations (`e.g.`, `vs.`, `No.`) do not end a sentence | framework |

The em-dash row is the one place the tokenizer goes beyond STE, and the
alternative (count dash-inserted words in the host; let BASE-S05 alone handle
dashes) is ruling 4 in § 9. The reason to prefer the extension: Roz Gate uses
dashes exactly where STE uses parentheses, and counting them in the host makes
BASE-S01 and BASE-S05 fire twice on one defect.

Each row is a test in `test_text.py` and a paragraph in `docs/rule-model.md`.

### 4.2 Rule model

One TOML file per rule. Fixed fields; `params` is per kind.

```toml
id          = "AGENT-M02"
revision    = 1                          # bump when meaning or detection semantics change materially
title       = "A stop condition comes before the action it guards"
layer       = "agent"                    # must equal the owning profile's name
check       = "deterministic"            # deterministic | judgment | both
kind        = "pattern"                  # length | char | phrase | pattern | list | glossary | judgment
source      = "ste-derived"              # ste-derived | framework | project
lineage     = ["STE 5.4"]                # required when ste-derived; citations, never quotations
# inspired_by = ["STE 7.1"]              # optional when framework | project; lineage forbidden there
severity    = { runtime = "warning", explanatory = "advisory" }
modality    = []                         # optional: categories from § 4.6 the rule concerns
message     = "The condition `{match}` follows the command it guards. Put the condition first, then a comma, then the command."
rationale   = """
An agent executes left to right. A command followed by `unless …` has already
been read as a command when the exception arrives. STE 5.4 orders condition,
comma, command for the same reason.
"""

[params]
pattern = '^(?P<cmd>[A-Z][^,.]{0,60}?)\s+(?P<match>unless|except when|except if|if not)\b'

[[examples]]
bad  = "Merge the branch unless a review thread is open."
good = "If a review thread is open, do not merge. Otherwise, merge `<feat-branch>` into `<spec-branch>`."

[judgment]                               # present when check is judgment | both
prompt = "…"
```

Schema rules enforced by `check-fixtures`: `source = "ste-derived"` requires
`lineage` and forbids `inspired_by`; the other two sources forbid `lineage`.
`revision` is a positive integer. A rule ID is owned by exactly one profile.

**Revision policy.** Bump `revision` when the rule's meaning or detection
changes so that a sentence previously reported (or not) would now be judged
differently: a new trigger word, a changed pattern, a changed subject
heuristic. Do not bump for a message reword, a rationale edit, or a new
near-miss fixture that the current detection already passes. A revision bump
is a minor release of the framework and is listed in the changelog with the
reason.

**Dogfood surfaces for rule metadata.** `title` and `message` are linted as
`runtime` (they instruct a writer). `rationale` is linted as `explanatory`.
Examples are fixtures and are not linted.

Checker kinds in v0.1 (the only code that knows how to find things):

| kind | finds | params |
|---|---|---|
| `length` | sentences over a word cap | `max_words = { runtime = 20, explanatory = 25 }` |
| `char` | a forbidden character in prose | `chars` |
| `phrase` | any of a phrase list, whole-word, case-insensitive | `phrases`, optional `allow` |
| `pattern` | a regex over one sentence, named groups feed the message | `pattern`; optional `subject = "actor" \| "non-actor" \| "any"` (classifies the noun phrase before the match against glossary actors) ; optional `clause = "action" \| "any"` |
| `list` | structural list defects | `dangling_conjunction`, `lead_in_colon` |
| `glossary` | a forbidden or non-canonical member of a glossary concept in scope | reads the merged glossary (§ 4.7) |
| `judgment` | nothing at lint time; validates fixtures; exports prompts | `prompt` |

### 4.3 Profiles, layers, composition

Three layers ship in this repository, each a profile:

```toml
# profiles/base/profile.toml
name = "base"

# profiles/agent/profile.toml
name    = "agent"
extends = ["base"]

# profiles/roz-gate/profile.toml
name    = "roz-gate"
extends = ["agent"]
[severity]                               # overrides by rule id, per surface
"BASE-S01" = { runtime = "warning" }
"BASE-M02" = { runtime = "error" }
```

A profile owns rules, severity overrides and a glossary. **A profile declares
no paths**; which files are which surface is the adopter's decision in
`.controlled-english.toml` (§ 4.4). This keeps composition path-free.

**Resolution.** The repo config lists profiles; the engine resolves each
profile's `extends` transitively, depth-first, parents before children,
left to right, each profile included once at its first position. A cycle is a
config error. Example: `profiles = ["agent", "api-docs", "security"]` where
`api-docs` extends `base` and `security` extends `agent` resolves to
`base, agent, api-docs, security`.

**Merge, in resolution order — deterministic, no silent choice:**

| what | semantics |
|---|---|
| rules | union; the same rule ID in two profiles is an error |
| severity | later profile's override wins, per rule, per surface; the repo config wins over every profile |
| glossary concept members (`allowed`, `forbidden`, actors, imperative verbs) | union |
| glossary `canonical` for one concept | two different values is an **error** naming both profiles and the concept; the same value is fine |
| modality convention (§ 4.6) | the same conflict rule as `canonical`: two profiles binding one category to different words is an error |

A future technical-documentation repository selects `profiles = ["base"]`
and gets structure without actor or modality rules; that is the test that
the layering is real.

### 4.4 Repository configuration

`.controlled-english.toml` at the adopter's root:

```toml
profiles = ["roz-gate"]                      # transitive extends supply agent and base

[surfaces]
runtime     = ["commands/**/*.md", "agents/**/*.md", "references/*-brief.md"]
explanatory = ["README.md", "docs/**/*.md", "references/*.md"]
ignore      = ["CHANGELOG.md", "evals/**", "docs/learn/**"]
front_matter_keys = ["description"]          # which front-matter strings are prose

[rules]
"BASE-V01" = "disabled"                      # or { runtime = "advisory" }

[baseline]
file = ".controlled-english.baseline.json"
mode = "new-only"                            # off | new-only | all
```

Surfaces (§ 9 ruling 5): **`runtime`** — prose that influences agent
execution; length cap 20. **`explanatory`** — prose a human reads; cap 25.
**`ignore`** — never linted. The names describe the kind of prose; severity
names (`error warning advisory disabled`) describe enforcement; the two
vocabularies never mix. Note that `runtime = 20` is itself a framework
decision: STE's 20 is for procedural sentences and a brief contains
descriptive ones; the runtime surface takes the stricter cap because the
reader executes it.

That is the whole language: profiles, surfaces, per-rule severity, baseline.
No includes, no conditionals, no per-path rule overrides in v0.1.

### 4.5 Finding and baseline identity

A finding is `(rule_id, revision, file, line, col, surface, severity,
message, match, sentence)`. Its baseline identity is

```
sha256(rule_id + "\n" + str(revision) + "\n" + file + "\n" + canonical_sentence)
```

where `file` is the repo-relative POSIX path and `canonical_sentence` is
produced by exactly these steps, in order, and nothing else:

1. Take the sentence's raw Markdown span as the tokenizer sliced it
   (including backticks, placeholders, link syntax, punctuation).
2. Unicode NFC normalization.
3. Remove emphasis markers (`**`, `__`, `*`, `_`) **only where the tokenizer
   parsed them as emphasis**; an underscore inside `snake_case` is not a
   marker and stays.
4. Collapse every whitespace run, including soft-wrap newlines, to one space;
   trim.

Preserved byte for byte: case, punctuation, inline-code content,
`<placeholders>`, numbers, labels, link text and URL. The table below is
`test_baseline.py`:

| edit | identity |
|---|---|
| re-wrap the paragraph; edit an unrelated sentence above | same |
| `**STOP**` → `STOP` | same (emphasis only) |
| `` `status: ready-for-dev` `` → `` `status: ready-for-spec` `` | **different** |
| `` `<feat-branch>` `` → `` `<qa-branch>` `` | **different** |
| `10 s` → `30 s`; `(5)` → `(6)` | **different** |
| `must` → `MUST` | different (case is semantic in Roz Gate) |
| rename or move the file | different for every sentence in it (re-baseline the file) |
| rule revision bump | different for every finding of that rule (and the baseline is refused until rewritten) |

A modified semantic token therefore makes the sentence **new prose**, and
`mode = "new-only"` requires it to pass every `error`-level rule, not only
the one it was baselined for. That is intended.

**Baseline file** (`schema_version` 1):

```json
{
  "schema_version": 1,
  "engine_version": "0.1.0",
  "tokenizer_version": 1,
  "profiles": ["roz-gate"],
  "rules": { "BASE-S01": 1, "BASE-S02": 1, "RG-S01": 1 },
  "ruleset_digest": "sha256 of profiles + the sorted rules map",
  "written_at": "2026-10-18T00:00:00Z",
  "findings": [
    { "id": "…", "rule": "BASE-S01", "file": "commands/integrate.md",
      "sentence": "canonical sentence, stored so the baseline is reviewable in a PR diff" }
  ]
}
```

**Compatibility, checked before any baseline is applied; failure is exit 2
with the reason, never a silent apply:**

| condition | result |
|---|---|
| `schema_version` unsupported | refuse |
| `tokenizer_version` ≠ engine's | refuse: re-baseline |
| `profiles` ≠ the config's resolved list | refuse |
| a rule in effect has a different `revision` than recorded | refuse, naming the rules |
| a rule in effect is absent from `rules` (new rule) | refuse, naming the rules: the baseline is stale |
| a recorded rule is no longer in effect (disabled, removed) | fine; its entries are ignored and `baseline diff` lists them as stale |
| `engine_version` major differs | refuse |

The adopter's upgrade path is therefore one PR: bump the pinned framework
tag, run `baseline write`, review the baseline's git diff (the stored
sentences make it readable), merge. `ruleset_digest` lets `baseline diff`
say in one line whether the rule set moved.

### 4.6 Modality model

Four categories. Base data (`profiles/base/glossary.toml [modality]`) names
the canonical runtime forms and the words the framework treats as ambiguous;
profiles may bind categories to conventions.

| category | canonical runtime forms | ambiguous words (flagged on `runtime`) |
|---|---|---|
| **obligation** | imperative; `MUST` | `should`, `ought to`, `is expected to`, `needs to`, `has to`, `is required to`, `is supposed to`, `it is recommended` |
| **prohibition** | `MUST NOT`, `NEVER`, `DO NOT` | `should not`, `is not expected to` |
| **permission** | `MAY` | a permission modal with an unclear or non-actor subject |
| **capability / possibility** | `CAN`; explicit wording (`can fail`, `it is possible that`) | a possibility modal with an actor subject in an instruction |

What the framework never does: it never tells a writer to turn a possibility
into MUST or MAY. `The command could fail if the remote is unavailable.`
states a possibility and is not flagged by any base or agent rule. `could`
and `might` are flagged only by a profile that has bound possibility to a
word (Roz Gate binds it to `CAN`), and then only as advisory.

Rules on this model: BASE-M02 flags the ambiguous obligation and prohibition
words (deterministic). AGENT-M01 checks permission against possibility by
the subject class of the modal (deterministic where the profile declares a
convention; advisory otherwise). The Roz Gate profile declares

```toml
[modality]
permission  = ["MAY"]
possibility = ["CAN"]
```

so that `may` with a non-actor subject (`the ref may survive`) is an error
with the message "a non-actor holds no permission; write `can`", and `can`
with an actor subject (`QA can run its suite`) is an advisory asking whether
this grants permission (then `MAY`) or states a capability (then it stands).
The subject is classified against the merged glossary actors; a pronoun or an
unparseable subject is `unknown` and gets the advisory, never the error.

### 4.7 Glossary model

A glossary concept:

```toml
[[concept]]
name      = "resolve-thread"
canonical = "resolve"                    # the one word for this meaning
allowed   = ["resolve", "resolved"]      # inflections and accepted aliases
forbidden = ["address", "handle", "deal with", "take care of", "close out"]
meaning   = "mark the forge review thread resolved"
scope     = { surfaces = ["runtime"], clause = "action" }
```

Scope decides where a hit is a finding. `surfaces` is the surface list;
`clause = "action"` restricts hits to **action clauses**: the word is the
head of an imperative (sentence-initial verb), or follows a strength word
(`MUST`, `MUST NOT`, `NEVER`, `MAY`), or follows an actor subject from the
glossary. `This section addresses the compatibility problem.` has a
non-actor subject and is not an action clause; `Address the finding.` and
`You MUST address every finding.` are. `clause = "any"` is the whole-surface
ban for the few words that are never right (Roz Gate: `approve`).

v0.1 implements exactly `surfaces` and `clause`. The shape leaves room for
operation families (a concept that names a set of forge ops) without a
model change: that is one more key under `scope`, added when a profile needs
it.

Three further glossary tables use the same merge rules: `actors`
(subject classification), `imperative_verbs` (BASE-S03 / S08 and the
`clause = "action"` heuristic), and `modality` (§ 4.6).

---

## 5. The first rules

Severities are base defaults (`runtime` / `explanatory`). Every rule ships
`positive.md`, `negative.md`, `near-miss.md`, a message, a rationale, at
least one example, `revision = 1`, and a `source`. Counts are the measured
day-one estimate on Roz Gate's runtime surfaces.

### 5.1 `base` — STE-derived structural discipline (12 rules)

| ID | rule | kind | source | runtime / explanatory | RG est. |
|---|---|---|---|---|---|
| BASE-S01 | Sentence over the surface cap (20 / 25), counted per § 4.1 | length | derived 5.1, 6.3, 8.4–8.7 | warning / advisory | ~520 |
| BASE-S02 | Semicolon in prose | char | derived 8.1 | error / warning | ~366 |
| BASE-S03 | Two instructions in one sentence, joined by a **sequence marker**: `then`, `and then`, `after that`, `;`, or ` — ` between two imperative heads (glossary `imperative_verbs`) | pattern | derived 5.2 | warning / advisory | tens |
| BASE-S05 | Stacked insertions: more than one dash insertion in a sentence, or a parenthetical nested in a parenthetical or a dash insertion | pattern | framework, inspired 4.1, 8.3 | warning / advisory | hundreds |
| BASE-S06 | Latin abbreviation: `e.g.`, `i.e.`, `etc.`, `cf.`, `vs.`, `viz.` | phrase | derived GR-6 | warning / advisory | few |
| BASE-S07 | A list item ends in `and` / `or`; a list lead-in lacks its colon | list | derived 4.3 | warning / warning | few |
| BASE-S08 | Two imperative heads joined by **bare `and`**: deterministic signal only; the judgment prompt asks whether the actions are simultaneous (STE's exception) or sequential (then S03 applies) | pattern + judgment (`both`) | derived 5.2 | advisory / advisory | tens |
| BASE-M01 | High-confidence vague qualifier: `if possible`, `where possible`, `when appropriate`, `where appropriate`, `as appropriate`, `as needed`, `as necessary`, `when ready`, `if needed`, `try to`, `attempt to` | phrase | framework, inspired 4.1, 5.3 (STE approves `as necessary`) | error / advisory | 0 today |
| BASE-M02 | Ambiguous obligation or prohibition word (§ 4.6 table); the message names the two categories to choose between. Never flags `may`, `can`, `could`, `might`. | phrase | framework, inspired 5.3 | error / advisory | ~10 |
| BASE-L01 | Glossary: a `forbidden` word in scope, or a non-canonical `allowed` alias where a canonical exists | glossary | derived 1.11, 9.4 | error / warning | by profile |
| BASE-L02 | **Two-reading connective**: `once` (after / one time), `since` (after / because), `while` (during / although). The message names both readings and the unambiguous word for each. `as` and `so` are not in the list: too frequent, mostly unambiguous in context; they live in near-miss fixtures and AGENT-J01. | phrase | framework, inspired 1.1 | warning / advisory | ~60 |
| BASE-V01 | Phrasal verb from the configured list (`spin up`, `kick off`, `reach out`, `dive into`, `circle back`, `end up`, `figure out`, `wrap up`, …); a profile's `allow` keeps domain terms (`roll back`, `set up`) | phrase | derived 9.3 | warning / advisory | tens |

Dropped from v0.1: BASE-V02 (agentless passive, advisory). It would report
hundreds of advisories on day one with a known false-positive rate; the
agentless-passive signal survives as AGENT-A01's deterministic companion.
BASE-S04 (list for three or more actions) stays deferred to judgment.

Frequency adverbs (`normally`, `usually`, `generally`, `typically`,
`in general`, `ideally`) are **not** in base: STE approves `usually`, and
the words are valid descriptive English. They are an agent-layer concern
(AGENT-M04) and fire only when they control a runtime decision.

There is **no general vocabulary list** in any layer. STE's dictionary is the
standard's protected core and a model reader does not stumble on `commence`;
it stumbles on a word with two readings. Vocabulary control is therefore the
profile glossary (domain terms), the modality table, and BASE-L02's
connectives — all self-authored, all scoped. A larger self-authored "plain
instruction vocabulary" is a rejected alternative (ruled 2026-10-18): high
maintenance, looks derivative of STE, low value for the reader we target.

### 5.2 `agent` — generic agent-language policy (7 rules)

| ID | rule | check | source | runtime / explanatory |
|---|---|---|---|---|
| AGENT-A01 | The actor is named when the surface declares more than one actor. Deterministic companion: an agentless passive or a bare imperative in a file whose glossary declares ≥ 2 actors → advisory pointer to the judgment question. | both | framework, inspired 3.6 | advisory / disabled |
| AGENT-R01 | A pronoun has one referent. Deterministic companion: sentence-initial bare `This` / `It` / `They` after a sentence with ≥ 2 nouns → advisory. | both | derived GR-3, GR-4 | advisory / advisory |
| AGENT-M01 | **Permission vs possibility by subject class** (§ 4.6): a permission modal with a non-actor subject → error when the profile binds the convention, advisory otherwise; a possibility modal with an actor subject in an instruction → advisory; unknown subject → advisory. | both | framework, inspired 5.3 and the dictionary's MAY / CAN semantics | error (bound) or advisory / disabled |
| AGENT-M02 | A stop condition precedes the action it guards: `<imperative> … unless / except when / if not …` → condition first | deterministic | derived 5.4 | warning / advisory |
| AGENT-M03 | A required action and a complex exception in one sentence: a strength word plus ≥ 2 of `unless`, `except`, `but`, `however`, `otherwise`, ` — ` | deterministic | framework, inspired 4.1, 5.2 | warning / advisory |
| AGENT-M04 | A **frequency adverb controls a runtime decision**: `normally`, `usually`, `generally`, `typically`, `in general`, `ideally` in a sentence that also contains an imperative head, a strength word, a modality word, `STOP`, or a glossary transition verb. The same adverb in a purely descriptive sentence is not flagged. | deterministic | framework, inspired 4.1 (STE approves `usually`) | warning / disabled |
| AGENT-J01 | **Two plausible executions**: "Could two competent agents execute this sentence differently and both claim to have obeyed it? If yes, name the two executions." | judgment | framework, inspired 4.1 | fixtures only in v0.1 |

### 5.3 `roz-gate` — the first project profile (5 rules + data)

All `source = "project"`. `glossary.toml` declares actors (`you`, `the
human`, `patrol`, `the scanner`, `the reviewer`, `QA`, `the implementer`,
`the loop`, `this command`, `the hook`), gate labels (`status:
ready-for-spec`, `status: ready-for-dev`), the modality convention
(`MAY` = permission, `CAN` = possibility), workflow verb concepts, and
`allow` entries for BASE-V01 (`roll back`, `set up`) and for the literal
command name `address-review`.

| ID | rule | check | inspired by | est. |
|---|---|---|---|---|
| RG-T01 | **Canonical workflow verbs**, through BASE-L01's glossary engine with `clause = "action"`, `surfaces = ["runtime"]`: `answer` = reply in a thread without resolving; `resolve` = mark the thread resolved; `fix` = change code to meet a finding. `address`, `handle`, `deal with`, `take care of` are forbidden **in action clauses only**: `This section addresses …` passes. `approve` is `clause = "any"` on runtime: gate labels are the authorization vocabulary. | glossary (det.) | STE 1.11, 9.4 | ~11 + rotation |
| RG-S01 | **STOP says how execution resumes.** A sentence that instructs `STOP` is followed, within the paragraph or list item, by a resume shape from the profile list (`resume`, `the STOP protocol`, `until <who> <does what>`), or the paragraph names the protocol section. A Roz Gate workflow rule shaped like STE's safety-instruction shape; not an STE rule. | pattern (det.) | STE 7.1–7.3 | ~100 sites |
| RG-A01 | **Gate labels have a human subject.** A gate label with an agent actor as subject and a verb in `apply`, `add`, `set`, `move`, `put` → error unless negated (`never applies`). The prose-layer twin of hook rule B. | pattern + `subject = "actor"` (det.) | — | small |
| RG-W01 | **A transition names its target.** `advance`, `move`, `route`, `transition`, `proceed` with `to the next stage` / `onward` / `forward` and no stage number, label, or command name in the sentence → warning. | pattern (det.) | — | small |
| RG-J01 | **Seat-named agent actions.** When a sentence instructs an agent action and the surface has several seats, it names the seat or command. | judgment | — | fixtures only |

The former RG-M01 (`may` has one reading) is no longer a rule: it is
AGENT-M01 plus the profile's modality convention. The same convention serves
any future profile that wants it.

What the profile does **not** do: no Roz Gate semantics in `base` or `agent`;
no rule that depends on the stage machine; no edit to Roz Gate from here.

---

## 6. CLI

```
controlled-english lint [PATHS…] [--config FILE] [--profiles a,b]
                        [--format human|compact|json] [--baseline off|new-only|all]
controlled-english rules [--profiles a,b]           # effective rules, revision, source, severity per surface
controlled-english explain RULE-ID                  # title, rationale, source, lineage, examples
controlled-english baseline write|diff [--config FILE]
controlled-english judgment export [--format json]  # judgment rules + the sentences they apply to; no runner
controlled-english check-fixtures                   # schema-validate every rule, glossary, profile and fixture
```

`ccl` is a second console script. Default output:

```
commands/integrate.md:84
AGENT-M01 error
"may" with a non-actor subject (`the ref`) states a possibility. Write `can`, or name the actor that is permitted.
```

`--format json` carries `tokenizer_version`, the effective `rules` map with
revisions, the findings, and `not_run` for judgment rules. Exit codes:
0 clean under the baseline policy; 1 policy failure; 2 usage, config,
composition, or baseline-compatibility error.

---

## 7. Testing and eval philosophy

*A check that has never been observed to fail is weak evidence*, made
systematic:

- **Per rule, three fixtures**: `positive.md` (`<!-- expect: RULE-ID -->` on
  each triggering line; exact count asserted), `negative.md`, `near-miss.md`
  (where false-positive design lives: `This section addresses …`, `The
  command could fail …`, `Open the PR and the issue`).
- **Red-proof by mutation, both directions, automated** in
  `test_redproof.py`; a rule whose mutation does not flip the result fails CI.
- **Composition tests** on tiny fixture profiles: resolution order with a
  diamond, later-wins severity, same rule ID twice → error, two canonicals →
  error, two modality bindings → error, a cycle → error.
- **Baseline tests**: the identity table in § 4.5 row by row; every
  compatibility refusal in § 4.5; `new-only` failing on an edited
  `may`-sentence and passing on a re-wrapped one.
- **Judgment fixtures** are JSON `{text, surface, expected, why}`; v0.1
  validates and exports them; the runner is M5.
- **Dogfood**: `docs/**` as `explanatory`; rule `title` and `message` as
  `runtime`; rule `rationale` as `explanatory`. CI fails on any of the three.
- **Real-text fixtures for RG rules**: five to ten Roz Gate sentences with
  their rewritten forms in `profiles/roz-gate/examples/`.

---

## 8. What green means

> A clean run means no configured, detectable language-policy violation was
> found on the linted surfaces, and judgment rules were not run. It does not
> mean the instruction is correct, complete, or safe. `Delete the database.`
> passes every rule in this framework.

---

## 9. Decisions that are hard to reverse — rulings requested

**Ruled 2026-10-18: all twelve as recommended.** Kept with their
alternatives so a later reader sees what was rejected and why.

1. **Layering.** `base` → `agent` → project/domain profiles, each a profile
   directory under `profiles/`; `agent` extends `base`; project profiles
   extend `agent` (or `base` alone for non-agent documentation) —
   **recommended**. Alternative: `base` and `agent` as one inseparable
   layer. Decides whether a documentation repository can ever use the
   structural rules without the actor and modality rules.
2. **Baseline / version contract.** Identity =
   `sha256(rule_id, revision, file, canonical_sentence)` with the
   canonicalization in § 4.5 (whitespace, emphasis markers, NFC; everything
   else preserved); baseline records `schema_version`, `engine_version`,
   `tokenizer_version`, `profiles`, per-rule `revision`, `ruleset_digest`;
   any mismatch is a refusal (exit 2) — **recommended**. Alternative: fewer
   fields, or warnings instead of refusals. Decides whether an old baseline
   can ever be applied to new semantics.
3. **Modality taxonomy.** Four categories — obligation, prohibition,
   permission, capability/possibility — with base flagging only ambiguous
   obligation/prohibition words and profiles binding permission/possibility
   to words — **recommended**. Alternative: a MUST/MAY-only model. Decides
   what BASE-M02 and AGENT-M01 mean forever.
4. **Em-dash insertion in the tokenizer.** Treat a dash insertion like a
   parenthetical for counting (one word in the host, its own sentence),
   labelled a framework extension — **recommended** — or count dash-inserted
   words in the host and leave dashes to BASE-S05 alone. Changes every
   BASE-S01 identity set; must be fixed before the first baseline.
5. **Surface names.** `runtime` / `explanatory` / `ignore` — **recommended**
   — or `procedural` / `descriptive` / `ignore`. Surface names appear in
   every rule file and every adopter config.
6. **Rule and config file format.** TOML (stdlib) — **recommended** — or
   YAML (`pyyaml`).
7. **Rule ID scheme.** Layer prefix + family letter + number (`BASE-S01`,
   `AGENT-M01`, `RG-T01`) — **recommended** — or flat per layer. IDs are
   never reused once a baseline references them.
8. **Tokenizer contract apart from dashes.** STE-style counting per § 4.1 —
   **recommended** — or whitespace split. Versioned by `TOKENIZER_VERSION`.
9. **Where the first Roz Gate integration lives.** A Roz Gate CI job
   installing this repo at a pinned tag (`uvx --from git+…@v0.1.0`) —
   **recommended** — or vendoring into Roz Gate's `evals/lint`.
10. **Composition semantics.** Resolution order and merge rules per § 4.3:
    union, later wins on severity, canonical and modality conflicts are
    errors, duplicate rule IDs are errors — **recommended** — or first wins.
11. **The standard's PDF.** Never tracked (`.gitignore` in place) —
    **recommended and done**. See also the note in § 10 about a second copy.
12. **Front matter is prose.** Configured front-matter keys (`description`)
    lint on the surface of their file — **recommended** — or front matter is
    skipped.

Anything not listed is a routine implementation call recorded in
`docs/rule-model.md`.

---

## 10. Assumptions and notes

- Python ≥ 3.11 on every machine that runs the linter. Roz Gate's evals
  already require this.
- Markdown and plain text only in v0.1. Hook deny messages (Python string
  literals) are a roadmap item with an extractor.
- Day one on Roz Gate reports **hundreds** of structural warnings and
  **tens** of meaning-level errors; the structural count shrinks only
  through dedicated prose-only PRs.
- Nothing in this repository edits Roz Gate. Adoption steps there are Roz
  Gate issues planned with its own `/plan-issue` flow.
- **A second copy of the standard** sits untracked in the Roz Gate checkout
  at `docs/ASD-STE100_ISSUE9.pdf`. Roz Gate is public and `docs/` is its
  GitHub Pages source; `git add docs/` there would publish the file. It
  should be deleted or ignored there; the reading copy is this repository's
  `references/`.
- Roz Gate's `MUST`-everywhere convention diverges from STE 5.3 (which
  reserves "must" for safety and important conditions). The profile's
  obligation canonical is therefore `project` data, not STE lineage.

---

## 11. Implementation order for v0.1 (after the rulings)

Each step has a test that must be red before it and green after it.

1. `text.py`: region model, tokenizer, sentence splitter, `canonical_sentence`,
   `TOKENIZER_VERSION` → `test_text.py` covers every § 4.1 row and every
   § 4.5 identity row.
2. `rules.py`: rule schema with `revision` / `source` / `lineage` validation;
   profile loading; resolution and merge per § 4.3 → `test_rules.py`,
   `test_compose.py` (fixture profiles, every error case).
3. Checker kinds `length`, `char`, `phrase`, `pattern` (with `subject`,
   `clause`), `list`, `glossary`, `judgment` (fixture-only) → the twelve
   BASE rules with fixtures; `test_redproof.py` flips every rule both ways.
4. `config.py`: `.controlled-english.toml`, surfaces, `front_matter_keys`,
   severity overrides → `test_config.py`.
5. `baseline.py`: identity, file schema, compatibility refusals, `write`,
   `diff`, `new-only` → `test_baseline.py`.
6. `cli.py` + `report.py`: `lint`, `rules`, `explain`, `baseline`,
   `judgment export`, `check-fixtures`; exit codes; JSON with `not_run`.
7. `profiles/agent/` skeleton (`extends = ["base"]`, glossary actors, no
   rules yet) so the shipped tree exercises a real `extends` chain; AGENT
   rules land in M2 with the Roz Gate profile.
8. Dogfood CI (`docs/**` explanatory; rule titles and messages runtime;
   rationales explanatory; `ruff`; `pytest`) and README (what it is, what it
   is not, what green means, install, config shape, the version contract).

Exit for v0.1: `uvx --from . controlled-english lint .` on this repository is
clean; `controlled-english rules --profiles base` prints twelve rules with
revision, source and per-surface severity; a deliberately stale baseline is
refused with the reason.
