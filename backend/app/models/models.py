"""
SQLAlchemy ORM models for all platform entities.

All models use UUID primary keys and include created_at/updated_at timestamps.
Sensitive payload columns are typed as JSON and are subject to the configured
payload-logging policy before being written.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


def _uuid() -> str:
    return str(uuid.uuid4())


# ─── Task ─────────────────────────────────────────────────────────────────────

class Task(Base):
    """
    Top-level unit of work submitted to the execution engine.

    Status lifecycle:
        pending → running → completed | failed | timed_out | cancelled
    """
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid, index=True
    )
    # Caller-supplied human-readable reference (optional, not unique)
    request_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    # Idempotency key: if set, duplicate submissions return the existing task
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    model_provider: Mapped[str] = mapped_column(String(100), nullable=False, default="mock")
    # JSON list of tool names requested for this task
    tool_ids: Mapped[list[Any]] = mapped_column(JSON_TYPE, nullable=False, default=list)
    # Raw input; redacted per PAYLOAD_LOG_LEVEL before storage
    input_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    # Output from last successful step
    output_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Token and cost tracking (populated by provider adapters when available)
    token_usage_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_usage_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    steps: Mapped[list[ExecutionStep]] = relationship(
        "ExecutionStep", back_populates="task", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} status={self.status}>"

    @property
    def duration_ms(self) -> float | None:
        if self.started_at and self.finished_at:
            delta = self.finished_at - self.started_at
            return delta.total_seconds() * 1000
        return None


# ─── ExecutionStep ────────────────────────────────────────────────────────────

class ExecutionStep(Base):
    """
    A single atomic step within a task execution.

    Steps are recorded even for failed or timed-out attempts,
    enabling post-mortem trace inspection.
    """
    __tablename__ = "execution_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Step-level I/O; redacted per PAYLOAD_LOG_LEVEL
    input: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    task: Mapped[Task] = relationship("Task", back_populates="steps")

    def __repr__(self) -> str:
        return f"<ExecutionStep id={self.id} name={self.step_name} status={self.status}>"

    @property
    def duration_ms(self) -> float | None:
        if self.started_at and self.finished_at:
            delta = self.finished_at - self.started_at
            return delta.total_seconds() * 1000
        return None


# ─── ToolRecord ───────────────────────────────────────────────────────────────

class ToolRecord(Base):
    """
    Registry entry for a tool.

    This table acts as an authoritative record of what tools are known to the
    system. The actual implementation lives in app.tools.*.
    """
    __tablename__ = "tools"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    # Permission levels: PUBLIC, AUTHENTICATED, ADMIN
    permission_level: Mapped[str] = mapped_column(String(50), nullable=False, default="PUBLIC")
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<ToolRecord name={self.name} enabled={self.enabled}>"


# ─── Evaluation ───────────────────────────────────────────────────────────────

class EvaluationDataset(Base):
    """Named collection of test cases."""
    __tablename__ = "evaluation_datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    cases: Mapped[list[EvaluationCase]] = relationship(
        "EvaluationCase", back_populates="dataset", cascade="all, delete-orphan", lazy="selectin"
    )
    runs: Mapped[list[EvaluationRun]] = relationship(
        "EvaluationRun", back_populates="dataset", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<EvaluationDataset name={self.name}>"


class EvaluationCase(Base):
    """A single input/expected-output test case within a dataset."""
    __tablename__ = "evaluation_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_datasets.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    # Human-readable case name (v2 versioned format)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    expected_output: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    tags: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False, default=list)
    # Assertion strategy: "exact" | "contains" | "schema" | "expect_error" | "tool_called"
    assertion_type: Mapped[str] = mapped_column(String(50), nullable=False, default="exact")
    # Per-case timeout override in milliseconds (None → use tool default)
    timeout_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # If True, the case expects the tool to raise a ToolError
    expect_error: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    dataset: Mapped[EvaluationDataset] = relationship("EvaluationDataset", back_populates="cases")
    results: Mapped[list[EvaluationResult]] = relationship(
        "EvaluationResult", back_populates="case", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<EvaluationCase id={self.id} name={self.name}>"


class EvaluationRun(Base):
    """One complete execution of all cases in a dataset."""
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_datasets.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    runtime_version: Mapped[str] = mapped_column(String(100), nullable=False, default="0.1.0")
    model_provider: Mapped[str] = mapped_column(String(100), nullable=False, default="mock")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Aggregate metrics (stored after run completes) ──────────────────────
    total_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errored_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    timed_out_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pass_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    timeout_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Latency percentiles across all case executions (milliseconds)
    latency_p50_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_p95_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_p99_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    dataset: Mapped[EvaluationDataset] = relationship("EvaluationDataset", back_populates="runs")
    results: Mapped[list[EvaluationResult]] = relationship(
        "EvaluationResult", back_populates="run", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<EvaluationRun id={self.id} status={self.status}>"


class EvaluationResult(Base):
    """Result of running one test case within one evaluation run."""
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_cases.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    actual_output: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    assertions: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped[EvaluationRun] = relationship("EvaluationRun", back_populates="results")
    case: Mapped[EvaluationCase] = relationship("EvaluationCase", back_populates="results")

    def __repr__(self) -> str:
        return f"<EvaluationResult id={self.id} passed={self.passed}>"
