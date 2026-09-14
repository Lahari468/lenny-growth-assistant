"""
Transcript chunking.

Chunks are built by greedily packing whole paragraphs (see
app.rag.normalize.split_paragraphs) up to a character budget, so we never
cut a sentence or speaker turn in half. When a chunk fills up, the last
`CHUNK_OVERLAP_PARAGRAPHS` paragraphs are carried into the start of the
next chunk, so context isn't lost right at a chunk boundary.

Chunk sizing rationale: ~1200 characters (roughly 200-300 words) is a
practical middle ground for podcast-transcript retrieval — long enough to
carry a coherent point, short enough that a handful of retrieved chunks
still fits comfortably in a prompt alongside the conversation history.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.rag.normalize import SPEAKER_LINE_RE

CHUNK_MAX_CHARS = 1200
CHUNK_OVERLAP_PARAGRAPHS = 1


@dataclass
class Chunk:
    content: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)


def _group_paragraph_indices(
    paragraphs: list[str],
    max_chars: int,
    overlap_paragraphs: int,
) -> list[list[int]]:
    groups: list[list[int]] = []
    current: list[int] = []
    current_len = 0
    i = 0
    n = len(paragraphs)

    while i < n:
        para_len = len(paragraphs[i])

        if current and current_len + para_len > max_chars:
            groups.append(current)
            overlap = current[-overlap_paragraphs:] if overlap_paragraphs > 0 else []
            overlap_len = sum(len(paragraphs[j]) for j in overlap)
            # If the carried-over overlap alone already leaves no room for
            # the next paragraph, drop the overlap instead of retrying with
            # the same (still too-big) group forever.
            if overlap and overlap_len + para_len > max_chars:
                current = []
                current_len = 0
            else:
                current = overlap
                current_len = overlap_len
            continue  # re-evaluate the same paragraph against the fresh group

        current.append(i)
        current_len += para_len
        i += 1

    if current:
        groups.append(current)

    return groups


def chunk_transcript(
    paragraphs: list[str],
    max_chars: int = CHUNK_MAX_CHARS,
    overlap_paragraphs: int = CHUNK_OVERLAP_PARAGRAPHS,
) -> list[Chunk]:
    """Pack paragraphs into overlapping, character-budgeted chunks.

    Note: a single paragraph longer than `max_chars` is kept intact as its
    own (oversized) chunk rather than being split mid-sentence — this
    trade-off favors coherence over strict size limits, and is rare in
    practice for transcript-style text.
    """
    if not paragraphs:
        return []

    groups = _group_paragraph_indices(paragraphs, max_chars, overlap_paragraphs)

    chunks: list[Chunk] = []
    for chunk_index, indices in enumerate(groups):
        texts = [paragraphs[j] for j in indices]
        content = "\n\n".join(texts)

        speakers: list[str] = []
        for text in texts:
            match = SPEAKER_LINE_RE.match(text)
            if match and match.group(1) not in speakers:
                speakers.append(match.group(1))

        metadata = {
            "paragraph_start": indices[0],
            "paragraph_end": indices[-1],
            "speakers": speakers,
            "char_count": len(content),
        }
        chunks.append(Chunk(content=content, chunk_index=chunk_index, metadata=metadata))

    return chunks
