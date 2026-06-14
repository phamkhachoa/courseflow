#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF_USAGE'
Usage: scripts/validate-prod-profile.sh [--compose] [--include-observability]

Validates the CourseFlow production Compose profile without starting containers.

Options:
  --compose                 Also run docker compose config and validate published ports.
  --include-observability   Include Prometheus/Grafana prod files and require GRAFANA_ADMIN_PASSWORD.
  -h, --help                Show this help.
EOF_USAGE
}

fail() {
  echo "prod profile validation failed: $*" >&2
  exit 1
}

validate_compose=0
include_observability=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --compose)
      validate_compose=1
      ;;
    --include-observability)
      validate_compose=1
      include_observability=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "unknown argument: $1"
      ;;
  esac
  shift
done

trimmed_is_empty() {
  [ -z "$(printf '%s' "$1" | tr -d '[:space:]')" ]
}

check_secret() {
  local name="$1"
  local min_length="$2"
  shift 2

  local value="${!name-}"
  if trimmed_is_empty "$value"; then
    fail "$name must be set and non-blank"
  fi

  if [ "${#value}" -lt "$min_length" ]; then
    fail "$name must be at least $min_length characters"
  fi

  local lower_value
  lower_value="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')"

  case "$lower_value" in
    *change-me*|*changeme*|*default*|*placeholder*|*replace-with*)
      fail "$name still looks like a placeholder"
      ;;
  esac

  local forbidden
  for forbidden in "$@"; do
    if [ "$lower_value" = "$forbidden" ]; then
      fail "$name is set to an insecure default value"
    fi
  done
}

check_value() {
  local name="$1"
  local value="${!name-}"
  if trimmed_is_empty "$value"; then
    fail "$name must be set and non-blank"
  fi
}

check_positive_int() {
  local name="$1"
  local default_value="$2"
  local value="${!name:-$default_value}"
  if ! [[ "$value" =~ ^[1-9][0-9]*$ ]]; then
    fail "$name must be a positive integer"
  fi
}

check_pem_value() {
  local name="$1"
  local begin_marker="$2"
  local value="${!name-}"
  check_value "$name"
  if [[ "$value" != *"$begin_marker"* ]]; then
    fail "$name must be a PEM value containing $begin_marker"
  fi

  local lower_value
  lower_value="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')"
  case "$lower_value" in
    *change-me*|*changeme*|*placeholder*|*replace-with*)
      fail "$name still looks like a placeholder"
      ;;
  esac
}

check_not_local_url() {
  local name="$1"
  local value="${!name-}"
  case "$value" in
    http://localhost*|https://localhost*|http://127.*|https://127.*)
      fail "$name must not point at localhost in the prod profile"
      ;;
  esac
}

check_liquibase_contexts() {
  local contexts="${SPRING_LIQUIBASE_CONTEXTS:-prod}"
  local normalized
  normalized="$(printf '%s' "$contexts" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  case ",$normalized," in
    *,demo,*)
      fail "SPRING_LIQUIBASE_CONTEXTS must not include demo in the prod profile"
      ;;
  esac
}

check_access_control_resolution_mode() {
  local mode="${ACCESS_CONTROL_RESOLUTION_MODE:-required}"
  local normalized
  normalized="$(printf '%s' "$mode" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  if [ "$normalized" != "required" ]; then
    fail "ACCESS_CONTROL_RESOLUTION_MODE must be required in the prod profile"
  fi
}

check_gateway_identity_routes() {
  local gateway_config="$backend_dir/services/api-gateway/src/main/resources/application.yml"
  if grep -Eq 'id:[[:space:]]*identity-auth-v1' "$gateway_config"; then
    fail "/api/v1/auth/** must not route to identity-service in the Keycloak gateway profile"
  fi
  if grep -Eq 'id:[[:space:]]*identity-user-me' "$gateway_config"; then
    fail "/api/v1/users/me must route to user-management-service, not identity-service"
  fi
  if grep -Eq 'id:[[:space:]]*identity-admin-users' "$gateway_config"; then
    fail "/api/admin/v1/users routes must use user-management-service/access-control-service in the Keycloak profile"
  fi
}

check_sts_allowed_clients() {
  local default_clients="api-gateway,access-control-service,user-management-service,organization-service,course-service,enrollment-service,assignment-service,deadline-service,announcement-service,portfolio-service,discussion-service,notification-service,chat-service,media-service,search-service,analytics-service,gradebook-service,quiz-service,certificate-service,peer-review-service,live-session-service,review-service,checkout-service,promotion-service,loyalty-service,outbox-relay"
  local clients="${COURSEFLOW_STS_ALLOWED_CLIENTS:-$default_clients}"
  local normalized
  normalized="$(printf '%s' "$clients" | tr '[:space:]' ',' | tr -s ',')"
  if trimmed_is_empty "$normalized"; then
    fail "COURSEFLOW_STS_ALLOWED_CLIENTS must be set and non-blank"
  fi
  case ",$normalized," in
    *,\*,*)
      fail "COURSEFLOW_STS_ALLOWED_CLIENTS must not use wildcard '*' in the prod profile"
      ;;
  esac
  case ",$normalized," in
    *,identity-service,*)
      fail "identity-service must not be an STS client in the Keycloak production profile"
      ;;
  esac
  local required
  for required in api-gateway access-control-service user-management-service organization-service course-service \
    enrollment-service assignment-service deadline-service announcement-service portfolio-service discussion-service \
    notification-service chat-service media-service search-service analytics-service gradebook-service quiz-service \
    certificate-service peer-review-service live-session-service review-service checkout-service promotion-service \
    loyalty-service outbox-relay; do
    case ",$normalized," in
      *,"$required",*)
        ;;
      *)
        fail "COURSEFLOW_STS_ALLOWED_CLIENTS must include $required"
        ;;
    esac
  done
}

