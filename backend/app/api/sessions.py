"""
Session management API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.db.database import get_db
from app.db.models import SessionModel, MessageModel
from app.schemas.session import SessionCreate, SessionResponse, SessionListResponse

router = APIRouter(prefix="/sessions", tags=["Sessions"])

@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionCreate, db: AsyncSession = Depends(get_db)):
    title = payload.title or "New Growth Chat"
    session = SessionModel(title=title, user_id=payload.user_id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return SessionResponse(
        id=session.id,
        title=session.title,
        user_id=session.user_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0,
    )

@router.get("", response_model=SessionListResponse)
async def list_sessions(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(SessionModel, func.count(MessageModel.id).label("msg_count"))
        .outerjoin(MessageModel, SessionModel.id == MessageModel.session_id)
        .group_by(SessionModel.id)
        .order_by(desc(SessionModel.updated_at))
    )
    results = (await db.execute(stmt)).all()
    
    session_list = []
    for s, count in results:
        session_list.append(SessionResponse(
            id=s.id,
            title=s.title,
            user_id=s.user_id,
            created_at=s.created_at,
            updated_at=s.updated_at,
            message_count=count,
        ))

    return SessionListResponse(sessions=session_list, total=len(session_list))

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await db.get(SessionModel, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    
    count_stmt = select(func.count(MessageModel.id)).where(MessageModel.session_id == session_id)
    msg_count = (await db.execute(count_stmt)).scalar_one() or 0

    return SessionResponse(
        id=session.id,
        title=session.title,
        user_id=session.user_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=msg_count,
    )

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await db.get(SessionModel, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    await db.delete(session)
    await db.commit()
    return None
