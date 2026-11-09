# Evaluation & Regression Guide

## 1. Overview

The AI Runtime & Evaluation Platform includes an evaluation and regression engine designed to measure whether task executions behave correctly, predictably, and without regressions across runtime versions or model configurations.

Evaluations run deterministically against predefined datasets, verifying tool behavior, output structure, error conditions, latency, and assertions without relying on unreliable or non-deterministic LLM-as-a-judge scorers.

---

## 2. Dataset Schema (v2 Format)

Datasets are defined in a versioned JSON format (`schema_version: "2"`). Each dataset contains metadata and an array of individual test cases.

```json
{
  "schema_version": "2",
  "name": "Math and Text Benchmark",
  "description": "Deterministic benchmark for core math and text manipulation tools",
  "cases": [
    {
      "name": "calculator_basic_add",
      "tags": ["calculator", "arithmetic", "smoke"],
      "input": {
        "expression": "2 + 2"
      },
      "expected_output": {
        "result": 4.0
      },
      "assertion_type": "exact",
      "timeout_ms": 1000,
      "expect_error": false
    }
  ]
}
```

### Case Fields:
- `name` *(string, optional)*: Unique human-readable identifier for reporting and regression diffs.
- `tags` *(list[string])*: Tags used for grouping, filtering, or categorization (e.g. `["smoke", "calculator"]`).
- `input` *(dict, required)*: Input payload passed directly to the tool or task execution.
- `expected_output` *(dict, required)*: Specification of expected outputs or schemas against which actual execution results are checked.
- `assertion_type` *(string, default "exact")*: Assertion strategy applied to evaluate the case.
- `timeout_ms` *(integer, optional)*: Maximum execution time allowed for this specific case (1 to 30,000 ms). If omitted, the tool's default timeout is enforced.
- `expect_error` *(boolean, default false)*: Flag indicating whether this case tests error handling. When `true`, the case passes only if the tool raises an expected error.

---

## 3. Assertion Strategies

The platform supports five assertion types:

| Assertion Type | Description | Expected Output Spec |
| :--- | :--- | :--- |
| `exact` | Compares all keys in `expected_output` to `actual_output`. Floats are compared using relative/absolute tolerance ($10^{-5}$). Supports nested dictionaries, list subsets, and `regex:` prefixes on string values. | `{"result": 42.0}` or `{"msg": "regex:Completed in \\d+ms"}` |
| `contains` | Checks that all keys and values specified in `expected_output` are present in `actual_output`, ignoring extra keys produced by the tool. | `{"status": "ok"}` |
| `schema` | Validates `actual_output` against a JSON Schema. Supports types, `required`, `properties`, `minimum`, `maximum`, `minLength`, `maxLength`, `pattern`, `enum`, and `items`. | `{"schema": {"type": "object", "required": ["result"], "properties": {"result": {"type": "number"}}}}` |
| `expect_error` | Verifies that the tool or step failed with a `ToolError`. Optionally matches against an error substring. | `{"error_contains": "division by zero"}` or `{}` |
| `tool_called` | Verifies that the tool was invoked and completed without raising an unexpected error, regardless of the output payload shape. | `{}` |

---

## 4. Metric Definitions

When an evaluation run completes, aggregate metrics are computed over all executed cases and persisted on the `EvaluationRun` record:

### Count Metrics
- **Total Cases ($N$)**: Total count of cases executed in the run ($N = N_{\text{passed}} + N_{\text{failed}}$).
- **Passed Cases ($N_{\text{passed}}$)**: Count of test cases where all assertions passed.
- **Failed Cases ($N_{\text{failed}}$)**: Count of cases where any assertion failed, including unexpected execution errors or timeouts.
- **Errored Cases ($N_{\text{errored}}$)**: Count of cases that failed due to unhandled execution or tool errors (excluding expected errors).
- **Timed Out Cases ($N_{\text{timeout}}$)**: Count of cases that exceeded either the case-specific `timeout_ms` or the tool's timeout limit.

