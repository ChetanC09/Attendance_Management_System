const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) { super(message); this.name = 'ApiError'; this.status = status; }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('X-Requested-With', 'XMLHttpRequest');
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const response = await fetch(`${API_BASE}${path.startsWith('/api') || path.startsWith('/health') ? '' : '/api'}${path}`, {
    ...init, headers, credentials: 'include',
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      const detail = body.detail ?? body.message;
      if (typeof detail === 'string') message = detail;
      else if (detail !== undefined) message = JSON.stringify(detail);
    } catch { /* non-JSON error */ }
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const jsonBody = (value: unknown) => JSON.stringify(value);
export const apiBaseUrl = API_BASE;

export interface ApiUser {
  id: string; institutional_id: string; email: string; full_name: string; role: 'ADMIN' | 'FACULTY' | 'STUDENT';
}
export interface ApiSession { user: ApiUser; expires_at: string }
