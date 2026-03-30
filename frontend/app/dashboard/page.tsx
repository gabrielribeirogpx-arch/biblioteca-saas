'use client';

import { useEffect, useState } from 'react';

import { AppShell } from '../../components/ui/AppShell';
import { MetricCard } from '../../components/ui/MetricCard';
import { apiFetch, type Book, type Copy, type Loan, type UserRole } from '../../lib/api';

interface DashboardState {
  books: Book[] | { items?: Book[]; data?: Book[]; total?: number; count?: number } | null;
  copies: Copy[] | { items?: Copy[]; data?: Copy[]; total?: number; count?: number } | null;
  loans: Loan[] | { items?: Loan[]; data?: Loan[]; total?: number; count?: number } | null;
  loading: boolean;
  error: string | null;
}

function getCollectionTotal<T>(payload: unknown): number {
  if (Array.isArray(payload)) {
    return payload.length;
  }

  if (payload && typeof payload === 'object') {
    const result = payload as { items?: T[]; data?: T[]; total?: number; count?: number };

    if (Array.isArray(result.items)) {
      return result.items.length;
    }

    if (Array.isArray(result.data)) {
      return result.data.length;
    }

    if (typeof result.total === 'number') {
      return result.total;
    }

    if (typeof result.count === 'number') {
      return result.count;
    }
  }

  return 0;
}

export default function DashboardPage() {
  const role: UserRole = 'librarian';
  const [state, setState] = useState<DashboardState>({
    books: null,
    copies: null,
    loans: null,
    loading: true,
    error: null
  });

  useEffect(() => {
    console.log('useEffect rodando');
  }, []);

  useEffect(() => {
    console.log('Chamando API...');

    fetch('https://backend-biblioteca-saas-production.up.railway.app/health', { cache: 'no-store' })
      .then((res) => res.json())
      .then((data) => console.log('API OK:', data))
      .catch((err) => console.error('Erro fetch:', err));
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function fetchDashboardData() {
      setState({ books: null, copies: null, loans: null, loading: true, error: null });

      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;
      console.log('NEXT_PUBLIC_API_URL:', apiBaseUrl ?? '(undefined - usando fallback)');

      const [books, copies, loans] = await Promise.all([
        apiFetch<Book[] | { items?: Book[]; data?: Book[]; total?: number; count?: number }>('/api/v1/books'),
        apiFetch<Copy[] | { items?: Copy[]; data?: Copy[]; total?: number; count?: number }>('/api/v1/copies'),
        apiFetch<Loan[] | { items?: Loan[]; data?: Loan[]; total?: number; count?: number }>('/api/v1/loans')
      ]);

      if (isMounted) {
        setState({ books, copies, loans, loading: false, error: null });
      }
    }

    fetchDashboardData().catch((error: unknown) => {
      console.error('Erro completo ao carregar dashboard:', error);
      if (isMounted) {
        const message = error instanceof Error ? error.message : 'Erro ao carregar dados';
        setState({ books: null, copies: null, loans: null, loading: false, error: message });
      }
    });

    return () => {
      isMounted = false;
    };
  }, []);

  const totalBooks = getCollectionTotal<Book>(state.books);
  const totalCopies = getCollectionTotal<Copy>(state.copies);
  const activeLoans = getCollectionTotal<Loan>(state.loans);

  return (
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

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard helper="MARC21-compliant bibliographic entries" label="Total Books" value={totalBooks} />
        <MetricCard helper="Inventory across branches and collections" label="Total Copies" value={totalCopies} />
        <MetricCard helper="Loans currently in active state" label="Active Loans" value={activeLoans} />
      </div>
    </AppShell>
  );
}
