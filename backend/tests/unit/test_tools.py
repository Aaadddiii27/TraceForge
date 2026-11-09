"""
Unit tests for all built-in tools.
"""
from __future__ import annotations

import pytest

from app.tools.base import ToolError
from app.tools.calculator import CalculatorTool
from app.tools.knowledge_base import KnowledgeBaseTool
from app.tools.mock_tool import MockTool
from app.tools.text_processor import TextProcessorTool


# ─── CalculatorTool Tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_calculator_basic_arithmetic():
    calc = CalculatorTool()
    res = await calc.execute({"expression": "2 + 2"})
    assert res["result"] == 4

    res = await calc.execute({"expression": "10 * 5 - 12"})
    assert res["result"] == 38

    res = await calc.execute({"expression": "100 / 4"})
    assert res["result"] == 25.0


@pytest.mark.asyncio
async def test_calculator_math_functions_and_constants():
    calc = CalculatorTool()
    res = await calc.execute({"expression": "sqrt(16)"})
    assert res["result"] == 4.0

    res = await calc.execute({"expression": "2 ** 10"})
    assert res["result"] == 1024

    res = await calc.execute({"expression": "round(pi, 2)"})
    assert res["result"] == 3.14


@pytest.mark.asyncio
async def test_calculator_division_by_zero():
    calc = CalculatorTool()
    with pytest.raises(ToolError, match="Division by zero"):
        await calc.execute({"expression": "10 / 0"})


@pytest.mark.asyncio
async def test_calculator_disallows_code_execution():
    calc = CalculatorTool()
    # Attempting to call arbitrary functions or import must be rejected
    with pytest.raises(ToolError):
        await calc.execute({"expression": "__import__('os').system('ls')"})

    with pytest.raises(ToolError):
        await calc.execute({"expression": "eval('2+2')"})

    with pytest.raises(ToolError):
        await calc.execute({"expression": "exec('x = 1')"})


@pytest.mark.asyncio
async def test_calculator_invalid_syntax():
    calc = CalculatorTool()
    with pytest.raises(ToolError, match="Invalid expression syntax"):
        await calc.execute({"expression": "++*--"})


# ─── TextProcessorTool Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_text_processor_operations():
    proc = TextProcessorTool()

    # Word count
    res = await proc.execute({"operation": "word_count", "text": "hello world from AI runtime"})
    assert res["result"] == 5

    # Uppercase
    res = await proc.execute({"operation": "uppercase", "text": "hello"})
    assert res["result"] == "HELLO"

    # Reverse
    res = await proc.execute({"operation": "reverse", "text": "abcde"})
    assert res["result"] == "edcba"

    # Summarize stats
    res = await proc.execute({"operation": "summarize_stats", "text": "Hello world! This is a test."})
    assert res["result"]["word_count"] == 6
    assert res["result"]["sentence_count"] == 2


@pytest.mark.asyncio
async def test_text_processor_extract_entities():
    proc = TextProcessorTool()
    sample = "Reach out to user@example.com or admin@domain.org. Visit https://antigravity.dev now."

    emails = await proc.execute({"operation": "extract_emails", "text": sample})
    assert "user@example.com" in emails["result"]
    assert "admin@domain.org" in emails["result"]

    urls = await proc.execute({"operation": "extract_urls", "text": sample})
    assert "https://antigravity.dev" in urls["result"]


@pytest.mark.asyncio
async def test_text_processor_invalid_operation():
    proc = TextProcessorTool()
    with pytest.raises(ToolError, match="Invalid operation"):
        await proc.execute({"operation": "nonexistent_op", "text": "test"})


# ─── KnowledgeBaseTool Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_knowledge_base_search():
    kb = KnowledgeBaseTool()
    res = await kb.execute({"operation": "search", "query": "capital of France"})
    assert res["total"] >= 1
    top_hit = res["results"][0]
    assert "Paris" in top_hit["answer"]


@pytest.mark.asyncio
async def test_knowledge_base_get_by_id():
    kb = KnowledgeBaseTool()
    res = await kb.execute({"operation": "get_by_id", "id": "kb-003"})
    assert res["found"] is True
    assert res["result"]["answer"] == "Paris"


@pytest.mark.asyncio
async def test_knowledge_base_list_topics():
    kb = KnowledgeBaseTool()
    res = await kb.execute({"operation": "list_topics"})
    assert "geography" in res["topics"]
    assert "fastapi" in res["topics"]


# ─── MockTool Tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mock_tool_modes():
    mock = MockTool()

    # Success mode
    res = await mock.execute({"mode": "success"})
    assert res["result"] == "Mock tool executed successfully"

    # Echo mode
    res = await mock.execute({"mode": "echo", "payload": {"foo": "bar"}})
    assert res["payload"] == {"foo": "bar"}

    # Error mode
    with pytest.raises(ToolError, match="Custom failure"):
        await mock.execute({"mode": "error", "error_message": "Custom failure"})

    # Retriable error mode
    with pytest.raises(ToolError) as exc_info:
        await mock.execute({"mode": "retriable_error", "error_message": "Transient error"})
    assert exc_info.value.retriable is True
