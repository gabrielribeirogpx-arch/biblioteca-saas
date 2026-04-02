'use client';

import { useAuth as useAuthContext } from '../context/AuthContext';

export function useAuth() {
  const { token, role, user, permissions, hasPermission, isLoading } = useAuthContext();

  return { token, role, user, permissions, hasPermission, loading: isLoading };
}
