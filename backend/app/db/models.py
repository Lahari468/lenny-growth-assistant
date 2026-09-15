"""
SQLAlchemy ORM models for Sessions, Messages, Transcripts, Transcript Chunks, and Artifacts.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Growth Chat")
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    # Relationships
    messages: Mapped[List["MessageModel"]] = relationship("MessageModel", back_populates="session", cascade="all, delete-orphan", order_by="MessageModel.created_at")
    artifacts: Mapped[List["ArtifactModel"]] = relationship("ArtifactModel", back_populates="session", cascade="all, delete-orphan", order_by="ArtifactModel.created_at")

class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 'grounded_qa', 'ship30', 'artifact_generation'
    citations_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON serialized list of Citation dicts
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, nullable=False)

    # Relationships
    session: Mapped["SessionModel"] = relationship("SessionModel", back_populates="messages")
    artifacts: Mapped[List["ArtifactModel"]] = relationship("ArtifactModel", back_populates="message", cascade="all, delete-orphan")

class TranscriptModel(Base):
    __tablename__ = "transcripts"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # Unique slug e.g. 'shreyas-doshi-high-agency'
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    guest: Mapped[str] = mapped_column(String(150), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    published_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, nullable=False)

    # Relationships
    chunks: Mapped[List["TranscriptChunkModel"]] = relationship("TranscriptChunkModel", back_populates="transcript", cascade="all, delete-orphan")

class TranscriptChunkModel(Base):
    __tablename__ = "transcript_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    transcript_id: Mapped[str] = mapped_column(String(100), ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_json: Mapped[str] = mapped_column(Text, nullable=False)  # Stored as JSON string vector for universal compatibility
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, nullable=False)

    # Relationships
    transcript: Mapped["TranscriptModel"] = relationship("TranscriptModel", back_populates="chunks")

    __table_args__ = (
        Index("idx_chunk_transcript_index", "transcript_id", "chunk_index"),
    )

class ArtifactModel(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'markdown', 'html'
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Sanitized content
    raw_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Original output before sanitization
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, nullable=False)

    # Relationships
    session: Mapped["SessionModel"] = relationship("SessionModel", back_populates="artifacts")
    message: Mapped[Optional["MessageModel"]] = relationship("MessageModel", back_populates="artifacts")
