import { AppShell } from '../../components/ui/AppShell';
import { DataTable } from '../../components/ui/DataTable';
import { MetricCard } from '../../components/ui/MetricCard';
import { createApiClient } from '../../lib/api';
import { getCurrentRole } from '../../lib/auth';

async function loadReportRows() {
  const api = createApiClient({ tenantId: process.env.DEFAULT_TENANT_ID ?? 'default' });

  const [mostBorrowed, overdue] = await Promise.all([
    api.listMostBorrowed(10).catch(() => []),
    api.listOverdue(20).catch(() => [])
  ]);

  return {
    mostBorrowed: mostBorrowed.map((item) => ({
      title: item.title,
      checkout_count: item.checkout_count
    })),
    overdue: overdue.map((item) => ({
      loan_id: item.loan_id,
      user_id: item.user_id,
      copy_id: item.copy_id,
      overdue_days: item.overdue_days
    }))
  };
}

export default async function ReportsPage() {
  const role = getCurrentRole();
  const reportData = await loadReportRows();

  return (
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
  );
}
