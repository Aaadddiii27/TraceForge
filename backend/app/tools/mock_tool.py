"""
Mock Tool — deterministic tool for testing.

Returns a configurable preset response. Useful in evaluation datasets and CI.
Can be configured to simulate errors or delays.
"""
from __future__ import annotations

import asyncio
from typing import Any

from app.tools.base import BaseTool, ToolError


class MockTool(BaseTool):
    """
    Deterministic mock tool for testing and evaluation.

    Behavior is controlled by the 'mode' field in input:
    - 'echo': returns the input as-is in the output
    - 'success': returns a preset success response
    - 'error': raises a ToolError
    - 'retriable_error': raises a retriable ToolError
    - 'slow': waits delay_seconds before responding (default 0)
    """
    name = "mock_tool"
    description = (
        "Deterministic mock tool for testing. Supports echo, success, error, "
        "and retriable_error modes. Use in evaluation datasets."
    )
    version = "1.0.0"
    timeout_seconds = 2

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["echo", "success", "error", "retriable_error", "slow"],
                    "default": "success",
                },
                "payload": {
                    "description": "Arbitrary payload echoed back in echo mode",
                },
                "delay_seconds": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 10,
                    "default": 0,
                    "description": "Artificial delay (used in slow mode)",
                },
                "error_message": {
                    "type": "string",
                    "default": "Mock tool error",
                },
            },
            "required": ["mode"],
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "mode": {"type": "string"},
                "result": {"type": "string"},
                "payload": {},
            },
            "required": ["mode"],
        }

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        mode = input_data.get("mode", "success")
        delay = float(input_data.get("delay_seconds", 0))

        if delay > 0:
            await asyncio.sleep(delay)

        match mode:
            case "echo":
                return {
                    "mode": "echo",
                    "payload": input_data.get("payload"),
                    "result": "echoed",
                }
            case "success":
                return {
                    "mode": "success",
                    "result": "Mock tool executed successfully",
                }
            case "slow":
                return {
                    "mode": "slow",
                    "result": f"Completed after {delay}s delay",
                }
            case "error":
                msg = input_data.get("error_message", "Mock tool error")
                raise ToolError(str(msg), retriable=False)
            case "retriable_error":
                msg = input_data.get("error_message", "Mock retriable error")
                raise ToolError(str(msg), retriable=True)
            case _:
                raise ToolError(f"Unknown mode '{mode}'", retriable=False)
