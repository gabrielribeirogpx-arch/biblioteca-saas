import type { ReactNode } from 'react';

import type { UserRole } from '../../lib/api';
import { RoleAwareNav } from './RoleAwareNav';

interface AppShellProps {
  role: UserRole;
  title: string;
  subtitle: string;
  children: ReactNode;
}

export function AppShell({ role, title, subtitle, children }: AppShellProps) {
  return (
    <div className="min-h-screen">
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 md:px-6 lg:grid-cols-[280px_1fr] lg:gap-8">
        <aside className="rounded-xl border bg-white p-4 shadow-sm">
          <div className="mb-6 border-b pb-4">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-700">Biblioteca SaaS</p>
            <h1 className="mt-2 text-lg font-semibold text-slate-900">Library Operations</h1>
            <p className="mt-1 text-sm text-slate-500">Role: {role.replace('_', ' ')}</p>
          </div>
          <RoleAwareNav role={role} />
        </aside>

        <main className="space-y-6">
          <header className="rounded-xl border bg-white p-4 shadow-sm md:p-6">
            <h2 className="text-2xl font-semibold text-slate-900">{title}</h2>
            <p className="mt-1 text-sm text-slate-600">{subtitle}</p>
          </header>

          <section className="space-y-6">{children}</section>
        </main>
      </div>
    </div>
  );
}
