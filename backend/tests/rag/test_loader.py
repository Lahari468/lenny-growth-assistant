from datetime import datetime
from pathlib import Path

import pytest

from app.rag.loader import (
    TranscriptLoadError,
    discover_transcript_files,
    load_transcript_file,
)


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_discover_transcript_files_only_returns_supported_extensions(tmp_path: Path):
    _write(tmp_path / "episode-one.md", "content")
    _write(tmp_path / "episode-two.txt", "content")
    _write(tmp_path / "notes.pdf", "content")
    _write(tmp_path / "ignore.json", "content")

    found = discover_transcript_files(tmp_path)

    assert [p.name for p in found] == ["episode-one.md", "episode-two.txt"]


def test_load_transcript_with_full_frontmatter(tmp_path: Path):
    file_path = _write(
        tmp_path / "example-episode.md",
        (
            "---\n"
            'title: "Finding product-market fit"\n'
            'source_url: "https://www.lennysnewsletter.com/p/example-episode"\n'
            "published_at: 2024-01-15\n"
            'guest: "Jane Doe"\n'
            "episode_number: 42\n"
            "---\n"
            "\n"
            "Lenny: Welcome to the show.\n"
            "Jane: Thanks for having me.\n"
        ),
    )

    result = load_transcript_file(file_path, base_dir=tmp_path)

    assert result.title == "Finding product-market fit"
    assert result.source_url == "https://www.lennysnewsletter.com/p/example-episode"
    assert result.published_at == datetime(2024, 1, 15)
    assert result.extra_metadata == {"guest": "Jane Doe", "episode_number": 42}
    assert "Lenny: Welcome to the show." in result.body
    assert result.source_file == "example-episode.md"


def test_load_transcript_without_frontmatter_falls_back_to_filename_title(tmp_path: Path):
    file_path = _write(tmp_path / "growth_loops_101.txt", "Just plain transcript text.")

    result = load_transcript_file(file_path, base_dir=tmp_path)

    assert result.title == "Growth Loops 101"
    assert result.source_url is None
    assert result.published_at is None
    assert result.body == "Just plain transcript text."


def test_load_transcript_with_empty_body_raises(tmp_path: Path):
    file_path = _write(
        tmp_path / "empty.md",
        "---\ntitle: Empty episode\n---\n\n   \n",
    )

    with pytest.raises(TranscriptLoadError):
        load_transcript_file(file_path, base_dir=tmp_path)


def test_load_transcript_with_malformed_frontmatter_raises(tmp_path: Path):
    file_path = _write(
        tmp_path / "broken.md",
        "---\ntitle: [unclosed list\n---\nBody text.",
    )

    with pytest.raises(TranscriptLoadError):
        load_transcript_file(file_path, base_dir=tmp_path)
