import { apiClient } from "@/shared/api/client";
import { unwrap } from "@/shared/api/envelope";
import type { TokenResponse } from "@/shared/auth/session-store";

export async function loginRequest(
  email: string,
  password: string
): Promise<TokenResponse> {
  const { data } = await apiClient.post("/v1/auth/login", { email, password });
  return unwrap<TokenResponse>(data);
}

export async function logoutRequest(): Promise<void> {
  try {
    await apiClient.post("/v1/auth/logout", {});
  } catch {
    // Logout is best-effort; clearing local state is what matters.
  }
}
