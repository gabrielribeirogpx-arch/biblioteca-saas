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
  tenant_id: number;
  organization_id: number;
  is_active: boolean;
  created_at: string;
}

interface SwitchLibraryResponse {
  access_token: string;
  token_type?: string;
}

export interface LibraryCreateInput {
  name: string;
  code?: string;
  timezone?: string;
  is_active: boolean;
}

export interface LibraryUpdateInput {
  name?: string;
  code?: string;
  is_active?: boolean;
}

export interface LibraryPolicy {
  library_id: number;
  max_loans: number;
  loan_days: number;
  fine_per_day: string;
  renewal_limit: number;
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

export class ApiError extends Error {
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
  const claims = parseJwtClaims(token);
  if (!claims || typeof claims.exp !== 'number') {
    return null;
  }
  return claims.exp * 1000;
}

function parseJwtClaims(token: string): Record<string, unknown> | null {
  const [, payload] = token.split('.');
  if (!payload) {
    return null;
  }

  try {
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(base64)) as Record<string, unknown>;
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
  const token = getStoredToken();
  const claims = token ? parseJwtClaims(token) : null;
  const tokenTenantId = claims?.tenant_id;
  if (tokenTenantId != null) {
    return String(tokenTenantId);
  }

  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID ?? DEFAULT_TENANT_ID;
  }

  return (
    window.localStorage.getItem('tenant_id')
    ?? process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID
    ?? DEFAULT_TENANT_ID
  );
}

export function getTenant(): string {
  return getStoredTenantId();
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

  const normalizedTenantId = tenantId.trim();
  window.localStorage.setItem('tenant_id', normalizedTenantId);
}

export function setStoredLibraryId(libraryId: string) {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem('library_id', libraryId);
}

export function setStoredToken(token: string) {
  if (typeof window === 'undefined') {
    return;
  }

  const normalizedToken = token.trim().replace(/^Bearer\s+/i, '');
  window.localStorage.setItem('access_token', normalizedToken);
  window.localStorage.setItem('token', normalizedToken);
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
  let libraryId = getStoredLibraryId();
  const isProtectedEndpoint = url.startsWith('/api/v1/') && !url.startsWith('/api/v1/auth/login');
  const isLibraryListingEndpoint = url === '/api/v1/libraries' || url.startsWith('/api/v1/libraries?');
  const isLibrarySwitchEndpoint = url === '/api/v1/auth/switch-library';

  if (isProtectedEndpoint && !token) {
    return null;
  }

  if (isProtectedEndpoint && !isLibraryListingEndpoint && !isLibrarySwitchEndpoint && !libraryId) {
    const fallbackLibraries = await apiFetch<LibraryOption[]>('/api/v1/libraries');
    if (fallbackLibraries?.length) {
      libraryId = String(fallbackLibraries[0].id);
      setStoredLibraryId(libraryId);
    } else {
      throw new ApiError('Selecione uma biblioteca', 400, 'library_id is required');
    }
  }

  const headers = new Headers(options.headers);
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }

  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  if (url.startsWith('/api/v1/')) {
    if (libraryId && !headers.has('X-Library-ID')) {
      headers.set('X-Library-ID', libraryId);
      headers.set('x-library-id', libraryId);
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

export async function createLibrary(payload: LibraryCreateInput): Promise<LibraryOption | null> {
  return await apiFetch<LibraryOption>('/api/v1/libraries', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateLibrary(libraryId: number, payload: LibraryUpdateInput): Promise<LibraryOption | null> {
  return await apiFetch<LibraryOption>(`/api/v1/libraries/${libraryId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function switchLibrary(libraryId: string): Promise<string> {
  const numericLibraryId = Number(libraryId);
  if (!Number.isInteger(numericLibraryId) || numericLibraryId <= 0) {
    throw new ApiError('Biblioteca inválida para troca de contexto', 400, 'invalid library_id');
  }

  const response = await apiFetch<SwitchLibraryResponse>('/api/v1/auth/switch-library', {
    method: 'POST',
    body: JSON.stringify({ library_id: numericLibraryId })
  });

  const nextToken = response?.access_token?.trim().replace(/^Bearer\s+/i, '');
  if (!nextToken) {
    throw new ApiError('Não foi possível atualizar o token da biblioteca', 500, 'missing access_token');
  }

  setStoredToken(nextToken);
  setStoredLibraryId(libraryId);
  return nextToken;
}

export async function deleteLibrary(libraryId: number): Promise<void> {
  await apiFetch(`/api/v1/libraries/${libraryId}`, {
    method: 'DELETE'
  });
}

export async function getLibraryPolicy(libraryId: number): Promise<LibraryPolicy | null> {
  return await apiFetch<LibraryPolicy>(`/api/v1/libraries/${libraryId}/policy`);
}

export async function updateLibraryPolicy(libraryId: number, payload: Omit<LibraryPolicy, 'library_id'>): Promise<LibraryPolicy | null> {
  return await apiFetch<LibraryPolicy>(`/api/v1/libraries/${libraryId}/policy`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  });
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
