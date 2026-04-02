'use client';

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';

import { ProtectedRoute } from '../../components/auth/ProtectedRoute';
import { AppShell } from '../../components/ui/AppShell';
import { DataTable } from '../../components/ui/DataTable';
import { Toast } from '../../components/ui/Toast';
import { useAuth } from '../../hooks/useAuth';
import { apiFetch, getCopies, getUsers, searchCopies, type Copy, type Loan, type User } from '../../lib/api';

interface LoanRow {
  [key: string]: string | number | null | undefined;
  id: number;
  copy_id: number;
  user_id: string;
  due_date: string;
  status: string;
}

const ACTIVE_LOAN_STATUSES = new Set(['active', 'open', 'loaned', 'overdue']);

const formatDate = (isoDate: string): string => {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) {
    return isoDate;
  }
  return date.toLocaleDateString('pt-BR');
};

const asLoanRows = (loans: Loan[]): LoanRow[] =>
  loans.map((loan) => ({
    id: loan.id,
    copy_id: loan.copy_id,
    user_id: String(loan.user_id),
    due_date: formatDate(loan.due_date),
    status: loan.status
  }));

export default function LoansPage() {
  const { token, role, loading } = useAuth();
  const [rows, setRows] = useState<LoanRow[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [copies, setCopies] = useState<Copy[]>([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [selectedCopyId, setSelectedCopyId] = useState('');
  const [copySearch, setCopySearch] = useState('');
  const [loadingData, setLoadingData] = useState(true);
  const [submittingLoan, setSubmittingLoan] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!token) {
      return;
    }

    setLoadingData(true);
    setErrorMessage(null);

    try {
      const [loanResponse, usersResponse, copyResponse] = await Promise.all([
        apiFetch<{ items: Loan[] }>('/api/loans/?page=1&page_size=100'),
        getUsers(1, 100),
        getCopies()
      ]);

      const activeLoans = (loanResponse?.items ?? []).filter((loan) =>
        ACTIVE_LOAN_STATUSES.has(loan.status.toLowerCase())
      );

      setRows(asLoanRows(activeLoans));
      setUsers(usersResponse.items);
      setCopies(copyResponse);
    } catch {
      setRows([]);
      setErrorMessage('Não foi possível carregar empréstimos ativos.');
    } finally {
      setLoadingData(false);
    }
  }, [token]);

  useEffect(() => {
    if (loading || !token) {
      return;
    }

    void loadData();
  }, [loading, token, loadData]);

  useEffect(() => {
    if (!successMessage) {
      return;
    }

    const timeout = window.setTimeout(() => setSuccessMessage(null), 3500);
    return () => window.clearTimeout(timeout);
  }, [successMessage]);

  useEffect(() => {
    if (!token) {
      return;
    }

    const timeout = window.setTimeout(() => {
      void searchCopies(copySearch)
        .then((result) => setCopies(result))
        .catch(() => {
          setErrorMessage('Não foi possível buscar exemplares.');
        });
    }, 250);

    return () => window.clearTimeout(timeout);
  }, [copySearch, token]);

  const filteredCopies = useMemo(() => copies, [copies]);

  const createLoan = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const userId = Number(selectedUserId);
    const copyId = Number(selectedCopyId);

    if (!userId || !copyId) {
      setErrorMessage('Selecione usuário e exemplar para registrar o empréstimo.');
      return;
    }

    setSubmittingLoan(true);
    setErrorMessage(null);

    try {
      await apiFetch('/api/loans/', {
        method: 'POST',
        body: JSON.stringify({ user_id: userId, copy_id: copyId })
      });

      setSelectedCopyId('');
      setCopySearch('');
      setSuccessMessage('Empréstimo registrado com sucesso.');
      await loadData();
    } catch {
      setErrorMessage('Falha ao registrar empréstimo. Verifique regras de circulação e tente novamente.');
    } finally {
      setSubmittingLoan(false);
    }
  };

  return (
    <ProtectedRoute>
      <AppShell
        role={role ?? 'member'}
        title="Empréstimos"
        subtitle="Controle de circulação com empréstimos ativos, cadastro rápido e histórico operacional."
      >
        {successMessage ? <Toast message={successMessage} /> : null}

        <article className="rounded-xl border bg-white p-4 shadow-sm md:p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-slate-900">Novo empréstimo</h3>
            <p className="text-sm text-slate-600">Selecione usuário e exemplar (barcode ou ID) para processar o empréstimo.</p>
          </div>

          <form className="grid gap-4 md:grid-cols-2" onSubmit={createLoan}>
            <label className="text-sm font-medium text-slate-700">
              Usuário
              <select
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                value={selectedUserId}
                onChange={(event) => setSelectedUserId(event.target.value)}
              >
                <option value="">Selecione um usuário</option>
                {users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.full_name} ({user.email})
                  </option>
                ))}
              </select>
            </label>

            <div>
              <label className="text-sm font-medium text-slate-700">
                Buscar exemplar (barcode ou ID)
                <input
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  placeholder="Ex.: 000123 ou 345"
                  value={copySearch}
                  onChange={(event) => setCopySearch(event.target.value)}
                />
              </label>
              <label className="mt-3 block text-sm font-medium text-slate-700">
                Exemplar
                <select
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  value={selectedCopyId}
                  onChange={(event) => setSelectedCopyId(event.target.value)}
                >
                  <option value="">Selecione um exemplar</option>
                  {filteredCopies.map((copy) => (
                    <option key={copy.id} value={copy.id}>
                      #{copy.id} {copy.barcode ? `- ${copy.barcode}` : '- sem barcode'}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="md:col-span-2">
              <button
                type="submit"
                disabled={submittingLoan}
                className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submittingLoan ? 'Processando...' : 'Emprestar'}
              </button>
            </div>
          </form>

          {errorMessage ? <p className="mt-3 text-sm font-medium text-rose-700">{errorMessage}</p> : null}
        </article>

        {loadingData ? <p className="text-sm text-slate-600">Carregando empréstimos ativos...</p> : null}

        <DataTable
          columns={[
            { key: 'id', label: 'Empréstimo #' },
            { key: 'copy_id', label: 'Exemplar' },
            { key: 'user_id', label: 'Usuário' },
            { key: 'due_date', label: 'Data de devolução' },
            { key: 'status', label: 'Status' }
          ]}
          description="Lista de empréstimos ativos da biblioteca."
          rows={rows}
          searchableFields={['id', 'copy_id', 'user_id', 'status']}
          title="Empréstimos ativos"
        />
      </AppShell>
    </ProtectedRoute>
  );
}
