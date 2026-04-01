'use client';

import { useRouter } from 'next/navigation';
import { FormEvent, useMemo, useState } from 'react';

import { setStoredTenantId } from '../../lib/api';

interface RegisterResponse {
  success: boolean;
  tenant_slug: string;
  token?: string | null;
}

interface ApiErrorDetail {
  detail?: string | Array<{ loc?: Array<string | number>; msg?: string }>;
}

function extractApiErrorMessage(errorBody: ApiErrorDetail | null): string {
  if (!errorBody?.detail) {
    return 'Falha no cadastro';
  }

  if (typeof errorBody.detail === 'string') {
    return errorBody.detail;
  }

  if (Array.isArray(errorBody.detail) && errorBody.detail.length > 0) {
    return errorBody.detail
      .map((item) => {
        const field = item.loc?.at(-1);
        if (field && item.msg) {
          return `${String(field)}: ${item.msg}`;
        }

        return item.msg ?? 'Dados inválidos';
      })
      .join('; ');
  }

  return 'Falha no cadastro';
}

function slugifyName(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/[\s_-]+/g, '-')
    .replace(/-+/g, '-');
}

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [checkingSlug, setCheckingSlug] = useState(false);
  const [slugAvailable, setSlugAvailable] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = useMemo(() => process.env.NEXT_PUBLIC_API_URL, []);

  async function checkSlugAvailability(slugCandidate: string) {
    if (!apiUrl || !slugCandidate) {
      setSlugAvailable(null);
      return;
    }

    setCheckingSlug(true);
    try {
      const response = await fetch(
        `${apiUrl}/api/public/slug-availability?slug=${encodeURIComponent(slugCandidate)}`,
        { cache: 'no-store' }
      );

      if (!response.ok) {
        setSlugAvailable(null);
        return;
      }

      const data = (await response.json()) as { available?: boolean };
      setSlugAvailable(Boolean(data.available));
    } catch {
      setSlugAvailable(null);
    } finally {
      setCheckingSlug(false);
    }
  }

  async function onNameChange(value: string) {
    setName(value);
    const generatedSlug = slugifyName(value);
    setSlug(generatedSlug);
    await checkSlugAvailability(generatedSlug);
  }

  async function onSlugChange(value: string) {
    const normalized = slugifyName(value);
    setSlug(normalized);
    await checkSlugAvailability(normalized);
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiUrl) {
      setError('NEXT_PUBLIC_API_URL não configurada');
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const response = await fetch(`${apiUrl}/api/public/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name, slug, email, password })
      });

      if (!response.ok) {
        const errorBody = (await response.json().catch(() => null)) as ApiErrorDetail | null;
        throw new Error(extractApiErrorMessage(errorBody));
      }

      const data = (await response.json()) as RegisterResponse;
      if (!data.success) {
        throw new Error('Cadastro não concluído');
      }

      if (data.token && typeof window !== 'undefined') {
        window.localStorage.setItem('access_token', data.token);
        window.localStorage.setItem('token', data.token);
        window.localStorage.setItem('user_email', email);
      }

      setStoredTenantId(data.tenant_slug);
      router.replace(`/t/${data.tenant_slug}/dashboard`);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Erro ao criar conta');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
      <form className="w-full max-w-md space-y-4 rounded-xl border bg-white p-6 shadow-sm" onSubmit={onSubmit}>
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Criar conta</h1>
          <p className="mt-1 text-sm text-slate-600">Crie sua biblioteca SaaS e acesse imediatamente.</p>
        </div>

        <label className="block text-sm font-medium text-slate-700">
          Nome da Biblioteca
          <input className="mt-1 w-full rounded-lg border px-3 py-2" onChange={(event) => onNameChange(event.target.value)} required value={name} />
        </label>

        <label className="block text-sm font-medium text-slate-700">
          Subdomínio
          <input className="mt-1 w-full rounded-lg border px-3 py-2" onChange={(event) => onSlugChange(event.target.value)} required value={slug} />
          {checkingSlug ? <p className="mt-1 text-xs text-slate-500">checking availability...</p> : null}
          {!checkingSlug && slugAvailable === true ? <p className="mt-1 text-xs text-emerald-700">Subdomínio disponível</p> : null}
          {!checkingSlug && slugAvailable === false ? <p className="mt-1 text-xs text-red-600">Subdomínio indisponível</p> : null}
        </label>

        <label className="block text-sm font-medium text-slate-700">
          Email
          <input className="mt-1 w-full rounded-lg border px-3 py-2" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
        </label>

        <label className="block text-sm font-medium text-slate-700">
          Senha
          <input className="mt-1 w-full rounded-lg border px-3 py-2" onChange={(event) => setPassword(event.target.value)} required type="password" value={password} />
        </label>

        {error ? <p className="text-sm text-red-600">{error}</p> : null}

        <button
          className="w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          disabled={loading || checkingSlug}
          type="submit"
        >
          {loading ? 'Criando conta...' : 'Criar conta'}
        </button>
      </form>
    </main>
  );
}
