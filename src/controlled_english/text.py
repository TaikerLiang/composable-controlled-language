"""Text model: Markdown → prose regions → sentences → tokens.

This module is the tokenizer contract (PLAN § 4.1). Every row of the contract table
is a test in tests/test_text.py. A change to any row bumps TOKENIZER_VERSION, and a
baseline written under another version is refused (baseline.py).

Placeholders inserted into a sentence's `text` are single tokens with no emphasis
marker at a word boundary, so phrase rules never match inside them:
CODE_SPAN (inline code), PAREN_SPAN (parenthetical), DASH_SPAN (dash insertion),
URL_SPAN (link target or bare URL).
"""

from __future__ import annotations

import re
import unicodedata
from bisect import bisect_right
from dataclasses import dataclass, field

TOKENIZER_VERSION = 1

CODE_SPAN = "CODESPAN"
PAREN_SPAN = "PARENSPAN"
DASH_SPAN = "DASHSPAN"
URL_SPAN = "URLSPAN"

# Abbreviations whose trailing period does not end a sentence.
ABBREVIATIONS = (
    "e.g.",
    "i.e.",
    "etc.",
    "cf.",
    "vs.",
    "viz.",
    "et al.",
    "no.",
    "fig.",
    "mr.",
    "ms.",
    "dr.",
    "approx.",
    "vol.",
    "ch.",
    "sec.",
)
# A number followed by one of these is one word (STE 8.6: numbers with units).
UNITS = {"s", "ms", "min", "h", "d", "kb", "mb", "gb", "%", "px", "pt", "x", "words"}

_FILL = "\x01"  # same-length mask for spans that must not influence splitting

