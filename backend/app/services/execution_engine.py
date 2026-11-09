"""
Execution Engine — orchestrates task execution through the state machine.

Responsibilities:
- Accept a Task ORM object and execute each of its tool_ids in order.
- Record each step as an ExecutionStep row.
- Enforce per-step and per-task timeouts.
- Apply bounded retry logic with backoff.
- Transition Task to completed, failed, or timed_out terminal states.
- Emit structured log events at each transition.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models import ExecutionStep, Task
from app.observability.metrics import (
    ACTIVE_TASKS,
    REQUESTS_TOTAL,
    TASK_DURATION_SECONDS,
    TOOL_DURATION_SECONDS,
    TOOL_ERRORS_TOTAL,
    TOOL_INVOCATIONS_TOTAL,
)
from app.tools.base import ToolError, ToolTimeoutError, registry

logger = get_logger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ExecutionEngine:
    """
    Executes a Task step-by-step, persisting state at each transition.

    Usage:
        engine = ExecutionEngine(db_session)
        await engine.run(task)
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run(self, task: Task) -> Task:
        """
        Run all steps for the given task.

        Mutates task.status and persists ExecutionSteps.
        Returns the updated task.
        """
        logger.info(
            "task_execution_started",
            task_id=task.id,
            tool_ids=task.tool_ids,
            provider=task.model_provider,
        )

        task.status = "running"
        task.started_at = _now()
        await self._save(task)
        ACTIVE_TASKS.inc()

        current_input = task.input_payload or {}
        final_output: dict[str, Any] | None = None

        try:
            for i, tool_name in enumerate(task.tool_ids):
                step_output = await self._run_step(
                    task=task,
                    tool_name=tool_name,
                    step_index=i,
                    input_data=current_input,
                )
                final_output = step_output
                # Chain: output of step N is input of step N+1
                current_input = step_output

            # All steps succeeded
            task.status = "completed"
            task.output_payload = final_output
            task.finished_at = _now()
            await self._save(task)
            logger.info("task_completed", task_id=task.id, duration_ms=task.duration_ms)

        except asyncio.TimeoutError:
            task.status = "timed_out"
            task.finished_at = _now()
            task.error_message = "Task execution timed out"
            await self._save(task)
            logger.warning("task_timed_out", task_id=task.id)

        except ToolError as exc:
            task.status = "failed"
            task.finished_at = _now()
            task.error_message = str(exc)
            await self._save(task)
            logger.warning("task_failed", task_id=task.id, error=str(exc))

        except Exception as exc:
            task.status = "failed"
            task.finished_at = _now()
            task.error_message = f"Unexpected error: {type(exc).__name__}: {exc}"
            await self._save(task)
            logger.error("task_unexpected_error", task_id=task.id, error=str(exc), exc_info=True)

        finally:
            ACTIVE_TASKS.dec()
            REQUESTS_TOTAL.labels(status=task.status, provider=task.model_provider).inc()
            if task.duration_ms is not None:
                TASK_DURATION_SECONDS.labels(provider=task.model_provider).observe(task.duration_ms / 1000.0)

        return task

    async def _run_step(
        self,
        task: Task,
        tool_name: str,
        step_index: int,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute one tool step with retry logic and timeout enforcement.

        Returns the step output on success.
        Raises ToolError (non-retriable) or re-raises after max retries.
        """
        max_attempts = settings.max_retry_attempts
        backoff = settings.retry_backoff_seconds

        # Validate tool exists before starting any attempts
        tool = registry.get_or_raise(tool_name)

        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            step = ExecutionStep(
                id=str(uuid.uuid4()),
                task_id=task.id,
                step_name=f"{tool_name}",
                status="running",
                attempt_number=attempt,
                started_at=_now(),
                input=self._redact_payload(input_data),
            )
            self.db.add(step)
            await self.db.flush()

            try:
                # Enforce per-tool timeout
                output = await asyncio.wait_for(
                    tool.execute(input_data),
                    timeout=tool.timeout_seconds,
                )
                step.status = "completed"
                step.output = self._redact_payload(output)
                step.finished_at = _now()
                await self._save(step)

                TOOL_INVOCATIONS_TOTAL.labels(tool=tool_name, status="completed").inc()
                if step.duration_ms is not None:
                    TOOL_DURATION_SECONDS.labels(tool=tool_name).observe(step.duration_ms / 1000.0)
                logger.info(
                    "step_completed",
                    task_id=task.id,
                    tool=tool_name,
                    attempt=attempt,
                    duration_ms=step.duration_ms,
                )
                return output

            except asyncio.TimeoutError:
                step.status = "timed_out"
                step.error = f"Tool '{tool_name}' timed out after {tool.timeout_seconds}s"
                step.finished_at = _now()
                await self._save(step)
                TOOL_INVOCATIONS_TOTAL.labels(tool=tool_name, status="timed_out").inc()
                TOOL_ERRORS_TOTAL.labels(tool=tool_name, error_type="TimeoutError").inc()
                last_error = ToolTimeoutError()
                logger.warning(
                    "step_timed_out",
                    task_id=task.id,
                    tool=tool_name,
                    attempt=attempt,
                    timeout=tool.timeout_seconds,
                )
                # Timeouts are retriable; apply backoff
                if attempt < max_attempts:
                    await asyncio.sleep(backoff * attempt)
                continue

            except ToolError as exc:
                step.status = "failed"
                step.error = str(exc)
                step.finished_at = _now()
                await self._save(step)
                TOOL_INVOCATIONS_TOTAL.labels(tool=tool_name, status="failed").inc()
                TOOL_ERRORS_TOTAL.labels(tool=tool_name, error_type=exc.__class__.__name__).inc()
                last_error = exc

                if not exc.retriable:
                    # Non-retriable error — fail immediately
                    logger.warning(
                        "step_failed_non_retriable",
                        task_id=task.id,
                        tool=tool_name,
                        error=str(exc),
                    )
                    raise

                logger.warning(
                    "step_failed_retriable",
                    task_id=task.id,
                    tool=tool_name,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=str(exc),
                )
                if attempt < max_attempts:
                    await asyncio.sleep(backoff * attempt)
                continue

            except Exception as exc:
                step.status = "failed"
                step.error = f"{type(exc).__name__}: {exc}"
                step.finished_at = _now()
                await self._save(step)
                logger.error(
                    "step_unexpected_error",
                    task_id=task.id,
                    tool=tool_name,
                    attempt=attempt,
                    error=str(exc),
                    exc_info=True,
                )
                raise ToolError(f"Unexpected error in tool '{tool_name}': {exc}", retriable=False) from exc

        # Exhausted all attempts
        task.retry_count = max_attempts - 1
        await self._save(task)
        raise last_error or ToolError(f"Tool '{tool_name}' failed after {max_attempts} attempts")

    def _redact_payload(self, payload: dict[str, Any] | None) -> dict[str, Any] | None:
        """
        Redact payload based on PAYLOAD_LOG_LEVEL setting.
        - 'none': return None
        - 'metadata_only': return keys only (values replaced)
        - 'full': return as-is
        """
        if payload is None:
            return None

        from app.core.config import PayloadLogLevel
        level = settings.payload_log_level

        if level == PayloadLogLevel.NONE:
            return None
        if level == PayloadLogLevel.METADATA_ONLY:
            return {k: "***REDACTED***" for k in payload}
        # FULL
        return payload

    async def _save(self, obj: Any) -> None:
        """Flush and commit a single ORM object."""
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
