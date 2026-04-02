'use client';

import { useEffect, useState } from 'react';

import { ProtectedRoute } from '../../components/auth/ProtectedRoute';
import { AppShell } from '../../components/ui/AppShell';
import { DataTable } from '../../components/ui/DataTable';
import { useAuth } from '../../hooks/useAuth';
import { apiFetch, type Loan } from '../../lib/api';

interface LoanRow {
  [key: string]: string | number | null | undefined;
  id: number;
  copy_id: number;
  user_id: string;
  due_date: string;
  status: string;
}

export default function LoansPage() {
  const { token, role, loading } = useAuth();
  const [rows, setRows] = useState<LoanRow[]>([]);

  useEffect(() => {
    let isMounted = true;
    if (loading || !token) {
      return;
    }

    apiFetch<{ items: Loan[] }>('/api/v1/loans/?page=1&page_size=50')
      .then((loans) => {
        if (!isMounted || !loans) {
          return;
        }
        setRows(
          (loans.items ?? []).map((loan) => ({
            id: loan.id,
            copy_id: loan.copy_id,
            user_id: loan.user_id,
            due_date: loan.due_date,
            status: loan.status
          }))
        );
      })
      .catch(() => {
        if (isMounted) {
          setRows([]);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [loading, token]);

  return (
    <ProtectedRoute>
      <AppShell
      role={role ?? 'member'}
      title="Loans"
      subtitle="Process checkouts, monitor due dates, and return circulation assets quickly."
    >
      <DataTable
        columns={[
          { key: 'id', label: 'Loan #' },
          { key: 'copy_id', label: 'Copy ID' },
          { key: 'user_id', label: 'User ID' },
          { key: 'due_date', label: 'Due Date' },
          { key: 'status', label: 'Status' }
        ]}
        description="Track renewals and returns across all active circulation events."
        rows={rows}
        searchableFields={['id', 'copy_id', 'user_id', 'status']}
        title="Circulation Queue"
      />
      </AppShell>
    </ProtectedRoute>
  );
}
