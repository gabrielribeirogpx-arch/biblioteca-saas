'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import {
  apiFetch,
  getStoredToken,
  setStoredToken,
  switchLibrary,
  type UserRole
} from '../lib/api';
import { useLibrary } from './LibraryContext';

interface AuthUser {
  id: number;
  email: string;
  role: UserRole;
  permissions: string[];
}

interface LoginResponse {
  access_token?: string;
  user?: AuthUser;
}

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  role: UserRole | null;
  permissions: string[];
  hasPermission: (permissionCode: string) => boolean;
  isAuthenticated: boolean;
  isLoading: boolean;
  libraryId: string | null;
  setLibraryId: (libraryId: string, options?: { reload?: boolean }) => Promise<void>;
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

function parseStoredUser(): AuthUser | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const rawUser = window.localStorage.getItem('user');
  if (!rawUser) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawUser) as Partial<AuthUser>;
    if (
      typeof parsed?.id === 'number'
      && typeof parsed?.email === 'string'
      && typeof parsed?.role === 'string'
      && ['super_admin', 'librarian', 'assistant', 'member'].includes(parsed.role)
    ) {
      return {
        id: parsed.id,
        email: parsed.email,
        role: parsed.role as UserRole,
        permissions: Array.isArray(parsed.permissions) ? parsed.permissions.filter((item): item is string => typeof item === 'string') : []
      };
    }
  } catch {
    return null;
  }

  return null;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const library = useLibrary();
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (typeof window === 'undefined') {
      setIsLoading(false);
      return;
    }

    const storedToken = getStoredToken();
    const storedUser = parseStoredUser();
    setToken(storedToken);
    if (storedToken && storedUser) {
      setUser(storedUser);
    } else {
      setUser(null);
    }
    const claims = storedToken ? parseTokenClaims(storedToken) : null;
    if (claims?.library_id != null) {
      library.setLibraryId(String(claims.library_id));
    }
    setIsLoading(false);
  }, [library]);

  const logout = useCallback(() => {
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem('access_token');
      window.localStorage.removeItem('token');
      window.localStorage.removeItem('user_email');
      window.localStorage.removeItem('library_id');
      window.dispatchEvent(new Event('auth:logout'));
      window.location.href = '/login';
    }

    setToken(null);
    setUser(null);
    library.setLibraryId(null);
  }, [library]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const handleLogout = () => logout();
    window.addEventListener('auth:unauthorized', handleLogout);
    return () => window.removeEventListener('auth:unauthorized', handleLogout);
  }, [logout]);

  const setLibraryId = useCallback(async (nextLibraryId: string, options?: { reload?: boolean }) => {
    const normalizedLibraryId = nextLibraryId.trim();
    if (!normalizedLibraryId) {
      return;
    }

    const updatedToken = await switchLibrary(normalizedLibraryId);
    setToken(updatedToken);
    const claims = parseTokenClaims(updatedToken);
    const switchedPermissions = Array.isArray(claims?.permissions)
      ? claims.permissions.filter((item): item is string => typeof item === 'string')
      : [];
    const switchedRole = typeof claims?.role === 'string' && ['super_admin', 'librarian', 'assistant', 'member'].includes(claims.role)
      ? (claims.role as UserRole)
      : user?.role ?? 'member';

    if (user) {
      const updatedUser = { ...user, role: switchedRole, permissions: switchedPermissions };
      setUser(updatedUser);
      if (typeof window !== 'undefined') {
        window.localStorage.setItem('user', JSON.stringify(updatedUser));
      }
    }

    library.setLibraryId(normalizedLibraryId);
    if (options?.reload && typeof window !== 'undefined') {
      window.location.reload();
    }
  }, [library, user]);

  const login = useCallback(async (email: string, password: string, _tenantId?: string, requestedLibraryId?: string) => {
    const resolvedLibraryId = requestedLibraryId?.trim() || library.libraryId || '';
    const sanitizedEmail = email.trim();
    const sanitizedPassword = password;
    let data: LoginResponse | null = null;
    try {
      data = await apiFetch<LoginResponse>('/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(resolvedLibraryId ? { 'X-Library-ID': resolvedLibraryId } : {})
        },
        body: JSON.stringify({ email: sanitizedEmail, password: sanitizedPassword })
      });
    } catch {
      throw new Error('Credenciais inválidas');
    }

    console.log('LOGIN RESPONSE', data);

    if (!data?.access_token || !data?.user) {
      throw new Error('Token de acesso não retornado pela API');
    }
    const normalizedToken = data.access_token.trim().replace(/^Bearer\s+/i, '');
    const payload = parseTokenClaims(normalizedToken);
    if (payload?.library_id) {
      library.setLibraryId(String(payload.library_id));
    }

    if (typeof window !== 'undefined') {
      setStoredToken(normalizedToken);
      console.log('TOKEN SAVED', window.localStorage.getItem('token'));
      window.localStorage.setItem('user', JSON.stringify(data.user));
      window.localStorage.setItem('user_email', data.user.email);
    }

    setToken(normalizedToken);
    const tokenPermissions = Array.isArray(payload?.permissions) ? payload.permissions.filter((item): item is string => typeof item === 'string') : [];
    const resolvedPermissions = Array.isArray(data.user.permissions) ? data.user.permissions : tokenPermissions;

    setUser({
      id: data.user.id,
      email: data.user.email,
      role: data.user.role ?? resolveRole(normalizedToken) ?? 'member',
      permissions: resolvedPermissions
    });
  }, [library]);

  const hasPermission = useCallback((permissionCode: string) => {
    const normalizedCode = permissionCode.trim();
    if (!normalizedCode) {
      return false;
    }

    return Boolean(user?.permissions?.includes(normalizedCode));
  }, [user]);

  const value = useMemo(
    () => ({
      user,
      token,
      role: user?.role ?? null,
      permissions: user?.permissions ?? [],
      hasPermission,
      libraryId: library.libraryId,
      setLibraryId,
      isAuthenticated: Boolean(token && user),
      isLoading,
      login,
      logout
    }),
    [user, token, hasPermission, library.libraryId, setLibraryId, isLoading, login, logout]
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
