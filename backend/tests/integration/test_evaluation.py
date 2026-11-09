"""
Integration tests for the Evaluation & Regression Engine (Task 3).

Covers:
- Empty dataset run — zero results, metrics are None/0
- Partial failure — mix of pass/fail cases; aggregate formulas verified
- Aggregate metric correctness: pass_rate == passed_cases / total_cases
- Two-run regression detection with deliberately introduced failure
- CSV export format validation (headers, summary rows)
- Built-in benchmark dataset execution
- Dataset validation endpoint
- AssertionType: expect_error, tool_called, schema, contains
- Latency percentile calculation
- compare_runs regression_detected flag
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import (
    EvaluationDatasetCreate,
    EvaluationRunCreate,
    EvaluationCaseCreate,
)
from app.services.evaluation_service import (
    AssertionType,
    EvaluationService,
    _aggregate_metrics,
    _compute_percentile,
    _validate_json_schema,
    evaluate_assertions,
)
from app.models import EvaluationResult


# ─── Unit: _compute_percentile ──────────────────────────────────────────────────

class TestComputePercentile:
    def test_empty_returns_none(self):
        assert _compute_percentile([], 50) is None

    def test_single_element(self):
        assert _compute_percentile([42.0], 50) == pytest.approx(42.0)
        assert _compute_percentile([42.0], 99) == pytest.approx(42.0)

    def test_p50_of_two(self):
        result = _compute_percentile([10.0, 20.0], 50)
        assert result == pytest.approx(15.0)

    def test_p0_is_min(self):
        vals = [5.0, 10.0, 15.0, 20.0, 25.0]
        assert _compute_percentile(vals, 0) == pytest.approx(5.0)

    def test_p100_is_max(self):
        vals = [5.0, 10.0, 15.0, 20.0, 25.0]
        assert _compute_percentile(vals, 100) == pytest.approx(25.0)

    def test_p95_on_sorted_list(self):
        # 20 evenly spaced values 1..20
        vals = [float(i) for i in range(1, 21)]
        p95 = _compute_percentile(vals, 95)
        assert p95 is not None
        assert 19.0 <= p95 <= 20.0


# ─── Unit: _validate_json_schema ───────────────────────────────────────────────

class TestValidateJsonSchema:
    def test_valid_object(self):
        schema = {"type": "object", "required": ["result"], "properties": {"result": {"type": "number"}}}
        errors = _validate_json_schema({"result": 42}, schema)
        assert errors == []

    def test_missing_required(self):
        schema = {"type": "object", "required": ["result"]}
        errors = _validate_json_schema({}, schema)
        assert any("result" in e for e in errors)

    def test_wrong_type(self):
        schema = {"type": "string"}
        errors = _validate_json_schema(42, schema)
        assert any("string" in e for e in errors)

    def test_minimum_violation(self):
        schema = {"type": "number", "minimum": 10}
        errors = _validate_json_schema(5, schema)
        assert any("minimum" in e for e in errors)

    def test_enum_violation(self):
        schema = {"enum": ["a", "b", "c"]}
        errors = _validate_json_schema("d", schema)
        assert any("enum" in e for e in errors)

    def test_array_items(self):
        schema = {"type": "array", "items": {"type": "number"}}
        errors = _validate_json_schema([1, "bad", 3], schema)
        assert len(errors) > 0

    def test_nested_properties(self):
        schema = {
            "type": "object",
            "properties": {
                "inner": {"type": "object", "required": ["x"], "properties": {"x": {"type": "integer"}}}
            }
        }
        errors = _validate_json_schema({"inner": {"x": "not_an_int"}}, schema)
        assert len(errors) > 0


# ─── Unit: evaluate_assertions ─────────────────────────────────────────────────

class TestEvaluateAssertions:
    # ── exact (default) ────────────────────────────────────────────────────────

    def test_exact_pass(self):
        passed, _ = evaluate_assertions({"result": 4.0}, {"result": 4.0})
        assert passed

    def test_exact_fail_wrong_value(self):
        passed, details = evaluate_assertions({"result": 5.0}, {"result": 4.0})
        assert not passed

    def test_exact_missing_key(self):
        passed, details = evaluate_assertions({}, {"result": 4.0})
        assert not passed
        assert "result" in details

    def test_exact_regex_pass(self):
        passed, _ = evaluate_assertions({"msg": "hello world"}, {"msg": "regex:hel.*world"})
        assert passed

    def test_exact_regex_fail(self):
        passed, _ = evaluate_assertions({"msg": "goodbye"}, {"msg": "regex:hel.*world"})
        assert not passed

    def test_numeric_float_tolerance(self):
        passed, _ = evaluate_assertions({"result": 4.000001}, {"result": 4.0})
        assert passed

    def test_list_subset(self):
        passed, _ = evaluate_assertions({"items": [1, 2, 3, 4]}, {"items": [1, 3]})
        assert passed

    def test_actual_none_fails(self):
        passed, details = evaluate_assertions(None, {"result": 1}, error_msg=None)
        assert not passed

    # ── contains ───────────────────────────────────────────────────────────────

    def test_contains_pass(self):
        passed, _ = evaluate_assertions(
            {"mode": "success", "result": "ok", "extra": "ignored"},
            {"mode": "success"},
            assertion_type="contains",
        )
        assert passed

    def test_contains_fail(self):
        passed, _ = evaluate_assertions(
            {"mode": "success"},
            {"mode": "success", "missing_key": "x"},
            assertion_type="contains",
        )
        assert not passed

    # ── expect_error ───────────────────────────────────────────────────────────

    def test_expect_error_passes_when_error_present(self):
        passed, details = evaluate_assertions(
            None, {}, assertion_type="expect_error", error_msg="Division by zero"
        )
        assert passed
        assert details["assertion_type"] == "expect_error"

    def test_expect_error_fails_when_no_error(self):
        passed, details = evaluate_assertions(
            {"result": 5}, {}, assertion_type="expect_error", error_msg=None
        )
        assert not passed

    def test_expect_error_with_error_contains_pass(self):
        passed, _ = evaluate_assertions(
            None,
            {"error_contains": "division"},
            assertion_type="expect_error",
            error_msg="Division by zero",
        )
        assert passed

    def test_expect_error_with_error_contains_fail(self):
        passed, _ = evaluate_assertions(
            None,
            {"error_contains": "timeout"},
            assertion_type="expect_error",
            error_msg="Division by zero",
        )
        assert not passed

    # ── tool_called ────────────────────────────────────────────────────────────

    def test_tool_called_passes_when_no_error(self):
        passed, _ = evaluate_assertions(
            {"result": 42}, {}, assertion_type="tool_called", error_msg=None
        )
        assert passed

    def test_tool_called_fails_when_error(self):
        passed, _ = evaluate_assertions(
            None, {}, assertion_type="tool_called", error_msg="Some error"
        )
        assert not passed

    def test_tool_called_fails_when_actual_none_no_error(self):
        passed, _ = evaluate_assertions(
            None, {}, assertion_type="tool_called", error_msg=None
        )
        assert not passed

    # ── schema ─────────────────────────────────────────────────────────────────

    def test_schema_pass(self):
        schema = {"type": "object", "required": ["result"], "properties": {"result": {"type": "number"}}}
        passed, _ = evaluate_assertions(
            {"result": 42.0},
            {"schema": schema},
            assertion_type="schema",
        )
        assert passed

    def test_schema_fail_missing_required(self):
        schema = {"type": "object", "required": ["result"]}
        passed, details = evaluate_assertions(
            {},
            {"schema": schema},
            assertion_type="schema",
        )
        assert not passed
        assert "schema_errors" in details

    def test_schema_no_schema_key(self):
        passed, details = evaluate_assertions(
            {"result": 1},
            {},
            assertion_type="schema",
        )
        assert not passed


# ─── Unit: _aggregate_metrics ──────────────────────────────────────────────────

class TestAggregateMetrics:
    def _make_result(self, passed: bool, latency_ms: float | None = 10.0, error: str | None = None):
        """Create a minimal EvaluationResult-like object."""
        from types import SimpleNamespace
        return SimpleNamespace(passed=passed, latency_ms=latency_ms, error=error)


    def test_empty_results(self):
        m = _aggregate_metrics([])
        assert m["total_cases"] == 0
        assert m["pass_rate"] is None
        assert m["latency_p50_ms"] is None

    def test_all_passing(self):
        results = [self._make_result(True, 10.0) for _ in range(5)]
        m = _aggregate_metrics(results)
        assert m["total_cases"] == 5
        assert m["passed_cases"] == 5
        assert m["pass_rate"] == pytest.approx(1.0)
        assert m["failed_cases"] == 0
        assert m["error_rate"] == pytest.approx(0.0)

    def test_partial_pass(self):
        results = [
            self._make_result(True, 10.0),
            self._make_result(True, 20.0),
            self._make_result(False, 15.0, error="some error"),
        ]
        m = _aggregate_metrics(results)
        assert m["total_cases"] == 3
        assert m["passed_cases"] == 2
        assert m["failed_cases"] == 1
        # pass_rate must equal passed / total exactly
        assert m["pass_rate"] == pytest.approx(2 / 3)

    def test_pass_rate_formula_invariant(self):
        """pass_rate == passed_cases / total_cases for various configurations."""
        for n_total, n_pass in [(1, 0), (1, 1), (10, 3), (100, 73)]:
            results = (
                [self._make_result(True) for _ in range(n_pass)] +
                [self._make_result(False, error="err") for _ in range(n_total - n_pass)]
            )
            m = _aggregate_metrics(results)
            assert m["pass_rate"] == pytest.approx(n_pass / n_total), (
                f"Formula failed for {n_pass}/{n_total}"
            )

    def test_latency_percentiles_computed(self):
        # 10 results with distinct latencies 10..100ms
        results = [self._make_result(True, float(i * 10)) for i in range(1, 11)]
        m = _aggregate_metrics(results)
        assert m["latency_p50_ms"] is not None
        assert m["latency_p95_ms"] is not None
        assert m["latency_p99_ms"] is not None
        # p50 should be around 55ms for [10,20,...,100]
        assert 50 <= m["latency_p50_ms"] <= 60

    def test_none_latencies_excluded(self):
        results = [self._make_result(True, None) for _ in range(3)]
        m = _aggregate_metrics(results)
        assert m["latency_p50_ms"] is None


# ─── Integration: API tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestEvaluationAPITask3:

    async def test_empty_dataset_run_returns_zero_metrics(self, async_client: AsyncClient):
        """Running an empty dataset produces 0 cases and None/zero metrics."""
        # Create empty dataset
        resp = await async_client.post("/api/v1/evaluation/datasets", json={
            "name": "Empty Dataset",
            "description": "has no cases",
            "cases": [],
        })
        assert resp.status_code == 201
        ds_id = resp.json()["id"]

        # Run evaluation
        resp = await async_client.post("/api/v1/evaluation/runs", json={
            "dataset_id": ds_id,
            "tool_name": "calculator",
        })
        assert resp.status_code == 201
        run = resp.json()
        assert run["total_cases"] == 0
        assert run["passed_cases"] == 0
        assert run["pass_rate"] is None
        assert run["error_rate"] is None

    async def test_partial_failure_aggregate_formulas(self, async_client: AsyncClient):
        """Aggregate metrics must agree with individual case results."""
        resp = await async_client.post("/api/v1/evaluation/datasets", json={
            "name": "Partial Failure Dataset",
            "description": "2 pass, 1 fail",
            "cases": [
                {
                    "name": "pass_case_1",
                    "input": {"expression": "1 + 1"},
                    "expected_output": {"result": 2.0},
                    "assertion_type": "exact",
                },
                {
                    "name": "pass_case_2",
                    "input": {"expression": "10 - 3"},
                    "expected_output": {"result": 7.0},
                    "assertion_type": "exact",
                },
                {
                    "name": "fail_case",
                    "input": {"expression": "5 + 5"},
                    "expected_output": {"result": 999.0},  # deliberately wrong
                    "assertion_type": "exact",
                },
            ],
        })
        assert resp.status_code == 201
        ds_id = resp.json()["id"]

        resp = await async_client.post("/api/v1/evaluation/runs", json={
            "dataset_id": ds_id,
            "tool_name": "calculator",
        })
        assert resp.status_code == 201
        run = resp.json()

        # Verify aggregate formula
        assert run["total_cases"] == 3
        assert run["passed_cases"] == 2
        assert run["failed_cases"] == 1
        # pass_rate must exactly equal passed / total
        assert abs(run["pass_rate"] - (2 / 3)) < 1e-5

    async def test_expect_error_assertion_type(self, async_client: AsyncClient):
        """expect_error cases pass when the tool raises a ToolError."""
        resp = await async_client.post("/api/v1/evaluation/datasets", json={
            "name": "Expect Error Dataset",
            "cases": [
                {
                    "name": "div_by_zero",
                    "input": {"expression": "1 / 0"},
                    "expected_output": {"error_contains": "division"},
                    "assertion_type": "expect_error",
                    "expect_error": True,
                },
            ],
        })
        assert resp.status_code == 201
        ds_id = resp.json()["id"]

        resp = await async_client.post("/api/v1/evaluation/runs", json={
            "dataset_id": ds_id,
            "tool_name": "calculator",
        })
        assert resp.status_code == 201
        run = resp.json()
        assert run["total_cases"] == 1
        assert run["passed_cases"] == 1
        assert run["pass_rate"] == pytest.approx(1.0)
        # Verify individual result
        result = run["results"][0]
        assert result["passed"] is True
        assert result["error"] is not None

    async def test_schema_assertion_type(self, async_client: AsyncClient):
        """schema assertion validates actual output against a JSON Schema."""
        resp = await async_client.post("/api/v1/evaluation/datasets", json={
            "name": "Schema Assertion Dataset",
            "cases": [
                {
                    "name": "schema_check",
                    "input": {"expression": "sqrt(9)"},
                    "expected_output": {
                        "schema": {
                            "type": "object",
                            "required": ["result"],
                            "properties": {
                                "result": {"type": "number", "minimum": 2.9, "maximum": 3.1}
                            },
                        }
                    },
                    "assertion_type": "schema",
                },
            ],
        })
        assert resp.status_code == 201
        ds_id = resp.json()["id"]

        resp = await async_client.post("/api/v1/evaluation/runs", json={
            "dataset_id": ds_id,
            "tool_name": "calculator",
        })
        assert resp.status_code == 201
        run = resp.json()
        assert run["passed_cases"] == 1

    async def test_regression_detection(self, async_client: AsyncClient):
        """
        Deliberate regression scenario:
        - Run A: both cases pass (100% pass rate)
        - Run B: one case is made to fail by changing expected_output (50% pass rate)
        - compare_runs must detect regression_detected=True for threshold < 0.5
        """
        # Dataset for Run A — two cases that both pass
        resp = await async_client.post("/api/v1/evaluation/datasets", json={
            "name": "Regression Test Dataset A",
            "cases": [
                {
                    "name": "case_1",
                    "input": {"expression": "2 + 2"},
                    "expected_output": {"result": 4.0},
                    "assertion_type": "exact",
                },
                {
                    "name": "case_2",
                    "input": {"expression": "3 * 3"},
                    "expected_output": {"result": 9.0},
                    "assertion_type": "exact",
                },
            ],
        })
        assert resp.status_code == 201
        ds_a_id = resp.json()["id"]

        # Run A — all pass
        resp = await async_client.post("/api/v1/evaluation/runs", json={
            "dataset_id": ds_a_id,
            "tool_name": "calculator",
        })
        assert resp.status_code == 201
        run_a_id = resp.json()["id"]
        assert resp.json()["pass_rate"] == pytest.approx(1.0)

        # Dataset for Run B — second case expects wrong value
        resp = await async_client.post("/api/v1/evaluation/datasets", json={
            "name": "Regression Test Dataset B",
            "cases": [
                {
                    "name": "case_1",
                    "input": {"expression": "2 + 2"},
                    "expected_output": {"result": 4.0},
                    "assertion_type": "exact",
                },
                {
                    "name": "case_2_regressed",
                    "input": {"expression": "3 * 3"},
                    "expected_output": {"result": 999.0},  # deliberately wrong!
                    "assertion_type": "exact",
                },
            ],
        })
        assert resp.status_code == 201
        ds_b_id = resp.json()["id"]

        # Run B — one passes, one fails
        resp = await async_client.post("/api/v1/evaluation/runs", json={
            "dataset_id": ds_b_id,
            "tool_name": "calculator",
        })
        assert resp.status_code == 201
        run_b_id = resp.json()["id"]
        assert resp.json()["pass_rate"] == pytest.approx(0.5)

        # Compare: delta = 0.5 - 1.0 = -0.5, threshold=0.05 → regression_detected=True
        resp = await async_client.get(
            f"/api/v1/evaluation/runs/{run_a_id}/compare/{run_b_id}",
            params={"regression_threshold": 0.05},
        )
        assert resp.status_code == 200
        comparison = resp.json()
        assert comparison["run_a_pass_rate"] == pytest.approx(1.0)
        assert comparison["run_b_pass_rate"] == pytest.approx(0.5)
        assert comparison["delta_pass_rate"] == pytest.approx(-0.5)
        assert comparison["regression_detected"] is True

    async def test_no_regression_within_threshold(self, async_client: AsyncClient):
        """A small delta below the threshold must not be flagged as regression."""
        # Both datasets pass all cases → delta = 0.0 → not a regression
        resp = await async_client.post("/api/v1/evaluation/datasets", json={
            "name": "No Regression A",
            "cases": [{"name": "c1", "input": {"expression": "1+1"}, "expected_output": {"result": 2.0}, "assertion_type": "exact"}],
        })
        ds_a_id = resp.json()["id"]
        resp = await async_client.post("/api/v1/evaluation/runs", json={"dataset_id": ds_a_id, "tool_name": "calculator"})
        run_a_id = resp.json()["id"]

        resp = await async_client.post("/api/v1/evaluation/datasets", json={
            "name": "No Regression B",
            "cases": [{"name": "c1", "input": {"expression": "2+2"}, "expected_output": {"result": 4.0}, "assertion_type": "exact"}],
        })
        ds_b_id = resp.json()["id"]
        resp = await async_client.post("/api/v1/evaluation/runs", json={"dataset_id": ds_b_id, "tool_name": "calculator"})
        run_b_id = resp.json()["id"]

        resp = await async_client.get(
            f"/api/v1/evaluation/runs/{run_a_id}/compare/{run_b_id}",
            params={"regression_threshold": 0.05},
        )
        assert resp.status_code == 200
        assert resp.json()["regression_detected"] is False

    async def test_repeated_runs_independent(self, async_client: AsyncClient):
        """Running the same dataset twice produces independent, persistent result sets."""
        resp = await async_client.post("/api/v1/evaluation/datasets", json={
            "name": "Repeated Runs Dataset",
            "cases": [
                {"name": "c1", "input": {"expression": "5 * 5"}, "expected_output": {"result": 25.0}, "assertion_type": "exact"},
            ],
        })
        ds_id = resp.json()["id"]

        resp1 = await async_client.post("/api/v1/evaluation/runs", json={"dataset_id": ds_id, "tool_name": "calculator"})
        resp2 = await async_client.post("/api/v1/evaluation/runs", json={"dataset_id": ds_id, "tool_name": "calculator"})

        run1_id = resp1.json()["id"]
        run2_id = resp2.json()["id"]
        assert run1_id != run2_id

        # Both persist independently
        r1 = await async_client.get(f"/api/v1/evaluation/runs/{run1_id}")
        r2 = await async_client.get(f"/api/v1/evaluation/runs/{run2_id}")
        assert r1.json()["pass_rate"] == pytest.approx(1.0)
        assert r2.json()["pass_rate"] == pytest.approx(1.0)

    async def test_csv_download_format(self, async_client: AsyncClient):
        """CSV download includes required headers and a summary section."""
        resp = await async_client.post("/api/v1/evaluation/datasets", json={
            "name": "CSV Export Dataset",
            "cases": [
                {"name": "ok", "input": {"expression": "7 + 3"}, "expected_output": {"result": 10.0}, "assertion_type": "exact"},
            ],
        })
        ds_id = resp.json()["id"]
        resp = await async_client.post("/api/v1/evaluation/runs", json={"dataset_id": ds_id, "tool_name": "calculator"})
        run_id = resp.json()["id"]

        resp = await async_client.get(f"/api/v1/evaluation/runs/{run_id}/download")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

        content = resp.text
        lines = content.strip().splitlines()
        # First line is header
        assert lines[0].startswith("case_id")
        # Header must include required columns
        assert "passed" in lines[0]
        assert "latency_ms" in lines[0]
        assert "assertion_type" in lines[0]
        # Summary section exists
        assert any("SUMMARY" in line for line in lines)
        assert any("pass_rate" in line for line in lines)

    async def test_dataset_validate_endpoint(self, async_client: AsyncClient):
        """Validate endpoint returns per-case validation results."""
        resp = await async_client.post("/api/v1/evaluation/datasets", json={
            "name": "Validate Endpoint Dataset",
            "cases": [
                {
                    "name": "valid_case",
                    "input": {"expression": "1+1"},
                    "expected_output": {"result": 2.0},
                    "assertion_type": "exact",
                },
            ],
        })
        ds_id = resp.json()["id"]

        resp = await async_client.post(f"/api/v1/evaluation/datasets/{ds_id}/validate")
        assert resp.status_code == 200
        v = resp.json()
        assert v["is_valid"] is True
        assert v["total_cases"] == 1
        assert v["valid_cases"] == 1
        assert v["invalid_cases"] == 0

    async def test_benchmark_dataset_loads(self, async_client: AsyncClient):
        """The built-in benchmark dataset loads without error."""
        resp = await async_client.get("/api/v1/evaluation/benchmark/dataset")
        assert resp.status_code == 200
        ds = resp.json()
        assert ds["name"] == "Built-in Benchmark v2"
        assert len(ds["cases"]) > 0

    async def test_benchmark_run_completes(self, async_client: AsyncClient):
        """Running the benchmark against mock_tool completes and returns metrics."""
        resp = await async_client.post(
            "/api/v1/evaluation/benchmark",
            params={"tool_name": "mock_tool"},
        )
        assert resp.status_code == 201
        run = resp.json()
        assert run["status"] == "completed"
        assert run["total_cases"] > 0
        assert run["pass_rate"] is not None
        # At least some cases should pass (mock_tool echo/success/tool_called should)
        assert run["passed_cases"] > 0

    async def test_benchmark_calculator_run(self, async_client: AsyncClient):
        """Calculator benchmark: only calculator-tagged cases should matter, but all run."""
        resp = await async_client.post(
            "/api/v1/evaluation/benchmark",
            params={"tool_name": "calculator"},
        )
        assert resp.status_code == 201
        run = resp.json()
        assert run["status"] == "completed"
        assert run["total_cases"] > 0

    async def test_run_metrics_persisted(self, async_client: AsyncClient):
        """Aggregate metrics are persisted on the run and returned on GET."""
        resp = await async_client.post("/api/v1/evaluation/datasets", json={
            "name": "Persisted Metrics Dataset",
            "cases": [
                {"name": "c1", "input": {"expression": "10 / 2"}, "expected_output": {"result": 5.0}, "assertion_type": "exact"},
                {"name": "c2", "input": {"expression": "1 / 0"}, "expected_output": {}, "assertion_type": "expect_error", "expect_error": True},
            ],
        })
        ds_id = resp.json()["id"]
        run_resp = await async_client.post("/api/v1/evaluation/runs", json={"dataset_id": ds_id, "tool_name": "calculator"})
        run_id = run_resp.json()["id"]

        # Re-fetch from DB
        get_resp = await async_client.get(f"/api/v1/evaluation/runs/{run_id}")
        assert get_resp.status_code == 200
        r = get_resp.json()
        assert r["total_cases"] == 2
        assert r["passed_cases"] == 2
        assert r["pass_rate"] == pytest.approx(1.0)
        assert r["latency_p50_ms"] is not None
