#!/bin/sh
set -eu

CONNECT_URL="${CONNECT_URL:-http://kafka-connect:8083}"
DB_HOST="${COURSEFLOW_DB_HOST:-postgres}"
DB_PORT="${COURSEFLOW_DB_PORT:-5432}"
DB_USER="${COURSEFLOW_DB_USERNAME:-courseflow}"
DB_NAME="${COURSEFLOW_COURSE_DB_NAME:-cf_course}"
DB_PASSWORD="${COURSEFLOW_DB_PASSWORD:?COURSEFLOW_DB_PASSWORD is required for the prod Debezium connector}"

case "$DB_PASSWORD" in
  *'
'*)
    echo "COURSEFLOW_DB_PASSWORD must not contain newlines for Debezium JSON registration" >&2
    exit 1
    ;;
esac

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g'
}

db_host_json="$(json_escape "$DB_HOST")"
db_port_json="$(json_escape "$DB_PORT")"
db_user_json="$(json_escape "$DB_USER")"
db_name_json="$(json_escape "$DB_NAME")"
db_password_json="$(json_escape "$DB_PASSWORD")"

cat > /tmp/course-search-cdc-connector-config.json <<EOF_CONFIG
{
  "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
  "database.hostname": "$db_host_json",
  "database.port": "$db_port_json",
  "database.user": "$db_user_json",
  "database.password": "$db_password_json",
  "database.dbname": "$db_name_json",
  "topic.prefix": "courseflow.course",
  "plugin.name": "pgoutput",
  "slot.name": "courseflow_course_search_cdc",
  "publication.name": "courseflow_course_search_cdc_publication",
  "table.include.list": "public.courses",
  "snapshot.mode": "initial",
  "tombstones.on.delete": "false",
  "key.converter": "org.apache.kafka.connect.json.JsonConverter",
  "key.converter.schemas.enable": "false",
  "value.converter": "org.apache.kafka.connect.json.JsonConverter",
  "value.converter.schemas.enable": "false",
  "topic.creation.default.replication.factor": "1",
  "topic.creation.default.partitions": "3"
}
EOF_CONFIG

until curl -fsS "$CONNECT_URL/connectors" >/dev/null; do
  echo "waiting for kafka-connect..."
  sleep 2
done

curl -fsS -X PUT \
  -H 'Content-Type: application/json' \
  --data @/tmp/course-search-cdc-connector-config.json \
  "$CONNECT_URL/connectors/courseflow-course-search-cdc/config"

echo 'Debezium connector ready: courseflow-course-search-cdc'
