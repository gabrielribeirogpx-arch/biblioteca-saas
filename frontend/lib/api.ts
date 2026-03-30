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

export class ApiClient {
  private readonly baseUrl: string;
  private readonly token?: string;
  private readonly tenantId?: string;

  constructor(config: ApiClientConfig = {}) {
    this.baseUrl = config.baseUrl ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';
    this.token = config.token;
    this.tenantId = config.tenantId;
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const headers = new Headers(init?.headers);
    headers.set('Content-Type', 'application/json');

    if (this.token) {
      headers.set('Authorization', `Bearer ${this.token}`);
    }

    if (this.tenantId) {
      headers.set('x-tenant-id', this.tenantId);
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers,
      cache: 'no-store'
    });

    if (!response.ok) {
      const body = await response.text();
      throw new ApiError(`API request failed for ${path}`, response.status, body);
    }

    return (await response.json()) as T;
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
