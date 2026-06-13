# CourseFlow Backend Local Infra

Run infrastructure only:

```bash
docker compose -f infra/docker/docker-compose.yml up -d
```

This starts Postgres, MongoDB, Redis, Kafka, Kafka Connect, Elasticsearch, Keycloak and MinIO.
Postgres creates one database per service. Service schema is created by each service's Liquibase changelog on first startup.
Postgres is started with logical replication enabled so Debezium can capture source tables for
Elasticsearch projections. Business events still use transactional outbox and Kafka.

To run every backend service as separate local containers, use the full local cluster override:

```bash
docker compose -f infra/docker/docker-compose.yml -f infra/docker/docker-compose.services.yml up --build
```

Optional observability stack:

```bash
docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  -f infra/docker/docker-compose.observability.yml \
  up --build
```

Prometheus: `http://localhost:19090`
Grafana: `http://localhost:13000` (default local user/password `admin` / `admin`)

See `infra/docker/LOCAL_CLUSTER.md` for details. Demo data is behind the Liquibase `demo` context; set
`SPRING_LIQUIBASE_CONTEXTS=prod,demo` only for local/demo environments.

## Object storage (MinIO)

MinIO is the S3-compatible object store used for uploaded files, video sources/renditions, submission attachments and session recordings.

- S3 API: `http://localhost:9000`
- Web console: `http://localhost:9001` (user `courseflow`, password `courseflow`)
- Buckets created automatically by the `minio-setup` container: `courseflow-media`, `courseflow-recordings`

Services talk to MinIO via `courseflow.storage.*` config (default `provider: minio`, `endpoint: http://localhost:9000`).

## Debezium course search projection

The local infra registers the `courseflow-course-search-cdc` Kafka Connect connector from
`infra/docker/debezium/course-search-cdc-connector-config.json`.

Flow:

```text
cf_course.public.courses
  -> Debezium PostgreSQL connector
  -> Kafka topic courseflow.course.public.courses
  -> search-service consumer
  -> Elasticsearch index courseflow-course-search
```

`outbox-relay` remains responsible for business events such as `course.published` and
`course.completed`; Elasticsearch sync does not depend on outbox rows.

## PostgreSQL settings for Debezium

Local Compose starts Postgres with:

```text
wal_level=logical
max_replication_slots=10
max_wal_senders=10
```

For shared or production environments, apply the same class of settings through the database parameter
group/config file, then restart Postgres if the provider requires it. Also create a dedicated Debezium
user with replication/publication privileges instead of using the application owner account.

Operational notes:

- One Debezium connector normally needs one replication slot; size `max_replication_slots` for all
  connectors plus headroom.
- `max_wal_senders` must be high enough for active logical replication streams.
- Monitor inactive replication slots because retained WAL can grow until disk pressure appears.
- For `pgoutput`, no custom decoder plugin is required on PostgreSQL 10+.

## Backup / restore drill

Run a local backup of every Postgres service database:

```bash
scripts/postgres-backup-drill.sh backup
```

Restore-check one dump into a temporary database:

```bash
scripts/postgres-backup-drill.sh restore-check backups/postgres/<timestamp> cf_identity
```

## Trust boundary

The gateway strips client-supplied `X-User-*` and `X-Service-Token` headers. After JWT validation it
adds verified identity headers plus the shared service token; downstream services reject forged
identity headers unless that token matches `COURSEFLOW_SERVICE_TOKEN`.

When `SPRING_LIQUIBASE_CONTEXTS=prod,demo` is enabled, demo accounts are seeded in `identity-service` with password `password`:

- `admin@courseflow.local`
- `professor@courseflow.local`
- `ta@courseflow.local`
- `student@courseflow.local`
