from unittest.mock import patch

import pytest
from sqlalchemy.exc import OperationalError

from app.db.models import Document, DocumentChunk, EMBEDDING_DIMENSION
from app.rag.embeddings import EmbeddingError
from app.rag.retriever import RetrievalError, RetrievalValidationError, Retriever
from tests.rag.conftest import StaticEmbeddingProvider


def _basis_vector(index: int, value: float = 1.0) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSION
    vector[index] = value
    return vector


def _insert_chunk(db_session, *, title, source_url, chunk_index, content, vector, metadata=None):
    document = (
        db_session.query(Document).filter(Document.title == title).one_or_none()
    )
    if document is None:
        document = Document(title=title, source_url=source_url)
        db_session.add(document)
        db_session.flush()

    chunk = DocumentChunk(
        document_id=document.id,
        chunk_index=chunk_index,
        content=content,
        embedding=vector,
        metadata_=metadata or {},
    )
    db_session.add(chunk)
    db_session.commit()
    return document, chunk


@pytest.fixture()
def three_chunks(db_session):
    """Three chunks with orthogonal basis-vector embeddings, so a query of
    [0.8, 0.2, 0, ...] is unambiguously closest to chunk A, then B, then C."""
    _, chunk_a = _insert_chunk(
        db_session,
        title="Episode A",
        source_url="https://example.com/a",
        chunk_index=0,
        content="Chunk A content about growth loops.",
        vector=_basis_vector(0),
        metadata={
            "source_file": "a.md",
            "speakers": ["Lenny", "Jane"],
            "paragraph_start": 0,
            "paragraph_end": 1,
        },
    )
    _, chunk_b = _insert_chunk(
        db_session,
        title="Episode B",
        source_url="https://example.com/b",
        chunk_index=0,
        content="Chunk B content about pricing.",
        vector=_basis_vector(1),
        metadata={"source_file": "b.md", "speakers": ["Guest"]},
    )
    _, chunk_c = _insert_chunk(
        db_session,
        title="Episode C",
        source_url=None,
        chunk_index=0,
        content="Chunk C content about hiring.",
        vector=_basis_vector(2),
        metadata={},
    )
    return chunk_a, chunk_b, chunk_c


QUERY_VECTOR = [0.0] * EMBEDDING_DIMENSION
QUERY_VECTOR[0] = 0.8
QUERY_VECTOR[1] = 0.2


def test_retrieve_rejects_empty_query(db_session, fake_embedding_provider):
    retriever = Retriever(embedding_provider=fake_embedding_provider)

    with pytest.raises(RetrievalValidationError):
        retriever.retrieve("", db_session)

    with pytest.raises(RetrievalValidationError):
        retriever.retrieve("   ", db_session)

    assert fake_embedding_provider.calls == []  # never even tried to embed


def test_retrieve_rejects_invalid_top_k(db_session, fake_embedding_provider):
    retriever = Retriever(embedding_provider=fake_embedding_provider)

    with pytest.raises(RetrievalValidationError):
        retriever.retrieve("growth loops", db_session, top_k=0)


def test_retrieve_returns_top_k_ordered_by_relevance(db_session, three_chunks):
    chunk_a, chunk_b, _ = three_chunks
    provider = StaticEmbeddingProvider(QUERY_VECTOR)
    retriever = Retriever(embedding_provider=provider)

    results = retriever.retrieve("What are good growth loops?", db_session, top_k=2)

    assert len(results) == 2
    assert results[0].chunk_id == chunk_a.id
    assert results[1].chunk_id == chunk_b.id
    # Ordered by relevance: strictly decreasing score / increasing distance.
    assert results[0].score > results[1].score
    assert results[0].distance < results[1].distance


def test_retrieve_similarity_threshold_filters_low_relevance(db_session, three_chunks):
    chunk_a, _, _ = three_chunks
    provider = StaticEmbeddingProvider(QUERY_VECTOR)
    retriever = Retriever(embedding_provider=provider)

    results = retriever.retrieve(
        "growth loops", db_session, top_k=10, similarity_threshold=0.5
    )

    assert len(results) == 1
    assert results[0].chunk_id == chunk_a.id


def test_retrieve_source_traceability_fields(db_session, three_chunks):
    chunk_a, _, _ = three_chunks
    provider = StaticEmbeddingProvider(QUERY_VECTOR)
    retriever = Retriever(embedding_provider=provider)

    results = retriever.retrieve("growth loops", db_session, top_k=1)

    result = results[0]
    assert result.chunk_id == chunk_a.id
    assert result.document_id == chunk_a.document_id
    assert result.chunk_index == 0
    assert result.content == "Chunk A content about growth loops."
    assert result.title == "Episode A"
    assert result.source_url == "https://example.com/a"
    assert result.source_file == "a.md"
    assert result.speakers == ["Lenny", "Jane"]
    assert result.paragraph_start == 0
    assert result.paragraph_end == 1
    assert isinstance(result.score, float)
    assert isinstance(result.distance, float)


def test_retrieve_traceability_handles_missing_optional_metadata(db_session, three_chunks):
    _, _, chunk_c = three_chunks  # no source_url, no metadata at all

    provider = StaticEmbeddingProvider(_basis_vector(2))
    retriever = Retriever(embedding_provider=provider)

    results = retriever.retrieve("hiring", db_session, top_k=1)

    result = results[0]
    assert result.chunk_id == chunk_c.id
    assert result.source_url is None
    assert result.source_file is None
    assert result.speakers == []
    assert result.paragraph_start is None
    assert result.paragraph_end is None


def test_retrieve_with_no_indexed_documents_returns_empty(db_session, fake_embedding_provider):
    retriever = Retriever(embedding_provider=fake_embedding_provider)

    results = retriever.retrieve("anything at all", db_session)

    assert results == []


def test_retrieve_with_no_matches_above_threshold_returns_empty(db_session, three_chunks):
    provider = StaticEmbeddingProvider(QUERY_VECTOR)
    retriever = Retriever(embedding_provider=provider)

    results = retriever.retrieve(
        "growth loops", db_session, top_k=10, similarity_threshold=0.999
    )

    assert results == []


def test_retrieve_propagates_embedding_failure(db_session):
    class FailingEmbeddingProvider:
        def embed(self, text: str) -> list[float]:
            raise EmbeddingError("simulated embedding backend failure")

        def health_check(self) -> None:
            pass

    retriever = Retriever(embedding_provider=FailingEmbeddingProvider())

    with pytest.raises(EmbeddingError):
        retriever.retrieve("growth loops", db_session)


def test_retrieve_wraps_database_failure_without_leaking_details(db_session, fake_embedding_provider):
    retriever = Retriever(embedding_provider=fake_embedding_provider)

    secret_message = "connection to server failed: password authentication failed for user 'supersecret_pw'"

    def boom(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception(secret_message))

    with patch.object(db_session, "execute", side_effect=boom):
        with pytest.raises(RetrievalError) as exc_info:
            retriever.retrieve("growth loops", db_session)

    assert "supersecret_pw" not in str(exc_info.value)
    assert "password" not in str(exc_info.value)
