"""
Persistence-layer tests.

These tests exercise the ORM models directly against a real PostgreSQL +
pgvector database (see tests/conftest.py). No LLM, embedding model, or
external API is called anywhere in this file.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models import ChatSession, Document, DocumentChunk, Message, User, EMBEDDING_DIMENSION


def _make_user(db_session, name: str = "Test User") -> User:
    user = User(name=name)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_create_session(db_session):
    user = _make_user(db_session)

    session = ChatSession(user_id=user.id, title="Growth strategy chat", provider="ollama")
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    assert session.id is not None
    assert session.user_id == user.id
    assert session.provider == "ollama"
    assert session.created_at is not None
    assert session.updated_at is not None


def test_create_message(db_session):
    user = _make_user(db_session)
    session = ChatSession(user_id=user.id, provider="anthropic")
    db_session.add(session)
    db_session.commit()

    message = Message(session_id=session.id, role="user", content="How do I grow a marketplace?")
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)

    assert message.id is not None
    assert message.role == "user"
    assert message.content == "How do I grow a marketplace?"


def test_session_message_relationship(db_session):
    user = _make_user(db_session)
    session = ChatSession(user_id=user.id)
    db_session.add(session)
    db_session.commit()

    db_session.add_all(
        [
            Message(session_id=session.id, role="user", content="Question one"),
            Message(session_id=session.id, role="assistant", content="Answer one"),
        ]
    )
    db_session.commit()
    db_session.refresh(session)

    assert len(session.messages) == 2
    assert [m.role for m in session.messages] == ["user", "assistant"]
    # Reverse relationship
    assert session.messages[0].session.id == session.id


def test_create_document(db_session):
    document = Document(
        title="How to find product-market fit",
        source_url="https://www.lennysnewsletter.com/p/example-episode",
        metadata_={"guest": "Jane Doe", "episode_number": 42},
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)

    assert document.id is not None
    assert document.source_url.endswith("example-episode")
    assert document.metadata_["episode_number"] == 42


def test_create_document_chunk(db_session):
    document = Document(title="Scaling growth teams")
    db_session.add(document)
    db_session.commit()

    chunk = DocumentChunk(
        document_id=document.id,
        chunk_index=0,
        content="This is the first chunk of the transcript.",
        embedding=[0.1] * EMBEDDING_DIMENSION,
        metadata_={"start_time_s": 0, "end_time_s": 30, "speaker": "Host"},
    )
    db_session.add(chunk)
    db_session.commit()
    db_session.refresh(chunk)

    assert chunk.id is not None
    assert chunk.chunk_index == 0
    assert len(chunk.embedding) == EMBEDDING_DIMENSION
    assert chunk.metadata_["speaker"] == "Host"
    # Traceability back to the source document
    assert chunk.document.title == "Scaling growth teams"


def test_message_requires_existing_session(db_session):
    """Foreign key behavior: a message cannot reference a non-existent session."""
    orphan_message = Message(session_id=uuid.uuid4(), role="user", content="Orphan")
    db_session.add(orphan_message)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_deleting_user_cascades_to_sessions_and_messages(db_session):
    user = _make_user(db_session)
    session = ChatSession(user_id=user.id)
    db_session.add(session)
    db_session.commit()

    message = Message(session_id=session.id, role="user", content="Hello")
    db_session.add(message)
    db_session.commit()

    session_id = session.id
    message_id = message.id

    db_session.delete(user)
    db_session.commit()

    assert db_session.get(ChatSession, session_id) is None
    assert db_session.get(Message, message_id) is None


def test_deleting_document_cascades_to_chunks(db_session):
    document = Document(title="Cascade test document")
    db_session.add(document)
    db_session.commit()

    chunk = DocumentChunk(document_id=document.id, chunk_index=0, content="chunk content")
    db_session.add(chunk)
    db_session.commit()
    chunk_id = chunk.id

    db_session.delete(document)
    db_session.commit()

    assert db_session.get(DocumentChunk, chunk_id) is None


def test_message_role_is_constrained(db_session):
    user = _make_user(db_session)
    session = ChatSession(user_id=user.id)
    db_session.add(session)
    db_session.commit()

    bad_message = Message(session_id=session.id, role="not-a-real-role", content="oops")
    db_session.add(bad_message)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_document_source_url_is_unique_for_idempotent_ingestion(db_session):
    url = "https://www.lennysnewsletter.com/p/duplicate-episode"
    db_session.add(Document(title="First ingestion", source_url=url))
    db_session.commit()

    db_session.add(Document(title="Accidental re-ingestion", source_url=url))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_document_chunk_is_unique_per_document_and_index(db_session):
    document = Document(title="Chunk idempotency test")
    db_session.add(document)
    db_session.commit()

    db_session.add(DocumentChunk(document_id=document.id, chunk_index=0, content="first pass"))
    db_session.commit()

    db_session.add(
        DocumentChunk(document_id=document.id, chunk_index=0, content="re-ingested duplicate")
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
