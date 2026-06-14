#!/usr/bin/env node

/**
 * CourseFlow Keycloak security smoke gate.
 *
 * This script validates the enterprise auth path against a running cluster:
 *   Keycloak access token -> api-gateway -> identity-token-converter-service
 *   -> access-control-service resolved claims -> internal JWT -> JWKS verification.
 *
 * The script intentionally does not default to password grant. Provide a real Keycloak access token
 * through COURSEFLOW_SECURITY_SMOKE_ACCESS_TOKEN, obtained by an approved login flow. Converter and
 * direct service checks default to Docker-network DNS because internal services are not host-published.
 */

import crypto from "node:crypto";

const API_BASE = stripTrailingSlash(process.env.COURSEFLOW_API_URL ?? "http://localhost:28080/api");
const TOKEN_CONVERTER_URL = stripTrailingSlash(
  process.env.TOKEN_CONVERTER_URL ?? process.env.COURSEFLOW_TOKEN_CONVERTER_URL ?? "http://identity-token-converter-service:8080"
);
const DIRECT_SERVICE_URL = stripTrailingSlash(
  process.env.COURSEFLOW_DIRECT_SERVICE_URL ?? "http://course-service:8080"
);
const INTERNAL_AUDIENCE = process.env.COURSEFLOW_INTERNAL_JWT_AUDIENCE ?? "courseflow-services";
const INTERNAL_ISSUER = process.env.COURSEFLOW_INTERNAL_JWT_ISSUER ?? "courseflow-token-converter";
const TOKEN_EXCHANGE_CLIENT_ID = process.env.COURSEFLOW_SECURITY_SMOKE_TOKEN_EXCHANGE_CLIENT_ID ?? "api-gateway";
const TOKEN_EXCHANGE_CLIENT_SECRET = process.env.COURSEFLOW_SECURITY_SMOKE_TOKEN_EXCHANGE_CLIENT_SECRET
  ?? process.env.COURSEFLOW_STS_API_GATEWAY_SECRET
  ?? "";
const STS_CLIENT_ID = process.env.COURSEFLOW_SECURITY_SMOKE_STS_CLIENT_ID ?? "course-service";
const STS_CLIENT_SECRET = process.env.COURSEFLOW_SECURITY_SMOKE_STS_CLIENT_SECRET
  ?? process.env.COURSEFLOW_STS_CLIENT_SECRET
  ?? process.env.COURSEFLOW_STS_COURSE_SERVICE_SECRET
  ?? "";
const REQUESTED_SCOPE = process.env.COURSEFLOW_SECURITY_SMOKE_SCOPE ?? "internal:service";

const checks = [];

async function main() {
  console.log("CourseFlow Keycloak security smoke");
  console.log(`API: ${API_BASE}`);
  console.log(`Token converter: ${TOKEN_CONVERTER_URL}`);
  console.log(`Token exchange client: ${TOKEN_EXCHANGE_CLIENT_ID}`);
  console.log(`STS client_credentials client: ${STS_CLIENT_ID}`);

  const externalAccessToken = await externalToken();
  record("external Keycloak access token supplied", Boolean(externalAccessToken), "token is present");

  const jwks = await getJson(`${TOKEN_CONVERTER_URL}/oauth/jwks`);
  record("converter JWKS exposes signing key", Array.isArray(jwks.keys) && jwks.keys.length > 0,
    `${jwks.keys?.length ?? 0} key(s)`);

  const exchanged = await exchangeExternalToken(externalAccessToken);
  const exchangedClaims = verifyJwt(exchanged.access_token, jwks, {
    expectedIssuer: INTERNAL_ISSUER,
    expectedAudience: INTERNAL_AUDIENCE,
    expectedTokenUse: "internal"
  });
  record("token exchange issued verifiable internal JWT",
    exchangedClaims.token_use === "internal" && Boolean(exchangedClaims.uid),
    `uid=${exchangedClaims.uid ?? "missing"}, actor=${exchangedClaims.actor_type ?? "missing"}`);

  const serviceToken = await clientCredentialsToken();
  const serviceClaims = verifyJwt(serviceToken.access_token, jwks, {
    expectedIssuer: INTERNAL_ISSUER,
    expectedAudience: INTERNAL_AUDIENCE,
    expectedTokenUse: "internal"
  });
  record("STS client_credentials issued service token",
    serviceClaims.actor_type === "service" && serviceClaims.sub === `service:${STS_CLIENT_ID}`,
    `sub=${serviceClaims.sub ?? "missing"}`);

  await assertGatewayAcceptsKeycloakToken(externalAccessToken);
  await assertPublicProfileDoesNotRequireBearer();
  await assertProfileSummaryBatchRequiresBearer();
  await assertDirectIdentitySpoofRejected();

  printSummary();
}

