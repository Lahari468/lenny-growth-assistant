"""
Grounded answer generation.

Combines the existing Retriever (app.rag.retriever) with any ChatProvider
(app.providers.base) to produce an answer that is strictly grounded in
retrieved transcript chunks, with deterministic, database-backed source
citations.

This module intentionally does not introduce its own retrieval or LLM
logic — it only orchestrates the two existing, already-tested pieces:

    query -> Retriever.retrieve() -> [RetrievedChunk, ...]
          -> build strict system prompt + structured context
          -> ChatProvider.generate()
          -> validate citations against the sources actually supplied
          -> GroundedAnswer

All exceptions raised by Retriever (RetrievalValidationError,
RetrievalError) and by the embedding layer (EmbeddingError) and by the
ChatProvider (ProviderError) are already safe (no secrets, no raw DB
errors) and are allowed to propagate unchanged rather than being
re-wrapped here.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.providers.base import ChatProvider, ProviderError
from app.rag.retriever import RetrievedChunk, Retriever

logger = logging.getLogger("app.rag.answerer")

_CITATION_PATTERN = re.compile(
    r"\[\s*(?P<closing>/?)\s*S\s*(?P<number>\d+)\s*\]", re.IGNORECASE
)

INSUFFICIENT_CONTEXT_MESSAGE = (
    "I couldn't find enough relevant information in the available Lenny "
    "material to answer that."
)

_SYSTEM_PROMPT_TEMPLATE = """You are a research assistant answering questions using ONLY the transcript excerpts from Lenny's Podcast supplied below.

Rules you must follow exactly:
- Answer strictly and only using the information contained in the numbered sources below.
- Do not use outside knowledge, training data, or assumptions of any kind.
- Do not invent facts, statistics, quotations, or sources that are not explicitly present in the context below.
- Every factual claim must be supported by at least one source, cited using its exact bracketed ID (for example [S1] or [S2]).
- Only cite source IDs that appear in the context below. Never invent a source ID that isn't listed.
- Follow-up wording (for example, "the retention point", "the first one", or "tell me more") may refer to a topic explicitly discussed in a source. When a supplied source directly discusses that topic, explain only what that source says and cite it; do not return insufficient context merely because the question is phrased as a follow-up.
- Return the insufficient-context sentence only when none of the supplied sources supports an answer to the topic in the question.
- If the context below does not contain enough information to answer the question, respond with exactly this sentence and nothing else: "{insufficient_context_message}"
- If you are uncertain whether the context fully supports part of an answer, say so explicitly rather than guessing.

Context:
{context_block}
"""


@dataclass(frozen=True)
class AnswerSource:
    """A single source backing a grounded answer. Every field is copied
    directly from a RetrievedChunk (i.e. from the database) — nothing here
    is invented."""

    source_id: str  # deterministic "S1", "S2", ... matching the prompt
    document_id: object
    chunk_id: object
    title: str
    source_url: str | None
    chunk_index: int
    score: float
    source_file: str | None = None
    speakers: list[str] = field(default_factory=list)
    paragraph_start: int | None = None
    paragraph_end: int | None = None


@dataclass(frozen=True)
class GroundedAnswer:
    text: str
    sources: list[AnswerSource]
    provider: str
    model: str
    retrieval_count: int


def _to_answer_source(source_id: str, chunk: RetrievedChunk) -> AnswerSource:
    return AnswerSource(
        source_id=source_id,
        document_id=chunk.document_id,
        chunk_id=chunk.chunk_id,
        title=chunk.title,
        source_url=chunk.source_url,
        chunk_index=chunk.chunk_index,
        score=chunk.score,
        source_file=chunk.source_file,
        speakers=chunk.speakers,
        paragraph_start=chunk.paragraph_start,
        paragraph_end=chunk.paragraph_end,
    )


def _build_context_block(sources: list[AnswerSource], chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for source, chunk in zip(sources, chunks):
        header = f"[{source.source_id}] {source.title}"
        if source.source_url:
            header += f" (source: {source.source_url})"
        blocks.append(f"{header}\n{chunk.content}")
    return "\n\n".join(blocks)


def _sanitize_citations(text: str, valid_source_ids: set[str]) -> tuple[str, list[str]]:
    """Remove any cited source ID that was not actually supplied to the
    model, so the displayed answer never carries an invented citation.
    Returns the sanitized text and the list of invalid IDs found."""
    invalid_ids: list[str] = []

    def _replace(match: re.Match) -> str:
        cited = f"S{match.group('number')}"
        # A leading slash is a malformed closing-style marker (e.g. [/S2]),
        # never a valid citation even if its numeric ID exists.
        if not match.group("closing") and cited in valid_source_ids:
            return f"[{cited}]"
        invalid_ids.append(cited)
        return ""

    sanitized = _CITATION_PATTERN.sub(_replace, text)
    sanitized = re.sub(r"[ \t]{2,}", " ", sanitized).strip()
    return sanitized, invalid_ids


def answer(
    query: str,
    retriever: Retriever,
    chat_provider: ChatProvider,
    db: Session,
    top_k: int = 5,
    similarity_threshold: float | None = None,
    retrieval_query: str | None = None,
) -> GroundedAnswer:
    """Produce a grounded answer to `query` using only retrieved transcript
    context.

    Raises:
        RetrievalValidationError: query is empty/blank, or top_k < 1
            (raised by Retriever before any embedding or DB call).
        EmbeddingError: the embedding backend is unavailable or failed.
        RetrievalError: the retrieval database query itself failed.
        ProviderError: the chat provider is unavailable or failed.
    """
    start = time.monotonic()

    # ``retrieval_query`` may carry non-evidentiary conversation references
    # used only to resolve a follow-up.  The original ``query`` remains the
    # user prompt sent to the answer model; retrieved transcript chunks remain
    # its only factual context.
    chunks = retriever.retrieve(
        retrieval_query or query, db, top_k=top_k, similarity_threshold=similarity_threshold
    )

    if not chunks:
        logger.info(
            "Answer skipped: no retrieved context, LLM not called (retrieval_count=0)"
        )
        return GroundedAnswer(
            text=INSUFFICIENT_CONTEXT_MESSAGE,
            sources=[],
            provider="none",
            model="none",
            retrieval_count=0,
        )

    sources = [_to_answer_source(f"S{i}", chunk) for i, chunk in enumerate(chunks, start=1)]
    context_block = _build_context_block(sources, chunks)
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        insufficient_context_message=INSUFFICIENT_CONTEXT_MESSAGE,
        context_block=context_block,
    )

    try:
        response = chat_provider.generate(system_prompt=system_prompt, user_prompt=query)
    except Exception as exc:
        logger.error(
            "Answer generation failed: provider error (%s) retrieval_count=%d",
            exc.__class__.__name__,
            len(chunks),
        )
        raise

    valid_source_ids = {source.source_id for source in sources}
    sanitized_text, invalid_ids = _sanitize_citations(response.text, valid_source_ids)
    if invalid_ids:
        logger.warning(
            "Answer contained %d invalid citation(s), removed (retrieval_count=%d)",
            len(invalid_ids),
            len(chunks),
        )

    duration = time.monotonic() - start
    logger.info(
        "Answer generated: provider=%s model=%s retrieval_count=%d duration=%.3fs "
        "invalid_citations=%d success=True",
        response.provider,
        response.model,
        len(chunks),
        duration,
        len(invalid_ids),
    )

    return GroundedAnswer(
        text=sanitized_text,
        sources=sources,
        provider=response.provider,
        model=response.model,
        retrieval_count=len(chunks),
    )
