"""
Unit tests for evaluation assertion engine.
"""
from __future__ import annotations

import pytest

from app.services.evaluation_service import evaluate_assertions


def test_exact_match_scalar():
    passed, res = evaluate_assertions({"result": 42}, {"result": 42})
    assert passed is True
    assert res["result"]["passed"] is True

    passed, res = evaluate_assertions({"result": 42}, {"result": 43})
    assert passed is False
    assert res["result"]["passed"] is False


def test_numeric_tolerance():
    passed, res = evaluate_assertions({"val": 3.14159265}, {"val": 3.14159})
    assert passed is True

    passed, res = evaluate_assertions({"val": 10.0}, {"val": 11.0})
    assert passed is False


def test_regex_matching():
    passed, res = evaluate_assertions(
        {"message": "Task 123 completed successfully"},
        {"message": "regex:Task \\d+ completed"}
    )
    assert passed is True

    passed, res = evaluate_assertions(
        {"message": "Task failed"},
        {"message": "regex:Task \\d+ completed"}
    )
    assert passed is False


def test_missing_key_in_actual():
    passed, res = evaluate_assertions({"output": 10}, {"missing_key": 10})
    assert passed is False
    assert "Missing expected key" in res["missing_key"]["reason"]


def test_nested_dict_assertions():
    actual = {"stats": {"words": 10, "chars": 50}}
    expected = {"stats": {"words": 10}}
    passed, res = evaluate_assertions(actual, expected)
    assert passed is True