check_sts_allowed_service_scopes() {
  local default_scopes="internal:service,internal:token-exchange,internal:user,internal:identity:resolve,internal:identity:provision,internal:authz:check,internal:authz:assert-topology,internal:user-directory:read,internal:user-directory:write,internal:role-assignment:read,internal:role-assignment:write,internal:role-management:read,internal:role-management:write,internal:profile:read,internal:profile:write,internal:backoffice,internal:promotion:admin,internal:promotion:evaluate,internal:promotion:reserve,internal:promotion:commit,internal:promotion:cancel,internal:promotion:reverse,internal:loyalty:admin,internal:loyalty:read,internal:loyalty:earn,internal:loyalty:burn,internal:loyalty:reverse,internal:loyalty:adjust,internal:loyalty:expire"
  local scopes="${COURSEFLOW_STS_ALLOWED_SERVICE_SCOPES:-$default_scopes}"
  local normalized
  normalized="$(printf '%s' "$scopes" | tr '[:space:]' ',' | tr -s ',')"
  if trimmed_is_empty "$normalized"; then
    fail "COURSEFLOW_STS_ALLOWED_SERVICE_SCOPES must be set and non-blank"
  fi
  case ",$normalized," in
    *,\*,*)
      fail "COURSEFLOW_STS_ALLOWED_SERVICE_SCOPES must not use wildcard '*' in the prod profile"
      ;;
  esac
  local required
  for required in internal:service internal:token-exchange internal:user internal:identity:resolve internal:identity:provision \
    internal:authz:check internal:authz:assert-topology internal:user-directory:read internal:user-directory:write \
    internal:role-assignment:read internal:role-assignment:write internal:role-management:read \
    internal:role-management:write internal:profile:read internal:profile:write internal:backoffice \
    internal:promotion:admin internal:promotion:evaluate internal:promotion:reserve internal:promotion:commit \
    internal:promotion:cancel internal:promotion:reverse internal:loyalty:admin internal:loyalty:read \
    internal:loyalty:earn internal:loyalty:burn internal:loyalty:reverse internal:loyalty:adjust \
    internal:loyalty:expire; do
    case ",$normalized," in
      *,"$required",*)
        ;;
      *)
        fail "COURSEFLOW_STS_ALLOWED_SERVICE_SCOPES must include $required"
        ;;
    esac
  done
}

