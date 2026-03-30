import { AppShell } from '../../components/ui/AppShell';
import { MetricCard } from '../../components/ui/MetricCard';
import { createApiClient } from '../../lib/api';
import { getCurrentRole } from '../../lib/auth';

async function getDashboardMetrics() {
  const api = createApiClient({ tenantId: process.env.DEFAULT_TENANT_ID ?? 'default' });

  const result = await api
    .getSummaryReport()
    .catch(() => ({ total_books: 0, total_copies: 0, active_loans: 0 }));

  return result;
}

export default async function DashboardPage() {
  const role = getCurrentRole();
  const metrics = await getDashboardMetrics();

  return (
    <AppShell
      role={role}
      title="Dashboard"
      subtitle="Monitor catalog health, circulation throughput, and tenant readiness."
    >
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard helper="MARC21-compliant bibliographic entries" label="Total Books" value={metrics.total_books} />
        <MetricCard helper="Inventory across branches and collections" label="Total Copies" value={metrics.total_copies} />
        <MetricCard helper="Loans currently in active state" label="Active Loans" value={metrics.active_loans} />
      </div>
    </AppShell>
  );
}
