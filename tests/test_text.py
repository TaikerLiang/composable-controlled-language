"""The tokenizer contract (PLAN § 4.1) and canonicalization (PLAN § 4.5), row by row."""

from controlled_english.text import (
    CODE_SPAN,
    DASH_SPAN,
    PAREN_SPAN,
    TOKENIZER_VERSION,
    canonical_sentence,
    count_words,
    parse,
)


def sentences(src, **kw):
    return parse(src, "f.md", **kw).sentences


def bodies(src, **kw):
    return [s for s in sentences(src, **kw) if s.kind not in ("parenthetical", "insertion")]


def test_tokenizer_version_is_an_int():
    assert isinstance(TOKENIZER_VERSION, int) and TOKENIZER_VERSION >= 1


# --- regions ------------------------------------------------------------------------


def test_fenced_code_html_and_link_defs_are_skipped():
    src = "Run it.\n\n```\nnot prose; at all\n```\n\n<!-- a comment. with a period -->\n\n[ref]: https://x.y\n\n<div>\n"
    got = sentences(src)
    assert [s.text for s in got] == ["Run it."]


def test_multiline_html_comment_is_skipped():
    src = "<!--\nhidden. words\n-->\nSeen.\n"
    assert [s.text for s in sentences(src)] == ["Seen."]


def test_front_matter_description_is_prose_and_other_keys_are_not():
    src = '---\ndescription: Drive stage six. Report it.\nargument-hint: "[n]"\n---\n\nBody.\n'
    got = sentences(src)
    assert [(s.kind, s.text, s.line) for s in got] == [
        ("front_matter", "Drive stage six.", 2),
        ("front_matter", "Report it.", 2),
        ("body", "Body.", 6),
    ]


def test_front_matter_block_scalar_and_configured_keys():
    src = "---\nsummary: >\n  First line\n  second line.\ndescription: skipped here\n---\n"
    got = sentences(src, front_matter_keys=("summary",))
    assert [s.text for s in got] == ["First line second line."]
    assert got[0].line == 3


def test_heading_is_one_word_and_visible_to_phrase_rules():
    got = sentences("## Try to run it when appropriate\n")
    assert got[0].kind == "heading"
    assert got[0].words == 1
    assert "when appropriate" in got[0].text


def test_table_cells_are_their_own_regions_and_separator_is_skipped():
    src = "| a | b |\n|---|---|\n| Run it. Then stop. | `code; here` |\n"
    got = sentences(src)
    kinds = {s.kind for s in got}
    assert kinds == {"cell"}
    texts = [s.text for s in got]
    assert "Run it." in texts and "Then stop." in texts
    assert CODE_SPAN in texts


def test_list_item_is_a_sentence_boundary_without_punctuation():
    src = "Steps:\n\n- open the PR\n- merge it\n"
    got = sentences(src)
    assert [(s.kind, s.text) for s in got] == [
        ("body", "Steps:"),
        ("list_item", "open the PR"),
        ("list_item", "merge it"),
    ]
    doc = parse(src, "f.md")
    assert len(doc.lists) == 1
    assert doc.lists[0].lead_in.text == "Steps:"
    assert [t for _, t in doc.lists[0].items] == ["open the PR", "merge it"]


def test_list_item_continuation_lines_join():
    src = "- open the PR\n  and wait\n- done\n"
    got = sentences(src)
    assert got[0].text == "open the PR and wait"
    assert got[0].line == 1


def test_list_after_heading_has_no_lead_in():
    doc = parse("## Steps\n\n- one\n", "f.md")
    assert doc.lists[0].lead_in is None


def test_lead_in_colon_ends_the_sentence_only_at_paragraph_end():
    got = bodies("Do these: open it. Then stop:\n\n- a\n")
    assert [s.text for s in got][:3] == ["Do these: open it.", "Then stop:", "a"]


def test_blockquote_is_quoted_text_and_skipped():
    assert sentences("> A long quoted sentence; with a semicolon.\n\nMine.\n")[0].text == "Mine."


# --- inline elements ----------------------------------------------------------------


def test_inline_code_is_one_word_and_invisible():
    got = sentences("Apply `status: ready-for-dev` now.\n")
    assert got[0].words == 3
    assert "ready" not in got[0].text and CODE_SPAN in got[0].text
    assert got[0].raw == "Apply `status: ready-for-dev` now."


def test_placeholder_is_one_word():
    got = sentences("Merge <feat-branch> into <spec-branch>.\n")
    assert got[0].words == 4


def test_link_text_counts_and_url_is_invisible():
    got = sentences("See [the plan here](https://example.com/a.b.c) now.\n")
    assert got[0].words == 5
    assert "example" not in got[0].text
    assert len(got) == 1


def test_emphasis_markers_are_removed():
    got = sentences("**STOP** here and *wait* for __them__ in snake_case_name.\n")
    assert got[0].text == "STOP here and wait for them in snake_case_name."