### Rate Metrics
- **Pass Rate**:
  $$\text{Pass Rate} = \frac{N_{\text{passed}}}{N}$$
  A value between $0.0$ and $1.0$ (or `None` if $N = 0$).
- **Error Rate**:
  $$\text{Error Rate} = \frac{N_{\text{errored}}}{N}$$
- **Timeout Rate**:
  $$\text{Timeout Rate} = \frac{N_{\text{timeout}}}{N}$$

### Latency Metrics (Percentiles)
Measured in milliseconds across all case executions:
- **p50 Latency (Median)**: The 50th percentile execution latency using linear interpolation.
- **p95 Latency**: 95th percentile latency, representing tail response time.
- **p99 Latency**: 99th percentile latency, capturing extreme outliers.

---

## 5. Baseline Comparison & Regression Detection

Evaluation runs can be compared against a baseline to detect regressions and performance degradations:

### Comparison Endpoint
`GET /api/v1/evaluation/runs/{run_a_id}/compare/{run_b_id}?regression_threshold=0.05`

### Calculation
- **$\Delta \text{Pass Rate}$**:
  $$\Delta \text{Pass Rate} = \text{Pass Rate}_B - \text{Pass Rate}_A$$
- **Regression Detection**:
  $$\text{Regression Detected} = \left( \Delta \text{Pass Rate} < -\text{threshold} \right)$$
  For example, with a threshold of $0.05$ (5 percentage points), if Run A had a pass rate of $1.00$ (100%) and Run B had $0.90$ (90%), $\Delta = -0.10 < -0.05$, so `regression_detected: true`.
- **Case-Level Attribution**:
  - `regression_cases`: List of `case_id`s that passed in Run A but failed in Run B.
  - `improvement_cases`: List of `case_id`s that failed in Run A but passed in Run B.
  - `delta_latency_ms`: Change in average execution latency ($\text{AvgLatency}_B - \text{AvgLatency}_A$).

---

## 6. Creating and Running a New Dataset

### Step 1: Create Dataset via REST API
```bash
curl -X POST "http://localhost:8000/api/v1/evaluation/datasets" \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": "2",
    "name": "Sample Benchmark",
    "description": "Smoke test suite for calculator",
    "cases": [
      {
        "name": "add_test",
        "input": {"expression": "10 + 5"},
        "expected_output": {"result": 15.0},
        "assertion_type": "exact"
      },
      {
        "name": "zero_div_test",
        "input": {"expression": "5 / 0"},
        "expected_output": {"error_contains": "division by zero"},
        "assertion_type": "expect_error",
        "expect_error": true
      }
    ]
  }'
```

### Step 2: Validate Dataset Schema
```bash
curl -X POST "http://localhost:8000/api/v1/evaluation/datasets/{dataset_id}/validate"
```

### Step 3: Trigger an Evaluation Run
```bash
curl -X POST "http://localhost:8000/api/v1/evaluation/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "{dataset_id}",
    "tool_name": "calculator",
    "model_provider": "mock"
  }'
```

### Step 4: Export Results to CSV
```bash
curl -O -J "http://localhost:8000/api/v1/evaluation/runs/{run_id}/download"
```

---

## 7. Known Limitations & Best Practices

1. **Deterministic Assertions Only**: Evaluator scores are strictly grounded in deterministic programmatic checks (exact match, numeric tolerance, regex, JSON schema). They do not call non-deterministic LLM evaluators as ground truth.
2. **Tool Scope**: An evaluation run currently evaluates a designated target tool (or mock pipeline) across all cases in the dataset. Multi-tool workflows can be evaluated by targeting tools like `mock_tool` with composite payloads.
3. **Floating-point Comparisons**: Use floating point numbers carefully; the engine applies an absolute and relative tolerance of $10^{-5}$ (`math.isclose`), but large scale differences should use explicit min/max ranges via the `schema` assertion type.
