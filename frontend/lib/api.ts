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

export interface LibraryOption {
  id: number;
  code: string;
  name: string;
  organization_id: number;
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


export interface Reservation {
  id: number;
  user_id: number;
  copy_id: number;
  position: number;
  status: string;
  reserved_at: string;
  expires_at?: string | null;
}

export interface Fine {
  id: number;
  user_id: number;
  loan_id: number;
  amount: string;
  currency: string;
  status: string;
  reason?: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
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
const TOKEN_EXPIRY_SKEW_MS = 30_000;

function parseJwtExpiryMs(token: string): number | null {
  const [, payload] = token.split('.');
  if (!payload) {
    return null;
  }

  try {
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
    const json = JSON.parse(atob(base64));
    if (typeof json.exp !== 'number') {
      return null;
    }
    return json.exp * 1000;
  } catch {
    return null;
  }
}

function clearStoredAuthState() {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.removeItem('access_token');
  window.localStorage.removeItem('token');
  window.localStorage.removeItem('user_email');
}

export function getStoredTenantId(): string {
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID ?? DEFAULT_TENANT_ID;
  }

  return (
    window.localStorage.getItem('tenant')
    ?? window.localStorage.getItem('tenant_id')
    ?? process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID
    ?? DEFAULT_TENANT_ID
  );
}

export function getStoredLibraryId(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  return window.localStorage.getItem('library_id');
}

export function setStoredTenantId(tenantId: string) {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem('tenant', tenantId);
  window.localStorage.setItem('tenant_id', tenantId);
}

export function setStoredLibraryId(libraryId: string) {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem('library_id', libraryId);
}

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const rawToken = window.localStorage.getItem('access_token') ?? window.localStorage.getItem('token');
  if (!rawToken) {
    return null;
  }

  const normalizedToken = rawToken
    .trim()
    .replace(/^Bearer\s+/i, '')
    .replace(/^"(.+)"$/, '$1');

  const expiryMs = parseJwtExpiryMs(normalizedToken);
  if (expiryMs && Date.now() >= expiryMs - TOKEN_EXPIRY_SKEW_MS) {
    clearStoredAuthState();
    return null;
  }

  return normalizedToken || null;
}

function getApiBaseUrl(): string {
  const configuredBaseUrl = (process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL).trim();

  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    return configuredBaseUrl.replace(/^http:/i, 'https:');
  }

  return configuredBaseUrl;
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
  const tenant = getStoredTenantId();
  const libraryId = getStoredLibraryId();
  const isProtectedEndpoint = url.startsWith('/api/v1/') && !url.startsWith('/api/v1/auth/login');

  if (isProtectedEndpoint && !token) {
    return null;
  }

  const headers = new Headers(options.headers);
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }

  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  if (url.startsWith('/api/v1/')) {
    if (!headers.has('X-Tenant-ID')) {
      headers.set('X-Tenant-ID', tenant);
    }
    if (!headers.has('X-Tenant-Slug')) {
      headers.set('X-Tenant-Slug', tenant);
    }
    if (libraryId && !headers.has('X-Library-ID')) {
      headers.set('X-Library-ID', libraryId);
    }
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
      clearStoredAuthState();
      window.dispatchEvent(new Event('auth:unauthorized'));
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
  return (await apiFetch<PaginatedResponse<Book>>('/api/v1/books/?page=1&page_size=50'))?.items ?? [];
}

export async function getCopies(): Promise<Copy[]> {
  return (await apiFetch<Copy[]>('/api/v1/copies/')) ?? [];
}

export async function getLoans(): Promise<Loan[]> {
  return (await apiFetch<PaginatedResponse<Loan>>('/api/v1/loans/?page=1&page_size=50'))?.items ?? [];
}

export async function getUsers(): Promise<User[]> {
  return (await apiFetch<PaginatedResponse<User>>('/api/v1/users/?page=1&page_size=50'))?.items ?? [];
}

export async function getLibraries(): Promise<LibraryOption[]> {
  return (await apiFetch<LibraryOption[]>('/api/v1/libraries')) ?? [];
}

export async function getReports(): Promise<ReportSummary> {
  return (await apiFetch<ReportSummary>('/api/v1/reports/summary')) ?? { total_books: 0, total_copies: 0, active_loans: 0 };
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

  listBooks(page = 1, pageSize = 20): Promise<PaginatedResponse<Book> | null> {
    return this.request<PaginatedResponse<Book>>(`/books/?page=${page}&page_size=${pageSize}`);
  }

  listLoans(page = 1, pageSize = 20): Promise<PaginatedResponse<Loan> | null> {
    return this.request<PaginatedResponse<Loan>>(`/loans/?page=${page}&page_size=${pageSize}`);
  }

  listUsers(page = 1, pageSize = 20): Promise<PaginatedResponse<User> | null> {
    return this.request<PaginatedResponse<User>>(`/users/?page=${page}&page_size=${pageSize}`);
  }

  listReservations(page = 1, pageSize = 20): Promise<PaginatedResponse<Reservation> | null> {
    return this.request<PaginatedResponse<Reservation>>(`/reservations/?page=${page}&page_size=${pageSize}`);
  }

  createReservation(copyId: number): Promise<Reservation | null> {
    return this.request<Reservation>('/reservations/', { method: 'POST', body: JSON.stringify({ copy_id: copyId }) });
  }

  listFines(page = 1, pageSize = 20): Promise<PaginatedResponse<Fine> | null> {
    return this.request<PaginatedResponse<Fine>>(`/fines/?page=${page}&page_size=${pageSize}`);
  }

  payFine(fineId: number, amount: number): Promise<Fine | null> {
    return this.request<Fine>(`/fines/${fineId}/pay`, { method: 'POST', body: JSON.stringify({ amount }) });
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
