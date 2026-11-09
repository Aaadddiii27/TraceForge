"""
Task Service — business logic for creating, fetching, and listing tasks.

Handles idempotency checking, initial persistence, and delegates
actual execution to ExecutionEngine.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models import Task
from app.schemas import TaskCreate
from app.services.execution_engine import ExecutionEngine

logger = get_logger(__name__)


class TaskNotFoundError(Exception):
    pass


class TaskService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_and_execute(self, request: TaskCreate) -> Task:
        """
        Create a task record and execute it synchronously.

        Idempotency: if idempotency_key is provided and a task with that key
        already exists, the existing task is returned without re-executing.
        """
        # Check idempotency key
        if request.idempotency_key:
            existing = await self._get_by_idempotency_key(request.idempotency_key)
            if existing:
                logger.info(
                    "task_idempotent_return",
                    idempotency_key=request.idempotency_key,
                    existing_task_id=existing.id,
                )
                return existing

        # Validate provider is registered
        from app.providers import provider_registry
        if not provider_registry.get(request.model_provider):
            from app.providers import ProviderError
            raise ProviderError(
                f"Provider '{request.model_provider}' is not available",
                retriable=False,
            )

        # Validate all tools exist
        from app.tools.base import ToolError, registry
        for tool_name in request.tool_ids:
            if not registry.get(tool_name):
                raise ToolError(f"Tool '{tool_name}' is not registered", retriable=False)

        # Redact input for storage per payload log level
        from app.core.config import PayloadLogLevel
        if settings.payload_log_level == PayloadLogLevel.NONE:
            stored_input = None
        elif settings.payload_log_level == PayloadLogLevel.METADATA_ONLY:
            stored_input = {k: "***REDACTED***" for k in request.input_payload}
        else:
            stored_input = request.input_payload

        # Create task record
        task = Task(
            id=str(uuid.uuid4()),
            request_id=request.request_id,
            idempotency_key=request.idempotency_key,
            status="pending",
            model_provider=request.model_provider,
            tool_ids=request.tool_ids,
            input_payload=stored_input,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)

        logger.info(
            "task_created",
            task_id=task.id,
            tool_ids=task.tool_ids,
            provider=task.model_provider,
        )

        # Execute synchronously (async background would be Task 6)
        # We pass the raw input (not stored/redacted) to the engine
        task.input_payload = request.input_payload
        engine = ExecutionEngine(self.db)
        try:
            from opentelemetry import trace
            tracer = trace.get_tracer("ai-runtime.execution")
            with tracer.start_as_current_span("runtime.execute_task") as span:
                span.set_attribute("runtime.task_id", task.id)
                span.set_attribute("runtime.provider", task.model_provider)
                span.set_attribute("runtime.tool_count", len(task.tool_ids or []))
                task = await engine.run(task)
                span.set_attribute("runtime.execution_status", task.status)
        except ImportError:
            task = await engine.run(task)

        return task

    async def get_by_id(self, task_id: str) -> Task:
        """Fetch a task by ID, raising TaskNotFoundError if absent."""
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task is None:
            raise TaskNotFoundError(f"Task '{task_id}' not found")
        return task

    async def list_tasks(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[Task], int]:
        """List tasks with optional status filter. Returns (items, total)."""
        query = select(Task)
        if status:
            query = query.where(Task.status == status)
        query = query.order_by(Task.created_at.desc())

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Paginate
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        result = await self.db.execute(query)
        tasks = list(result.scalars().all())

        return tasks, total

    async def _get_by_idempotency_key(self, key: str) -> Task | None:
        result = await self.db.execute(
            select(Task).where(Task.idempotency_key == key)
        )
        return result.scalar_one_or_none()
