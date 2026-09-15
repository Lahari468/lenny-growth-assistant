"""
Health and diagnostics endpoint.
Reports operational health of the database, vector store, and LLM providers without leaking secrets.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.database import get_db, is_sqlite
from app.retrieval.vector_store import vector_store
from app.providers.factory import provider_factory
from app.schemas.common import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("", response_model=HealthResponse)
async def get_health(db: AsyncSession = Depends(get_db)):
    db_status = "connected"
    db_type = "sqlite" if is_sqlite else "postgresql"
    try:
        await db.execute(text("SELECT 1;"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Check vector store count
    chunk_count = 0
    try:
        chunk_count = await vector_store.get_chunk_count(db)
    except Exception:
        chunk_count = 0

    # Check LLM providers
    ollama_ok = await provider_factory.get_provider("ollama").is_available()
    anthropic_ok = await provider_factory.get_provider("anthropic").is_available()

    overall_status = "healthy"
    if db_status != "connected":
        overall_status = "unhealthy"
    elif not ollama_ok and not anthropic_ok:
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        database={
            "status": db_status,
            "type": db_type,
        },
        vector_store={
            "indexed_chunks": chunk_count,
            "ready": chunk_count > 0,
        },
        llm_providers={
            "active_provider": provider_factory.get_active_provider_name(),
            "ollama_available": ollama_ok,
            "anthropic_available": anthropic_ok,
        },
        version="0.1.0",
    )
