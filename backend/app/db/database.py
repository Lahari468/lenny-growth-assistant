"""
Database engine and session management.
Supports PostgreSQL with pgvector as primary, with automatic fallback to SQLite.
"""

import os
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import create_engine

logger = logging.getLogger("lenny_growth.db")

class Base(DeclarativeBase):
    pass

from pathlib import Path

# Project root: dhl
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SQLITE_PATH = str(PROJECT_ROOT / "data" / "lenny_growth.db")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/lenny_growth")
FALLBACK_TO_SQLITE = os.getenv("FALLBACK_TO_SQLITE", "true").lower() in ("true", "1", "yes")
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH") or DEFAULT_SQLITE_PATH

# Create data directory if it doesn't exist
os.makedirs(os.path.dirname(SQLITE_DB_PATH) if os.path.dirname(SQLITE_DB_PATH) else "./data", exist_ok=True)


# Engine holders
engine = None
async_session_factory = None
is_sqlite = False

def get_database_url() -> str:
    global is_sqlite
    # If using SQLite explicitly or testing
    if DATABASE_URL.startswith("sqlite"):
        is_sqlite = True
        return DATABASE_URL
    return DATABASE_URL

async def init_db():
    """Initialize database tables. Falls back to SQLite if PostgreSQL is unreachable."""
    global engine, async_session_factory, is_sqlite
    
    url = get_database_url()
    
    if not is_sqlite and "postgresql" in url:
        try:
            logger.info("Attempting connection to PostgreSQL with pgvector at: %s", url.split("@")[-1] if "@" in url else url)
            test_engine = create_async_engine(url, echo=False, pool_pre_ping=True)
            async with test_engine.begin() as conn:
                # Try creating extension if postgres
                try:
                    from sqlalchemy import text
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                except Exception as ext_err:
                    logger.warning("Could not create vector extension (might already exist or permission limited): %s", ext_err)
                await conn.run_sync(Base.metadata.create_all)
            engine = test_engine
            async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
            logger.info("Successfully connected and initialized PostgreSQL schema.")
            return
        except Exception as pg_err:
            logger.warning("PostgreSQL connection failed: %s", pg_err)
            if not FALLBACK_TO_SQLITE:
                raise pg_err
            logger.info("Falling back to local SQLite database: %s", SQLITE_DB_PATH)

    # SQLite fallback
    is_sqlite = True
    sqlite_url = f"sqlite+aiosqlite:///{SQLITE_DB_PATH}"
    logger.info("Initializing SQLite database at: %s", sqlite_url)
    engine = create_async_engine(sqlite_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    logger.info("SQLite database initialized successfully.")

def get_session_factory():
    global async_session_factory
    return async_session_factory

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing an async database session."""
    global async_session_factory
    if async_session_factory is None:
        await init_db()
    assert async_session_factory is not None, "Database session factory could not be initialized"
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

