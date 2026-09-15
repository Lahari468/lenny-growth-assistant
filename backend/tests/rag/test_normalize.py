from app.rag.normalize import normalize_whitespace, split_paragraphs


def test_normalize_whitespace_collapses_excess_blank_lines_and_trailing_spaces():
    raw = "Line one.   \r\nLine two.\r\n\r\n\r\n\r\nLine three."

    result = normalize_whitespace(raw)

    assert "\r" not in result
    assert "Line one.\nLine two.\n\nLine three." == result


def test_split_paragraphs_on_blank_line_boundaries():
    text = "First paragraph.\n\nSecond paragraph spans\ntwo lines."

    paragraphs = split_paragraphs(text)

    assert paragraphs == ["First paragraph.", "Second paragraph spans two lines."]


def test_split_paragraphs_separates_consecutive_speaker_turns_without_blank_lines():
    text = "Lenny: Welcome to the show.\nJane: Thanks for having me.\nLenny: Let's dive in."

    paragraphs = split_paragraphs(text)

    assert paragraphs == [
        "Lenny: Welcome to the show.",
        "Jane: Thanks for having me.",
        "Lenny: Let's dive in.",
    ]


def test_split_paragraphs_keeps_single_speaker_multiline_block_together():
    # Only one speaker line present in the block, so it should NOT be
    # force-split -- this is a single continuous turn, not multiple turns.
    text = "Lenny: This is a long answer\nthat wraps onto a second line\nwithout another speaker."

    paragraphs = split_paragraphs(text)

    assert len(paragraphs) == 1
    assert paragraphs[0].startswith("Lenny: This is a long answer")


def test_split_paragraphs_ignores_empty_blocks():
    text = "Paragraph one.\n\n\n\nParagraph two."

    paragraphs = split_paragraphs(normalize_whitespace(text))

    assert paragraphs == ["Paragraph one.", "Paragraph two."]
