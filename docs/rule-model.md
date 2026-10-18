# Rule model reference

The file formats and the tokenizer contract that `controlled-english` 0.1
implements. `docs/PLAN.md` explains why. This page says what.

## Tokenizer contract (`TOKENIZER_VERSION = 1`)

A Markdown or text file becomes prose regions, each region becomes sentences,
each sentence gets a word count and a canonical form. Every row is a test in
`tests/test_text.py`. Changing a row bumps `TOKENIZER_VERSION`, and a baseline
written under another version is refused.

| element | treatment | source |
|---|---|---|
| fenced code, HTML blocks and comments, link reference definitions, horizontal rules | skipped | framework |
| blockquotes | quoted text, skipped | framework, by analogy with STE 8.6 |
| YAML front matter | string values of `front_matter_keys` (default `description`) are prose, other keys are skipped | framework |
| headings | one word, never length-checked, phrase rules apply | derived, STE 8.6 |
| table cells | each cell is its own region, separator rows skipped | framework |
| list items | a sentence boundary even without punctuation, continuation lines join the item, a lead-in sentence ends at its colon | derived, STE 8.4 |
| inline code | one word, content invisible to phrase and glossary rules | framework, by analogy with STE 8.6 |
| `<placeholder>` | one word | framework, by analogy with STE 8.6 |
| `[text](url)`, autolinks, bare URLs | the text's words, the URL invisible | framework |
| emphasis markers | removed, the words count | framework |
| numbers, `10 s`, `v2.1.0`, `#144` | one word | derived, STE 8.6 |
| hyphenated words | one word | derived, STE 8.7 |
| `(parenthetical)` | one word in the host sentence and its own sentence, checked separately | derived, STE 8.5 |
| em-dash insertion (` — x — `, or ` — x` to the end) | treated like a parenthetical for counting, insertion count feeds BASE-S05 | framework extension, STE 8.2 gives dashes no rule |
| sentence end | `.` `!` `?`, a paragraph-final colon, the end of a list item or cell, abbreviations such as `e.g.` do not end a sentence | framework |

### Canonical sentence

The identity of a finding is `sha256(rule_id, revision, file, canonical_sentence)`.
Canonicalization is exactly, in order: Unicode NFC, emphasis markers removed
where the tokenizer parsed them as emphasis, whitespace runs collapsed to one
space, leading and trailing whitespace trimmed. Everything else is preserved
byte for byte: case, punctuation, inline-code content, placeholders, numbers,
link text and URL.

## Rule file

One TOML file per rule at `profiles/<profile>/rules/<ID>.toml`.

| field | required | values |
|---|---|---|
| `id` | yes | equals the file stem, `LAYER-F01` with a family letter |
| `revision` | yes | positive integer, bumped when detection semantics change |
| `title`, `message`, `rationale` | yes | title and message lint as runtime prose, rationale as explanatory |
| `layer` | yes | equals the profile name |
| `check` | yes | `deterministic`, `judgment`, `both` |
| `kind` | yes | `length`, `char`, `phrase`, `pattern`, `list`, `insertion`, `glossary`, `judgment` |
| `source` | yes | `ste-derived` (requires `lineage`), `framework`, `project` (both may have `inspired_by`, neither may have `lineage`) |
| `severity` | yes | one severity, or a table `{ runtime = …, explanatory = … }` with `error`, `warning`, `advisory`, `disabled` |
| `modality` | no | subset of `obligation`, `prohibition`, `permission`, `possibility` |
| `[params]` | per kind | see below |
| `[[examples]]` | at least one | `bad`, optional `good`; the red-proof tests inject them |
| `[judgment].prompt` | when `check` is `judgment` or `both` | the question a judge model answers |

Message templates take `{match}` and the kind's fields. Checker kinds and
their parameters:

| kind | finds | params |
|---|---|---|
| `length` | sentences over the cap, headings excluded | `max_words = { runtime = 20, explanatory = 25 }`, fields `{words}`, `{max}`, `{surface}` |
| `char` | a forbidden character in a sentence's text | `chars`, field `{count}` |
| `phrase` | whole-word phrases, longest first, case-insensitive | `phrases`, `allow`, `inflect`, `inflect_first`, `readings`, `hints` (fields `{readings}`, `{hint}`) |
| `pattern` | a regex over a sentence, `{{verbs}}` expands to the glossary's imperative verbs | `pattern` or `patterns`, `ignore_case`, `on = "text" \| "flat"`, `subject = "actor" \| "non-actor" \| "any"`, `clause = "action" \| "any"` |
| `list` | items ending in `and` / `or`, lead-ins without a colon | `dangling_conjunction`, `lead_in_colon`, `messages = { dangling, lead_in }` |
| `insertion` | stacked dash insertions, nested parentheses, mixed nesting | `max_dash_insertions`, field `{kinds}` |
| `glossary` | forbidden words and non-canonical aliases of glossary concepts in scope | `message_no_canonical`, fields `{concept}`, `{canonical}`, `{meaning}` |
| `judgment` | nothing at lint time | reported as `not_run` |

### Subject and clause heuristics

`subject` classifies the noun phrase before the match against the merged
glossary `actors`: `actor` (a listed actor, or you / we), `non-actor` (another
noun phrase), `unknown` (a pronoun, a masked span, nothing parseable). `clause
= "action"` accepts a match that is sentence-initial, follows a strength word
(`MUST`, `MUST NOT`, `NEVER`, `DO NOT`, `MAY`), or follows an actor subject.

## Profile and glossary

```toml
# profile.toml
name    = "roz-gate"
extends = ["agent"]
[severity]
"BASE-S01" = { runtime = "warning" }
```

```toml
# glossary.toml
actors = ["patrol", "QA", "the human"]
imperative_verbs = ["answer", "resolve"]

[modality]
permission  = ["MAY"]
possibility = ["CAN"]

[allow]
"BASE-V01" = ["roll back", "set up"]

[[concept]]
name      = "fix-finding"
canonical = "fix"
allowed   = ["fix", "repair"]
forbidden = ["address", "handle"]
meaning   = "change code so the finding no longer applies"
scope     = { surfaces = ["runtime"], clause = "action" }
```

Composition resolves `extends` depth-first, parents first, left to right, each
profile once at its first position. Rules are a union and a duplicate ID is an
error. Severity overrides apply in resolution order, later wins, and the
repository config wins over every profile. Glossary members are a union. Two
different `canonical` values for one concept, or two different bindings for
one modality category, are errors.

## Baseline file

```json
{
  "schema_version": 1,
  "engine_version": "0.1.0",
  "tokenizer_version": 1,
  "profiles": ["base", "agent", "roz-gate"],
  "rules": { "BASE-S01": 1 },
  "ruleset_digest": "sha256 of profiles and the rules map",
  "written_at": "2026-10-18T00:00:00Z",
  "findings": [ { "id": "…", "rule": "BASE-S01", "file": "commands/x.md", "sentence": "…" } ]
}
```

`lint` refuses the baseline, exit 2, when the schema version is unsupported,
the tokenizer version differs, the engine major version differs, the resolved
profiles differ, a rule in effect has another revision, or a rule in effect is
not recorded. A recorded rule that is no longer in effect is stale and ignored.
`baseline diff` reports all of this without refusing.

Modes: `off` reads no baseline and every error fails. `new-only` fails only on
error-level findings whose identity is not in the baseline. `all` annotates
findings with the baseline and every error fails. `--no-fail` always exits 0.
