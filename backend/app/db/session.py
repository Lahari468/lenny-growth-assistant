"""
SQLAlchemy engine and session management.

Exposes:
- `engine`: the shared SQLAlchemy engine.
- `Base`: declarative base for ORM models.
- `get_db`: FastAPI dependency that yields a scoped session per request
  and translates database connection failures into a clean HTTP error
  instead of leaking a raw stack trace.
"""

from collections.abc import Generator

from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# pool_pre_ping avoids handing out dead connections after e.g. a DB restart.
engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Yield a database session, closing it after the request completes."""
    db = SessionLocal()
    try:
        yield db
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable. Check DATABASE_URL and that PostgreSQL is running.",
        ) from exc
    finally:
        db.close()
