'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { apiFetch, getStoredTenantId, setStoredTenantId } from '../lib/api';

interface AuthUser {
  email: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string, tenantId?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (typeof window === 'undefined') {
      setIsLoading(false);
      return;
    }

    const storedToken = window.localStorage.getItem('access_token') ?? window.localStorage.getItem('token');
    const storedEmail = window.localStorage.getItem('user_email');

    setToken(storedToken);
    setUser(storedEmail ? { email: storedEmail } : null);
    setIsLoading(false);
  }, []);

  const login = useCallback(async (email: string, password: string, tenantId?: string) => {
    const resolvedTenantId = (tenantId ?? getStoredTenantId()).trim();

    if (!resolvedTenantId) {
      throw new Error('Informe o tenant para acessar sua biblioteca');
    }
    const sanitizedEmail = email.trim();
    const sanitizedPassword = password;
    let data: { access_token?: string } | null = null;
    try {
      data = await apiFetch<{ access_token?: string }>(`/api/v1/auth/login?tenant=${encodeURIComponent(resolvedTenantId)}`, {
        method: 'POST',
        headers: {
          'X-Tenant-ID': resolvedTenantId
        },
        body: JSON.stringify({ email: sanitizedEmail, password: sanitizedPassword })
      });
    } catch {
      throw new Error('Credenciais inválidas');
    }

    if (!data?.access_token) {
      throw new Error('Token de acesso não retornado pela API');
    }

    if (typeof window !== 'undefined') {
      window.localStorage.setItem('access_token', data.access_token);
      window.localStorage.setItem('token', data.access_token);
      window.localStorage.setItem('user_email', sanitizedEmail);
      setStoredTenantId(resolvedTenantId);
    }

    setToken(data.access_token);
    setUser({ email: sanitizedEmail });
  }, []);

  const logout = useCallback(() => {
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem('access_token');
      window.localStorage.removeItem('token');
      window.localStorage.removeItem('user_email');
      window.localStorage.removeItem('tenant');
      window.localStorage.removeItem('tenant_id');
    }

    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, token, isAuthenticated: Boolean(token), isLoading, login, logout }),
    [user, token, isLoading, login, logout]
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
