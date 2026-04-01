
'use client';

import { useEffect, useState } from 'react';

import { ProtectedRoute } from '../../components/auth/ProtectedRoute';
import { AppShell } from '../../components/ui/AppShell';
import { DataTable } from '../../components/ui/DataTable';
import { useAuth } from '../../hooks/useAuth';
import { apiFetch, type Fine } from '../../lib/api';

interface FineRow {
  [key: string]: string | number | null | undefined;
  id: number;
  user_id: number;
  loan_id: number;
  amount: string;
  status: string;
}

export default function FinesPage() {
  const role = 'librarian';
  const [rows, setRows] = useState<FineRow[]>([]);
  const { token, loading } = useAuth();

  const load = async () => {
    const data = await apiFetch<{ items: Fine[] }>('/api/v1/fines/?page=1&page_size=50');
    setRows((data?.items ?? []).map((f) => ({ id: f.id, user_id: f.user_id, loan_id: f.loan_id, amount: String(f.amount), status: f.status })));
  };

  useEffect(() => {
    if (loading || !token) return;
    load().catch(() => setRows([]));
  }, [loading, token]);

  const payFine = async () => {
    const fineId = window.prompt('ID da multa:');
    if (!fineId) return;
    await apiFetch(`/api/v1/fines/${fineId}/pay`, { method: 'POST', body: JSON.stringify({ amount: 1 }) });
    await load();
  };

  return (
    <ProtectedRoute>
      <AppShell role={role} title="Fines" subtitle="Controle de multas pendentes e pagamentos.">
        <button onClick={payFine} className="mb-4 rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white">pagar</button>
        <DataTable
          columns={[
            { key: 'id', label: 'Multa #' },
            { key: 'user_id', label: 'User ID' },
            { key: 'loan_id', label: 'Loan ID' },
            { key: 'amount', label: 'Valor' },
            { key: 'status', label: 'Status' }
          ]}
          rows={rows.filter((row) => row.status !== 'paid')}
          searchableFields={['id', 'user_id', 'loan_id', 'status']}
          title="Multas pendentes"
        />
      </AppShell>
    </ProtectedRoute>
  );
}
