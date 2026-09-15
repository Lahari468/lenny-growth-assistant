"""
Messages and conversational turn API routes.
"""

import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import SessionModel, MessageModel, ArtifactModel
from app.schemas.message import MessageCreate, MessageResponse, MessageListResponse, Citation
from app.agent.orchestrator import orchestrator

router = APIRouter(prefix="/sessions/{session_id}/messages", tags=["Messages"])

@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    session_id: str,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
):
    if not payload.content or not payload.content.strip():
        raise HTTPException(status_code=400, detail="Message content cannot be empty.")

    session = await db.get(SessionModel, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    try:
        response = await orchestrator.process_message(
            db=db,
            session_id=session_id,
            user_content=payload.content.strip(),
            provider_name=payload.provider,
            model_name=payload.model,
        )
        return response
    except ConnectionError as conn_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(conn_err),
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating the response: {str(e)}",
        )

@router.get("", response_model=MessageListResponse)
async def list_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(SessionModel, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    stmt = (
        select(MessageModel)
        .where(MessageModel.session_id == session_id)
        .order_by(MessageModel.created_at.asc())
    )
    messages = (await db.execute(stmt)).scalars().all()

    response_list = []
    for msg in messages:
        citations = []
        if msg.citations_json:
            try:
                citations_data = json.loads(msg.citations_json)
                citations = [Citation(**c) for c in citations_data]
            except Exception:
                citations = []

        # Check if message has linked artifact
        art_stmt = select(ArtifactModel.id).where(ArtifactModel.message_id == msg.id)
        art_id = (await db.execute(art_stmt)).scalar_one_or_none()

        response_list.append(MessageResponse(
            id=msg.id,
            session_id=msg.session_id,
            role=msg.role,
            content=msg.content,
            intent=msg.intent,
            citations=citations,
            created_at=msg.created_at,
            has_artifact=bool(art_id),
            artifact_id=art_id,
        ))

    return MessageListResponse(messages=response_list, total=len(response_list))
