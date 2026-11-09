"""
Tool Registry — abstract base class and registry.

Every tool must:
- Define an input schema (JSON Schema dict).
- Define an output schema (JSON Schema dict).
- Implement execute() which is deterministic and sandboxed.
- Declare its permission level, timeout, and version.
- Never execute arbitrary user-supplied code.
"""
from __future__ import annotations

import abc
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class ToolPermission:
    PUBLIC = "PUBLIC"          # No authentication required
    AUTHENTICATED = "AUTHENTICATED"  # Requires valid session/token
    ADMIN = "ADMIN"            # Requires admin role


class ToolError(Exception):
    """Raised when a tool execution fails in an expected way."""
    def __init__(self, message: str, retriable: bool = False) -> None:
        super().__init__(message)
        self.retriable = retriable


class ToolTimeoutError(ToolError):
    """Raised when a tool execution exceeds its allowed duration."""
    def __init__(self) -> None:
        super().__init__("Tool execution timed out", retriable=True)


class BaseTool(abc.ABC):
    """Abstract base class that all tools must implement."""

    # Subclasses must override these
    name: str
    description: str
    version: str = "1.0.0"
    permission_level: str = ToolPermission.PUBLIC
    timeout_seconds: int = 10

    @property
    @abc.abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """JSON Schema for the tool's accepted input."""
        ...

    @property
    @abc.abstractmethod
    def output_schema(self) -> dict[str, Any]:
        """JSON Schema for the tool's produced output."""
        ...

    @abc.abstractmethod
    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the tool with validated input.

        Returns a dict conforming to output_schema.
        Raises ToolError on expected failures.
        Raises ToolTimeoutError if implementation detects timeout.
        Must NEVER eval/exec user-supplied strings.
        """
        ...

    def validate_input(self, input_data: dict[str, Any]) -> None:
        """Basic structural validation before execution. Override for stricter checks."""
        pass

    def to_record_dict(self) -> dict[str, Any]:
        """Return a dict suitable for inserting into the tools table."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "enabled": True,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "permission_level": self.permission_level,
            "timeout_seconds": self.timeout_seconds,
        }


class ToolRegistry:
    """
    In-memory registry of available tools.

    Tools are registered at application startup. The registry is the
    single source of truth for which tools are available and their schemas.
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool. Raises if a tool with the same name already exists."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool
        logger.info("tool_registered", name=tool.name, version=tool.version)

    def get(self, name: str) -> BaseTool | None:
        """Return tool by name, or None if not found."""
        return self._tools.get(name)

    def get_or_raise(self, name: str) -> BaseTool:
        """Return tool by name, raising ToolError if not found or disabled."""
        tool = self._tools.get(name)
        if tool is None:
            raise ToolError(f"Tool '{name}' is not registered", retriable=False)
        return tool

    def list_tools(self) -> list[BaseTool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def __len__(self) -> int:
        return len(self._tools)


# Module-level singleton registry
registry = ToolRegistry()
