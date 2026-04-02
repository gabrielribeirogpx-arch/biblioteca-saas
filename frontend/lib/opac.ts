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
}

export interface OPACBookDetail {
  id: number;
  title: string;
  subtitle?: string | null;
  author: string;
  isbn?: string | null;
  subjects: string[];
  publication_year?: number | null;
  edition?: string | null;
  cover_url?: string | null;
  available: boolean;
  total_copies: number;
  available_copies: number;
  library: OPACLibraryInfo;
  libraries: OPACHoldingLibrary[];
}

const DEFAULT_API_URL = 'https://backend-biblioteca-saas-production.up.railway.app';

function apiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL).replace(/\/$/, '');
}

async function opacFetch<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${apiBaseUrl()}${path}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      next: { revalidate: 60 }
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export async function getPublicBooks(query: string): Promise<OPACBookListResponse> {
  return (
    await opacFetch<OPACBookListResponse>(`/api/public/books${query ? `?${query}` : ''}`)
  ) ?? {
    items: [],
    page: 1,
    page_size: 20,
    total: 0
  };
}

export async function getPublicBook(bookId: number): Promise<OPACBookDetail | null> {
  return await opacFetch<OPACBookDetail>(`/api/public/books/${bookId}`);
}
