"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from app.api.chat import router as chat_router

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.api.health import router as health_router
from app.core.config import get_settings
from app.db.session import engine

logger = logging.getLogger("lenny_growth_assistant")


def _check_database_connection() -> None:
    # Non-fatal: the API should still start (e.g. the health endpoint must
    # work) even if the database isn't reachable yet. We only log a clear
    # warning so misconfiguration is obvious during local dev.
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError:
        logger.warning(
            "Could not connect to the database at startup. "
            "Check DATABASE_URL in your .env file and that PostgreSQL is running."
        )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    _check_database_connection()
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(chat_router)

    return app


app = create_app()
