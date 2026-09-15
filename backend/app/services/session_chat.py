"""Database-backed session and grounded chat orchestration."""

from __future__ import annotations

import logging
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.agents.pi import PiBridge, PiError
from app.db.models import ChatSession, Message, User
from app.rag.answerer import GroundedAnswer, answer

logger = logging.getLogger("app.services.session_chat")


class SessionNotFoundError(LookupError):
    pass


class PersistenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class MessageResult:
    user_message: Message
    assistant_message: Message
    grounded_answer: GroundedAnswer


def create_session(db: Session, user_name: str, title: str | None, provider: str) -> ChatSession:
    try:
        user = User(name=user_name)
        session = ChatSession(user=user, title=title, provider=provider)
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info("Session created: session_id=%s provider=%s", session.id, provider)
        return session
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Session creation failed: error=%s", exc.__class__.__name__)
        raise PersistenceError("Unable to create session.") from exc


def list_sessions(db: Session) -> list[ChatSession]:
    try:
        return list(db.scalars(select(ChatSession).order_by(ChatSession.updated_at.desc())).all())
    except SQLAlchemyError as exc:
        logger.error("Session listing failed: error=%s", exc.__class__.__name__)
        raise PersistenceError("Unable to load sessions.") from exc


def get_session(db: Session, session_id: uuid.UUID) -> ChatSession:
    try:
        session = db.scalar(select(ChatSession).options(selectinload(ChatSession.messages), selectinload(ChatSession.user)).where(ChatSession.id == session_id))
    except SQLAlchemyError as exc:
        logger.error("Session lookup failed: error=%s", exc.__class__.__name__)
        raise PersistenceError("Unable to load session.") from exc
    if session is None:
        raise SessionNotFoundError("Session not found.")
    return session


def _top_k_from_agent_plan(plan_text: str, requested_top_k: int) -> int:
    """Use only a safe, bounded routing choice from Pi's JSON plan.

    Pi never supplies answer text or transcript evidence.  Its sole current
    orchestration capability is selecting the retrieval breadth; malformed or
    unsupported plans retain the caller's validated value.
    """
    try:
        plan = json.loads(plan_text)
    except (TypeError, ValueError):
        logger.warning("Pi plan ignored: malformed JSON")
        return requested_top_k
    if not isinstance(plan, dict) or plan.get("operation") != "grounded_answer":
        logger.warning("Pi plan ignored: unsupported operation")
        return requested_top_k
    candidate = plan.get("top_k")
    if isinstance(candidate, int) and not isinstance(candidate, bool) and 1 <= candidate <= 20:
        return candidate
    return requested_top_k


def _build_retrieval_query(
    current_message: str, current_message_id: uuid.UUID, history: list[Message]
) -> str:
    """Resolve follow-up references without treating history as evidence.

    Conversation turns are supplied solely to the embedding/retrieval query.
    They are never added to the grounded-answer prompt or source list, where
    only retrieved transcript chunks are factual evidence.  A bounded recent
    window covers references such as "the first one" while avoiding an
    unbounded session-sized query.
    """
    prior_turns = [
        message
        for message in history
        if message.id != current_message_id and message.role in {"user", "assistant"}
    ][-6:]
    if not prior_turns:
        return current_message
    references = "\n".join(
        "%s: %s" % (message.role, message.content[:1000])
        for message in prior_turns
    )
    return (
        "Current follow-up question:\n%s\n\n"
        "Conversation references for retrieval intent only; they are not evidence:\n%s"
        % (current_message, references)
    )


def process_message(db: Session, session_id: uuid.UUID, content: str, retriever: object, chat_provider: object, pi_bridge: PiBridge | None = None, top_k: int = 5, similarity_threshold: float | None = None) -> MessageResult:
    start = time.monotonic()
    session = get_session(db, session_id)
    try:
        user_message = Message(session=session, role="user", content=content)
        db.add(user_message)
        session.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user_message)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("User message persistence failed: session_id=%s error=%s", session_id, exc.__class__.__name__)
        raise PersistenceError("Unable to save message.") from exc

    history = list(
        db.scalars(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    retrieval_query = _build_retrieval_query(content, user_message.id, history)
    effective_top_k = top_k
    # Pi is a genuine agent invocation. Its bounded routing output is used to
    # select retrieval breadth, but never becomes transcript knowledge or a
    # user-visible answer.
    if pi_bridge is not None:
        history = history[-10:]
        safe_context = "\n".join("%s: %s" % (item.role, item.content[:500]) for item in history)
        agent_prompt = (
            "Route this conversation to the transcript-grounded answer operation. "
            "Return JSON only, with exactly an operation of 'grounded_answer' and "
            "an integer top_k from 1 to 20. Do not answer the user or add facts. "
            "The final answer will be produced only by a transcript-grounded service.\n"
            + safe_context
        )
        try:
            pi_result = pi_bridge.run(agent_prompt)
            effective_top_k = _top_k_from_agent_plan(pi_result.text, top_k)
            logger.info("Pi plan applied: session_id=%s requested_top_k=%d effective_top_k=%d", session_id, top_k, effective_top_k)
        except PiError as exc:
            # Pi enhances orchestration but must not make the authoritative
            # retrieval-and-grounding path unavailable.
            logger.warning("Pi unavailable; using grounded fallback: session_id=%s error=%s", session_id, exc.__class__.__name__)

    result = answer(query=content, retrieval_query=retrieval_query, retriever=retriever, chat_provider=chat_provider, db=db, top_k=effective_top_k, similarity_threshold=similarity_threshold)
    try:
        assistant_message = Message(session=session, role="assistant", content=result.text, provider=result.provider, model=result.model)
        db.add(assistant_message)
        session.provider = result.provider if result.provider != "none" else session.provider
        session.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(assistant_message)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Assistant message persistence failed: session_id=%s error=%s", session_id, exc.__class__.__name__)
        raise PersistenceError("Unable to save assistant response.") from exc
    logger.info("Message processed: session_id=%s retrieval_count=%d provider=%s model=%s duration=%.3fs", session_id, result.retrieval_count, result.provider, result.model, time.monotonic() - start)
    return MessageResult(user_message=user_message, assistant_message=assistant_message, grounded_answer=result)
