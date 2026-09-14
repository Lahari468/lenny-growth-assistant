"""
Transcript loading.

Transcript files live under a directory (default: data/transcripts/) as
.txt or .md files. Each file may optionally start with a YAML frontmatter
block delimited by `---` lines, e.g.:

    ---
    title: "Finding product-market fit"
    source_url: "https://www.lennysnewsletter.com/p/example-episode"
    published_at: 2024-01-15
    guest: "Jane Doe"
    episode_number: 42
    ---

    Lenny: Welcome to the show...
    Jane: Thanks for having me...

Recognized keys (case-insensitive, with a couple of aliases) are mapped
onto the file's title / source_url / published_at. Anything else in the
frontmatter (guest, episode_number, tags, etc.) is preserved verbatim as
extra metadata and stored on the Document row for traceability.

Files with no frontmatter at all are still supported: the title falls
back to a human-readable version of the filename, and source_url /
published_at are left unset.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import yaml

SUPPORTED_EXTENSIONS = {".txt", ".md"}
_FRONTMATTER_DELIMITER = "---"

_RECOGNIZED_KEY_ALIASES = {
    "title": "title",
    "source_url": "source_url",
    "url": "source_url",
    "source": "source_url",
    "published_at": "published_at",
    "published": "published_at",
    "published_date": "published_at",
    "date": "published_at",
}


class TranscriptLoadError(RuntimeError):
    """Raised when a transcript file is missing, unreadable, or malformed."""


@dataclass
class RawTranscript:
    source_file: str  # path relative to the transcripts directory (posix style)
    title: str
    source_url: str | None
    published_at: datetime | None
    extra_metadata: dict = field(default_factory=dict)
    body: str = ""


def discover_transcript_files(directory: Path) -> list[Path]:
    """Return all supported transcript files under `directory`, sorted for
    deterministic ingestion order."""
    return sorted(
        p
        for p in directory.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split `text` into (frontmatter_metadata, body). Returns ({}, text)
    unchanged if there is no well-formed frontmatter block."""
    text = text.lstrip("\ufeff")  # tolerate a leading BOM
    lines = text.split("\n")

    if not lines or lines[0].strip() != _FRONTMATTER_DELIMITER:
        return {}, text

    closing_index = None
    for i in range(1, len(lines)):
        if lines[i].strip() == _FRONTMATTER_DELIMITER:
            closing_index = i
            break

    if closing_index is None:
        # Looked like frontmatter but was never closed; treat the whole
        # file as body rather than guessing.
        return {}, text

    frontmatter_text = "\n".join(lines[1:closing_index])
    body = "\n".join(lines[closing_index + 1 :])

    try:
        raw_metadata = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError as exc:
        raise TranscriptLoadError(f"Invalid YAML frontmatter: {exc}") from exc

    if not isinstance(raw_metadata, dict):
        raise TranscriptLoadError(
            "Frontmatter must be a YAML mapping of key: value pairs."
        )

    return raw_metadata, body


def _coerce_published_at(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def load_transcript_file(path: Path, base_dir: Path) -> RawTranscript:
    """Load and parse a single transcript file. Raises TranscriptLoadError
    for anything that makes the file unusable (unreadable, malformed
    frontmatter, empty body)."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise TranscriptLoadError(
            f"Could not read '{path.name}' as UTF-8 text: {exc}"
        ) from exc
    except OSError as exc:
        raise TranscriptLoadError(f"Could not read '{path.name}': {exc}") from exc

    raw_metadata, body = _parse_frontmatter(text)

    known_metadata: dict = {}
    extra_metadata: dict = {}
    for key, value in raw_metadata.items():
        canonical = _RECOGNIZED_KEY_ALIASES.get(str(key).strip().lower())
        if canonical:
            known_metadata[canonical] = value
        else:
            extra_metadata[key] = value

    title = known_metadata.get("title")
    if not title:
        title = path.stem.replace("_", " ").replace("-", " ").strip().title()

    source_url = known_metadata.get("source_url")
    published_at = _coerce_published_at(known_metadata.get("published_at"))

    body = body.strip()
    if not body:
        raise TranscriptLoadError(f"'{path.name}' has no transcript body content.")

    return RawTranscript(
        source_file=path.relative_to(base_dir).as_posix(),
        title=str(title),
        source_url=str(source_url) if source_url else None,
        published_at=published_at,
        extra_metadata=extra_metadata,
        body=body,
    )
