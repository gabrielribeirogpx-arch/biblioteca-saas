'use client';

import { useEffect, useState } from 'react';

import { AppShell } from '../../components/ui/AppShell';
import { MetricCard } from '../../components/ui/MetricCard';
import { apiFetch, getStoredToken, type Book, type Copy, type Loan, type UserRole } from '../../lib/api';

type CollectionPayload<T> =
  | T[]
  | { items?: T[]; data?: T[]; dados?: T[]; total?: number; count?: number }
  | null
  | undefined;

interface DashboardState {
  books: CollectionPayload<Book>;
  copies: CollectionPayload<Copy>;
  loans: CollectionPayload<Loan>;
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
  const role: UserRole = 'librarian';
  const [state, setState] = useState<DashboardState>({
    books: null,
    copies: null,
    loans: null,
    loading: true,
    error: null
  });

  useEffect(() => {
    let isMounted = true;

    async function fetchDashboardData() {
      setState({ books: null, copies: null, loans: null, loading: true, error: null });

      const token = getStoredToken();
      if (!token) {
        if (isMounted) {
          setState({ books: null, copies: null, loans: null, loading: false, error: null });
        }
        return;
      }

      const books = await apiFetch<CollectionPayload<Book>>('/api/v1/books/');

      const copies = await apiFetch<CollectionPayload<Copy>>('/api/v1/copies/');

      const loans = await apiFetch<CollectionPayload<Loan>>('/api/v1/loans/');

      if (isMounted) {
        setState({ books, copies, loans, loading: false, error: null });
      }
    }

    fetchDashboardData().catch((error: unknown) => {
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
