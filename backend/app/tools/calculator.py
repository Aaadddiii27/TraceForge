"""
Calculator Tool — safe mathematical expression evaluator.

Uses Python's ast module to parse expressions and evaluates only
safe numeric operations. Never calls eval() on user input directly.
"""
from __future__ import annotations

import ast
import math
import operator
from typing import Any

from app.tools.base import BaseTool, ToolError


# Allowlisted AST node types for safe evaluation
_SAFE_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.Call,       # Only for allowlisted math functions
    ast.Name,       # Only for allowlisted names
    ast.Load,
)

# Allowlisted math functions
_SAFE_FUNCTIONS: dict[str, Any] = {
    "abs": abs,
    "round": round,
    "sqrt": math.sqrt,
    "ceil": math.ceil,
    "floor": math.floor,
    "log": math.log,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pi": math.pi,
    "e": math.e,
}

_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.AST) -> float | int:
    """Recursively evaluate an AST node using only safe operations."""
    if not isinstance(node, _SAFE_NODES):
        raise ToolError(f"Unsupported operation: {type(node).__name__}", retriable=False)

    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)

    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ToolError("Only numeric constants are allowed", retriable=False)
        return node.value

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPS:
            raise ToolError(f"Operator {op_type.__name__} is not allowed", retriable=False)
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        try:
            return _SAFE_OPS[op_type](left, right)
        except ZeroDivisionError:
            raise ToolError("Division by zero", retriable=False)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPS:
            raise ToolError(f"Unary operator {op_type.__name__} is not allowed", retriable=False)
        operand = _safe_eval(node.operand)
        return _SAFE_OPS[op_type](operand)

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ToolError("Only named function calls are allowed", retriable=False)
        func_name = node.func.id
        if func_name not in _SAFE_FUNCTIONS:
            raise ToolError(f"Function '{func_name}' is not allowed", retriable=False)
        func = _SAFE_FUNCTIONS[func_name]
        if callable(func):
            args = [_safe_eval(arg) for arg in node.args]
            try:
                return func(*args)
            except Exception as exc:
                raise ToolError(f"Math error: {exc}", retriable=False)
        # It's a constant like pi or e
        return float(func)

    if isinstance(node, ast.Name):
        if node.id in _SAFE_FUNCTIONS and not callable(_SAFE_FUNCTIONS[node.id]):
            return float(_SAFE_FUNCTIONS[node.id])
        raise ToolError(f"Name '{node.id}' is not allowed", retriable=False)

    raise ToolError(f"Unsupported node type: {type(node).__name__}", retriable=False)


class CalculatorTool(BaseTool):
    """
    Evaluates mathematical expressions safely.

    Supports: +, -, *, /, //, %, **, unary +/-
    Functions: abs, round, sqrt, ceil, floor, log, log10, sin, cos, tan
    Constants: pi, e
    """
    name = "calculator"
    description = (
        "Evaluates mathematical expressions safely. Supports basic arithmetic, "
        "exponentiation, and common math functions (sqrt, sin, cos, log, etc.). "
        "Never executes arbitrary code."
    )
    version = "1.0.0"
    timeout_seconds = 5

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate",
                    "examples": ["2 + 2", "sqrt(16)", "pi * 2"],
                    "maxLength": 500,
                }
            },
            "required": ["expression"],
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "result": {"type": "number"},
                "expression": {"type": "string"},
            },
            "required": ["result", "expression"],
        }

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        expression = input_data.get("expression", "")
        if not isinstance(expression, str) or not expression.strip():
            raise ToolError("'expression' must be a non-empty string", retriable=False)
        if len(expression) > 500:
            raise ToolError("Expression too long (max 500 chars)", retriable=False)

        try:
            tree = ast.parse(expression.strip(), mode="eval")
        except SyntaxError as exc:
            raise ToolError(f"Invalid expression syntax: {exc}", retriable=False)

        result = _safe_eval(tree)
        return {"result": result, "expression": expression}
