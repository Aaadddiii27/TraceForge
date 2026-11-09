"""
Pydantic schemas for request/response validation.

All schemas use model_config = ConfigDict(from_attributes=True) so they can be
constructed directly from SQLAlchemy ORM instances.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─── Common ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime


class ReadinessResponse(BaseModel):
    ready: bool
    database: bool
    redis: bool
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    pages: int


# ─── Task Schemas ─────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    """Request body for submitting a new task."""
    tool_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of tool names to execute, in order",
        examples=[["calculator"]],
    )
    input_payload: dict[str, Any] = Field(
        ...,
        description="Input data for the first tool",
        examples=[{"expression": "2 + 2"}],
    )
    model_provider: str = Field(
        default="mock",
        description="Model provider to use (mock, openai, gemini)",
        examples=["mock"],
    )
    idempotency_key: str | None = Field(
        default=None,
        max_length=255,
        description="Optional idempotency key. Duplicate submissions return the original task.",
    )
    request_id: str | None = Field(
        default=None,
        max_length=255,
        description="Optional caller-supplied request identifier for correlation",
    )

    @field_validator("tool_ids")
    @classmethod
    def validate_tool_ids(cls, v: list[str]) -> list[str]:
        for tid in v:
            if not tid or len(tid) > 100:
                raise ValueError(f"Invalid tool_id: '{tid}'")
        return v

    @field_validator("model_provider")
    @classmethod
    def validate_model_provider(cls, v: str) -> str:
        allowed = {"mock", "openai", "gemini"}
        if v not in allowed:
            raise ValueError(f"model_provider must be one of {allowed}")
        return v


class ExecutionStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    step_name: str
    status: str
    attempt_number: int
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: float | None
    input: dict[str, Any] | None
    output: dict[str, Any] | None
    error: str | None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    request_id: str | None
    idempotency_key: str | None
    status: str
    model_provider: str
    tool_ids: list[Any]
    input_payload: dict[str, Any] | None
    output_payload: dict[str, Any] | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: float | None
    error_message: str | None
    retry_count: int
    token_usage_input: int | None
    token_usage_output: int | None
    estimated_cost_usd: float | None
    steps: list[ExecutionStepResponse] = Field(default_factory=list)


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ─── Tool Schemas ─────────────────────────────────────────────────────────────

class ToolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    version: str
    enabled: bool
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    permission_level: str
    timeout_seconds: int


class ToolListResponse(BaseModel):
    items: list[ToolResponse]
    total: int


# ─── Evaluation Schemas ───────────────────────────────────────────────────────

class EvaluationCaseCreate(BaseModel):
    name: str | None = Field(default=None, max_length=255, description="Human-readable case name")
    input: dict[str, Any] = Field(..., description="Input to pass to the tool")
    expected_output: dict[str, Any] = Field(..., description="Expected output fields")
    tags: list[str] = Field(default_factory=list)
    assertion_type: str = Field(
        default="exact",
        description=(
            "Assertion strategy: 'exact' (key-by-key equality), "
            "'contains' (subset match), 'schema' (JSON schema validation), "
            "'expect_error' (tool must raise ToolError), "
            "'tool_called' (tool must be invoked without error)"
        ),
    )
    timeout_ms: int | None = Field(
        default=None, ge=1, le=30_000,
        description="Per-case timeout override in milliseconds",
    )
    expect_error: bool = Field(
        default=False,
        description="If True, the case expects the tool to raise a ToolError",
    )

    @field_validator("assertion_type")
    @classmethod
    def validate_assertion_type(cls, v: str) -> str:
        allowed = {"exact", "contains", "schema", "expect_error", "tool_called"}
        if v not in allowed:
            raise ValueError(f"assertion_type must be one of {allowed}")
        return v


class EvaluationCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    name: str | None
    input: dict[str, Any]
    expected_output: dict[str, Any]
    tags: list[Any]
    assertion_type: str
    timeout_ms: int | None
    expect_error: bool
    created_at: datetime


class EvaluationDatasetCreate(BaseModel):
    schema_version: str = Field(
        default="2",
        description="Dataset format version. Use '2' for the versioned format with named cases.",
    )
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    cases: list[EvaluationCaseCreate] = Field(default_factory=list)


class EvaluationDatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    cases: list[EvaluationCaseResponse] = Field(default_factory=list)


class EvaluationDatasetListResponse(BaseModel):
    items: list[EvaluationDatasetResponse]
    total: int


class EvaluationRunCreate(BaseModel):
    dataset_id: str = Field(..., description="Dataset ID to evaluate")
    model_provider: str = Field(default="mock")
    tool_name: str = Field(..., description="Tool to use for evaluation tasks")
    config: dict[str, Any] = Field(default_factory=dict)
    regression_threshold: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum drop in pass-rate vs. a baseline run to flag as regression. "
            "For example 0.05 = 5 percentage-point drop."
        ),
    )

    @field_validator("model_provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        allowed = {"mock", "openai", "gemini"}
        if v not in allowed:
            raise ValueError(f"model_provider must be one of {allowed}")
        return v


class EvaluationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    case_id: str
    actual_output: dict[str, Any] | None
    passed: bool
    assertions: dict[str, Any]
    latency_ms: float | None
    error: str | None


class EvaluationRunMetrics(BaseModel):
    """Aggregate metrics for a completed evaluation run."""
    total_cases: int
    passed_cases: int
    failed_cases: int
    errored_cases: int
    timed_out_cases: int
    pass_rate: float | None
    error_rate: float | None
    timeout_rate: float | None
    latency_p50_ms: float | None
    latency_p95_ms: float | None
    latency_p99_ms: float | None


class EvaluationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    runtime_version: str
    model_provider: str
    status: str
    config: dict[str, Any]
    started_at: datetime | None
    finished_at: datetime | None
    # Aggregate metrics (populated after run completes)
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    errored_cases: int = 0
    timed_out_cases: int = 0
    pass_rate: float | None = None
    error_rate: float | None = None
    timeout_rate: float | None = None
    latency_p50_ms: float | None = None
    latency_p95_ms: float | None = None
    latency_p99_ms: float | None = None
    results: list[EvaluationResultResponse] = Field(default_factory=list)


class EvaluationRunListResponse(BaseModel):
    items: list[EvaluationRunResponse]
    total: int


class EvaluationComparisonResponse(BaseModel):
    run_a_id: str
    run_b_id: str
    run_a_pass_rate: float | None
    run_b_pass_rate: float | None
    delta_pass_rate: float | None
    run_a_avg_latency_ms: float | None
    run_b_avg_latency_ms: float | None
    delta_latency_ms: float | None
    regression_cases: list[str]   # case IDs that regressed (pass → fail)
    improvement_cases: list[str]  # case IDs that improved (fail → pass)
    regression_detected: bool = False
    regression_threshold: float = 0.05


# ── Dataset validation ─────────────────────────────────────────────────────────

class CaseValidationResult(BaseModel):
    case_index: int
    case_name: str | None
    valid: bool
    errors: list[str] = Field(default_factory=list)


class DatasetValidationResponse(BaseModel):
    dataset_id: str
    total_cases: int
    valid_cases: int
    invalid_cases: int
    errors: list[CaseValidationResult] = Field(default_factory=list)
    is_valid: bool

