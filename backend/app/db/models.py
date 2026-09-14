"""
ORM models: relational persistence + pgvector-backed retrieval storage.

Embedding model decision
-------------------------
This project standardizes on a SINGLE embedding model for the entire
application, regardless of which LLM provider (Ollama or Anthropic) is
answering a given chat: **nomic-embed-text (768 dimensions)**, served
locally via Ollama.

Why:
- Anthropic does not offer a first-party embeddings API, so a local model
  is required no matter what — using it everywhere means there is only
  ever one vector space to reason about.
- Keeping embeddings on one fixed local model means switching the *chat*
  provider never requires re-embedding the corpus or maintaining parallel
  provider-specific indexes (this was flagged as a real risk during
  architecture planning: mixing embedding spaces silently degrades
  retrieval instead of failing loudly).
- 768 dimensions is a solid quality/storage/index-cost balance for a
  podcast-transcript corpus of this size.

`EMBEDDING_DIMENSION` below is the single source of truth for this and is
used directly in the `document_chunks.embedding` column definition.
"""

import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# Fixed embedding dimension for nomic-embed-text. Do not change without a
# full re-embedding of the corpus (see module docstring).
EMBEDDING_DIMENSION = 768


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ChatSession(Base):
    """A single independent chat session (table name: sessions)."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ollama", server_default="ollama"
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False, index=True
    )

    session: Mapped["ChatSession"] = relationship(back_populates="messages")

    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'system')", name="ck_messages_role"
        ),
    )


class Document(Base):
    """A source document (e.g. one podcast episode transcript)."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    # Named metadata_ in Python to avoid clashing with SQLAlchemy's
    # reserved Base.metadata attribute; the DB column itself is "metadata".
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
    )

    __table_args__ = (
        # Idempotency: re-ingesting the same source URL must not create a
        # duplicate document. NULLs are not considered equal by Postgres,
        # so documents without a source_url are unaffected.
        UniqueConstraint("source_url", name="uq_documents_source_url"),
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(EMBEDDING_DIMENSION), nullable=True
    )
    # Traces the chunk back to its exact position in the source (e.g.
    # transcript timestamp range, speaker), for grounded citations.
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    document: Mapped["Document"] = relationship(back_populates="chunks")

    __table_args__ = (
        # Idempotency: re-ingesting a document must not duplicate its chunks.
        # This unique index also covers document_id-only lookups (leftmost
        # prefix), so no separate composite index is added.
        UniqueConstraint(
            "document_id", "chunk_index", name="uq_document_chunks_doc_idx"
        ),
    )


__all__ = [
    "Base",
    "User",
    "ChatSession",
    "Message",
    "Document",
    "DocumentChunk",
    "EMBEDDING_DIMENSION",
]
