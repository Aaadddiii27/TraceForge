"""
Prometheus metrics collection and export.
"""
from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# Request & Task metrics
REQUESTS_TOTAL = Counter(
    "ai_runtime_requests_total",
    "Total task requests handled by the runtime",
    ["status", "provider"],
)

TASK_DURATION_SECONDS = Histogram(
    "ai_runtime_task_duration_seconds",
    "Task execution duration in seconds",
    ["provider"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

ACTIVE_TASKS = Gauge(
    "ai_runtime_active_tasks",
    "Number of tasks currently in running state",
)

# Tool metrics
TOOL_INVOCATIONS_TOTAL = Counter(
    "ai_runtime_tool_invocations_total",
    "Total invocations per tool",
    ["tool", "status"],
)

TOOL_ERRORS_TOTAL = Counter(
    "ai_runtime_tool_errors_total",
    "Total tool errors encountered",
    ["tool", "error_type"],
)

TOOL_DURATION_SECONDS = Histogram(
    "ai_runtime_tool_duration_seconds",
    "Tool execution duration in seconds",
    ["tool"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Evaluation metrics
EVALUATION_RUNS_TOTAL = Counter(
    "ai_runtime_evaluation_runs_total",
    "Total evaluation runs executed",
    ["tool", "status"],
)

HTTP_REQUESTS_TOTAL = Counter(
    "ai_runtime_http_requests_total",
    "HTTP requests handled by the API",
    ["method", "route", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "ai_runtime_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

EVALUATION_PASS_RATE = Gauge(
    "ai_runtime_evaluation_pass_rate",
    "Pass rate of the most recent evaluation run",
    ["dataset_id", "tool"],
)


def get_metrics_payload() -> tuple[bytes, str]:
    """Return formatted Prometheus metrics and content type."""
    return generate_latest(), CONTENT_TYPE_LATEST
