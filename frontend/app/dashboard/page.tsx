'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { ProtectedRoute } from '../../components/auth/ProtectedRoute';
import { AppShell } from '../../components/ui/AppShell';
import { MetricCard } from '../../components/ui/MetricCard';
import { useAuth } from '../../hooks/useAuth';
import { apiFetch, type Book, type Copy, type Loan, type UserRole } from '../../lib/api';

type CollectionPayload<T> =
  | T[]
  | { items?: T[]; data?: T[]; dados?: T[]; total?: number; count?: number }
  | null
  | undefined;

interface DashboardState {
  books: CollectionPayload<Book>;
  copies: CollectionPayload<Copy>;
  loans: CollectionPayload<Loan>;
  users: CollectionPayload<{ id: number }>;
  mostBorrowed: Array<{ title: string; checkout_count: number }>;
  loading: boolean;
  error: string | null;
}

function getCollectionTotal<T>(payload: CollectionPayload<T>): number {
  if (!payload) {
    return 0;
  }

  if (Array.isArray(payload)) {
    return payload.length;
  }

  if (payload?.items && Array.isArray(payload.items)) {
    return payload.items.length;
  }

  if (payload?.dados && Array.isArray(payload.dados)) {
    return payload.dados.length;
  }

  if (payload?.data && Array.isArray(payload.data)) {
    return payload.data.length;
  }

  if (typeof payload?.total === 'number') {
    return payload.total;
  }

  if (typeof payload?.count === 'number') {
    return payload.count;
  }

  return 0;
}

export default function DashboardPage() {
  const router = useRouter();
  const role: UserRole = 'librarian';
  const [state, setState] = useState<DashboardState>({
    books: null,
    copies: null,
    loans: null,
    users: null,
    mostBorrowed: [],
    loading: true,
    error: null
  });
  const { token, loading } = useAuth();

  useEffect(() => {
    if (!loading && !token) {
      router.push('/login');
    }
  }, [loading, token, router]);

  useEffect(() => {
    if (loading || !token) {
      return;
    }

    let isMounted = true;

    async function fetchDashboardData() {
      setState({ books: null, copies: null, loans: null, users: null, mostBorrowed: [], loading: true, error: null });

      const books = await apiFetch<CollectionPayload<Book>>('/api/v1/books/?page=1&page_size=50');

      const copies = await apiFetch<CollectionPayload<Copy>>('/api/v1/copies/');

      const loans = await apiFetch<CollectionPayload<Loan>>('/api/v1/loans/?page=1&page_size=50');
      const users = await apiFetch<CollectionPayload<{ id: number }>>('/api/v1/users/?page=1&page_size=50');
      const mostBorrowed = await apiFetch<Array<{ title: string; checkout_count: number }>>('/api/v1/reports/most-borrowed?limit=5');

      if (isMounted) {
        setState({ books, copies, loans, users, mostBorrowed: mostBorrowed ?? [], loading: false, error: null });
      }
    }

    fetchDashboardData().catch((error: unknown) => {
      if (isMounted) {
        const message = error instanceof Error ? error.message : 'Erro ao carregar dados';
        setState({ books: null, copies: null, loans: null, users: null, mostBorrowed: [], loading: false, error: message });
      }
    });

    return () => {
      isMounted = false;
    };
  }, [loading, token]);

  const totalBooks = getCollectionTotal<Book>(state.books);
  const totalCopies = getCollectionTotal<Copy>(state.copies);
  const activeLoans = getCollectionTotal<Loan>(state.loans);
  const activeUsers = getCollectionTotal<{ id: number }>(state.users);

  if (loading) {
    return <div>Carregando autenticação...</div>;
  }

  if (!token) {
    return null;
  }

  return (
    <ProtectedRoute>
      <AppShell
      role={role}
      title="Dashboard"
      subtitle="Monitor catalog health, circulation throughput, and tenant readiness."
    >
      {state.loading ? (
        <div className="rounded-xl border bg-white p-4 text-sm text-slate-600 shadow-sm">Carregando dados...</div>
      ) : null}

      {state.error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 shadow-sm">Erro ao carregar dados</div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard helper="MARC21-compliant bibliographic entries" label="Total Books" value={totalBooks} />
        <MetricCard helper="Inventory across branches and collections" label="Total Copies" value={totalCopies} />
        <MetricCard helper="Loans currently in active state" label="Active Loans" value={activeLoans} />
        <MetricCard helper="Usuários com atividade recente" label="Active Users" value={activeUsers} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border bg-white p-4 shadow-sm">
          <h3 className="mb-2 text-sm font-semibold text-slate-900">Gráfico de Empréstimos</h3>
          <div className="space-y-2">
            {['Ativos', 'Acervo', 'Usuários'].map((label, index) => {
              const value = [activeLoans, totalBooks, activeUsers][index] || 0;
              const width = Math.min(100, value === 0 ? 0 : (value / Math.max(activeLoans, totalBooks, activeUsers, 1)) * 100);
              return (
                <div key={label}>
                  <div className="mb-1 flex items-center justify-between text-xs text-slate-600"><span>{label}</span><span>{value}</span></div>
                  <div className="h-2 rounded bg-slate-100"><div className="h-2 rounded bg-blue-500" style={{ width: `${width}%` }} /></div>
                </div>
              );
            })}
          </div>
        </div>
        <div className="rounded-xl border bg-white p-4 shadow-sm">
          <h3 className="mb-2 text-sm font-semibold text-slate-900">Livros Mais Populares</h3>
          <ul className="space-y-2 text-sm text-slate-700">
            {state.mostBorrowed.length === 0 ? <li>Nenhum dado disponível.</li> : state.mostBorrowed.map((item) => <li key={item.title} className="flex justify-between"><span>{item.title}</span><span>{item.checkout_count}</span></li>)}
          </ul>
        </div>
      </div>
      </AppShell>
    </ProtectedRoute>
  );
}
