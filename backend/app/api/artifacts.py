import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import SessionModel, ArtifactModel, MessageModel
from app.schemas.artifact import ArtifactCreate, ArtifactResponse, ArtifactListResponse
from app.schemas.message import Citation
from app.security.sanitizer import sanitize_html

router = APIRouter(prefix="/sessions/{session_id}/artifacts", tags=["Artifacts"])

def _extract_sources(artifact: ArtifactModel) -> List[Citation]:
    if not artifact.message or not artifact.message.citations_json:
        return []
    try:
        raw_list = json.loads(artifact.message.citations_json)
        return [Citation(**c) for c in raw_list]
    except Exception:
        return []

@router.post("", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
async def create_artifact(
    session_id: str,
    payload: ArtifactCreate,
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(SessionModel, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    sanitized = sanitize_html(payload.content) if payload.type == "html" else payload.content

    artifact = ArtifactModel(
        session_id=session_id,
        message_id=payload.message_id,
        type=payload.type,
        title=payload.title,
        content=sanitized,
        raw_content=payload.content,
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)

    message = await db.get(MessageModel, payload.message_id) if payload.message_id else None
    artifact.message = message

    return ArtifactResponse(
        id=artifact.id,
        session_id=artifact.session_id,
        message_id=artifact.message_id,
        type=artifact.type,
        title=artifact.title,
        content=artifact.content,
        raw_content=artifact.raw_content,
        created_at=artifact.created_at,
        is_sandboxed=True,
        sources=_extract_sources(artifact),
    )

@router.get("", response_model=ArtifactListResponse)
async def list_artifacts(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(SessionModel, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    stmt = (
        select(ArtifactModel)
        .options(selectinload(ArtifactModel.message))
        .where(ArtifactModel.session_id == session_id)
        .order_by(desc(ArtifactModel.created_at))
    )
    artifacts = (await db.execute(stmt)).scalars().all()

    artifact_list = [
        ArtifactResponse(
            id=a.id,
            session_id=a.session_id,
            message_id=a.message_id,
            type=a.type,
            title=a.title,
            content=a.content,
            raw_content=a.raw_content,
            created_at=a.created_at,
            is_sandboxed=True,
            sources=_extract_sources(a),
        )
        for a in artifacts
    ]
    return ArtifactListResponse(artifacts=artifact_list, total=len(artifact_list))

@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    session_id: str,
    artifact_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ArtifactModel)
        .options(selectinload(ArtifactModel.message))
        .where(ArtifactModel.id == artifact_id, ArtifactModel.session_id == session_id)
    )
    artifact = (await db.execute(stmt)).scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail=f"Artifact '{artifact_id}' not found in session '{session_id}'.")

    return ArtifactResponse(
        id=artifact.id,
        session_id=artifact.session_id,
        message_id=artifact.message_id,
        type=artifact.type,
        title=artifact.title,
        content=artifact.content,
        raw_content=artifact.raw_content,
        created_at=artifact.created_at,
        is_sandboxed=True,
        sources=_extract_sources(artifact),
    )

