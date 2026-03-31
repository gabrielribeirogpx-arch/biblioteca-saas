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
const DEFAULT_TENANT_ID = 'default';

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  return window.localStorage.getItem('token');
}

function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL;
}

function getDefaultTenantId(): string {
  return process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID ?? DEFAULT_TENANT_ID;
}

function buildUrl(baseUrl: string, endpoint: string): string {
  if (/^https?:\/\//i.test(endpoint)) {
    return endpoint;
  }

  const normalizedBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${normalizedBase}${normalizedEndpoint}`;
}

export async function apiFetch<T>(endpoint: string, options?: RequestInit, baseUrl = getApiBaseUrl()): Promise<T | null> {
  const url = buildUrl(baseUrl, endpoint);

  const headers = new Headers(options?.headers);
  const isTenantScopedEndpoint = endpoint.startsWith('/api/v1/');
  const providedAuthHeader = headers.get('Authorization');
  const token = providedAuthHeader ? null : getStoredToken();

  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  if (isTenantScopedEndpoint && !headers.has('X-Tenant-ID')) {
    headers.set('X-Tenant-ID', getDefaultTenantId());
  }

  const hasBody = options?.body !== undefined && options?.body !== null;
  if (hasBody && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  if (isTenantScopedEndpoint && !providedAuthHeader) {
    if (!token) {
      return null;
    }
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, {
    ...options,
    headers,
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
    if (response.status === 401 && typeof window !== 'undefined') {
      window.localStorage.removeItem('token');
    }
    const body = typeof responseBody === 'string' ? responseBody : JSON.stringify(responseBody);
    throw new ApiError(`API request failed for ${endpoint}`, response.status, body);
  }

  return responseBody as T;
}

export async function getBooks(): Promise<Book[]> {
  return (await apiFetch<Book[]>('/api/v1/books/')) ?? [];
}

export async function getCopies(): Promise<Copy[]> {
  return (await apiFetch<Copy[]>('/api/v1/copies/')) ?? [];
}

export async function getLoans(): Promise<Loan[]> {
  return (await apiFetch<Loan[]>('/api/v1/loans/')) ?? [];
}

export async function getUsers(): Promise<User[]> {
  return (await apiFetch<User[]>('/api/v1/users')) ?? [];
}

export async function getReports(): Promise<ReportSummary> {
  return (await apiFetch<ReportSummary>('/api/v1/reports')) ?? { total_books: 0, total_copies: 0, active_loans: 0 };
}

export async function getHealth(): Promise<{ status: string }> {
  return (await apiFetch<{ status: string }>('/health')) ?? { status: 'ok' };
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

  private async request<T>(path: string, init?: RequestInit): Promise<T | null> {
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

  listBooks(): Promise<Book[] | null> {
    return this.request<Book[]>('/books/');
  }

  listLoans(): Promise<Loan[] | null> {
    return this.request<Loan[]>('/loans/');
  }

  listUsers(): Promise<User[] | null> {
    return this.request<User[]>('/users/');
  }

  getSummaryReport(): Promise<ReportSummary | null> {
    return this.request<ReportSummary>('/reports/summary');
  }

  listOverdue(limit = 25): Promise<OverdueItem[] | null> {
    return this.request<OverdueItem[]>(`/reports/overdue?limit=${limit}`);
  }

  listMostBorrowed(limit = 10): Promise<MostBorrowedItem[] | null> {
    return this.request<MostBorrowedItem[]>(`/reports/most-borrowed?limit=${limit}`);
  }
}

export function createApiClient(config?: ApiClientConfig): ApiClient {
  return new ApiClient(config);
}

export { ApiError };
