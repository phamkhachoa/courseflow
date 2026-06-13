#!/usr/bin/env bash
set -euo pipefail

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-courseflow-postgres}"
POSTGRES_USER="${POSTGRES_USER:-courseflow}"
DEFAULT_BACKUP_DIR="backups/postgres/$(date -u +%Y%m%dT%H%M%SZ)"
RESTORE_TEMP_DB=""

DATABASES=(
  cf_identity
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
  cf_gradebook
  cf_quiz
  cf_certificate
  cf_peer_review
  cf_live_session
  cf_review
  cf_outbox
)

usage() {
  cat <<'USAGE'
Usage:
  scripts/postgres-backup-drill.sh backup [backup-dir]
  scripts/postgres-backup-drill.sh restore-check <backup-dir> [database]

Environment:
  POSTGRES_CONTAINER   Docker container name, default courseflow-postgres
  POSTGRES_USER        PostgreSQL user, default courseflow

Examples:
  scripts/postgres-backup-drill.sh backup
  scripts/postgres-backup-drill.sh restore-check backups/postgres/20260612T120000Z cf_identity
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
  echo "Run restore check: scripts/postgres-backup-drill.sh restore-check $backup_dir cf_identity"
}

restore_check() {
  local backup_dir="${1:-}"
  local db="${2:-cf_identity}"
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

  docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$RESTORE_TEMP_DB" -v ON_ERROR_STOP=1 \
    -c "select current_database() as restored_database, now() as checked_at" >/dev/null

  cleanup_restore_db
  trap - EXIT
  echo "Restore check passed for $db using $dump_file"
}

main() {
  local command="${1:-backup}"
  shift || true
  case "$command" in
    backup)
      backup "${1:-}"
      ;;
    restore-check)
      restore_check "${1:-}" "${2:-cf_identity}"
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