# CommonMark code span: a backtick run closes only at a run of the same length.
RE_CODE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.S)
RE_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
RE_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
RE_LINK = re.compile(r"\[([^\]]+)\]\((?:[^()\s]|\([^)]*\))*\)")
RE_REF_LINK = re.compile(r"\[([^\]]+)\]\[[^\]]*\]")
RE_AUTOLINK = re.compile(r"<(?:https?|mailto):[^>]+>")
RE_URL = re.compile(r"(?<![\w`])(?:https?://|www\.)\S+")
RE_WS = re.compile(r"\s+")
RE_DASH = re.compile(r"\s*—\s*|\s+--\s+|\s+–\s+")
RE_TERMINATOR = re.compile(r"[.!?]+[*_)`\"'”’\]]*(?=\s|$)")
RE_FENCE = re.compile(r"^\s*(```|~~~)")
RE_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
RE_LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
RE_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
RE_LINK_DEF = re.compile(r"^\s*\[[^\]]+\]:\s+\S+")
RE_HR = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
# A complete open or close tag alone on a line starts an HTML block (CommonMark
# start condition 6/7); the block runs to the next blank line.
RE_HTML_BLOCK = re.compile(r"^\s*</?[a-zA-Z][a-zA-Z0-9-]*(?:\s[^>]*)?/?>\s*$")
RE_NUM_UNIT = re.compile(r"^\d+(?:[.,]\d+)*$")
RE_ALNUM = re.compile(r"[^\W_]", re.UNICODE)
RE_EMPH_STRONG = re.compile(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1")
RE_EMPH_STAR = re.compile(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?!\w)")
RE_EMPH_UNDER = re.compile(r"(?<!\w)_(?=\S)(.+?)(?<=\S)_(?!\w)")


@dataclass(frozen=True)
class Sentence:
    """One sentence of prose with its source position and derived forms."""

    file: str
    line: int
    col: int
    kind: str  # body | heading | list_item | cell | front_matter | parenthetical | insertion
    raw: str  # source span, soft-wrap newlines preserved
    text: str  # host text: markup stripped, code masked, insertions replaced by one token
    flat: str  # markup stripped, code masked, insertions kept inline
    words: int
    dash_insertions: int = 0
    paren_depth: int = 0
    mixed_nesting: bool = False  # a parenthetical inside a dash insertion, or the reverse

    @property
    def canonical(self) -> str:
        return canonical_sentence(self.raw)


@dataclass
class ListBlock:
    """A vertical list: the sentence that leads into it and the raw text of each item."""

    line: int
    lead_in: Sentence | None
    items: list[tuple[int, str]] = field(default_factory=list)  # (line, item text)


@dataclass
class Document:
    file: str
    sentences: list[Sentence] = field(default_factory=list)
    lists: list[ListBlock] = field(default_factory=list)


# --- canonical form (PLAN § 4.5) -------------------------------------------------


def strip_emphasis(s: str) -> str:
    """Remove emphasis markers where they delimit a run; code spans are untouched."""
    spans = [(m.start(), m.end()) for m in RE_CODE.finditer(s)]
    if not spans:
        return _strip_emphasis_plain(s)
    out, pos = [], 0
    for a, b in spans:
        out.append(_strip_emphasis_plain(s[pos:a]))
        out.append(s[a:b])
        pos = b
    out.append(_strip_emphasis_plain(s[pos:]))
    return "".join(out)


def _strip_emphasis_plain(s: str) -> str:
    s = RE_EMPH_STRONG.sub(r"\2", s)
    s = RE_EMPH_STAR.sub(r"\1", s)
    s = RE_EMPH_UNDER.sub(r"\1", s)
    return s


def canonical_sentence(raw: str) -> str:
    """NFC, emphasis markers removed, whitespace collapsed. Nothing else."""
    s = unicodedata.normalize("NFC", raw)
    s = strip_emphasis(s)
    return RE_WS.sub(" ", s).strip()


# --- inline forms -----------------------------------------------------------------


def _mask(s: str, pattern: re.Pattern[str]) -> str:
    return pattern.sub(lambda m: _FILL * (m.end() - m.start()), s)


def flatten(raw: str) -> str:
    """Markup stripped, code and URLs masked, insertions kept inline, whitespace collapsed."""
    s = RE_IMAGE.sub(r"\1", raw)
    s = RE_CODE.sub(CODE_SPAN, s)
    s = RE_LINK.sub(r"\1", s)
    s = RE_REF_LINK.sub(r"\1", s)
    s = RE_AUTOLINK.sub(URL_SPAN, s)
    s = RE_URL.sub(URL_SPAN, s)
    s = strip_emphasis(s)
    return RE_WS.sub(" ", s).strip()


def count_words(text: str) -> int:
    """Whitespace tokens that contain a letter or digit; a number plus a unit is one."""
    tokens = text.split()
    n, i = 0, 0
    while i < len(tokens):
        tok = tokens[i]
        if not RE_ALNUM.search(tok):
            i += 1
            continue
        if RE_NUM_UNIT.match(tok) and i + 1 < len(tokens):
            nxt = tokens[i + 1].rstrip(".,;:)")
            if nxt.lower() in UNITS:
                i += 2
                n += 1
                continue
        n += 1
        i += 1
    return n


def _paren_spans(masked: str) -> tuple[list[tuple[int, int]], int]:
    """Top-level (open, close) spans of parentheses and the maximum nesting depth."""
    spans, depth, max_depth, start = [], 0, 0, -1
    for i, ch in enumerate(masked):
        if ch == "(":
            if depth == 0:
                start = i
            depth += 1
            max_depth = max(max_depth, depth)
        elif ch == ")" and depth > 0:
            depth -= 1
            if depth == 0:
                spans.append((start, i + 1))
    return spans, max_depth


def _dash_spans(masked: str, parens: list[tuple[int, int]]) -> tuple[list[tuple[int, int]], bool]:
    """Dash insertions as (start, end) spans over the inner text; flags a dash inside a paren."""
    dash_in_paren = False
    dashes = []
    for m in RE_DASH.finditer(masked):
        if any(a < m.start() < b for a, b in parens):
            dash_in_paren = True
            continue
        dashes.append(m)
    spans = []
    i = 0
    while i < len(dashes):
        if i + 1 < len(dashes):
            spans.append((dashes[i].end(), dashes[i + 1].start()))
            i += 2
        else:
            end = len(masked)
            tail = RE_TERMINATOR.search(masked, dashes[i].end())
            if tail:
                end = tail.start()
            spans.append((dashes[i].end(), end))
            i += 1
    return spans, dash_in_paren


def _mask_abbreviations(masked: str) -> str:
    low = masked.lower()
    out = list(masked)
    for abbr in ABBREVIATIONS:
        start = 0
        while True:
            k = low.find(abbr, start)
            if k < 0:
                break
            if k == 0 or not low[k - 1].isalnum():
                for j, ch in enumerate(abbr):
                    if ch == ".":
                        out[k + j] = _FILL
            start = k + len(abbr)
    return "".join(out)


def _split_points(par: str, lead_in_colon: bool) -> list[int]:
    """End offsets of sentences in a paragraph string."""
    masked = _mask(par, RE_CODE)
    masked = _mask(masked, RE_LINK)
    parens, _ = _paren_spans(masked)
    m = list(masked)
    for a, b in parens:
        for k in range(a + 1, b - 1):
            m[k] = _FILL
    masked = _mask_abbreviations("".join(m))
    ends = [t.end() for t in RE_TERMINATOR.finditer(masked)]
    if lead_in_colon and par.rstrip().endswith(":"):
        ends.append(len(par.rstrip()))
    if not ends or ends[-1] < len(par.rstrip()):
        ends.append(len(par))
    return sorted(set(ends))


class _Para:
    """Lines of one prose block with their source positions, joined by newlines."""

    def __init__(self, file: str, kind: str):
        self.file = file
        self.kind = kind
        self.parts: list[tuple[int, int, str]] = []  # (line, col offset, text)

    def add(self, line: int, col: int, text: str) -> None:
        self.parts.append((line, col, text))

    def joined(self) -> tuple[str, list[int]]:
        text = "\n".join(p[2] for p in self.parts)
        starts, pos = [], 0
        for _, _, t in self.parts:
            starts.append(pos)
            pos += len(t) + 1
        return text, starts

    def position(self, starts: list[int], offset: int) -> tuple[int, int]:
        idx = bisect_right(starts, offset) - 1
        line, col, _ = self.parts[idx]
        return line, col + (offset - starts[idx]) + 1


def _build_sentence(
    file: str, kind: str, raw: str, line: int, col: int, out: list[Sentence], line_of=None
) -> Sentence:
    """Build one Sentence from its raw span and append its insertion children to `out`."""
    raw_clean = RE_HTML_COMMENT.sub(lambda m: " " * (m.end() - m.start()), raw)
    masked = _mask(raw_clean, RE_CODE)
    masked = _mask(masked, RE_LINK)
    parens, depth = _paren_spans(masked)
    dashes, dash_in_paren = _dash_spans(masked, parens)
    mixed = dash_in_paren or any(
        any(da <= pa and pb <= db for da, db in dashes) for pa, pb in parens
    )
    # host text: replace top-level insertions with one token each
    repl = [(a, b, f" {PAREN_SPAN} ") for a, b in parens]
    for a, b in dashes:
        if not any(pa <= a and b <= pb for pa, pb in parens):
            repl.append((a, b, f" {DASH_SPAN} "))
    repl.sort()
    host, pos = [], 0
    for a, b, token in repl:
        if a < pos:
            continue
        host.append(raw_clean[pos:a])
        host.append(token)
        pos = b
    host.append(raw_clean[pos:])
    host_text = "".join(host)
    host_text = re.sub(rf"\s*—\s*{DASH_SPAN}\s*—?\s*", f" {DASH_SPAN} ", host_text)
    text = flatten(host_text)
    flat = flatten(raw_clean)
    words = 1 if kind == "heading" else count_words(text)
    sentence = Sentence(
        file=file,
        line=line,
        col=col,
        kind=kind,
        raw=raw_clean.strip(),
        text=text,
        flat=flat,
        words=words,
        dash_insertions=len(dashes),
        paren_depth=depth,
        mixed_nesting=mixed,
    )
    out.append(sentence)
    children = [
        ("parenthetical", a + 1, b - 1)
        for a, b in parens
        if not any(da <= a and b <= db for da, db in dashes)  # emitted by the insertion itself
    ]
    children += [
        ("insertion", a, b) for a, b in dashes if not any(pa <= a and b <= pb for pa, pb in parens)
    ]
    for child_kind, a, b in children:
        inner = raw_clean[a:b].strip()
        if not inner or not RE_ALNUM.search(inner):
            continue
        lead = len(raw_clean[a:b]) - len(raw_clean[a:b].lstrip())
        if line_of is not None:
            c_line, c_col = line_of(a + lead)
        else:
            c_line, c_col = line, col + a + lead
        _build_sentence(file, child_kind, inner, c_line, c_col, out)
    return sentence


def _emit_paragraph(para: _Para, doc: Document, lead_in_colon: bool = True) -> list[Sentence]:
    text, starts = para.joined()
    if not text.strip():
        return []
    made: list[Sentence] = []
    begin = 0
    for end in _split_points(text, lead_in_colon):
        span = text[begin:end]
        lead = len(span) - len(span.lstrip())
        if span.strip():
            line, col = para.position(starts, begin + lead)
            before = len(doc.sentences)
            _build_sentence(
                para.file,
                para.kind,
                span.strip(),
                line,
                col,
                doc.sentences,
                line_of=lambda off, b=begin + lead: para.position(starts, b + off),
            )
            made.append(doc.sentences[before])
        begin = end
    return made


# --- front matter -------------------------------------------------------------------


def _front_matter(lines: list[str], keys: tuple[str, ...], file: str, doc: Document) -> int:
    """Parse a leading YAML block; emit configured string values as prose. Returns lines used."""
    if not lines or lines[0].strip() != "---":
        return 0
    try:
        close = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return 0
    i = 1
    while i < close:
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", lines[i])
        if not m:
            i += 1
            continue
        key, value = m.group(1), m.group(2).strip()
        if value in (">", "|", ">-", "|-"):
            j = i + 1
            parts = []
            while j < close and (lines[j].startswith(" ") or not lines[j].strip()):
                parts.append((j + 1, len(lines[j]) - len(lines[j].lstrip()), lines[j].strip()))
                j += 1
            if key in keys:
                para = _Para(file, "front_matter")
                for ln, col, t in parts:
                    if t:
                        para.add(ln, col, t)
                _emit_paragraph(para, doc, lead_in_colon=False)
            i = j
            continue
        if key in keys and value:
            col = len(lines[i]) - len(lines[i].lstrip()) + len(key) + 1
            col += len(lines[i][col:]) - len(lines[i][col:].lstrip())
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
                col += 1
            para = _Para(file, "front_matter")
            para.add(i + 1, col, value)
            _emit_paragraph(para, doc, lead_in_colon=False)
        i += 1
    return close + 1


# --- block scan ------------------------------------------------------------------


def parse(
    source: str, file: str = "<text>", front_matter_keys: tuple[str, ...] = ("description",)
) -> Document:
    """Turn Markdown or plain text into a Document of sentences and lists."""
    doc = Document(file=file)
    lines = source.split("\n")
    start = _front_matter(lines, front_matter_keys, file, doc)

    para: _Para | None = None
    current_list: ListBlock | None = None
    item_para: _Para | None = None
    last_para_sentences: list[Sentence] = []
    blank_since_para = 0
    in_fence = None
    in_comment = False
    in_html = False

    def flush_para() -> None:
        nonlocal para, last_para_sentences
        if para is not None:
            last_para_sentences = _emit_paragraph(para, doc)
            para = None

    def flush_item() -> None:
        nonlocal item_para
        if item_para is not None and current_list is not None:
            made = _emit_paragraph(item_para, doc, lead_in_colon=False)
            if made:
                text, _ = item_para.joined()
                current_list.items.append(
                    (item_para.parts[0][0], flatten(RE_HTML_COMMENT.sub(" ", text)))
                )
            item_para = None

    def close_list() -> None:
        nonlocal current_list
        flush_item()
        if current_list is not None:
            doc.lists.append(current_list)
            current_list = None

    for idx in range(start, len(lines)):
        line = lines[idx]
        lineno = idx + 1
        stripped = line.strip()

        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if in_html:
            in_html = bool(stripped)
            if in_html:
                continue
        if in_fence is not None:
            if stripped.startswith(in_fence):
                in_fence = None
            continue
        fence = RE_FENCE.match(line)
        if fence:
            flush_para()
            close_list()
            in_fence = fence.group(1)
            continue
        if stripped.startswith("<!--"):
            if "-->" not in stripped[4:]:
                in_comment = True
            continue
        if not stripped:
            flush_para()
            flush_item()
            blank_since_para += 1
            continue
        if RE_HTML_BLOCK.match(line):
            flush_para()
            close_list()
            in_html = True
            continue
        if stripped.startswith(">") or RE_LINK_DEF.match(line) or RE_HR.match(line):
            flush_para()
            close_list()
            continue

        heading = RE_HEADING.match(line)
        if heading:
            flush_para()
            close_list()
            col = len(line) - len(line.lstrip()) + len(heading.group(1)) + 1
            col += len(line[col:]) - len(line[col:].lstrip())
            _build_sentence(file, "heading", heading.group(2), lineno, col + 1, doc.sentences)
            last_para_sentences = []
            blank_since_para = 0
            continue

        if stripped.startswith("|"):
            flush_para()
            close_list()
            if RE_TABLE_SEP.match(line):
                continue
            _emit_row(file, line, lineno, doc)
            last_para_sentences = []
            continue

        item = RE_LIST_ITEM.match(line)
        if item and (current_list is not None or para is None or not para.parts):
            flush_para()
            flush_item()
            if current_list is None:
                lead = (
                    last_para_sentences[-1]
                    if last_para_sentences and blank_since_para <= 1
                    else None
                )
                current_list = ListBlock(line=lineno, lead_in=lead)
            item_para = _Para(file, "list_item")
            col = len(item.group(1)) + len(item.group(2)) + 1
            col += len(line[col:]) - len(line[col:].lstrip())
            item_para.add(lineno, col, item.group(3))
            blank_since_para = 0
            continue

        if current_list is not None and item_para is not None and line.startswith(" "):
            item_para.add(lineno, len(line) - len(line.lstrip()), stripped)
            continue
        if current_list is not None:
            close_list()

        if para is None:
            para = _Para(file, "body")
            blank_since_para = 0
        para.add(lineno, len(line) - len(line.lstrip()), stripped)

    flush_para()
    close_list()
    return doc


def _emit_row(file: str, line: str, lineno: int, doc: Document) -> None:
    masked = _mask(line, RE_CODE)
    cells, start = [], None
    for i, ch in enumerate(masked):
        if ch == "|" and (i == 0 or masked[i - 1] != "\\"):
            if start is not None:
                cells.append((start, i))
            start = i + 1
    if start is not None and start < len(masked) and masked[start:].strip():
        cells.append((start, len(masked)))
    for a, b in cells:
        cell = line[a:b]
        lead = len(cell) - len(cell.lstrip())
        if not cell.strip():
            continue
        para = _Para(file, "cell")
        para.add(lineno, a + lead, cell.strip())
        _emit_paragraph(para, doc, lead_in_colon=False)
