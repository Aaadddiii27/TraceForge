import { useHealth, useReadiness } from '@/hooks/useApi';
import { format } from 'date-fns';
import { Card, CardHeader, CardTitle, Dot, ErrorState, LoadingState, StatCard } from '@/components/ui';
import { Database, Radio, Server, Zap } from 'lucide-react';

function StatusRow({ label, ok, detail }: { label: string; ok: boolean | undefined; detail?: string }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-surface-border last:border-0">
      <div className="flex items-center gap-3">
        <Dot color={ok === undefined ? 'gray' : ok ? 'green' : 'red'} />
        <span className="text-sm text-slate-200">{label}</span>
      </div>
      <div className="text-right">
        <span className={ok ? 'text-xs text-emerald-400' : ok === false ? 'text-xs text-rose-400' : 'text-xs text-slate-500'}>
          {ok === undefined ? 'checking…' : ok ? 'healthy' : 'unavailable'}
        </span>
        {detail && <p className="text-xs text-slate-600 mt-0.5">{detail}</p>}
      </div>
    </div>
  );
}

export default function HealthPage() {
  const { data: health, isLoading: healthLoading, error: healthError } = useHealth();
  const { data: readiness, isLoading: readyLoading } = useReadiness();

  const isLoading = healthLoading || readyLoading;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">System Health</h1>
        <p className="mt-1 text-sm text-slate-500">Service status, database, and dependency health</p>
      </div>

      {isLoading ? (
        <LoadingState message="Checking services…" />
      ) : healthError ? (
        <ErrorState message="Unable to reach backend" />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard
              label="Backend"
              value={health?.status === 'ok' ? 'Operational' : 'Degraded'}
              icon={<Server size={18} />}
              colorClass={health?.status === 'ok' ? 'text-emerald-400' : 'text-rose-400'}
            />
            <StatCard
              label="Database"
              value={readiness?.database ? 'Connected' : 'Disconnected'}
              icon={<Database size={18} />}
              colorClass={readiness?.database ? 'text-emerald-400' : 'text-rose-400'}
            />
            <StatCard
              label="Redis"
              value={readiness?.redis ? 'Connected' : 'Unavailable'}
              icon={<Radio size={18} />}
              colorClass={readiness?.redis ? 'text-emerald-400' : 'text-amber-400'}
            />
            <StatCard
              label="Version"
              value={health?.version ?? '—'}
              icon={<Zap size={18} />}
              colorClass="text-violet-400"
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Service Status</CardTitle></CardHeader>
              <StatusRow label="API Backend" ok={health?.status === 'ok'} detail={`v${health?.version}`} />
              <StatusRow label="PostgreSQL Database" ok={readiness?.database} detail={readiness?.details?.database_url} />
              <StatusRow label="Redis Cache" ok={readiness?.redis} detail={readiness?.details?.redis_url} />
              <StatusRow label="Overall Readiness" ok={readiness?.ready} />
            </Card>

            <Card>
              <CardHeader><CardTitle>Runtime Info</CardTitle></CardHeader>
              <dl className="space-y-3 text-sm">
                {[
                  ['Version', health?.version ?? '—'],
                  ['Status', health?.status ?? '—'],
                  ['Timestamp', health?.timestamp ? format(new Date(health.timestamp), 'PPpp') : '—'],
                  ['DB URL', readiness?.details?.database_url ?? '—'],
                  ['Redis URL', readiness?.details?.redis_url ?? '—'],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <dt className="text-slate-500">{k}</dt>
                    <dd className="font-mono text-xs text-slate-300 text-right">{v}</dd>
                  </div>
                ))}
              </dl>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
