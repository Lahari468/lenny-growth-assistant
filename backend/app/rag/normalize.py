"""
Transcript text normalization and paragraph splitting.

Two things matter for downstream chunk quality:
1. Consistent whitespace, so chunk sizes are predictable.
2. Splitting on paragraph AND speaker-turn boundaries, since transcripts
   often place each speaker's turn on its own line without a blank line
   in between (e.g. "Lenny: ...\\nJane: ...").
"""

from __future__ import annotations

import re

# Matches a line that starts with a short "Name:" style speaker label,
# e.g. "Lenny:", "Jane Doe:". Used both to split speaker turns into their
# own paragraphs and to extract speaker names for chunk metadata.
SPEAKER_LINE_RE = re.compile(r"^([A-Z][A-Za-z0-9 .'\-]{0,40}):\s+(.*)$")


def normalize_whitespace(text: str) -> str:
    """Normalize line endings, strip trailing whitespace per line, and
    collapse runs of 3+ blank lines down to a single paragraph break."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_paragraphs(text: str) -> list[str]:
    """Split normalized text into paragraph units, treating consecutive
    speaker-labeled lines within a block as separate paragraphs even when
    there's no blank line between them."""
    blocks = re.split(r"\n\s*\n", text)
    paragraphs: list[str] = []

    for block in blocks:
        lines = [line for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        speaker_hits = sum(1 for line in lines if SPEAKER_LINE_RE.match(line))
        if len(lines) > 1 and speaker_hits >= 2:
            # Multiple speaker turns packed into one block: split them out
            # so each turn becomes its own paragraph/chunk unit.
            paragraphs.extend(line.strip() for line in lines)
        else:
            paragraphs.append(" ".join(lines))

    return [p for p in paragraphs if p]
