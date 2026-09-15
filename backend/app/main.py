"""
FastAPI application entry point.
Configures CORS, lifespan initialization, request tracing, and structured error handlers.
"""

import time
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.db.database import init_db
from app.api.health import router as health_router
from app.api.sessions import router as sessions_router
from app.api.messages import router as messages_router
from app.api.artifacts import router as artifacts_router
from app.api.models import router as models_router

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [req_id=%(name)s] %(message)s",
)
logger = logging.getLogger("lenny_growth")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing application lifespan and database schemas...")
    await init_db()
    logger.info("Application startup complete.")
    yield
    logger.info("Application shutdown.")

app = FastAPI(
    title="The Lenny Growth Assistant API",
    description="Conversational AI platform grounded in Lenny's Podcast transcripts with Ship 30 essays and sandboxed artifacts.",
    version="0.1.0",
    lifespan=lifespan,
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID & Timing Middleware
@app.middleware("http")
async def trace_and_log_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.time()
    
    logger.info("[%s] Started %s %s", req_id, request.method, request.url.path)
    
    try:
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = req_id
        logger.info("[%s] Completed %s %s status=%d duration=%.2fms", req_id, request.method, request.url.path, response.status_code, duration_ms)
        return response
    except Exception as exc:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.error("[%s] Unhandled exception on %s %s: %s (duration=%.2fms)", req_id, request.method, request.url.path, exc, duration_ms)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal error occurred. Please check system logs.",
                    "details": {"request_id": req_id}
                }
            }
        )

# Validation Error Handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The request payload failed schema validation.",
                "details": {"errors": exc.errors()}
            }
        }
    )

# Register API Routers
app.include_router(health_router, prefix="/api")
app.include_router(health_router)  # Also expose /health at root for docker checks
app.include_router(sessions_router, prefix="/api")
app.include_router(messages_router, prefix="/api")
app.include_router(artifacts_router, prefix="/api")
app.include_router(models_router, prefix="/api")
