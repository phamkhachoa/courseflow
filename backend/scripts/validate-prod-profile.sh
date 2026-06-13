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

check_secret COURSEFLOW_JWT_SECRET 32 \
  courseflow-local-cluster-jwt-secret-change-me-32 \
  courseflow \
  password \
  admin
check_secret COURSEFLOW_INTERNAL_JWT_SECRET 32 \
  courseflow-local-internal-jwt-secret-change-me-32 \
  courseflow \
  password \
  admin
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

  script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
  backend_dir="$(CDPATH= cd -- "$script_dir/.." && pwd)"
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

  for (const [key, value] of envEntries(service.environment)) {
    const upperKey = key.toUpperCase();
    const lowerValue = value.trim().toLowerCase();
    if (upperKey === "SPRING_LIQUIBASE_CONTEXTS" && lowerValue.split(",").map((part) => part.trim()).includes("demo")) {
      secretViolations.push(`${serviceName}.${key} includes demo`);
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

if (publishedPortViolations.length > 0 || secretViolations.length > 0) {
  process.exit(1);
}
EOF_NODE
fi

echo "prod profile validation passed"
