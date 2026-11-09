"""
Integration tests for TaskService and ExecutionEngine.
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import PayloadLogLevel, settings
from app.models import Task
from app.schemas import TaskCreate
from app.services.task_service import TaskNotFoundError, TaskService


@pytest.mark.asyncio
async def test_successful_multi_step_task(db_session: AsyncSession):
    service = TaskService(db_session)
    request = TaskCreate(
        tool_ids=["calculator", "text_processor"],
        input_payload={"expression": "25 * 4"},
        model_provider="mock",
    )

    task = await service.create_and_execute(request)

    assert task.status == "completed"
    assert task.error_message is None
    assert task.output_payload is not None
    # Output of calculator was {"result": 100, ...} which text_processor received
    assert len(task.steps) == 2
    assert task.steps[0].status == "completed"
    assert task.steps[1].status == "completed"


@pytest.mark.asyncio
async def test_tool_failure_produces_failed_task(db_session: AsyncSession):
    service = TaskService(db_session)
    request = TaskCreate(
        tool_ids=["calculator"],
        input_payload={"expression": "1 / 0"},
        model_provider="mock",
    )

    task = await service.create_and_execute(request)

    assert task.status == "failed"
    assert "Division by zero" in (task.error_message or "")
    assert len(task.steps) == 1
    assert task.steps[0].status == "failed"
    assert "Division by zero" in (task.steps[0].error or "")


@pytest.mark.asyncio
async def test_idempotency_prevents_duplicate_execution(db_session: AsyncSession):
    service = TaskService(db_session)
    idempotency_key = "idemp-test-key-12345"

    request1 = TaskCreate(
        tool_ids=["calculator"],
        input_payload={"expression": "10 + 20"},
        model_provider="mock",
        idempotency_key=idempotency_key,
    )
    task1 = await service.create_and_execute(request1)
    assert task1.status == "completed"

    request2 = TaskCreate(
        tool_ids=["calculator"],
        input_payload={"expression": "999 + 999"},  # different payload
        model_provider="mock",
        idempotency_key=idempotency_key,  # same key
    )
    task2 = await service.create_and_execute(request2)

    # Must return the original task without executing again
    assert task2.id == task1.id
    assert task2.output_payload == task1.output_payload


@pytest.mark.asyncio
async def test_retriable_error_retries_and_exhausts(db_session: AsyncSession):
    service = TaskService(db_session)
    # mock_tool in retriable_error mode
    request = TaskCreate(
        tool_ids=["mock_tool"],
        input_payload={"mode": "retriable_error", "error_message": "Transient network issue"},
        model_provider="mock",
    )

    task = await service.create_and_execute(request)

    assert task.status == "failed"
    # Should have retried up to settings.max_retry_attempts
    assert len(task.steps) == settings.max_retry_attempts
    for step in task.steps:
        assert step.status == "failed"
        assert "Transient network issue" in (step.error or "")


@pytest.mark.asyncio
async def test_non_retriable_error_fails_immediately(db_session: AsyncSession):
    service = TaskService(db_session)
    # calculator division by zero is non-retriable
    request = TaskCreate(
        tool_ids=["calculator"],
        input_payload={"expression": "5 / 0"},
        model_provider="mock",
    )

    task = await service.create_and_execute(request)

    assert task.status == "failed"
    # Non-retriable: must only have 1 step attempt
    assert len(task.steps) == 1


@pytest.mark.asyncio
async def test_payload_redaction_metadata_only(db_session: AsyncSession, monkeypatch):
    monkeypatch.setattr(settings, "payload_log_level", PayloadLogLevel.METADATA_ONLY)
    service = TaskService(db_session)

    request = TaskCreate(
        tool_ids=["calculator"],
        input_payload={"expression": "40 + 2"},
        model_provider="mock",
    )

    task = await service.create_and_execute(request)
    # The step inputs stored in DB must be redacted
    assert task.steps[0].input == {"expression": "***REDACTED***"}
