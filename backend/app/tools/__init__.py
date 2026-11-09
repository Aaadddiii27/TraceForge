"""Tools package — register all built-in tools."""
from app.tools.base import BaseTool, ToolError, ToolPermission, ToolRegistry, ToolTimeoutError, registry
from app.tools.calculator import CalculatorTool
from app.tools.knowledge_base import KnowledgeBaseTool
from app.tools.mock_tool import MockTool
from app.tools.text_processor import TextProcessorTool


def register_builtin_tools() -> None:
    """Register all built-in tools into the global registry."""
    tools = [
        CalculatorTool(),
        TextProcessorTool(),
        KnowledgeBaseTool(),
        MockTool(),
    ]
    for tool in tools:
        registry.register(tool)


__all__ = [
    "BaseTool",
    "ToolError",
    "ToolTimeoutError",
    "ToolPermission",
    "ToolRegistry",
    "registry",
    "CalculatorTool",
    "TextProcessorTool",
    "KnowledgeBaseTool",
    "MockTool",
    "register_builtin_tools",
]
