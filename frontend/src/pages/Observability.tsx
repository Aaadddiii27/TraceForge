import { useTasks, useRuns } from '@/hooks/useApi';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  PieChart,
  Pie,
} from 'recharts';
import { Card, CardHeader, CardTitle, EmptyState, LoadingState, StatCard } from '@/components/ui';
import { BarChart2 } from 'lucide-react';

const STATUS_COLORS: Record<string, string> = {
  completed: '#10b981',
  failed: '#f43f5e',
  timed_out: '#f59e0b',
  running: '#3b82f6',
  pending: '#64748b',
};

function fmt(ms: number | null) {
  if (ms === null) return '—';
  return `${Math.round(ms)}ms`;
}

export default function ObservabilityPage() {
  const { data: tasks, isLoading } = useTasks(1, 200);
  const { data: runs } = useRuns(1, 50);

  const taskList = tasks?.items ?? [];
  const runList = runs?.items ?? [];

  // Status distribution
  const statusCounts = Object.entries(
    taskList.reduce<Record<string, number>>((acc, t) => {
      acc[t.status] = (acc[t.status] ?? 0) + 1;
      return acc;
    }, {}),
  ).map(([name, value]) => ({ name, value }));

  // Latency histogram bins
  const latencies = taskList.filter(t => t.duration_ms !== null).map(t => t.duration_ms!);
  const bins = [0, 10, 50, 100, 250, 500, 1000, Infinity];
  const labels = ['<10ms', '10-50', '50-100', '100-250', '250-500', '500-1s', '>1s'];
  const latencyBins = labels.map((label, i) => ({
    range: label,
    count: latencies.filter(v => v >= bins[i] && v < bins[i + 1]).length,
  }));

  // Tool usage
  const toolCounts = Object.entries(
    taskList.reduce<Record<string, number>>((acc, t) => {
      (t.tool_ids as string[]).forEach(tool => {
        acc[tool] = (acc[tool] ?? 0) + 1;
      });
      return acc;
    }, {}),
  ).map(([tool, count]) => ({ tool, count }));

  // Eval pass rates over time
  const evalSeries = runList
    .filter(r => r.pass_rate !== null)
    .slice(-10)
    .map((r, i) => ({
      i: i + 1,
      passRate: r.pass_rate !== null ? +(r.pass_rate * 100).toFixed(1) : null,
    }));

  const avgLatency = latencies.length > 0
    ? latencies.reduce((a, b) => a + b, 0) / latencies.length
    : null;
  const p95 = latencies.length > 0
    ? latencies.sort((a, b) => a - b)[Math.floor(latencies.length * 0.95)]
    : null;

  if (isLoading) return <div className="p-6"><LoadingState /></div>;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Observability</h1>
        <p className="mt-1 text-sm text-slate-500">Request volume, latency, and error distribution</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Total Tasks" value={taskList.length} colorClass="text-blue-400" />
        <StatCard label="Success Rate" value={
          taskList.length > 0
            ? `${(taskList.filter(t => t.status === 'completed').length / taskList.length * 100).toFixed(1)}%`
            : '—'
        } colorClass="text-emerald-400" />
        <StatCard label="Avg Latency" value={fmt(avgLatency)} colorClass="text-cyan-400" />
        <StatCard label="p95 Latency" value={fmt(p95 ?? null)} colorClass="text-violet-400" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Status distribution pie */}
        <Card>
          <CardHeader><CardTitle>Execution Status Distribution</CardTitle></CardHeader>
          {statusCounts.length === 0 ? (
            <EmptyState title="No data yet" icon={<BarChart2 size={36} />} />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={statusCounts}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {statusCounts.map(entry => (
                    <Cell key={entry.name} fill={STATUS_COLORS[entry.name] ?? '#64748b'} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#111827', border: '1px solid #1f2d47', borderRadius: 8 }}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Latency histogram */}
        <Card>
          <CardHeader><CardTitle>Latency Distribution</CardTitle></CardHeader>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={latencyBins} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2d47" />
              <XAxis dataKey="range" tick={{ fill: '#64748b', fontSize: 10 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #1f2d47', borderRadius: 8 }}
                labelStyle={{ color: '#94a3b8' }}
              />
              <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Tool usage */}
        <Card>
          <CardHeader><CardTitle>Tool Invocations</CardTitle></CardHeader>
          {toolCounts.length === 0 ? (
            <EmptyState title="No tool executions yet" />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={toolCounts} layout="vertical" margin={{ top: 4, right: 20, bottom: 0, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2d47" horizontal={false} />
                <XAxis type="number" tick={{ fill: '#64748b', fontSize: 10 }} />
                <YAxis dataKey="tool" type="category" tick={{ fill: '#64748b', fontSize: 10 }} width={90} />
                <Tooltip
                  contentStyle={{ background: '#111827', border: '1px solid #1f2d47', borderRadius: 8 }}
                />
                <Bar dataKey="count" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Eval pass rate over time */}
        <Card>
          <CardHeader><CardTitle>Evaluation Pass Rate Trend</CardTitle></CardHeader>
          {evalSeries.length === 0 ? (
            <EmptyState title="No evaluation runs yet" />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={evalSeries} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
                <defs>
                  <linearGradient id="passGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2d47" />
                <XAxis dataKey="i" tick={{ fill: '#64748b', fontSize: 10 }} />
                <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 10 }} unit="%" />
                <Tooltip
                  contentStyle={{ background: '#111827', border: '1px solid #1f2d47', borderRadius: 8 }}
                  formatter={(v: number) => [`${v}%`, 'Pass Rate']}
                />
                <Area
                  type="monotone"
                  dataKey="passRate"
                  stroke="#10b981"
                  strokeWidth={2}
                  fill="url(#passGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>
    </div>
  );
}
