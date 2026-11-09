"""
Evaluation Service — manages datasets, test cases, evaluation runs, and assertion checks.

Task 3 enhancements:
- AssertionType enum with exact, contains, schema, expect_error, tool_called
- Per-case assertion dispatch that honours case.assertion_type
- Aggregate metrics: pass_rate, error_rate, timeout_rate, latency percentiles (p50/p95/p99)
- Stored aggregate metrics written back to EvaluationRun after each run
- Dataset validation (validate_dataset)
- Built-in benchmark dataset loader (load_benchmark_dataset)
- compare_runs: configurable regression_threshold, regression_detected flag
"""
from __future__ import annotations

import asyncio
import importlib.resources
import json
import math
import re
import statistics
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import get_logger
from app.models import (
    EvaluationCase,
    EvaluationDataset,
    EvaluationResult,
    EvaluationRun,
)
from app.schemas import (
    CaseValidationResult,
    DatasetValidationResponse,
    EvaluationComparisonResponse,
    EvaluationDatasetCreate,
    EvaluationRunCreate,
)
from app.tools.base import ToolError, ToolTimeoutError, registry

logger = get_logger(__name__)

# Path to the bundled benchmark dataset
_BENCHMARK_PATH = Path(__file__).parent.parent.parent / "datasets" / "benchmark.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── AssertionType ─────────────────────────────────────────────────────────────

class AssertionType(str, Enum):
    EXACT = "exact"          # Key-by-key equality (float-tolerant)
    CONTAINS = "contains"    # Actual output must contain all expected keys (subset)
    SCHEMA = "schema"        # Validate actual output against a JSON Schema in expected_output["schema"]
    EXPECT_ERROR = "expect_error"  # Tool must raise ToolError; optional "error_contains" key
    TOOL_CALLED = "tool_called"    # Tool must complete without raising (output shape ignored)


class EvaluationNotFoundError(Exception):
    pass


# ─── Core assertion engine ─────────────────────────────────────────────────────

def evaluate_assertions(
    actual: dict[str, Any] | None,
    expected: dict[str, Any],
    assertion_type: str = AssertionType.EXACT,
    error_msg: str | None = None,
) -> tuple[bool, dict[str, Any]]:
    """
    Evaluate deterministic assertions between actual output and expected spec.

    Supports:
    - exact          Key-by-key equality (strings, numbers, booleans). Floats use
                     math.isclose. Nested dicts are checked recursively. Lists are
                     checked for subset containment.
    - contains       Actual output must contain all keys in expected (values must match).
    - schema         Validate actual output against a JSON Schema stored in expected["schema"].
    - expect_error   The test expects a ToolError. Passes if error_msg is not None.
                     Optional expected["error_contains"] does a substring check.
    - tool_called    The tool must have been called without raising. Passes if actual
                     is not None and error_msg is None.
    """
    atype = AssertionType(assertion_type) if assertion_type in AssertionType._value2member_map_ else AssertionType.EXACT

    # ── expect_error ───────────────────────────────────────────────────────────
    if atype == AssertionType.EXPECT_ERROR:
        if error_msg is None:
            return False, {
                "assertion_type": "expect_error",
                "passed": False,
                "reason": "Expected a ToolError but tool succeeded without error.",
            }
        result: dict[str, Any] = {
            "assertion_type": "expect_error",
            "passed": True,
            "error_received": error_msg,
        }
        # Optional substring check
        error_contains = expected.get("error_contains")
        if error_contains:
            if error_contains.lower() not in error_msg.lower():
                result["passed"] = False
                result["reason"] = (
                    f"Expected error to contain '{error_contains}' but got: {error_msg!r}"
                )
        return result["passed"], result

    # ── tool_called ────────────────────────────────────────────────────────────
    if atype == AssertionType.TOOL_CALLED:
        if error_msg is not None:
            return False, {
                "assertion_type": "tool_called",
                "passed": False,
                "reason": f"Tool raised an error: {error_msg}",
            }
        if actual is None:
            return False, {
                "assertion_type": "tool_called",
                "passed": False,
                "reason": "Tool returned None output.",
            }
        return True, {"assertion_type": "tool_called", "passed": True}

    # All remaining assertion types require actual output (no error)
    if error_msg is not None:
        return False, {
            "assertion_type": assertion_type,
            "passed": False,
            "reason": f"Tool raised unexpected error: {error_msg}",
        }
    if actual is None:
        return False, {
            "assertion_type": assertion_type,
            "passed": False,
            "reason": "Actual output is None",
        }

    # ── schema ─────────────────────────────────────────────────────────────────
    if atype == AssertionType.SCHEMA:
        schema = expected.get("schema")
        if not schema:
            return False, {
                "assertion_type": "schema",
                "passed": False,
                "reason": "No 'schema' key found in expected_output for schema assertion.",
            }
        schema_errors = _validate_json_schema(actual, schema)
        if schema_errors:
            return False, {
                "assertion_type": "schema",
                "passed": False,
                "schema_errors": schema_errors,
            }
        return True, {"assertion_type": "schema", "passed": True}

    # ── exact / contains ───────────────────────────────────────────────────────
    results: dict[str, Any] = {}
    all_passed = True

    for key, exp_val in expected.items():
        if key not in actual:
            results[key] = {
                "passed": False,
                "reason": f"Missing expected key '{key}' in actual output",
                "expected": exp_val,
                "actual": None,
            }
            all_passed = False
            continue

        act_val = actual[key]

        # Regex pattern (backwards compatible)
        if isinstance(exp_val, str) and exp_val.startswith("regex:"):
            pattern = exp_val[6:]
            match = bool(re.search(pattern, str(act_val)))
            results[key] = {"passed": match, "expected": exp_val, "actual": act_val}
            if not match:
                all_passed = False

        # Numeric tolerance comparison
        elif isinstance(exp_val, (int, float)) and isinstance(act_val, (int, float)):
            matches = math.isclose(float(exp_val), float(act_val), rel_tol=1e-5, abs_tol=1e-5)
            results[key] = {"passed": matches, "expected": exp_val, "actual": act_val}
            if not matches:
                all_passed = False

        # List subset containment
        elif isinstance(exp_val, list) and isinstance(act_val, list):
            matches = all(item in act_val for item in exp_val)
            results[key] = {"passed": matches, "expected": exp_val, "actual": act_val}
            if not matches:
                all_passed = False

        # Dict sub-assertions (recursive)
        elif isinstance(exp_val, dict) and isinstance(act_val, dict):
            sub_pass, sub_res = evaluate_assertions(act_val, exp_val, AssertionType.EXACT)
            results[key] = sub_res
            if not sub_pass:
                all_passed = False

        # Exact equality
        else:
            matches = exp_val == act_val
            results[key] = {"passed": matches, "expected": exp_val, "actual": act_val}
            if not matches:
                all_passed = False

    return all_passed, results


