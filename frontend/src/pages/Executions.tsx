import type { FormEvent } from 'react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { format } from 'date-fns';
import { Play, Search, Filter } from 'lucide-react';
import { useSubmitTask, useTasks, useTools } from '@/hooks/useApi';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  Input,
  Label,
  LoadingState,
  Select,
  statusBadge,
  Td,
  Table,
  Textarea,
  Tr,
} from '@/components/ui';

function fmt(ms: number | null) {
  if (ms === null) return '—';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export default function ExecutionsPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');

  // Submit form
  const [toolId, setToolId] = useState('calculator');
  const [inputJson, setInputJson] = useState('{\n  "expression": "2 + 2"\n}');
  const [jsonError, setJsonError] = useState('');
  const [showForm, setShowForm] = useState(false);

  const { data: tasks, isLoading, error } = useTasks(page, 20, statusFilter || undefined);
  const { data: tools } = useTools();
  const submitMutation = useSubmitTask();

  const filtered = (tasks?.items ?? []).filter(t =>
    !search || t.id.includes(search) || (t.tool_ids as string[]).some(id => id.includes(search))
  );

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setJsonError('');
    let payload: Record<string, unknown>;
    try {
      payload = JSON.parse(inputJson);
    } catch {
      setJsonError('Invalid JSON');
      return;
    }
    try {
      await submitMutation.mutateAsync({
        tool_ids: [toolId],
        input_payload: payload,
        model_provider: 'mock',
      });
      setShowForm(false);
    } catch (e: unknown) {
      setJsonError(e instanceof Error ? e.message : 'Submission failed');
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Executions</h1>
          <p className="mt-1 text-sm text-slate-500">Task execution history and traces</p>
        </div>
        <Button icon={<Play size={14} />} onClick={() => setShowForm(v => !v)}>
          New Task
        </Button>
      </div>

      {/* Submit Form */}
      {showForm && (
        <Card className="border-blue-500/30 bg-surface/80">
          <CardHeader>
            <CardTitle>Submit Task</CardTitle>
            <button onClick={() => setShowForm(false)} className="text-slate-500 hover:text-slate-300 text-lg leading-none">×</button>
          </CardHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="tool">Tool</Label>
              <Select
                id="tool"
                value={toolId}
                onChange={e => setToolId(e.target.value)}
              >
                {tools?.items.map(t => (
                  <option key={t.name} value={t.name}>{t.name}</option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="payload">Input Payload (JSON)</Label>
              <Textarea
                id="payload"
                value={inputJson}
                onChange={e => { setInputJson(e.target.value); setJsonError(''); }}
                rows={5}
              />
              {jsonError && <p className="mt-1 text-xs text-rose-400">{jsonError}</p>}
            </div>
            <div className="flex gap-3">
              <Button type="submit" loading={submitMutation.isPending}>
                Execute
              </Button>
              <Button variant="secondary" type="button" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <Input
            placeholder="Search by ID or tool…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}>
          <option value="">All statuses</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="running">Running</option>
          <option value="pending">Pending</option>
          <option value="timed_out">Timed Out</option>
        </Select>
      </div>

      {/* Table */}
      {isLoading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message="Failed to load executions" />
      ) : filtered.length === 0 ? (
        <Card>
          <EmptyState title="No executions found" description="Submit a task to see executions." icon={<Play size={36} />} />
        </Card>
      ) : (
        <Card className="p-0">
          <Table headers={['Execution ID', 'Tool(s)', 'Status', 'Provider', 'Duration', 'Retries', 'Created']}>
            {filtered.map(t => (
              <Tr key={t.id} clickable>
                <Td>
                  <Link to={`/executions/${t.id}`} className="font-mono text-xs text-blue-400 hover:underline">
                    {t.id.slice(0, 12)}…
                  </Link>
                </Td>
                <Td>{(t.tool_ids as string[]).join(', ')}</Td>
                <Td>{statusBadge(t.status)}</Td>
                <Td className="text-slate-500 text-xs">{t.model_provider}</Td>
                <Td>{fmt(t.duration_ms)}</Td>
                <Td>{t.retry_count > 0 ? <span className="text-amber-400">{t.retry_count}</span> : '0'}</Td>
                <Td className="text-slate-500 text-xs">{format(new Date(t.created_at), 'MMM d, HH:mm:ss')}</Td>
              </Tr>
            ))}
          </Table>
          {/* Pagination */}
          {tasks && tasks.pages > 1 && (
            <div className="flex items-center justify-between border-t border-surface-border px-4 py-3">
              <span className="text-xs text-slate-500">
                Showing {(page - 1) * 20 + 1}–{Math.min(page * 20, tasks.total)} of {tasks.total}
              </span>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>
                  Prev
                </Button>
                <Button variant="secondary" size="sm" disabled={page === tasks.pages} onClick={() => setPage(p => p + 1)}>
                  Next
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
