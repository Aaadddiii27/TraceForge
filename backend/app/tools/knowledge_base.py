"""
Knowledge Base Tool — read-only retrieval over a seeded local knowledge base.

The knowledge base is a static in-memory store of facts seeded at startup.
Lookups are exact-match and fuzzy-match by keyword. No external calls.
"""
from __future__ import annotations

import re
from typing import Any

from app.tools.base import BaseTool, ToolError


# Seeded knowledge base entries
_KNOWLEDGE_BASE: list[dict[str, str]] = [
    {"id": "kb-001", "topic": "fastapi", "question": "What is FastAPI?", "answer": "FastAPI is a modern, fast web framework for building APIs with Python based on standard Python type hints. It was created by Sebastián Ramírez."},
    {"id": "kb-002", "topic": "python", "question": "What is Python?", "answer": "Python is a high-level, interpreted programming language known for its clear syntax and readability. It was created by Guido van Rossum."},
    {"id": "kb-003", "topic": "geography", "question": "What is the capital of France?", "answer": "Paris"},
    {"id": "kb-004", "topic": "geography", "question": "What is the capital of Japan?", "answer": "Tokyo"},
    {"id": "kb-005", "topic": "geography", "question": "What is the capital of Germany?", "answer": "Berlin"},
    {"id": "kb-006", "topic": "math", "question": "What is 2 + 2?", "answer": "4"},
    {"id": "kb-007", "topic": "technology", "question": "What is Docker?", "answer": "Docker is a platform for developing, shipping, and running applications in containers. Containers allow developers to package an application with all its dependencies."},
    {"id": "kb-008", "topic": "technology", "question": "What is PostgreSQL?", "answer": "PostgreSQL is a powerful, open-source object-relational database system with a strong reputation for reliability and data integrity."},
    {"id": "kb-009", "topic": "technology", "question": "What is Redis?", "answer": "Redis is an open-source, in-memory data structure store used as a database, cache, message broker, and streaming engine."},
    {"id": "kb-010", "topic": "technology", "question": "What language is FastAPI written in?", "answer": "Python"},
    {"id": "kb-011", "topic": "science", "question": "What is the speed of light?", "answer": "The speed of light in a vacuum is approximately 299,792,458 metres per second (about 3×10^8 m/s)."},
    {"id": "kb-012", "topic": "science", "question": "What is the boiling point of water?", "answer": "Water boils at 100°C (212°F) at standard atmospheric pressure (1 atm)."},
    {"id": "kb-013", "topic": "ai", "question": "What is machine learning?", "answer": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed."},
    {"id": "kb-014", "topic": "ai", "question": "What is a neural network?", "answer": "A neural network is a machine learning model inspired by the human brain, consisting of interconnected layers of nodes that process and transform input data."},
    {"id": "kb-015", "topic": "ai_runtime", "question": "What is the AI Runtime Platform?", "answer": "The AI Runtime & Evaluation Platform is a developer tool for reliable AI task execution, traceable tool orchestration, repeatable evaluation, performance metrics, and operational dashboards."},
]


class KnowledgeBaseTool(BaseTool):
    """
    Read-only retrieval over a seeded local knowledge base.

    Supports: exact topic lookup, keyword search, list topics.
    All access is read-only; no mutation of the knowledge base is possible.
    """
    name = "knowledge_base"
    description = (
        "Read-only retrieval over a local knowledge base. "
        "Operations: search (keyword search), get_by_id (fetch by ID), "
        "list_topics (list available topics)."
    )
    version = "1.0.0"
    timeout_seconds = 10

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["search", "get_by_id", "list_topics"],
                },
                "query": {
                    "type": "string",
                    "description": "Search query (used for 'search' operation)",
                    "maxLength": 500,
                },
                "id": {
                    "type": "string",
                    "description": "Knowledge base entry ID (used for 'get_by_id')",
                },
                "topic": {
                    "type": "string",
                    "description": "Filter results by topic",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 5,
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {"type": "string"},
                "results": {"type": "array"},
                "total": {"type": "integer"},
            },
            "required": ["operation"],
        }

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        operation = input_data.get("operation", "")
        limit = min(int(input_data.get("limit", 5)), 20)
        topic_filter = input_data.get("topic", "").lower() if input_data.get("topic") else None

        match operation:
            case "search":
                query = input_data.get("query", "")
                if not isinstance(query, str) or not query.strip():
                    raise ToolError("'query' is required for search operation", retriable=False)
                results = self._search(query, topic_filter, limit)
                return {"operation": "search", "results": results, "total": len(results), "query": query}

            case "get_by_id":
                entry_id = input_data.get("id", "")
                if not isinstance(entry_id, str) or not entry_id.strip():
                    raise ToolError("'id' is required for get_by_id operation", retriable=False)
                entry = next((e for e in _KNOWLEDGE_BASE if e["id"] == entry_id), None)
                if entry is None:
                    return {"operation": "get_by_id", "result": None, "found": False}
                return {"operation": "get_by_id", "result": entry, "found": True}

            case "list_topics":
                topics = sorted({e["topic"] for e in _KNOWLEDGE_BASE})
                if topic_filter:
                    topics = [t for t in topics if topic_filter in t]
                return {"operation": "list_topics", "topics": topics, "total": len(topics)}

            case _:
                raise ToolError(
                    f"Unknown operation '{operation}'. Must be: search, get_by_id, list_topics",
                    retriable=False,
                )

    def _search(
        self, query: str, topic_filter: str | None, limit: int
    ) -> list[dict[str, Any]]:
        """Keyword-based search with relevance scoring."""
        query_lower = query.lower()
        query_words = set(re.split(r"\W+", query_lower)) - {"", "the", "a", "an", "is", "what"}

        scored: list[tuple[float, dict[str, str]]] = []
        for entry in _KNOWLEDGE_BASE:
            if topic_filter and entry["topic"] != topic_filter:
                continue

            # Score based on keyword matches in question + answer
            text = (entry["question"] + " " + entry["answer"]).lower()
            score = 0.0
            for word in query_words:
                if word in text:
                    score += 2.0 if word in entry["question"].lower() else 1.0

            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]
