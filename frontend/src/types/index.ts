// ─── Core Types matching backend schemas ─────────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
}

export interface ReadinessResponse {
  ready: boolean;
  database: boolean;
  redis: boolean;
  details: Record<string, string>;
}

// ─── Task Types ───────────────────────────────────────────────────────────────

export interface ExecutionStep {
  id: string;
  task_id: string;
  step_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'timed_out';
  attempt_number: number;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  error: string | null;
}

export interface Task {
  id: string;
  request_id: string | null;
  idempotency_key: string | null;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'timed_out';
  model_provider: string;
  tool_ids: string[];
  input_payload: Record<string, unknown> | null;
  output_payload: Record<string, unknown> | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  error_message: string | null;
  retry_count: number;
  token_usage_input: number | null;
  token_usage_output: number | null;
  estimated_cost_usd: number | null;
  steps: ExecutionStep[];
}

export interface TaskCreate {
  tool_ids: string[];
  input_payload: Record<string, unknown>;
  model_provider?: string;
  idempotency_key?: string;
  request_id?: string;
}

export interface TaskListResponse {
  items: Task[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ─── Tool Types ───────────────────────────────────────────────────────────────

export interface Tool {
  id: string;
  name: string;
  description: string;
  version: string;
  enabled: boolean;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  permission_level: string;
  timeout_seconds: number;
}

export interface ToolListResponse {
  items: Tool[];
  total: number;
}

// ─── Evaluation Types ─────────────────────────────────────────────────────────

export interface EvaluationCase {
  id: string;
  dataset_id: string;
  name: string | null;
  input: Record<string, unknown>;
  expected_output: Record<string, unknown>;
  tags: string[];
  assertion_type: string;
  timeout_ms: number | null;
  expect_error: boolean;
  created_at: string;
}

export interface EvaluationDataset {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  cases: EvaluationCase[];
}

export interface EvaluationDatasetListResponse {
  items: EvaluationDataset[];
  total: number;
}

export interface EvaluationResult {
  id: string;
  run_id: string;
  case_id: string;
  actual_output: Record<string, unknown> | null;
  passed: boolean;
  assertions: Record<string, unknown>;
  latency_ms: number | null;
  error: string | null;
}

export interface EvaluationRun {
  id: string;
  dataset_id: string;
  runtime_version: string;
  model_provider: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  config: Record<string, unknown>;
  started_at: string | null;
  finished_at: string | null;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  errored_cases: number;
  timed_out_cases: number;
  pass_rate: number | null;
  error_rate: number | null;
  timeout_rate: number | null;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  latency_p99_ms: number | null;
  results: EvaluationResult[];
}

export interface EvaluationRunListResponse {
  items: EvaluationRun[];
  total: number;
}

export interface EvaluationRunCreate {
  dataset_id: string;
  tool_name: string;
  model_provider?: string;
  regression_threshold?: number;
}

export interface EvaluationComparison {
  run_a_id: string;
  run_b_id: string;
  run_a_pass_rate: number | null;
  run_b_pass_rate: number | null;
  delta_pass_rate: number | null;
  run_a_avg_latency_ms: number | null;
  run_b_avg_latency_ms: number | null;
  delta_latency_ms: number | null;
  regression_cases: string[];
  improvement_cases: string[];
  regression_detected: boolean;
  regression_threshold: number;
}

export interface DatasetValidationResponse {
  dataset_id: string;
  total_cases: number;
  valid_cases: number;
  invalid_cases: number;
  errors: Array<{
    case_index: number;
    case_name: string | null;
    valid: boolean;
    errors: string[];
  }>;
  is_valid: boolean;
}

// ─── API Error ────────────────────────────────────────────────────────────────

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}
