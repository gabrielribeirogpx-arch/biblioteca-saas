'use client';

import { useEffect, useState } from 'react';

import { useAuth } from './useAuth';
import { apiFetch } from '../lib/api';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function useApi<T>(endpoint: string) {
  const { token, loading: authLoading } = useAuth();
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: true,
    error: null
  });

  useEffect(() => {
    let isMounted = true;

    async function fetchData() {
      setState({ data: null, loading: true, error: null });

      if (authLoading) {
        return;
      }

      if (!token && endpoint.startsWith('/api/v1/')) {
        if (isMounted) {
          setState({ data: null, loading: false, error: null });
        }
        return;
      }

      try {
        const data = await apiFetch<T>(endpoint);
        if (isMounted) {
          setState({ data, loading: false, error: null });
        }
      } catch (error) {
        if (isMounted) {
          setState({
            data: null,
            loading: false,
            error: error instanceof Error ? error.message : 'Erro ao carregar dados'
          });
        }
      }
    }

    fetchData();

    return () => {
      isMounted = false;
    };
  }, [endpoint, authLoading, token]);

  return state;
}
