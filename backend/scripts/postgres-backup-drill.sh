#!/usr/bin/env bash
set -euo pipefail

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-courseflow-postgres}"
POSTGRES_USER="${POSTGRES_USER:-courseflow}"
DEFAULT_BACKUP_DIR="backups/postgres/$(date -u +%Y%m%dT%H%M%SZ)"
RESTORE_TEMP_DB=""

DATABASES=(
  cf_access_control
  cf_user_management
  cf_organization
  cf_course
  cf_enrollment
  cf_assignment
  cf_deadline
  cf_announcement
  cf_discussion
  cf_notification
  cf_media
  cf_analytics
  cf_recommendation_ml
  cf_gradebook
  cf_quiz
  cf_certificate
  cf_peer_review
  cf_live_session
  cf_review
  cf_outbox
  cf_promotion
  cf_loyalty
)

usage() {
  cat <<'USAGE'
Usage:
  scripts/postgres-backup-drill.sh backup [backup-dir]
  scripts/postgres-backup-drill.sh restore-check <backup-dir> [database]

Environment:
  POSTGRES_CONTAINER   Docker container name, default courseflow-postgres
  POSTGRES_USER        PostgreSQL user, default courseflow
  RESTORE_DRILL_REF    Optional restore drill reference written to restore-check evidence
  RESTORE_DRILL_EVIDENCE_FILE
                      Optional restore-check evidence JSON path
  RECOMMENDATION_ML_EXPECTED_MIGRATION_REVISION
                      Expected ML Alembic revision for cf_recommendation_ml restore probes

Examples:
  scripts/postgres-backup-drill.sh backup
  scripts/postgres-backup-drill.sh restore-check backups/postgres/20260612T120000Z cf_promotion
  scripts/postgres-backup-drill.sh restore-check backups/postgres/20260612T120000Z cf_recommendation_ml
USAGE
}

require_container() {
  if ! docker inspect "$POSTGRES_CONTAINER" >/dev/null 2>&1; then
    echo "Postgres container not found: $POSTGRES_CONTAINER" >&2
    echo "Start local infra first: docker compose -f infra/docker/docker-compose.yml up -d postgres" >&2
    exit 1
  fi
}

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1"
  else
    shasum -a 256 "$1"
  fi
}

sha256_hex() {
  sha256_file "$1" | awk '{print $1}'
}

