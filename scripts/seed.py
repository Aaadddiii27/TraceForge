#!/usr/bin/env python3
"""
Deterministic seed script for the AI Runtime & Evaluation Platform.

Populates the database with demonstration data:
- Built-in tool registry entries
- Sample evaluation datasets with test cases
- Sample task execution history and execution steps
- Demonstration evaluation run and verification results

Run: python scripts/seed.py
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from app.core.database import AsyncSessionLocal, create_all_tables
from app.models import (
    EvaluationCase,
    EvaluationDataset,
    EvaluationResult,
    EvaluationRun,
    ExecutionStep,
    Task,
)
from app.providers import register_providers
from app.services.tool_service import ToolService
from app.tools import register_builtin_tools


def _now() -> datetime:
    return datetime.now(timezone.utc)


SEED_TASKS = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "request_id": "demo-calc-001",
        "status": "completed",
        "model_provider": "mock",
        "tool_ids": ["calculator"],
        "input_payload": {"expression": "42 * 7 + 100"},
        "output_payload": {"result": 394, "expression": "42 * 7 + 100"},
        "created_at": _now() - timedelta(hours=2),
        "started_at": _now() - timedelta(hours=2),
        "finished_at": _now() - timedelta(hours=2) + timedelta(milliseconds=120),
        "retry_count": 0,
        "steps": [
            {
                "id": str(uuid.uuid4()),
                "step_name": "calculator",
                "status": "completed",
                "attempt_number": 1,
                "input": {"expression": "42 * 7 + 100"},
                "output": {"result": 394, "expression": "42 * 7 + 100"},
                "started_at": _now() - timedelta(hours=2),
                "finished_at": _now() - timedelta(hours=2) + timedelta(milliseconds=120),
            }
        ]
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "request_id": "demo-text-001",
        "status": "completed",
        "model_provider": "mock",
        "tool_ids": ["text_processor"],
        "input_payload": {"operation": "word_count", "text": "The quick brown fox jumps over the lazy dog"},
        "output_payload": {"operation": "word_count", "result": 9},
        "created_at": _now() - timedelta(hours=1, minutes=30),
        "started_at": _now() - timedelta(hours=1, minutes=30),
        "finished_at": _now() - timedelta(hours=1, minutes=30) + timedelta(milliseconds=80),
        "retry_count": 0,
        "steps": [
            {
                "id": str(uuid.uuid4()),
                "step_name": "text_processor",
                "status": "completed",
                "attempt_number": 1,
                "input": {"operation": "word_count", "text": "The quick brown fox jumps over the lazy dog"},
                "output": {"operation": "word_count", "result": 9},
                "started_at": _now() - timedelta(hours=1, minutes=30),
                "finished_at": _now() - timedelta(hours=1, minutes=30) + timedelta(milliseconds=80),
            }
        ]
    },
    {
        "id": "33333333-3333-3333-3333-333333333333",
        "request_id": "demo-multi-001",
        "status": "completed",
        "model_provider": "mock",
        "tool_ids": ["calculator", "text_processor"],
        "input_payload": {"expression": "100 / 4"},
        "output_payload": {"operation": "char_count", "result": 4},
        "created_at": _now() - timedelta(hours=1),
        "started_at": _now() - timedelta(hours=1),
        "finished_at": _now() - timedelta(hours=1) + timedelta(milliseconds=150),
        "retry_count": 0,
        "steps": [
            {
                "id": str(uuid.uuid4()),
                "step_name": "calculator",
                "status": "completed",
                "attempt_number": 1,
                "input": {"expression": "100 / 4"},
                "output": {"result": 25.0, "expression": "100 / 4"},
                "started_at": _now() - timedelta(hours=1),
                "finished_at": _now() - timedelta(hours=1) + timedelta(milliseconds=70),
            },
            {
                "id": str(uuid.uuid4()),
                "step_name": "text_processor",
                "status": "completed",
                "attempt_number": 1,
                "input": {"operation": "char_count", "text": "25.0"},
                "output": {"operation": "char_count", "result": 4},
                "started_at": _now() - timedelta(hours=1) + timedelta(milliseconds=70),
                "finished_at": _now() - timedelta(hours=1) + timedelta(milliseconds=150),
            }
        ]
    },
    {
        "id": "44444444-4444-4444-4444-444444444444",
        "request_id": "demo-fail-001",
        "status": "failed",
        "model_provider": "mock",
        "tool_ids": ["calculator"],
        "input_payload": {"expression": "1 / 0"},
        "output_payload": None,
        "created_at": _now() - timedelta(minutes=45),
        "started_at": _now() - timedelta(minutes=45),
        "finished_at": _now() - timedelta(minutes=45) + timedelta(milliseconds=20),
        "error_message": "Division by zero",
        "retry_count": 0,
        "steps": [
            {
                "id": str(uuid.uuid4()),
                "step_name": "calculator",
                "status": "failed",
                "attempt_number": 1,
                "input": {"expression": "1 / 0"},
                "output": None,
                "error": "Division by zero",
                "started_at": _now() - timedelta(minutes=45),
                "finished_at": _now() - timedelta(minutes=45) + timedelta(milliseconds=20),
            }
        ]
    },
]

SEED_DATASET = {
    "id": "55555555-5555-5555-5555-555555555555",
    "name": "Calculator Correctness Suite",
    "description": "Deterministic tests validating basic arithmetic and mathematical operations.",
    "cases": [
        {"id": "c1111111-1111-1111-1111-111111111111", "input": {"expression": "2 + 2"}, "expected_output": {"result": 4}, "tags": ["arithmetic", "basic"]},
        {"id": "c2222222-2222-2222-2222-222222222222", "input": {"expression": "10 * 5"}, "expected_output": {"result": 50}, "tags": ["arithmetic"]},
        {"id": "c3333333-3333-3333-3333-333333333333", "input": {"expression": "100 / 4"}, "expected_output": {"result": 25.0}, "tags": ["division"]},
        {"id": "c4444444-4444-4444-4444-444444444444", "input": {"expression": "2 ** 10"}, "expected_output": {"result": 1024}, "tags": ["exponent"]},
        {"id": "c5555555-5555-5555-5555-555555555555", "input": {"expression": "sqrt(16)"}, "expected_output": {"result": 4.0}, "tags": ["functions"]},
    ],
}


async def seed() -> None:
    print("[*] Starting database seeding...")

    # 1. Register tools and providers
    register_builtin_tools()
    register_providers()

    # 2. Ensure schema exists
    await create_all_tables()
    print("[OK] Database tables ensured")

    async with AsyncSessionLocal() as session:
        # 3. Upsert tools in database
        tool_svc = ToolService(session)
        await tool_svc.sync_registry_to_db()
        print("[OK] Registered tools synced to database")

        # 4. Insert demonstration tasks
        for task_dict in SEED_TASKS:
            task_copy = dict(task_dict)
            steps_data = task_copy.pop("steps", [])
            task = Task(**task_copy)
            session.add(task)
            for step_data in steps_data:
                step = ExecutionStep(task_id=task.id, **step_data)
                session.add(step)

        # 5. Insert evaluation dataset & cases
        dataset = EvaluationDataset(
            id=SEED_DATASET["id"],
            name=SEED_DATASET["name"],
            description=SEED_DATASET["description"],
        )
        session.add(dataset)

        for case_data in SEED_DATASET["cases"]:
            case = EvaluationCase(
                id=case_data["id"],
                dataset_id=dataset.id,
                input=case_data["input"],
                expected_output=case_data["expected_output"],
                tags=case_data["tags"],
            )
            session.add(case)

        # 6. Insert demonstration evaluation run
        eval_run_id = "66666666-6666-6666-6666-666666666666"
        eval_run = EvaluationRun(
            id=eval_run_id,
            dataset_id=dataset.id,
            runtime_version="0.1.0",
            model_provider="mock",
            status="completed",
            config={"tool_name": "calculator"},
            started_at=_now() - timedelta(minutes=10),
            finished_at=_now() - timedelta(minutes=10) + timedelta(seconds=2),
        )
        session.add(eval_run)

        # Add passing results for all 5 cases
        for case_data in SEED_DATASET["cases"]:
            res = EvaluationResult(
                id=str(uuid.uuid4()),
                run_id=eval_run_id,
                case_id=case_data["id"],
                actual_output=case_data["expected_output"],
                passed=True,
                assertions={"result": {"passed": True, "expected": case_data["expected_output"]["result"], "actual": case_data["expected_output"]["result"]}},
                latency_ms=1.5,
                error=None,
            )
            session.add(res)

        await session.commit()
        print("[OK] Demonstration tasks, dataset, and evaluation run seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
