import type {
  DatasetValidationResponse,
  EvaluationComparison,
  EvaluationDataset,
  EvaluationDatasetListResponse,
  EvaluationRun,
  EvaluationRunCreate,
  EvaluationRunListResponse,
  HealthResponse,
  ReadinessResponse,
  Task,
  TaskCreate,
  TaskListResponse,
  Tool,
  ToolListResponse,
} from '@/types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

class ApiClientError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiClientError';
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    let code = 'UNKNOWN_ERROR';
    let message = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) {
        const d = body.detail;
        if (typeof d === 'object' && d !== null) {
          code = d.code ?? code;
          message = d.message ?? message;
        } else if (typeof d === 'string') {
          message = d;
        }
      }
    } catch {
      /* ignore parse errors */
    }
    throw new ApiClientError(res.status, code, message);
  }

  if (res.status === 204) return undefined as unknown as T;
  return res.json() as Promise<T>;
}

function buildQuery(params: Record<string, string | number | boolean | undefined | null>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) q.set(k, String(v));
  }
  const s = q.toString();
  return s ? `?${s}` : '';
}

// ─── Health ───────────────────────────────────────────────────────────────────

export const healthApi = {
  get: () => request<HealthResponse>('/health'),
  ready: () => request<ReadinessResponse>('/health/ready'),
};

// ─── Tasks ────────────────────────────────────────────────────────────────────

export const tasksApi = {
  list: (page = 1, pageSize = 20, status?: string) =>
    request<TaskListResponse>(
      `/tasks${buildQuery({ page, page_size: pageSize, status })}`,
    ),

  get: (id: string) => request<Task>(`/tasks/${id}`),

  submit: (data: TaskCreate) =>
    request<Task>('/tasks', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getSteps: (id: string) =>
    request<Task['steps']>(`/tasks/${id}/steps`),
};

// ─── Tools ───────────────────────────────────────────────────────────────────

export const toolsApi = {
  list: () => request<ToolListResponse>('/tools'),
  get: (name: string) => request<Tool>(`/tools/${name}`),
};

// ─── Evaluation ───────────────────────────────────────────────────────────────

export const evaluationApi = {
  // Datasets
  listDatasets: (page = 1, pageSize = 20) =>
    request<EvaluationDatasetListResponse>(
      `/evaluation/datasets${buildQuery({ page, page_size: pageSize })}`,
    ),

  getDataset: (id: string) =>
    request<EvaluationDataset>(`/evaluation/datasets/${id}`),

  createDataset: (data: {
    name: string;
    description?: string;
    cases?: unknown[];
    schema_version?: string;
  }) =>
    request<EvaluationDataset>('/evaluation/datasets', {
      method: 'POST',
      body: JSON.stringify({ schema_version: '2', ...data }),
    }),

  validateDataset: (id: string) =>
    request<DatasetValidationResponse>(`/evaluation/datasets/${id}/validate`, {
      method: 'POST',
    }),

  // Benchmark
  getBenchmarkDataset: () =>
    request<EvaluationDataset>('/evaluation/benchmark/dataset'),

  runBenchmark: (toolName = 'calculator') =>
    request<EvaluationRun>(
      `/evaluation/benchmark${buildQuery({ tool_name: toolName })}`,
      { method: 'POST' },
    ),

  // Runs
  listRuns: (page = 1, pageSize = 20) =>
    request<EvaluationRunListResponse>(
      `/evaluation/runs${buildQuery({ page, page_size: pageSize })}`,
    ),

  getRun: (id: string) => request<EvaluationRun>(`/evaluation/runs/${id}`),

  startRun: (data: EvaluationRunCreate) =>
    request<EvaluationRun>('/evaluation/runs', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  compareRuns: (runAId: string, runBId: string, threshold = 0.05) =>
    request<EvaluationComparison>(
      `/evaluation/runs/${runAId}/compare/${runBId}${buildQuery({ regression_threshold: threshold })}`,
    ),

  downloadCSV: (runId: string) =>
    `${BASE_URL}/evaluation/runs/${runId}/download`,
};

export { ApiClientError };
