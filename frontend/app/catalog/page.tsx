'use client';

import { useEffect, useState } from 'react';

import { ProtectedRoute } from '../../components/auth/ProtectedRoute';
import { AppShell } from '../../components/ui/AppShell';
import { DataTable } from '../../components/ui/DataTable';
import { useAuth } from '../../hooks/useAuth';
import { apiFetch, type Book } from '../../lib/api';

interface CatalogRow {
  [key: string]: string | number | null | undefined;
  title: string;
  isbn: string;
  authors: string;
  publication_year: string | number;
}

export default function CatalogPage() {
  const role = 'librarian';
  const [rows, setRows] = useState<CatalogRow[]>([]);
  const { token, loading } = useAuth();

  useEffect(() => {
    let isMounted = true;
    if (loading || !token) {
      return;
    }

    apiFetch<{ items: Book[] }>('/api/v1/books/?page=1&page_size=50')
      .then((books) => {
        if (!isMounted || !books) {
          return;
        }
        setRows(
          (books.items ?? []).map((book) => ({
            title: book.title,
            isbn: book.isbn ?? 'N/A',
            authors: book.authors.join(', ') || 'N/A',
            publication_year: book.publication_year ?? 'N/A'
          }))
        );
      })
      .catch(() => {
        if (isMounted) {
          setRows([]);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [loading, token]);

  return (
    <ProtectedRoute>
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
    </ProtectedRoute>
  );
}
