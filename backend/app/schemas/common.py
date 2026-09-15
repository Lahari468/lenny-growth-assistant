"""
Common schemas for API responses, structured errors, and health checks.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error explanation")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional context or validation details")

class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail

class HealthResponse(BaseModel):
    status: str = Field(..., description="'healthy', 'degraded', or 'unhealthy'")
    database: Dict[str, Any] = Field(..., description="Database connection and stats")
    vector_store: Dict[str, Any] = Field(..., description="Vector store chunks count")
    llm_providers: Dict[str, Any] = Field(..., description="Ollama & Claude availability")
    version: str = "0.1.0"

class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str  # 'ollama' or 'anthropic'
    is_active: bool
    is_available: bool
    description: Optional[str] = None
