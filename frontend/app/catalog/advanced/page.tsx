'use client';

import { ProtectedRoute } from '../../../components/auth/ProtectedRoute';
import { AdvancedCatalogWorkspace } from '../../../components/catalog/AdvancedCatalogWorkspace';
import { AppShell } from '../../../components/ui/AppShell';
import { useAuth } from '../../../hooks/useAuth';

export default function AdvancedCatalogPage() {
  const { role } = useAuth();

  return (
    <ProtectedRoute>
      <AppShell
        role={role ?? 'member'}
        title="Catalogação avançada"
        subtitle="Catalogação MARC21 com preenchimento assistido, preview em tempo real e persistência multi-tenant."
      >
        <AdvancedCatalogWorkspace />
      </AppShell>
    </ProtectedRoute>
  );
}
