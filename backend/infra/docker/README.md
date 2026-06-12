# CourseFlow Backend Local Infra

Run infrastructure only:

```bash
docker compose -f infra/docker/docker-compose.yml up -d
```

This starts Postgres, MongoDB, Redis, Kafka, Kafka Connect, Elasticsearch, Keycloak and MinIO.
Postgres creates one database per service. Service schema is created by each service's Liquibase changelog on first startup.

To run every backend service as separate local containers, use the full local cluster override:

```bash
docker compose -f infra/docker/docker-compose.yml -f infra/docker/docker-compose.services.yml up --build
```

See `infra/docker/LOCAL_CLUSTER.md` for details. Demo data is behind the Liquibase `demo` context; set
`LIQUIBASE_CONTEXTS=prod,demo` only for local/demo environments.

## Object storage (MinIO)

MinIO is the S3-compatible object store used for uploaded files, video sources/renditions, submission attachments and session recordings.

- S3 API: `http://localhost:9000`
- Web console: `http://localhost:9001` (user `courseflow`, password `courseflow`)
- Buckets created automatically by the `minio-setup` container: `courseflow-media`, `courseflow-recordings`

Services talk to MinIO via `courseflow.storage.*` config (default `provider: minio`, `endpoint: http://localhost:9000`).

When `LIQUIBASE_CONTEXTS=prod,demo` is enabled, demo accounts are seeded in `identity-service` with password `Password123!`:

- `admin@courseflow.local`
- `professor@courseflow.local`
- `ta@courseflow.local`
- `student@courseflow.local`
