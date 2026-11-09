"""
Evaluation API endpoints — datasets, cases, runs, comparisons, results download.

Task 3 additions:
  POST /evaluation/datasets/{id}/validate — validate all cases in a dataset
  POST /evaluation/benchmark             — load & run the built-in benchmark dataset
  GET  /evaluation/benchmark/dataset     — load (or return cached) benchmark dataset info
"""
from __future__ import annotations

import csv
import io
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.schemas import (
    DatasetValidationResponse,
    EvaluationComparisonResponse,
    EvaluationDatasetCreate,
    EvaluationDatasetListResponse,
    EvaluationDatasetResponse,
    EvaluationRunCreate,
    EvaluationRunListResponse,
    EvaluationRunResponse,
)
from app.services.evaluation_service import EvaluationNotFoundError, EvaluationService

logger = get_logger(__name__)
router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


# ── Datasets ───────────────────────────────────────────────────────────────────

@router.post(
    "/datasets",
    response_model=EvaluationDatasetResponse,
    status_code=201,
    summary="Create evaluation dataset",
    description=(
        "Create a versioned evaluation dataset (schema_version='2') with named test cases. "
        "Each case specifies assertion_type, optional timeout_ms, and expect_error flag."
    ),
)
async def create_dataset(
    request: EvaluationDatasetCreate,
    db: AsyncSession = Depends(get_db),
) -> EvaluationDatasetResponse:
    svc = EvaluationService(db)
    dataset = await svc.create_dataset(request)
    return EvaluationDatasetResponse.model_validate(dataset)


@router.get(
    "/datasets",
    response_model=EvaluationDatasetListResponse,
    summary="List evaluation datasets",
)
async def list_datasets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> EvaluationDatasetListResponse:
    svc = EvaluationService(db)
    datasets, total = await svc.list_datasets(page=page, page_size=page_size)
    return EvaluationDatasetListResponse(
        items=[EvaluationDatasetResponse.model_validate(d) for d in datasets],
        total=total,
    )


@router.get(
    "/datasets/{dataset_id}",
    response_model=EvaluationDatasetResponse,
    summary="Get dataset detail with cases",
)
async def get_dataset(dataset_id: str, db: AsyncSession = Depends(get_db)) -> EvaluationDatasetResponse:
    svc = EvaluationService(db)
    try:
        dataset = await svc.get_dataset(dataset_id)
    except EvaluationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Dataset '{dataset_id}' not found"},
        )
    return EvaluationDatasetResponse.model_validate(dataset)


@router.post(
    "/datasets/{dataset_id}/validate",
    response_model=DatasetValidationResponse,
    summary="Validate all cases in a dataset",
    description=(
        "Check each case for required fields, valid assertion_type, "
        "schema presence for schema assertions, and timeout range."
    ),
)
async def validate_dataset(
    dataset_id: str, db: AsyncSession = Depends(get_db)
) -> DatasetValidationResponse:
    svc = EvaluationService(db)
    try:
        return await svc.validate_dataset(dataset_id)
    except EvaluationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Dataset '{dataset_id}' not found"},
        )


# ── Runs ───────────────────────────────────────────────────────────────────────

@router.post(
    "/runs",
    response_model=EvaluationRunResponse,
    status_code=201,
    summary="Start evaluation run",
    description=(
        "Run all test cases in a dataset and record pass/fail results. "
        "Aggregate metrics (pass_rate, error_rate, latency percentiles) are computed "
        "and stored on the run object."
    ),
)
async def start_evaluation_run(
    request: EvaluationRunCreate,
    db: AsyncSession = Depends(get_db),
) -> EvaluationRunResponse:
    svc = EvaluationService(db)
    try:
        run = await svc.run_evaluation(request)
    except EvaluationNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)})
    except Exception as exc:
        logger.error("evaluation_run_failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": str(exc)})
    return EvaluationRunResponse.model_validate(run)


@router.get(
    "/runs",
    response_model=EvaluationRunListResponse,
    summary="List evaluation runs",
)
async def list_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> EvaluationRunListResponse:
    svc = EvaluationService(db)
    runs, total = await svc.list_runs(page=page, page_size=page_size)
    return EvaluationRunListResponse(
        items=[EvaluationRunResponse.model_validate(r) for r in runs],
        total=total,
    )


