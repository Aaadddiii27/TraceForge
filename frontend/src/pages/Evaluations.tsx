import type { FormEvent } from 'react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { format } from 'date-fns';
import { BarChart2, Play, Plus, RefreshCw } from 'lucide-react';
import { clsx } from 'clsx';
import {
  useBenchmarkDataset,
  useDatasets,
  useRunBenchmark,
  useRuns,
  useStartRun,
  useTools,
} from '@/hooks/useApi';
import { evaluationApi } from '@/api/client';
import {
  Badge,
  Button,
  Card,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  Input,
  Label,
  LoadingState,
  ProgressBar,
  Select,
  statusBadge,
  Td,
  Table,
  Tr,
} from '@/components/ui';

function pct(n: number | null) {
  if (n === null) return '—';
  return `${(n * 100).toFixed(1)}%`;
}

function fmt(ms: number | null) {
  if (ms === null) return '—';
  return `${Math.round(ms)}ms`;
}

function StartRunModal({
  datasetId,
  onClose,
}: {
  datasetId: string;
  onClose: () => void;
}) {
  const { data: tools } = useTools();
  const [toolName, setToolName] = useState('calculator');
  const [threshold, setThreshold] = useState('0.05');
  const [error, setError] = useState('');
  const startRun = useStartRun();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await startRun.mutateAsync({
        dataset_id: datasetId,
        tool_name: toolName,
        model_provider: 'mock',
        regression_threshold: parseFloat(threshold),
      });
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Run failed');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <Card className="w-full max-w-md border-blue-500/30">
        <CardHeader>
          <CardTitle>Start Evaluation Run</CardTitle>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-200 text-xl leading-none">×</button>
        </CardHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="tool">Tool to Evaluate</Label>
            <Select id="tool" value={toolName} onChange={e => setToolName(e.target.value)} className="w-full">
              {tools?.items.map(t => <option key={t.name} value={t.name}>{t.name}</option>)}
            </Select>
          </div>
          <div>
            <Label htmlFor="threshold">Regression Threshold</Label>
            <Input
              id="threshold"
              type="number"
              min="0"
              max="1"
              step="0.01"
              value={threshold}
              onChange={e => setThreshold(e.target.value)}
            />
            <p className="mt-1 text-xs text-slate-500">Drop in pass rate that triggers regression alert (0–1)</p>
          </div>
          {error && <p className="text-xs text-rose-400">{error}</p>}
          <div className="flex gap-3">
            <Button type="submit" loading={startRun.isPending} icon={<Play size={14} />}>
              Start Run
            </Button>
            <Button variant="secondary" type="button" onClick={onClose}>Cancel</Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

export default function EvaluationsPage() {
  const [activeTab, setActiveTab] = useState<'datasets' | 'runs'>('datasets');
  const [dsPage, setDsPage] = useState(1);
  const [runPage, setRunPage] = useState(1);
  const [runModalDatasetId, setRunModalDatasetId] = useState<string | null>(null);

  const { data: datasets, isLoading: dsLoading, error: dsError } = useDatasets(dsPage, 20);
  const { data: runs, isLoading: runsLoading, error: runsError } = useRuns(runPage, 20);
  const { data: benchmarkDs } = useBenchmarkDataset();
  const benchmarkMutation = useRunBenchmark();

  return (
    <div className="p-6 space-y-6">
      {runModalDatasetId && (
        <StartRunModal
          datasetId={runModalDatasetId}
          onClose={() => setRunModalDatasetId(null)}
        />
      )}

      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Evaluations</h1>
          <p className="mt-1 text-sm text-slate-500">Dataset management and evaluation run history</p>
        </div>
        <Button
          icon={<RefreshCw size={14} />}
          loading={benchmarkMutation.isPending}
          onClick={() => benchmarkMutation.mutate('calculator')}
          variant="secondary"
        >
          Run Benchmark
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-xl border border-surface-border bg-surface p-1 w-fit">
        {(['datasets', 'runs'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={clsx(
              'rounded-lg px-4 py-1.5 text-sm font-medium capitalize transition-all',
              activeTab === tab
                ? 'bg-blue-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200',
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === 'datasets' && (
        <div className="space-y-4">
          {/* Benchmark dataset pill */}
          {benchmarkDs && (
            <div className="flex items-center gap-3 rounded-xl border border-blue-500/30 bg-blue-500/5 px-4 py-3">
              <BarChart2 size={16} className="text-blue-400 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-blue-300">Built-in Benchmark</p>
                <p className="text-xs text-slate-500">{benchmarkDs.cases.length} cases • {benchmarkDs.name}</p>
              </div>
              <Button size="sm" onClick={() => benchmarkMutation.mutate('calculator')} loading={benchmarkMutation.isPending}>
                Run
              </Button>
            </div>
          )}

          {dsLoading ? (
            <LoadingState />
          ) : dsError ? (
            <ErrorState message="Failed to load datasets" />
          ) : (datasets?.items.length ?? 0) === 0 ? (
            <Card>
              <EmptyState
                title="No datasets yet"
                description="Create a dataset via the API or use the built-in benchmark."
                icon={<BarChart2 size={36} />}
              />
            </Card>
          ) : (
            <Card className="p-0">
              <Table headers={['Dataset', 'Cases', 'Created', 'Actions']}>
                {datasets!.items.map(ds => (
                  <Tr key={ds.id}>
                    <Td>
                      <Link to={`/evaluations/datasets/${ds.id}`} className="text-blue-400 hover:underline font-medium">
                        {ds.name}
                      </Link>
                      <p className="text-xs text-slate-500 mt-0.5 font-mono">{ds.id.slice(0, 10)}…</p>
                    </Td>
                    <Td>{ds.cases.length}</Td>
                    <Td className="text-slate-500 text-xs">{format(new Date(ds.created_at), 'MMM d, yyyy')}</Td>
                    <Td>
                      <Button
                        size="sm"
                        variant="secondary"
                        icon={<Play size={12} />}
                        onClick={() => setRunModalDatasetId(ds.id)}
                      >
                        Run
                      </Button>
                    </Td>
                  </Tr>
                ))}
              </Table>
            </Card>
          )}
        </div>
      )}

      {activeTab === 'runs' && (
        <div className="space-y-4">
          {runsLoading ? (
            <LoadingState />
          ) : runsError ? (
            <ErrorState message="Failed to load runs" />
          ) : (runs?.items.length ?? 0) === 0 ? (
            <Card>
              <EmptyState title="No evaluation runs yet" description="Run an evaluation dataset to see results." />
            </Card>
          ) : (
            <Card className="p-0">
              <Table headers={['Run ID', 'Status', 'Cases', 'Pass Rate', 'p50 Latency', 'Started', 'Compare']}>
                {runs!.items.map((run, i) => (
                  <Tr key={run.id} clickable>
                    <Td>
                      <Link to={`/evaluations/runs/${run.id}`} className="font-mono text-xs text-blue-400 hover:underline">
                        {run.id.slice(0, 10)}…
                      </Link>
                    </Td>
                    <Td>{statusBadge(run.status)}</Td>
                    <Td>{run.passed_cases}/{run.total_cases}</Td>
                    <Td>
                      <div className="flex items-center gap-2">
                        <span className={clsx('text-sm font-semibold', (run.pass_rate ?? 0) >= 0.9 ? 'text-emerald-400' : 'text-amber-400')}>
                          {pct(run.pass_rate)}
                        </span>
                        {run.total_cases > 0 && <ProgressBar value={run.pass_rate ?? 0} colorClass={(run.pass_rate ?? 0) >= 0.9 ? 'bg-emerald-500' : 'bg-amber-500'} />}
                      </div>
                    </Td>
                    <Td className="text-slate-400">{fmt(run.latency_p50_ms)}</Td>
                    <Td className="text-slate-500 text-xs">{run.started_at ? format(new Date(run.started_at), 'MMM d, HH:mm') : '—'}</Td>
                    <Td>
                      {i > 0 && (
                        <Link
                          to={`/evaluations/compare/${runs!.items[i - 1].id}/${run.id}`}
                          className="text-xs text-violet-400 hover:underline"
                        >
                          vs prev
                        </Link>
                      )}
                    </Td>
                  </Tr>
                ))}
              </Table>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
