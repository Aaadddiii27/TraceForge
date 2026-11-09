import { Link } from 'react-router-dom';
import { Activity, CheckCircle, Clock, Cpu, TrendingUp, XCircle, Zap } from 'lucide-react';
import { format } from 'date-fns';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useHealth, useReadiness, useRuns, useTasks } from '@/hooks/useApi';
import {
  Badge,
  Card,
  CardHeader,
  CardTitle,
  Dot,
  EmptyState,
  ErrorState,
  LoadingState,
  StatCard,
  statusBadge,
  Td,
  Table,
  Tr,
} from '@/components/ui';

function fmt(ms: number | null) {
  if (ms === null) return '—';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function pct(n: number | null) {
  if (n === null) return '—';
  return `${(n * 100).toFixed(1)}%`;
}

export default function OverviewPage() {
  const { data: health } = useHealth();
  const { data: readiness } = useReadiness();
  const { data: tasks, isLoading: tasksLoading, error: tasksError } = useTasks(1, 100);
  const { data: runs } = useRuns(1, 20);

  const taskList = tasks?.items ?? [];
  const completed = taskList.filter(t => t.status === 'completed').length;
  const failed = taskList.filter(t => t.status === 'failed').length;
  const successRate = taskList.length > 0 ? completed / taskList.length : null;
  const avgLatency = taskList.filter(t => t.duration_ms !== null).reduce((acc, t) => acc + (t.duration_ms ?? 0), 0) / (taskList.filter(t => t.duration_ms !== null).length || 1);

  // Build a simple time-series from last 10 tasks
  const chartData = [...taskList]
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
    .slice(-10)
    .map((t, i) => ({
      i: i + 1,
      ms: t.duration_ms ? Math.round(t.duration_ms) : 0,
      status: t.status,
    }));

  const latestRun = runs?.items?.[0];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Overview</h1>
        <p className="mt-1 text-sm text-slate-500">AI Runtime & Evaluation Platform</p>
      </div>

      {/* Health pills */}
      <div className="flex flex-wrap gap-2">
        <div className="flex items-center gap-2 rounded-full bg-surface px-3 py-1 text-xs border border-surface-border">
          <Dot color={health?.status === 'ok' ? 'green' : 'red'} />
          <span className="text-slate-300">Backend {health?.status ?? '…'}</span>
        </div>
        <div className="flex items-center gap-2 rounded-full bg-surface px-3 py-1 text-xs border border-surface-border">
          <Dot color={readiness?.database ? 'green' : 'red'} />
          <span className="text-slate-300">Database {readiness?.database ? 'ready' : readiness ? 'down' : '…'}</span>
        </div>
        <div className="flex items-center gap-2 rounded-full bg-surface px-3 py-1 text-xs border border-surface-border">
          <Dot color={readiness?.redis ? 'green' : 'yellow'} />
          <span className="text-slate-300">Redis {readiness?.redis ? 'ready' : readiness ? 'unavailable' : '…'}</span>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Total Executions"
          value={tasks?.total ?? '—'}
          icon={<Cpu size={18} />}
          colorClass="text-blue-400"
        />
        <StatCard
          label="Success Rate"
          value={pct(successRate)}
          sub={`${completed} of ${taskList.length}`}
          icon={<CheckCircle size={18} />}
          colorClass="text-emerald-400"
        />
        <StatCard
          label="Failed"
          value={failed}
          icon={<XCircle size={18} />}
          colorClass="text-rose-400"
        />
        <StatCard
          label="Avg Latency"
          value={taskList.length > 0 ? fmt(avgLatency) : '—'}
          icon={<Clock size={18} />}
          colorClass="text-cyan-400"
        />
      </div>

      {/* Charts + Eval */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Latency chart */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Execution Latency (last 10)</CardTitle>
            <TrendingUp size={14} className="text-slate-600" />
          </CardHeader>
          {tasksLoading ? (
            <LoadingState />
          ) : chartData.length === 0 ? (
            <EmptyState title="No executions yet" description="Submit a task to see latency data." icon={<Activity size={36} />} />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2d47" />
                <XAxis dataKey="i" tick={{ fill: '#64748b', fontSize: 11 }} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: '#111827', border: '1px solid #1f2d47', borderRadius: 8 }}
                  labelStyle={{ color: '#94a3b8' }}
                  itemStyle={{ color: '#3b82f6' }}
                  formatter={(v: number) => [`${v}ms`, 'Latency']}
                />
                <Line
                  type="monotone"
                  dataKey="ms"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ fill: '#3b82f6', r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Eval snapshot */}
        <Card>
          <CardHeader>
            <CardTitle>Latest Eval Run</CardTitle>
            <Zap size={14} className="text-slate-600" />
          </CardHeader>
          {latestRun ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">Status</span>
                {statusBadge(latestRun.status)}
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">Pass Rate</span>
                <span className={latestRun.pass_rate && latestRun.pass_rate > 0.9 ? 'text-emerald-400 font-bold' : 'text-amber-400 font-bold'}>
                  {pct(latestRun.pass_rate)}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">Cases</span>
                <span className="text-slate-300">{latestRun.passed_cases}/{latestRun.total_cases}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">p50</span>
                <span className="text-slate-300">{fmt(latestRun.latency_p50_ms)}</span>
              </div>
              <Link
                to={`/evaluations/runs/${latestRun.id}`}
                className="mt-2 block text-center text-xs text-blue-400 hover:text-blue-300"
              >
                View details →
              </Link>
            </div>
          ) : (
            <EmptyState title="No eval runs yet" description="Run an evaluation dataset." />
          )}
        </Card>
      </div>

      {/* Recent executions */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Executions</CardTitle>
          <Link to="/executions" className="text-xs text-blue-400 hover:text-blue-300">
            View all →
          </Link>
        </CardHeader>
        {tasksLoading ? (
          <LoadingState />
        ) : tasksError ? (
          <ErrorState message="Failed to load executions" />
        ) : taskList.length === 0 ? (
          <EmptyState title="No executions yet" description="Submit a task via the Executions page." icon={<Cpu size={36} />} />
        ) : (
          <Table headers={['ID', 'Tool', 'Status', 'Duration', 'Created']}>
            {[...taskList].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 8).map(t => (
              <Tr key={t.id} clickable onClick={() => { window.location.href = `/executions/${t.id}`; }}>
                <Td><span className="font-mono text-xs text-slate-400">{t.id.slice(0, 8)}…</span></Td>
                <Td>{(t.tool_ids as string[]).join(', ')}</Td>
                <Td>{statusBadge(t.status)}</Td>
                <Td>{fmt(t.duration_ms)}</Td>
                <Td className="text-slate-500">{format(new Date(t.created_at), 'MMM d, HH:mm')}</Td>
              </Tr>
            ))}
          </Table>
        )}
      </Card>
    </div>
  );
}
