'use client';

import { usePathname, useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { useAuth } from '../../context/AuthContext';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, libraryId } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const storedToken = typeof window !== 'undefined' ? window.localStorage.getItem('token') : null;
  const storedTenant = typeof window !== 'undefined' ? window.localStorage.getItem('tenant') : null;
  const canAccessRoute = (isAuthenticated || Boolean(storedToken)) && Boolean(storedTenant);

  useEffect(() => {
    if (isLoading) {
      return;
    }

    if (!canAccessRoute && pathname !== '/login') {
      router.replace('/login');
    }
  }, [canAccessRoute, isLoading, pathname, router]);

  if (isLoading) {
    return <div className="p-6 text-sm text-slate-600">Carregando sessão...</div>;
  }

  if (!canAccessRoute && pathname !== '/login') {
    return null;
  }

  if (!libraryId) {
    return (
      <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
        Selecione uma biblioteca para continuar usando o sistema.
      </div>
    );
  }

  return <>{children}</>;
}
