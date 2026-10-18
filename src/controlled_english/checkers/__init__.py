"""Checker kinds: the only code that knows how to find things (PLAN § 4.2).

Each checker is `check(rule, doc, surface, ruleset) -> list[Finding]`; the engine sets the
severity afterwards. Messages are rule data; checkers only supply the fields the
template names (`{match}`, `{words}`, `{max}`, …).
"""

from __future__ import annotations

import re
from collections.abc import Callable

from ..findings import Finding
from ..rules import Rule, RuleSet
from ..text import Document, Sentence
from . import _clause


class _Fields(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def finding(rule: Rule, s: Sentence, surface: str, match: str = "", **fields) -> Finding:
    fields.setdefault("match", match)
    fields.setdefault("surface", surface)
    return Finding(
        rule_id=rule.id,
        revision=rule.revision,
        file=s.file,
        line=s.line,
        col=s.col,
        surface=surface,
        severity="",
        message=rule.message.format_map(_Fields(fields)),
        match=match,
        sentence=s.canonical,
        kind=s.kind,
    )


_INFLECT = r"(?:s|es|ed|d|ing)?"


def _word_regex(phrases, inflect: bool = False, inflect_first: bool = False) -> re.Pattern[str]:
    """Whole-word alternation, longest first. `inflect` suffixes the phrase; `inflect_first`
    suffixes its first word (phrasal verbs: `sets up`, `spun up` is not covered)."""
    alts = []
    for p in sorted((p for p in phrases if p), key=len, reverse=True):
        words = p.split()
        if inflect_first and len(words) > 1:
            alts.append(
                re.escape(words[0])
                + _INFLECT
                + r"\s+"
                + r"\s+".join(re.escape(w) for w in words[1:])
            )
        else:
            alts.append(re.escape(p).replace(r"\ ", r"\s+"))
    body = "|".join(alts)
    suffix = _INFLECT if inflect else ""
    return re.compile(rf"(?<![\w-])(?:{body}){suffix}(?![\w-])", re.I)


def _mask_allowed(text: str, allowed) -> str:
    if not allowed:
        return text
    return _word_regex(allowed).sub(lambda m: " " * (m.end() - m.start()), text)


def _lookup(table, key: str):
    if not isinstance(table, dict):
        return None
    low = key.lower()
    for k, v in table.items():
        if k.lower() == low:
            return v
    return None


# --- kinds ---------------------------------------------------------------------------


def check_length(rule, doc, surface, rs):
    cap = rule.params.get("max_words", {}).get(surface)
    if not cap:
        return []
    return [
        finding(rule, s, surface, words=s.words, max=cap)
        for s in doc.sentences
        if s.kind != "heading" and s.words > cap
    ]


def check_char(rule, doc, surface, rs):
    out = []
    for s in doc.sentences:
        for ch in rule.params.get("chars", []):
            n = s.text.count(ch)
            if n:
                out.append(finding(rule, s, surface, match=ch, count=n))
    return out


def check_phrase(rule, doc, surface, rs):
    phrases = rule.params.get("phrases", [])
    if not phrases:
        return []
    rx = _word_regex(
        phrases,
        inflect=bool(rule.params.get("inflect", False)),
        inflect_first=bool(rule.params.get("inflect_first", False)),
    )
    allowed = list(rule.params.get("allow", [])) + rs.glossary.allow.get(rule.id, [])
    out = []
    for s in doc.sentences:
        text = _mask_allowed(s.text, allowed)
        for m in rx.finditer(text):
            word = m.group(0)
            extra = {}
            for table in ("readings", "hints"):
                v = _lookup(rule.params.get(table), re.sub(r"\s+", " ", word))
                if v is not None:
                    extra[table[:-1] if table == "hints" else table] = v
            out.append(finding(rule, s, surface, match=word, **extra))
    return out


def check_pattern(rule, doc, surface, rs):
    patterns = rule.params.get("patterns") or [rule.params["pattern"]]
    verbs = "|".join(re.escape(v) for v in rs.glossary.imperative_verbs) or "(?!x)x"
    flags = re.I if rule.params.get("ignore_case", True) else 0
    compiled = [re.compile(p.replace("{{verbs}}", f"(?:{verbs})"), flags) for p in patterns]
    on = rule.params.get("on", "text")
    subject = rule.params.get("subject", "any")
    clause = rule.params.get("clause", "any")
    out = []
    for s in doc.sentences:
        text = s.flat if on == "flat" else s.text
        for rx in compiled:
            m = rx.search(text)
            if not m:
                continue
            start = m.start("match") if "match" in rx.groupindex else m.start()
            before = text[:start]
            if subject != "any" and _clause.subject_class(before, rs.glossary.actors) != subject:
                continue
            if clause == "action" and not _clause.is_action_clause(before, rs.glossary):
                continue
            word = m.group("match") if "match" in rx.groupindex else m.group(0)
            out.append(finding(rule, s, surface, match=word))
            break
    return out


def check_list(rule, doc, surface, rs):
    msgs = rule.params.get("messages", {})
    out = []
    for lb in doc.lists:
        if rule.params.get("dangling_conjunction", True):
            for line, item in lb.items:
                last = re.sub(r"[\s,.;:]+$", "", item).rsplit(" ", 1)[-1].lower()
                if last in ("and", "or"):
                    s = next(
                        (x for x in doc.sentences if x.line == line and x.kind == "list_item"), None
                    )
                    if s is not None:
                        f = finding(
                            rule, s, surface, match=last, detail=msgs.get("dangling", rule.message)
                        )
                        f.message = msgs.get("dangling", rule.message).format_map(
                            _Fields(match=last)
                        )
                        out.append(f)
        if rule.params.get("lead_in_colon", True) and lb.lead_in is not None:
            lead = lb.lead_in
            if not lead.raw.rstrip().endswith(":"):
                last = lead.raw.rstrip()[-1:]
                f = finding(rule, lead, surface, match=last)
                f.message = msgs.get("lead_in", rule.message).format_map(_Fields(match=last))
                out.append(f)
    return out


def check_insertion(rule, doc, surface, rs):
    max_dash = rule.params.get("max_dash_insertions", 1)
    out = []
    for s in doc.sentences:
        kinds = []
        if s.dash_insertions > max_dash:
            kinds.append(f"{s.dash_insertions} dash insertions")
        if s.paren_depth > 1:
            kinds.append("a parenthesis inside a parenthesis")
        if s.mixed_nesting:
            kinds.append("a parenthesis and a dash insertion nested")
        if kinds:
            out.append(
                finding(rule, s, surface, match="", count=len(kinds), kinds="; ".join(kinds))
            )
    return out


def check_glossary(rule, doc, surface, rs):
    out = []
    for concept in rs.glossary.concepts.values():
        if surface not in concept.surfaces:
            continue
        terms = {t: "forbidden" for t in concept.forbidden}
        if concept.canonical:
            for t in concept.allowed:
                if t.lower() != concept.canonical.lower():
                    terms[t] = "alias"
        if not terms:
            continue
        rx = _word_regex(terms, inflect=True)
        for s in doc.sentences:
            for m in rx.finditer(s.text):
                if concept.clause == "action" and not _clause.is_action_clause(
                    s.text[: m.start()], rs.glossary
                ):
                    continue
                f = finding(
                    rule,
                    s,
                    surface,
                    match=m.group(0),
                    concept=concept.name,
                    canonical=concept.canonical or "",
                    meaning=concept.meaning,
                )
                if not concept.canonical and rule.params.get("message_no_canonical"):
                    f.message = rule.params["message_no_canonical"].format_map(
                        _Fields(match=m.group(0), concept=concept.name, meaning=concept.meaning)
                    )
                out.append(f)
    return out


def check_judgment(rule, doc, surface, rs):
    return []


CHECKERS: dict[str, Callable[[Rule, Document, str, RuleSet], list[Finding]]] = {
    "length": check_length,
    "char": check_char,
    "phrase": check_phrase,
    "pattern": check_pattern,
    "list": check_list,
    "insertion": check_insertion,
    "glossary": check_glossary,
    "judgment": check_judgment,
}
