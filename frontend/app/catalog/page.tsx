import { AppShell } from '../../components/ui/AppShell';
import { DataTable } from '../../components/ui/DataTable';
import { createApiClient } from '../../lib/api';
import { getCurrentRole } from '../../lib/auth';

async function loadCatalogRows() {
  const api = createApiClient({ tenantId: process.env.DEFAULT_TENANT_ID ?? 'default' });
  const books = await api.listBooks().catch(() => []);

  return books.map((book) => ({
    title: book.title,
    isbn: book.isbn ?? 'N/A',
    authors: book.authors.join(', ') || 'N/A',
    publication_year: book.publication_year ?? 'N/A'
  }));
}

export default async function CatalogPage() {
  const role = getCurrentRole();
  const rows = await loadCatalogRows();

  return (
    <AppShell
      role={role}
      title="Catalog"
      subtitle="Search and review AACR2-ready catalog records in one operational queue."
    >
      <DataTable
        columns={[
          { key: 'title', label: 'Title' },
          { key: 'isbn', label: 'ISBN' },
          { key: 'authors', label: 'Authors' },
          { key: 'publication_year', label: 'Year' }
        ]}
        description="Includes imported MARC21 metadata and normalized catalog fields."
        rows={rows}
        searchableFields={['title', 'isbn', 'authors']}
        title="Catalog Records"
      />
    </AppShell>
  );
}
