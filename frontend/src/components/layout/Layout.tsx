import type { ElementType, ReactNode } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  Activity,
  BarChart2,
  BookOpen,
  CheckSquare,
  Cpu,
  Heart,
  Home,
  List,
  Menu,
  Moon,
  Wrench,
  X,
} from 'lucide-react';
import { useState } from 'react';
import { useHealth } from '@/hooks/useApi';
import { Dot } from '@/components/ui';

const navItems = [
  { to: '/',             label: 'Overview',      icon: Home },
  { to: '/executions',   label: 'Executions',    icon: List },
  { to: '/evaluations',  label: 'Evaluations',   icon: CheckSquare },
  { to: '/tools',        label: 'Tool Registry', icon: Wrench },
  { to: '/observability',label: 'Observability', icon: BarChart2 },
  { to: '/health',       label: 'System Health', icon: Heart },
];

function NavItem({ to, label, icon: Icon }: { to: string; label: string; icon: ElementType }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        clsx(
          'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all',
          isActive
            ? 'bg-blue-600/20 text-blue-400'
            : 'text-slate-400 hover:bg-surface-elevated hover:text-slate-200',
        )
      }
    >
      <Icon size={16} />
      {label}
    </NavLink>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { data: health } = useHealth();
  const location = useLocation();

  return (
    <div className="flex h-screen bg-navy-950 overflow-hidden">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/60 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-30 flex w-60 flex-col border-r border-surface-border bg-navy-900 transition-transform lg:relative lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        {/* Logo */}
        <div className="flex h-14 items-center gap-3 border-b border-surface-border px-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
            <Cpu size={16} className="text-white" />
          </div>
          <div>
            <p className="text-sm font-bold text-slate-100">AI Runtime</p>
            <p className="text-[10px] text-slate-500">Evaluation Platform</p>
          </div>
          <button
            className="ml-auto text-slate-500 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={16} />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {navItems.map(item => (
            <NavItem key={item.to} {...item} />
          ))}
        </nav>

        {/* Footer */}
        <div className="border-t border-surface-border px-4 py-3">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Dot color={health?.status === 'ok' ? 'green' : 'gray'} />
            <span>{health ? `v${health.version}` : 'connecting…'}</span>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-surface-border bg-navy-900 px-4">
          <button
            className="text-slate-400 hover:text-slate-200 lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={20} />
          </button>
          <div className="flex-1" />
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Activity size={12} />
            <span>Local provider</span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <div className="animate-fade-in">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
