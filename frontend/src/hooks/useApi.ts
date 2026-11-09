import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { evaluationApi, healthApi, tasksApi, toolsApi } from '@/api/client';
import type { EvaluationRunCreate, TaskCreate } from '@/types';

// ─── Query keys ───────────────────────────────────────────────────────────────

export const qk = {
  health: ['health'] as const,
  ready: ['ready'] as const,
  tasks: (page: number, size: number, status?: string) =>
    ['tasks', page, size, status] as const,
  task: (id: string) => ['task', id] as const,
  taskSteps: (id: string) => ['taskSteps', id] as const,
  tools: ['tools'] as const,
  tool: (name: string) => ['tool', name] as const,
  datasets: (page: number, size: number) => ['datasets', page, size] as const,
  dataset: (id: string) => ['dataset', id] as const,
  runs: (page: number, size: number) => ['runs', page, size] as const,
  run: (id: string) => ['run', id] as const,
  comparison: (a: string, b: string) => ['comparison', a, b] as const,
  benchmarkDataset: ['benchmarkDataset'] as const,
};

// ─── Health hooks ─────────────────────────────────────────────────────────────

export const useHealth = () =>
  useQuery({ queryKey: qk.health, queryFn: healthApi.get, refetchInterval: 30_000 });

export const useReadiness = () =>
  useQuery({ queryKey: qk.ready, queryFn: healthApi.ready, refetchInterval: 15_000 });

// ─── Task hooks ───────────────────────────────────────────────────────────────

export const useTasks = (page = 1, pageSize = 20, status?: string) =>
  useQuery({
    queryKey: qk.tasks(page, pageSize, status),
    queryFn: () => tasksApi.list(page, pageSize, status),
    refetchInterval: 10_000,
  });

export const useTask = (id: string) =>
  useQuery({
    queryKey: qk.task(id),
    queryFn: () => tasksApi.get(id),
    enabled: !!id,
  });

export const useSubmitTask = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TaskCreate) => tasksApi.submit(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
};

// ─── Tool hooks ───────────────────────────────────────────────────────────────

export const useTools = () =>
  useQuery({ queryKey: qk.tools, queryFn: toolsApi.list, staleTime: 60_000 });

export const useTool = (name: string) =>
  useQuery({
    queryKey: qk.tool(name),
    queryFn: () => toolsApi.get(name),
    enabled: !!name,
    staleTime: 60_000,
  });

// ─── Evaluation hooks ─────────────────────────────────────────────────────────

export const useDatasets = (page = 1, pageSize = 20) =>
  useQuery({
    queryKey: qk.datasets(page, pageSize),
    queryFn: () => evaluationApi.listDatasets(page, pageSize),
  });

export const useDataset = (id: string) =>
  useQuery({
    queryKey: qk.dataset(id),
    queryFn: () => evaluationApi.getDataset(id),
    enabled: !!id,
  });

export const useBenchmarkDataset = () =>
  useQuery({
    queryKey: qk.benchmarkDataset,
    queryFn: evaluationApi.getBenchmarkDataset,
    staleTime: 300_000,
    retry: 1,
  });

export const useRuns = (page = 1, pageSize = 20) =>
  useQuery({
    queryKey: qk.runs(page, pageSize),
    queryFn: () => evaluationApi.listRuns(page, pageSize),
    refetchInterval: 10_000,
  });

export const useRun = (id: string) =>
  useQuery({
    queryKey: qk.run(id),
    queryFn: () => evaluationApi.getRun(id),
    enabled: !!id,
  });

export const useComparison = (runAId: string, runBId: string, threshold: number, enabled: boolean) =>
  useQuery({
    queryKey: qk.comparison(runAId, runBId),
    queryFn: () => evaluationApi.compareRuns(runAId, runBId, threshold),
    enabled: enabled && !!runAId && !!runBId,
  });

export const useStartRun = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: EvaluationRunCreate) => evaluationApi.startRun(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['runs'] });
    },
  });
};

export const useRunBenchmark = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (toolName: string) => evaluationApi.runBenchmark(toolName),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['runs'] });
    },
  });
};
