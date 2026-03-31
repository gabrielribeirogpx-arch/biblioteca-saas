'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { setStoredTenantId } from '../../../../lib/api';

export default function TenantDashboardRedirectPage({ params }: { params: { slug: string } }) {
  const router = useRouter();

  useEffect(() => {
    setStoredTenantId(params.slug);
    router.replace('/dashboard');
  }, [params.slug, router]);

  return <main className="flex min-h-screen items-center justify-center bg-slate-100 text-sm text-slate-600">Redirecionando...</main>;
}
