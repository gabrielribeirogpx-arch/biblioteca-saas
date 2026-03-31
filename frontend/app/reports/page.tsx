'use client';

import { useEffect, useState } from 'react';

import { ProtectedRoute } from '../../components/auth/ProtectedRoute';
import { AppShell } from '../../components/ui/AppShell';
import { DataTable } from '../../components/ui/DataTable';
import { MetricCard } from '../../components/ui/MetricCard';
import { apiFetch, getStoredToken, type MostBorrowedItem, type OverdueItem } from '../../lib/api';

interface MostBorrowedRow {
  [key: string]: string | number | null | undefined;
  title: string;
  checkout_count: number;
}

interface OverdueRow {
  [key: string]: string | number | null | undefined;
  loan_id: number;
  user_id: number;
  copy_id: number;
  overdue_days: number;
}

export default function ReportsPage() {
  const role = 'librarian';
  const [reportData, setReportData] = useState<{ mostBorrowed: MostBorrowedRow[]; overdue: OverdueRow[] }>({
    mostBorrowed: [],
    overdue: []
  });

  useEffect(() => {
    let isMounted = true;
    const token = getStoredToken();
    if (!token) {
      return;
    }

    Promise.all([
      apiFetch<MostBorrowedItem[]>('/api/v1/reports/most-borrowed?limit=10'),
      apiFetch<OverdueItem[]>('/api/v1/reports/overdue?limit=20')
    ])
      .then(([mostBorrowed, overdue]) => {
        if (!isMounted) {
          return;
        }
        setReportData({
          mostBorrowed: (mostBorrowed ?? []).map((item) => ({
            title: item.title,
            checkout_count: item.checkout_count
          })),
          overdue: (overdue ?? []).map((item) => ({
            loan_id: item.loan_id,
            user_id: item.user_id,
            copy_id: item.copy_id,
            overdue_days: item.overdue_days
          }))
        });
      })
      .catch(() => {
        if (isMounted) {
          setReportData({ mostBorrowed: [], overdue: [] });
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <ProtectedRoute>
      <AppShell
      role={role}
      title="Reports"
      subtitle="Review high-impact operational indicators for policy and performance workflows."
    >
      <div className="grid gap-4 md:grid-cols-2">
        <MetricCard label="Most Borrowed Titles" value={reportData.mostBorrowed.length} />
        <MetricCard label="Overdue Records" value={reportData.overdue.length} />
      </div>

      <DataTable
        columns={[
          { key: 'title', label: 'Title' },
          { key: 'checkout_count', label: 'Checkouts' }
        ]}
        rows={reportData.mostBorrowed}
        searchableFields={['title']}
        title="Most Borrowed"
      />

      <DataTable
        columns={[
          { key: 'loan_id', label: 'Loan ID' },
          { key: 'user_id', label: 'User ID' },
          { key: 'copy_id', label: 'Copy ID' },
          { key: 'overdue_days', label: 'Overdue Days' }
        ]}
        rows={reportData.overdue}
        searchableFields={['loan_id', 'user_id', 'copy_id']}
        title="Overdue Loans"
      />
      </AppShell>
    </ProtectedRoute>
  );
}
