"""
Pydantic schemas for chat sessions.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class SessionCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255, description="Initial session title")
    user_id: Optional[str] = Field(default=None, max_length=100, description="Optional user identifier")

class SessionResponse(BaseModel):
    id: str
    title: str
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True

class SessionListResponse(BaseModel):
    sessions: List[SessionResponse]
    total: int
