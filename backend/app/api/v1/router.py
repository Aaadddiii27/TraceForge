"""
API v1 main router — combines all sub-routers.
"""
from __future__ import annotations

from fastapi import APIRouter, Response

from app.api.v1.endpoints import evaluation, health, tasks, tools
from app.observability.metrics import get_metrics_payload

api_router = APIRouter()

# Health & readiness
api_router.include_router(health.router)

# Core domain endpoints
api_router.include_router(tasks.router)
api_router.include_router(tools.router)
api_router.include_router(evaluation.router)


@api_router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Exposes Prometheus-formatted metrics for runtime observability.",
    tags=["Observability"],
)
async def metrics() -> Response:
    content, content_type = get_metrics_payload()
    return Response(content=content, media_type=content_type)
