'use client';

import { ProtectedRoute } from '../../../components/auth/ProtectedRoute';
import { AdvancedCatalogWorkspace } from '../../../components/catalog/AdvancedCatalogWorkspace';
import { AppShell } from '../../../components/ui/AppShell';

export default function AdvancedCatalogPage() {
  return (
    <ProtectedRoute>
      <AppShell
        role="librarian"
        title="Catalogação avançada"
        subtitle="Catalogação MARC21 com preenchimento assistido, preview em tempo real e persistência multi-tenant."
      >
        <AdvancedCatalogWorkspace />
      </AppShell>
    </ProtectedRoute>
  );
}
