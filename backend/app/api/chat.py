"""Grounded chat API."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.providers.ollama import OllamaChatProvider
from app.rag.answerer import answer
from app.rag.embeddings import OllamaEmbeddingProvider
from app.rag.retriever import Retriever

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=20)
    similarity_threshold: Optional[float] = Field(
        default=None,
        ge=-1.0,
        le=1.0,
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

    return Retriever(embedding_provider=embedding_provider)


def _build_chat_provider() -> OllamaChatProvider:
    settings = get_settings()

    return OllamaChatProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_chat_model,
    )


@router.post("/grounded", response_model=ChatResponse)
def grounded_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    try:
        result = answer(
            query=request.query,
            retriever=_build_retriever(),
            chat_provider=_build_chat_provider(),
            db=db,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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