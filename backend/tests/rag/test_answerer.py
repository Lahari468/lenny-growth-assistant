"""
Tests for app.rag.answerer.

Retriever and ChatProvider are both faked here -- these tests exercise
only the answerer's own orchestration logic (prompt construction, source
bookkeeping, citation validation, error propagation, logging safety). The
retrieval and provider logic themselves are already covered by
tests/rag/test_retriever.py and tests/providers/test_ollama_provider.py.
"""

from __future__ import annotations

import logging

import pytest

from app.providers.base import ChatResponse, ProviderError
from app.rag.answerer import INSUFFICIENT_CONTEXT_MESSAGE, answer
from app.rag.retriever import RetrievalError, RetrievalValidationError, RetrievedChunk, Retriever


class _FakeRetriever:
    def __init__(self, chunks=None, error: Exception | None = None):
        self.chunks = chunks or []
        self.error = error
        self.calls: list[dict] = []

    def retrieve(self, query, db, top_k=5, similarity_threshold=None):
        self.calls.append(
            {"query": query, "top_k": top_k, "similarity_threshold": similarity_threshold}
        )
        if self.error is not None:
            raise self.error
        return self.chunks


class _FakeChatProvider:
    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls: list[dict] = []

    def generate(self, system_prompt, user_prompt):
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        if self.error is not None:
            raise self.error
        return self.response


class _NeverCallEmbeddingProvider:
    """Used to prove a code path never reaches the embedding step."""

    def embed(self, text: str) -> list[float]:
        raise AssertionError("embed() should never be called for this test case")


def _make_chunk(**overrides) -> RetrievedChunk:
    defaults = dict(
        chunk_id="chunk-1",
        document_id="doc-1",
        chunk_index=0,
        content="Jane: Product-market fit is when retention holds steady.",
        title="Finding product-market fit",
        source_url="https://www.lennysnewsletter.com/p/example",
        source_file="example.md",
        speakers=["Lenny", "Jane"],
        paragraph_start=0,
        paragraph_end=1,
        score=0.91,
        distance=0.09,
    )
    defaults.update(overrides)
    return RetrievedChunk(**defaults)


def test_answer_with_supported_question_produces_grounded_answer():
    chunk = _make_chunk()
    retriever = _FakeRetriever(chunks=[chunk])
    provider = _FakeChatProvider(
        response=ChatResponse(
            text="Product-market fit means retention holds steady [S1].",
            provider="ollama",
            model="phi3:latest",
        )
    )

    result = answer("what is product-market fit?", retriever, provider, db=object())

    assert result.text == "Product-market fit means retention holds steady [S1]."
    assert result.provider == "ollama"
    assert result.model == "phi3:latest"
    assert result.retrieval_count == 1
    assert len(provider.calls) == 1


def test_answer_preserves_retrieved_source_traceability():
    chunk = _make_chunk(
        chunk_id="chunk-42",
        document_id="doc-7",
        title="Scaling growth teams",
        source_url="https://example.com/ep7",
        chunk_index=3,
        score=0.77,
        source_file="ep7.md",
        speakers=["Guest"],
        paragraph_start=5,
        paragraph_end=9,
    )
    retriever = _FakeRetriever(chunks=[chunk])
    provider = _FakeChatProvider(
        response=ChatResponse(text="Answer [S1].", provider="ollama", model="phi3:latest")
    )

    result = answer("question", retriever, provider, db=object())

    assert len(result.sources) == 1
    source = result.sources[0]
    assert source.document_id == "doc-7"
    assert source.chunk_id == "chunk-42"
    assert source.title == "Scaling growth teams"
    assert source.source_url == "https://example.com/ep7"
    assert source.chunk_index == 3
    assert source.score == 0.77
    assert source.source_file == "ep7.md"
    assert source.speakers == ["Guest"]
    assert source.paragraph_start == 5
    assert source.paragraph_end == 9


def test_source_ids_are_deterministic_and_match_retrieval_order():
    chunks = [_make_chunk(chunk_id=f"chunk-{i}", chunk_index=i) for i in range(3)]
    retriever = _FakeRetriever(chunks=chunks)
    provider = _FakeChatProvider(
        response=ChatResponse(text="Answer [S1][S2][S3].", provider="ollama", model="phi3:latest")
    )

    result = answer("question", retriever, provider, db=object())

    assert [s.source_id for s in result.sources] == ["S1", "S2", "S3"]
    assert [s.chunk_id for s in result.sources] == ["chunk-0", "chunk-1", "chunk-2"]
    # The IDs used in the prompt context must be the same deterministic IDs.
    sent_system_prompt = provider.calls[0]["system_prompt"]
    assert "[S1]" in sent_system_prompt
    assert "[S2]" in sent_system_prompt
    assert "[S3]" in sent_system_prompt


