'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';

import { ProtectedRoute } from '../../../components/auth/ProtectedRoute';
import { AppShell } from '../../../components/ui/AppShell';
import { useAuth } from '../../../context/AuthContext';
import { ApiError, createLibrary, getLibraries, type LibraryOption, type UserRole } from '../../../lib/api';

export default function SettingsLibrariesPage() {
  const { role } = useAuth();
  const [libraries, setLibraries] = useState<LibraryOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [name, setName] = useState('');
  const [code, setCode] = useState('');

  const isAdmin = role === 'super_admin';

  async function loadLibraries() {
    setLoading(true);
    try {
      const items = await getLibraries();
      setLibraries(items);
      setError('');
    } catch {
      setError('Erro ao carregar bibliotecas.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadLibraries();
  }, []);

  const canSubmit = useMemo(() => name.trim().length > 1 && code.trim().length > 1, [name, code]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit || isSubmitting || !isAdmin) {
      return;
    }

    setIsSubmitting(true);
    setError('');
    setSuccess('');
    try {
      await createLibrary({ name: name.trim(), code: code.trim(), is_active: true });
      setSuccess('Biblioteca criada');
      setName('');
      setCode('');
      setIsModalOpen(false);
      await loadLibraries();
      window.dispatchEvent(new Event('libraries:updated'));
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 409) {
        setError('Código já existe para este tenant.');
      } else {
        setError('Não foi possível criar a biblioteca.');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <ProtectedRoute>
      <AppShell
        role={(role ?? 'member') as UserRole}
        title="Configurações · Bibliotecas"
        subtitle="Gestão de bibliotecas por tenant com isolamento multi-tenant."
      >
        <div className="rounded-xl border bg-white p-4 shadow-sm md:p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-slate-900">Bibliotecas do Tenant</h3>
            {isAdmin ? (
              <button
                type="button"
                onClick={() => setIsModalOpen(true)}
                className="rounded-md bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800"
              >
                Nova Biblioteca
              </button>
            ) : null}
          </div>

          {success ? <p className="mb-3 rounded-md bg-emerald-50 p-2 text-sm text-emerald-700">{success}</p> : null}
          {error ? <p className="mb-3 rounded-md bg-rose-50 p-2 text-sm text-rose-700">{error}</p> : null}

          {loading ? <p className="text-sm text-slate-500">Carregando bibliotecas...</p> : null}

          {!loading ? (
            <ul className="divide-y rounded-lg border">
              {libraries.map((library) => (
                <li key={library.id} className="flex items-center justify-between gap-3 px-4 py-3">
                  <div>
                    <p className="font-medium text-slate-900">{library.name}</p>
                    <p className="text-xs text-slate-500">Código: {library.code}</p>
                  </div>
                  <span
                    className={`rounded px-2 py-1 text-xs ${
                      library.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {library.is_active ? 'Ativa' : 'Inativa'}
                  </span>
                </li>
              ))}
              {libraries.length === 0 ? (
                <li className="px-4 py-6 text-center text-sm text-slate-500">Nenhuma biblioteca cadastrada.</li>
              ) : null}
            </ul>
          ) : null}
        </div>

        {isModalOpen && isAdmin ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
            <div className="w-full max-w-md rounded-xl border bg-white p-5 shadow-xl">
              <h4 className="text-lg font-semibold text-slate-900">Nova Biblioteca</h4>
              <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
                <div>
                  <label className="text-sm text-slate-600">Nome</label>
                  <input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    placeholder="Biblioteca Central"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm text-slate-600">Código</label>
                  <input
                    value={code}
                    onChange={(event) => setCode(event.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    placeholder="central"
                    required
                  />
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="rounded-md border border-slate-300 px-4 py-2 text-sm"
                    disabled={isSubmitting}
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={!canSubmit || isSubmitting}
                    className="rounded-md bg-brand-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                  >
                    {isSubmitting ? 'Salvando...' : 'Criar'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        ) : null}
      </AppShell>
    </ProtectedRoute>
  );
}
