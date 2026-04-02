'use client';

import { useEffect } from 'react';

import { setStoredTenantId } from '../../../../lib/api';
import DashboardPage from '../../../dashboard/page';

export default function TenantDashboardRedirectPage({ params }: { params: { slug: string } }) {
  useEffect(() => {
    setStoredTenantId(params.slug);
  }, [params.slug]);

  return <DashboardPage />;
}
