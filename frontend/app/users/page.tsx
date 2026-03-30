import { AppShell } from '../../components/ui/AppShell';
import { DataTable } from '../../components/ui/DataTable';
import { createApiClient } from '../../lib/api';
import { getCurrentRole } from '../../lib/auth';

async function loadUsersRows() {
  const api = createApiClient({ tenantId: process.env.DEFAULT_TENANT_ID ?? 'default' });
  const users = await api.listUsers().catch(() => []);

  return users.map((user) => ({
    id: user.id,
    full_name: user.full_name,
    email: user.email,
    role: user.role
  }));
}

export default async function UsersPage() {
  const role = getCurrentRole();
  const rows = await loadUsersRows();

  return (
    <AppShell
      role={role}
      title="Users"
      subtitle="Administer tenant user access and role assignments for secure operations."
    >
      <DataTable
        columns={[
          { key: 'id', label: 'User ID' },
          { key: 'full_name', label: 'Name' },
          { key: 'email', label: 'Email' },
          { key: 'role', label: 'Role' }
        ]}
        description="Role-aware access control aligned with operational responsibilities."
        rows={rows}
        searchableFields={['full_name', 'email', 'role']}
        title="Tenant Users"
      />
    </AppShell>
  );
}