check_sts_client_policy() {
  COURSEFLOW_STS_CLIENT_SECRETS="${COURSEFLOW_STS_CLIENT_SECRETS-}" \
  COURSEFLOW_STS_CLIENT_SCOPES="${COURSEFLOW_STS_CLIENT_SCOPES-}" \
    node <<'EOF_NODE' || fail "COURSEFLOW_STS per-client secret/scope policy is not production-safe"
const requiredClients = [
  "api-gateway",
  "access-control-service",
  "user-management-service",
  "organization-service",
  "course-service",
  "enrollment-service",
  "assignment-service",
  "deadline-service",
  "announcement-service",
  "portfolio-service",
  "discussion-service",
  "notification-service",
  "chat-service",
  "media-service",
  "search-service",
  "analytics-service",
  "gradebook-service",
  "quiz-service",
  "certificate-service",
  "peer-review-service",
  "live-session-service",
  "review-service",
  "checkout-service",
  "promotion-service",
  "loyalty-service",
  "outbox-relay"
];
const requiredUserManagementScopes = [
  "internal:identity:provision",
  "internal:authz:check",
  "internal:user-directory:read",
  "internal:user-directory:write",
  "internal:role-assignment:read"
];
const topologyAssertionClients = new Set(["organization-service", "course-service"]);
const topologyAssertionScopes = new Set(["internal:authz:check", "internal:authz:assert-topology"]);
const promotionAdminScope = "internal:promotion:admin";
const promotionRuntimeScopes = new Set([
  "internal:promotion:evaluate",
  "internal:promotion:reserve",
  "internal:promotion:commit",
  "internal:promotion:cancel",
  "internal:promotion:reverse"
]);
const promotionRuntimeClients = new Set(["enrollment-service", "checkout-service"]);
const loyaltyAdminScope = "internal:loyalty:admin";
const loyaltyCheckoutScopes = new Set([
  "internal:loyalty:earn",
  "internal:loyalty:burn",
  "internal:loyalty:reverse",
  "internal:loyalty:read"
]);
const loyaltyServiceScopes = new Set([
  "internal:loyalty:admin",
  "internal:loyalty:read"
]);
const loyaltyMutationScopes = new Set([
  "internal:loyalty:earn",
  "internal:loyalty:burn",
  "internal:loyalty:reverse"
]);
const loyaltyOperatorScopes = new Set([
  "internal:loyalty:admin",
  "internal:loyalty:adjust",
  "internal:loyalty:expire"
]);
const defaultClientScopes =
  "api-gateway=internal:service,internal:token-exchange;"
  + "access-control-service=internal:service;"
  + "user-management-service=internal:identity:provision,internal:authz:check,internal:user-directory:read,internal:user-directory:write,internal:role-assignment:read;"
  + "organization-service=internal:service,internal:authz:check,internal:authz:assert-topology;"
  + "course-service=internal:service,internal:user,internal:authz:check,internal:authz:assert-topology;"
  + "enrollment-service=internal:service,internal:promotion:evaluate,internal:promotion:reserve,"
  + "internal:promotion:commit,internal:promotion:cancel,internal:promotion:reverse;"
  + "assignment-service=internal:service;"
  + "deadline-service=internal:service;"
  + "announcement-service=internal:service;"
  + "portfolio-service=internal:service;"
  + "discussion-service=internal:service;"
  + "notification-service=internal:service;"
  + "chat-service=internal:service,internal:token-exchange;"
  + "media-service=internal:service;"
  + "search-service=internal:service;"
  + "analytics-service=internal:service;"
  + "gradebook-service=internal:service;"
  + "quiz-service=internal:service;"
  + "certificate-service=internal:service;"
  + "peer-review-service=internal:service;"
  + "live-session-service=internal:service;"
  + "review-service=internal:service;"
  + "checkout-service=internal:service,internal:promotion:evaluate,internal:promotion:reserve,"
  + "internal:promotion:commit,internal:promotion:cancel,internal:promotion:reverse,"
  + "internal:loyalty:earn,internal:loyalty:burn,internal:loyalty:reverse,internal:loyalty:read;"
  + "promotion-service=internal:service,internal:promotion:admin;"
  + "loyalty-service=internal:service,internal:loyalty:admin,internal:loyalty:read;"
  + "outbox-relay=internal:service";
const privilegedScopes = new Set([
  "internal:identity:resolve",
  "internal:identity:provision",
  "internal:authz:check",
  "internal:authz:assert-topology",
  "internal:user-directory:read",
  "internal:user-directory:write",
  "internal:role-assignment:read",
  "internal:role-assignment:write",
  "internal:role-management:read",
  "internal:role-management:write",
  "internal:profile:read",
  "internal:profile:write",
  "internal:backoffice"
]);
const violations = [];

function parseMap(raw, name, valuesAsScopes = false, required = true) {
  if (!raw || !raw.trim()) {
    if (required) {
      violations.push(`${name} must be set and non-blank`);
    }
    return new Map();
  }
  const map = new Map();
  for (const entry of raw.split(";").map((value) => value.trim()).filter(Boolean)) {
    const separator = entry.indexOf("=");
    if (separator <= 0 || separator === entry.length - 1) {
      violations.push(`${name} has invalid entry: ${entry}`);
      continue;
    }
    const client = entry.slice(0, separator).trim();
    const value = entry.slice(separator + 1).trim();
    if (client === "*" || client === "identity-service") {
      violations.push(`${name} must not include client ${client}`);
    }
    if (map.has(client)) {
      violations.push(`${name} repeats client ${client}`);
    }
    map.set(client, valuesAsScopes ? value.split(/[,\s]+/).map((scope) => scope.trim()).filter(Boolean) : value);
  }
  return map;
}

function clientSecretEnvName(client) {
  return `COURSEFLOW_STS_${client.toUpperCase().replace(/-/g, "_")}_SECRET`;
}

function resolveClientSecrets() {
  const configured = parseMap(process.env.COURSEFLOW_STS_CLIENT_SECRETS, "COURSEFLOW_STS_CLIENT_SECRETS", false, false);
  if (configured.size > 0) {
    return configured;
  }
  const resolved = new Map();
  for (const client of requiredClients) {
    const envName = clientSecretEnvName(client);
    const value = (process.env[envName] ?? "").trim();
    if (!value) {
      violations.push(`${envName} must be set when COURSEFLOW_STS_CLIENT_SECRETS is not provided`);
      continue;
    }
    resolved.set(client, value);
  }
  return resolved;
}

function secretLooksWeak(secret) {
  const lower = String(secret ?? "").toLowerCase();
  return lower.length < 32
    || lower.includes("change-me")
    || lower.includes("changeme")
    || lower.includes("default")
    || lower.includes("placeholder")
    || lower.includes("replace-with")
    || ["courseflow", "password", "admin"].includes(lower);
}

const secrets = resolveClientSecrets();
const scopes = parseMap(process.env.COURSEFLOW_STS_CLIENT_SCOPES || defaultClientScopes, "COURSEFLOW_STS_CLIENT_SCOPES", true);

for (const client of requiredClients) {
  if (!secrets.has(client)) {
    violations.push(`COURSEFLOW_STS_CLIENT_SECRETS missing ${client}`);
  }
  if (!scopes.has(client)) {
    violations.push(`COURSEFLOW_STS_CLIENT_SCOPES missing ${client}`);
  }
}

const seenSecrets = new Map();
for (const [client, secret] of secrets) {
  if (secretLooksWeak(secret)) {
    violations.push(`COURSEFLOW_STS_CLIENT_SECRETS[${client}] is weak or placeholder-like`);
  }
  if (seenSecrets.has(secret)) {
    violations.push(`COURSEFLOW_STS_CLIENT_SECRETS reuses the same secret for ${seenSecrets.get(secret)} and ${client}`);
  }
  seenSecrets.set(secret, client);
}

for (const [client, clientScopes] of scopes) {
  if (clientScopes.length === 0) {
    violations.push(`COURSEFLOW_STS_CLIENT_SCOPES[${client}] must not be empty`);
  }
  if (clientScopes.includes("*")) {
    violations.push(`COURSEFLOW_STS_CLIENT_SCOPES[${client}] must not include wildcard '*'`);
  }
  for (const scope of clientScopes) {
    const allowedTopologyScope = topologyAssertionClients.has(client) && topologyAssertionScopes.has(scope);
    if (privilegedScopes.has(scope) && client !== "user-management-service" && !allowedTopologyScope) {
      violations.push(`${client} must not be granted privileged STS scope ${scope}`);
    }
    if (scope === "internal:user" && client !== "course-service") {
      violations.push(`${client} must not be granted trusted-user delegation scope internal:user`);
    }
    if (scope === "internal:token-exchange" && !["api-gateway", "chat-service"].includes(client)) {
      violations.push(`${client} must not be granted token exchange scope internal:token-exchange`);
    }
    if (promotionRuntimeScopes.has(scope) && !promotionRuntimeClients.has(client)) {
      violations.push(`${client} must not be granted promotion runtime operation scope ${scope} by default`);
    }
    if (scope === promotionAdminScope && client !== "promotion-service") {
      violations.push(`${client} must not be granted promotion admin scope ${scope} by default`);
    }
    if (scope === "internal:loyalty:read" && !["checkout-service", "loyalty-service"].includes(client)) {
      violations.push(`${client} must not be granted loyalty read scope ${scope} by default`);
    }
    if (loyaltyMutationScopes.has(scope) && client !== "checkout-service") {
      violations.push(`${client} must not be granted loyalty mutation scope ${scope} by default`);
    }
    if (loyaltyOperatorScopes.has(scope) && client !== "loyalty-service") {
      violations.push(`${client} must not be granted loyalty operator scope ${scope} by default`);
    }
    if (scope.startsWith("internal:role-management:")) {
      violations.push(`${client} must not be granted role-management machine scope by default`);
    }
  }
}

const userManagementScopes = new Set(scopes.get("user-management-service") ?? []);
for (const scope of requiredUserManagementScopes) {
  if (!userManagementScopes.has(scope)) {
    violations.push(`user-management-service must be granted ${scope}`);
  }
}
const courseScopes = new Set(scopes.get("course-service") ?? []);
if (!courseScopes.has("internal:service") || !courseScopes.has("internal:user")) {
  violations.push("course-service must be granted internal:service and internal:user");
}
for (const client of topologyAssertionClients) {
  const clientScopes = new Set(scopes.get(client) ?? []);
  for (const scope of topologyAssertionScopes) {
    if (!clientScopes.has(scope)) {
      violations.push(`${client} must be granted ${scope} to assert server-derived authorization topology`);
    }
  }
}
for (const client of ["api-gateway", "chat-service"]) {
  const clientScopeSet = new Set(scopes.get(client) ?? []);
  if (!clientScopeSet.has("internal:token-exchange")) {
    violations.push(`${client} must be granted internal:token-exchange`);
  }
}
for (const client of promotionRuntimeClients) {
  const clientScopes = new Set(scopes.get(client) ?? []);
  for (const scope of promotionRuntimeScopes) {
    if (!clientScopes.has(scope)) {
      violations.push(`${client} must be granted ${scope}`);
    }
  }
}
const checkoutScopes = new Set(scopes.get("checkout-service") ?? []);
for (const scope of loyaltyCheckoutScopes) {
  if (!checkoutScopes.has(scope)) {
    violations.push(`checkout-service must be granted ${scope}`);
  }
}
const promotionScopes = new Set(scopes.get("promotion-service") ?? []);
if (!promotionScopes.has(promotionAdminScope)) {
  violations.push(`promotion-service must be granted ${promotionAdminScope}`);
}
const loyaltyScopes = new Set(scopes.get("loyalty-service") ?? []);
for (const scope of loyaltyServiceScopes) {
  if (!loyaltyScopes.has(scope)) {
    violations.push(`loyalty-service must be granted ${scope}`);
  }
}

if (violations.length > 0) {
  for (const violation of violations) {
    console.error(`  - ${violation}`);
  }
  process.exit(1);
}
EOF_NODE
}

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
backend_dir="$(CDPATH= cd -- "$script_dir/.." && pwd)"

