
'use client';

import { useEffect, useState } from 'react';

import { ProtectedRoute } from '../../components/auth/ProtectedRoute';
import { AppShell } from '../../components/ui/AppShell';
import { DataTable } from '../../components/ui/DataTable';
import { useAuth } from '../../hooks/useAuth';
import { apiFetch, type Reservation } from '../../lib/api';

interface ReservationRow {
  [key: string]: string | number | null | undefined;
  id: number;
  copy_id: number;
  user_id: number;
  status: string;
}

export default function ReservationsPage() {
  const role = 'librarian';
  const [rows, setRows] = useState<ReservationRow[]>([]);
  const { token, loading } = useAuth();

  useEffect(() => {
    if (loading || !token) return;
    apiFetch<{ items: Reservation[] }>('/api/v1/reservations/?page=1&page_size=50')
      .then((data) => setRows((data?.items ?? []).map((r) => ({ id: r.id, copy_id: r.copy_id, user_id: r.user_id, status: r.status }))))
      .catch(() => setRows([]));
  }, [loading, token]);

  const reserveBook = async () => {
    const copyId = window.prompt('ID da cópia para reservar:');
    if (!copyId) return;
    await apiFetch('/api/v1/reservations/', { method: 'POST', body: JSON.stringify({ copy_id: Number(copyId) }) });
    const refreshed = await apiFetch<{ items: Reservation[] }>('/api/v1/reservations/?page=1&page_size=50');
    setRows((refreshed?.items ?? []).map((r) => ({ id: r.id, copy_id: r.copy_id, user_id: r.user_id, status: r.status })));
  };

  return (
    <ProtectedRoute>
      <AppShell role={role} title="Reservations" subtitle="Gerencie fila de reservas por livro e usuário.">
        <button onClick={reserveBook} className="mb-4 rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white">reservar livro</button>
        <DataTable
          columns={[
            { key: 'id', label: 'Reserva #' },
            { key: 'copy_id', label: 'Copy ID' },
            { key: 'user_id', label: 'User ID' },
            { key: 'status', label: 'Status' }
          ]}
          rows={rows}
          searchableFields={['id', 'copy_id', 'user_id', 'status']}
          title="Reservas"
        />
      </AppShell>
    </ProtectedRoute>
  );
}
