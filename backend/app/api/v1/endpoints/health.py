"""
Health and readiness endpoints.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.redis import ping_redis
from app.schemas import HealthResponse, ReadinessResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness check",
    description="Returns 200 if the application process is alive.",
)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "/health/ready",
    summary="Readiness check",
    description="Returns 200 when all required dependencies are reachable.",
)
async def readiness() -> JSONResponse:
    redis_ok = await ping_redis()

    # Check database — import here to avoid circular import at module load
    db_ok = False
    try:
        from sqlalchemy import text
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False

    ready = db_ok and redis_ok
    response = ReadinessResponse(
        ready=ready,
        database=db_ok,
        redis=redis_ok,
        details={
            "database_url": "configured" if settings.database_url else "missing",
            "redis_url": "configured" if settings.redis_url else "missing",
        },
    )
    status_code = 200 if ready else 503
    return JSONResponse(content=response.model_dump(mode="json"), status_code=status_code)