if ! command -v node >/dev/null 2>&1; then
  fail "node is required for Keycloak realm validation"
fi

node "$script_dir/validate-keycloak-realm.mjs" \
  "$backend_dir/infra/docker/keycloak/courseflow-realm.prod-template.json" \
  --prod-template >/dev/null

check_secret CERTIFICATE_SIGNING_SECRET 32 \
  courseflow-local-certificate-signing-secret-change-me-32 \
  courseflow \
  password \
  admin
check_secret COURSEFLOW_DB_PASSWORD 12 \
  courseflow \
  password \
  admin
check_secret COURSEFLOW_STORAGE_ACCESS_KEY 8 \
  courseflow \
  minioadmin \
  admin
check_secret COURSEFLOW_STORAGE_SECRET_KEY 16 \
  courseflow \
  minioadmin \
  password \
  admin
check_secret KEYCLOAK_ADMIN_PASSWORD 12 \
  admin \
  password \
  courseflow
check_value COURSEFLOW_STORAGE_EXTERNAL_ENDPOINT
check_not_local_url COURSEFLOW_STORAGE_EXTERNAL_ENDPOINT
check_value EXTERNAL_TOKEN_MODE
if [ "${EXTERNAL_TOKEN_MODE}" != "oidc" ]; then
  fail "EXTERNAL_TOKEN_MODE must be oidc in the prod profile"
fi
check_value COURSEFLOW_INTERNAL_JWT_ALGORITHM
if [ "${COURSEFLOW_INTERNAL_JWT_ALGORITHM}" != "RS256" ]; then
  fail "COURSEFLOW_INTERNAL_JWT_ALGORITHM must be RS256 in the prod profile"
fi
check_pem_value COURSEFLOW_INTERNAL_JWT_PRIVATE_KEY "-----BEGIN PRIVATE KEY-----"
check_value COURSEFLOW_INTERNAL_JWT_VERIFICATION_MODE
if [ "${COURSEFLOW_INTERNAL_JWT_VERIFICATION_MODE}" != "jwks" ]; then
  fail "COURSEFLOW_INTERNAL_JWT_VERIFICATION_MODE must be jwks in the prod profile"
fi
check_value COURSEFLOW_INTERNAL_JWT_JWKS_URI
check_sts_allowed_clients
check_sts_allowed_service_scopes
check_sts_client_policy
check_value TOKEN_CONVERTER_URI
check_access_control_resolution_mode
check_gateway_identity_routes
check_value KEYCLOAK_ISSUER_URI
check_not_local_url KEYCLOAK_ISSUER_URI
check_value KEYCLOAK_JWK_SET_URI
check_not_local_url KEYCLOAK_JWK_SET_URI
check_value KEYCLOAK_AUDIENCE
check_value KEYCLOAK_PUBLIC_BASE_URL
check_not_local_url KEYCLOAK_PUBLIC_BASE_URL
check_value KEYCLOAK_BASE_URL
check_not_local_url KEYCLOAK_BASE_URL
check_value KEYCLOAK_REALM
check_value KEYCLOAK_ADMIN_CLIENT_ID
check_secret KEYCLOAK_ADMIN_CLIENT_SECRET 24 \
  admin \
  password \
  courseflow \
  local-courseflow-iam-lifecycle-secret-change-me \
  local-keycloak-user-lifecycle-secret-change-me \
  __REPLACE_WITH_GENERATED_LIFECYCLE_CLIENT_SECRET__
check_value PROMOTION_COUPON_FINGERPRINT_KEY_ID
case "$PROMOTION_COUPON_FINGERPRINT_KEY_ID" in
  *[!A-Za-z0-9._-]*)
    fail "PROMOTION_COUPON_FINGERPRINT_KEY_ID may only contain letters, digits, dot, underscore, or hyphen"
    ;;
esac
check_secret PROMOTION_COUPON_FINGERPRINT_PEPPER 32 \
  courseflow-local-coupon-fingerprint-pepper-change-me \
  courseflow \
  password \
  admin
check_value PROMOTION_COUPON_LEGACY_FALLBACK_ENABLED
case "$PROMOTION_COUPON_LEGACY_FALLBACK_ENABLED" in
  true|false)
    ;;
  *)
    fail "PROMOTION_COUPON_LEGACY_FALLBACK_ENABLED must be true or false in the prod profile"
    ;;
