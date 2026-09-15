"""
Model listing and active provider management routes.
"""

from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.providers.factory import provider_factory
from app.schemas.common import ModelInfo

router = APIRouter(prefix="/models", tags=["Models"])

class SetActiveModelRequest(BaseModel):
    provider: str

@router.get("", response_model=List[ModelInfo])
async def list_models():
    """List all local Ollama and cloud Anthropic models with their availability."""
    return await provider_factory.list_available_models()

@router.post("/active")
async def set_active_provider(payload: SetActiveModelRequest):
    """Switch active LLM provider between 'ollama' and 'anthropic'."""
    try:
        provider_factory.set_active_provider(payload.provider)
        return {"status": "success", "active_provider": provider_factory.get_active_provider_name()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
