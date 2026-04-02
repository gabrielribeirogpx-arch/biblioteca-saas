'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import { ProtectedRoute } from '../../components/auth/ProtectedRoute';
import { AppShell } from '../../components/ui/AppShell';
import { DataTable } from '../../components/ui/DataTable';
import { Toast } from '../../components/ui/Toast';
import { useAuth } from '../../hooks/useAuth';
import { apiFetch, type Reservation } from '../../lib/api';

interface ReservationRow {
  [key: string]: string | number | null | undefined;
  id: number;
  book_id: number;
  copy_id: number | null;
  user_id: number;
  position: number;
  status: string;
}

const STATUS_LABELS: Record<string, string> = {
  waiting: 'waiting',
  ready: 'ready',
  expired: 'expired',
  cancelled: 'cancelled'
};

export default function ReservationsPage() {
  const { token, role, loading } = useAuth();
  const [rows, setRows] = useState<ReservationRow[]>([]);
  const [loadingData, setLoadingData] = useState(true);
  const [creating, setCreating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadReservations = useCallback(async () => {
    if (!token) return;
    setLoadingData(true);
    setErrorMessage(null);

    try {
      const data = await apiFetch<{ items: Reservation[] }>('/api/reservations/?page=1&page_size=100');
      const mapped = (data?.items ?? []).map((reservation) => ({
        id: reservation.id,
        book_id: reservation.book_id,
        copy_id: reservation.copy_id ?? null,
        user_id: reservation.user_id,
        position: reservation.position,
        status: STATUS_LABELS[reservation.status] ?? reservation.status
      }));

      setRows(mapped.sort((a, b) => (a.book_id - b.book_id) || (a.position - b.position)));
    } catch {
      setRows([]);
      setErrorMessage('Não foi possível carregar a fila de reservas.');
    } finally {
      setLoadingData(false);
    }
  }, [token]);

  useEffect(() => {
    if (loading || !token) return;
    void loadReservations();
  }, [loading, token, loadReservations]);

  useEffect(() => {
    if (!successMessage) return;
    const timeout = window.setTimeout(() => setSuccessMessage(null), 3000);
    return () => window.clearTimeout(timeout);
  }, [successMessage]);

  const queueSummary = useMemo(() => {
    return rows.reduce<Record<number, number>>((acc, row) => {
      acc[row.book_id] = (acc[row.book_id] ?? 0) + 1;
      return acc;
    }, {});
  }, [rows]);

  const createReservation = async () => {
    const bookId = window.prompt('Informe o ID do livro para reserva:');
    if (!bookId) return;

    setCreating(true);
    setErrorMessage(null);

    try {
      await apiFetch('/api/reservations/', {
        method: 'POST',
        body: JSON.stringify({ book_id: Number(bookId) })
      });
      setSuccessMessage('Reserva criada com sucesso.');
      await loadReservations();
    } catch {
      setErrorMessage('Falha ao criar reserva.');
    } finally {
      setCreating(false);
    }
  };

  return (
    <ProtectedRoute>
      <AppShell role={role ?? 'member'} title="Reservas" subtitle="Fila de reservas por livro, com posição e status operacional.">
        {successMessage ? <Toast message={successMessage} /> : null}

        <article className="rounded-xl border bg-white p-4 shadow-sm md:p-6">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Fila por livro</h3>
              <p className="text-sm text-slate-600">Status suportados: waiting e ready.</p>
            </div>
            <button
              type="button"
              onClick={() => void createReservation()}
              disabled={creating}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {creating ? 'Salvando...' : 'Nova reserva'}
            </button>
          </div>

          {Object.keys(queueSummary).length > 0 ? (
            <ul className="mb-4 grid gap-2 text-sm text-slate-700 md:grid-cols-3">
              {Object.entries(queueSummary).map(([bookId, total]) => (
                <li key={bookId} className="rounded-lg border border-slate-200 px-3 py-2">
                  Livro #{bookId}: {total} reserva(s)
                </li>
              ))}
            </ul>
          ) : null}

          {loadingData ? <p className="text-sm text-slate-600">Carregando reservas...</p> : null}
          {errorMessage ? <p className="text-sm font-medium text-rose-700">{errorMessage}</p> : null}
        </article>

        <DataTable
          columns={[
            { key: 'id', label: 'Reserva #' },
            { key: 'book_id', label: 'Livro' },
            { key: 'copy_id', label: 'Exemplar' },
            { key: 'user_id', label: 'Usuário' },
            { key: 'position', label: 'Posição na fila' },
            { key: 'status', label: 'Status' }
          ]}
          rows={rows}
          searchableFields={['id', 'book_id', 'copy_id', 'user_id', 'position', 'status']}
          title="Reservas por livro"
        />
      </AppShell>
    </ProtectedRoute>
  );
}
