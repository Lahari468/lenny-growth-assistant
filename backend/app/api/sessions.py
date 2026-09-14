"""Persistent session and message API."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.pi import PiBridge, PiError
from app.api.chat import SourceResponse, _build_chat_provider, _build_retriever
from app.core.config import get_settings
from app.db.models import ChatSession, Message
from app.db.session import get_db
from app.providers.factory import build_chat_provider
from app.services.session_chat import (
    PersistenceError,
    SessionNotFoundError,
    create_session,
    get_session,
    list_sessions,
    process_message,
)

logger = logging.getLogger("app.api.sessions")

router = APIRouter(
    prefix="/api/sessions",
    tags=["sessions"],
)


class CreateSessionRequest(BaseModel):
    user_name: str = Field(
        default="Anonymous",
        min_length=1,
        max_length=255,
    )
    title: Optional[str] = Field(
        default=None,
        max_length=255,
    )
    provider: Optional[str] = Field(
        default=None,
        description="Chat provider: ollama or anthropic",
    )


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    provider: Optional[str] = None
    model: Optional[str] = None


class SessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    title: Optional[str]
    provider: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = Field(
        default_factory=list
    )


class SendMessageRequest(BaseModel):
    content: str = Field(
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


class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
    sources: list[SourceResponse]
    provider: str
    model: str
    retrieval_count: int


def _message_response(
    message: Message,
) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        provider=message.provider,
        model=message.model,
    )


def _session_response(
    session: ChatSession,
    include_messages: bool = False,
) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        user_name=(
            session.user.name
            if session.user is not None
            else ""
        ),
        title=session.title,
        provider=session.provider,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=(
            [
                _message_response(message)
                for message in session.messages
            ]
            if include_messages
            else []
        ),
    )


def _build_pi_bridge() -> PiBridge | None:
    settings = get_settings()

    if not settings.pi_enabled:
        return None

    return PiBridge(
        command=settings.pi_command,
        provider=settings.pi_provider,
        model=settings.pi_model,
        timeout_seconds=settings.pi_timeout_seconds,
    )


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_session(
    request: CreateSessionRequest,
    db: Session = Depends(get_db),
) -> SessionResponse:
    try:
        settings = get_settings()

        provider = (
            request.provider.strip().lower()
            if request.provider
            else settings.chat_provider.strip().lower()
        )

        if provider not in {"ollama", "anthropic"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unsupported chat provider '{provider}'. "
                    "Use 'ollama' or 'anthropic'."
                ),
            )

        session = create_session(
            db,
            request.user_name.strip(),
            request.title,
            provider,
        )

        return _session_response(
            get_session(db, session.id)
        )

    except HTTPException:
        raise

    except PersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc


@router.get(
    "",
    response_model=list[SessionResponse],
)
def get_sessions(
    db: Session = Depends(get_db),
) -> list[SessionResponse]:
    try:
        return [
            _session_response(
                get_session(db, item.id)
            )
            for item in list_sessions(db)
        ]

    except PersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
)
def get_session_by_id(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> SessionResponse:
    try:
        return _session_response(
            get_session(db, session_id),
            include_messages=True,
        )

    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        ) from exc

    except PersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc


@router.post(
    "/{session_id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_message(
    session_id: uuid.UUID,
    request: SendMessageRequest,
    db: Session = Depends(get_db),
) -> SendMessageResponse:
    try:
        chat_provider = (
    build_chat_provider(request.provider)
    if request.provider
    else _build_chat_provider()
)
        outcome = process_message(
            db=db,
            session_id=session_id,
            content=request.content,
            retriever=_build_retriever(),
            chat_provider=chat_provider,
            pi_bridge=_build_pi_bridge(),
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
        )

    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        ) from exc

    except PiError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Agent service is unavailable. "
                "Please retry shortly."
            ),
        ) from exc

    except PersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.error(
            "Message processing failed: "
            "session_id=%s error=%s",
            session_id,
            exc.__class__.__name__,
        )

        raise
    result = outcome.grounded_answer

    return SendMessageResponse(
        user_message=_message_response(
            outcome.user_message
        ),
        assistant_message=_message_response(
            outcome.assistant_message
        ),
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