json_escape() {
  local value="$1"
  value=${value//\\/\\\\}
  value=${value//\"/\\\"}
  value=${value//$'\n'/\\n}
  value=${value//$'\r'/\\r}
  value=${value//$'\t'/\\t}
  printf '%s' "$value"
}

cleanup_restore_db() {
  if [[ -z "${RESTORE_TEMP_DB:-}" ]]; then
    return 0
  fi
  docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
    -c "DROP DATABASE IF EXISTS $RESTORE_TEMP_DB" >/dev/null || true
  RESTORE_TEMP_DB=""
}

backup() {
  local backup_dir="${1:-$DEFAULT_BACKUP_DIR}"
  require_container
  mkdir -p "$backup_dir"
  : > "$backup_dir/SHA256SUMS"

  for db in "${DATABASES[@]}"; do
    local dump_file="$backup_dir/$db.dump"
    echo "Backing up $db -> $dump_file"
    docker exec "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" -Fc "$db" > "$dump_file"
    test -s "$dump_file"
    sha256_file "$dump_file" >> "$backup_dir/SHA256SUMS"
  done

  cat > "$backup_dir/MANIFEST.txt" <<EOF_MANIFEST
created_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
postgres_container=$POSTGRES_CONTAINER
postgres_user=$POSTGRES_USER
format=pg_dump_custom
database_count=${#DATABASES[@]}
EOF_MANIFEST

  echo "Backup complete: $backup_dir"
  echo "Run restore check: scripts/postgres-backup-drill.sh restore-check $backup_dir cf_promotion"
  echo "Run ML restore check: scripts/postgres-backup-drill.sh restore-check $backup_dir cf_recommendation_ml"
}

restore_probe() {
  local db="$1"
  docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$RESTORE_TEMP_DB" -v ON_ERROR_STOP=1 \
    -c "select current_database() as restored_database, now() as checked_at" >/dev/null

  case "$db" in
    cf_recommendation_ml)
      local expected_revision
      local escaped_revision
      expected_revision="${RECOMMENDATION_ML_EXPECTED_MIGRATION_REVISION:-007_model_activation_governance}"
      escaped_revision="${expected_revision//\'/\'\'}"
      docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$RESTORE_TEMP_DB" -v ON_ERROR_STOP=1 <<SQL >/dev/null
DO \$\$
BEGIN
  IF to_regclass('public.recommendation_training_runs') IS NULL THEN
    RAISE EXCEPTION 'missing recommendation_training_runs table after restore';
  END IF;
  IF to_regclass('public.recommendation_model_versions') IS NULL THEN
    RAISE EXCEPTION 'missing recommendation_model_versions table after restore';
  END IF;
  IF to_regclass('public.recommendation_model_activation_approvals') IS NULL THEN
    RAISE EXCEPTION 'missing recommendation_model_activation_approvals table after restore';
  END IF;
  IF NOT EXISTS (
    SELECT 1
    FROM public.alembic_version
    WHERE version_num = '$escaped_revision'
  ) THEN
    RAISE EXCEPTION 'cf_recommendation_ml Alembic revision mismatch: expected %', '$escaped_revision';
  END IF;
END;
\$\$;
SQL
      ;;
  esac
}

restore_probe_name() {
  local db="$1"
  case "$db" in
    cf_recommendation_ml)
      printf '%s' "recommendation_ml_schema_and_revision"
      ;;
    *)
      printf '%s' "generic_restore_connection"
      ;;
  esac
}

restore_check() {
  local backup_dir="${1:-}"
  local db="${2:-cf_promotion}"
  if [[ -z "$backup_dir" ]]; then
    usage
    exit 1
  fi
  local dump_file="$backup_dir/$db.dump"
  if [[ ! -s "$dump_file" ]]; then
    echo "Dump file not found or empty: $dump_file" >&2
    exit 1
  fi

  require_container
  local suffix
  suffix="$(date -u +%Y%m%d%H%M%S)"
  RESTORE_TEMP_DB="restore_drill_${db}_${suffix}"

  echo "Creating temporary restore database: $RESTORE_TEMP_DB"
  docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
    -c "CREATE DATABASE $RESTORE_TEMP_DB OWNER $POSTGRES_USER" >/dev/null
  trap cleanup_restore_db EXIT

  echo "Restoring $dump_file into $RESTORE_TEMP_DB"
  docker exec -i "$POSTGRES_CONTAINER" pg_restore -U "$POSTGRES_USER" -d "$RESTORE_TEMP_DB" --no-owner < "$dump_file"

  restore_probe "$db"

  local checked_at
  local artifact_hash
  local restore_drill_ref
  local evidence_file
  local restore_probe_label
  local temp_db
  checked_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  artifact_hash="sha256:$(sha256_hex "$dump_file")"
  restore_drill_ref="${RESTORE_DRILL_REF:-restore-drill-${db}-${suffix}}"
  evidence_file="${RESTORE_DRILL_EVIDENCE_FILE:-$backup_dir/restore-check-$db.json}"
  restore_probe_label="$(restore_probe_name "$db")"
  temp_db="$RESTORE_TEMP_DB"
  mkdir -p "$(dirname "$evidence_file")"
  cat > "$evidence_file" <<EOF_EVIDENCE
{
  "schemaVersion": 1,
  "artifactType": "postgres_restore_drill_evidence",
  "restoreDrillRef": "$(json_escape "$restore_drill_ref")",
  "databaseName": "$(json_escape "$db")",
  "backupPath": "$(json_escape "$dump_file")",
  "artifactHash": "$(json_escape "$artifact_hash")",
  "status": "PASSED",
  "restoreProbe": "$(json_escape "$restore_probe_label")",
  "checkedAt": "$(json_escape "$checked_at")",
  "postgresContainer": "$(json_escape "$POSTGRES_CONTAINER")",
  "postgresUser": "$(json_escape "$POSTGRES_USER")",
  "temporaryDatabase": "$(json_escape "$temp_db")",
  "generatedAt": "$(json_escape "$checked_at")"
}
EOF_EVIDENCE

  cleanup_restore_db
  trap - EXIT
  echo "Restore check passed for $db using $dump_file"
  echo "Restore drill evidence: $evidence_file"
  echo "Register restore drill payload values: restoreDrillRef=$restore_drill_ref databaseName=$db artifactHash=$artifact_hash checkedAt=$checked_at"
}

main() {
  local command="${1:-backup}"
  shift || true
  case "$command" in
    backup)
      backup "${1:-}"
      ;;
    restore-check)
      restore_check "${1:-}" "${2:-cf_promotion}"
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
