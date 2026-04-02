'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';

import { ProtectedRoute } from '../../../components/auth/ProtectedRoute';
import { AppShell } from '../../../components/ui/AppShell';
import { Toast } from '../../../components/ui/Toast';
import { useAuth } from '../../../context/AuthContext';
import { ApiError, apiFetch, getLibraries, type LibraryOption, type UserRole } from '../../../lib/api';

const SUCCESS_MESSAGE = 'Biblioteca criada com sucesso.';

function parseTenantIdFromToken(token: string | null): string | null {
  if (!token) {
    return null;
  }

  const [, payload] = token.split('.');
  if (!payload) {
    return null;
  }

  try {
    const claims = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))) as { tenant_id?: number | string };
    return claims.tenant_id == null ? null : String(claims.tenant_id);
  } catch {
    return null;
  }
}

async function createLibraryWithName(name: string): Promise<LibraryOption | null> {
  return await apiFetch<LibraryOption>('/api/v1/libraries', {
    method: 'POST',
    body: JSON.stringify({ name })
  });
}

function getStatusLabel(isActive: boolean): string {
  return isActive ? 'Ativo' : 'Inativo';
}

export default function SettingsLibrariesPage() {
  const { role, token } = useAuth();
  const [libraries, setLibraries] = useState<LibraryOption[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [name, setName] = useState('');
  const [showValidation, setShowValidation] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toastMessage, setToastMessage] = useState('');

  const normalizedRole = (role ?? 'member') as UserRole;
  const isAdmin = role === 'super_admin';
  const tenantId = useMemo(() => parseTenantIdFromToken(token), [token]);

  async function loadLibraries() {
    if (!isAdmin) {
      setLoadingList(false);
      return;
    }

    setLoadingList(true);

    try {
      const items = await getLibraries();
      const filteredItems = tenantId ? items.filter((library) => String(library.tenant_id) === tenantId) : items;
      setLibraries(filteredItems);
      setError('');
    } catch {
      setError('Erro ao carregar bibliotecas.');
    } finally {
      setLoadingList(false);
    }
  }

  useEffect(() => {
    void loadLibraries();
  }, [isAdmin, tenantId]);

  useEffect(() => {
    if (!toastMessage) {
      return;
    }

    const timeoutId = window.setTimeout(() => setToastMessage(''), 3000);
    return () => window.clearTimeout(timeoutId);
  }, [toastMessage]);

  const canSubmit = name.trim().length > 0;

  async function handleCreateLibrary(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setShowValidation(true);

    if (!canSubmit || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      await createLibraryWithName(name.trim());
      setToastMessage(SUCCESS_MESSAGE);
      setShowModal(false);
      setName('');
      setShowValidation(false);
      await loadLibraries();
      window.dispatchEvent(new Event('libraries:updated'));
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 409) {
        setError('Já existe uma biblioteca com este nome para o tenant atual.');
      } else {
        setError('Não foi possível criar a biblioteca.');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <ProtectedRoute>
      <AppShell role={normalizedRole} title="Bibliotecas" subtitle="Gerencie as bibliotecas do tenant.">
        {!isAdmin ? (
          <div className="rounded-xl border bg-white p-4 text-sm text-rose-700 shadow-sm md:p-6">
            Acesso restrito. Somente ADMIN pode acessar esta página.
          </div>
        ) : (
          <div className="rounded-xl border bg-white p-4 shadow-sm md:p-6">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h3 className="text-lg font-semibold text-slate-900">Bibliotecas</h3>
              <button
                type="button"
                onClick={() => {
                  setShowModal(true);
                  setShowValidation(false);
                }}
                className="rounded-md bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800"
              >
                + Nova Biblioteca
              </button>
            </div>

            {error ? <p className="mb-3 rounded-md bg-rose-50 p-2 text-sm text-rose-700">{error}</p> : null}

            {loadingList ? <p className="text-sm text-slate-500">Carregando bibliotecas...</p> : null}

            {!loadingList ? (
              <div className="overflow-x-auto rounded-lg border">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-3 text-left font-semibold text-slate-700">Nome</th>
                      <th className="px-4 py-3 text-left font-semibold text-slate-700">ID</th>
                      <th className="px-4 py-3 text-left font-semibold text-slate-700">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {libraries.map((library) => (
                      <tr key={library.id}>
                        <td className="px-4 py-3 font-medium text-slate-900">{library.name}</td>
                        <td className="px-4 py-3 text-slate-600">{library.id}</td>
                        <td className="px-4 py-3">
                          <span
                            className={`rounded px-2 py-1 text-xs ${
                              library.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'
                            }`}
                          >
                            {getStatusLabel(library.is_active)}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {libraries.length === 0 ? (
                      <tr>
                        <td className="px-4 py-6 text-center text-sm text-slate-500" colSpan={3}>
                          Nenhuma biblioteca cadastrada.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        )}

        {showModal && isAdmin ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
            <div className="w-full max-w-md rounded-xl border bg-white p-5 shadow-xl">
              <h4 className="text-lg font-semibold text-slate-900">Nova Biblioteca</h4>

              <form className="mt-4 space-y-3" onSubmit={(event) => void handleCreateLibrary(event)}>
                <div>
                  <label className="text-sm text-slate-600">Nome</label>
                  <input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    placeholder="Biblioteca Central"
                    required
                    autoFocus
                  />
                  {showValidation && !canSubmit ? (
                    <p className="mt-1 text-xs text-rose-700">O campo Nome é obrigatório.</p>
                  ) : null}
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setShowModal(false);
                      setName('');
                      setShowValidation(false);
                    }}
                    className="rounded-md border border-slate-300 px-4 py-2 text-sm"
                    disabled={isSubmitting}
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={!canSubmit || isSubmitting}
                    className="rounded-md bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-60"
                  >
                    {isSubmitting ? 'Salvando...' : 'Salvar'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        ) : null}

        {toastMessage ? <Toast message={toastMessage} /> : null}
      </AppShell>
    </ProtectedRoute>
  );
}
