import type * as React from 'react';
import { clsx } from 'clsx';

// ─── Badge ────────────────────────────────────────────────────────────────────

type BadgeVariant = 'success' | 'error' | 'warning' | 'info' | 'neutral' | 'purple';

const badgeClasses: Record<BadgeVariant, string> = {
  success: 'bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30',
  error:   'bg-rose-500/15 text-rose-400 ring-1 ring-rose-500/30',
  warning: 'bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/30',
  info:    'bg-blue-500/15 text-blue-400 ring-1 ring-blue-500/30',
  neutral: 'bg-slate-500/15 text-slate-400 ring-1 ring-slate-500/30',
  purple:  'bg-violet-500/15 text-violet-400 ring-1 ring-violet-500/30',
};

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

export function Badge({ variant = 'neutral', children, className }: BadgeProps) {
  return (
    <span className={clsx(
      'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
      badgeClasses[variant],
      className,
    )}>
      {children}
    </span>
  );
}

export function statusBadge(status: string) {
  const map: Record<string, BadgeVariant> = {
    completed: 'success',
    success: 'success',
    failed: 'error',
    timed_out: 'warning',
    running: 'info',
    pending: 'neutral',
  };
  return <Badge variant={map[status] ?? 'neutral'}>{status}</Badge>;
}

// ─── Card ─────────────────────────────────────────────────────────────────────

export function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={clsx(
      'rounded-xl border border-surface-border bg-surface p-5',
      className,
    )}>
      {children}
    </div>
  );
}

export function CardHeader({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={clsx('mb-4 flex items-center justify-between', className)}>{children}</div>;
}

export function CardTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return <h3 className={clsx('text-sm font-semibold text-slate-200', className)}>{children}</h3>;
}

// ─── Stat Card ────────────────────────────────────────────────────────────────

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  colorClass?: string;
}

export function StatCard({ label, value, sub, icon, colorClass = 'text-blue-400' }: StatCardProps) {
  return (
    <Card>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{label}</p>
          <p className={clsx('mt-1.5 text-2xl font-bold', colorClass)}>{value}</p>
          {sub && <p className="mt-0.5 text-xs text-slate-500">{sub}</p>}
        </div>
        {icon && (
          <div className="rounded-lg bg-surface-elevated p-2.5 text-slate-400">
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
}

// ─── Spinner ─────────────────────────────────────────────────────────────────

export function Spinner({ size = 16 }: { size?: number }) {
  return (
    <svg
      className="animate-spin text-blue-400"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      width={size}
      height={size}
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

// ─── Loading State ────────────────────────────────────────────────────────────

export function LoadingState({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-slate-500">
      <Spinner size={28} />
      <p className="text-sm">{message}</p>
    </div>
  );
}

// ─── Error State ──────────────────────────────────────────────────────────────

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center gap-2 py-12 text-center">
      <div className="rounded-full bg-rose-500/10 p-3">
        <svg className="h-6 w-6 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M12 3a9 9 0 110 18A9 9 0 0112 3z" />
        </svg>
      </div>
      <p className="text-sm font-medium text-slate-300">Something went wrong</p>
      <p className="max-w-sm text-xs text-slate-500">{message}</p>
    </div>
  );
}

// ─── Empty State ──────────────────────────────────────────────────────────────

export function EmptyState({ title, description, icon }: { title: string; description?: string; icon?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 py-16 text-center">
      {icon && <div className="text-slate-600">{icon}</div>}
      <p className="text-sm font-medium text-slate-400">{title}</p>
      {description && <p className="max-w-sm text-xs text-slate-600">{description}</p>}
    </div>
  );
}

// ─── Button ───────────────────────────────────────────────────────────────────

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

const btnVariant: Record<ButtonVariant, string> = {
  primary:   'bg-blue-600 text-white hover:bg-blue-500 focus-visible:ring-blue-500',
  secondary: 'bg-surface-elevated text-slate-200 border border-surface-border hover:bg-surface-hover',
  danger:    'bg-rose-600/20 text-rose-400 border border-rose-500/30 hover:bg-rose-600/30',
  ghost:     'text-slate-400 hover:text-slate-200 hover:bg-surface-elevated',
};

const btnSize: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-5 py-2.5 text-base',
};

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ReactNode;
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  children,
  className,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={clsx(
        'inline-flex items-center gap-2 rounded-lg font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-navy-900 disabled:cursor-not-allowed disabled:opacity-50',
        btnVariant[variant],
        btnSize[size],
        className,
      )}
    >
      {loading ? <Spinner size={14} /> : icon}
      {children}
    </button>
  );
}

// ─── Code block ───────────────────────────────────────────────────────────────

export function CodeBlock({ value, maxH }: { value: unknown; maxH?: string }) {
  return (
    <pre
      className={clsx(
        'overflow-auto rounded-lg bg-navy-900 p-3 text-xs text-slate-300 font-mono',
        maxH && `max-h-[${maxH}]`,
      )}
    >
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

// ─── Progress bar ─────────────────────────────────────────────────────────────

export function ProgressBar({ value, max = 1, colorClass = 'bg-blue-500' }: { value: number; max?: number; colorClass?: string }) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  return (
    <div className="h-1.5 w-full rounded-full bg-surface-elevated">
      <div
        className={clsx('h-full rounded-full transition-all', colorClass)}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

// ─── Table ────────────────────────────────────────────────────────────────────

export function Table({ headers, children }: { headers: string[]; children: React.ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-surface-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-surface-border bg-surface-elevated">
            {headers.map(h => (
              <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-border">
          {children}
        </tbody>
      </table>
    </div>
  );
}

export function Tr({ children, onClick, clickable }: { children: React.ReactNode; onClick?: () => void; clickable?: boolean }) {
  return (
    <tr
      onClick={onClick}
      className={clsx(
        'transition-colors',
        clickable && 'cursor-pointer hover:bg-surface-hover',
      )}
    >
      {children}
    </tr>
  );
}

export function Td({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <td className={clsx('px-4 py-3 text-slate-300', className)}>{children}</td>
  );
}

// ─── Input ────────────────────────────────────────────────────────────────────

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={clsx(
        'w-full rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500',
        className,
      )}
    />
  );
}

export function Select({ className, children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={clsx(
        'rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500',
        className,
      )}
    >
      {children}
    </select>
  );
}

export function Textarea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={clsx(
        'w-full rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono',
        className,
      )}
    />
  );
}

// ─── Label ────────────────────────────────────────────────────────────────────

export function Label({ htmlFor, children }: { htmlFor?: string; children: React.ReactNode }) {
  return (
    <label htmlFor={htmlFor} className="block text-xs font-medium text-slate-400 mb-1">
      {children}
    </label>
  );
}

// ─── Divider ─────────────────────────────────────────────────────────────────

export function Divider() {
  return <hr className="border-surface-border" />;
}

// ─── Tooltip helper (simple title-based) ─────────────────────────────────────

export function Dot({ color }: { color: 'green' | 'red' | 'yellow' | 'gray' | 'blue' }) {
  const cls: Record<typeof color, string> = {
    green:  'bg-emerald-400',
    red:    'bg-rose-400',
    yellow: 'bg-amber-400',
    gray:   'bg-slate-500',
    blue:   'bg-blue-400',
  };
  return <span className={clsx('inline-block h-2 w-2 rounded-full', cls[color])} />;
}
