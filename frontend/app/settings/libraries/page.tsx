'use client';

import { useEffect, useState } from 'react';

import { ProtectedRoute } from '../../../components/auth/ProtectedRoute';
import { CreateLibraryModal } from '../../../components/libraries/CreateLibraryModal';
import { LibrariesTable } from '../../../components/libraries/LibrariesTable';
import { AppShell } from '../../../components/ui/AppShell';
import { Toast } from '../../../components/ui/Toast';
import { useAuth } from '../../../context/AuthContext';
import { ApiError, createLibrary, getLibraries, getStoredToken, type LibraryOption, type UserRole } from '../../../lib/api';

const TOAST_MESSAGE = 'Biblioteca criada com sucesso';

function toSlug(rawValue: string): string {
  return rawValue
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function getTokenTenantId(): string | null {
  const token = getStoredToken();

  if (!token) {
    return null;
  }

  const [, payload] = token.split('.');
  if (!payload) {
    return null;
  }

  try {
    const claims = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))) as { tenant_id?: string | number };
    return claims.tenant_id != null ? String(claims.tenant_id) : null;
  } catch {
    return null;
  }
}

export default function SettingsLibrariesPage() {
  const { role } = useAuth();
  const [libraries, setLibraries] = useState<LibraryOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toastMessage, setToastMessage] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const normalizedRole = (role ?? 'member') as UserRole;
  const isAdmin = role === 'super_admin';

  async function loadLibraries() {
    setLoading(true);

    try {
      const items = await getLibraries();
      const tenantIdFromToken = getTokenTenantId();
      const tenantScopedItems = tenantIdFromToken
        ? items.filter((library) => String(library.tenant_id) === tenantIdFromToken)
        : items;

      setLibraries(tenantScopedItems);
      setError('');
    } catch {
      setError('Erro ao carregar bibliotecas.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!isAdmin) {
      setLoading(false);
      return;
    }

    void loadLibraries();
  }, [isAdmin]);

  useEffect(() => {
    if (!toastMessage) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setToastMessage('');
    }, 3000);

    return () => window.clearTimeout(timeoutId);
  }, [toastMessage]);

  async function handleCreateLibrary(payload: { name: string }) {
    if (!isAdmin) {
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      const generatedCode = toSlug(payload.name);

      await createLibrary({ name: payload.name, code: generatedCode, is_active: true });
      setToastMessage(TOAST_MESSAGE);
      setIsModalOpen(false);
      await loadLibraries();
      window.dispatchEvent(new Event('libraries:updated'));
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 409) {
        setError('Já existe uma biblioteca com esse nome para este tenant.');
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
        subtitle="Gerencie bibliotecas do tenant atual com isolamento multi-tenant."
      >
        {!isAdmin ? (
          <div className="rounded-xl border bg-white p-4 text-sm text-rose-700 shadow-sm md:p-6">
            Acesso restrito. Apenas usuários ADMIN podem gerenciar bibliotecas.
          </div>
        ) : (
          <div className="rounded-xl border bg-white p-4 shadow-sm md:p-6">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h3 className="text-lg font-semibold text-slate-900">Bibliotecas</h3>

              <button
                type="button"
                onClick={() => setIsModalOpen(true)}
                className="rounded-md bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800"
              >
                + Nova Biblioteca
              </button>
            </div>

            {error ? <p className="mb-3 rounded-md bg-rose-50 p-2 text-sm text-rose-700">{error}</p> : null}

            <LibrariesTable libraries={libraries} loading={loading} />
          </div>
        )}

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
