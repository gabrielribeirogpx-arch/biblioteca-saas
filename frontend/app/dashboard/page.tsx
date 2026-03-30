'use client';

import { AppShell } from '../../components/ui/AppShell';
import { MetricCard } from '../../components/ui/MetricCard';
import { useApi } from '../../hooks/useApi';
import type { Book, Copy, Loan, UserRole } from '../../lib/api';

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

  const booksState = useApi<Book[] | { items?: Book[]; data?: Book[]; total?: number; count?: number }>('/api/v1/books');
  const copiesState = useApi<Copy[] | { items?: Copy[]; data?: Copy[]; total?: number; count?: number }>('/api/v1/copies');
  const loansState = useApi<Loan[] | { items?: Loan[]; data?: Loan[]; total?: number; count?: number }>('/api/v1/loans');

  const isLoading = booksState.loading || copiesState.loading || loansState.loading;
  const hasError = booksState.error || copiesState.error || loansState.error;

  const totalBooks = getCollectionTotal<Book>(booksState.data);
  const totalCopies = getCollectionTotal<Copy>(copiesState.data);
  const activeLoans = getCollectionTotal<Loan>(loansState.data);

  return (
    <AppShell
      role={role}
      title="Dashboard"
      subtitle="Monitor catalog health, circulation throughput, and tenant readiness."
    >
      {isLoading ? (
        <div className="rounded-xl border bg-white p-4 text-sm text-slate-600 shadow-sm">Carregando dados...</div>
      ) : null}

      {hasError ? (
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