def _validate_json_schema(instance: Any, schema: dict[str, Any]) -> list[str]:
    """
    Minimal built-in JSON Schema validator (no external library required).

    Supports: type, required, properties, minimum, maximum, minLength, maxLength,
              pattern, enum, items.
    Returns a list of error strings (empty → valid).
    """
    errors: list[str] = []

    def _check(obj: Any, s: dict[str, Any], path: str) -> None:
        # type
        if "type" in s:
            expected_type = s["type"]
            type_map = {
                "object": dict, "array": list, "string": str,
                "number": (int, float), "integer": int,
                "boolean": bool, "null": type(None),
            }
            py_type = type_map.get(expected_type)
            if py_type and not isinstance(obj, py_type):
                errors.append(f"{path}: expected type '{expected_type}', got {type(obj).__name__!r}")
                return  # Can't go deeper on type mismatch

        # required
        if isinstance(obj, dict) and "required" in s:
            for req_key in s["required"]:
                if req_key not in obj:
                    errors.append(f"{path}: missing required field '{req_key}'")

        # properties
        if isinstance(obj, dict) and "properties" in s:
            for prop, prop_schema in s["properties"].items():
                if prop in obj:
                    _check(obj[prop], prop_schema, f"{path}.{prop}")

        # numeric constraints
        if isinstance(obj, (int, float)):
            if "minimum" in s and obj < s["minimum"]:
                errors.append(f"{path}: {obj} < minimum {s['minimum']}")
            if "maximum" in s and obj > s["maximum"]:
                errors.append(f"{path}: {obj} > maximum {s['maximum']}")

        # string constraints
        if isinstance(obj, str):
            if "minLength" in s and len(obj) < s["minLength"]:
                errors.append(f"{path}: string length {len(obj)} < minLength {s['minLength']}")
            if "maxLength" in s and len(obj) > s["maxLength"]:
                errors.append(f"{path}: string length {len(obj)} > maxLength {s['maxLength']}")
            if "pattern" in s and not re.search(s["pattern"], obj):
                errors.append(f"{path}: string does not match pattern '{s['pattern']}'")

        # enum
        if "enum" in s and obj not in s["enum"]:
            errors.append(f"{path}: value {obj!r} not in enum {s['enum']}")

        # items (array)
        if isinstance(obj, list) and "items" in s:
            for idx, item in enumerate(obj):
                _check(item, s["items"], f"{path}[{idx}]")

    _check(instance, schema, "$")
    return errors