def test_numbers_units_versions_and_hyphens_are_one_word():
    assert count_words("wait 10 s then") == 3
    assert count_words("v2.1.0 and #144") == 3
    assert count_words("a well-known long-running thing") == 4
    assert count_words("— → :") == 0


def test_parenthetical_is_one_word_in_host_and_its_own_sentence():
    got = sentences("Remove the valve (the one on the left side of the housing) now.\n")
    host, child = got[0], got[1]
    assert host.words == 5
    assert PAREN_SPAN in host.text
    assert child.kind == "parenthetical"
    assert child.text == "the one on the left side of the housing"
    assert child.words == 9
    assert (child.line, child.col) == (1, 19)


def test_dash_insertion_is_a_framework_extension_counted_like_a_parenthetical():
    got = sentences("The branch carries the code — QA starts after it lands — so nothing blocks.\n")
    host, child = got[0], got[1]
    assert host.words == 9  # "The branch carries the code DASHSPAN so nothing blocks." = 9
    assert DASH_SPAN in host.text
    assert host.dash_insertions == 1
    assert child.kind == "insertion"
    assert child.text == "QA starts after it lands"


def test_trailing_dash_insertion_and_stacking_metrics():
    got = sentences("Do it now — carefully — and then rest — slowly.\n")
    host = got[0]
    assert host.dash_insertions == 2
    assert [s.text for s in got[1:]] == ["carefully", "slowly"]
    nested = sentences("A (b (c) d) e.\n")[0]
    assert nested.paren_depth == 2
    mixed = sentences("A — b (c) d — e.\n")[0]
    assert mixed.mixed_nesting is True
    plain = sentences("A (b) and — c — d.\n")[0]
    assert plain.mixed_nesting is False and plain.paren_depth == 1


def test_parenthetical_inside_a_dash_insertion_is_emitted_once():
    got = sentences("## M4 — enforce new prose (Roz Gate issue; this repo `v0.3.0`)\n")
    kinds = [(s.kind, s.text) for s in got]
    assert kinds.count(("parenthetical", "Roz Gate issue; this repo CODESPAN")) == 1
    assert got[0].kind == "heading" and got[1].kind == "insertion"


def test_sentence_ends_and_abbreviations():
    got = bodies("Use e.g. this one. Then No. 5 is next! Really? Yes.\n")
    assert [s.text for s in got] == ["Use e.g. this one.", "Then No. 5 is next!", "Really?", "Yes."]


def test_period_inside_code_or_parens_does_not_split():
    got = bodies("Run `a.b. c` now (see 4.5. Then stop) please.\n")
    assert len(got) == 1


def test_wrapped_sentence_counts_once_and_positions_point_at_the_start():
    src = "Intro.\n\nThis sentence wraps\nonto a second line. Next\none.\n"
    got = bodies(src)
    assert [(s.text, s.line, s.col) for s in got] == [
        ("Intro.", 1, 1),
        ("This sentence wraps onto a second line.", 3, 1),
        ("Next one.", 4, 21),
    ]


def test_code_span_closes_at_a_run_of_the_opening_length():
    got = sentences("Use ``foo `;` bar`` now.\n")
    assert [s.flat for s in got] == ["Use CODESPAN now."]
    assert got[0].words == 3
    # an unmatched run is literal text, not a span swallowing the rest of the line
    assert [s.flat for s in sentences("A ``b` c; d.\n")] == ["A ``b` c; d."]


def test_html_comment_inline_is_dropped_from_raw_and_text():
    got = sentences("Run it. <!-- expect: X -->\n")
    assert got[0].raw == "Run it." and got[0].text == "Run it."


def test_plain_text_file_parses_as_paragraphs():
    got = sentences("One. Two.\n\nThree.\n")
    assert [s.text for s in got] == ["One.", "Two.", "Three."]


# --- canonical form (PLAN § 4.5 identity table) ----------------------------------


def test_canonical_rewrap_and_emphasis_are_identity_neutral():
    a = canonical_sentence("Apply `status: ready-for-dev`\n   to the **issue**.")
    b = canonical_sentence("Apply `status: ready-for-dev` to the issue.")
    assert a == b


def test_canonical_preserves_semantic_tokens():
    base = canonical_sentence("Apply `status: ready-for-dev`.")
    assert base != canonical_sentence("Apply `status: ready-for-spec`.")
    assert canonical_sentence("Merge `<feat-branch>` into `<spec-branch>`.") != canonical_sentence(
        "Merge `<qa-branch>` into `<spec-branch>`."
    )
    assert canonical_sentence("Wait 10 s.") != canonical_sentence("Wait 30 s.")
    assert canonical_sentence("You must stop.") != canonical_sentence("You MUST stop.")
    assert canonical_sentence("snake_case_name stays") == "snake_case_name stays"
