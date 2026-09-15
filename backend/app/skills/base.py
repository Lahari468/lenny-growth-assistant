"""
BaseSkill interface.
Every agent capability implements this abstract contract.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.message import Citation

class SkillResult(BaseModel):
    content: str
    intent: str
    citations: List[Citation] = []
    has_artifact: bool = False
    artifact_id: Optional[str] = None
    artifact_title: Optional[str] = None
    artifact_type: Optional[str] = None
    artifact_content: Optional[str] = None
    metadata: Dict[str, Any] = {}

class BaseSkill(ABC):
    @abstractmethod
    async def execute(
        self,
        query: str,
        history: List[Dict[str, str]],
        db: AsyncSession,
        session_id: str,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> SkillResult:
        """Execute the skill capability and return structured output."""
        pass