# ─── Metrics computation ────────────────────────────────────────────────────────

def _compute_percentile(values: list[float], p: int) -> float | None:
    """Return the p-th percentile (0–100) using linear interpolation, or None if empty."""
    if not values:
        return None
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    # Use statistics.quantiles for n >= 2
    # statistics.quantiles returns n-1 cut points for n intervals
    # For p50 use quantiles(data, n=100)[49] when len >= 2
    # Simpler: use direct linear interpolation
    idx = (p / 100) * (n - 1)
    lo = int(idx)
    hi = lo + 1
    if hi >= n:
        return sorted_vals[-1]
    frac = idx - lo
    return sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])


def _aggregate_metrics(results: list[EvaluationResult]) -> dict[str, Any]:
    """Compute aggregate metrics from a list of EvaluationResult ORM objects."""
    total = len(results)
    if total == 0:
        return {
            "total_cases": 0,
            "passed_cases": 0,
            "failed_cases": 0,
            "errored_cases": 0,
            "timed_out_cases": 0,
            "pass_rate": None,
            "error_rate": None,
            "timeout_rate": None,
            "latency_p50_ms": None,
            "latency_p95_ms": None,
            "latency_p99_ms": None,
        }

    passed = sum(1 for r in results if r.passed)
    errored = sum(1 for r in results if r.error and not r.passed)
    timed_out = sum(1 for r in results if r.error and "timeout" in (r.error or "").lower())
    failed = total - passed  # includes errored and timed-out

    latencies = [r.latency_ms for r in results if r.latency_ms is not None]

    return {
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": failed,
        "errored_cases": errored,
        "timed_out_cases": timed_out,
        "pass_rate": round(passed / total, 6),
        "error_rate": round(errored / total, 6),
        "timeout_rate": round(timed_out / total, 6),
        "latency_p50_ms": round(_compute_percentile(latencies, 50), 3) if latencies else None,
        "latency_p95_ms": round(_compute_percentile(latencies, 95), 3) if latencies else None,
        "latency_p99_ms": round(_compute_percentile(latencies, 99), 3) if latencies else None,
    }


# ─── Dataset validation ─────────────────────────────────────────────────────────

def _validate_case(case: EvaluationCase, index: int) -> CaseValidationResult:
    """Validate a single EvaluationCase and return a structured result."""
    errors: list[str] = []

    if not case.input:
        errors.append("'input' must be a non-empty dict")

    if not isinstance(case.expected_output, dict):
        errors.append("'expected_output' must be a dict")

    atype = case.assertion_type
    valid_types = {t.value for t in AssertionType}
    if atype not in valid_types:
        errors.append(f"'assertion_type' must be one of {sorted(valid_types)}, got {atype!r}")

    if atype == AssertionType.SCHEMA and "schema" not in case.expected_output:
        errors.append("assertion_type='schema' requires 'schema' key in expected_output")

    if case.timeout_ms is not None and not (1 <= case.timeout_ms <= 30_000):
        errors.append(f"'timeout_ms' must be between 1 and 30000, got {case.timeout_ms}")

    return CaseValidationResult(
        case_index=index,
        case_name=case.name,
        valid=len(errors) == 0,
        errors=errors,
    )


# ─── EvaluationService ──────────────────────────────────────────────────────────

class EvaluationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Dataset CRUD ───────────────────────────────────────────────────────────

    async def create_dataset(self, request: EvaluationDatasetCreate) -> EvaluationDataset:
        dataset_id = str(uuid.uuid4())
        dataset = EvaluationDataset(
            id=dataset_id,
            name=request.name,
            description=request.description,
        )
        self.db.add(dataset)

        for case_data in request.cases:
            case = EvaluationCase(
                id=str(uuid.uuid4()),
                dataset_id=dataset_id,
                name=case_data.name,
                input=case_data.input,
                expected_output=case_data.expected_output,
                tags=case_data.tags,
                assertion_type=case_data.assertion_type,
                timeout_ms=case_data.timeout_ms,
                expect_error=case_data.expect_error,
            )
            self.db.add(case)

        await self.db.commit()
        return await self.get_dataset(dataset_id)

    async def list_datasets(self, page: int = 1, page_size: int = 20) -> tuple[list[EvaluationDataset], int]:
        count_stmt = select(func.count(EvaluationDataset.id))
        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one()

        offset = (page - 1) * page_size
        stmt = (
            select(EvaluationDataset)
            .options(selectinload(EvaluationDataset.cases))
            .order_by(EvaluationDataset.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        res = await self.db.execute(stmt)
        datasets = list(res.scalars().all())
        return datasets, total

    async def get_dataset(self, dataset_id: str) -> EvaluationDataset:
        stmt = (
            select(EvaluationDataset)
            .options(selectinload(EvaluationDataset.cases))
            .where(EvaluationDataset.id == dataset_id)
        )
        res = await self.db.execute(stmt)
        dataset = res.scalar_one_or_none()
        if not dataset:
            raise EvaluationNotFoundError(f"Dataset '{dataset_id}' not found")
        return dataset

    async def validate_dataset(self, dataset_id: str) -> DatasetValidationResponse:
        """Validate every case in a dataset and return structured per-case results."""
        dataset = await self.get_dataset(dataset_id)
        case_results = [_validate_case(case, idx) for idx, case in enumerate(dataset.cases)]
        valid_count = sum(1 for r in case_results if r.valid)
        invalid_results = [r for r in case_results if not r.valid]
        return DatasetValidationResponse(
            dataset_id=dataset_id,
            total_cases=len(case_results),
            valid_cases=valid_count,
            invalid_cases=len(case_results) - valid_count,
            errors=invalid_results,
            is_valid=(len(invalid_results) == 0),
        )

    # ── Evaluation run ─────────────────────────────────────────────────────────

    async def run_evaluation(self, request: EvaluationRunCreate) -> EvaluationRun:
        dataset = await self.get_dataset(request.dataset_id)
        tool = registry.get_or_raise(request.tool_name)

        run_id = str(uuid.uuid4())
        run = EvaluationRun(
            id=run_id,
            dataset_id=dataset.id,
            runtime_version=settings.app_version,
            model_provider=request.model_provider,
            status="running",
            config={"tool_name": request.tool_name, **request.config},
            started_at=_now(),
        )
        self.db.add(run)
        await self.db.commit()

        result_objects: list[EvaluationResult] = []

        for case in dataset.cases:
            t0 = time.perf_counter()
            actual_output = None
            error_msg = None

            # Determine per-case timeout
            timeout_sec = (
                case.timeout_ms / 1000.0 if case.timeout_ms else tool.timeout_seconds
            )

            try:
                actual_output = await asyncio.wait_for(
                    tool.execute(case.input), timeout=timeout_sec
                )
            except asyncio.TimeoutError:
                error_msg = f"Case timed out after {timeout_sec:.1f}s"
            except ToolError as exc:
                error_msg = str(exc)
            except Exception as exc:
                error_msg = f"Unexpected execution failure: {exc}"

            latency_ms = (time.perf_counter() - t0) * 1000.0

            # Evaluate assertions based on case assertion_type
            atype = case.assertion_type
            passed, assertions = evaluate_assertions(
                actual=actual_output,
                expected=case.expected_output,
                assertion_type=atype,
                error_msg=error_msg,
            )

            result = EvaluationResult(
                id=str(uuid.uuid4()),
                run_id=run.id,
                case_id=case.id,
                actual_output=actual_output,
                passed=passed,
                assertions=assertions,
                latency_ms=round(latency_ms, 2),
                error=error_msg,
            )
            self.db.add(result)
            result_objects.append(result)

        # ── Compute and persist aggregate metrics ────────────────────────────
        metrics = _aggregate_metrics(result_objects)
        run.status = "completed"
        run.finished_at = _now()
        run.total_cases = metrics["total_cases"]
        run.passed_cases = metrics["passed_cases"]
        run.failed_cases = metrics["failed_cases"]
        run.errored_cases = metrics["errored_cases"]
        run.timed_out_cases = metrics["timed_out_cases"]
        run.pass_rate = metrics["pass_rate"]
        run.error_rate = metrics["error_rate"]
        run.timeout_rate = metrics["timeout_rate"]
        run.latency_p50_ms = metrics["latency_p50_ms"]
        run.latency_p95_ms = metrics["latency_p95_ms"]
        run.latency_p99_ms = metrics["latency_p99_ms"]

        await self.db.commit()
        return await self.get_run(run_id)

    # ── Benchmark dataset ──────────────────────────────────────────────────────

    async def load_benchmark_dataset(self) -> EvaluationDataset:
        """
        Load the built-in benchmark dataset from disk.

        If the benchmark dataset already exists in the DB (by name) it is returned
        without re-creating it.
        """
        stmt = select(EvaluationDataset).where(EvaluationDataset.name == "Built-in Benchmark v2")
        res = await self.db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            return await self.get_dataset(existing.id)

        if not _BENCHMARK_PATH.exists():
            raise FileNotFoundError(f"Benchmark dataset file not found: {_BENCHMARK_PATH}")

        with _BENCHMARK_PATH.open(encoding="utf-8") as fh:
            raw = json.load(fh)

        # Parse into EvaluationDatasetCreate
        cases = []
        for c in raw.get("cases", []):
            from app.schemas import EvaluationCaseCreate  # local import avoids circular
            cases.append(EvaluationCaseCreate(
                name=c.get("name"),
                input=c["input"],
                expected_output=c.get("expected_output", {}),
                tags=c.get("tags", []),
                assertion_type=c.get("assertion_type", "exact"),
                timeout_ms=c.get("timeout_ms"),
                expect_error=c.get("expect_error", False),
            ))

        from app.schemas import EvaluationDatasetCreate  # local import
        request = EvaluationDatasetCreate(
            schema_version=raw.get("schema_version", "2"),
            name=raw["name"],
            description=raw.get("description", ""),
            cases=cases,
        )
        return await self.create_dataset(request)

    # ── Runs CRUD ──────────────────────────────────────────────────────────────

    async def list_runs(self, page: int = 1, page_size: int = 20) -> tuple[list[EvaluationRun], int]:
        count_stmt = select(func.count(EvaluationRun.id))
        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one()

        offset = (page - 1) * page_size
        stmt = (
            select(EvaluationRun)
            .options(selectinload(EvaluationRun.results))
            .order_by(EvaluationRun.started_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        res = await self.db.execute(stmt)
        runs = list(res.scalars().all())
        return runs, total

    async def get_run(self, run_id: str) -> EvaluationRun:
        stmt = (
            select(EvaluationRun)
            .options(selectinload(EvaluationRun.results))
            .where(EvaluationRun.id == run_id)
        )
        res = await self.db.execute(stmt)
        run = res.scalar_one_or_none()
        if not run:
            raise EvaluationNotFoundError(f"Run '{run_id}' not found")
        return run

    async def compare_runs(
        self,
        run_a_id: str,
        run_b_id: str,
        regression_threshold: float = 0.05,
    ) -> EvaluationComparisonResponse:
        run_a = await self.get_run(run_a_id)
        run_b = await self.get_run(run_b_id)

        res_a_map = {r.case_id: r for r in run_a.results}
        res_b_map = {r.case_id: r for r in run_b.results}

        pass_rate_a = run_a.pass_rate if run_a.pass_rate is not None else (
            sum(1 for r in run_a.results if r.passed) / len(run_a.results)
            if run_a.results else 0.0
        )
        pass_rate_b = run_b.pass_rate if run_b.pass_rate is not None else (
            sum(1 for r in run_b.results if r.passed) / len(run_b.results)
            if run_b.results else 0.0
        )

        latencies_a = [r.latency_ms for r in run_a.results if r.latency_ms is not None]
        latencies_b = [r.latency_ms for r in run_b.results if r.latency_ms is not None]

        avg_lat_a = sum(latencies_a) / len(latencies_a) if latencies_a else 0.0
        avg_lat_b = sum(latencies_b) / len(latencies_b) if latencies_b else 0.0

        regression_cases: list[str] = []
        improvement_cases: list[str] = []

        shared_case_ids = set(res_a_map.keys()) & set(res_b_map.keys())
        for case_id in shared_case_ids:
            a_passed = res_a_map[case_id].passed
            b_passed = res_b_map[case_id].passed

            if a_passed and not b_passed:
                regression_cases.append(case_id)
            elif not a_passed and b_passed:
                improvement_cases.append(case_id)

        delta_pass_rate = round(pass_rate_b - pass_rate_a, 6)
        regression_detected = delta_pass_rate < -regression_threshold

        return EvaluationComparisonResponse(
            run_a_id=run_a.id,
            run_b_id=run_b.id,
            run_a_pass_rate=round(pass_rate_a, 6),
            run_b_pass_rate=round(pass_rate_b, 6),
            delta_pass_rate=delta_pass_rate,
            run_a_avg_latency_ms=round(avg_lat_a, 2),
            run_b_avg_latency_ms=round(avg_lat_b, 2),
            delta_latency_ms=round(avg_lat_b - avg_lat_a, 2),
            regression_cases=regression_cases,
            improvement_cases=improvement_cases,
            regression_detected=regression_detected,
            regression_threshold=regression_threshold,
        )
