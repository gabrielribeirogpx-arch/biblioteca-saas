'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { apiFetch, getStoredLibraryId, getStoredTenantId, getStoredToken, setStoredLibraryId, setStoredTenantId, type UserRole } from '../lib/api';

interface AuthUser {
  email: string;
  role: UserRole;
}

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  libraryId: string | null;
  setLibraryId: (libraryId: string) => void;
  login: (email: string, password: string, tenantId?: string, libraryId?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function parseTokenClaims(token: string): Record<string, unknown> | null {
  const [, payload] = token.split('.');
  if (!payload) {
    return null;
  }

  try {
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function resolveRole(token: string | null): UserRole | null {
  if (!token) {
    return null;
  }

  const payload = parseTokenClaims(token);
  const role = payload?.role;
  if (typeof role === 'string' && ['super_admin', 'librarian', 'assistant', 'member'].includes(role)) {
    return role as UserRole;
  }

  return null;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [libraryId, setLibraryIdState] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') {
      setIsLoading(false);
      return;
    }

    const storedToken = getStoredToken();
    const storedEmail = window.localStorage.getItem('user_email');
    const storedLibraryId = getStoredLibraryId();
    const parsedRole = resolveRole(storedToken) ?? 'member';

    setToken(storedToken);
    setUser(storedToken && storedEmail ? { email: storedEmail, role: parsedRole } : null);
    setLibraryIdState(storedLibraryId);
    setIsLoading(false);
  }, []);

  const logout = useCallback(() => {
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem('access_token');
      window.localStorage.removeItem('token');
      window.localStorage.removeItem('tenant');
      window.localStorage.removeItem('tenant_id');
      window.localStorage.removeItem('user');
      window.localStorage.removeItem('user_email');
      window.localStorage.removeItem('library_id');
      window.dispatchEvent(new Event('auth:logout'));
      window.location.href = '/login';
    }

    setToken(null);
    setUser(null);
    setLibraryIdState(null);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const handleLogout = () => logout();
    window.addEventListener('auth:unauthorized', handleLogout);
    return () => window.removeEventListener('auth:unauthorized', handleLogout);
  }, [logout]);

  const setLibraryId = useCallback((nextLibraryId: string) => {
    setStoredLibraryId(nextLibraryId);
    setLibraryIdState(nextLibraryId);
  }, []);

  const login = useCallback(async (email: string, password: string, tenantId?: string, requestedLibraryId?: string) => {
    const resolvedTenantId = (tenantId ?? getStoredTenantId()).trim();
    const resolvedLibraryId = requestedLibraryId?.trim() || getStoredLibraryId() || '';

    if (!resolvedTenantId) {
      throw new Error('Informe o tenant para acessar sua biblioteca');
    }
    const sanitizedEmail = email.trim();
    const sanitizedPassword = password;
    let data: { access_token?: string } | null = null;
    try {
      data = await apiFetch<{ access_token?: string }>('/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': resolvedTenantId,
          ...(resolvedLibraryId ? { 'X-Library-ID': resolvedLibraryId } : {})
        },
        body: JSON.stringify({ email: sanitizedEmail, password: sanitizedPassword, tenant: resolvedTenantId })
      });
    } catch {
      throw new Error('Credenciais inválidas');
    }

    if (!data?.access_token) {
      throw new Error('Token de acesso não retornado pela API');
    }
    const normalizedToken = data.access_token.trim().replace(/^Bearer\s+/i, '');
    const payload = parseTokenClaims(normalizedToken);
    if (payload?.library_id) {
      setStoredLibraryId(String(payload.library_id));
      setLibraryIdState(String(payload.library_id));
    }

    if (typeof window !== 'undefined') {
      window.localStorage.setItem('access_token', normalizedToken);
      window.localStorage.setItem('token', normalizedToken);
      window.localStorage.setItem('user_email', sanitizedEmail);
      setStoredTenantId(resolvedTenantId);
    }

    setToken(normalizedToken);
    setUser({ email: sanitizedEmail, role: resolveRole(normalizedToken) ?? 'member' });
  }, []);

  const value = useMemo(
    () => ({ user, token, role: user?.role ?? null, libraryId, setLibraryId, isAuthenticated: Boolean(token), isLoading, login, logout }),
    [user, token, libraryId, setLibraryId, isLoading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth deve ser usado dentro de AuthProvider');
  }

  return context;
}
