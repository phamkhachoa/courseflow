import type { StoredSession } from "./session-store";

const PKCE_STORAGE_KEY = "courseflow.admin.keycloak.pkce";

type PendingPkce = {
  state: string;
  nonce: string;
  verifier: string;
  returnTo: string;
};

type KeycloakTokenResponse = {
  access_token: string;
  refresh_token?: string;
  id_token?: string;
  token_type?: string;
  expires_in?: number;
};

type JwtClaims = {
  sub?: string;
  email?: string;
  preferred_username?: string;
  name?: string;
  given_name?: string;
  family_name?: string;
};

const authority = (import.meta.env.VITE_KEYCLOAK_ISSUER_URI ?? "http://localhost:18080/realms/courseflow")
  .replace(/\/$/, "");
const clientId = import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? "courseflow-admin-web";

function callbackUrl() {
  return `${window.location.origin}/login/callback`;
}

function postLogoutRedirectUrl() {
  return `${window.location.origin}/login`;
}

function endpoint(path: string) {
  return `${authority}/protocol/openid-connect/${path}`;
}

function randomBase64Url(bytes = 32) {
  const data = new Uint8Array(bytes);
  crypto.getRandomValues(data);
  return base64Url(data);
}

function base64Url(input: Uint8Array) {
  let binary = "";
  input.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function codeChallenge(verifier: string) {
  const encoded = new TextEncoder().encode(verifier);
  const digest = await crypto.subtle.digest("SHA-256", encoded);
  return base64Url(new Uint8Array(digest));
}

function readPending(): PendingPkce {
  const raw = sessionStorage.getItem(PKCE_STORAGE_KEY);
  if (!raw) {
    throw new Error("Phiên đăng nhập Keycloak đã hết hạn. Hãy thử lại.");
  }
  return JSON.parse(raw) as PendingPkce;
}

function clearPending() {
  sessionStorage.removeItem(PKCE_STORAGE_KEY);
}

function decodeJwt(token?: string): JwtClaims {
  if (!token) return {};
  const [, payload] = token.split(".");
  if (!payload) return {};
  const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  try {
    return JSON.parse(atob(padded)) as JwtClaims;
  } catch {
    return {};
  }
}

function sessionFromToken(token: KeycloakTokenResponse): StoredSession {
  const claims = decodeJwt(token.id_token ?? token.access_token);
  const email = claims.email ?? claims.preferred_username ?? "";
  const fullName =
    claims.name ??
    ([claims.given_name, claims.family_name].filter(Boolean).join(" ") || email);
  return {
    accessToken: token.access_token,
    refreshToken: token.refresh_token ?? "",
    idToken: token.id_token,
    user: {
      id: 0,
      email,
      fullName,
      role: "UNRESOLVED",
      status: "ACTIVE"
    }
  };
}

export async function beginKeycloakLogin(returnTo: string) {
  const verifier = randomBase64Url(64);
  const pending: PendingPkce = {
    state: randomBase64Url(32),
    nonce: randomBase64Url(32),
    verifier,
    returnTo: returnTo.startsWith("/") && !returnTo.startsWith("//") ? returnTo : "/"
  };
  sessionStorage.setItem(PKCE_STORAGE_KEY, JSON.stringify(pending));

  const params = new URLSearchParams({
    response_type: "code",
    client_id: clientId,
    redirect_uri: callbackUrl(),
    scope: "openid profile email",
    state: pending.state,
    nonce: pending.nonce,
    code_challenge: await codeChallenge(verifier),
    code_challenge_method: "S256"
  });
  window.location.assign(`${endpoint("auth")}?${params.toString()}`);
}

export async function completeKeycloakLogin(url: string) {
  const callback = new URL(url);
  const error = callback.searchParams.get("error");
  if (error) {
    throw new Error(callback.searchParams.get("error_description") ?? error);
  }
  const code = callback.searchParams.get("code");
  const state = callback.searchParams.get("state");
  const pending = readPending();
  if (!code || state !== pending.state) {
    clearPending();
    throw new Error("Keycloak callback không hợp lệ.");
  }

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: clientId,
    code,
    redirect_uri: callbackUrl(),
    code_verifier: pending.verifier
  });
  const response = await fetch(endpoint("token"), {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body
  });
  if (!response.ok) {
    clearPending();
    throw new Error("Không đổi được authorization code từ Keycloak.");
  }
  const token = (await response.json()) as KeycloakTokenResponse;
  clearPending();
  return {
    session: sessionFromToken(token),
    returnTo: pending.returnTo
  };
}

export async function refreshKeycloakToken(refreshToken: string) {
  const body = new URLSearchParams({
    grant_type: "refresh_token",
    client_id: clientId,
    refresh_token: refreshToken
  });
  const response = await fetch(endpoint("token"), {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body
  });
  if (!response.ok) {
    throw new Error("Không refresh được Keycloak token.");
  }
  return sessionFromToken((await response.json()) as KeycloakTokenResponse);
}

export function redirectToKeycloakLogout(session: StoredSession | null) {
  const params = new URLSearchParams({
    client_id: clientId,
    post_logout_redirect_uri: postLogoutRedirectUrl()
  });
  if (session?.idToken) {
    params.set("id_token_hint", session.idToken);
  }
  window.location.assign(`${endpoint("logout")}?${params.toString()}`);
}
