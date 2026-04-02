'use client';

import { useCallback, useEffect, useState } from 'react';

import { ProtectedRoute } from '../../components/auth/ProtectedRoute';
import { AppShell } from '../../components/ui/AppShell';
import { Toast } from '../../components/ui/Toast';
import { useAuth } from '../../hooks/useAuth';
import { apiFetch, type Loan } from '../../lib/api';

const ACTIVE_LOAN_STATUSES = new Set(['active', 'open', 'loaned', 'overdue']);

const formatDate = (isoDate: string): string => {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) {
    return isoDate;
  }
  return date.toLocaleDateString('pt-BR');
};

export default function ReturnsPage() {
  const { token, role, loading } = useAuth();
  const [loans, setLoans] = useState<Loan[]>([]);
  const [loadingData, setLoadingData] = useState(true);
  const [processingId, setProcessingId] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadLoans = useCallback(async () => {
    if (!token) {
      return;
    }

    setLoadingData(true);
    setErrorMessage(null);

    try {
      const response = await apiFetch<{ items: Loan[] }>('/api/loans/?page=1&page_size=100');
      const active = (response?.items ?? []).filter((loan) => ACTIVE_LOAN_STATUSES.has(loan.status.toLowerCase()));
      setLoans(active);
    } catch {
      setLoans([]);
      setErrorMessage('Não foi possível carregar os empréstimos para devolução.');
    } finally {
      setLoadingData(false);
    }
  }, [token]);

  useEffect(() => {
    if (loading || !token) {
      return;
    }

    void loadLoans();
  }, [loading, token, loadLoans]);

  useEffect(() => {
    if (!successMessage) {
      return;
    }
    const timeout = window.setTimeout(() => setSuccessMessage(null), 3000);
    return () => window.clearTimeout(timeout);
  }, [successMessage]);

  const returnLoan = async (loanId: number) => {
    setProcessingId(loanId);
    setErrorMessage(null);

    try {
      await apiFetch(`/api/loans/returns/${loanId}`, { method: 'POST' });
      setSuccessMessage(`Empréstimo #${loanId} devolvido com sucesso.`);
      await loadLoans();
    } catch {
      setErrorMessage(`Falha ao devolver empréstimo #${loanId}.`);
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <ProtectedRoute>
      <AppShell
        role={role ?? 'member'}
        title="Devoluções"
        subtitle="Finalize empréstimos ativos e mantenha a circulação atualizada em tempo real."
      >
        {successMessage ? <Toast message={successMessage} /> : null}

        <article className="rounded-xl border bg-white p-4 shadow-sm md:p-6">
          <header className="mb-4">
            <h3 className="text-lg font-semibold text-slate-900">Empréstimos ativos</h3>
            <p className="text-sm text-slate-600">Selecione um empréstimo para registrar a devolução imediata.</p>
          </header>

          {loadingData ? <p className="text-sm text-slate-600">Carregando devoluções...</p> : null}
          {errorMessage ? <p className="mb-3 text-sm font-medium text-rose-700">{errorMessage}</p> : null}

          {!loadingData && loans.length === 0 ? (
            <p className="text-sm text-slate-600">Nenhum empréstimo ativo encontrado.</p>
          ) : (
            <ul className="space-y-3">
              {loans.map((loan) => (
                <li key={loan.id} className="flex flex-col gap-3 rounded-lg border border-slate-200 p-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="font-semibold text-slate-900">Empréstimo #{loan.id}</p>
                    <p className="text-sm text-slate-600">Usuário {String(loan.user_id)} · Exemplar #{loan.copy_id}</p>
                    <p className="text-xs text-slate-500">Previsto para {formatDate(loan.due_date)} · status: {loan.status}</p>
                  </div>
                  <button
                    type="button"
                    className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={processingId === loan.id}
                    onClick={() => void returnLoan(loan.id)}
                  >
                    {processingId === loan.id ? 'Processando...' : 'Devolver'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </article>
      </AppShell>
    </ProtectedRoute>
  );
}