async function externalToken() {
  const supplied = process.env.COURSEFLOW_SECURITY_SMOKE_ACCESS_TOKEN ?? process.env.KEYCLOAK_ACCESS_TOKEN;
  if (supplied && supplied.trim()) {
    return supplied.trim();
  }
  if (process.env.COURSEFLOW_SECURITY_SMOKE_ALLOW_PASSWORD_GRANT === "true") {
    return passwordGrantToken();
  }
  throw new Error(
    "COURSEFLOW_SECURITY_SMOKE_ACCESS_TOKEN is required. Obtain it via the approved Keycloak login flow; "
      + "set COURSEFLOW_SECURITY_SMOKE_ALLOW_PASSWORD_GRANT=true only for local/demo realms."
  );
}

async function passwordGrantToken() {
  const tokenUrl = requiredEnv("KEYCLOAK_TOKEN_URL");
  const clientId = requiredEnv("KEYCLOAK_CLIENT_ID");
  const username = requiredEnv("KEYCLOAK_USERNAME");
  const password = requiredEnv("KEYCLOAK_PASSWORD");
  const body = new URLSearchParams();
  body.set("grant_type", "password");
  body.set("client_id", clientId);
  body.set("username", username);
  body.set("password", password);
  if (process.env.KEYCLOAK_CLIENT_SECRET) {
    body.set("client_secret", process.env.KEYCLOAK_CLIENT_SECRET);
  }
  const json = await postForm(tokenUrl, body);
  if (!json.access_token) {
    throw new Error("Keycloak password grant response did not include access_token");
  }
  return json.access_token;
}

async function exchangeExternalToken(subjectToken) {
  if (!TOKEN_EXCHANGE_CLIENT_SECRET) {
    throw new Error(
      "COURSEFLOW_SECURITY_SMOKE_TOKEN_EXCHANGE_CLIENT_SECRET or COURSEFLOW_STS_API_GATEWAY_SECRET "
        + "is required for token exchange smoke"
    );
  }
  const body = new URLSearchParams();
  body.set("grant_type", "urn:ietf:params:oauth:grant-type:token-exchange");
  body.set("client_id", TOKEN_EXCHANGE_CLIENT_ID);
  body.set("client_secret", TOKEN_EXCHANGE_CLIENT_SECRET);
  body.set("subject_token_type", "urn:ietf:params:oauth:token-type:access_token");
  body.set("subject_token", subjectToken);
  body.set("audience", INTERNAL_AUDIENCE);
  body.set("scope", process.env.COURSEFLOW_SECURITY_SMOKE_USER_SCOPE ?? "course:read learning:write");
  const json = await postForm(`${TOKEN_CONVERTER_URL}/oauth/token`, body);
  if (!json.access_token) {
    throw new Error("Token converter did not return access_token for token exchange");
  }
  return json;
}

async function clientCredentialsToken() {
  if (!STS_CLIENT_SECRET) {
    throw new Error(
      "COURSEFLOW_SECURITY_SMOKE_STS_CLIENT_SECRET, COURSEFLOW_STS_CLIENT_SECRET or "
        + "COURSEFLOW_STS_COURSE_SERVICE_SECRET is required for STS client_credentials smoke"
    );
  }
  const body = new URLSearchParams();
  body.set("grant_type", "client_credentials");
  body.set("client_id", STS_CLIENT_ID);
  body.set("client_secret", STS_CLIENT_SECRET);
  body.set("audience", INTERNAL_AUDIENCE);
  body.set("scope", REQUESTED_SCOPE);
  const json = await postForm(`${TOKEN_CONVERTER_URL}/oauth/token`, body);
  if (!json.access_token) {
    throw new Error("Token converter did not return access_token for client_credentials");
  }
  return json;
}

async function assertGatewayAcceptsKeycloakToken(externalAccessToken) {
  const response = await fetch(`${API_BASE}/v1/users/me`, {
    headers: { Authorization: `Bearer ${externalAccessToken}` }
  });
  record("gateway accepts Keycloak access token",
    response.status === 200,
    `GET /v1/users/me -> ${response.status}`);
}

async function assertPublicProfileDoesNotRequireBearer() {
  const response = await fetch(`${API_BASE}/v1/profiles/${encodeURIComponent(
    process.env.COURSEFLOW_SECURITY_SMOKE_PUBLIC_PROFILE_USER_ID ?? "3"
  )}`);
  record("gateway allows public profile lookup without bearer",
    response.status === 200,
    `GET /v1/profiles/:id -> ${response.status}`);
}

