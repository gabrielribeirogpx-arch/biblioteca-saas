'use client';

import { useEffect, useState } from 'react';

import { ProtectedRoute } from '../../components/auth/ProtectedRoute';
import { AppShell } from '../../components/ui/AppShell';
import { DataTable } from '../../components/ui/DataTable';
import { useAuth } from '../../hooks/useAuth';
import { apiFetch, type User } from '../../lib/api';
import { hasPermission } from '../../lib/permissions';

interface UserRow {
  [key: string]: string | number | null | undefined;
  id: number;
  full_name: string;
  email: string;
  role: string;
}

export default function UsersPage() {
  const { token, role, loading, permissions } = useAuth();
  const [rows, setRows] = useState<UserRow[]>([]);

  useEffect(() => {
    if (!hasPermission('users.read', permissions)) {
      setRows([]);
      return;
    }
    let isMounted = true;
    if (loading || !token) {
      return;
    }

    apiFetch<{ items: User[] }>('/api/v1/users/?page=1&page_size=50')
      .then((users) => {
        if (!isMounted || !users) {
          return;
        }
        setRows(
          (users.items ?? []).map((user) => ({
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
  }, [loading, permissions, token]);

  return (
    <ProtectedRoute>
      <AppShell
      role={role ?? 'member'}
      title="Users"
      subtitle="Administer tenant user access and role assignments for secure operations."
    >

      {!hasPermission('users.read', permissions) ? (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          Seu perfil não possui a permissão <strong>users.read</strong> para visualizar este módulo.
        </div>
      ) : (
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
      )}
      </AppShell>
    </ProtectedRoute>
  );
}
