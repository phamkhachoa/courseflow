import axios, {
  AxiosError,
  AxiosHeaders,
  type AxiosInstance,
  type InternalAxiosRequestConfig
} from "axios";
import { unwrap } from "@/shared/api/envelope";
import { sessionStore, type TokenResponse } from "@/shared/auth/session-store";

export const API_BASE_URL =
  import.meta.env.VITE_API_GATEWAY_URL ?? "http://localhost:8080/api";

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" }
});

/** Attach the bearer token to every outgoing request. */
apiClient.interceptors.request.use((config) => {
  const session = sessionStore.read();
  if (session?.accessToken) {
    const headers = AxiosHeaders.from(config.headers);
    headers.set("Authorization", `Bearer ${session.accessToken}`);
    config.headers = headers;
  }
  return config;
});

// --- single-flight refresh -------------------------------------------------
// When several requests hit a 401 at once we only want ONE refresh call; the
// rest wait for it and then replay with the new token.
let refreshPromise: Promise<string> | null = null;

/** Callback fired when refresh ultimately fails (used by the auth context). */
let onAuthFailure: (() => void) | null = null;
export function setAuthFailureHandler(handler: (() => void) | null): void {
  onAuthFailure = handler;
}

async function refreshAccessToken(): Promise<string> {
  const session = sessionStore.read();
  if (!session?.refreshToken) {
    throw new Error("No refresh token available");
  }
  // Bare axios call so we don't recurse through the interceptors below.
  const { data: payload } = await axios.post<unknown>(
    `${API_BASE_URL}/v1/auth/refresh`,
    { refreshToken: session.refreshToken },
    { headers: { "Content-Type": "application/json" } }
  );
  const data = unwrap<TokenResponse>(payload);
  sessionStore.write({
    accessToken: data.accessToken,
    refreshToken: data.refreshToken,
    user: data.user
  });
  return data.accessToken;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as
      | (InternalAxiosRequestConfig & { _retried?: boolean })
      | undefined;

    const isAuthCall = original?.url?.includes("/v1/auth/");
    if (error.response?.status !== 401 || !original || original._retried || isAuthCall) {
      return Promise.reject(error);
    }

    original._retried = true;
    try {
      refreshPromise = refreshPromise ?? refreshAccessToken();
      const token = await refreshPromise;
      refreshPromise = null;
      const headers = AxiosHeaders.from(original.headers);
      headers.set("Authorization", `Bearer ${token}`);
      original.headers = headers;
      return apiClient(original);
    } catch (refreshError) {
      refreshPromise = null;
      sessionStore.clear();
      onAuthFailure?.();
      return Promise.reject(refreshError);
    }
  }
);
