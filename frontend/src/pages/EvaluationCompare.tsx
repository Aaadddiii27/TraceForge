import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, GitCompare } from 'lucide-react';
import { clsx } from 'clsx';
import { useComparison, useRun } from '@/hooks/useApi';
import {
  Badge,
  Button,
  Card,
  CardHeader,
  CardTitle,
  ErrorState,
  Input,
  Label,
  LoadingState,
  StatCard,
} from '@/components/ui';

function pct(n: number | null) {
  if (n === null) return '—';
  return `${(n * 100).toFixed(1)}%`;
}
function delta(n: number | null) {
  if (n === null) return '—';
  const sign = n >= 0 ? '+' : '';
  return `${sign}${(n * 100).toFixed(1)}pp`;
}
function fmtms(n: number | null) {
  if (n === null) return '—';
  return `${n.toFixed(1)}ms`;
}

export default function EvaluationComparePage() {
  const { runAId, runBId } = useParams<{ runAId: string; runBId: string }>();
  const [threshold, setThreshold] = useState(0.05);

  const { data: comparison, isLoading, error } = useComparison(
    runAId!,
    runBId!,
    threshold,
    !!(runAId && runBId),
  );

  const { data: runA } = useRun(runAId!);
  const { data: runB } = useRun(runBId!);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-2">
        <Link to="/evaluations" className="flex items-center gap-1 text-sm text-slate-400 hover:text-slate-200">
          <ArrowLeft size={14} /> Evaluations
        </Link>
        <span className="text-slate-600">/</span>
        <span className="text-sm text-slate-300">Compare Runs</span>
      </div>

      <div className="flex items-center gap-3">
        <GitCompare size={22} className="text-violet-400" />
        <div>
          <h1 className="text-xl font-bold text-slate-100">Run Comparison</h1>
          <p className="text-xs text-slate-500 font-mono">{runAId?.slice(0, 10)} vs {runBId?.slice(0, 10)}</p>
        </div>
      </div>

      {/* Threshold control */}
      <Card className="max-w-sm">
        <Label htmlFor="thresh">Regression Threshold</Label>
        <div className="flex items-center gap-3">
          <Input
            id="thresh"
            type="number"
            min="0"
            max="1"
            step="0.01"
            value={threshold}
            onChange={e => setThreshold(parseFloat(e.target.value))}
            className="w-28"
          />
          <span className="text-xs text-slate-500">drop triggers regression alert</span>
        </div>
      </Card>

      {isLoading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message="Failed to load comparison" />
      ) : !comparison ? null : (
        <>
          {/* Regression alert */}
          {comparison.regression_detected && (
            <div className="flex items-center gap-3 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3">
              <span className="text-2xl">⚠️</span>
              <div>
                <p className="text-sm font-semibold text-rose-300">Regression Detected</p>
                <p className="text-xs text-slate-400">
                  Pass rate dropped by {delta(comparison.delta_pass_rate)} — exceeds {(threshold * 100).toFixed(0)}pp threshold.
                </p>
              </div>
            </div>
          )}
          {!comparison.regression_detected && (
            <div className="flex items-center gap-3 rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3">
              <span className="text-2xl">✅</span>
              <div>
                <p className="text-sm font-semibold text-emerald-300">No Regression Detected</p>
                <p className="text-xs text-slate-400">
                  Pass rate delta {delta(comparison.delta_pass_rate)} within acceptable threshold.
                </p>
              </div>
            </div>
          )}

          {/* Side-by-side metrics */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Run A */}
            <Card className="border-blue-500/30">
              <CardHeader>
                <CardTitle>Baseline (Run A)</CardTitle>
                <Link to={`/evaluations/runs/${comparison.run_a_id}`} className="text-xs text-blue-400 hover:underline">
                  View →
                </Link>
              </CardHeader>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500">Pass Rate</span>
                  <span className="font-bold text-blue-400">{pct(comparison.run_a_pass_rate)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Avg Latency</span>
                  <span className="text-slate-300">{fmtms(comparison.run_a_avg_latency_ms)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Total Cases</span>
                  <span className="text-slate-300">{runA?.total_cases ?? '—'}</span>
                </div>
              </div>
            </Card>

            {/* Run B */}
            <Card className={clsx(comparison.regression_detected ? 'border-rose-500/30' : 'border-emerald-500/30')}>
              <CardHeader>
                <CardTitle>Candidate (Run B)</CardTitle>
                <Link to={`/evaluations/runs/${comparison.run_b_id}`} className="text-xs text-blue-400 hover:underline">
                  View →
                </Link>
              </CardHeader>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500">Pass Rate</span>
                  <span className={clsx('font-bold', comparison.regression_detected ? 'text-rose-400' : 'text-emerald-400')}>
                    {pct(comparison.run_b_pass_rate)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Avg Latency</span>
                  <span className="text-slate-300">{fmtms(comparison.run_b_avg_latency_ms)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Total Cases</span>
                  <span className="text-slate-300">{runB?.total_cases ?? '—'}</span>
                </div>
              </div>
            </Card>
          </div>

          {/* Delta */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard
              label="Δ Pass Rate"
              value={delta(comparison.delta_pass_rate)}
              colorClass={comparison.delta_pass_rate !== null && comparison.delta_pass_rate < 0 ? 'text-rose-400' : 'text-emerald-400'}
            />
            <StatCard
              label="Δ Latency"
              value={comparison.delta_latency_ms !== null ? `${comparison.delta_latency_ms > 0 ? '+' : ''}${comparison.delta_latency_ms.toFixed(1)}ms` : '—'}
              colorClass="text-slate-300"
            />
            <StatCard
              label="Regressions"
              value={comparison.regression_cases.length}
              colorClass="text-rose-400"
            />
            <StatCard
              label="Improvements"
              value={comparison.improvement_cases.length}
              colorClass="text-emerald-400"
            />
          </div>

          {/* Case-level breakdown */}
          {(comparison.regression_cases.length > 0 || comparison.improvement_cases.length > 0) && (
            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader><CardTitle className="text-rose-400">Regressions ({comparison.regression_cases.length})</CardTitle></CardHeader>
                {comparison.regression_cases.length === 0 ? (
                  <p className="text-sm text-slate-500">None</p>
                ) : (
                  <ul className="space-y-1">
                    {comparison.regression_cases.map(id => (
                      <li key={id} className="font-mono text-xs text-slate-400 bg-rose-500/10 rounded px-2 py-1">{id.slice(0, 16)}…</li>
                    ))}
                  </ul>
                )}
              </Card>
              <Card>
                <CardHeader><CardTitle className="text-emerald-400">Improvements ({comparison.improvement_cases.length})</CardTitle></CardHeader>
                {comparison.improvement_cases.length === 0 ? (
                  <p className="text-sm text-slate-500">None</p>
                ) : (
                  <ul className="space-y-1">
                    {comparison.improvement_cases.map(id => (
                      <li key={id} className="font-mono text-xs text-slate-400 bg-emerald-500/10 rounded px-2 py-1">{id.slice(0, 16)}…</li>
                    ))}
                  </ul>
                )}
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  );
}
