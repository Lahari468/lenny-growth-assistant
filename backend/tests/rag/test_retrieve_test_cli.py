"""
Tests for the developer retrieval CLI (app.rag.retrieve_test).

Scope is deliberately narrow: argument parsing, output formatting, and
which exception maps to which exit code / message. The retrieval logic
itself (ordering, thresholds, traceability, etc.) is already covered by
tests/rag/test_retriever.py and is not re-tested here.

None of these tests require a live Ollama server or a live database: the
empty-query case is rejected by Retriever's own input validation before
either is touched, and all other cases substitute a fake Retriever so the
CLI's own logic (argument parsing, formatting, error mapping) can be
tested in isolation.
"""

from __future__ import annotations

import logging

import pytest

from app.rag import retrieve_test as cli
from app.rag.embeddings import EmbeddingError
from app.rag.retriever import RetrievalError, RetrievedChunk


class _DummySession:
    """Stands in for a SQLAlchemy Session without ever connecting."""

    def close(self) -> None:
        pass


class _FakeRetriever:
    """Stands in for app.rag.retriever.Retriever. Instances are callable
    so the same instance can replace the `Retriever` class reference in
    the CLI module (`Retriever(embedding_provider=...)` becomes
    `fake(embedding_provider=...)`, which just returns `fake` itself) --
    that way a test can configure `.result` up front and have every call
    the CLI makes see it.
    """

    def __init__(self) -> None:
        self.embedding_provider = None
        self.received_call: dict | None = None
        self.result: list[RetrievedChunk] | Exception = []

    def __call__(self, embedding_provider):
        self.embedding_provider = embedding_provider
        return self

    def retrieve(self, query, db, top_k=5, similarity_threshold=None):
        self.received_call = {
            "query": query,
            "top_k": top_k,
            "similarity_threshold": similarity_threshold,
        }
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _make_chunk(**overrides) -> RetrievedChunk:
    defaults = dict(
        chunk_id="chunk-1",
        document_id="doc-1",
        chunk_index=2,
        content="Lenny: Welcome. " + ("word " * 60),
        title="How to find product-market fit",
        source_url="https://www.lennysnewsletter.com/p/example",
        source_file="example.md",
        speakers=["Lenny", "Jane"],
        paragraph_start=4,
        paragraph_end=6,
        score=0.8123,
        distance=0.1877,
    )
    defaults.update(overrides)
    return RetrievedChunk(**defaults)


@pytest.fixture(autouse=True)
def _patch_session(monkeypatch):
    # No test here should ever open a real database connection.
    monkeypatch.setattr(cli, "SessionLocal", lambda: _DummySession())


@pytest.fixture()
def fake_retriever(monkeypatch) -> _FakeRetriever:
    fake = _FakeRetriever()
    monkeypatch.setattr(cli, "Retriever", fake)
    return fake


def test_main_rejects_empty_query(caplog):
    """No query argument at all -- rejected by Retriever's own validation
    before touching Ollama or the database. Uses the REAL Retriever."""
    with caplog.at_level(logging.ERROR):
        exit_code = cli.main([])

    assert exit_code == 1
    assert "must not be empty" in caplog.text
    assert "python -m app.rag.retrieve_test" in caplog.text


def test_main_rejects_whitespace_only_query(caplog):
    with caplog.at_level(logging.ERROR):
        exit_code = cli.main(["   "])

    assert exit_code == 1
    assert "must not be empty" in caplog.text


def test_main_joins_multi_word_query_without_quotes(fake_retriever):
    exit_code = cli.main(["how", "do", "I", "find", "product-market", "fit"])

    assert exit_code == 0
    assert fake_retriever.received_call["query"] == "how do I find product-market fit"
    assert fake_retriever.received_call["top_k"] == 5  # default
    assert fake_retriever.received_call["similarity_threshold"] is None  # default


def test_main_forwards_top_k_and_threshold_flags(fake_retriever):
    exit_code = cli.main(["--top-k", "3", "--threshold", "0.5", "growth", "loops"])

    assert exit_code == 0
    assert fake_retriever.received_call["query"] == "growth loops"
    assert fake_retriever.received_call["top_k"] == 3
    assert fake_retriever.received_call["similarity_threshold"] == 0.5


def test_main_prints_no_results_message(fake_retriever, capsys):
    exit_code = cli.main(["nonexistent", "topic"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "No matching results" in out
    assert "nonexistent topic" in out


def test_main_prints_formatted_results_with_traceability(fake_retriever, capsys):
    fake_retriever.result = [_make_chunk()]

    exit_code = cli.main(["find", "pmf"])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "[1]" in out
    assert "score=0.8123" in out
    assert "distance=0.1877" in out
    assert "How to find product-market fit" in out
    assert "https://www.lennysnewsletter.com/p/example" in out
    assert "example.md" in out
    assert "Chunk index: 2" in out
    assert "Lenny, Jane" in out
    assert "4 - 6" in out


def test_main_result_preview_is_truncated_for_long_content(fake_retriever, capsys):
    long_content = "word " * 200
    fake_retriever.result = [_make_chunk(content=long_content)]

    cli.main(["anything"])
    out = capsys.readouterr().out

    assert "..." in out
    preview_line = next(line for line in out.splitlines() if "Preview:" in line)
    assert len(preview_line) < len(long_content)


def test_main_result_omits_optional_fields_when_absent(fake_retriever, capsys):
    fake_retriever.result = [
        _make_chunk(
            source_url=None,
            source_file=None,
            speakers=[],
            paragraph_start=None,
            paragraph_end=None,
        )
    ]

    cli.main(["anything"])
    out = capsys.readouterr().out

    assert "Source URL:  (none)" in out
    assert "Source file: (none)" in out
    assert "Speakers:" not in out
    assert "Paragraphs:" not in out


def test_main_handles_embedding_backend_unavailable(fake_retriever, caplog):
    fake_retriever.result = EmbeddingError(
        "Could not reach Ollama at http://localhost:11434 for embeddings."
    )

    with caplog.at_level(logging.ERROR):
        exit_code = cli.main(["anything"])

    assert exit_code == 1
    assert "Ollama embedding backend unavailable" in caplog.text


def test_main_handles_database_failure_without_leaking_details(fake_retriever, caplog):
    fake_retriever.result = RetrievalError(
        "Database query failed while retrieving chunks. "
        "Check that PostgreSQL is running and migrations are applied."
    )

    with caplog.at_level(logging.ERROR):
        exit_code = cli.main(["anything"])

    assert exit_code == 1
    assert "Database query failed" in caplog.text
    assert "password" not in caplog.text.lower()
    assert "postgresql://" not in caplog.text
