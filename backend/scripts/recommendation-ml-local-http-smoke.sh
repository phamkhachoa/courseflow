#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
backend_dir="$(cd "$script_dir/.." && pwd)"
repo_root="$(cd "$backend_dir/.." && pwd)"
service_dir="$repo_root/ai/services/recommendation-ml-service"

postgres_image="${RECOMMENDATION_ML_LOCAL_SMOKE_POSTGRES_IMAGE:-postgres:16-alpine}"
container="${RECOMMENDATION_ML_LOCAL_SMOKE_CONTAINER:-courseflow-reco-ml-http-smoke-$(date +%s)}"
internal_jwt_secret="${COURSEFLOW_INTERNAL_JWT_SECRET:-courseflow-local-internal-jwt-secret-change-me-32}"
uvicorn_log_path="${RECOMMENDATION_ML_LOCAL_SMOKE_UVICORN_LOG:-/tmp/courseflow-recommendation-ml-uvicorn.log}"
worker_log_path="${RECOMMENDATION_ML_LOCAL_SMOKE_WORKER_LOG:-/tmp/courseflow-recommendation-ml-worker.log}"
evidence_file_path="${RECOMMENDATION_ML_LOCAL_SMOKE_EVIDENCE_FILE:-/tmp/courseflow-recommendation-ml-ops-smoke-evidence.json}"
server_pid=""
worker_pid=""

