from app.rag.chunker import chunk_transcript


def test_chunk_transcript_packs_paragraphs_within_char_budget():
    paragraphs = ["A" * 500, "B" * 500, "C" * 500]

    chunks = chunk_transcript(paragraphs, max_chars=800, overlap_paragraphs=0)

    assert len(chunks) == 3  # each paragraph alone already exceeds half the budget
    assert chunks[0].content == "A" * 500
    assert chunks[1].content == "B" * 500
    assert chunks[2].content == "C" * 500


def test_chunk_transcript_packs_small_paragraphs_together_up_to_budget():
    paragraphs = ["one", "two", "three", "four"]

    chunks = chunk_transcript(paragraphs, max_chars=20, overlap_paragraphs=0)

    # "one two three" as separate lines joined by "\n\n" -- verify grouping
    # happened (fewer chunks than paragraphs) rather than one-per-paragraph.
    assert len(chunks) < len(paragraphs)


def test_chunk_transcript_applies_overlap_between_consecutive_chunks():
    paragraphs = [f"paragraph-{i} " + "x" * 40 for i in range(6)]

    chunks = chunk_transcript(paragraphs, max_chars=110, overlap_paragraphs=1)

    assert len(chunks) >= 2
    # The last paragraph of chunk N should also appear at the start of
    # chunk N+1's content (the overlap).
    first_chunk_last_line = chunks[0].content.split("\n\n")[-1]
    assert first_chunk_last_line in chunks[1].content


def test_chunk_transcript_assigns_sequential_chunk_index():
    paragraphs = [f"paragraph {i}" for i in range(5)]

    chunks = chunk_transcript(paragraphs, max_chars=15, overlap_paragraphs=0)

    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_chunk_metadata_includes_speakers_and_char_count():
    paragraphs = ["Lenny: Question one.", "Jane: Answer one."]

    chunks = chunk_transcript(paragraphs, max_chars=1000, overlap_paragraphs=0)

    assert len(chunks) == 1
    metadata = chunks[0].metadata
    assert metadata["speakers"] == ["Lenny", "Jane"]
    assert metadata["char_count"] == len(chunks[0].content)
    assert metadata["paragraph_start"] == 0
    assert metadata["paragraph_end"] == 1


def test_chunk_transcript_handles_oversized_single_paragraph_without_splitting():
    huge_paragraph = "word " * 1000  # way over any reasonable max_chars
    paragraphs = ["short intro", huge_paragraph]

    chunks = chunk_transcript(paragraphs, max_chars=200, overlap_paragraphs=0)

    # The oversized paragraph must still appear intact in exactly one chunk.
    assert any(c.content == huge_paragraph for c in chunks)


def test_chunk_transcript_empty_input_returns_no_chunks():
    assert chunk_transcript([]) == []
