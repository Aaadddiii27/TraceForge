"""
FastAPI application factory and entry point.
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import AsyncSessionLocal, create_all_tables
from app.core.logging import configure_logging, get_logger
from app.core.redis import close_redis
from app.providers import register_providers
from app.observability.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION_SECONDS
from app.observability.tracing import configure_tracing, shutdown_tracing
from app.services.tool_service import ToolService
from app.tools import register_builtin_tools

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle handler."""
    # ─── Startup ─────────────────────────────────────────────────────────────
    configure_logging(log_level=settings.log_level, json_logs=settings.is_production)
    logger.info("app_starting", env=settings.app_env, version=settings.app_version)

    # 1. Register tools in memory
    register_builtin_tools()

    # 2. Register model providers
    register_providers()

    # 3. Create tables in development / test if not using migrations
    try:
        await create_all_tables()
        logger.info("database_tables_verified")
    except Exception as exc:
        logger.warning("database_table_creation_skipped", reason=str(exc))

    # 4. Sync tools to database if DB reachable
    try:
        async with AsyncSessionLocal() as session:
            tool_svc = ToolService(session)
            await tool_svc.sync_registry_to_db()
            logger.info("tool_registry_synced_to_db")
    except Exception as exc:
        logger.warning("tool_registry_db_sync_skipped", reason=str(exc))

    yield

    # ─── Shutdown ────────────────────────────────────────────────────────────
    logger.info("app_shutting_down")
    await close_redis()
    shutdown_tracing(getattr(app.state, "tracer_provider", None))


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Developer-oriented AI Runtime & Evaluation Platform. "
            "Provides reliable task execution, traceable tool orchestration, "
            "repeatable evaluation framework, and performance observability."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.state.tracer_provider = configure_tracing(app)

    # ─── CORS Middleware ───────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── Request Context & Timing Middleware ──────────────────────────────────
    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start_time = time.perf_counter()

        try:
            response: Response = await call_next(request)
            return response
        finally:
            process_time_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            route = getattr(request.scope.get("route"), "path", "unmatched")
            status_code = str(getattr(locals().get("response"), "status_code", 500))
            HTTP_REQUESTS_TOTAL.labels(request.method, route, status_code).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(request.method, route).observe(process_time_ms / 1000.0)
            if "response" in locals():
                response.headers["X-Request-ID"] = req_id
                response.headers["X-Process-Time-Ms"] = str(process_time_ms)

    # ─── Exception Handlers ───────────────────────────────────────────────────
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning("validation_error", errors=exc.errors(), path=request.url.path)
        return JSONResponse(
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            content={
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters or payload",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", error=str(exc), path=request.url.path, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred",
            },
        )

    # ─── Routes ───────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "api": settings.api_prefix,
        }

    return app


app = create_app()
