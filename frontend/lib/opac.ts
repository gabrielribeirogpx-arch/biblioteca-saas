import { apiPublicGet } from './apiPublic';

export interface OPACLibraryInfo {
  id: number;
  name: string;
  code: string;
  tenant_id: number;
  tenant_name: string;
  tenant_slug: string;
}

export interface OPACBookListItem {
  id: number;
  title: string;
  author: string;
  isbn?: string | null;
  subjects: string[];
  cover_url?: string | null;
  available: boolean;
  total_copies: number;
  available_copies: number;
  status: string;
  library: OPACLibraryInfo;
}

export interface OPACBookListResponse {
  items: OPACBookListItem[];
  page: number;
  page_size: number;
  total: number;
}

export interface OPACHoldingLibrary {
  library: OPACLibraryInfo;
  total_copies: number;
  available_copies: number;
  available: boolean;
  status: string;
}

export interface OPACBookDetail {
  id: number;
  title: string;
  subtitle?: string | null;
  author: string;
  isbn?: string | null;
  subject?: string | null;
  subjects: string[];
  publication_year?: number | null;
  edition?: string | null;
  cover_url?: string | null;
  available: boolean;
  total_copies: number;
  available_copies: number;
  status: string;
  library: OPACLibraryInfo;
  libraries: OPACHoldingLibrary[];
}

async function opacFetch<T>(path: string): Promise<T | null> {
  return apiPublicGet<T>(path, { revalidate: 60 });
}

export async function getPublicBooks(query: string, tenant?: string): Promise<OPACBookListResponse> {
  const resolvedQuery = new URLSearchParams(query);
  if (tenant) {
    resolvedQuery.set('tenant', tenant);
  }
  return (
    await opacFetch<OPACBookListResponse>(`/api/public/books${resolvedQuery.size > 0 ? `?${resolvedQuery.toString()}` : ''}`)
  ) ?? {
    items: [],
    page: 1,
    page_size: 20,
    total: 0
  };
}

export async function getPublicBook(bookId: number, tenant?: string): Promise<OPACBookDetail | null> {
  const query = new URLSearchParams();
  if (tenant) {
    query.set('tenant', tenant);
  }
  return await opacFetch<OPACBookDetail>(`/api/public/books/${bookId}${query.size > 0 ? `?${query.toString()}` : ''}`);
}
