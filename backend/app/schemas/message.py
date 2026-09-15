"""
Pydantic schemas for messages, citations, and conversational turns.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class Citation(BaseModel):
    chunk_id: str
    transcript_id: str
    episode_title: str
    guest: str
    source_url: str
    snippet: str
    similarity_score: float

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000, description="User question or prompt")
    provider: Optional[str] = Field(default=None, description="Optional LLM provider override: 'ollama' or 'anthropic'")
    model: Optional[str] = Field(default=None, description="Optional model override")

class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    intent: Optional[str] = None
    citations: List[Citation] = Field(default_factory=list)
    created_at: datetime
    has_artifact: bool = False
    artifact_id: Optional[str] = None

    class Config:
        from_attributes = True

class MessageListResponse(BaseModel):
    messages: List[MessageResponse]
    total: int
