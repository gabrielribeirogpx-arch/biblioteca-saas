'use client';

import { useEffect, useMemo, useState } from 'react';

import { useAuth } from '../context/AuthContext';
import { apiFetch, type LibraryOption } from '../lib/api';

interface StoredUser {
  email?: string;
  name?: string;
  full_name?: string;
}

function parseTenantIdFromToken(token: string | null): string | null {
  if (!token) {
    return null;
  }

  const [, payload] = token.split('.');
  if (!payload) {
    return null;
  }

  try {
    const normalizedPayload = payload.replace(/-/g, '+').replace(/_/g, '/');
    const claims = JSON.parse(atob(normalizedPayload)) as { tenant_id?: number | string };

    if (claims.tenant_id == null) {
      return null;
    }

    return String(claims.tenant_id);
  } catch {
    return null;
  }
}

async function getDropdownLibraries(): Promise<LibraryOption[]> {
  const libraries = await apiFetch<LibraryOption[]>('/api/v1/libraries');
  return Array.isArray(libraries) ? libraries : [];
}

export function UserMenu() {
  const { logout, isAuthenticated, libraryId, setLibraryId } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [tenantId, setTenantId] = useState('');
  const [nextLibraryId, setNextLibraryId] = useState('');
  const [libraries, setLibraries] = useState<LibraryOption[]>([]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const storedEmail = window.localStorage.getItem('user_email') ?? '';
    const rawUser = window.localStorage.getItem('user');
    const token = window.localStorage.getItem('access_token') ?? window.localStorage.getItem('token');

    let parsedUser: StoredUser | null = null;

    if (rawUser) {
      try {
        parsedUser = JSON.parse(rawUser) as StoredUser;
      } catch {
        parsedUser = null;
      }
    }

    setTenantId(parseTenantIdFromToken(token) ?? '');
    setNextLibraryId(libraryId ?? '');
    setEmail(parsedUser?.email ?? storedEmail);
    setName(parsedUser?.name ?? parsedUser?.full_name ?? '');
  }, [isAuthenticated, libraryId]);

  useEffect(() => {
    let isMounted = true;

    async function loadLibraries() {
      if (!isAuthenticated) {
        if (isMounted) {
          setLibraries([]);
        }
        return;
      }

      try {
        const allLibraries = await getDropdownLibraries();

        if (!isMounted) {
          return;
        }

        const filteredLibraries = tenantId
          ? allLibraries.filter((library) => String(library.tenant_id) === tenantId)
          : allLibraries;

        setLibraries(filteredLibraries);

        if (!libraryId && filteredLibraries.length > 0) {
          const firstLibraryId = String(filteredLibraries[0].id);
          void setLibraryId(firstLibraryId);
          setNextLibraryId(firstLibraryId);
        }
      } catch {
        if (isMounted) {
          setLibraries([]);
        }
      }
    }

    void loadLibraries();

    const handleLibrariesUpdated = () => {
      void loadLibraries();
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('libraries:updated', handleLibrariesUpdated);
    }

    return () => {
      isMounted = false;
      if (typeof window !== 'undefined') {
        window.removeEventListener('libraries:updated', handleLibrariesUpdated);
      }
    };
  }, [isAuthenticated, libraryId, setLibraryId, tenantId]);

  const displayName = useMemo(() => {
    if (name.trim()) {
      return name;
    }

    return email || 'Usuário';
  }, [email, name]);

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen((previous) => !previous)}
        className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
      >
        {displayName}
      </button>

      {isOpen ? (
        <div className="absolute right-0 z-50 mt-2 w-64 rounded-md border border-slate-200 bg-white p-3 shadow-lg">
          <p className="text-sm font-semibold text-slate-900">{displayName}</p>
          {email ? <p className="text-xs text-slate-600">{email}</p> : null}
          {tenantId ? <p className="mt-1 text-xs text-slate-500">Tenant ID: {tenantId}</p> : null}
          <div className="mt-2">
            <label className="text-xs text-slate-500">Biblioteca</label>
            {!libraryId ? <p className="mt-1 text-xs text-amber-700">Selecione uma biblioteca</p> : null}
            <select
              value={nextLibraryId}
              onChange={async (event) => {
                const selectedLibraryId = event.target.value;
                setNextLibraryId(selectedLibraryId);
                if (selectedLibraryId) {
                  try {
                    await setLibraryId(selectedLibraryId);
                  } catch {
                    setNextLibraryId(libraryId ?? '');
                  }
                }
              }}
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs"
            >
              <option value="">Selecione uma biblioteca</option>
              {libraries.map((library) => (
                <option key={library.id} value={library.id}>
                  {library.name}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            className="mt-3 w-full rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700"
            onClick={() => {
              if (window.confirm('Deseja sair?')) {
                logout();
              }
            }}
          >
            Sair
          </button>
        </div>
      ) : null}
    </div>
  );
}