def test_no_retrieval_results_does_not_call_llm():
    retriever = _FakeRetriever(chunks=[])
    provider = _FakeChatProvider(
        response=ChatResponse(text="should never be used", provider="ollama", model="phi3:latest")
    )

    result = answer("obscure question", retriever, provider, db=object())

    assert result.text == INSUFFICIENT_CONTEXT_MESSAGE
    assert result.sources == []
    assert result.provider == "none"
    assert result.model == "none"
    assert result.retrieval_count == 0
    assert provider.calls == []  # LLM never invoked


def test_insufficient_context_from_model_preserves_real_sources():
    """When the retriever DOES find chunks but the model itself judges the
    context insufficient, the real (non-empty) source list is still
    returned -- only the zero-retrieval case forces sources to []."""
    chunk = _make_chunk()
    retriever = _FakeRetriever(chunks=[chunk])
    provider = _FakeChatProvider(
        response=ChatResponse(
            text=INSUFFICIENT_CONTEXT_MESSAGE, provider="ollama", model="phi3:latest"
        )
    )

    result = answer("unrelated question", retriever, provider, db=object())

    assert result.text == INSUFFICIENT_CONTEXT_MESSAGE
    assert result.retrieval_count == 1
    assert len(result.sources) == 1  # real sources preserved, not wiped


def test_invalid_citation_is_removed_and_flagged(caplog):
    chunk = _make_chunk()
    retriever = _FakeRetriever(chunks=[chunk])
    provider = _FakeChatProvider(
        response=ChatResponse(
            text="Growth loops compound over time [S1] and also [S99].",
            provider="ollama",
            model="phi3:latest",
        )
    )

    with caplog.at_level(logging.WARNING):
        result = answer("question", retriever, provider, db=object())

    assert "[S1]" in result.text
    assert "[S99]" not in result.text
    assert "invalid citation" in caplog.text.lower()
    # The real, database-backed source list is untouched by the bad citation.
    assert len(result.sources) == 1
    assert result.sources[0].source_id == "S1"


def test_provider_error_propagates():
    chunk = _make_chunk()
    retriever = _FakeRetriever(chunks=[chunk])
    provider = _FakeChatProvider(error=ProviderError("Could not reach Ollama for chat generation."))

    with pytest.raises(ProviderError):
        answer("question", retriever, provider, db=object())

    assert len(provider.calls) == 1  # the LLM call was actually attempted


def test_retrieval_error_propagates_without_calling_llm():
    retriever = _FakeRetriever(error=RetrievalError("Database query failed while retrieving chunks."))
    provider = _FakeChatProvider(
        response=ChatResponse(text="should never be used", provider="ollama", model="phi3:latest")
    )

    with pytest.raises(RetrievalError):
        answer("question", retriever, provider, db=object())

    assert provider.calls == []  # never reached the LLM step


def test_empty_query_is_rejected_before_touching_embedding_or_llm():
    # Uses the REAL Retriever (not a fake) to prove validation happens
    # before the embedding provider or chat provider are ever touched.
    real_retriever = Retriever(embedding_provider=_NeverCallEmbeddingProvider())
    provider = _FakeChatProvider(
        response=ChatResponse(text="should never be used", provider="ollama", model="phi3:latest")
    )

    with pytest.raises(RetrievalValidationError):
        answer("", real_retriever, provider, db=object())

    assert provider.calls == []


def test_logging_never_includes_query_or_answer_content(caplog):
    secret_query = "SECRET_API_KEY=abcd1234 what is product-market fit?"
    secret_answer_text = "The answer contains SENSITIVE_TRANSCRIPT_DATA [S1]."
    chunk = _make_chunk(content="Also SENSITIVE_TRANSCRIPT_DATA in the chunk body.")
    retriever = _FakeRetriever(chunks=[chunk])
    provider = _FakeChatProvider(
        response=ChatResponse(text=secret_answer_text, provider="ollama", model="phi3:latest")
    )

    with caplog.at_level(logging.INFO):
        result = answer(secret_query, retriever, provider, db=object())

    assert secret_query not in caplog.text
    assert "SENSITIVE_TRANSCRIPT_DATA" not in caplog.text
    assert result.text == secret_answer_text  # sanity: the answer itself is untouched
    # Safe metadata should still be present.
    assert "retrieval_count=1" in caplog.text
    assert "provider=ollama" in caplog.text
    assert "model=phi3:latest" in caplog.text
