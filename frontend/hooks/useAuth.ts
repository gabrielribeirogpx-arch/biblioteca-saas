'use client';

import { useAuth as useAuthContext } from '../context/AuthContext';

export function useAuth() {
  const { token, role, user, isLoading } = useAuthContext();

  return { token, role, user, loading: isLoading };
}
