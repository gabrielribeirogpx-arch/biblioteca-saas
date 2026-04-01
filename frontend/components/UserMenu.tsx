'use client';

import { useEffect, useMemo, useState } from 'react';

import { useAuth } from '../context/AuthContext';

interface StoredUser {
  email?: string;
  name?: string;
  full_name?: string;
}

export function UserMenu() {
  const { logout, isAuthenticated } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [tenant, setTenant] = useState('');

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const storedTenant = window.localStorage.getItem('tenant') ?? window.localStorage.getItem('tenant_id') ?? '';
    const storedEmail = window.localStorage.getItem('user_email') ?? '';
    const rawUser = window.localStorage.getItem('user');

    let parsedUser: StoredUser | null = null;

    if (rawUser) {
      try {
        parsedUser = JSON.parse(rawUser) as StoredUser;
      } catch {
        parsedUser = null;
      }
    }

    setTenant(storedTenant);
    setEmail(parsedUser?.email ?? storedEmail);
    setName(parsedUser?.name ?? parsedUser?.full_name ?? '');
  }, [isAuthenticated]);

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
          {tenant ? <p className="mt-1 text-xs text-slate-500">Tenant: {tenant}</p> : null}

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
