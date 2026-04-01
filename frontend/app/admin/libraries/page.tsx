'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';

import { ProtectedRoute } from '../../../components/auth/ProtectedRoute';
import { AppShell } from '../../../components/ui/AppShell';
import {
  ApiError,
  createLibrary,
  deleteLibrary,
  getLibraries,
  type LibraryOption,
  updateLibrary
} from '../../../lib/api';

type ModalMode = 'create' | 'edit';

export default function AdminLibrariesPage() {
  const [libraries, setLibraries] = useState<LibraryOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalMode, setModalMode] = useState<ModalMode>('create');
  const [editingLibraryId, setEditingLibraryId] = useState<number | null>(null);

  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [isActive, setIsActive] = useState(true);

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

  function resetModal() {
    setName('');
    setCode('');
    setIsActive(true);
    setEditingLibraryId(null);
    setModalMode('create');
  }

  function openCreateModal() {
    resetModal();
    setError('');
    setSuccess('');
    setIsModalOpen(true);
  }

  function openEditModal(library: LibraryOption) {
    setName(library.name);
    setCode(library.code);
    setIsActive(library.is_active);
    setEditingLibraryId(library.id);
    setModalMode('edit');
    setError('');
    setSuccess('');
    setIsModalOpen(true);
  }

  async function handleSubmitLibrary(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!canSubmit || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setError('');
    setSuccess('');

    try {
      if (modalMode === 'edit' && editingLibraryId) {
        await updateLibrary(editingLibraryId, { name: name.trim(), code: code.trim(), is_active: isActive });
        setSuccess('Biblioteca atualizada com sucesso.');
      } else {
        await createLibrary({
          name: name.trim(),
          code: code.trim(),
          is_active: isActive
        });
        setSuccess('Biblioteca criada com sucesso.');
      }

      setIsModalOpen(false);
      resetModal();
      await loadLibraries();
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('libraries:updated'));
      }
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 409) {
        setError('Código já existe para este tenant.');
      } else {
        setError('Não foi possível salvar a biblioteca.');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDeleteLibrary(libraryId: number) {
    if (!window.confirm('Deseja realmente excluir esta biblioteca?')) {
      return;
    }

    try {
      await deleteLibrary(libraryId);
      setSuccess('Biblioteca removida com sucesso.');
      await loadLibraries();
    } catch {
      setError('Não foi possível remover a biblioteca.');
    }
  }

  return (
    <ProtectedRoute>
      <AppShell role="super_admin" title="Admin · Bibliotecas" subtitle="Gestão completa de bibliotecas por tenant.">
        <div className="rounded-xl border bg-white p-4 shadow-sm md:p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-slate-900">Bibliotecas do Tenant</h3>
            <button
              type="button"
              onClick={openCreateModal}
              className="rounded-md bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800"
            >
              Nova Biblioteca
            </button>
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
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded px-2 py-1 text-xs ${
                        library.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {library.is_active ? 'Ativa' : 'Inativa'}
                    </span>
                    <button
                      type="button"
                      onClick={() => openEditModal(library)}
                      className="rounded border border-slate-300 px-3 py-1 text-xs"
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDeleteLibrary(library.id)}
                      className="rounded border border-rose-300 px-3 py-1 text-xs text-rose-600"
                    >
                      Deletar
                    </button>
                  </div>
                </li>
              ))}
              {libraries.length === 0 ? (
                <li className="px-4 py-6 text-center text-sm text-slate-500">Nenhuma biblioteca cadastrada.</li>
              ) : null}
            </ul>
          ) : null}
        </div>

        {isModalOpen ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
            <div className="w-full max-w-md rounded-xl border bg-white p-5 shadow-xl">
              <h4 className="text-lg font-semibold text-slate-900">
                {modalMode === 'edit' ? 'Editar Biblioteca' : 'Nova Biblioteca'}
              </h4>

              <form className="mt-4 space-y-3" onSubmit={handleSubmitLibrary}>
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
                <div>
                  <label className="text-sm text-slate-600">Status</label>
                  <select
                    value={isActive ? 'active' : 'inactive'}
                    onChange={(event) => setIsActive(event.target.value === 'active')}
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  >
                    <option value="active">Ativa</option>
                    <option value="inactive">Inativa</option>
                  </select>
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setIsModalOpen(false);
                      resetModal();
                    }}
                    className="rounded-md border border-slate-300 px-4 py-2 text-sm"
                    disabled={isSubmitting}
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="rounded-md bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={!canSubmit || isSubmitting}
                  >
                    {isSubmitting ? 'Salvando...' : 'Salvar biblioteca'}
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