@router.get(
    "/runs/{run_id}",
    response_model=EvaluationRunResponse,
    summary="Get evaluation run detail with results and aggregate metrics",
)
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)) -> EvaluationRunResponse:
    svc = EvaluationService(db)
    try:
        run = await svc.get_run(run_id)
    except EvaluationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Run '{run_id}' not found"},
        )
    return EvaluationRunResponse.model_validate(run)


@router.get(
    "/runs/{run_id}/compare/{other_run_id}",
    response_model=EvaluationComparisonResponse,
    summary="Compare two evaluation runs",
    description=(
        "Detect regressions (pass → fail) and improvements (fail → pass) for shared test cases. "
        "Pass regression_threshold (0–1, default 0.05) to configure how large a pass-rate drop "
        "must be to flag regression_detected=true."
    ),
)
async def compare_runs(
    run_id: str,
    other_run_id: str,
    regression_threshold: float = Query(default=0.05, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
) -> EvaluationComparisonResponse:
    svc = EvaluationService(db)
    try:
        return await svc.compare_runs(run_id, other_run_id, regression_threshold=regression_threshold)
    except EvaluationNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)})


# ── CSV download ───────────────────────────────────────────────────────────────

@router.get(
    "/runs/{run_id}/download",
    summary="Download evaluation results as CSV",
)
async def download_results(run_id: str, db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    svc = EvaluationService(db)
    try:
        run = await svc.get_run(run_id)
    except EvaluationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Run '{run_id}' not found"},
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "case_id", "passed", "assertion_type", "latency_ms",
        "error", "actual_output", "assertions",
    ])
    for result in run.results:
        writer.writerow([
            result.case_id,
            result.passed,
            result.assertions.get("assertion_type", ""),
            result.latency_ms,
            result.error or "",
            json.dumps(result.actual_output or {}),
            json.dumps(result.assertions),
        ])

    # Append aggregate summary as trailing comment-rows
    writer.writerow([])
    writer.writerow(["# SUMMARY"])
    writer.writerow(["# run_id", run.id])
    writer.writerow(["# status", run.status])
    writer.writerow(["# total_cases", run.total_cases])
    writer.writerow(["# passed_cases", run.passed_cases])
    writer.writerow(["# pass_rate", run.pass_rate])
    writer.writerow(["# error_rate", run.error_rate])
    writer.writerow(["# timeout_rate", run.timeout_rate])
    writer.writerow(["# latency_p50_ms", run.latency_p50_ms])
    writer.writerow(["# latency_p95_ms", run.latency_p95_ms])
    writer.writerow(["# latency_p99_ms", run.latency_p99_ms])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=eval_run_{run_id}.csv"},
    )


# ── Benchmark ──────────────────────────────────────────────────────────────────

@router.get(
    "/benchmark/dataset",
    response_model=EvaluationDatasetResponse,
    summary="Load (or retrieve cached) the built-in benchmark dataset",
)
async def get_benchmark_dataset(db: AsyncSession = Depends(get_db)) -> EvaluationDatasetResponse:
    svc = EvaluationService(db)
    try:
        dataset = await svc.load_benchmark_dataset()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": str(exc)})
    return EvaluationDatasetResponse.model_validate(dataset)


@router.post(
    "/benchmark",
    response_model=EvaluationRunResponse,
    status_code=201,
    summary="Run the built-in benchmark dataset",
    description=(
        "Load the bundled benchmark dataset and execute all its cases. "
        "Specify tool_name to select which built-in tool to evaluate (default: 'calculator')."
    ),
)
async def run_benchmark(
    tool_name: str = Query(default="calculator"),
    model_provider: str = Query(default="mock"),
    db: AsyncSession = Depends(get_db),
) -> EvaluationRunResponse:
    svc = EvaluationService(db)
    try:
        dataset = await svc.load_benchmark_dataset()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": str(exc)})

    try:
        run = await svc.run_evaluation(EvaluationRunCreate(
            dataset_id=dataset.id,
            tool_name=tool_name,
            model_provider=model_provider,
        ))
    except Exception as exc:
        logger.error("benchmark_run_failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": str(exc)})

    return EvaluationRunResponse.model_validate(run)
