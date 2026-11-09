"""
Text Processor Tool — safe text analysis and transformation.

Operations are purely deterministic and operate only on user-provided text.
No external calls, no code execution.
"""
from __future__ import annotations

import re
from typing import Any

from app.tools.base import BaseTool, ToolError


class TextProcessorTool(BaseTool):
    """
    Performs deterministic text operations.

    Operations: word_count, char_count, uppercase, lowercase, reverse,
                title_case, sentence_count, extract_emails, extract_urls
    """
    name = "text_processor"
    description = (
        "Performs deterministic text analysis and transformation. "
        "Supported operations: word_count, char_count, uppercase, lowercase, "
        "reverse, title_case, sentence_count, extract_emails, extract_urls."
    )
    version = "1.0.0"
    timeout_seconds = 10

    SUPPORTED_OPERATIONS = {
        "word_count",
        "char_count",
        "uppercase",
        "lowercase",
        "reverse",
        "title_case",
        "sentence_count",
        "extract_emails",
        "extract_urls",
        "summarize_stats",
    }

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": sorted(self.SUPPORTED_OPERATIONS),
                    "description": "Text operation to perform",
                },
                "text": {
                    "type": "string",
                    "description": "Input text to process",
                    "maxLength": 100_000,
                },
            },
            "required": ["operation", "text"],
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {"type": "string"},
                "result": {},  # varies by operation
            },
            "required": ["operation", "result"],
        }

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        operation = input_data.get("operation") or "char_count"
        text = input_data.get("text")
        if text is None:
            if "result" in input_data:
                text = str(input_data["result"])
            elif "expression" in input_data:
                text = str(input_data["expression"])
            elif "payload" in input_data:
                text = str(input_data["payload"])
            else:
                text = ""

        if not isinstance(operation, str) or operation not in self.SUPPORTED_OPERATIONS:
            raise ToolError(
                f"Invalid operation '{operation}'. Must be one of: "
                f"{sorted(self.SUPPORTED_OPERATIONS)}",
                retriable=False,
            )
        if not isinstance(text, str):
            raise ToolError("'text' must be a string", retriable=False)
        if len(text) > 100_000:
            raise ToolError("Text too long (max 100,000 characters)", retriable=False)

        result = await self._dispatch(operation, text)
        return {"operation": operation, "result": result}

    async def _dispatch(self, operation: str, text: str) -> Any:
        match operation:
            case "word_count":
                return len(text.split())
            case "char_count":
                return len(text)
            case "uppercase":
                return text.upper()
            case "lowercase":
                return text.lower()
            case "reverse":
                return text[::-1]
            case "title_case":
                return text.title()
            case "sentence_count":
                # Count sentences by splitting on .!? followed by whitespace or end
                sentences = re.split(r"[.!?]+\s*", text.strip())
                return len([s for s in sentences if s.strip()])
            case "extract_emails":
                pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
                return re.findall(pattern, text)
            case "extract_urls":
                pattern = r"https?://[^\s<>\"{}|\\^`\[\]]+"
                return re.findall(pattern, text)
            case "summarize_stats":
                words = text.split()
                sentences = re.split(r"[.!?]+\s*", text.strip())
                return {
                    "word_count": len(words),
                    "char_count": len(text),
                    "sentence_count": len([s for s in sentences if s.strip()]),
                    "avg_word_length": (
                        round(sum(len(w) for w in words) / len(words), 2) if words else 0
                    ),
                    "unique_words": len(set(w.lower().strip(".,!?;:") for w in words)),
                }
            case _:
                raise ToolError(f"Unknown operation: {operation}", retriable=False)