esac
check_positive_int PROMOTION_COUPON_IMPORT_ISSUE_EXPORT_MAX_ROWS 10000
check_secret PROMOTION_REQUEST_SNAPSHOT_HASH_SECRET 32 \
  local-request-snapshot-secret-change-me-32 \
  courseflow-local-request-snapshot-hash-secret-change-me-32 \
  courseflow-local-internal-jwt-secret-change-me-32 \
  courseflow \
  password \
  admin
check_value PROMOTION_COUPON_ABUSE_GUARD_MODE
case "$PROMOTION_COUPON_ABUSE_GUARD_MODE" in
  shadow|enforced)
    ;;
  disabled)
    fail "PROMOTION_COUPON_ABUSE_GUARD_MODE must not be disabled in the prod profile"
    ;;
  *)
    fail "PROMOTION_COUPON_ABUSE_GUARD_MODE must be shadow or enforced in the prod profile"
    ;;
esac
check_value PROMOTION_COUPON_ABUSE_GUARD_KEY_ID
case "$PROMOTION_COUPON_ABUSE_GUARD_KEY_ID" in
  *[!A-Za-z0-9._-]*)
    fail "PROMOTION_COUPON_ABUSE_GUARD_KEY_ID may only contain letters, digits, dot, underscore, or hyphen"
    ;;
esac
check_secret PROMOTION_COUPON_ABUSE_GUARD_PEPPER 32 \
  courseflow-local-coupon-abuse-guard-pepper-change-me \
  courseflow \
  password \
  admin
case "${PROMOTION_COUPON_ABUSE_GUARD_FAIL_POLICY:-allow_with_alert}" in
  allow_with_alert|deny_coupon_required)
    ;;
  *)
    fail "PROMOTION_COUPON_ABUSE_GUARD_FAIL_POLICY must be allow_with_alert or deny_coupon_required"
    ;;
esac
check_value PROMOTION_ADMIN_OPERATION_RATE_GUARD_MODE
case "$PROMOTION_ADMIN_OPERATION_RATE_GUARD_MODE" in
  shadow|enforced)
    ;;
  disabled)
    fail "PROMOTION_ADMIN_OPERATION_RATE_GUARD_MODE must not be disabled in the prod profile"
    ;;
  *)
    fail "PROMOTION_ADMIN_OPERATION_RATE_GUARD_MODE must be shadow or enforced in the prod profile"
    ;;
esac
check_value PROMOTION_ADMIN_OPERATION_RATE_GUARD_KEY_ID
case "$PROMOTION_ADMIN_OPERATION_RATE_GUARD_KEY_ID" in
  *[!A-Za-z0-9._-]*)
    fail "PROMOTION_ADMIN_OPERATION_RATE_GUARD_KEY_ID may only contain letters, digits, dot, underscore, or hyphen"
    ;;
esac
check_secret PROMOTION_ADMIN_OPERATION_RATE_GUARD_PEPPER 32 \
  courseflow-local-admin-operation-rate-guard-pepper-change-me \
  courseflow \
  password \
  admin
check_positive_int PROMOTION_ADMIN_OPERATION_RATE_GUARD_ACTOR_CAPACITY 1
check_positive_int PROMOTION_ADMIN_OPERATION_RATE_GUARD_SOURCE_CLIENT_CAPACITY 1
check_positive_int PROMOTION_ADMIN_OPERATION_RATE_GUARD_APPLICATION_CAPACITY 1
check_positive_int PROMOTION_ADMIN_OPERATION_RATE_GUARD_CAMPAIGN_CAPACITY 1
check_positive_int PROMOTION_ADMIN_OPERATION_RATE_GUARD_CONTENT_CAPACITY 1
check_positive_int PROMOTION_ADMIN_OPERATION_RATE_GUARD_MISSING_IDENTITY_CAPACITY 1
case "${PROMOTION_ADMIN_OPERATION_RATE_GUARD_FAIL_POLICY:-deny}" in
  allow_with_alert|deny)
    ;;
  *)
    fail "PROMOTION_ADMIN_OPERATION_RATE_GUARD_FAIL_POLICY must be allow_with_alert or deny"
    ;;
esac
if [ "${PROMOTION_RETENTION_EXECUTION_ENABLED:-false}" = "true" ] &&
  [ "${PROMOTION_RETENTION_EXECUTION_PROD_APPROVED:-false}" != "true" ]; then
  fail "PROMOTION_RETENTION_EXECUTION_ENABLED=true requires PROMOTION_RETENTION_EXECUTION_PROD_APPROVED=true after approval workflow, restore-drill registry, and runbook sign-off"
fi
check_value KEYCLOAK_SETUP_EMAIL_CLIENT_ID
check_value KEYCLOAK_SETUP_EMAIL_REDIRECT_URI
check_not_local_url KEYCLOAK_SETUP_EMAIL_REDIRECT_URI
check_liquibase_contexts

if [ "${COURSEFLOW_STORAGE_ALLOW_DEMO_CREDENTIALS:-false}" = "true" ] ||
  [ "${STORAGE_ALLOW_DEMO_CREDENTIALS:-false}" = "true" ]; then
  fail "storage demo credentials must be disabled in the prod profile"
fi

if [ "$include_observability" -eq 1 ]; then
  check_secret GRAFANA_ADMIN_PASSWORD 12 \
    admin \
    password \
    courseflow
fi

if [ "$validate_compose" -eq 1 ]; then
  if ! command -v docker >/dev/null 2>&1; then
    fail "docker is required for --compose"
  fi
  if ! command -v node >/dev/null 2>&1; then
    fail "node is required for --compose port validation"
  fi

  docker_dir="$backend_dir/infra/docker"
  config_json="$(mktemp)"
  trap 'rm -f "$config_json"' EXIT

  compose_args=(
    -f "$docker_dir/docker-compose.yml"
    -f "$docker_dir/docker-compose.services.yml"
  )

  if [ "$include_observability" -eq 1 ]; then
    compose_args+=(-f "$docker_dir/docker-compose.observability.yml")
  fi

  compose_args+=(-f "$docker_dir/docker-compose.prod.yml")

  if [ "$include_observability" -eq 1 ]; then
    compose_args+=(-f "$docker_dir/docker-compose.prod.observability.yml")
  fi

  docker compose "${compose_args[@]}" config --format json > "$config_json"

  allowed_ports="api-gateway"
  if [ "$include_observability" -eq 1 ]; then
    allowed_ports="$allowed_ports,prometheus,grafana"
  fi

  ALLOWED_PORT_SERVICES="$allowed_ports" node - "$config_json" <<'EOF_NODE'
