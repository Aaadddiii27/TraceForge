import { Link, useParams } from 'react-router-dom';
import { format } from 'date-fns';
import { ArrowLeft, ChevronDown, ChevronRight, Clock, RotateCw } from 'lucide-react';
import { useState } from 'react';
import { clsx } from 'clsx';
import { useTask } from '@/hooks/useApi';
import {
  Badge,
  Card,
  CardHeader,
  CardTitle,
  CodeBlock,
  Divider,
  ErrorState,
  LoadingState,
  statusBadge,
  StatCard,
} from '@/components/ui';
import type { ExecutionStep } from '@/types';

function fmt(ms: number | null) {
  if (ms === null) return '—';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function StepRow({ step }: { step: ExecutionStep }) {
  const [open, setOpen] = useState(false);
  const statusColors: Record<string, string> = {
    completed: 'border-emerald-500/50 bg-emerald-500/5',
    failed:    'border-rose-500/50 bg-rose-500/5',
    timed_out: 'border-amber-500/50 bg-amber-500/5',
    running:   'border-blue-500/50 bg-blue-500/5',
    pending:   'border-slate-500/50 bg-slate-500/5',
  };

  return (
    <div className={clsx('rounded-lg border p-3', statusColors[step.status] ?? statusColors.pending)}>
      <div
        className="flex cursor-pointer items-center gap-3"
        onClick={() => setOpen(o => !o)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-sm text-slate-200">{step.step_name}</span>
            {statusBadge(step.status)}
            {step.attempt_number > 1 && (
              <Badge variant="warning">
                <RotateCw size={10} className="mr-1" />
                Attempt {step.attempt_number}
              </Badge>
            )}
          </div>
          <div className="mt-1 flex gap-4 text-xs text-slate-500">
            <span><Clock size={10} className="inline mr-1" />{fmt(step.duration_ms)}</span>
            {step.started_at && (
              <span>{format(new Date(step.started_at), 'HH:mm:ss.SSS')}</span>
            )}
          </div>
        </div>
        {open ? <ChevronDown size={14} className="shrink-0 text-slate-500" /> : <ChevronRight size={14} className="shrink-0 text-slate-500" />}
      </div>

      {open && (
        <div className="mt-3 space-y-3 border-t border-white/5 pt-3">
          {step.error && (
            <div>
              <p className="text-xs font-semibold uppercase text-rose-400 mb-1">Error</p>
              <p className="text-xs text-rose-300 font-mono bg-rose-500/10 rounded p-2">{step.error}</p>
            </div>
          )}
          {step.input && (
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500 mb-1">Input</p>
              <CodeBlock value={step.input} />
            </div>
          )}
          {step.output && (
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500 mb-1">Output</p>
              <CodeBlock value={step.output} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ExecutionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: task, isLoading, error } = useTask(id!);

  if (isLoading) return <div className="p-6"><LoadingState message="Loading execution…" /></div>;
  if (error || !task) return <div className="p-6"><ErrorState message="Execution not found" /></div>;

  const durationFormatted = task.duration_ms !== null ? fmt(task.duration_ms) : '—';

  return (
    <div className="p-6 space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2">
        <Link to="/executions" className="flex items-center gap-1 text-sm text-slate-400 hover:text-slate-200">
          <ArrowLeft size={14} />
          Executions
        </Link>
        <span className="text-slate-600">/</span>
        <span className="font-mono text-sm text-slate-300">{task.id.slice(0, 12)}…</span>
      </div>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-slate-100">Execution Trace</h1>
            {statusBadge(task.status)}
          </div>
          <p className="mt-1 font-mono text-xs text-slate-500">{task.id}</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Duration" value={durationFormatted} colorClass="text-cyan-400" />
        <StatCard label="Steps" value={task.steps.length} colorClass="text-blue-400" />
        <StatCard label="Retries" value={task.retry_count} colorClass={task.retry_count > 0 ? 'text-amber-400' : 'text-slate-400'} />
        <StatCard label="Provider" value={task.model_provider} colorClass="text-violet-400" />
      </div>

      {/* Metadata */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Execution Metadata</CardTitle></CardHeader>
          <dl className="space-y-2.5 text-sm">
            {[
              ['Tool(s)', (task.tool_ids as string[]).join(', ')],
              ['Provider', task.model_provider],
              ['Created', task.created_at ? format(new Date(task.created_at), 'PPpp') : '—'],
              ['Started', task.started_at ? format(new Date(task.started_at), 'PPpp') : '—'],
              ['Finished', task.finished_at ? format(new Date(task.finished_at), 'PPpp') : '—'],
              ['Request ID', task.request_id ?? '—'],
              ['Idempotency Key', task.idempotency_key ?? '—'],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between gap-4">
                <dt className="text-slate-500 shrink-0">{k}</dt>
                <dd className="text-slate-300 font-mono text-xs text-right break-all">{v}</dd>
              </div>
            ))}
            {task.error_message && (
              <div>
                <dt className="text-rose-400 text-xs font-semibold uppercase mb-1">Error</dt>
                <dd className="rounded bg-rose-500/10 p-2 font-mono text-xs text-rose-300">{task.error_message}</dd>
              </div>
            )}
          </dl>
        </Card>

        <Card>
          <CardHeader><CardTitle>Input / Output</CardTitle></CardHeader>
          <div className="space-y-3">
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500 mb-1">Input</p>
              <CodeBlock value={task.input_payload} />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500 mb-1">Output</p>
              <CodeBlock value={task.output_payload} />
            </div>
          </div>
        </Card>
      </div>

      {/* Steps Timeline */}
      <Card>
        <CardHeader>
          <CardTitle>Execution Steps</CardTitle>
          <span className="text-xs text-slate-500">{task.steps.length} step(s)</span>
        </CardHeader>
        {task.steps.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-8">No steps recorded.</p>
        ) : (
          <div className="space-y-3">
            {task.steps.map(step => (
              <StepRow key={step.id} step={step} />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
