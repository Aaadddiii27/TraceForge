"""
Task execution API endpoints.
"""
from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.models import ExecutionStep
from app.providers import ProviderError
from app.schemas import ExecutionStepResponse, TaskCreate, TaskListResponse, TaskResponse
from app.services.task_service import TaskNotFoundError, TaskService
from app.tools.base import ToolError

logger = get_logger(__name__)
router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=201,
    summary="Submit a task",
    description=(
        "Submit a task for execution. Specify one or more tool names and input payload. "
        "The task is executed synchronously and the final state is returned."
    ),
)
async def submit_task(
    request: TaskCreate,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    service = TaskService(db)
    try:
        task = await service.create_and_execute(request)
    except ToolError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "TOOL_ERROR", "message": str(exc)},
        )
    except ProviderError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "PROVIDER_ERROR", "message": str(exc)},
        )
    except Exception as exc:
        logger.error("submit_task_unexpected_error", error=str(exc), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"code": "INTERNAL_ERROR", "message": "Task execution failed unexpectedly"},
        )
    return TaskResponse.model_validate(task)


@router.get(
    "",
    response_model=TaskListResponse,
    summary="List tasks",
)
async def list_tasks(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(default=None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
) -> TaskListResponse:
    service = TaskService(db)
    tasks, total = await service.list_tasks(page=page, page_size=page_size, status=status)
    pages = math.ceil(total / page_size) if total > 0 else 0
    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get task detail",
)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    service = TaskService(db)
    try:
        task = await service.get_by_id(task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": f"Task '{task_id}' not found"})
    return TaskResponse.model_validate(task)


@router.get(
    "/{task_id}/steps",
    response_model=list[ExecutionStepResponse],
    summary="Get execution steps",
    description="Retrieve the step-by-step execution trace for a task.",
)
async def get_task_steps(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[ExecutionStepResponse]:
    service = TaskService(db)
    try:
        task = await service.get_by_id(task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": f"Task '{task_id}' not found"})

    return [ExecutionStepResponse.model_validate(step) for step in task.steps]
