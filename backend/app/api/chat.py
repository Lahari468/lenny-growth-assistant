"""Grounded chat API."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.providers.base import ChatProvider
from app.providers.factory import build_chat_provider
from app.rag.answerer import answer
from app.rag.embeddings import OllamaEmbeddingProvider
from app.rag.retriever import Retriever
from app.services.ship30 import Ship30Skill

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=4000,
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
    )

    similarity_threshold: Optional[float] = Field(
        default=None,
        ge=-1.0,
        le=1.0,
    )

    provider: Optional[str] = Field(
        default=None,
        description="Chat provider override: ollama or anthropic",
    )


class SourceResponse(BaseModel):
    source_id: str
    document_id: str
    chunk_id: str
    title: str
    source_url: Optional[str]
    chunk_index: int
    score: float
    source_file: Optional[str]
    speakers: list[str]
    paragraph_start: Optional[int]
    paragraph_end: Optional[int]


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]
    provider: str
    model: str
    retrieval_count: int


def _build_retriever() -> Retriever:
    settings = get_settings()

    embedding_provider = OllamaEmbeddingProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_embedding_model,
    )

    return Retriever(
        embedding_provider=embedding_provider,
    )


# IMPORTANT:
# Keep this function with ZERO arguments.
# Existing tests monkey-patch this helper with a zero-argument lambda.
def _build_chat_provider() -> ChatProvider:
    return build_chat_provider()


@router.post(
    "/grounded",
    response_model=ChatResponse,
)
def grounded_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:

    try:
        # Preserve the existing zero-argument helper for the default path.
        # Use the factory directly only when the client explicitly
        # requests a provider override.
        chat_provider = (
            build_chat_provider(request.provider)
            if request.provider
            else _build_chat_provider()
        )

        result = answer(
            query=request.query,
            retriever=_build_retriever(),
            chat_provider=chat_provider,
            db=db,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to generate grounded answer.",
        ) from exc

    return ChatResponse(
        answer=result.text,
        sources=[
            SourceResponse(
                source_id=source.source_id,
                document_id=str(source.document_id),
                chunk_id=str(source.chunk_id),
                title=source.title,
                source_url=source.source_url,
                chunk_index=source.chunk_index,
                score=source.score,
                source_file=source.source_file,
                speakers=source.speakers,
                paragraph_start=source.paragraph_start,
                paragraph_end=source.paragraph_end,
            )
            for source in result.sources
        ],
        provider=result.provider,
        model=result.model,
        retrieval_count=result.retrieval_count,
    )


@router.post("/ship30")
def ship30_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    try:
        retriever = _build_retriever()

        chunks = retriever.retrieve(
            request.query,
            db,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
        )

        if not chunks:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Not enough Lenny transcript evidence "
                    "to create an essay."
                ),
            )

        evidence = "\n\n".join(
            f"[S{i}] {chunk.title}\n{chunk.content}"
            for i, chunk in enumerate(chunks, start=1)
        )

        # Same provider-selection rule:
        # default -> existing testable helper
        # explicit provider -> factory override
        provider = (
            build_chat_provider(request.provider)
            if request.provider
            else _build_chat_provider()
        )

        skill = Ship30Skill()

        essay = skill.generate(
            topic=request.query,
            grounded_answer="",
            evidence=evidence,
            chat_provider=provider,
        )

        return {
            "artifact_type": "markdown",
            "title": request.query,
            "content": essay,
            "provider": (
                provider.provider_name
                if hasattr(provider, "provider_name")
                else request.provider
                or get_settings().chat_provider
            ),
            "model": provider.model,
            "retrieval_count": len(chunks),
            "sources": [
                {
                    "source_id": f"S{i}",
                    "title": chunk.title,
                    "source_url": chunk.source_url,
                    "score": chunk.score,
                }
                for i, chunk in enumerate(chunks, start=1)
            ],
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Unable to generate Ship 30 essay.",
        ) from exc