async function assertProfileSummaryBatchRequiresBearer() {
  const response = await fetch(`${API_BASE}/v1/profiles/summary:batch`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ userIds: ["1"] })
  });
  record("gateway protects profile summary batch without bearer",
    response.status === 401,
    `POST /v1/profiles/summary:batch -> ${response.status}`);
}

async function assertDirectIdentitySpoofRejected() {
  const response = await fetch(`${DIRECT_SERVICE_URL}/internal/courses`, {
    headers: {
      "X-User-Id": "1",
      "X-User-Role": "ADMIN",
      "X-User-Roles": "ADMIN"
    }
  });
  record("direct service rejects forged identity headers",
    response.status === 401,
    `GET ${DIRECT_SERVICE_URL}/internal/courses -> ${response.status}`);
}

function verifyJwt(jwt, jwks, expectations) {
  const [encodedHeader, encodedPayload, encodedSignature] = String(jwt).split(".");
  if (!encodedHeader || !encodedPayload || !encodedSignature) {
    throw new Error("JWT must contain header, payload and signature");
  }
  const header = JSON.parse(base64UrlDecode(encodedHeader).toString("utf8"));
  const payload = JSON.parse(base64UrlDecode(encodedPayload).toString("utf8"));
  const jwk = selectJwk(jwks, header.kid);
  const publicKey = crypto.createPublicKey({ key: jwk, format: "jwk" });
  const verified = crypto.verify(
    "RSA-SHA256",
    Buffer.from(`${encodedHeader}.${encodedPayload}`),
    publicKey,
    base64UrlDecode(encodedSignature)
  );
  if (!verified) {
    throw new Error(`JWT signature did not verify for kid=${header.kid ?? "<missing>"}`);
  }
  assertEqual(payload.iss, expectations.expectedIssuer, "internal JWT issuer");
  assertAudience(payload.aud, expectations.expectedAudience);
  assertEqual(payload.token_use, expectations.expectedTokenUse, "internal JWT token_use");
  if (payload.exp && payload.exp < Math.floor(Date.now() / 1000)) {
    throw new Error("internal JWT is expired");
  }
  return payload;
}

function selectJwk(jwks, kid) {
  const keys = Array.isArray(jwks.keys) ? jwks.keys : [];
  const jwk = kid ? keys.find((key) => key.kid === kid) : keys[0];
  if (!jwk) {
    throw new Error(`JWKS did not include kid=${kid ?? "<missing>"}`);
  }
  if (jwk.kty !== "RSA" || jwk.alg !== "RS256") {
    throw new Error(`JWKS key ${jwk.kid ?? "<missing>"} must be RSA/RS256`);
  }
  return jwk;
}

async function getJson(url) {
  const response = await fetch(url);
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`${url} returned ${response.status}: ${text.slice(0, 300)}`);
  }
  return text ? JSON.parse(text) : {};
}

async function postForm(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body
  });
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`${url} returned ${response.status}: ${text.slice(0, 500)}`);
  }
  return text ? JSON.parse(text) : {};
}

function assertEqual(actual, expected, name) {
  if (actual !== expected) {
    throw new Error(`${name} expected ${expected}, got ${actual}`);
  }
}

function assertAudience(actual, expected) {
  const values = Array.isArray(actual) ? actual.map(String) : [String(actual)];
  if (!values.includes(expected)) {
    throw new Error(`internal JWT audience expected ${expected}, got ${values.join(",")}`);
  }
}

function base64UrlDecode(value) {
  return Buffer.from(value.replace(/-/g, "+").replace(/_/g, "/"), "base64");
}

function stripTrailingSlash(value) {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

function requiredEnv(name) {
  const value = process.env[name];
  if (!value || !value.trim()) {
    throw new Error(`${name} is required`);
  }
  return value.trim();
}

function record(name, pass, detail = "") {
  checks.push({ name, pass, detail });
  const status = pass ? "PASS" : "FAIL";
  console.log(`[${status}] ${name}${detail ? ` - ${detail}` : ""}`);
}

function printSummary() {
  const failed = checks.filter((check) => !check.pass);
  console.log(`\n${checks.length - failed.length}/${checks.length} checks passed`);
  if (failed.length > 0) {
    process.exitCode = 1;
    for (const check of failed) {
      console.error(`FAILED: ${check.name} ${check.detail}`);
    }
    return;
  }
  console.log("Keycloak security smoke passed");
}

main().catch((error) => {
  console.error(`Smoke failed: ${error.message}`);
  process.exit(1);
});
