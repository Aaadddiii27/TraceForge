import { useState } from 'react';
import { clsx } from 'clsx';
import { ChevronDown, ChevronRight, Wrench, Shield, Clock } from 'lucide-react';
import { useTool, useTools } from '@/hooks/useApi';
import {
  Badge,
  Card,
  CardHeader,
  CardTitle,
  CodeBlock,
  Dot,
  EmptyState,
  ErrorState,
  LoadingState,
  StatCard,
} from '@/components/ui';

function ToolDetail({ name }: { name: string }) {
  const { data: tool, isLoading, error } = useTool(name);
  if (isLoading) return <LoadingState />;
  if (error || !tool) return <ErrorState message="Tool not found" />;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-lg font-bold text-slate-100">{tool.name}</span>
        <Badge variant={tool.enabled ? 'success' : 'neutral'}>{tool.enabled ? 'enabled' : 'disabled'}</Badge>
        <Badge variant="info">v{tool.version}</Badge>
        <Badge variant="neutral">{tool.permission_level}</Badge>
      </div>
      <p className="text-sm text-slate-400">{tool.description}</p>

      <div className="grid grid-cols-2 gap-4">
        <StatCard label="Timeout" value={`${tool.timeout_seconds}s`} icon={<Clock size={16} />} colorClass="text-cyan-400" />
        <StatCard label="Permission" value={tool.permission_level} icon={<Shield size={16} />} colorClass="text-violet-400" />
      </div>

      <div>
        <p className="text-xs font-semibold uppercase text-slate-500 mb-2">Input Schema</p>
        <CodeBlock value={tool.input_schema} />
      </div>
      <div>
        <p className="text-xs font-semibold uppercase text-slate-500 mb-2">Output Schema</p>
        <CodeBlock value={tool.output_schema} />
      </div>
    </div>
  );
}

export default function ToolRegistryPage() {
  const { data: tools, isLoading, error } = useTools();
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Tool Registry</h1>
        <p className="mt-1 text-sm text-slate-500">Available deterministic execution tools</p>
      </div>

      {isLoading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message="Failed to load tools" />
      ) : (tools?.items.length ?? 0) === 0 ? (
        <EmptyState title="No tools registered" icon={<Wrench size={36} />} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Tool list */}
          <div className="space-y-2 lg:col-span-1">
            {tools!.items.map(tool => (
              <button
                key={tool.name}
                onClick={() => setSelected(tool.name === selected ? null : tool.name)}
                className={clsx(
                  'w-full text-left rounded-xl border p-4 transition-all',
                  selected === tool.name
                    ? 'border-blue-500/50 bg-blue-500/10'
                    : 'border-surface-border bg-surface hover:bg-surface-elevated',
                )}
              >
                <div className="flex items-center gap-3">
                  <div className={clsx('rounded-lg p-2', tool.enabled ? 'bg-emerald-500/10' : 'bg-slate-500/10')}>
                    <Wrench size={16} className={tool.enabled ? 'text-emerald-400' : 'text-slate-500'} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-200">{tool.name}</p>
                    <p className="text-xs text-slate-500 truncate">{tool.description.slice(0, 50)}…</p>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Dot color={tool.enabled ? 'green' : 'gray'} />
                    {selected === tool.name
                      ? <ChevronDown size={14} className="text-slate-500" />
                      : <ChevronRight size={14} className="text-slate-500" />}
                  </div>
                </div>
              </button>
            ))}
          </div>

          {/* Detail panel */}
          <div className="lg:col-span-2">
            {selected ? (
              <Card>
                <ToolDetail name={selected} />
              </Card>
            ) : (
              <Card>
                <EmptyState
                  title="Select a tool to view details"
                  description="Click on a tool in the list to see its schema, timeout, and configuration."
                  icon={<Wrench size={36} />}
                />
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