const fs = require("fs");

const configPath = process.argv[2];
const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
const services = config.services ?? {};
const allowedPortServices = new Set(
  (process.env.ALLOWED_PORT_SERVICES ?? "").split(",").filter(Boolean)
);
const forbiddenValues = new Set([
  "admin",
  "courseflow",
  "password",
  "minioadmin",
  "courseflow-local-cluster-jwt-secret-change-me-32",
  "courseflow-local-internal-jwt-secret-change-me-32",
  "courseflow-local-certificate-signing-secret-change-me-32"
]);

const publishedPortViolations = [];
const secretViolations = [];
const keycloakViolations = [];
const internalJwtViolations = [];
const tokenConverterViolations = [];
const legacyIdentityViolations = [];
const requiredClients = [
  "api-gateway",
  "access-control-service",
  "user-management-service",
  "organization-service",
  "course-service",
  "enrollment-service",
  "assignment-service",
  "deadline-service",
  "announcement-service",
  "portfolio-service",
  "discussion-service",
  "notification-service",
  "chat-service",
  "media-service",
  "search-service",
  "analytics-service",
  "gradebook-service",
  "quiz-service",
  "certificate-service",
  "peer-review-service",
  "live-session-service",
  "review-service",
  "checkout-service",
  "promotion-service",
  "loyalty-service",
  "outbox-relay"
];
const promotionAdminScope = "internal:promotion:admin";
const promotionRuntimeScopes = new Set([
  "internal:promotion:evaluate",
  "internal:promotion:reserve",
  "internal:promotion:commit",
  "internal:promotion:cancel",
  "internal:promotion:reverse"
]);
const promotionRuntimeClients = new Set(["enrollment-service", "checkout-service"]);
const loyaltyAdminScope = "internal:loyalty:admin";
const loyaltyCheckoutScopes = new Set([
  "internal:loyalty:earn",
  "internal:loyalty:burn",
  "internal:loyalty:reverse",
  "internal:loyalty:read"
]);
const loyaltyServiceScopes = new Set([
  "internal:loyalty:admin",
  "internal:loyalty:read"
]);
const loyaltyMutationScopes = new Set([
  "internal:loyalty:earn",
  "internal:loyalty:burn",
  "internal:loyalty:reverse"
]);
const loyaltyOperatorScopes = new Set([
  "internal:loyalty:admin",
  "internal:loyalty:adjust",
  "internal:loyalty:expire"
]);

function envEntries(environment) {
  if (!environment) return [];
  if (Array.isArray(environment)) {
    return environment.map((entry) => {
      const index = String(entry).indexOf("=");
      return index === -1 ? [String(entry), ""] : [String(entry).slice(0, index), String(entry).slice(index + 1)];
    });
  }
  return Object.entries(environment).map(([key, value]) => [key, value == null ? "" : String(value)]);
}

function pairMap(raw, valueParser = (value) => value) {
  const map = new Map();
  for (const entry of String(raw ?? "").split(";").map((value) => value.trim()).filter(Boolean)) {
    const separator = entry.indexOf("=");
    if (separator <= 0 || separator === entry.length - 1) {
      continue;
    }
    map.set(entry.slice(0, separator).trim(), valueParser(entry.slice(separator + 1).trim()));
  }
  return map;
}

for (const [serviceName, service] of Object.entries(services)) {
  const ports = Array.isArray(service.ports) ? service.ports : [];
  if (ports.length > 0 && !allowedPortServices.has(serviceName)) {
    for (const port of ports) {
      const published = port.published ?? "";
      const target = port.target ?? "";
      const protocol = port.protocol ?? "tcp";
      publishedPortViolations.push(`${serviceName}:${published}->${target}/${protocol}`);
    }
  }

  const serviceEnv = new Map(envEntries(service.environment));
  const internalJwtAlgorithm = (serviceEnv.get("COURSEFLOW_INTERNAL_JWT_ALGORITHM") ?? "").trim().toUpperCase();
  const internalJwtVerificationMode =
    (serviceEnv.get("COURSEFLOW_INTERNAL_JWT_VERIFICATION_MODE") ?? "").trim().toLowerCase();
  const internalJwtJwksUri = (serviceEnv.get("COURSEFLOW_INTERNAL_JWT_JWKS_URI") ?? "").trim();
  const internalJwtPrivateKey = (serviceEnv.get("COURSEFLOW_INTERNAL_JWT_PRIVATE_KEY") ?? "").trim();
  const serviceTokenMode = (serviceEnv.get("COURSEFLOW_INTERNAL_SERVICE_TOKEN_MODE") ?? "").trim().toLowerCase();
  const tokenConverterUri = (serviceEnv.get("TOKEN_CONVERTER_URI") ?? "").trim();
  const isTokenConverter = serviceName === "identity-token-converter-service";

  if (internalJwtAlgorithm === "RS256") {
    if (isTokenConverter) {
      if (!internalJwtPrivateKey) {
        internalJwtViolations.push(`${serviceName} must hold COURSEFLOW_INTERNAL_JWT_PRIVATE_KEY for signing`);
      }
    } else {
      if (internalJwtPrivateKey) {
        internalJwtViolations.push(`${serviceName} must not receive COURSEFLOW_INTERNAL_JWT_PRIVATE_KEY`);
      }
      if (internalJwtVerificationMode !== "jwks") {
        internalJwtViolations.push(`${serviceName} must verify internal JWTs with JWKS`);
      }
      if (!internalJwtJwksUri) {
        internalJwtViolations.push(`${serviceName} must set COURSEFLOW_INTERNAL_JWT_JWKS_URI`);
      }
    }
  }

  if (!isTokenConverter && serviceTokenMode === "sts" && !tokenConverterUri) {
    internalJwtViolations.push(`${serviceName} must set TOKEN_CONVERTER_URI when COURSEFLOW_INTERNAL_SERVICE_TOKEN_MODE=sts`);
  }

  for (const [key, value] of envEntries(service.environment)) {
    const upperKey = key.toUpperCase();
    const lowerValue = value.trim().toLowerCase();
    if (upperKey === "SPRING_LIQUIBASE_CONTEXTS" && lowerValue.split(",").map((part) => part.trim()).includes("demo")) {
      secretViolations.push(`${serviceName}.${key} includes demo`);
    }
    if (upperKey === "COURSEFLOW_INTERNAL_JWT_SECRET" && internalJwtAlgorithm === "RS256") {
      continue;
    }
    if (upperKey === "COURSEFLOW_JWT_SECRET") {
      continue;
    }
    if (/(PASSWORD|SECRET|TOKEN|ACCESS_KEY)$/.test(upperKey)) {
      if (!value.trim()) {
        secretViolations.push(`${serviceName}.${key} is blank`);
      } else if (
        forbiddenValues.has(lowerValue) ||
        lowerValue.includes("change-me") ||
        lowerValue.includes("changeme") ||
        lowerValue.includes("placeholder") ||
        lowerValue.includes("replace-with")
      ) {
        secretViolations.push(`${serviceName}.${key} uses an insecure default`);
      }
    }
  }
}

