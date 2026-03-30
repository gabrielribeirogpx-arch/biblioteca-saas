export type UserRole = 'super_admin' | 'librarian' | 'assistant' | 'member';

export interface Book {
  id: number;
  library_id: number;
  title: string;
  subtitle?: string | null;
  isbn?: string | null;
  edition?: string | null;
  publication_year?: number | null;
  authors: string[];
  subjects: string[];
}

export interface Copy {
  id: number;
  book_id: number;
  library_id?: number;
  barcode?: string;
  status?: string;
}

export interface Loan {
  id: number;
  copy_id: number;
  user_id: string;
  due_date: string;
  status: string;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
}

export interface ReportSummary {
  total_books: number;
  total_copies: number;
  active_loans: number;
}

export interface OverdueItem {
  loan_id: number;
  user_id: number;
  copy_id: number;
  overdue_days: number;
}

export interface MostBorrowedItem {
  book_id: number;
  title: string;
  checkout_count: number;
}

interface ApiClientConfig {
  baseUrl?: string;
  token?: string;
  tenantId?: string;
}

class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const DEFAULT_API_URL = 'https://backend-biblioteca-saas-production.up.railway.app';

function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL;
}

function buildUrl(baseUrl: string, endpoint: string): string {
  if (/^https?:\/\//i.test(endpoint)) {
    return endpoint;
  }

  const normalizedBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${normalizedBase}${normalizedEndpoint}`;
}

export async function apiFetch<T>(endpoint: string, options?: RequestInit, baseUrl = getApiBaseUrl()): Promise<T> {
  const url = buildUrl(baseUrl, endpoint);

  console.log('Calling API:', endpoint);

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {})
    },
    cache: 'no-store'
  });

  const contentType = response.headers.get('content-type') ?? '';

  let responseBody: unknown = null;
  if (contentType.includes('application/json')) {
    responseBody = await response.json();
  } else {
    responseBody = await response.text();
  }

  if (!response.ok) {
    const body = typeof responseBody === 'string' ? responseBody : JSON.stringify(responseBody);
    throw new ApiError(`API request failed for ${endpoint}`, response.status, body);
  }

  return responseBody as T;
}

export async function getBooks(): Promise<Book[]> {
  return apiFetch<Book[]>('/api/v1/books');
}

export async function getCopies(): Promise<Copy[]> {
  return apiFetch<Copy[]>('/api/v1/copies');
}

export async function getLoans(): Promise<Loan[]> {
  return apiFetch<Loan[]>('/api/v1/loans');
}

export async function getUsers(): Promise<User[]> {
  return apiFetch<User[]>('/api/v1/users');
}

export async function getReports(): Promise<ReportSummary> {
  return apiFetch<ReportSummary>('/api/v1/reports');
}

export async function getHealth(): Promise<{ status: string }> {
  return apiFetch<{ status: string }>('/health');
}

export class ApiClient {
  private readonly baseUrl: string;
  private readonly token?: string;
  private readonly tenantId?: string;

  constructor(config: ApiClientConfig = {}) {
    this.baseUrl = config.baseUrl ?? getApiBaseUrl();
    this.token = config.token;
    this.tenantId = config.tenantId;
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const headers = new Headers(init?.headers);

    if (this.token) {
      headers.set('Authorization', `Bearer ${this.token}`);
    }

    if (this.tenantId) {
      headers.set('x-tenant-id', this.tenantId);
    }

    return apiFetch<T>(`/api/v1${path}`, {
      ...init,
      headers
    }, this.baseUrl);
  }

  listBooks(): Promise<Book[]> {
    return this.request<Book[]>('/books/');
  }

  listLoans(): Promise<Loan[]> {
    return this.request<Loan[]>('/loans/');
  }

  listUsers(): Promise<User[]> {
    return this.request<User[]>('/users/');
  }

  getSummaryReport(): Promise<ReportSummary> {
    return this.request<ReportSummary>('/reports/summary');
  }

  listOverdue(limit = 25): Promise<OverdueItem[]> {
    return this.request<OverdueItem[]>(`/reports/overdue?limit=${limit}`);
  }

  listMostBorrowed(limit = 10): Promise<MostBorrowedItem[]> {
    return this.request<MostBorrowedItem[]>(`/reports/most-borrowed?limit=${limit}`);
  }
}

export function createApiClient(config?: ApiClientConfig): ApiClient {
  return new ApiClient(config);
}

export { ApiError };
