#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
backend_dir="$(cd "$script_dir/.." && pwd)"

image_ref="${1:-${RECOMMENDATION_ML_IMAGE_REF:-}}"
if [ -z "$image_ref" ]; then
  echo "Usage: scripts/recommendation-ml-image-runtime-smoke.sh <image-ref>" >&2
  exit 1
fi

postgres_image="${RECOMMENDATION_ML_IMAGE_RUNTIME_POSTGRES_IMAGE:-postgres:16-alpine}"
run_id="$(date +%s)-$$"
network_name="${RECOMMENDATION_ML_IMAGE_RUNTIME_NETWORK:-courseflow-reco-ml-image-${run_id}}"
postgres_container="${RECOMMENDATION_ML_IMAGE_RUNTIME_POSTGRES_CONTAINER:-courseflow-reco-ml-image-pg-${run_id}}"
app_container="${RECOMMENDATION_ML_IMAGE_RUNTIME_APP_CONTAINER:-courseflow-reco-ml-image-app-${run_id}}"
internal_jwt_secret="${COURSEFLOW_INTERNAL_JWT_SECRET:-courseflow-local-internal-jwt-secret-change-me-32}"
evidence_file_path="${RECOMMENDATION_ML_IMAGE_RUNTIME_EVIDENCE_FILE:-}"
python_bin="${PYTHON:-python3}"

backend_absolute_path() {
  case "$1" in
    "")
      printf '\n'
      ;;
    /*)
      printf '%s\n' "$1"
      ;;
    *)
      printf '%s/%s\n' "$backend_dir" "$1"
      ;;
  esac
}

evidence_file="$(backend_absolute_path "$evidence_file_path")"

cleanup() {
  docker rm -f "$app_container" "$postgres_container" >/dev/null 2>&1 || true
  docker network rm "$network_name" >/dev/null 2>&1 || true
}
trap cleanup EXIT

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_command docker
require_command "$python_bin"

docker network create "$network_name" >/dev/null
docker run --rm -d \
  --name "$postgres_container" \
  --network "$network_name" \
  --network-alias postgres \
  -e POSTGRES_DB=cf_recommendation_ml \
  -e POSTGRES_USER=courseflow \
  -e POSTGRES_PASSWORD=courseflow \
  "$postgres_image" >/dev/null

for attempt in $(seq 1 60); do
  if docker exec "$postgres_container" pg_isready \
    -U courseflow \
    -d cf_recommendation_ml >/dev/null 2>&1; then
    break
  fi
  if [ "$attempt" -eq 60 ]; then
    docker logs "$postgres_container" >&2 || true
    echo "Postgres did not become ready" >&2
    exit 1
  fi
  sleep 1
done

db_url="postgresql://courseflow:courseflow@postgres:5432/cf_recommendation_ml"
echo "Running Recommendation ML image migrations through ${image_ref}"
docker run --rm \
  --network "$network_name" \
  -e RECOMMENDATION_ML_DB_URL="$db_url" \
  -e COURSEFLOW_INTERNAL_JWT_SECRET="$internal_jwt_secret" \
  "$image_ref" \
  alembic upgrade head

echo "Starting Recommendation ML image runtime"
docker run -d \
  --name "$app_container" \
  --network "$network_name" \
  -e RECOMMENDATION_ML_DB_URL="$db_url" \
  -e COURSEFLOW_INTERNAL_JWT_SECRET="$internal_jwt_secret" \
  -e RECOMMENDATION_ML_REQUIRE_ACTIVE_MODEL_READY=true \
  -e RECOMMENDATION_ML_AUTO_ACTIVATE_TRAINED_MODELS=false \
  -e RECOMMENDATION_ML_SYNC_TRAINING_ENABLED=false \
  -e RECOMMENDATION_ML_DOCS_ENABLED=false \
  "$image_ref" >/dev/null

for attempt in $(seq 1 60); do
  health_state="$(docker inspect --format '{{.State.Health.Status}}' "$app_container")"
  if [ "$health_state" = "healthy" ]; then
    break
  fi
  if [ "$health_state" = "unhealthy" ]; then
    docker logs "$app_container" >&2 || true
    echo "Recommendation ML image runtime became unhealthy" >&2
    exit 1
  fi
  sleep 2
done

health_state="$(docker inspect --format '{{.State.Health.Status}}' "$app_container")"
if [ "$health_state" != "healthy" ]; then
  docker logs "$app_container" >&2 || true
  echo "Recommendation ML image runtime did not become healthy; status=${health_state}" >&2
  exit 1
fi

liveness_http="$(
  docker exec "$app_container" python -c \
    "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3).status)"
)"
readiness_http="$(
  cat <<'PY' | docker exec -i "$app_container" python -
import urllib.error
import urllib.request

try:
    urllib.request.urlopen("http://127.0.0.1:8080/actuator/health", timeout=3)
    print("unexpected-200")
except urllib.error.HTTPError as exc:
    print(exc.code)
PY
)"

if [ "$liveness_http" != "200" ]; then
  echo "Expected liveness /health=200, got ${liveness_http}" >&2
  exit 1
fi
if [ "$readiness_http" != "503" ]; then
  echo "Expected readiness /actuator/health=503 without active model, got ${readiness_http}" >&2
  exit 1
fi

echo "Recommendation ML image runtime smoke passed: dockerHealth=${health_state} livenessHttp=${liveness_http} readinessHttp=${readiness_http}"

if [ -n "$evidence_file" ]; then
  mkdir -p "$(dirname "$evidence_file")"
  "$python_bin" - <<PY
import json
from pathlib import Path

evidence = {
    "artifactType": "recommendation_ml_image_runtime_smoke_evidence",
    "artifactVersion": 1,
    "status": "pass",
    "imageRef": "$image_ref",
    "dockerHealth": "$health_state",
    "livenessHttp": int("$liveness_http"),
    "readinessHttp": int("$readiness_http"),
}
Path("$evidence_file").write_text(json.dumps(evidence, indent=2) + "\\n", encoding="utf-8")
print(f"Recommendation ML image runtime smoke evidence written to {Path('$evidence_file')}")
PY
fi
