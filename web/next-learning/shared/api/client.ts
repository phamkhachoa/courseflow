"use client";

import { API_BASE_URL, unwrap } from "./envelope";

export type LearnerUser = {
  id: number;
  email: string;
  fullName: string;
  role?: string;
  status: string;
};
export type StoredSession = {
  accessToken: string;
  refreshToken: string;
  user: LearnerUser;
};

const STORAGE_KEY = "courseflow.learning.session";
const SESSION_CHANGED_EVENT = "courseflow.learning.session.changed";

type SessionListener = (session: StoredSession | null) => void;

function emitSessionChanged(session: StoredSession | null) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent<StoredSession | null>(SESSION_CHANGED_EVENT, { detail: session }));
}

async function readJson<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  if (!text) return undefined as T;
  return unwrap<T>(JSON.parse(text));
}

export const learnerSession = {
  read(): StoredSession | null {
    if (typeof window === "undefined") return null;
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? (JSON.parse(raw) as StoredSession) : null;
    } catch {
      return null;
    }
  },
  write(session: StoredSession): void {
    if (typeof window === "undefined") return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    emitSessionChanged(session);
  },
  clear(): void {
    if (typeof window === "undefined") return;
    localStorage.removeItem(STORAGE_KEY);
    emitSessionChanged(null);
  },
  subscribe(listener: SessionListener): () => void {
    if (typeof window === "undefined") return () => undefined;
    const onSessionChanged = (event: Event) => {
      listener((event as CustomEvent<StoredSession | null>).detail ?? null);
    };
    const onStorage = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) listener(learnerSession.read());
    };
    window.addEventListener(SESSION_CHANGED_EVENT, onSessionChanged);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener(SESSION_CHANGED_EVENT, onSessionChanged);
      window.removeEventListener("storage", onStorage);
    };
  }
};

type ClientFetchOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
};

type ApiErrorPayload = {
  title?: string;
  detail?: string;
  statusCode?: string;
};

/**
 * Browser-side fetch with the learner bearer token attached. On a 401 it tries
 * one refresh, then replays the request once.
 */
export async function clientFetch<T>(
  path: string,
  { method = "GET", body }: ClientFetchOptions = {}
): Promise<T> {
  const run = async (token?: string): Promise<Response> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;
    return fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined
    });
  };

  let session = learnerSession.read();
  let response = await run(session?.accessToken);

  if (response.status === 401 && session?.refreshToken) {
    const refreshed = await fetch(`${API_BASE_URL}/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refreshToken: session.refreshToken })
    });
    if (refreshed.ok) {
      const next = unwrap<StoredSession & { accessToken: string }>(await refreshed.json());
      learnerSession.write(next);
      session = next;
      response = await run(next.accessToken);
    } else {
      learnerSession.clear();
    }
  }

  if (!response.ok) {
    let message = `Request ${path} failed with ${response.status}`;
    try {
      const payload = (await response.json()) as ApiErrorPayload;
      message = payload.detail ?? payload.title ?? message;
    } catch {
      // Keep the generic message when the server does not return JSON.
    }
    const error = new Error(message) as Error & { status?: number };
    error.status = response.status;
    throw error;
  }
  return readJson<T>(response);
}
