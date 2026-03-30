'use client';

import { useEffect, useState } from 'react';

import { apiFetch } from '../lib/api';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function useApi<T>(endpoint: string) {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: true,
    error: null
  });

  useEffect(() => {
    let isMounted = true;

    async function fetchData() {
      setState({ data: null, loading: true, error: null });

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
  }, [endpoint]);

  return state;
}