const keycloak = services.keycloak;
if (!keycloak) {
  keycloakViolations.push("keycloak service is missing");
} else {
  const command = Array.isArray(keycloak.command) ? keycloak.command.join(" ") : String(keycloak.command ?? "");
  if (/\bstart-dev\b/.test(command)) {
    keycloakViolations.push("keycloak command uses start-dev");
  }
  if (/--import-realm\b/.test(command)) {
    keycloakViolations.push("keycloak command imports the local realm");
  }
  const volumes = Array.isArray(keycloak.volumes) ? keycloak.volumes : [];
  for (const volume of volumes) {
    const target = typeof volume === "string" ? volume : String(volume.target ?? "");
    if (target.includes("/opt/keycloak/data/import")) {
      keycloakViolations.push("keycloak mounts the local realm import directory");
    }
  }
  const env = new Map(envEntries(keycloak.environment));
  if ((env.get("KC_DB") ?? "").trim() !== "postgres") {
    keycloakViolations.push("keycloak must use KC_DB=postgres in the prod profile");
  }
}

const tokenConverter = services["identity-token-converter-service"];
let tokenConverterClientSecrets = new Map();
if (!tokenConverter) {
  tokenConverterViolations.push("identity-token-converter-service is missing");
} else {
  const env = new Map(envEntries(tokenConverter.environment));
  const accessControlMode = (env.get("ACCESS_CONTROL_RESOLUTION_MODE") ?? "").trim().toLowerCase();
  if (accessControlMode !== "required") {
    tokenConverterViolations.push("identity-token-converter-service must use ACCESS_CONTROL_RESOLUTION_MODE=required");
  }
  const allowedClients = (env.get("COURSEFLOW_STS_ALLOWED_CLIENTS") ?? "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  const allowedServiceScopes = (env.get("COURSEFLOW_STS_ALLOWED_SERVICE_SCOPES") ?? "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  tokenConverterClientSecrets = pairMap(env.get("COURSEFLOW_STS_CLIENT_SECRETS") ?? "");
  const tokenConverterClientScopes = pairMap(
    env.get("COURSEFLOW_STS_CLIENT_SCOPES") ?? "",
    (value) => value.split(/[,\s]+/).map((scope) => scope.trim()).filter(Boolean)
  );
  const requiredServiceScopes = [
    "internal:service",
    "internal:token-exchange",
    "internal:user",
    "internal:identity:resolve",
    "internal:identity:provision",
    "internal:authz:check",
    "internal:authz:assert-topology",
    "internal:user-directory:read",
    "internal:user-directory:write",
    "internal:role-assignment:read",
    "internal:role-assignment:write",
    "internal:role-management:read",
    "internal:role-management:write",
    "internal:profile:read",
    "internal:profile:write",
    "internal:backoffice",
    "internal:promotion:admin",
    "internal:promotion:evaluate",
    "internal:promotion:reserve",
    "internal:promotion:commit",
    "internal:promotion:cancel",
    "internal:promotion:reverse",
    "internal:loyalty:admin",
    "internal:loyalty:read",
    "internal:loyalty:earn",
    "internal:loyalty:burn",
    "internal:loyalty:reverse",
    "internal:loyalty:adjust",
    "internal:loyalty:expire"
  ];
  if (allowedClients.length === 0) {
    tokenConverterViolations.push("identity-token-converter-service must define COURSEFLOW_STS_ALLOWED_CLIENTS");
  }
  if (allowedClients.includes("*")) {
    tokenConverterViolations.push("COURSEFLOW_STS_ALLOWED_CLIENTS must not include wildcard '*'");
  }
  if (allowedClients.includes("identity-service")) {
    tokenConverterViolations.push("identity-service must not be an STS client in the Keycloak production profile");
  }
  const allowedClientSet = new Set(allowedClients);
  for (const client of requiredClients) {
    if (!allowedClientSet.has(client)) {
      tokenConverterViolations.push(`COURSEFLOW_STS_ALLOWED_CLIENTS missing ${client}`);
    }
  }
  if (allowedServiceScopes.length === 0) {
    tokenConverterViolations.push("identity-token-converter-service must define COURSEFLOW_STS_ALLOWED_SERVICE_SCOPES");
  }
  if (allowedServiceScopes.includes("*")) {
    tokenConverterViolations.push("COURSEFLOW_STS_ALLOWED_SERVICE_SCOPES must not include wildcard '*'");
  }
  if (tokenConverterClientSecrets.size === 0) {
    tokenConverterViolations.push("identity-token-converter-service must define COURSEFLOW_STS_CLIENT_SECRETS");
  }
  if (tokenConverterClientScopes.size === 0) {
    tokenConverterViolations.push("identity-token-converter-service must define COURSEFLOW_STS_CLIENT_SCOPES");
  }
  for (const scope of requiredServiceScopes) {
    if (!allowedServiceScopes.includes(scope)) {
      tokenConverterViolations.push(`COURSEFLOW_STS_ALLOWED_SERVICE_SCOPES must include ${scope}`);
    }
  }
  for (const client of allowedClients) {
    if (!tokenConverterClientSecrets.has(client)) {
      tokenConverterViolations.push(`COURSEFLOW_STS_CLIENT_SECRETS missing ${client}`);
    }
    if (!tokenConverterClientScopes.has(client)) {
      tokenConverterViolations.push(`COURSEFLOW_STS_CLIENT_SCOPES missing ${client}`);
    }
  }
  for (const [client, scopes] of tokenConverterClientScopes) {
    if (scopes.includes("*")) {
      tokenConverterViolations.push(`COURSEFLOW_STS_CLIENT_SCOPES[${client}] must not include wildcard '*'`);
    }
    for (const scope of scopes) {
      if (promotionRuntimeScopes.has(scope) && !promotionRuntimeClients.has(client)) {
        tokenConverterViolations.push(
          `COURSEFLOW_STS_CLIENT_SCOPES[${client}] must not include promotion runtime operation scope ${scope}`
        );
      }
      if (scope === promotionAdminScope && client !== "promotion-service") {
        tokenConverterViolations.push(
          `COURSEFLOW_STS_CLIENT_SCOPES[${client}] must not include promotion admin scope ${scope}`
        );
      }
      if (scope === "internal:loyalty:read" && !["checkout-service", "loyalty-service"].includes(client)) {
        tokenConverterViolations.push(
          `COURSEFLOW_STS_CLIENT_SCOPES[${client}] must not include loyalty read scope ${scope}`
        );
      }
      if (loyaltyMutationScopes.has(scope) && client !== "checkout-service") {
        tokenConverterViolations.push(
          `COURSEFLOW_STS_CLIENT_SCOPES[${client}] must not include loyalty mutation scope ${scope}`
        );
      }
      if (loyaltyOperatorScopes.has(scope) && client !== "loyalty-service") {
        tokenConverterViolations.push(
          `COURSEFLOW_STS_CLIENT_SCOPES[${client}] must not include loyalty operator scope ${scope}`
        );
      }
    }
  }
  for (const client of promotionRuntimeClients) {
    const clientScopes = new Set(tokenConverterClientScopes.get(client) ?? []);
    for (const scope of promotionRuntimeScopes) {
      if (!clientScopes.has(scope)) {
        tokenConverterViolations.push(`COURSEFLOW_STS_CLIENT_SCOPES[${client}] must include ${scope}`);
      }
    }
  }
  const checkoutScopes = new Set(tokenConverterClientScopes.get("checkout-service") ?? []);
  for (const scope of loyaltyCheckoutScopes) {
    if (!checkoutScopes.has(scope)) {
      tokenConverterViolations.push(`COURSEFLOW_STS_CLIENT_SCOPES[checkout-service] must include ${scope}`);
    }
  }
  const promotionScopes = new Set(tokenConverterClientScopes.get("promotion-service") ?? []);
  if (!promotionScopes.has(promotionAdminScope)) {
    tokenConverterViolations.push(`COURSEFLOW_STS_CLIENT_SCOPES[promotion-service] must include ${promotionAdminScope}`);
  }
  const loyaltyScopes = new Set(tokenConverterClientScopes.get("loyalty-service") ?? []);
  for (const scope of loyaltyServiceScopes) {
    if (!loyaltyScopes.has(scope)) {
      tokenConverterViolations.push(`COURSEFLOW_STS_CLIENT_SCOPES[loyalty-service] must include ${scope}`);
    }
  }
}

for (const [serviceName, service] of Object.entries(services)) {
  if (serviceName === "identity-token-converter-service" || serviceName === "identity-service") {
    continue;
  }
  const serviceEnv = new Map(envEntries(service.environment));
  const serviceTokenMode = (serviceEnv.get("COURSEFLOW_INTERNAL_SERVICE_TOKEN_MODE") ?? "").trim().toLowerCase();
  if (serviceTokenMode !== "sts") {
    continue;
  }
  const expectedSecret = tokenConverterClientSecrets.get(serviceName);
  const actualSecret = (serviceEnv.get("COURSEFLOW_STS_CLIENT_SECRET") ?? "").trim();
  if (!actualSecret) {
    tokenConverterViolations.push(`${serviceName} must receive only its own COURSEFLOW_STS_CLIENT_SECRET`);
  } else if (expectedSecret && actualSecret !== expectedSecret) {
    tokenConverterViolations.push(`${serviceName} COURSEFLOW_STS_CLIENT_SECRET does not match converter client secret map`);
  }
}

const identityService = services["identity-service"];
if (identityService) {
  const profiles = Array.isArray(identityService.profiles) ? identityService.profiles : [];
  if (!profiles.includes("legacy-identity")) {
    legacyIdentityViolations.push("identity-service must be behind the legacy-identity profile in prod");
  }
}

if (publishedPortViolations.length > 0) {
  console.error("Unexpected prod published ports:");
  for (const violation of publishedPortViolations) {
    console.error(`  - ${violation}`);
  }
}

if (secretViolations.length > 0) {
  console.error("Unexpected prod secret/default values:");
  for (const violation of secretViolations) {
    console.error(`  - ${violation}`);
  }
}

if (keycloakViolations.length > 0) {
  console.error("Unsafe prod Keycloak configuration:");
  for (const violation of keycloakViolations) {
    console.error(`  - ${violation}`);
  }
}

if (internalJwtViolations.length > 0) {
  console.error("Unsafe prod internal JWT configuration:");
  for (const violation of internalJwtViolations) {
    console.error(`  - ${violation}`);
  }
}

if (tokenConverterViolations.length > 0) {
  console.error("Unsafe prod token converter configuration:");
  for (const violation of tokenConverterViolations) {
    console.error(`  - ${violation}`);
  }
}

if (legacyIdentityViolations.length > 0) {
  console.error("Unsafe prod legacy identity-service configuration:");
  for (const violation of legacyIdentityViolations) {
    console.error(`  - ${violation}`);
  }
}

if (publishedPortViolations.length > 0 || secretViolations.length > 0 ||
    keycloakViolations.length > 0 || internalJwtViolations.length > 0 ||
    tokenConverterViolations.length > 0 || legacyIdentityViolations.length > 0) {
  process.exit(1);
}
EOF_NODE
fi

echo "prod profile validation passed"
