'use client';

import { usePathname, useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { useAuth } from '../../context/AuthContext';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const storedToken = typeof window !== 'undefined' ? window.localStorage.getItem('token') : null;
  const canAccessRoute = isAuthenticated || Boolean(storedToken);

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

  return <>{children}</>;
}
