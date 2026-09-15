"""
Chunk retrieval over the pgvector-backed document store.

Flow: query string -> embed (same EmbeddingProvider used for ingestion,
see app.rag.embeddings) -> cosine-distance search against
document_chunks.embedding -> top-k results ordered by relevance, each
carrying full source traceability pulled directly from the database.

This module has no notion of the LLM/agent layer that will eventually
consume it — `Retriever.retrieve()` is a plain, provider/API-independent
function call: (query, db session, top_k, threshold) -> list[RetrievedChunk].
That keeps it trivially callable from a future agent layer, from a FastAPI
route, or from a test, without any web-framework or agent-framework
dependency baked in here.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.rag.embeddings import EmbeddingError, EmbeddingProvider

logger = logging.getLogger("app.rag.retriever")


class RetrievalValidationError(ValueError):
    """Raised for invalid retrieval input, e.g. an empty query."""


class RetrievalError(RuntimeError):
    """Raised when the retrieval query itself fails (database unavailable,
    query error, etc). Deliberately does not include the underlying
    exception's message, since that can contain connection details."""


@dataclass(frozen=True)
class RetrievedChunk:
    """A single retrieved chunk with full source traceability. Every field
    here is read directly from the database — nothing is inferred or
    invented by the retriever."""

    chunk_id: object  # uuid.UUID
    document_id: object  # uuid.UUID
    chunk_index: int
    content: str
    title: str
    source_url: str | None
    source_file: str | None
    speakers: list[str]
    paragraph_start: int | None
    paragraph_end: int | None
    score: float  # cosine similarity, higher = more relevant
    distance: float  # raw pgvector cosine distance, lower = more relevant


class Retriever:
    """Provider/API-independent retrieval service.

    Mirrors the shape of TranscriptIngestionPipeline (app.rag.pipeline):
    constructed once with an EmbeddingProvider, then called per-request
    with an explicit database session.
    """

    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self.embedding_provider = embedding_provider

    def retrieve(
        self,
        query: str,
        db: Session,
        top_k: int = 5,
        similarity_threshold: float | None = None,
    ) -> list[RetrievedChunk]:
        """Return up to `top_k` chunks most relevant to `query`, ordered by
        relevance (most relevant first).

        Raises:
            RetrievalValidationError: query is empty/blank, or top_k < 1.
            EmbeddingError: the embedding backend is unavailable or failed
                (see app.rag.embeddings).
            RetrievalError: the database query itself failed.
        """
        start = time.monotonic()
        query_length = len(query) if query else 0

        if not query or not query.strip():
            logger.warning("Retrieval rejected: empty query")
            raise RetrievalValidationError("Query must not be empty.")
        if top_k < 1:
            logger.warning("Retrieval rejected: top_k=%d must be >= 1", top_k)
            raise RetrievalValidationError("top_k must be at least 1.")

        logger.info(
            "Retrieval request: query_length=%d top_k=%d threshold=%s",
            query_length,
            top_k,
            similarity_threshold,
        )

        try:
            query_embedding = self.embedding_provider.embed(query)
        except EmbeddingError as exc:
            logger.error("Retrieval failed: embedding error (%s)", exc.__class__.__name__)
            raise

        distance_expr = DocumentChunk.embedding.cosine_distance(query_embedding)

        stmt = (
            select(DocumentChunk, Document, distance_expr.label("distance"))
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(DocumentChunk.embedding.isnot(None))
        )
        if similarity_threshold is not None:
            # cosine_distance == 1 - cosine_similarity, so a minimum
            # similarity translates to a maximum allowed distance.
            max_distance = 1 - similarity_threshold
            stmt = stmt.where(distance_expr <= max_distance)

        stmt = stmt.order_by(distance_expr.asc()).limit(top_k)

        try:
            rows = db.execute(stmt).all()
        except SQLAlchemyError as exc:
            logger.error("Retrieval failed: database error (%s)", exc.__class__.__name__)
            raise RetrievalError(
                "Database query failed while retrieving chunks. "
                "Check that PostgreSQL is running and migrations are applied."
            ) from exc

        results = [self._to_retrieved_chunk(chunk, document, distance) for chunk, document, distance in rows]

        duration = time.monotonic() - start
        logger.info(
            "Retrieval complete: results=%d duration=%.3fs",
            len(results),
            duration,
        )
        return results

    @staticmethod
    def _to_retrieved_chunk(chunk: DocumentChunk, document: Document, distance: float) -> RetrievedChunk:
        metadata = chunk.metadata_ or {}
        return RetrievedChunk(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            title=document.title,
            source_url=document.source_url,
            source_file=metadata.get("source_file"),
            speakers=metadata.get("speakers") or [],
            paragraph_start=metadata.get("paragraph_start"),
            paragraph_end=metadata.get("paragraph_end"),
            score=1 - distance,
            distance=distance,
        )
