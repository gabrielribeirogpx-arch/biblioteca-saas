'use client';

import { useEffect, useState } from 'react';

export function useAuth() {
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = localStorage.getItem('access_token') ?? localStorage.getItem('token');

    console.log('🔐 Token inicial:', t);

    setToken(t);
    setLoading(false);
  }, []);

  return { token, loading };
}
