'use client';

import { useAuth as useAuthContext } from '../context/AuthContext';

export function useAuth() {
  const { token, isLoading } = useAuthContext();

  return { token, loading: isLoading };
}
