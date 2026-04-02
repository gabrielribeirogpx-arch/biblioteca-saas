const DEFAULT_API_URL = 'https://backend-biblioteca-saas-production.up.railway.app';

function apiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL).replace(/\/$/, '');
}

interface PublicRequestOptions {
  revalidate?: number;
}

export async function apiPublicGet<T>(path: string, options: PublicRequestOptions = {}): Promise<T | null> {
  try {
    const response = await fetch(`${apiBaseUrl()}${path}`, {
      method: 'GET',
      headers: {
        Accept: 'application/json'
      },
      next: options.revalidate ? { revalidate: options.revalidate } : undefined
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as T;
  } catch {
    return null;
  }
}
