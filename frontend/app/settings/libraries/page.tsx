'use client';

import { useEffect, useState } from 'react';

import { ProtectedRoute } from '../../../components/auth/ProtectedRoute';
import { CreateLibraryModal } from '../../../components/libraries/CreateLibraryModal';
import { LibrariesTable } from '../../../components/libraries/LibrariesTable';
import { AppShell } from '../../../components/ui/AppShell';
import { Toast } from '../../../components/ui/Toast';
import { useAuth } from '../../../context/AuthContext';
import { ApiError, createLibrary, getLibraries, type LibraryOption, type UserRole } from '../../../lib/api';

const TOAST_MESSAGE = 'Biblioteca criada com sucesso';

export default function SettingsLibrariesPage() {
  const { role, libraryId, setLibraryId } = useAuth();
  const [libraries, setLibraries] = useState<LibraryOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toastMessage, setToastMessage] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const normalizedRole = (role ?? 'member') as UserRole;
  const isAdmin = role === 'super_admin' || (role as string | null) === 'admin';

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

  useEffect(() => {
    if (!toastMessage) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setToastMessage('');
    }, 3000);

    return () => window.clearTimeout(timeoutId);
  }, [toastMessage]);

  async function handleCreateLibrary(payload: { name: string; code: string }) {
    if (!isAdmin) {
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      await createLibrary({ ...payload, is_active: true });
      setToastMessage(TOAST_MESSAGE);
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
        role={normalizedRole}
        title="Bibliotecas"
        subtitle="Gerencie unidades, códigos e status de bibliotecas do tenant atual."
      >
        <div className="rounded-xl border bg-white p-4 shadow-sm md:p-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h3 className="text-lg font-semibold text-slate-900">Lista de bibliotecas</h3>

            {isAdmin ? (
              <button
                type="button"
                onClick={() => setIsModalOpen(true)}
                className="rounded-md bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800"
              >
                + Nova Biblioteca
              </button>
            ) : null}
          </div>

          {error ? <p className="mb-3 rounded-md bg-rose-50 p-2 text-sm text-rose-700">{error}</p> : null}

          <LibrariesTable
            libraries={libraries}
            loading={loading}
            selectedLibraryId={libraryId}
            onSelectLibrary={(selectedLibraryId) => setLibraryId(String(selectedLibraryId))}
          />
        </div>

        <CreateLibraryModal
          isOpen={isModalOpen && isAdmin}
          isSubmitting={isSubmitting}
          onClose={() => setIsModalOpen(false)}
          onSubmit={handleCreateLibrary}
        />

        {toastMessage ? <Toast message={toastMessage} /> : null}
      </AppShell>
    </ProtectedRoute>
  );
}
