
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
  position: number;
  status: string;
  remaining_time: string;
}

const STATUS_LABELS: Record<string, string> = {
  waiting: '🟡 aguardando',
  ready: '🟢 disponível',
  expired: '🔴 expirado',
  cancelled: '⚪ cancelado'
};

const formatRemainingTime = (expiresAt?: string | null): string => {
  if (!expiresAt) return '-';
  const now = Date.now();
  const expires = new Date(expiresAt).getTime();
  const diffMs = expires - now;
  if (diffMs <= 0) return 'expirado';
  const totalMinutes = Math.floor(diffMs / (1000 * 60));
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${hours}h ${minutes}m`;
};

export default function ReservationsPage() {
  const role = 'librarian';
  const [rows, setRows] = useState<ReservationRow[]>([]);
  const { token, loading } = useAuth();

  useEffect(() => {
    if (loading || !token) return;
    apiFetch<{ items: Reservation[] }>('/api/v1/reservations/?page=1&page_size=50')
      .then((data) => setRows((data?.items ?? []).map((r) => ({
        id: r.id,
        copy_id: r.copy_id,
        user_id: r.user_id,
        position: r.position,
        status: STATUS_LABELS[r.status] ?? r.status,
        remaining_time: r.status === 'ready' ? formatRemainingTime(r.expires_at) : '-'
      }))))
      .catch(() => setRows([]));
  }, [loading, token]);

  const reserveBook = async () => {
    const copyId = window.prompt('ID da cópia para reservar:');
    if (!copyId) return;
    await apiFetch('/api/v1/reservations/', { method: 'POST', body: JSON.stringify({ copy_id: Number(copyId) }) });
    const refreshed = await apiFetch<{ items: Reservation[] }>('/api/v1/reservations/?page=1&page_size=50');
    setRows((refreshed?.items ?? []).map((r) => ({
      id: r.id,
      copy_id: r.copy_id,
      user_id: r.user_id,
      position: r.position,
      status: STATUS_LABELS[r.status] ?? r.status,
      remaining_time: r.status === 'ready' ? formatRemainingTime(r.expires_at) : '-'
    })));
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
            { key: 'position', label: 'Posição na fila' },
            { key: 'status', label: 'Status' },
            { key: 'remaining_time', label: 'Tempo restante' }
          ]}
          rows={rows.sort((a, b) => Number(a.position) - Number(b.position))}
          searchableFields={['id', 'copy_id', 'user_id', 'position', 'status']}
          title="Reservas"
        />
      </AppShell>
    </ProtectedRoute>
  );
}
