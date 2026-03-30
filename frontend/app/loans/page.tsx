import { AppShell } from '../../components/ui/AppShell';
import { DataTable } from '../../components/ui/DataTable';
import { createApiClient } from '../../lib/api';
import { getCurrentRole } from '../../lib/auth';

async function loadLoanRows() {
  const api = createApiClient({ tenantId: process.env.DEFAULT_TENANT_ID ?? 'default' });
  const loans = await api.listLoans().catch(() => []);

  return loans.map((loan) => ({
    id: loan.id,
    copy_id: loan.copy_id,
    user_id: loan.user_id,
    due_date: loan.due_date,
    status: loan.status
  }));
}

export default async function LoansPage() {
  const role = getCurrentRole();
  const rows = await loadLoanRows();

  return (
    <AppShell
      role={role}
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
  );
}