backend_absolute_path() {
  case "$1" in
    /*)
      printf '%s\n' "$1"
      ;;
    *)
      printf '%s/%s\n' "$backend_dir" "$1"
      ;;
  esac
}

resolve_python_bin() {
  if [ -n "${PYTHON:-}" ]; then
    printf '%s\n' "$PYTHON"
    return
  fi
  local candidate
  for candidate in python3.12 python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return
    fi
  done
  echo "python"
}

python_bin="$(resolve_python_bin)"
uvicorn_log="$(backend_absolute_path "$uvicorn_log_path")"
worker_log="$(backend_absolute_path "$worker_log_path")"
evidence_file="$(backend_absolute_path "$evidence_file_path")"

cleanup() {
  if [ -n "$worker_pid" ] && kill -0 "$worker_pid" >/dev/null 2>&1; then
    kill "$worker_pid" >/dev/null 2>&1 || true
    wait "$worker_pid" >/dev/null 2>&1 || true
  fi
  if [ -n "$server_pid" ] && kill -0 "$server_pid" >/dev/null 2>&1; then
    kill "$server_pid" >/dev/null 2>&1 || true
    wait "$server_pid" >/dev/null 2>&1 || true
  fi
  docker rm -f "$container" >/dev/null 2>&1 || true
}
trap cleanup EXIT

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_command docker
require_command node
require_command curl
require_command "$python_bin"

cd "$repo_root"

docker run --rm -d --name "$container" \
  -e POSTGRES_DB=cf_recommendation_ml \
  -e POSTGRES_USER=courseflow \
  -e POSTGRES_PASSWORD=courseflow \
  -p 127.0.0.1::5432 \
  "$postgres_image" >/dev/null

for attempt in $(seq 1 60); do
  if docker exec "$container" pg_isready \
    -U courseflow \
    -d cf_recommendation_ml >/dev/null 2>&1; then
    break
  fi
  if [ "$attempt" -eq 60 ]; then
    docker logs "$container" >&2 || true
    echo "Postgres did not become ready" >&2
    exit 1
  fi
  sleep 1
done

pg_port="$(docker port "$container" 5432/tcp | sed 's/.*://')"
db_url="postgresql://courseflow:courseflow@localhost:${pg_port}/cf_recommendation_ml"
echo "Migrating Recommendation ML DB on localhost:${pg_port}"
(
  cd "$service_dir"
  PYTHONPATH=src \
  RECOMMENDATION_ML_DB_URL="$db_url" \
  COURSEFLOW_INTERNAL_JWT_SECRET="$internal_jwt_secret" \
  "$python_bin" -m alembic upgrade head
)

echo "Seeding active Recommendation ML baseline model"
(
  cd "$service_dir"
  PYTHONPATH=src \
  RECOMMENDATION_ML_DB_URL="$db_url" \
  COURSEFLOW_INTERNAL_JWT_SECRET="$internal_jwt_secret" \
  "$python_bin" - <<'PY'
from uuid import UUID, uuid4

from courseflow_ml.core.config import Settings
from courseflow_ml.domain.recommendation import TrainingInteraction
from courseflow_ml.repositories.postgres_recommendation_repository import (
    PostgresRecommendationRepository,
)
from courseflow_ml.services.recommendation_service import RecommendationMlService

settings = Settings()
repository = PostgresRecommendationRepository(settings.database_url)
service = RecommendationMlService(
    repository,
    min_activation_event_count=2,
    min_activation_principal_count=1,
    min_activation_course_count=2,
    min_activation_pair_count=1,
    min_activation_quality_score=0.0,
    auto_activate_trained_models=True,
)
course_a = UUID("30000000-0000-0000-0000-0000000a0001")
course_b = UUID("30000000-0000-0000-0000-0000000a0002")
interactions = []
for index in range(1, 7):
    interactions.append(
        TrainingInteraction(f"local-smoke-learner-{index}", course_a, "ENROLLMENT")
    )
    interactions.append(
        TrainingInteraction(f"local-smoke-learner-{index}", course_b, "ENROLLMENT")
    )
run_id = uuid4()
model_version = f"local-smoke-active-{run_id.hex[:12]}"
response = service.train_related_courses(
    run_id,
    model_version,
    1,
    10,
    interactions,
    "service:local-http-smoke-seed",
)
print(
    {
        "trainingRunId": str(run_id),
        "modelVersion": model_version,
        "status": response["status"],
    }
)
PY
)

api_port="$("$python_bin" - <<'PY'
import socket

with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
)"
mkdir -p "$(dirname "$uvicorn_log")" "$(dirname "$worker_log")" "$(dirname "$evidence_file")"
rm -f "$uvicorn_log" "$worker_log" "$evidence_file"
(
  cd "$service_dir"
  PYTHONPATH=src \
  RECOMMENDATION_ML_DB_URL="$db_url" \
  COURSEFLOW_INTERNAL_JWT_SECRET="$internal_jwt_secret" \
  RECOMMENDATION_ML_REQUIRE_ACTIVE_MODEL_READY=true \
  RECOMMENDATION_ML_AUTO_ACTIVATE_TRAINED_MODELS=false \
  RECOMMENDATION_ML_SYNC_TRAINING_ENABLED=false \
  RECOMMENDATION_ML_DOCS_ENABLED=false \
  "$python_bin" -m uvicorn courseflow_ml.main:app \
    --host 127.0.0.1 \
    --port "$api_port" >"$uvicorn_log" 2>&1
) &
server_pid=$!

for attempt in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${api_port}/health" >/dev/null 2>&1; then
    break
  fi
  if [ "$attempt" -eq 60 ]; then
    echo "Recommendation ML API did not become ready; Uvicorn log follows" >&2
    cat "$uvicorn_log" >&2 || true
    exit 1
  fi
  sleep 1
done

echo "Starting Recommendation ML worker for queued smoke job"
(
  cd "$service_dir"
  PYTHONPATH=src \
  RECOMMENDATION_ML_DB_URL="$db_url" \
  COURSEFLOW_INTERNAL_JWT_SECRET="$internal_jwt_secret" \
  RECOMMENDATION_ML_REQUIRE_ACTIVE_MODEL_READY=true \
  RECOMMENDATION_ML_AUTO_ACTIVATE_TRAINED_MODELS=false \
  RECOMMENDATION_ML_SYNC_TRAINING_ENABLED=false \
  "$python_bin" -m courseflow_ml.training.cli worker \
    --worker-id local-http-smoke-worker \
    --idle-sleep-seconds 1 >"$worker_log" 2>&1
) &
worker_pid=$!

echo "Running Recommendation ML HTTP ops smoke on localhost:${api_port}"
(
  cd "$backend_dir"
  RECOMMENDATION_ML_SMOKE_URL="http://127.0.0.1:${api_port}" \
  COURSEFLOW_INTERNAL_JWT_SECRET="$internal_jwt_secret" \
  RECOMMENDATION_ML_SMOKE_INTERNAL_JWT_SECRET="$internal_jwt_secret" \
  RECOMMENDATION_ML_SMOKE_REQUIRE_ACTIVE_MODEL=true \
  RECOMMENDATION_ML_SMOKE_MUTATION_FLOW_ENABLED=true \
  RECOMMENDATION_ML_SMOKE_EXPECT_SYNC_TRAIN_DISABLED=true \
  RECOMMENDATION_ML_SMOKE_EVIDENCE_FILE="$evidence_file" \
  node scripts/recommendation-ml-ops-smoke.mjs
)

echo "Recommendation ML local HTTP smoke evidence: $evidence_file"
"$python_bin" - <<PY
import json
from pathlib import Path

payload = json.loads(Path("$evidence_file").read_text())
print(json.dumps({
    "status": payload["status"],
    "checks": len(payload["checks"]),
    "mutationFlow": payload["mutationFlow"],
}, indent=2))
PY
