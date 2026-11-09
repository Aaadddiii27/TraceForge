"""
Full integration tests for FastAPI REST API endpoints.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


# ─── Health & Readiness ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_readiness_endpoint(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/health/ready")
    # Redis might be offline in unit test environment, so 503 or 200 is acceptable format
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "ready" in data
    assert "database" in data
    assert "redis" in data


# ─── Tools API ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_tools(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/tools")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 4
    tool_names = [t["name"] for t in data["items"]]
    assert "calculator" in tool_names
    assert "text_processor" in tool_names
    assert "knowledge_base" in tool_names
    assert "mock_tool" in tool_names


@pytest.mark.asyncio
async def test_get_tool_by_name(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/tools/calculator")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "calculator"
    assert "input_schema" in data
    assert "output_schema" in data

    # Nonexistent tool
    resp404 = await async_client.get("/api/v1/tools/nonexistent_tool")
    assert resp404.status_code == 404


# ─── Tasks API ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_task_success(async_client: AsyncClient):
    payload = {
        "tool_ids": ["calculator"],
        "input_payload": {"expression": "15 * 3 + 5"},
        "model_provider": "mock",
        "request_id": "test-req-001",
    }
    resp = await async_client.post("/api/v1/tasks", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "completed"
    assert data["output_payload"]["result"] == 50
    assert len(data["steps"]) == 1
    assert data["steps"][0]["status"] == "completed"

    # Verify task can be retrieved by ID
    task_id = data["id"]
    get_resp = await async_client.get(f"/api/v1/tasks/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == task_id

    # Verify task steps trace
    steps_resp = await async_client.get(f"/api/v1/tasks/{task_id}/steps")
    assert steps_resp.status_code == 200
    steps = steps_resp.json()
    assert len(steps) == 1
    assert steps[0]["step_name"] == "calculator"


@pytest.mark.asyncio
async def test_submit_task_failure(async_client: AsyncClient):
    payload = {
        "tool_ids": ["calculator"],
        "input_payload": {"expression": "1 / 0"},
        "model_provider": "mock",
    }
    resp = await async_client.post("/api/v1/tasks", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "failed"
    assert "Division by zero" in data["error_message"]
    assert len(data["steps"]) == 1
    assert data["steps"][0]["status"] == "failed"


@pytest.mark.asyncio
async def test_submit_task_validation_error(async_client: AsyncClient):
    # Empty tool_ids should produce 422
    resp = await async_client.post("/api/v1/tasks", json={"tool_ids": [], "input_payload": {}})
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_list_tasks_pagination(async_client: AsyncClient):
    # Create two tasks
    for expr in ["1 + 1", "2 + 2"]:
        await async_client.post("/api/v1/tasks", json={
            "tool_ids": ["calculator"],
            "input_payload": {"expression": expr},
        })

    resp = await async_client.get("/api/v1/tasks?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


# ─── Evaluation API ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_evaluation_workflow(async_client: AsyncClient):
    # 1. Create dataset
    dataset_payload = {
        "name": "Integration Test Dataset",
        "description": "Validation suite for evaluation endpoints",
        "cases": [
            {"input": {"expression": "3 * 3"}, "expected_output": {"result": 9}, "tags": ["math"]},
            {"input": {"expression": "4 * 4"}, "expected_output": {"result": 16}, "tags": ["math"]},
        ],
    }
    ds_resp = await async_client.post("/api/v1/evaluation/datasets", json=dataset_payload)
    assert ds_resp.status_code == 201
    dataset = ds_resp.json()
    dataset_id = dataset["id"]
    assert len(dataset["cases"]) == 2

    # 2. Start evaluation run
    run_payload = {
        "dataset_id": dataset_id,
        "model_provider": "mock",
        "tool_name": "calculator",
    }
    run_resp = await async_client.post("/api/v1/evaluation/runs", json=run_payload)
    assert run_resp.status_code == 201
    run = run_resp.json()
    assert run["status"] == "completed"
    assert len(run["results"]) == 2
    assert all(r["passed"] for r in run["results"])

    # 3. Get run by ID
    run_id = run["id"]
    get_run_resp = await async_client.get(f"/api/v1/evaluation/runs/{run_id}")
    assert get_run_resp.status_code == 200

    # 4. Compare run with itself
    comp_resp = await async_client.get(f"/api/v1/evaluation/runs/{run_id}/compare/{run_id}")
    assert comp_resp.status_code == 200
    comp = comp_resp.json()
    assert comp["run_a_pass_rate"] == 1.0
    assert comp["delta_pass_rate"] == 0.0

    # 5. Download results as CSV
    dl_resp = await async_client.get(f"/api/v1/evaluation/runs/{run_id}/download")
    assert dl_resp.status_code == 200
    assert "case_id,passed" in dl_resp.text
    assert "latency_ms" in dl_resp.text


# ─── Metrics API ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/metrics")
    assert resp.status_code == 200
    assert "ai_runtime_requests_total" in resp.text
