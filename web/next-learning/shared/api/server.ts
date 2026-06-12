import { API_BASE_URL, unwrap } from "./envelope";

type ServerFetchOptions = {
  /** ISR revalidation window in seconds. Defaults to 60. Pass 0 to disable. */
  revalidate?: number;
  /** Forward an auth token for protected reads. */
  token?: string;
};

/**
 * Fetch helper for React Server Components. Returns the unwrapped payload, or
 * throws on non-2xx so callers can decide on a fallback.
 */
export async function serverFetch<T>(
  path: string,
  { revalidate = 60, token }: ServerFetchOptions = {}
): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers,
    next: revalidate > 0 ? { revalidate } : undefined,
    cache: revalidate > 0 ? undefined : "no-store"
  });

  if (!response.ok) {
    throw new Error(`Request ${path} failed with ${response.status}`);
  }
  return unwrap<T>(await response.json());
}
