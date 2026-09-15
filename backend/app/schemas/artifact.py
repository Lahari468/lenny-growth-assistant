"""
Pydantic schemas for generated artifacts (Markdown / HTML).
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.schemas.message import Citation

class ArtifactCreate(BaseModel):
    session_id: str
    message_id: Optional[str] = None
    type: str = Field(..., pattern="^(markdown|html)$", description="Type: 'markdown' or 'html'")
    title: str = Field(..., max_length=255)
    content: str = Field(..., min_length=1)

class ArtifactResponse(BaseModel):
    id: str
    session_id: str
    message_id: Optional[str] = None
    type: str  # 'markdown' or 'html'
    title: str
    content: str  # Sanitized content
    raw_content: Optional[str] = None
    created_at: datetime
    is_sandboxed: bool = True
    sources: List[Citation] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ArtifactListResponse(BaseModel):
    artifacts: List[ArtifactResponse]
    total: int
