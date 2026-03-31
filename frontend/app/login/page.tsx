'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { FormEvent, useEffect, useState } from 'react';

import { useAuth } from '../../context/AuthContext';

export default function LoginPage() {
  const { login, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState(searchParams.get('email') ?? '');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const tenantParam = searchParams.get('tenant') ?? undefined;

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      if (tenantParam) {
        router.replace(`/t/${tenantParam}/dashboard`);
        return;
      }
      router.replace('/dashboard');
    }
  }, [isAuthenticated, isLoading, router, tenantParam]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      await login(email, password, tenantParam);
      if (tenantParam) {
        router.replace(`/t/${tenantParam}/dashboard`);
        return;
      }
      router.replace('/dashboard');
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Falha ao autenticar');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
      <form className="w-full max-w-md space-y-4 rounded-xl border bg-white p-6 shadow-sm" onSubmit={onSubmit}>
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Entrar</h1>
          <p className="mt-1 text-sm text-slate-600">Acesse o painel da biblioteca.</p>
        </div>

        <label className="block text-sm font-medium text-slate-700">
          E-mail
          <input
            className="mt-1 w-full rounded-lg border px-3 py-2"
            onChange={(event) => setEmail(event.target.value)}
            required
            type="email"
            value={email}
          />
        </label>

        <label className="block text-sm font-medium text-slate-700">
          Senha
          <input
            className="mt-1 w-full rounded-lg border px-3 py-2"
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </label>

        {error ? <p className="text-sm text-red-600">{error}</p> : null}

        <button
          className="w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          disabled={submitting}
          type="submit"
        >
          {submitting ? 'Entrando...' : 'Entrar'}
        </button>

        <Link className="block text-center text-sm font-medium text-brand-700 hover:text-brand-800" href="/register">
          Criar conta
        </Link>
      </form>
    </main>
  );
}
