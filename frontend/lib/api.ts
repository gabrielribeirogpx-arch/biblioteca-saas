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

export function getStoredTenantId(): string {
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID ?? DEFAULT_TENANT_ID;
  }

  return window.localStorage.getItem('tenant_id') ?? process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID ?? DEFAULT_TENANT_ID;
}

export function setStoredTenantId(tenantId: string) {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem('tenant_id', tenantId);
}

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }

  return window.localStorage.getItem('access_token') ?? window.localStorage.getItem('token');
}

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

export async function apiFetch<T = unknown>(url: string, options: RequestInit = {}): Promise<T | null> {
  const token = getStoredToken();
  if (typeof window !== 'undefined') {
    console.log('[apiFetch] JWT token:', token);
    console.log('Authorization header:', token ? `Bearer ${token}` : 'sem token');
  }

  const headers = new Headers(options.headers);
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }

  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  if (url.startsWith('/api/v1/') && !headers.has('X-Tenant-ID')) {
    headers.set('X-Tenant-ID', getStoredTenantId());
  }

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(buildUrl(getApiBaseUrl(), url), {
    ...options,
    headers,
    cache: 'no-store'
  });

  if (response.status === 401) {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('token');
      localStorage.removeItem('user_email');
      localStorage.removeItem('tenant_id');
      window.location.href = '/login';
    }
    return null;
  }

  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(`API request failed for ${url}`, response.status, body);
  }

  const contentType = response.headers.get('content-type') ?? '';

  if (!contentType.includes('application/json')) {
    return null;
  }

  return (await response.json()) as T;
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
    });
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
