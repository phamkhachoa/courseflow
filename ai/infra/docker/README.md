# CourseFlow AI Local Cluster

This Compose project runs the AI platform runtime independently from the backend and data platform
clusters. Backend services integrate with AI through `RECOMMENDATION_ML_SERVICE_URL` /
`RECOMMENDATION_ML_SERVICE_URI`; they do not share the AI database or start AI containers.

## Start

From `v2/courseflow/ai`:

```bash
docker compose -f infra/docker/docker-compose.yml up --build
```

Recommendation ML API:

```text
http://localhost:18088
```

Postgres is published only for local diagnostics:

```text
localhost:15434/cf_recommendation_ml
```

## Worker

Run the async training worker with the `worker` profile:

```bash
COMPOSE_PROFILES=worker docker compose -f infra/docker/docker-compose.yml up --build
```

## Migrations

Local API startup runs Alembic by default through `RECOMMENDATION_ML_RUN_MIGRATIONS=true`.
For production-shaped runs, disable API migrations and execute the migrator explicitly:

```bash
RECOMMENDATION_ML_RUN_MIGRATIONS=false \
docker compose -f infra/docker/docker-compose.yml --profile migration run --rm recommendation-ml-migrator
```

## Backend Integration

The backend local cluster defaults to:

```text
RECOMMENDATION_ML_SERVICE_URL=http://host.docker.internal:18088
RECOMMENDATION_ML_SERVICE_URI=http://host.docker.internal:18088
```

Override those values when AI runs behind a different hostname, platform network or gateway.
