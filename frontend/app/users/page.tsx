'use client';

import { useEffect, useState } from 'react';

import { AppShell } from '../../components/ui/AppShell';
import { DataTable } from '../../components/ui/DataTable';
import { apiFetch, getStoredToken, type User } from '../../lib/api';

interface UserRow {
  [key: string]: string | number | null | undefined;
  id: number;
  full_name: string;
  email: string;
  role: string;
}

export default function UsersPage() {
  const role = 'librarian';
  const [rows, setRows] = useState<UserRow[]>([]);

  useEffect(() => {
    let isMounted = true;
    const token = getStoredToken();
    if (!token) {
      return;
    }

    apiFetch<User[]>('/api/v1/users')
      .then((users) => {
        if (!isMounted || !users) {
          return;
        }
        setRows(
          users.map((user) => ({
            id: user.id,
            full_name: user.full_name,
            email: user.email,
            role: user.role
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
  }, []);

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
