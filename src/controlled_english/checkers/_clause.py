"""Subject classification and action-clause detection shared by pattern and glossary kinds.

Deterministic heuristics over the text before a match. Three subject classes:
`actor` (a glossary actor, or you / we), `non-actor` (any other noun phrase), `unknown`
(a pronoun, a masked span, or nothing parseable). Rules treat `unknown` as advisory
territory, never as an error.
"""

from __future__ import annotations

import re

from ..text import CODE_SPAN, DASH_SPAN, PAREN_SPAN, URL_SPAN

STRENGTH_WORDS = ("MUST NOT", "MUST", "NEVER", "DO NOT", "MAY", "SHOULD", "CAN")
DETERMINERS = (
    "the",
    "a",
    "an",
    "this",
    "that",
    "each",
    "every",
    "any",
    "some",
    "no",
    "its",
    "their",
    "your",
    "our",
    "one",
    "either",
    "neither",
)
UNKNOWN_PRONOUNS = {
    "it",
    "this",
    "that",
    "they",
    "these",
    "those",
    "which",
    "who",
    "what",
    "one",
    "something",
    "anything",
    "everything",
    "nothing",
    "there",
}
SPANS = {CODE_SPAN, DASH_SPAN, PAREN_SPAN, URL_SPAN}


def _last_segment(before: str) -> str:
    seg = re.split(r"[,;:]", before.strip())[-1].strip()
    return re.sub(r"\s+", " ", seg)


def _strip_determiners(phrase: str) -> str:
    words = phrase.lower().split()
    while words and words[0] in DETERMINERS:
        words = words[1:]
    return " ".join(words)


def subject_class(before: str, actors) -> str:
    seg = _last_segment(before)
    if not seg:
        return "unknown"
    words = seg.split()
    if words[-1] in SPANS:
        return "unknown"
    low = seg.lower()
    heads = {_strip_determiners(a) for a in actors}
    for k in range(1, min(4, len(words)) + 1):
        tail = _strip_determiners(" ".join(words[-k:]))
        if tail in heads or tail in ("you", "we", "i"):
            return "actor"
    if _strip_determiners(low).split()[-1:] and words[-1].lower() in UNKNOWN_PRONOUNS:
        return "unknown"
    return "non-actor"


def is_action_clause(before: str, glossary) -> bool:
    """Sentence-initial, after a strength word, or after an actor subject."""
    seg = before.strip()
    if not seg or seg in ("-", "*", "•"):
        return True
    for word in STRENGTH_WORDS:
        if re.search(rf"(?<!\w){re.escape(word)}(\s+(?:also|then|first|now))?\s*$", seg):
            return True
    if re.search(r"\b(?:to)\s*$", seg):
        # "You MUST not forget to address" / "need to address": look before the "to"
        return subject_class(re.sub(r"\b\w+\s+to\s*$", "", seg), glossary.actors) == "actor"
    return subject_class(seg, glossary.actors) == "actor"
