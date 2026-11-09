import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Download } from 'lucide-react';
import { clsx } from 'clsx';
import { useRun } from '@/hooks/useApi';
import { evaluationApi } from '@/api/client';
import {
  Badge,
  Button,
  Card,
  CardHeader,
  CardTitle,
  CodeBlock,
  EmptyState,
  ErrorState,
  LoadingState,
  ProgressBar,
  StatCard,
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
  return `${ms.toFixed(1)}ms`;
}

export default function EvaluationRunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: run, isLoading, error } = useRun(id!);

  if (isLoading) return <div className="p-6"><LoadingState /></div>;
  if (error || !run) return <div className="p-6"><ErrorState message="Run not found" /></div>;

  const passColor = (run.pass_rate ?? 0) >= 0.9 ? 'text-emerald-400' : (run.pass_rate ?? 0) >= 0.7 ? 'text-amber-400' : 'text-rose-400';

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-2">
        <Link to="/evaluations" className="flex items-center gap-1 text-sm text-slate-400 hover:text-slate-200">
          <ArrowLeft size={14} /> Evaluations
        </Link>
        <span className="text-slate-600">/</span>
        <span className="font-mono text-sm text-slate-300">{run.id.slice(0, 12)}…</span>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-slate-100">Evaluation Run</h1>
            {statusBadge(run.status)}
          </div>
          <p className="mt-1 font-mono text-xs text-slate-500">{run.id}</p>
        </div>
        <a href={evaluationApi.downloadCSV(run.id)} download>
          <Button variant="secondary" icon={<Download size={14} />}>
            Download CSV
          </Button>
        </a>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <StatCard label="Pass Rate" value={pct(run.pass_rate)} colorClass={passColor} />
        <StatCard label="Passed" value={run.passed_cases} colorClass="text-emerald-400" />
        <StatCard label="Failed" value={run.failed_cases} colorClass="text-rose-400" />
        <StatCard label="Errored" value={run.errored_cases} colorClass="text-amber-400" />
        <StatCard label="Timed Out" value={run.timed_out_cases} colorClass="text-violet-400" />
      </div>

      {/* Latency */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="p50 Latency" value={fmt(run.latency_p50_ms)} colorClass="text-cyan-400" />
        <StatCard label="p95 Latency" value={fmt(run.latency_p95_ms)} colorClass="text-cyan-400" />
        <StatCard label="p99 Latency" value={fmt(run.latency_p99_ms)} colorClass="text-cyan-400" />
      </div>

      {/* Meta */}
      <Card>
        <CardHeader><CardTitle>Run Metadata</CardTitle></CardHeader>
        <dl className="grid grid-cols-2 gap-3 text-sm lg:grid-cols-4">
          {[
            ['Provider', run.model_provider],
            ['Runtime', run.runtime_version],
            ['Dataset ID', run.dataset_id.slice(0, 12) + '…'],
            ['Error Rate', pct(run.error_rate)],
          ].map(([k, v]) => (
            <div key={k}>
              <dt className="text-xs text-slate-500">{k}</dt>
              <dd className="text-slate-200 font-mono">{v}</dd>
            </div>
          ))}
        </dl>
      </Card>

      {/* Results table */}
      <Card className="p-0">
        <div className="px-5 py-4 border-b border-surface-border flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200">Case Results</h3>
          <span className="text-xs text-slate-500">{run.results.length} cases</span>
        </div>
        {run.results.length === 0 ? (
          <EmptyState title="No results recorded" />
        ) : (
          <Table headers={['Case ID', 'Assertion', 'Passed', 'Latency', 'Error']}>
            {run.results.map(r => (
              <Tr key={r.id}>
                <Td><span className="font-mono text-xs">{r.case_id.slice(0, 10)}…</span></Td>
                <Td><Badge variant="neutral">{r.assertions?.assertion_type as string ?? '—'}</Badge></Td>
                <Td>
                  {r.passed
                    ? <span className="text-emerald-400 font-semibold">✓</span>
                    : <span className="text-rose-400 font-semibold">✗</span>}
                </Td>
                <Td>{fmt(r.latency_ms)}</Td>
                <Td>
                  {r.error
                    ? <span className="text-xs text-rose-400 font-mono truncate max-w-xs block" title={r.error}>{r.error}</span>
                    : <span className="text-slate-600">—</span>}
                </Td>
              </Tr>
            ))}
          </Table>
        )}
      </Card>
    </div>
  );
}
